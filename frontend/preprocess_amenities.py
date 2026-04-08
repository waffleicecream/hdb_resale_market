"""
preprocess_amenities.py
-----------------------
Enrich outputs/unique_addresses.csv with amenity features for every unique
HDB address (block + street_name).

Run from project root:
    python frontend/preprocess_amenities.py

Outputs:
    outputs/unique_addresses.csv  (overwrites existing file)
"""

import json
import os
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
MERGED = os.path.join(ROOT, "merged_data")
OUTPUTS = os.path.join(ROOT, "outputs")

FINAL_2026 = os.path.join(MERGED, "[FINAL]hdb_with_amenities_macro_2026.csv")
FINAL_PRE2026 = os.path.join(MERGED, "[FINAL]hdb_with_amenities_macro_pre2026.csv")
UNIQUE_ADDR = os.path.join(OUTPUTS, "unique_addresses.csv")

# Reference date for hawker centre open/closed check
REFERENCE_DATE = pd.Timestamp("2026-04-07")

# ---------------------------------------------------------------------------
# Haversine helpers
# ---------------------------------------------------------------------------
R_EARTH = 6_371_000.0  # metres


def nearest_with_name_vectorized(lats_arr, lons_arr, facility_coords, facility_names=None):
    """
    Return (distances, names) arrays (shape N) for the nearest facility.

    Parameters
    ----------
    lats_arr, lons_arr : 1-D float arrays (N,)
    facility_coords    : 2-D float array (F, 2) — [lat, lon]
    facility_names     : sequence of length F, or None

    Returns
    -------
    distances  : (N,) float array — NaN where lat/lon is NaN
    names_out  : (N,) object array — None where distance is NaN
    """
    n = len(lats_arr)
    distances = np.full(n, np.nan)
    names_out = np.full(n, None, dtype=object)

    if len(facility_coords) == 0:
        return distances, names_out

    valid = ~(np.isnan(lats_arr) | np.isnan(lons_arr))
    if not valid.any():
        return distances, names_out

    lat1 = np.radians(lats_arr[valid])[:, np.newaxis]
    lon1 = np.radians(lons_arr[valid])[:, np.newaxis]
    lat2 = np.radians(facility_coords[:, 0])[np.newaxis, :]
    lon2 = np.radians(facility_coords[:, 1])[np.newaxis, :]

    a = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    )
    dist_m = R_EARTH * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))  # (N_v, F)

    min_idx = np.argmin(dist_m, axis=1)
    nv = valid.sum()
    distances[valid] = np.round(dist_m[np.arange(nv), min_idx], 1)

    if facility_names is not None:
        names_arr = np.asarray(facility_names)
        names_out[valid] = names_arr[min_idx]

    return distances, names_out


def within_radius_list(lats_arr, lons_arr, facility_coords, facility_names, radius_m=1000):
    """
    Return (pipe_str_array, count_array) for all facilities within radius_m.

    pipe_str_array : (N,) object — pipe-separated names, '0' if none
    count_array    : (N,) int
    """
    n = len(lats_arr)
    result_names = np.full(n, "0", dtype=object)
    result_counts = np.zeros(n, dtype=int)

    if len(facility_coords) == 0:
        return result_names, result_counts

    valid = ~(np.isnan(lats_arr) | np.isnan(lons_arr))
    if not valid.any():
        return result_names, result_counts

    lat1 = np.radians(lats_arr[valid])[:, np.newaxis]
    lon1 = np.radians(lons_arr[valid])[:, np.newaxis]
    lat2 = np.radians(facility_coords[:, 0])[np.newaxis, :]
    lon2 = np.radians(facility_coords[:, 1])[np.newaxis, :]

    a = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    )
    dist_m = R_EARTH * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))  # (N_v, F)

    names_arr = np.asarray(facility_names)
    valid_indices = np.where(valid)[0]
    for i, vi in enumerate(valid_indices):
        within = dist_m[i] <= radius_m
        if within.any():
            result_names[vi] = "|".join(names_arr[within])
            result_counts[vi] = int(within.sum())

    return result_names, result_counts


# ---------------------------------------------------------------------------
# Step 1 — Load unique_addresses and add lat/lon + train cols from FINAL CSVs
# ---------------------------------------------------------------------------
print("Loading unique_addresses.csv...")
addr = pd.read_csv(UNIQUE_ADDR)

# Drop any columns that will be re-computed, so re-runs don't create _x/_y suffixes
_RECOMPUTE_COLS = [
    "lat", "lon",
    "nearest_train_line", "nearest_train_dist_m", "nearest_train_name",
    "dist_cbd_m",
    "dist_nearest_hawker_m", "nearest_hawker_name",
    "dist_nearest_primary_m", "primary_schools_1km", "num_primary_1km",
    "dist_nearest_park_m", "parks_1km", "num_parks_1km",
    "dist_nearest_sportsg_m", "nearest_sportsg_name",
    "dist_nearest_mall_m", "nearest_mall_name",
    "dist_nearest_healthcare_m", "nearest_healthcare_name",
]
addr = addr.drop(columns=[c for c in _RECOMPUTE_COLS if c in addr.columns])

print("Loading FINAL CSVs for lat/lon and train data...")
train_cols = ["block", "street_name", "lat", "lon",
              "nearest_train_line", "nearest_train_dist_m", "nearest_train_name"]
df1 = pd.read_csv(FINAL_2026, usecols=train_cols)
df2 = pd.read_csv(FINAL_PRE2026, usecols=train_cols)
coords_df = (
    pd.concat([df1, df2], ignore_index=True)
    .drop_duplicates(subset=["block", "street_name"])
    .reset_index(drop=True)
)

# Merge on upper-cased keys to handle casing differences between CSVs
addr["_bk"] = addr["block"].astype(str).str.upper().str.strip()
addr["_st"] = addr["street_name"].astype(str).str.upper().str.strip()
coords_df["_bk"] = coords_df["block"].astype(str).str.upper().str.strip()
coords_df["_st"] = coords_df["street_name"].astype(str).str.upper().str.strip()
addr = addr.merge(
    coords_df.drop(columns=["block", "street_name"]),
    on=["_bk", "_st"], how="left"
).drop(columns=["_bk", "_st"])
lats = addr["lat"].values.astype(float)
lons = addr["lon"].values.astype(float)
print(f"  Addresses with valid lat/lon: {(~np.isnan(lats)).sum()} / {len(addr)}")

# ---------------------------------------------------------------------------
# Step 1b — CBD Distance (Raffles Place MRT proxy)
# ---------------------------------------------------------------------------
CBD_LAT = 1.2830
CBD_LON = 103.8513

cbd_coords = np.array([[CBD_LAT, CBD_LON]])
dist_cbd, _ = nearest_with_name_vectorized(lats, lons, cbd_coords)
addr["dist_cbd_m"] = dist_cbd
print(f"  CBD distances computed (non-null: {(~np.isnan(dist_cbd)).sum()})")

# ---------------------------------------------------------------------------
# Step 2 — Hawker Centres
# ---------------------------------------------------------------------------
print("Processing hawker centres...")

def is_hawker_open(status, est_dt, ref_date):
    if status == "Under Construction":
        return False
    if status in ("Existing", "Existing (replacement)"):
        return True
    if pd.isna(est_dt):
        return True  # parse failure — safe fallback
    return ref_date >= est_dt


with open(os.path.join(DATA, "HawkerCentresGEOJSON.geojson")) as f:
    hawker_geojson = json.load(f)

hawker_rows = []
for feat in hawker_geojson["features"]:
    props = feat["properties"]
    coords = feat["geometry"]["coordinates"]  # [lon, lat]
    name = props.get("NAME", "")
    status = props.get("STATUS", "")
    raw_date = props.get("EST_ORIGINAL_COMPLETION_DATE", "")
    try:
        est_dt = pd.to_datetime(raw_date, dayfirst=True)
    except Exception:
        est_dt = pd.NaT
    hawker_rows.append({
        "name": name,
        "status": status,
        "est_dt": est_dt,
        "lat": coords[1],
        "lon": coords[0],
    })

hawker_df = pd.DataFrame(hawker_rows)
open_hawkers = hawker_df[
    hawker_df.apply(lambda r: is_hawker_open(r["status"], r["est_dt"], REFERENCE_DATE), axis=1)
].reset_index(drop=True)
print(f"  Open hawker centres: {len(open_hawkers)} / {len(hawker_df)}")

hawker_coords = open_hawkers[["lat", "lon"]].values
hawker_names = open_hawkers["name"].tolist()

dist_hawker, name_hawker = nearest_with_name_vectorized(lats, lons, hawker_coords, hawker_names)
addr["dist_nearest_hawker_m"] = dist_hawker
addr["nearest_hawker_name"] = name_hawker

# ---------------------------------------------------------------------------
# Step 3 — MRT/LRT (already joined from FINAL CSVs in Step 1)
# ---------------------------------------------------------------------------
# nearest_train_line, nearest_train_dist_m, nearest_train_name already in addr
print("Train station columns carried over from FINAL CSVs.")

# ---------------------------------------------------------------------------
# Step 4 — Primary Schools
# ---------------------------------------------------------------------------
print("Processing primary schools...")

schools_raw = pd.read_csv(os.path.join(DATA, "Generalinformationofschools.csv"))
primary = schools_raw[schools_raw["mainlevel_code"] == "PRIMARY"][
    ["school_name", "postal_code"]
].copy()
primary["postal_code"] = primary["postal_code"].astype(str).str.strip()

with open(os.path.join(DATA, "school_geocode_cache.json")) as f:
    school_cache = json.load(f)

school_rows = []
for _, row in primary.iterrows():
    pc = row["postal_code"]
    entry = school_cache.get(pc)
    if entry and entry.get("lat") and entry.get("lon"):
        school_rows.append({
            "name": row["school_name"],
            "lat": float(entry["lat"]),
            "lon": float(entry["lon"]),
        })

school_df = pd.DataFrame(school_rows)
print(f"  Geocoded primary schools: {len(school_df)} / {len(primary)}")

school_coords = school_df[["lat", "lon"]].values
school_names = school_df["name"].tolist()

dist_primary, _ = nearest_with_name_vectorized(lats, lons, school_coords)
schools_list, schools_count = within_radius_list(lats, lons, school_coords, school_names)

addr["dist_nearest_primary_m"] = dist_primary
addr["primary_schools_1km"] = schools_list
addr["num_primary_1km"] = schools_count

# ---------------------------------------------------------------------------
# Step 5 — Parks
# ---------------------------------------------------------------------------
print("Processing parks...")

with open(os.path.join(DATA, "Parks.geojson")) as f:
    parks_geojson = json.load(f)

PARK_EXCLUDE_SUFFIXES = ("PLAYGROUND", "TERMINAL", "NURSERY", "STATELAND", "LINKWAY")
PARK_EXCLUDE_CONTAINS = ("CAR PARK", "FOOTBALL FIELD", "SPORTSG")

park_rows = []
for feat in parks_geojson["features"]:
    props = feat.get("properties", {})
    name = (props.get("NAME") or "").strip()
    name_up = name.upper()

    # Apply exclusion filters
    if any(name_up.endswith(s) for s in PARK_EXCLUDE_SUFFIXES):
        continue
    if any(s in name_up for s in PARK_EXCLUDE_CONTAINS):
        continue
    if name_up.endswith(" PG"):
        continue
    if " PG " in name_up:
        continue

    coords = feat["geometry"]["coordinates"]  # [lon, lat]
    park_rows.append({"name": name, "lat": coords[1], "lon": coords[0]})

park_df = pd.DataFrame(park_rows)
print(f"  Parks after filtering: {len(park_df)} (from {len(parks_geojson['features'])})")

park_coords = park_df[["lat", "lon"]].values
park_names = park_df["name"].tolist()

dist_park, _ = nearest_with_name_vectorized(lats, lons, park_coords)
parks_list, parks_count = within_radius_list(lats, lons, park_coords, park_names)

addr["dist_nearest_park_m"] = dist_park
addr["parks_1km"] = parks_list
addr["num_parks_1km"] = parks_count

# ---------------------------------------------------------------------------
# Step 6 — SportSG Facilities
# ---------------------------------------------------------------------------
print("Processing SportSG facilities...")

with open(os.path.join(DATA, "SportSGSportFacilitiesGEOJSON.geojson")) as f:
    sportsg_geojson = json.load(f)

sportsg_rows = []
for feat in sportsg_geojson["features"]:
    props = feat["properties"]
    coords = feat["geometry"]["coordinates"]  # [lon, lat]
    sportsg_rows.append({
        "name": props.get("VENUE", ""),
        "lat": coords[1],
        "lon": coords[0],
    })

sportsg_df = pd.DataFrame(sportsg_rows)
print(f"  SportSG facilities: {len(sportsg_df)}")

sportsg_coords = sportsg_df[["lat", "lon"]].values
sportsg_names = sportsg_df["name"].tolist()

dist_sportsg, name_sportsg = nearest_with_name_vectorized(lats, lons, sportsg_coords, sportsg_names)
addr["dist_nearest_sportsg_m"] = dist_sportsg
addr["nearest_sportsg_name"] = name_sportsg

# ---------------------------------------------------------------------------
# Step 7 — Shopping Malls
# ---------------------------------------------------------------------------
print("Processing shopping malls...")

malls_raw = pd.read_csv(os.path.join(DATA, "shoppingmalls.csv"))
malls_df = (
    malls_raw.groupby("name", as_index=False)
    .agg(lat=("lat", "mean"), lon=("lon", "mean"))
)
print(f"  Unique malls: {len(malls_df)} (from {len(malls_raw)} rows)")

mall_coords = malls_df[["lat", "lon"]].values
mall_names = malls_df["name"].tolist()

dist_mall, name_mall = nearest_with_name_vectorized(lats, lons, mall_coords, mall_names)
addr["dist_nearest_mall_m"] = dist_mall
addr["nearest_mall_name"] = name_mall

# ---------------------------------------------------------------------------
# Step 8 — Healthcare (Polyclinics & Hospitals)
# ---------------------------------------------------------------------------
print("Processing healthcare facilities...")

hc_raw = pd.read_csv(os.path.join(DATA, "healthcare_address.csv"))
hc_raw["postal_code"] = hc_raw["postal_code"].astype(str).str.strip()

with open(os.path.join(DATA, "healthcare_geocode_cache.json")) as f:
    hc_cache = json.load(f)

hc_rows = []
for _, row in hc_raw.iterrows():
    pc = row["postal_code"]
    entry = hc_cache.get(pc)
    if entry and entry.get("lat") and entry.get("lon"):
        hc_rows.append({
            "name": row["institution"],
            "lat": float(entry["lat"]),
            "lon": float(entry["lon"]),
        })

hc_df = pd.DataFrame(hc_rows)
print(f"  Geocoded healthcare facilities: {len(hc_df)} / {len(hc_raw)}")

hc_coords = hc_df[["lat", "lon"]].values
hc_names = hc_df["name"].tolist()

dist_hc, name_hc = nearest_with_name_vectorized(lats, lons, hc_coords, hc_names)
addr["dist_nearest_healthcare_m"] = dist_hc
addr["nearest_healthcare_name"] = name_hc

# ---------------------------------------------------------------------------
# Step 9 — Save
# ---------------------------------------------------------------------------
col_order = [
    "town", "block", "street_name", "lease_commence_date", "lat", "lon",
    "nearest_train_line", "nearest_train_dist_m", "nearest_train_name",
    "dist_nearest_hawker_m", "nearest_hawker_name",
    "dist_cbd_m",
    "dist_nearest_primary_m", "primary_schools_1km", "num_primary_1km",
    "dist_nearest_park_m", "parks_1km", "num_parks_1km",
    "dist_nearest_sportsg_m", "nearest_sportsg_name",
    "dist_nearest_mall_m", "nearest_mall_name",
    "dist_nearest_healthcare_m", "nearest_healthcare_name",
]
addr = addr[col_order]
addr.to_csv(UNIQUE_ADDR, index=False)
print(f"\nDone. Saved {len(addr)} rows to outputs/unique_addresses.csv")
print(f"Columns: {list(addr.columns)}")
