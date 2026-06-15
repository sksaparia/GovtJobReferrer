# scraper/scraper.py — No Selenium version (GitHub Actions compatible)

import os
import time
import logging
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TARGET_SITES, REQUEST_DELAY, PDF_DOWNLOAD_DIR

logger = logging.getLogger(__name__)


def fetch_page(url: str) -> BeautifulSoup | None:
    ua = UserAgent()
    headers = {
        "User-Agent": ua.random,
        "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        logger.warning(f"Fetch failed for {url}: {e}")
        return None


def extract_job_links(soup: BeautifulSoup, base_url: str, keywords: list) -> list[dict]:
    jobs = []
    if not soup:
        return jobs

    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        text = link.get_text(strip=True)
        text_lower = text.lower()
        href_lower = href.lower()

        is_relevant = any(kw in text_lower or kw in href_lower for kw in keywords)
        if not is_relevant or len(text) < 5:
            continue

        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            full_url = base_url.rstrip("/") + href
        else:
            full_url = base_url.rstrip("/") + "/" + href

        is_pdf = ".pdf" in href_lower
        jobs.append({"title": text[:200], "url": full_url, "is_pdf": is_pdf})

    seen = set()
    unique = []
    for j in jobs:
        if j["url"] not in seen:
            seen.add(j["url"])
            unique.append(j)
    return unique


def download_pdf(url: str, dest_dir: str = PDF_DOWNLOAD_DIR) -> str | None:
    os.makedirs(dest_dir, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0]
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    filepath = os.path.join(dest_dir, filename)

    if os.path.exists(filepath):
        return filepath

    try:
        ua = UserAgent()
        headers = {"User-Agent": ua.random}
        resp = requests.get(url, headers=headers, timeout=30, stream=True)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Downloaded PDF: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"PDF download failed for {url}: {e}")
        return None


def scrape_site(site_key: str) -> list[dict]:
    cfg = TARGET_SITES.get(site_key)
    if not cfg:
        return []

    logger.info(f"Scraping {cfg['name']} → {cfg['jobs_url']}")
    soup = fetch_page(cfg["jobs_url"])
    if not soup:
        logger.error(f"Could not fetch {cfg['name']}")
        return []

    jobs = extract_job_links(soup, cfg["base_url"], cfg["keywords"])
    logger.info(f"Found {len(jobs)} links on {cfg['name']}")

    results = []
    for job in jobs:
        job["source"] = cfg["name"]
        job["source_key"] = site_key
        if job["is_pdf"]:
            job["local_pdf"] = download_pdf(job["url"]) or ""
        else:
            job["local_pdf"] = ""
        results.append(job)

    return results


def scrape_all_sites() -> list[dict]:
    all_jobs = []
    for site_key in TARGET_SITES:
        try:
            jobs = scrape_site(site_key)
            all_jobs.extend(jobs)
            time.sleep(REQUEST_DELAY * 2)
        except Exception as e:
            logger.error(f"Error scraping {site_key}: {e}")

    logger.info(f"Total jobs scraped: {len(all_jobs)}")
    return all_jobs
