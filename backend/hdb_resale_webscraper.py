"""
Selenium-based scraper for live HDB resale listings from homes.hdb.gov.sg.

Opens the listing search page, lets the user apply filters manually, then
paginates through results to collect listing URLs. For each URL it loads the
detail page and extracts: address, postal code, town, flat type (rooms), price,
remaining lease, and storey range. Results are saved incrementally to
hdb_resale_2026.csv; failed URLs are written to hdb_resale_failed_urls.csv.

Usage:
    python hdb_resale_webscraper.py

The browser will open and pause for manual filter selection before scraping begins.
"""
import re
import time
import pandas as pd
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


START_URL = "https://homes.hdb.gov.sg/home/finding-a-flat"
LISTING_HREF_KEYWORD = "/home/resale/"
MAX_PAGES = 40
HEADLESS = False

OUTPUT_CSV = "hdb_resale_2026.csv"
FAILED_CSV = "hdb_resale_failed_urls.csv"
SAVE_EVERY = 100

DETAIL_TIMEOUT = 12
PAGE_TIMEOUT = 20
RETRIES_PER_URL = 2


def make_driver(headless=True):
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    
    options.page_load_strategy = "eager"

    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # Disable images for speed
    prefs = {
        "profile.managed_default_content_settings.images": 2,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options,
    )

    driver.set_page_load_timeout(PAGE_TIMEOUT)

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )
    return driver


def wait_for_document_ready(driver, timeout=15):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
    )


def wait_for_listing_text(driver, timeout=DETAIL_TIMEOUT):
    """
    Wait until body text contains at least one strong signal that the listing details loaded.
    """
    def _loaded(d):
        try:
            body = d.find_element(By.TAG_NAME, "body").text
            signals = [
                "Remaining lease",
                "Storey range",
                "Singapore",
                "Blk ",
                "BLK ",
                "$",
            ]
            return any(sig in body for sig in signals)
        except Exception:
            return False

    WebDriverWait(driver, timeout).until(_loaded)


def maybe_close_popups(driver):
    xpaths = [
        "//button[contains(., 'Accept')]",
        "//button[contains(., 'I agree')]",
        "//button[contains(., 'Close')]",
        "//button[contains(., 'OK')]",
        "//button[contains(., 'Got it')]",
    ]

    for xp in xpaths:
        try:
            elems = driver.find_elements(By.XPATH, xp)
            for e in elems:
                if e.is_displayed() and e.is_enabled():
                    try:
                        driver.execute_script("arguments[0].click();", e)
                        time.sleep(0.2)
                    except Exception:
                        pass
        except Exception:
            pass


def try_set_results_per_page(driver):
    try:
        selects = driver.find_elements(By.TAG_NAME, "select")
        for s in selects:
            try:
                sel = Select(s)
                values = [opt.get_attribute("value") for opt in sel.options]
                if "50" in values:
                    sel.select_by_value("50")
                    time.sleep(1)
                    print("Set results per page to 50")
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def get_listing_links_from_dom(driver):
    js = f"""
    const urls = new Set();
    document.querySelectorAll('a[href*="{LISTING_HREF_KEYWORD}"]').forEach(a => {{
        const href = a.href || a.getAttribute('href');
        if (href) urls.add(href);
    }});
    return [...urls];
    """
    links = driver.execute_script(js)
    return [x.strip() for x in links if x and x.strip()]


def click_next_page(driver):
    xpaths = [
        "//button[@aria-label='Next']",
        "//a[@aria-label='Next']",
        "//button[contains(., 'Next')]",
        "//a[contains(., 'Next')]",
        "//*[contains(@class, 'pagination')]//*[contains(., 'Next')]",
    ]

    for xp in xpaths:
        try:
            elems = driver.find_elements(By.XPATH, xp)
            for e in elems:
                if e.is_displayed() and e.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", e)
                    time.sleep(0.2)
                    driver.execute_script("arguments[0].click();", e)
                    return True
        except Exception:
            continue
    return False


def collect_listing_links(driver, max_pages=5):
    all_links = []
    seen = set()
    page = 1

    while page <= max_pages:
        wait_for_document_ready(driver)
        maybe_close_popups(driver)
        time.sleep(0.5)

        links = get_listing_links_from_dom(driver)
        fresh = [u for u in links if u not in seen]

        print(f"Page {page}: found {len(links)} links, {len(fresh)} new")

        for u in fresh:
            seen.add(u)
            all_links.append(u)

        if page == max_pages:
            break

        clicked = click_next_page(driver)
        if not clicked:
            print("No next page found. Stopping pagination.")
            break

        page += 1
        time.sleep(0.7)

    return all_links


def clean_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def get_label_value(lines, label):
    label_lower = label.lower()

    for i, line in enumerate(lines):
        current = line.strip().lower()

        if current == label_lower:
            if i + 1 < len(lines):
                return lines[i + 1].strip()

        if current.startswith(label_lower):
            value = line[len(label):].strip(" :")
            if value:
                return value

    return ""


def extract_price(lines, body_text):
    # Prefer a price-looking line
    for line in lines:
        if re.fullmatch(r"\$[\d,]+", line):
            return line

    m = re.search(r"\$[\d,]+", body_text)
    if m:
        return m.group(0)

    return ""


def parse_listing_from_text(url, body_text):
    lines = clean_lines(body_text)

    address = ""
    postal_code = ""
    town = ""
    rooms = ""
    remaining_lease = ""
    storey_range = ""
    price = ""

    # Address
    for line in lines:
        if line.lower().startswith("blk "):
            address = line
            break

    # Postal + town
    for line in lines:
        m = re.search(r"Singapore\s+(\d{6})\s+(.+)", line, flags=re.I)
        if m:
            postal_code = m.group(1)
            town = m.group(2).strip()
            break

    # Rooms
    for line in lines:
        if re.fullmatch(r"\d+\s*-\s*Room", line, flags=re.I) or line.lower() in {
            "executive",
            "multi-generation",
        }:
            rooms = line
            break

    remaining_lease = get_label_value(lines, "Remaining lease")
    storey_range = get_label_value(lines, "Storey range")
    price = extract_price(lines, body_text)

    # Fallback regex
    if not remaining_lease:
        m = re.search(r"Remaining lease\s*\n\s*(.+)", body_text, flags=re.I)
        if m:
            remaining_lease = m.group(1).strip()

    if not storey_range:
        m = re.search(r"Storey range\s*\n\s*(.+)", body_text, flags=re.I)
        if m:
            storey_range = m.group(1).strip()

    return {
        "url": url,
        "address": address,
        "postal_code": postal_code,
        "town": town,
        "rooms": rooms,
        "price": price,
        "remaining_lease": remaining_lease,
        "storey_range": storey_range,
    }


def row_looks_valid(row):
    filled = sum(bool(str(row.get(k, "")).strip()) for k in [
        "address", "postal_code", "town", "rooms", "price", "remaining_lease", "storey_range"
    ])
    return filled >= 3


def extract_listing(driver, url):
    driver.get(url)
    wait_for_document_ready(driver)
    maybe_close_popups(driver)
    wait_for_listing_text(driver)

    body_text = driver.find_element(By.TAG_NAME, "body").text
    row = parse_listing_from_text(url, body_text)

    if not row_looks_valid(row):
        raise ValueError("Listing loaded but parsed too few fields")

    row["scrape_failed"] = False
    return row


def extract_listing_with_retry(driver, url, retries=2):
    last_err = None

    for attempt in range(1, retries + 1):
        try:
            return extract_listing(driver, url)
        except Exception as e:
            last_err = e
            print(f"  Attempt {attempt}/{retries} failed: {e}")
            time.sleep(0.6 * attempt)

    return {
        "url": url,
        "address": "",
        "postal_code": "",
        "town": "",
        "rooms": "",
        "price": "",
        "remaining_lease": "",
        "storey_range": "",
        "scrape_failed": True,
        "error": str(last_err),
    }


def save_progress(rows, output_csv):
    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")


def main():
    print("Starting scraper...")
    driver = make_driver(headless=HEADLESS)
    rows = []

    try:
        driver.get(START_URL)
        wait_for_document_ready(driver)
        time.sleep(2)
        maybe_close_popups(driver)

        input("Set your filters on the page, then press Enter to continue... ")

        try_set_results_per_page(driver)

        print("Collecting listing links...")
        links = collect_listing_links(driver, max_pages=MAX_PAGES)

        if not links:
            print("No listing links found.")
            return

        print(f"Total listing links collected: {len(links)}")
        print("Now scraping listing details...")

        start = time.time()

        for i, link in enumerate(links, start=1):
            print(f"[{i}/{len(links)}] Scraping {link}")
            row = extract_listing_with_retry(driver, link, retries=RETRIES_PER_URL)
            rows.append(row)

            if i % SAVE_EVERY == 0:
                save_progress(rows, OUTPUT_CSV)
                elapsed = time.time() - start
                rate = i / elapsed if elapsed > 0 else 0
                eta = (len(links) - i) / rate if rate > 0 else 0
                print(f"Saved progress at {i} rows | rate={rate:.2f} rows/s | ETA={eta/60:.1f} min")

        save_progress(rows, OUTPUT_CSV)

        df = pd.DataFrame(rows)
        failed = df[df["scrape_failed"] == True][["url", "error"]] if "scrape_failed" in df.columns else pd.DataFrame()
        if len(failed) > 0:
            failed.to_csv(FAILED_CSV, index=False, encoding="utf-8-sig")

        print(f"Done. Saved {len(df)} rows to {OUTPUT_CSV}")
        if len(failed) > 0:
            print(f"Failed URLs saved to {FAILED_CSV}: {len(failed)}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()