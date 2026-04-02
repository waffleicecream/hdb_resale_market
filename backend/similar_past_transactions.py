"""
similar_past_transactions.py — Find comparable 2025 HDB resale transactions near a postal code.

Given a postal code, this script:
  1. Looks up the lat/lon from the geocode cache (data/geocode_cache.json)
  2. Loads 2025 transactions from the final amenities-enriched dataset
  3. Filters to transactions within RADIUS_M metres of the input location
  4. Optionally filters by flat type and floor category (Low / Mid / High)
  5. Saves the results to outputs/similar_past_transactions.csv

Usage:
    python backend/similar_past_transactions.py

Edit the USER INPUTS section below before running.
"""

import json
import math
import os

import numpy as np
import pandas as pd

# =============================================================================
# USER INPUTS — edit these before running
# =============================================================================
POSTAL_CODE    = "520123"   # 6-digit Singapore postal code
FLAT_TYPE      = "4 ROOM"   # None to include all flat types
                             # Options: "2 ROOM" | "3 ROOM" | "4 ROOM" | "5 ROOM" | "EXECUTIVE"
FLOOR_CATEGORY = "Mid"      # None to include all floor categories
                             # Options: "Low" (floors 1–5) | "Mid" (6–12) | "High" (13+)
RADIUS_M       = 200        # Search radius in metres

# =============================================================================
# PATHS
# =============================================================================
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR     = os.path.join(BASE_DIR, "data")
MERGED_DIR   = os.path.join(BASE_DIR, "merged_data")
OUTPUTS_DIR  = os.path.join(BASE_DIR, "outputs")
SOURCE_PATH  = os.path.join(MERGED_DIR, "[FINAL]hdb_with_amenities_macro_pre2026.csv")
DATASET_PATH = os.path.join(MERGED_DIR, "[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv")
CACHE_PATH   = os.path.join(DATA_DIR, "geocode_cache.json")
OUTPUT_PATH  = os.path.join(OUTPUTS_DIR, "similar_past_transactions.csv")


# =============================================================================
# HELPERS
# =============================================================================

def haversine_m(lat1: float, lon1: float, lat2_arr, lon2_arr) -> np.ndarray:
    """Vectorised haversine distance in metres from a single point to an array of points."""
    R = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = np.radians(lat2_arr)
    dphi = np.radians(np.asarray(lat2_arr) - lat1)
    dlambda = np.radians(np.asarray(lon2_arr) - lon1)
    a = np.sin(dphi / 2) ** 2 + math.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def geocode_from_cache(postal_code: str, cache_path: str) -> tuple[float, float]:
    """
    Look up a 6-digit postal code in the geocode cache and return (lat, lon).
    Raises ValueError if the postal code is not found.
    """
    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)

    # Build reverse lookup: postal -> (lat, lon)
    for entry in cache.values():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("postal", "")).strip() == postal_code.strip():
            return float(entry["lat"]), float(entry["lon"])

    raise ValueError(
        f"Postal code '{postal_code}' was not found in the geocode cache "
        f"({cache_path}).\n"
        "Only postal codes corresponding to HDB blocks already geocoded by "
        "the pipeline (2_train_pipeline.ipynb) are supported. "
        "Check that the postal code is correct, or use a nearby block's postal code."
    )


# =============================================================================
# MAIN
# =============================================================================

def main():
    # ------------------------------------------------------------------
    # Step 1: Geocode the input postal code
    # ------------------------------------------------------------------
    print(f"Looking up postal code {POSTAL_CODE} in geocode cache...")
    input_lat, input_lon = geocode_from_cache(POSTAL_CODE, CACHE_PATH)
    print(f"  lat={input_lat:.6f}, lon={input_lon:.6f}")

    # ------------------------------------------------------------------
    # Step 2: Load 2025 dataset (create cached copy on first run)
    # ------------------------------------------------------------------
    if os.path.exists(DATASET_PATH):
        print(f"\nLoading cached 2025 dataset from {DATASET_PATH}...")
        df_2025 = pd.read_csv(DATASET_PATH, low_memory=False)
    else:
        print(f"\nCached dataset not found. Filtering from source: {SOURCE_PATH}...")
        df = pd.read_csv(SOURCE_PATH, low_memory=False)
        df_2025 = df[df["year"] == 2025].dropna(subset=["lat", "lon"]).copy()
        df_2025.to_csv(DATASET_PATH, index=False)
        print(f"  Saved to {DATASET_PATH}")
    print(f"  {len(df_2025):,} 2025 transactions loaded")

    # ------------------------------------------------------------------
    # Step 3: Compute distances and filter by radius
    # ------------------------------------------------------------------
    df_2025["dist_from_input_m"] = haversine_m(
        input_lat, input_lon,
        df_2025["lat"].values,
        df_2025["lon"].values,
    ).round(1)

    nearby = df_2025[df_2025["dist_from_input_m"] <= RADIUS_M].copy()
    print(f"\nTransactions within {RADIUS_M}m: {len(nearby):,}")

    if nearby.empty:
        print(
            f"\nNo transactions found within {RADIUS_M}m of postal code {POSTAL_CODE}.\n"
            "Try increasing RADIUS_M."
        )
        return pd.DataFrame()

    # ------------------------------------------------------------------
    # Step 4: Apply optional filters
    # ------------------------------------------------------------------
    if FLAT_TYPE is not None:
        nearby = nearby[nearby["flat_type"] == FLAT_TYPE.upper()]
        print(f"After flat_type filter ({FLAT_TYPE.upper()}): {len(nearby):,}")

    if FLOOR_CATEGORY is not None:
        nearby = nearby[nearby["floor_category"] == FLOOR_CATEGORY.capitalize()]
        print(f"After floor_category filter ({FLOOR_CATEGORY.capitalize()}): {len(nearby):,}")

    if nearby.empty:
        print("\nNo transactions matched the specified filters.")
        return pd.DataFrame()

    # ------------------------------------------------------------------
    # Step 5: Sort and save
    # ------------------------------------------------------------------
    nearby = nearby.sort_values(["dist_from_input_m", "resale_price"]).reset_index(drop=True)

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    nearby.to_csv(OUTPUT_PATH, index=False)

    prices = nearby["resale_price"]
    print(f"\nMatches : {len(nearby)}")
    print(f"Median  : S${prices.median():,.0f}")
    print(f"Range   : S${prices.min():,.0f} - S${prices.max():,.0f}")
    print(f"Saved   : {OUTPUT_PATH}")

    return nearby


if __name__ == "__main__":
    main()
