# scraper/data_manager.py — Student data storage, deduplication, tracking

import os
import csv
import logging
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DATA_FILE

logger = logging.getLogger(__name__)

FIELDNAMES = ["email", "name", "phone", "roll_no", "exam", "source",
              "job_title", "job_url", "added_on", "email_sent", "email_sent_on"]


def ensure_csv_exists():
    """Create the CSV with headers if it doesn't exist."""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
        logger.info(f"Created student data file: {DATA_FILE}")


def load_existing_emails() -> set:
    """Return set of emails already in the CSV (for deduplication)."""
    ensure_csv_exists()
    emails = set()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("email"):
                emails.add(row["email"].lower().strip())
    return emails


def save_students(students: list[dict]) -> int:
    """
    Save new students to CSV. Skips duplicates by email.
    Returns count of newly added records.
    """
    ensure_csv_exists()
    existing = load_existing_emails()
    new_count = 0

    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        for s in students:
            email = s.get("email", "").lower().strip()
            if not email or email in existing:
                continue
            row = {field: s.get(field, "") for field in FIELDNAMES}
            row["added_on"]     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row["email_sent"]   = "false"
            row["email_sent_on"] = ""
            writer.writerow(row)
            existing.add(email)
            new_count += 1

    logger.info(f"Saved {new_count} new student records")
    return new_count


def get_pending_emails() -> list[dict]:
    """Return all students who haven't been emailed yet."""
    ensure_csv_exists()
    pending = []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("email") and row.get("email_sent", "").lower() != "true":
                pending.append(dict(row))
    logger.info(f"Found {len(pending)} students pending email")
    return pending


def mark_email_sent(email: str):
    """Update CSV to mark an email address as contacted."""
    ensure_csv_exists()
    rows = []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("email", "").lower().strip() == email.lower().strip():
                row["email_sent"]    = "true"
                row["email_sent_on"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rows.append(row)

    with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def build_student_list_from_scrape(jobs: list[dict], pdf_results: list[dict]) -> list[dict]:
    """
    Combine scrape results + PDF extracted emails into a unified student list.
    Each student gets enriched with the job context.
    """
    students = []

    # From PDF parsed student tables
    for pdf_result in pdf_results:
        exam = pdf_result.get("exam_details", {})
        exam_name = ", ".join(exam.get("exam_names", [])) or "Sarkari Job"
        for s in pdf_result.get("students", []):
            if s.get("email"):
                s.setdefault("exam", exam_name)
                s.setdefault("source", "PDF")
                students.append(s)

        # Also add emails extracted directly from PDF text
        for email in exam.get("emails_found", []):
            students.append({
                "email":  email,
                "name":   "",
                "exam":   exam_name,
                "source": "PDF_text",
            })

    # From job pages — any emails found in scraped HTML (contact emails)
    for job in jobs:
        if job.get("contact_email"):
            students.append({
                "email":     job["contact_email"],
                "name":      "",
                "exam":      job.get("title", ""),
                "source":    job.get("source", ""),
                "job_title": job.get("title", ""),
                "job_url":   job.get("url", ""),
            })

    return students
