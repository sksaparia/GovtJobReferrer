# config.py — Central configuration for GovtJobReferrer

import os
from dotenv import load_dotenv

load_dotenv()

# ── AWS SES SMTP ──────────────────────────────────────────
SMTP_HOST     = os.getenv("AWS_SES_SMTP_HOST", "email-smtp.ap-south-1.amazonaws.com")
SMTP_PORT     = int(os.getenv("AWS_SES_SMTP_PORT", 587))
SMTP_USER     = os.getenv("AWS_SES_SMTP_USER", "")
SMTP_PASSWORD = os.getenv("AWS_SES_SMTP_PASSWORD", "")
FROM_EMAIL    = os.getenv("AWS_SES_FROM_EMAIL", "")
FROM_NAME     = os.getenv("AWS_SES_FROM_NAME", "Sachin - GK with Sachin")

# ── Referral Link ─────────────────────────────────────────
EBOOK_URL = os.getenv("EBOOK_REFERRAL_URL", "https://topmate.io/bloodyreal/2072489")

# ── Target Websites ───────────────────────────────────────
TARGET_SITES = {
    "railway": {
        "name": "Indian Railways",
        "base_url": "https://www.rrcgkp.gov.in",          # RRC Gorakhpur (Railway recruitment)
        "jobs_url": "https://www.rrcgkp.gov.in/vacancy.aspx",
        "pdf_listing_url": "https://www.rrcgkp.gov.in/notice.aspx",
        "selectors": {
            "job_links": "a[href*='.pdf'], a[href*='notification'], a[href*='vacancy']",
            "title": "title",
        },
        "keywords": ["notification", "vacancy", "recruitment", "result", "admit card"],
    },
    "ssc": {
        "name": "SSC",
        "base_url": "https://ssc.gov.in",
        "jobs_url": "https://ssc.gov.in/",
        "pdf_listing_url": "https://ssc.gov.in/",
        "selectors": {
            "job_links": "a[href*='.pdf'], .notice a, .latest-news a",
            "title": "title",
        },
        "keywords": ["notification", "recruitment", "result", "apply", "exam"],
    },
    "bank_of_baroda": {
        "name": "Bank of Baroda",
        "base_url": "https://www.bankofbaroda.in",
        "jobs_url": "https://www.bankofbaroda.in/careers/current-openings",
        "pdf_listing_url": "https://www.bankofbaroda.in/careers/current-openings",
        "selectors": {
            "job_links": "a[href*='.pdf'], .career-listing a, .job-listing a",
            "title": ".job-title, h3, h4",
        },
        "keywords": ["recruitment", "officer", "clerk", "specialist", "apply"],
    },
}

# ── Scraper Settings ──────────────────────────────────────
HEADLESS         = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"
SCRAPE_INTERVAL  = int(os.getenv("SCRAPE_INTERVAL_HOURS", 6))
REQUEST_DELAY    = 3          # seconds between requests (polite scraping)
PDF_DOWNLOAD_DIR = "data/pdfs"
DATA_FILE        = os.getenv("DATA_FILE", "data/students.csv")
LOG_FILE         = os.getenv("LOG_FILE", "logs/referrer.log")

# ── Telegram Alerts (optional) ────────────────────────────
TG_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Email Template Variables ──────────────────────────────
EMAIL_SUBJECT = "🔔 Naya Sarkari Job Notification — Free eBook bhi lelo!"
SENDER_NAME   = FROM_NAME
