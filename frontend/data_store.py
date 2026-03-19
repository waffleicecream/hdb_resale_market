"""
data_store.py — loads the HDB dataset once and exposes shared variables.
Both app.py and pages/ import from here to avoid circular imports.
"""

import os
import re
import pandas as pd

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "..", "merged_data")


def load_data():
    """Load the richest available merged dataset."""
    for fname in [
        "hdb_with_amenities_macro.csv",
        "hdb_with_mrt_distances.csv",
        "merged_hdb_resale_with_macro.csv",
    ]:
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            print(f"  Loading: {fname}")
            df = pd.read_csv(path, parse_dates=["month"], low_memory=False)
            break
    else:
        raise FileNotFoundError(
            f"No merged HDB CSV found in {DATA_DIR}. "
            "Run the backend notebooks first."
        )

    df["year"] = df["month"].dt.year
    df["flat_type"] = df["flat_type"].str.upper().str.strip()

    # Numeric floor midpoint from storey_range e.g. "10 TO 12" → 11.0
    if "storey_range" in df.columns:
        extracted = df["storey_range"].str.extract(r"(\d+)\s+TO\s+(\d+)", expand=True)
        df["floor_level"] = extracted.astype(float).mean(axis=1)

    # Numeric remaining lease years e.g. "58 years 09 months" → 58.75
    if "remaining_lease" in df.columns:
        def _parse_lease(s):
            if pd.isna(s):
                return None
            yr = re.search(r"(\d+)\s*year", str(s), re.I)
            mo = re.search(r"(\d+)\s*month", str(s), re.I)
            y = int(yr.group(1)) if yr else 0
            m = int(mo.group(1)) if mo else 0
            total = y + m / 12
            return round(total, 2) if total > 0 else None
        df["remaining_lease_yrs"] = df["remaining_lease"].apply(_parse_lease)

    return df


print("Loading HDB data …")
DF = load_data()
print(f"  {len(DF):,} rows | years {DF['year'].min()}–{DF['year'].max()}")

FLAT_TYPES = sorted(DF["flat_type"].dropna().unique().tolist())
TOWNS      = sorted(DF["town"].dropna().unique().tolist())
YEAR_MIN   = int(DF["year"].min())
YEAR_MAX   = int(DF["year"].max())
