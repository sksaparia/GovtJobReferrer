# emailer/emailer.py — AWS SES SMTP bulk emailer with personalized referral links

import os
import smtplib
import logging
import time
import hashlib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader, select_autoescape

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    FROM_EMAIL, FROM_NAME, EBOOK_URL, EMAIL_SUBJECT
)

logger = logging.getLogger(__name__)

# Jinja2 template environment
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__))
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html"]),
)


def build_referral_url(base_url: str, email: str, name: str = "") -> str:
    """
    Create a personalized referral URL with UTM tracking params.
    Adds a unique token per student for tracking clicks.
    """
    token = hashlib.md5(email.lower().encode()).hexdigest()[:8]
    slug  = name.lower().replace(" ", "_")[:20] if name else "student"
    return (
        f"{base_url}"
        f"?utm_source=email"
        f"&utm_medium=referral"
        f"&utm_campaign=govtjob_alert"
        f"&ref={slug}_{token}"
    )


def render_email_html(student: dict, job: dict) -> str:
    """Render the HTML email template with student + job context."""
    template = jinja_env.get_template("email_template.html")

    name      = student.get("name", "").strip() or "Student"
    email     = student.get("email", "")
    ref_url   = build_referral_url(EBOOK_URL, email, name)
    unsub_url = f"https://github.com/sachin/GovtJobReferrer/issues/new?title=Unsubscribe+{email}"

    context = {
        "name":          name,
        "source":        job.get("source", "Sarkari"),
        "job_title":     job.get("title", "Naya Job Notification"),
        "job_url":       job.get("url", "#"),
        "job_excerpt":   job.get("excerpt", "Official notification ke liye link dekho."),
        "last_date":     job.get("last_date", ""),
        "vacancies":     job.get("vacancies", ""),
        "ebook_url":     ref_url,
        "unsubscribe_url": unsub_url,
    }
    return template.render(**context)


def send_email(to_email: str, to_name: str, html_body: str, subject: str = EMAIL_SUBJECT) -> bool:
    """
    Send a single HTML email via AWS SES SMTP.
    Returns True on success, False on failure.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"]      = f"{to_name} <{to_email}>" if to_name else to_email
    msg["Reply-To"] = FROM_EMAIL

    # Plain text fallback
    plain = (
        f"Namaste {to_name}!\n\n"
        f"Naya Sarkari Job Notification aaya hai.\n\n"
        f"Aur saath mein Bharat GK Master book bhi dekho:\n{EBOOK_URL}\n\n"
        f"Best of luck!\nSachin - GK with Sachin"
    )
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        logger.info(f"✅ Email sent to {to_email}")
        return True
    except smtplib.SMTPRecipientsRefused:
        logger.warning(f"Recipient refused: {to_email}")
    except smtplib.SMTPAuthenticationError:
        logger.error("SES SMTP auth failed — check credentials in .env")
    except Exception as e:
        logger.error(f"Email failed for {to_email}: {e}")
    return False


def send_bulk_emails(students: list[dict], jobs: list[dict],
                     delay_seconds: float = 1.2, dry_run: bool = False) -> dict:
    """
    Send personalized emails to all students.
    Picks the most relevant job per student based on source matching.
    Returns stats dict.
    """
    from scraper.data_manager import mark_email_sent

    # Build a quick job lookup by source
    job_by_source = {}
    for j in jobs:
        src = j.get("source_key", "")
        if src not in job_by_source:
            job_by_source[src] = j

    # Use the first job as fallback
    fallback_job = jobs[0] if jobs else {
        "title": "Naya Sarkari Job Notification",
        "url": "https://www.sarkariresult.com",
        "source": "Sarkari",
        "excerpt": "Latest government job notifications.",
    }

    stats = {"total": len(students), "sent": 0, "failed": 0, "skipped": 0}

    for student in students:
        email = student.get("email", "").strip()
        name  = student.get("name", "").strip()

        if not email:
            stats["skipped"] += 1
            continue

        # Pick best matching job
        src_key = student.get("source", "")
        job = job_by_source.get(src_key, fallback_job)

        html_body = render_email_html(student, job)

        if dry_run:
            logger.info(f"[DRY RUN] Would email: {email} ({name})")
            stats["sent"] += 1
            continue

        success = send_email(email, name, html_body)
        if success:
            mark_email_sent(email)
            stats["sent"] += 1
        else:
            stats["failed"] += 1

        time.sleep(delay_seconds)  # Rate limit: ~50 emails/min (SES free tier safe)

    logger.info(f"Bulk email done: {stats}")
    return stats


def send_telegram_alert(message: str):
    """Send a Telegram message as post-run summary (optional)."""
    import requests as req
    from config import TG_TOKEN, TG_CHAT_ID
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        req.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Telegram alert failed: {e}")


if __name__ == "__main__":
    # Quick test: render one email to test.html
    test_student = {"email": "test@example.com", "name": "Rahul Kumar", "source": "ssc"}
    test_job = {
        "title": "SSC CGL 2025 Notification",
        "url": "https://ssc.gov.in/",
        "source": "SSC",
        "excerpt": "SSC CGL 2025 ke liye applications shuru ho gayi hain. Total 17000+ vacancies.",
        "last_date": "15 July 2025",
        "vacancies": "17000",
    }
    html = render_email_html(test_student, test_job)
    with open("test_email_preview.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Email preview saved to test_email_preview.html")
