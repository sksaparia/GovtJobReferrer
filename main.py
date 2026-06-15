#!/usr/bin/env python3
# main.py — GovtJobReferrer Orchestrator
# Run this script to scrape → parse → email in one shot

import os
import sys
import logging
from datetime import datetime

from config import LOG_FILE, PDF_DOWNLOAD_DIR
from scraper.scraper import scrape_all_sites
from parser.pdf_parser import process_pdf
from scraper.data_manager import (
    save_students, get_pending_emails,
    build_student_list_from_scrape
)
from emailer.emailer import send_bulk_emails, send_telegram_alert

# ── Logging Setup ──────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")


def run_full_pipeline(dry_run: bool = False):
    """
    Full pipeline:
    1. Scrape all government job sites
    2. Download and parse PDFs
    3. Extract student emails from PDFs
    4. Save new students to CSV
    5. Send personalized referral emails via AWS SES
    6. Send Telegram summary
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"GovtJobReferrer Pipeline Started — {start_time:%Y-%m-%d %H:%M:%S}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info("=" * 60)

    # ── Step 1: Scrape job sites ───────────────────────────────────────────
    logger.info("STEP 1: Scraping government job websites...")
    jobs = scrape_all_sites()
    logger.info(f"Total jobs scraped: {len(jobs)}")

    if not jobs:
        logger.warning("No jobs scraped. Exiting.")
        return

    # ── Step 2: Parse PDFs ─────────────────────────────────────────────────
    logger.info("STEP 2: Parsing downloaded PDFs...")
    pdf_results = []
    pdf_jobs = [j for j in jobs if j.get("local_pdf")]

    for job in pdf_jobs:
        pdf_path = job["local_pdf"]
        if os.path.exists(pdf_path):
            result = process_pdf(pdf_path)
            result["job"] = job  # Attach job context
            pdf_results.append(result)
            logger.info(
                f"  PDF: {os.path.basename(pdf_path)} — "
                f"{len(result['students'])} student rows, "
                f"{len(result['exam_details'].get('emails_found', []))} emails found"
            )

    logger.info(f"PDFs processed: {len(pdf_results)}")

    # ── Step 3: Build student list ─────────────────────────────────────────
    logger.info("STEP 3: Building student contact list...")
    new_students = build_student_list_from_scrape(jobs, pdf_results)

    # Enrich students with job context
    for i, s in enumerate(new_students):
        if not s.get("job_url") and jobs:
            s["job_url"] = jobs[0].get("url", "")
        if not s.get("job_title") and jobs:
            s["job_title"] = jobs[0].get("title", "")

    saved = save_students(new_students)
    logger.info(f"New students saved: {saved}")

    # ── Step 4: Get all pending emails ────────────────────────────────────
    logger.info("STEP 4: Fetching pending email queue...")
    pending = get_pending_emails()
    logger.info(f"Students pending email: {len(pending)}")

    if not pending:
        logger.info("No pending emails. Pipeline complete.")
        _send_summary(start_time, len(jobs), len(pdf_results), 0, 0, 0)
        return

    # ── Step 5: Send emails ───────────────────────────────────────────────
    logger.info(f"STEP 5: Sending {'[DRY RUN] ' if dry_run else ''}emails...")
    stats = send_bulk_emails(pending, jobs, delay_seconds=1.2, dry_run=dry_run)

    # ── Step 6: Summary ───────────────────────────────────────────────────
    duration = (datetime.now() - start_time).seconds
    logger.info("=" * 60)
    logger.info(f"Pipeline Complete in {duration}s")
    logger.info(f"  Jobs scraped:  {len(jobs)}")
    logger.info(f"  PDFs parsed:   {len(pdf_results)}")
    logger.info(f"  Emails sent:   {stats['sent']}")
    logger.info(f"  Emails failed: {stats['failed']}")
    logger.info("=" * 60)

    _send_summary(start_time, len(jobs), len(pdf_results),
                  stats["sent"], stats["failed"], duration)


def _send_summary(start, jobs, pdfs, sent, failed, duration):
    """Send Telegram summary message."""
    msg = (
        f"✅ <b>GovtJobReferrer Run Complete</b>\n"
        f"📅 {start:%d %b %Y %H:%M}\n\n"
        f"🔍 Jobs scraped: <b>{jobs}</b>\n"
        f"📄 PDFs parsed: <b>{pdfs}</b>\n"
        f"📧 Emails sent: <b>{sent}</b>\n"
        f"❌ Failed: <b>{failed}</b>\n"
        f"⏱ Duration: {duration}s"
    )
    send_telegram_alert(msg)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run_full_pipeline(dry_run=dry_run)
