"""
Enrich the 191 blocks in hdb_2026_enriched.csv that are missing amenity data.

For blocks with lat/lon already: compute amenities directly.
For blocks without lat/lon: geocode via OneMap first, then compute.

Output: appends new rows to [PAST_TRANSACTIONS]hdb_with_amenities_macro.csv
and updates data/geocode_cache.json and data/train_cache.json.
"""

import json
import os
import re
import time
import requests
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT      = os.path.dirname(os.path.dirname(__file__))
DATA      = os.path.join(ROOT, "data")
MERGED    = os.path.join(ROOT, "merged_data")

AMENITY_CSV  = os.path.join(MERGED, "[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv")
POSTAL_CSV   = os.path.join(DATA,   "hdb_2026_enriched.csv")
MALLS_CSV    = os.path.join(DATA,   "shoppingmalls.csv")
HEALTHCARE_CSV = os.path.join(DATA, "healthcare_address.csv")

GEO_CACHE_PATH       = os.path.join(DATA, "geocode_cache.json")
TRAIN_CACHE_PATH     = os.path.join(DATA, "train_cache.json")
SCHOOL_CACHE_PATH    = os.path.join(DATA, "school_geocode_cache.json")
HEALTHCARE_CACHE_PATH= os.path.join(DATA, "healthcare_geocode_cache.json")

MRT_LOCS_PATH     = os.path.join(DATA, "mrt_approx_locs.json")
HAWKER_LOCS_PATH  = os.path.join(DATA, "hawker_approx_locs.json")
SCHOOL_LOCS_PATH  = os.path.join(DATA, "school_name_locs.json")
PARK_LOCS_PATH    = os.path.join(DATA, "park_approx_locs.json")
SPORTSG_LOCS_PATH = os.path.join(DATA, "sportsg_approx_locs.json")

load_dotenv(os.path.join(ROOT, ".env"))

# ── OneMap auth ────────────────────────────────────────────────────────────────
_token     = None
_token_exp = 0

def get_token():
    global _token, _token_exp
    if _token and time.time() < _token_exp - 60:
        return _token
    r = requests.post(
        "https://www.onemap.gov.sg/api/auth/post/getToken",
        json={"email": os.getenv("ONEMAP_EMAIL"), "password": os.getenv("ONEMAP_PASSWORD")},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    _token     = data["access_token"]
    _token_exp = data["expiry_timestamp"]
    return _token

# ── Haversine ──────────────────────────────────────────────────────────────────
R_EARTH = 6_371_000.0

def haversine_matrix(lats, lons, facility_coords):
    """
    lats, lons: 1D arrays of shape (N,)
    facility_coords: 2D array of shape (F, 2) — [lat, lon]
    Returns dist_m: 2D array (N, F)
    """
    lat1 = np.radians(lats)[:, np.newaxis]
    lon1 = np.radians(lons)[:, np.newaxis]
    lat2 = np.radians(facility_coords[:, 0])[np.newaxis, :]
    lon2 = np.radians(facility_coords[:, 1])[np.newaxis, :]
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return R_EARTH * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# ── OneMap geocode ─────────────────────────────────────────────────────────────
STREET_ABBR = {
    "JLN": "JALAN", "LOR": "LORONG", "BT": "BUKIT", "KG": "KAMPONG",
    "C'WEALTH": "COMMONWEALTH", "ST": "STREET", "AVE": "AVENUE",
    "DR": "DRIVE", "CRES": "CRESCENT", "PL": "PLACE", "TER": "TERRACE",
}

def normalize_street(s):
    tokens = s.upper().split()
    return " ".join(STREET_ABBR.get(t, t) for t in tokens)

def geocode_block(block, street, cache):
    key = f"{block} {street}".upper()
    if key in cache and cache[key]:
        return cache[key].get("lat"), cache[key].get("lon")
    query = f"{block} {normalize_street(street)}"
    try:
        r = requests.get(
            "https://www.onemap.gov.sg/api/common/elastic/search",
            params={"searchVal": query, "returnGeom": "Y", "getAddrDetails": "Y", "pageNum": 1},
            headers={"Authorization": get_token()},
            timeout=15,
        )
        results = r.json().get("results", [])
        if results:
            lat = float(results[0]["LATITUDE"])
            lon = float(results[0]["LONGITUDE"])
            cache[key] = {"lat": lat, "lon": lon,
                          "postal": results[0].get("POSTAL", ""),
                          "address": results[0].get("ADDRESS", "")}
            return lat, lon
    except Exception as e:
        print(f"  Geocode failed for {key}: {e}")
    cache[key] = {}
    return None, None

def geocode_postal(postal, cache):
    key = str(postal).zfill(6)
    if key in cache and cache[key]:
        return cache[key].get("lat"), cache[key].get("lon")
    try:
        r = requests.get(
            "https://www.onemap.gov.sg/api/common/elastic/search",
            params={"searchVal": key, "returnGeom": "Y", "getAddrDetails": "Y", "pageNum": 1},
            headers={"Authorization": get_token()},
            timeout=15,
        )
        results = r.json().get("results", [])
        if results:
            lat = float(results[0]["LATITUDE"])
            lon = float(results[0]["LONGITUDE"])
            cache[key] = {"lat": lat, "lon": lon}
            return lat, lon
    except Exception as e:
        print(f"  Geocode postal failed for {key}: {e}")
    cache[key] = {}
    return None, None

def get_nearest_train(block, street, lat, lon, train_cache):
    """Query OneMap for nearest MRT stations, cache result."""
    key = f"{block} {street}".upper()
    if key in train_cache:
        return train_cache[key]
    try:
        r = requests.get(
            "https://www.onemap.gov.sg/api/public/transportapi/getTransportLayer",
            params={"latitude": lat, "longitude": lon, "transportType": "RAIL"},
            headers={"Authorization": get_token()},
            timeout=15,
        )
        data = r.json()
        stations = []
        for item in data.get("GeometryCollection", {}).get("geometries", [])[:20]:
            props = item.get("properties", {})
            name  = props.get("ShortName", "")
            sid   = props.get("StationID", "")
            slat  = item["geometry"]["coordinates"][1] if "geometry" in item else None
            slon  = item["geometry"]["coordinates"][0] if "geometry" in item else None
            if slat and slon:
                dist = round(haversine_matrix(
                    np.array([lat]), np.array([lon]),
                    np.array([[slat, slon]])
                )[0, 0], 1)
                stations.append({"name": name, "id": sid, "dist_m": dist})
        train_cache[key] = sorted(stations, key=lambda x: x["dist_m"])
        return train_cache[key]
    except Exception as e:
        print(f"  Train lookup failed for {key}: {e}")
        train_cache[key] = []
        return []

# ── Load reference data ────────────────────────────────────────────────────────
def load_reference_data():
    # MRT
    mrt_raw = json.load(open(MRT_LOCS_PATH))
    mrt_coords = np.array([[v["lat"], v["lon"]] for v in mrt_raw.values()])
    mrt_names  = list(mrt_raw.keys())
    mrt_lines  = [v["line"] for v in mrt_raw.values()]

    # Hawker (use approx locs — no temporal filtering needed for current listings)
    hawker_raw = json.load(open(HAWKER_LOCS_PATH))
    hawker_coords = np.array([[v["lat"], v["lon"]] for v in hawker_raw.values()])
    hawker_names  = list(hawker_raw.keys())

    # Schools
    school_raw = json.load(open(SCHOOL_LOCS_PATH))
    school_coords = np.array([[v["lat"], v["lon"]] for v in school_raw.values()])
    school_names  = list(school_raw.keys())

    # Parks
    park_raw = json.load(open(PARK_LOCS_PATH))
    park_coords = np.array([[v["lat"], v["lon"]] for v in park_raw.values()])

    # Malls — deduplicate by name, mean lat/lon
    malls_df = pd.read_csv(MALLS_CSV)
    malls_df = malls_df.dropna(subset=["lat", "lon"])
    malls_df = malls_df.groupby("name", as_index=False)[["lat", "lon"]].mean()
    mall_coords = malls_df[["lat", "lon"]].values
    mall_names  = malls_df["name"].tolist()

    # Healthcare — geocode via cache
    hc_df    = pd.read_csv(HEALTHCARE_CSV)
    hc_cache = json.load(open(HEALTHCARE_CACHE_PATH))
    hc_lats, hc_lons, hc_names_list = [], [], []
    for _, row in hc_df.iterrows():
        postal = str(row["postal_code"]).zfill(6)
        cached = hc_cache.get(postal, {})
        if cached.get("lat") and cached.get("lon"):
            hc_lats.append(cached["lat"])
            hc_lons.append(cached["lon"])
            hc_names_list.append(row["institution"])
    hc_coords = np.array(list(zip(hc_lats, hc_lons)))
    hc_names  = hc_names_list

    # SportSG
    sportsg_raw    = json.load(open(SPORTSG_LOCS_PATH))
    sportsg_coords = np.array([[v["lat"], v["lon"]] for v in sportsg_raw.values()])
    sportsg_names  = list(sportsg_raw.keys())

    # CBD
    CBD = np.array([[1.2830, 103.8513]])

    return dict(
        mrt_coords=mrt_coords, mrt_names=mrt_names, mrt_lines=mrt_lines,
        hawker_coords=hawker_coords, hawker_names=hawker_names,
        school_coords=school_coords, school_names=school_names,
        park_coords=park_coords,
        sportsg_coords=sportsg_coords, sportsg_names=sportsg_names,
        mall_coords=mall_coords, mall_names=mall_names,
        hc_coords=hc_coords, hc_names=hc_names,
        cbd=CBD,
    )

# ── Compute amenities for a single block ──────────────────────────────────────
def compute_amenities(lat, lon, ref, block, street, train_cache):
    lats    = np.array([lat])
    lons    = np.array([lon])

    # Hawker
    d_hawker = haversine_matrix(lats, lons, ref["hawker_coords"])[0]
    idx_h    = int(np.argmin(d_hawker))
    dist_hawker  = round(float(d_hawker[idx_h]), 1)
    name_hawker  = ref["hawker_names"][idx_h]

    # CBD
    dist_cbd = round(float(haversine_matrix(lats, lons, ref["cbd"])[0, 0]), 1)

    # Schools within 1km
    d_school = haversine_matrix(lats, lons, ref["school_coords"])[0]
    within_1km = [ref["school_names"][i] for i, d in enumerate(d_school) if d <= 1000]
    dist_nearest_primary = round(float(d_school.min()), 1)
    primary_schools_1km  = "|".join(within_1km) if within_1km else "0"
    num_primary_1km      = len(within_1km)

    # Parks within 1km
    d_park = haversine_matrix(lats, lons, ref["park_coords"])[0]
    dist_nearest_park = round(float(d_park.min()), 1)
    # parks_1km not used by frontend but kept for schema consistency
    num_parks_1km = int((d_park <= 1000).sum())

    # SportSG
    d_sportsg  = haversine_matrix(lats, lons, ref["sportsg_coords"])[0]
    idx_sg     = int(np.argmin(d_sportsg))
    dist_sportsg = round(float(d_sportsg[idx_sg]), 1)
    name_sportsg = ref["sportsg_names"][idx_sg]

    # Malls
    d_mall  = haversine_matrix(lats, lons, ref["mall_coords"])[0]
    idx_m   = int(np.argmin(d_mall))
    dist_mall = round(float(d_mall[idx_m]), 1)
    name_mall = ref["mall_names"][idx_m]

    # Healthcare
    d_hc  = haversine_matrix(lats, lons, ref["hc_coords"])[0]
    idx_h = int(np.argmin(d_hc))
    dist_hc  = round(float(d_hc[idx_h]), 1)
    name_hc  = ref["hc_names"][idx_h]

    # Nearest train — use train_cache (already queried by train_pipeline)
    key = f"{block} {street}".upper()
    stations = train_cache.get(key, [])
    if stations:
        nearest = stations[0]
        line_match = re.match(r"^([A-Za-z]+)", nearest.get("id", ""))
        nearest_train_line = line_match.group(1).upper() if line_match else None
        nearest_train_dist = nearest.get("dist_m")
        nearest_train_name = nearest.get("name")
    else:
        # Fall back to nearest from mrt_approx_locs
        d_mrt = haversine_matrix(lats, lons, ref["mrt_coords"])[0]
        idx_t = int(np.argmin(d_mrt))
        nearest_train_line = ref["mrt_lines"][idx_t]
        nearest_train_dist = round(float(d_mrt[idx_t]), 1)
        nearest_train_name = ref["mrt_names"][idx_t]

    return {
        "lat": lat, "lon": lon,
        "nearest_train_line":      nearest_train_line,
        "nearest_train_dist_m":    nearest_train_dist,
        "nearest_train_name":      nearest_train_name,
        "dist_nearest_hawker_m":   dist_hawker,
        "nearest_hawker_name":     name_hawker,
        "dist_cbd_m":              dist_cbd,
        "dist_nearest_primary_m":  dist_nearest_primary,
        "primary_schools_1km":     primary_schools_1km,
        "num_primary_1km":         num_primary_1km,
        "dist_nearest_park_m":     dist_nearest_park,
        "num_parks_1km":           num_parks_1km,
        "dist_nearest_sportsg_m":  dist_sportsg,
        "nearest_sportsg_name":    name_sportsg,
        "dist_nearest_mall_m":     dist_mall,
        "nearest_mall_name":       name_mall,
        "dist_nearest_healthcare_m": dist_hc,
        "nearest_healthcare_name": name_hc,
    }

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("Loading existing amenity data...")
    amenity_df = pd.read_csv(AMENITY_CSV, low_memory=False)
    amenity_df["_block"]  = amenity_df["block"].astype(str).str.strip().str.upper()
    amenity_df["_street"] = amenity_df["street_name"].astype(str).str.strip().str.upper()
    existing_keys = set(zip(amenity_df["_block"], amenity_df["_street"]))

    print("Loading postal lookup...")
    postal_df = pd.read_csv(POSTAL_CSV)
    postal_df["_block"]  = postal_df["block"].astype(str).str.strip().str.upper()
    postal_df["_street"] = postal_df["street"].astype(str).str.strip().str.upper()

    # Deduplicate postal_df to unique blocks
    postal_unique = postal_df.drop_duplicates(subset=["_block", "_street"]).copy()

    # Find missing blocks
    missing = postal_unique[
        ~postal_unique.apply(lambda r: (r["_block"], r["_street"]) in existing_keys, axis=1)
    ].copy()
    print(f"Blocks missing amenity data: {len(missing)}")

    # Load caches
    geo_cache   = json.load(open(GEO_CACHE_PATH))
    train_cache = json.load(open(TRAIN_CACHE_PATH))

    # Load reference amenity data
    print("Loading reference amenity data...")
    ref = load_reference_data()

    # Geocode missing lat/lon
    need_geocode = missing[missing[["lat", "lon"]].isna().any(axis=1)]
    print(f"Blocks needing geocoding: {len(need_geocode)}")

    for i, (idx, row) in enumerate(need_geocode.iterrows()):
        block  = str(row["block"]).strip()
        street = str(row["street"]).strip()
        print(f"  [{i+1}/{len(need_geocode)}] Geocoding: {block} {street}")
        lat, lon = geocode_block(block, street, geo_cache)
        missing.at[idx, "lat"] = lat
        missing.at[idx, "lon"] = lon
        time.sleep(0.3)
        if (i + 1) % 50 == 0:
            json.dump(geo_cache, open(GEO_CACHE_PATH, "w"), indent=2)
            print(f"  Saved geocode cache ({i+1} processed)")

    json.dump(geo_cache, open(GEO_CACHE_PATH, "w"), indent=2)
    print("Geocode cache saved.")

    # Query train cache for blocks missing it
    has_latlon = missing[missing[["lat", "lon"]].notna().all(axis=1)]
    print(f"Blocks with lat/lon (can enrich): {len(has_latlon)}")

    for i, (idx, row) in enumerate(has_latlon.iterrows()):
        block  = str(row["block"]).strip()
        street = str(row["street"]).strip()
        key    = f"{block} {street}".upper()
        if key not in train_cache:
            print(f"  [{i+1}] Querying train for: {key}")
            get_nearest_train(block, street, row["lat"], row["lon"], train_cache)
            time.sleep(0.3)
            if (i + 1) % 50 == 0:
                json.dump(train_cache, open(TRAIN_CACHE_PATH, "w"), indent=2)

    json.dump(train_cache, open(TRAIN_CACHE_PATH, "w"), indent=2)
    print("Train cache saved.")

    # Compute amenities for all blocks with lat/lon
    print("Computing amenities...")
    new_rows = []
    skipped  = 0
    for _, row in has_latlon.iterrows():
        block  = str(row["block"]).strip()
        street = str(row["street"]).strip()
        lat, lon = float(row["lat"]), float(row["lon"])
        town   = str(row.get("town", "")).replace(" Town", "").upper().strip()

        amenities = compute_amenities(lat, lon, ref, block, street, train_cache)

        # Build a row matching the schema of the amenity CSV
        # Use a placeholder month (latest known) since these are listings not transactions
        new_rows.append({
            "month":        "2026-01",
            "town":         town,
            "flat_type":    str(row.get("flat_type_norm", "")).upper().strip(),
            "block":        block,
            "street_name":  street,
            "storey_range": str(row.get("storey_range", "")).strip(),
            "floor_area_sqm": None,
            "flat_model":   None,
            "lease_commence_date": None,
            "remaining_lease": str(row.get("remaining_lease", "")),
            "resale_price": row.get("price_numeric", None),
            "quarter":      "2026-Q1",
            "rpi":          None,
            "resale_price_real": None,
            "remaining_lease_years": row.get("remaining_lease_years", None),
            **amenities,
        })

    print(f"Enriched {len(new_rows)} blocks, skipped {skipped} (no lat/lon)")

    # Append to amenity CSV
    new_df = pd.DataFrame(new_rows)
    # Align columns to existing
    for col in amenity_df.columns:
        if col not in new_df.columns and col not in ("_block", "_street"):
            new_df[col] = None

    # Drop internal columns before saving
    amenity_df.drop(columns=["_block", "_street"], inplace=True)
    out_cols = [c for c in amenity_df.columns]
    new_df   = new_df.reindex(columns=out_cols)

    combined = pd.concat([amenity_df, new_df], ignore_index=True)
    combined.to_csv(AMENITY_CSV, index=False)
    print(f"Saved {len(combined)} rows to {AMENITY_CSV}")
    print(f"  ({len(amenity_df)} original + {len(new_df)} new)")


if __name__ == "__main__":
    main()
