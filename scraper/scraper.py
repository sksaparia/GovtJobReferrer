# scraper/scraper.py — Multi-site Government Job Scraper
# Uses Selenium for JS-heavy pages, BeautifulSoup for static parsing

import os
import time
import logging
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TARGET_SITES, HEADLESS, REQUEST_DELAY, PDF_DOWNLOAD_DIR

logger = logging.getLogger(__name__)


def get_chrome_driver() -> webdriver.Chrome:
    """Initialize a headless Chrome driver with anti-bot settings."""
    ua = UserAgent()
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(f"user-agent={ua.random}")
    options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def fetch_with_requests(url: str) -> BeautifulSoup | None:
    """Lightweight fetch using requests + BeautifulSoup for static pages."""
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
        logger.warning(f"requests fetch failed for {url}: {e}")
        return None


def fetch_with_selenium(driver: webdriver.Chrome, url: str, wait_selector: str = "body") -> BeautifulSoup | None:
    """Fetch a JS-rendered page via Selenium and return parsed soup."""
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
        )
        time.sleep(REQUEST_DELAY)
        return BeautifulSoup(driver.page_source, "lxml")
    except Exception as e:
        logger.warning(f"Selenium fetch failed for {url}: {e}")
        return None


def extract_job_links(soup: BeautifulSoup, base_url: str, keywords: list) -> list[dict]:
    """
    Extract all relevant job notification links from a parsed page.
    Returns list of dicts: {title, url, is_pdf}
    """
    jobs = []
    if not soup:
        return jobs

    all_links = soup.find_all("a", href=True)
    for link in all_links:
        href = link["href"].strip()
        text = link.get_text(strip=True)

        # Filter by keyword relevance
        text_lower = text.lower()
        href_lower = href.lower()
        is_relevant = any(kw in text_lower or kw in href_lower for kw in keywords)
        if not is_relevant or len(text) < 5:
            continue

        # Normalize URL
        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            full_url = base_url.rstrip("/") + href
        else:
            full_url = base_url.rstrip("/") + "/" + href

        is_pdf = ".pdf" in href_lower
        jobs.append({"title": text[:200], "url": full_url, "is_pdf": is_pdf})

    # Deduplicate by URL
    seen = set()
    unique = []
    for j in jobs:
        if j["url"] not in seen:
            seen.add(j["url"])
            unique.append(j)
    return unique


def download_pdf(url: str, dest_dir: str = PDF_DOWNLOAD_DIR) -> str | None:
    """Download a PDF to local storage. Returns local filepath or None."""
    os.makedirs(dest_dir, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0]
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    filepath = os.path.join(dest_dir, filename)

    if os.path.exists(filepath):
        logger.info(f"PDF already downloaded: {filepath}")
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


def scrape_site(site_key: str, driver: webdriver.Chrome) -> list[dict]:
    """
    Scrape a single target site for job notifications.
    Returns list of job dicts.
    """
    cfg = TARGET_SITES.get(site_key)
    if not cfg:
        return []

    logger.info(f"Scraping {cfg['name']} → {cfg['jobs_url']}")
    results = []

    # Try static fetch first, fall back to Selenium
    soup = fetch_with_requests(cfg["jobs_url"])
    if not soup or len(soup.find_all("a")) < 5:
        logger.info(f"Static fetch insufficient for {site_key}, using Selenium...")
        soup = fetch_with_selenium(driver, cfg["jobs_url"])

    if not soup:
        logger.error(f"Could not fetch {cfg['name']}")
        return []

    jobs = extract_job_links(soup, cfg["base_url"], cfg["keywords"])
    logger.info(f"Found {len(jobs)} job links on {cfg['name']}")

    for job in jobs:
        job["source"] = cfg["name"]
        job["source_key"] = site_key
        results.append(job)

        # Download PDFs
        if job["is_pdf"]:
            local_path = download_pdf(job["url"])
            job["local_pdf"] = local_path or ""
        else:
            job["local_pdf"] = ""

    return results


def scrape_all_sites() -> list[dict]:
    """
    Scrape all configured government job sites.
    Returns combined list of all job notifications found.
    """
    driver = get_chrome_driver()
    all_jobs = []
    try:
        for site_key in TARGET_SITES:
            try:
                jobs = scrape_site(site_key, driver)
                all_jobs.extend(jobs)
                time.sleep(REQUEST_DELAY * 2)  # Polite delay between sites
            except Exception as e:
                logger.error(f"Error scraping {site_key}: {e}")
    finally:
        driver.quit()

    logger.info(f"Total job notifications scraped: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    jobs = scrape_all_sites()
    for j in jobs[:5]:
        print(f"[{j['source']}] {j['title'][:80]} — {'PDF' if j['is_pdf'] else 'Link'}")
