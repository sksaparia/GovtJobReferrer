# 🔔 GovtJobReferrer

**Automated Indian Government Job Scraper + Referral Email System**

> Scrapes Railway, SSC, and Bank of Baroda job notifications → Parses PDFs → Auto-emails students with your personalized eBook referral link via AWS SES.

Built by **Sachin** | [GK with Sachin](https://t.me/BharatGKCurrentAffairs) | [Bharat GK Master eBook](https://topmate.io/bloodyreal/2072489)

---

## ✨ Features

- 🔍 **Multi-site scraping** — Railway (RRC), SSC, Bank of Baroda using BeautifulSoup + Selenium
- 📄 **PDF parsing** — Extracts exam details, dates, vacancies, and student emails from official notification PDFs
- 📧 **Personalized emails** — HTML emails with UTM-tracked referral links per student, sent via AWS SES SMTP
- 💾 **Deduplication** — CSV-based student store ensures no one gets emailed twice
- 🤖 **Fully automated** — GitHub Actions runs twice daily (7 AM + 2 PM IST)
- 📢 **Telegram alerts** — Summary notification after each run
- 🔄 **Keep-alive** — Built-in workflow to prevent GitHub from disabling scheduled jobs

---

## 📁 Project Structure

```
GovtJobReferrer/
├── main.py                          # Orchestrator — runs full pipeline
├── config.py                        # Central config (reads from .env)
├── requirements.txt
│
├── scraper/
│   ├── scraper.py                   # Selenium + BeautifulSoup scraper
│   └── data_manager.py              # CSV storage, deduplication, queue
│
├── parser/
│   └── pdf_parser.py                # pdfplumber — exam details + student data
│
├── emailer/
│   ├── emailer.py                   # AWS SES SMTP bulk emailer
│   └── email_template.html          # Jinja2 HTML email template (Hindi)
│
├── data/
│   ├── students.csv                 # Student contact database (auto-created)
│   └── pdfs/                        # Downloaded PDF notifications
│
├── logs/
│   └── referrer.log                 # Run logs
│
└── .github/
    └── workflows/
        └── daily_run.yml            # GitHub Actions automation
```

---

## 🚀 Quick Setup

### 1. Clone the Repo

```bash
git clone https://github.com/YOUR_USERNAME/GovtJobReferrer.git
cd GovtJobReferrer
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** Chrome must be installed for Selenium. On Ubuntu/Debian:
> ```bash
> sudo apt-get install google-chrome-stable
> ```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:

```env
# AWS SES SMTP (get from AWS Console → SES → SMTP Settings)
AWS_SES_SMTP_HOST=email-smtp.ap-south-1.amazonaws.com
AWS_SES_SMTP_PORT=587
AWS_SES_SMTP_USER=YOUR_SMTP_USERNAME
AWS_SES_SMTP_PASSWORD=YOUR_SMTP_PASSWORD
AWS_SES_FROM_EMAIL=you@yourdomain.com
AWS_SES_FROM_NAME=Sachin - GK with Sachin

# Your eBook referral link
EBOOK_REFERRAL_URL=https://topmate.io/bloodyreal/2072489

# Optional: Telegram for run summaries
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 4. Test Run (Dry Run — no emails sent)

```bash
python main.py --dry-run
```

### 5. Live Run

```bash
python main.py
```

---

## ☁️ AWS SES Setup

### Step 1 — Verify Your Email/Domain in SES

1. Go to **AWS Console → Simple Email Service (SES)**
2. Under **Verified Identities**, click **Create Identity**
3. Add your sending domain or email address
4. Complete DNS verification (add TXT/CNAME records to your domain)

> 💡 **Free Tier:** AWS SES gives you **62,000 free emails/month** when sending from an EC2 instance or GitHub Actions.

### Step 2 — Create SMTP Credentials

1. In SES Console → **SMTP Settings** → **Create SMTP Credentials**
2. This creates an IAM user — download the credentials
3. Copy the **SMTP Username** and **SMTP Password** to your `.env`

### Step 3 — Move Out of Sandbox (Production Access)

By default, SES is in sandbox mode (can only send to verified emails). To send to real users:

1. SES Console → **Account Dashboard** → **Request Production Access**
2. Fill the form explaining your use case (exam alerts for students)
3. AWS approves within 24 hours

### Step 4 — Region Note

Use `ap-south-1` (Mumbai) for lowest latency from India:

```
email-smtp.ap-south-1.amazonaws.com
```

---

## 🤖 GitHub Actions — Auto Deploy

### Step 1 — Add Secrets to GitHub

Go to your repo → **Settings → Secrets and Variables → Actions → New repository secret**

Add these secrets:

| Secret Name | Value |
|---|---|
| `AWS_SES_SMTP_HOST` | `email-smtp.ap-south-1.amazonaws.com` |
| `AWS_SES_SMTP_PORT` | `587` |
| `AWS_SES_SMTP_USER` | Your SES SMTP username |
| `AWS_SES_SMTP_PASSWORD` | Your SES SMTP password |
| `AWS_SES_FROM_EMAIL` | Your verified sender email |
| `AWS_SES_FROM_NAME` | `Sachin - GK with Sachin` |
| `EBOOK_REFERRAL_URL` | `https://topmate.io/bloodyreal/2072489` |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token (optional) |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID (optional) |

### Step 2 — Push to GitHub

```bash
git add .
git commit -m "feat: initial GovtJobReferrer setup"
git push origin main
```

### Step 3 — Enable Actions

Go to **Actions tab** in your repo → Enable workflows if prompted.

The bot will automatically run:
- **7:00 AM IST** daily
- **2:00 PM IST** daily
- Manually via **Run workflow** button

---

## 🧪 Testing Individual Components

```bash
# Test scraper only
python -c "from scraper.scraper import scrape_all_sites; jobs = scrape_all_sites(); print(f'{len(jobs)} jobs found')"

# Test PDF parser
python parser/pdf_parser.py data/pdfs/sample.pdf

# Test email rendering (saves preview to test_email_preview.html)
python emailer/emailer.py

# Check pending email queue
python -c "from scraper.data_manager import get_pending_emails; print(len(get_pending_emails()), 'pending')"
```

---

## 📊 Student Data Format

Student emails are stored in `data/students.csv`:

| Column | Description |
|---|---|
| `email` | Student email address |
| `name` | Name (if found in PDF) |
| `phone` | Phone number (if found) |
| `roll_no` | Roll/registration number |
| `exam` | Exam name (SSC CGL, RRB NTPC, etc.) |
| `source` | Source website |
| `job_title` | Job notification title |
| `job_url` | Direct link to notification |
| `added_on` | Timestamp added |
| `email_sent` | `true`/`false` |
| `email_sent_on` | Timestamp emailed |

---

## 📧 Email Features

The HTML email (in Hindi + English) includes:
- ✅ Personalized greeting with student name
- ✅ Job notification details (title, source, last date, vacancies)
- ✅ UTM-tracked referral link unique to each student
- ✅ eBook promo block with CTA button
- ✅ Social media links (Instagram, Telegram channels)
- ✅ Unsubscribe link
- ✅ Plain text fallback

---

## 🛠️ Customization

### Add More Job Sites

Edit `config.py` → `TARGET_SITES` dict:

```python
"your_site": {
    "name": "Site Name",
    "base_url": "https://example.gov.in",
    "jobs_url": "https://example.gov.in/jobs",
    "selectors": {"job_links": "a[href*='.pdf']"},
    "keywords": ["recruitment", "vacancy"],
},
```

### Change Email Schedule

Edit `.github/workflows/daily_run.yml`:

```yaml
- cron: "30 1 * * *"   # 7:00 AM IST
- cron: "30 8 * * *"   # 2:00 PM IST
```

Use [crontab.guru](https://crontab.guru) to build your schedule.

### Customize Email Template

Edit `emailer/email_template.html` — it uses Jinja2 syntax.

Available template variables:
- `{{ name }}` — Student name
- `{{ source }}` — Source website
- `{{ job_title }}` — Job title
- `{{ job_url }}` — Job URL
- `{{ last_date }}` — Application last date
- `{{ vacancies }}` — Number of vacancies
- `{{ ebook_url }}` — Personalized referral URL (auto-generated)

---

## ⚠️ Legal & Ethical Notes

1. **Robots.txt:** The scraper respects `REQUEST_DELAY` between requests. Check each site's robots.txt before heavy scraping.
2. **SES Compliance:** Always include unsubscribe links (already in template). AWS SES requires CAN-SPAM compliance.
3. **Data Privacy:** Student emails from government PDFs are public domain. Don't share the CSV externally.
4. **Rate Limits:** AWS SES free tier allows 62,000 emails/month from GitHub Actions. The built-in 1.2-second delay keeps you safe.

---

## 🔗 Related Projects

- 📚 [Bharat GK Master eBook](https://topmate.io/bloodyreal/2072489) — ₹49
- 📢 [Telegram GK Channel](https://t.me/BharatGKCurrentAffairs)
- 🔔 [Sarkari Naukri Alerts](https://t.me/sarkari_naukri_alert_official)
- 📸 [Instagram GK Shorts](https://www.instagram.com/gkshortsnew/)

---

## 📄 License

MIT License — Free to use, modify, and distribute.

---

*Built with ❤️ for Indian competitive exam students | Jamshedpur, Jharkhand 🇮🇳*
