"""
preprocess_amenities.py

Builds outputs/amenities_by_postal.csv — a lookup table keyed by postal code
containing the latest known amenity data for each unique HDB block.

Processing order:
  1. [FINAL]hdb_with_amenities_macro_2026.csv  (latest, takes priority)
  2. [FINAL]hdb_with_amenities_macro_pre2026.csv (fills gaps for postal codes
     not covered by 2026 data)

Within each file, rows are processed latest-first (by month) so only the most
recent amenity snapshot is retained per postal code.

Postal codes are resolved via data/geocode_cache.json whose keys are
"BLOCK STREET_NAME" (uppercase) and values contain a "postal" field.

Run:
    python frontend/preprocess_amenities.py
"""

import json
import os
import pandas as pd

# ---------------------------------------------------------------------------
# Paths (relative to project root)
# ---------------------------------------------------------------------------
GEOCODE_CACHE   = "data/geocode_cache.json"
FILE_2026       = "merged_data/[FINAL]hdb_with_amenities_macro_2026.csv"
FILE_PRE2026    = "merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv"
OUTPUT_PATH     = "outputs/amenities_by_postal.csv"

AMENITY_COLS = [
    "nearest_train_line", "nearest_train_dist_m", "nearest_train_name",
    "dist_nearest_hawker_m", "nearest_hawker_name",
    "dist_cbd_m",
    "dist_nearest_primary_m", "primary_schools_1km", "num_primary_1km",
    "dist_nearest_park_m", "parks_1km", "num_parks_1km",
    "dist_nearest_sportsg_m", "nearest_sportsg_name",
    "dist_nearest_mall_m", "nearest_mall_name",
    "dist_nearest_healthcare_m", "nearest_healthcare_name",
]

# ---------------------------------------------------------------------------
# Build postal lookup from geocode cache
# ---------------------------------------------------------------------------
print("Loading geocode cache...")
with open(GEOCODE_CACHE, "r") as f:
    geocode_cache = json.load(f)

# key: "BLOCK STREET_NAME" (uppercase) → postal code string
block_street_to_postal = {
    k: v["postal"]
    for k, v in geocode_cache.items()
    if v and v.get("postal")
}
print(f"  {len(block_street_to_postal):,} entries in geocode cache")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def process_file(path: str) -> pd.DataFrame:
    label = os.path.basename(path)
    print(f"\nProcessing {label}...")
    df = pd.read_csv(path, low_memory=False)
    print(f"  {len(df):,} rows loaded")

    # Resolve postal code via geocode cache
    lookup_key = (df["block"].astype(str) + " " + df["street_name"].astype(str)).str.upper()
    df["postal_code"] = lookup_key.map(block_street_to_postal)

    no_postal = df["postal_code"].isna().sum()
    if no_postal:
        print(f"  WARNING: {no_postal:,} rows could not be matched to a postal code — skipped")

    df = df.dropna(subset=["postal_code"])

    # Combined address column
    df["address"] = df["block"].astype(str) + " " + df["street_name"].astype(str)

    # Sort latest-first, keep first occurrence per postal code
    df["month"] = pd.to_datetime(df["month"])
    df = df.sort_values("month", ascending=False)
    df = df.drop_duplicates(subset=["postal_code"], keep="first")

    n_unique = len(df)
    print(f"  {n_unique:,} unique postal codes retained")

    keep = ["postal_code", "address", "town", "lat", "lon", "month"] + AMENITY_COLS
    return df[keep].rename(columns={"month": "source_month"})


# ---------------------------------------------------------------------------
# Process both files
# ---------------------------------------------------------------------------
df_2026    = process_file(FILE_2026)
df_pre2026 = process_file(FILE_PRE2026)

# Fill gaps: pre2026 rows whose postal code is not already in df_2026
covered = set(df_2026["postal_code"])
df_fill  = df_pre2026[~df_pre2026["postal_code"].isin(covered)]
print(f"\n{len(df_fill):,} additional postal codes filled from pre-2026 data")

# ---------------------------------------------------------------------------
# Combine and save
# ---------------------------------------------------------------------------
combined = (
    pd.concat([df_2026, df_fill], ignore_index=True)
    .sort_values("postal_code")
    .reset_index(drop=True)
)

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
combined.to_csv(OUTPUT_PATH, index=False)

print(f"\nDone. {len(combined):,} postal codes saved to {OUTPUT_PATH}")
print(f"  From 2026 data:     {len(df_2026):,}")
print(f"  From pre-2026 data: {len(df_fill):,}")
