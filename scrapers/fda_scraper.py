import requests
import json
import time
import os
from bs4 import BeautifulSoup

BASE_URL = "https://www.fda.gov"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
}

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "fda_response.json")
PROCESSED_DATA_FILE = os.path.join(DATA_DIR, "fda_all_records.json")


def fetch_recall_list():
    """Fetch recall records from FDA API"""
    os.makedirs(DATA_DIR, exist_ok=True)

    url = f"{BASE_URL}/datatables/views/ajax"
    params = {
        "search_api_fulltext": "",
        "field_regulated_product_field": "2323",
        "field_terminated_recall": "All",
        "start": 0,
        "length": 1000,
        "_drupal_ajax": 1,
        "_wrapper_format": "drupal_ajax",
        "view_name": "recall_solr_index",
        "view_display_id": "recall_datatable_block_1",
        "view_base_path": "safety/recalls-market-withdrawals-safety-alerts/datatables-data",
    }

    response = requests.get(url, params=params, headers=HEADERS)
    data = response.json()

    # Save raw response
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Fetched {len(data['data'])} records from FDA API")
    return data["data"]


def load_or_fetch():
    """Load from file if exists and has data, otherwise fetch"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        if data.get("data") and len(data["data"]) > 0:
            print(f"Loaded {len(data['data'])} records from {DATA_FILE}")
            return data["data"]

    print(f"{DATA_FILE} empty or missing — fetching from FDA...")
    return fetch_recall_list()


def load_processed_records():
    """Reuse fully processed FDA records when available."""
    if os.path.exists(PROCESSED_DATA_FILE):
        with open(PROCESSED_DATA_FILE, "r") as f:
            data = json.load(f)
        if data and len(data) > 0:
            print(f"Loaded {len(data)} processed FDA records from {PROCESSED_DATA_FILE}")
            return data
    return None


def parse_list_record(record):
    """Parse a single record from the list API response"""
    soup = BeautifulSoup(record[1], "html.parser")
    link = soup.find("a")
    brand_name = link.get_text(strip=True) if link else ""
    detail_url = BASE_URL + link["href"] if link else ""

    product_description = BeautifulSoup(record[2], "html.parser").get_text(strip=True)

    raw_type = BeautifulSoup(record[3], "html.parser").get_text(strip=True)
    product_type = [t.strip() for t in raw_type.replace("&amp;", "&").split(",") if t.strip()]

    recall_reason = BeautifulSoup(record[4], "html.parser").get_text(strip=True)
    company_name = BeautifulSoup(record[5], "html.parser").get_text(strip=True)

    terminated_text = BeautifulSoup(record[6], "html.parser").get_text(strip=True)
    is_terminated = "terminated" in terminated_text.lower() if terminated_text else False

    return {
        "brand_name": brand_name,
        "product_description": product_description,
        "product_type": product_type,
        "recall_reason": recall_reason,
        "company_name": company_name,
        "is_terminated": is_terminated,
        "detail_url": detail_url,
    }


def parse_detail_page(url):
    """Scrape a single recall detail page"""
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    detail = {}

    title_tag = soup.find("h1", class_="content-title")
    detail["announcement_title"] = title_tag.get_text(strip=True) if title_tag else None
    detail["source"] = "FDA"

    # --- SUMMARY SECTION ---
    summary = soup.find("dl", class_="lcds-description-list--grid")
    if summary:
        date_dd = summary.find("dd", class_="cell-2_1")
        if date_dd:
            time_tag = date_dd.find("time")
            detail["company_announcement_date"] = time_tag["datetime"] if time_tag else None

        fda_dd = summary.find("dd", class_="cell-2_2")
        if fda_dd:
            time_tag = fda_dd.find("time")
            detail["fda_publish_date"] = time_tag["datetime"] if time_tag else None

        type_dd = summary.find("dd", class_="cell-2_3")
        if type_dd:
            raw_text = type_dd.get_text(separator="|", strip=True)
            detail["product_type"] = [t.strip() for t in raw_text.split("|") if t.strip()]

        reason_dd = summary.find("dd", class_="cell-2_4")
        if reason_dd:
            item = reason_dd.find("div", class_="field--item")
            detail["recall_reason"] = item.get_text(strip=True) if item else None

        company_dd = summary.find("dd", class_="cell-2_5")
        if company_dd:
            detail["company_name"] = company_dd.get_text(strip=True)

        brand_dd = summary.find("dd", class_="cell-2_6")
        if brand_dd:
            item = brand_dd.find("div", class_="field--item")
            detail["brand_name"] = item.get_text(strip=True) if item else None

        desc_dd = summary.find("dd", class_="cell-2_7")
        if desc_dd:
            item = desc_dd.find("div", class_="field--item")
            detail["product_description"] = item.get_text(strip=True) if item else None

    # --- COMPANY ANNOUNCEMENT ---
    announcement_heading = soup.find("h2", id="recall-announcement")
    if announcement_heading:
        content = []
        for sibling in announcement_heading.find_next_siblings():
            if sibling.name == "div" and "inset-column" in sibling.get("class", []):
                break
            if sibling.name == "hr":
                break
            content.append(sibling)

        detail["announcement_html"] = "".join(str(c) for c in content)
        detail["announcement_text"] = " ".join(
            c.get_text(separator=" ", strip=True) for c in content
        )

        # --- ANNOUNCEMENT TABLES ---
        tables = []
        for c in content:
            if hasattr(c, "find_all"):
                for table in c.find_all("table"):
                    headers = [th.get_text(strip=True) for th in table.find_all("th")]
                    for row in table.find_all("tr"):
                        cells = [td.get_text(strip=True) for td in row.find_all("td")]
                        if cells and len(cells) == len(headers):
                            tables.append(dict(zip(headers, cells)))

        detail["product_details"] = tables if tables else None

    # --- PRODUCT PHOTOS ---
    photos_div = soup.find("div", id="recall-photos")
    photo_urls = []
    if photos_div:
        for img in photos_div.find_all("img"):
            src = img.get("src", "")
            if src:
                full_url = BASE_URL + src if src.startswith("/") else src
                photo_urls.append(full_url)

    detail["photo_urls"] = photo_urls

    return detail


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    processed_records = load_processed_records()
    if processed_records is not None:
        print("Skipping FDA re-scrape because processed recall data already exists.")
        raise SystemExit(0)

    records = load_or_fetch()

    # Only process first 3 for testing
    results = []
    for i, record in enumerate(records):
        print(f"\nProcessing record {i + 1}/{len(records)}...")

        try:
            list_data = parse_list_record(record)
            print(f"  → {list_data['brand_name']} - {list_data['product_description']}")

            detail_data = parse_detail_page(list_data["detail_url"])

            merged = {**list_data, **detail_data}
            results.append(merged)
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({"error": str(e), "raw_record": record})

        time.sleep(1)

    output_path = PROCESSED_DATA_FILE
    with open(output_path, "w") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"\nDone! Saved {len(results)} records to {output_path}")
