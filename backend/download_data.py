"""
download_data.py — Fetch raw data files from data.gov.sg

Run this once before executing the pipeline notebooks:
    python backend/download_data.py

Files are saved to ../data/ and skipped if they already exist.
"""

import sys
import time
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent.parent / "data"

DATASETS = [
    {
        "id": "d_8b84c4ee58e3cfc0ece0d773c8ca6abc",
        "filename": "ResaleflatpricesbasedonregistrationdatefromJan2017onwards.csv",
        "description": "HDB resale transactions (Jan 2017 onwards)",
    },
    {
        "id": "d_14f63e595975691e7c24a27ae4c07c79",
        "filename": "HDBResalePriceIndex1Q2009100Quarterly.csv",
        "description": "HDB Resale Price Index (quarterly, base 2009-Q1=100)",
    },
    {
        "id": "d_4a086da0a5553be1d89383cd90d07ecd",
        "filename": "HawkerCentresGEOJSON.geojson",
        "description": "Hawker centre locations (GeoJSON)",
    },
    {
        "id": "d_0542d48f0991541706b58059381a6eca",
        "filename": "Parks.geojson",
        "description": "NParks managed green spaces (GeoJSON)",
    },
    {
        "id": "d_9b87bab59d036a60fad2a91530e10773",
        "filename": "SportSGSportFacilitiesGEOJSON.geojson",
        "description": "SportSG sport facilities (GeoJSON)",
    },
    {
        "id": "d_688b934f82c1059ed0a6993d2a829089",
        "filename": "Generalinformationofschools.csv",
        "description": "MOE general information of schools",
    },
]

POLL_URL = "https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"


def download_dataset(dataset_id: str, filename: str, description: str) -> bool:
    dest = DATA_DIR / filename
    if dest.exists():
        size_mb = dest.stat().st_size / 1_048_576
        print(f"  [skip] {filename} already exists ({size_mb:.1f} MB)")
        return True

    print(f"  Fetching URL for: {description}")
    url = POLL_URL.format(dataset_id=dataset_id)

    for attempt in range(5):
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        json_data = response.json()

        if json_data.get("code") != 0:
            raise RuntimeError(f"API error for {filename}: {json_data.get('errMsg')}")

        download_url = json_data.get("data", {}).get("url")
        if download_url:
            break
        print(f"  Waiting for download URL (attempt {attempt + 1})...")
        time.sleep(3)
    else:
        raise RuntimeError(f"Download URL not available after retries for {filename}")

    print(f"  Downloading {filename}...")
    with requests.get(download_url, stream=True, timeout=120) as r:
        r.raise_for_status()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)

    size_mb = dest.stat().st_size / 1_048_576
    print(f"  [done]  {filename} ({size_mb:.1f} MB)")
    return True


def main():
    print(f"Saving files to: {DATA_DIR.resolve()}\n")
    errors = []
    for ds in DATASETS:
        try:
            download_dataset(ds["id"], ds["filename"], ds["description"])
        except Exception as e:
            print(f"  [ERROR] {ds['filename']}: {e}")
            errors.append(ds["filename"])

    print()
    if errors:
        print(f"Failed: {', '.join(errors)}")
        sys.exit(1)
    else:
        print("All files ready.")


if __name__ == "__main__":
    main()
