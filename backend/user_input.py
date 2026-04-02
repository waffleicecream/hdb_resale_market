"""
user_input.py — Compute amenity features for a single HDB address.

Given a postal code, flat type, floor category, and remaining lease, this script:
  1. Geocodes the postal code via the local geocode cache → lat/lon
  2. Detects the HDB town via point-in-polygon against URA planning area boundaries
  3. Finds the nearest train station from MasterPlan2025RailStationLayer.geojson
  4. Computes all amenity distance features using the same static data files
     as the batch pipeline (backend/data_pipeline/3_amenities_pipeline.ipynb)
  5. Prints the complete feature row ready for model inference

Usage:
    python backend/user_input.py

Edit the USER INPUTS section below before running.

NOTE: Postal codes must be present in data/geocode_cache.json (populated by
2_train_pipeline.ipynb). Only HDB blocks that have been processed by the
pipeline are supported.

Output features
---------------
Model inputs (continuous):
  remaining_lease_years     Remaining lease as a decimal year
  nearest_train_dist_m      Distance to nearest open MRT/LRT station (metres)
  dist_nearest_hawker_m     Distance to nearest hawker centre (metres)
  dist_nearest_primary_m    Distance to nearest MOE primary school (metres)
  num_primary_1km           Count of MOE primary schools within 1 km
  dist_nearest_park_m       Distance to nearest NParks park (metres)
  num_parks_1km             Count of NParks parks within 1 km
  dist_nearest_sportsg_m    Distance to nearest SportSG facility (metres)
  dist_nearest_mall_m       Distance to nearest shopping mall (metres)
  dist_nearest_healthcare_m Distance to nearest polyclinic or hospital (metres)

Model inputs (categorical — one-hot encoded at prediction time):
  flat_type                 e.g. 4 ROOM
  town                      HDB town, auto-detected from postal code
  floor_category            Low (floors 1–5) | Mid (6–12) | High (13+)

Informational only (not model features):
  dist_cbd_m                Distance to CBD / Raffles Place MRT (excluded: high
                            VIF with town dummies)
  nearest_train_name/line   Name and line code of the nearest station
  nearest_hawker_name       Name of the nearest hawker centre
  nearest_primary_name      Name of the nearest MOE primary school
  primary_schools_1km       Pipe-separated names of MOE primary schools within 1 km
  nearest_park_name         Name of the nearest NParks park
  parks_1km                 Pipe-separated names of NParks parks within 1 km
  nearest_mall_name         Name of the nearest shopping mall
  nearest_sportsg_name      Name of the nearest SportSG facility
  nearest_healthcare_name   Name of the nearest polyclinic or hospital

Intentionally excluded:
  floor_area_sqm            Not a user-facing input (users pick flat type, not sqm)
"""

import json
import math
import os
import re

import numpy as np
import pandas as pd

# =============================================================================
# USER INPUTS — edit these before running
# =============================================================================
POSTAL_CODE     = "520123"               # 6-digit Singapore postal code
FLAT_TYPE       = "4 ROOM"               # 2 ROOM | 3 ROOM | 4 ROOM | 5 ROOM | EXECUTIVE
FLOOR_CATEGORY  = "Mid"                  # Low (floors 1–5) | Mid (6–12) | High (13+)
REMAINING_LEASE = "61 years 4 months"    # e.g. "61 years" or "61 years 4 months"
# Town is auto-detected from the postal code. Override here only if the
# detected value is wrong (e.g. address is near a planning area boundary):
TOWN_OVERRIDE   = None                   # e.g. "TAMPINES" — set to None to auto-detect

# =============================================================================
# PATHS
# =============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

GEOCODE_CACHE_PATH  = os.path.join(DATA_DIR, "geocode_cache.json")
TRAIN_CACHE_PATH    = os.path.join(DATA_DIR, "train_cache.json")
STATIONS_GEOJSON    = os.path.join(DATA_DIR, "MasterPlan2025RailStationLayer.geojson")


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


def parse_remaining_lease(s: str) -> float:
    """Parse '61 years 4 months' → 61.33, or '61 years' → 61.0."""
    match = re.match(r"(\d+) years?(?: (\d+) months?)?", str(s))
    if not match:
        raise ValueError(f"Cannot parse remaining_lease: {s!r}  (expected e.g. '61 years 4 months')")
    years = int(match.group(1))
    months = int(match.group(2)) if match.group(2) else 0
    return round(years + months / 12, 2)


def point_in_polygon(lon: float, lat: float, ring: list) -> bool:
    """Ray-casting test: True if (lon, lat) is inside the closed coordinate ring."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def lookup_hdb_town(point_lon: float, point_lat: float) -> str | None:
    """
    Return the HDB town name for a given coordinate using a point-in-polygon
    lookup against URA planning area boundaries, then mapping to HDB town names.
    Returns None if the point falls outside all known HDB town areas.
    """
    URA_TO_HDB = {
        "ANG MO KIO":    "ANG MO KIO",    "BEDOK":         "BEDOK",
        "BISHAN":        "BISHAN",         "BUKIT BATOK":   "BUKIT BATOK",
        "BUKIT MERAH":   "BUKIT MERAH",    "BUKIT PANJANG": "BUKIT PANJANG",
        "BUKIT TIMAH":   "BUKIT TIMAH",    "CHOA CHU KANG": "CHOA CHU KANG",
        "CLEMENTI":      "CLEMENTI",        "GEYLANG":       "GEYLANG",
        "HOUGANG":       "HOUGANG",         "JURONG EAST":   "JURONG EAST",
        "JURONG WEST":   "JURONG WEST",     "MARINE PARADE": "MARINE PARADE",
        "PASIR RIS":     "PASIR RIS",       "PUNGGOL":       "PUNGGOL",
        "QUEENSTOWN":    "QUEENSTOWN",      "SEMBAWANG":     "SEMBAWANG",
        "SENGKANG":      "SENGKANG",        "SERANGOON":     "SERANGOON",
        "TAMPINES":      "TAMPINES",        "TOA PAYOH":     "TOA PAYOH",
        "WOODLANDS":     "WOODLANDS",       "YISHUN":        "YISHUN",
        # URA names that differ from HDB town names
        "KALLANG":       "KALLANG/WHAMPOA",
        "ROCHOR":        "KALLANG/WHAMPOA",  # Whampoa HDB estates are in Rochor
        "BOON LAY":      "JURONG WEST",
        "PIONEER":       "JURONG WEST",
        "DOWNTOWN CORE": "CENTRAL AREA",    "MUSEUM":        "CENTRAL AREA",
        "NEWTON":        "CENTRAL AREA",    "ORCHARD":       "CENTRAL AREA",
        "OUTRAM":        "CENTRAL AREA",    "RIVER VALLEY":  "CENTRAL AREA",
        "SINGAPORE RIVER": "CENTRAL AREA",  "TANGLIN":       "CENTRAL AREA",
    }

    with open(os.path.join(DATA_DIR, "ura_planning_area_2019.geojson")) as f:
        gj = json.load(f)

    for feat in gj["features"]:
        ura_name = feat["properties"]["PLN_AREA_N"]
        if ura_name not in URA_TO_HDB:
            continue
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            polygons = [geom["coordinates"]]
        else:  # MultiPolygon
            polygons = geom["coordinates"]

        for poly in polygons:
            outer_ring = poly[0]
            if point_in_polygon(point_lon, point_lat, outer_ring):
                return URA_TO_HDB[ura_name]

    return None


def geocode_from_cache(postal_code: str, cache_path: str) -> tuple[float, float]:
    """
    Look up a 6-digit postal code in the geocode cache and return (lat, lon).
    Raises ValueError if the postal code is not found.
    """
    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)

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


def load_station_data() -> pd.DataFrame:
    """
    Build a DataFrame of MRT/LRT station centroids with line codes.

    Station coordinates come from MasterPlan2025RailStationLayer.geojson
    (centroid of each polygon, averaged across duplicate-name features).
    Line codes come from train_cache.json (name → line prefix mapping).

    Returns columns: name, lat, lon, line_prefix
    """
    # --- Station centroids from GeoJSON ---
    with open(STATIONS_GEOJSON, encoding="utf-8") as f:
        stations_gj = json.load(f)

    centroid_rows = []
    for feat in stations_gj["features"]:
        name = feat["properties"]["NAME"].strip().upper()
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            rings = [geom["coordinates"][0]]
        else:  # MultiPolygon
            rings = [poly[0] for poly in geom["coordinates"]]
        all_coords = [pt for ring in rings for pt in ring]
        centroid_lon = sum(c[0] for c in all_coords) / len(all_coords)
        centroid_lat = sum(c[1] for c in all_coords) / len(all_coords)
        centroid_rows.append({"name": name, "lat": centroid_lat, "lon": centroid_lon})

    centroids = (
        pd.DataFrame(centroid_rows)
        .groupby("name", as_index=False)
        .agg(lat=("lat", "mean"), lon=("lon", "mean"))
    )

    # --- Line code lookup from train_cache ---
    with open(TRAIN_CACHE_PATH, encoding="utf-8") as f:
        train_cache = json.load(f)

    _suffix_re = re.compile(
        r"\s+(?:MRT STATION|LRT STATION|MRT|LRT)$", re.IGNORECASE
    )
    name_to_line: dict[str, str] = {}
    for entries in train_cache.values():
        if not isinstance(entries, list):
            continue
        for s in entries:
            raw_name = str(s.get("name", "")).strip().upper()
            station_id = str(s.get("id", ""))
            m = re.match(r"^([A-Za-z]+)", station_id)
            if not m:
                continue
            line_prefix = m.group(1).upper()
            normalised = _suffix_re.sub("", raw_name).strip()
            if normalised not in name_to_line:
                name_to_line[normalised] = line_prefix

    centroids["line_prefix"] = centroids["name"].map(name_to_line).fillna("UNKNOWN")
    return centroids


# =============================================================================
# STEP 1 — Geocode postal code via cache
# =============================================================================
print(f"Step 1: Looking up postal code {POSTAL_CODE} in geocode cache...")
lat, lon = geocode_from_cache(POSTAL_CODE, GEOCODE_CACHE_PATH)
print(f"  lat={lat:.6f}, lon={lon:.6f}")

# Detect HDB town from coordinates
print("  Detecting HDB town from coordinates...")
detected_town = lookup_hdb_town(lon, lat)
if TOWN_OVERRIDE:
    town = TOWN_OVERRIDE.upper()
    print(f"  town: {town} (manually overridden; auto-detected: {detected_town})")
elif detected_town:
    town = detected_town
    print(f"  town: {town} (auto-detected)")
else:
    raise SystemExit(
        f"Could not map postal code {POSTAL_CODE} to an HDB town. "
        "Set TOWN_OVERRIDE manually (e.g. TOWN_OVERRIDE = 'TAMPINES')."
    )


# =============================================================================
# STEP 2 — Nearest train station via static GeoJSON
# =============================================================================
PUBLIC_RAIL_PREFIXES = (
    "NS", "EW", "CC", "DT", "NE", "TE", "CG", "CE", "JS", "JW",
    "BP", "SW", "SE", "PE", "PW",
)

print("Step 2: Finding nearest train station from static data...")
stations = load_station_data()

# Filter to public rail only (exclude any non-rail features with unknown codes)
public_mask = stations["line_prefix"].isin(PUBLIC_RAIL_PREFIXES)
public_stations = stations[public_mask].reset_index(drop=True)

if public_stations.empty:
    raise SystemExit("No public rail stations found in MasterPlan2025RailStationLayer.geojson.")

dists = haversine_m(lat, lon, public_stations["lat"].values, public_stations["lon"].values)
best_idx             = int(np.argmin(dists))
nearest_train_dist_m = float(dists[best_idx])
nearest_train_name   = public_stations.iloc[best_idx]["name"]
nearest_train_line   = public_stations.iloc[best_idx]["line_prefix"]

print(f"  {nearest_train_name} ({nearest_train_line}) — {nearest_train_dist_m:.0f} m")


# =============================================================================
# STEP 3 — Amenity features (mirrors 3_amenities_pipeline.ipynb logic)
# All distances in metres. Transaction is assumed to be in 2026, so all
# hawker centres are treated as open (no date-based filtering needed).
# =============================================================================
print("Step 3: Computing amenity features...")


# --- Hawker centres ---
with open(os.path.join(DATA_DIR, "HawkerCentresGEOJSON.geojson")) as f:
    hawker_geojson = json.load(f)

hawker_rows = []
for feat in hawker_geojson["features"]:
    h_lon, h_lat = feat["geometry"]["coordinates"][:2]
    hawker_rows.append({"name": feat["properties"]["NAME"], "lat": h_lat, "lon": h_lon})
hawkers = pd.DataFrame(hawker_rows)

hawker_dists          = haversine_m(lat, lon, hawkers["lat"].values, hawkers["lon"].values)
nearest_hawker_idx    = int(np.argmin(hawker_dists))
dist_nearest_hawker_m = float(hawker_dists[nearest_hawker_idx])
nearest_hawker_name   = hawkers.iloc[nearest_hawker_idx]["name"]

print(f"  hawker:     {nearest_hawker_name} — {dist_nearest_hawker_m:.0f} m")


# --- CBD distance (Raffles Place MRT — informational only, not a model feature) ---
CBD_LAT, CBD_LON = 1.2830, 103.8513
dist_cbd_m = float(haversine_m(lat, lon, np.array([CBD_LAT]), np.array([CBD_LON]))[0])


# --- Primary schools ---
with open(os.path.join(DATA_DIR, "school_geocode_cache.json")) as f:
    school_cache = json.load(f)

_schools_df = pd.read_csv(os.path.join(DATA_DIR, "Generalinformationofschools.csv"))
_schools_df = _schools_df[_schools_df["mainlevel_code"] == "PRIMARY"]
_school_postal_to_name = dict(
    zip(_schools_df["postal_code"].astype(str), _schools_df["school_name"])
)
school_names = [_school_postal_to_name.get(k, k) for k in school_cache.keys()]
school_lats  = np.array([v["lat"] for v in school_cache.values()])
school_lons  = np.array([v["lon"] for v in school_cache.values()])
school_dists            = haversine_m(lat, lon, school_lats, school_lons)
nearest_school_idx      = int(np.argmin(school_dists))
dist_nearest_primary_m  = float(school_dists[nearest_school_idx])
nearest_primary_name    = school_names[nearest_school_idx]
num_primary_1km         = int(np.sum(school_dists <= 1000))
primary_schools_1km     = "|".join(school_names[i] for i in np.where(school_dists <= 1000)[0])

print(f"  schools:    nearest={dist_nearest_primary_m:.0f} m ({nearest_primary_name}), within 1 km={num_primary_1km}")


# --- Parks (same exclusion rules as the pipeline) ---
PARK_EXCLUSION_SUFFIXES = ("PLAYGROUND", "TERMINAL", "NURSERY", "STATELAND", "LINKWAY")
PARK_EXCLUSION_CONTAINS = ("CAR PARK",)

with open(os.path.join(DATA_DIR, "Parks.geojson")) as f:
    parks_geojson = json.load(f)

park_rows = []
for feat in parks_geojson["features"]:
    name = feat["properties"].get("NAME", "")
    if any(name.endswith(s) for s in PARK_EXCLUSION_SUFFIXES):
        continue
    if any(s in name for s in PARK_EXCLUSION_CONTAINS):
        continue
    p_lon, p_lat = feat["geometry"]["coordinates"][:2]
    park_rows.append({"name": name, "lat": p_lat, "lon": p_lon})
parks = pd.DataFrame(park_rows)

park_dists          = haversine_m(lat, lon, parks["lat"].values, parks["lon"].values)
nearest_park_idx    = int(np.argmin(park_dists))
dist_nearest_park_m = float(park_dists[nearest_park_idx])
nearest_park_name   = parks.iloc[nearest_park_idx]["name"]
num_parks_1km       = int(np.sum(park_dists <= 1000))
parks_1km           = "|".join(parks.iloc[i]["name"] for i in np.where(park_dists <= 1000)[0])

print(f"  parks:      nearest={dist_nearest_park_m:.0f} m ({nearest_park_name}), within 1 km={num_parks_1km}")


# --- SportSG facilities ---
with open(os.path.join(DATA_DIR, "SportSGSportFacilitiesGEOJSON.geojson")) as f:
    sport_geojson = json.load(f)

sport_rows = []
for feat in sport_geojson["features"]:
    s_lon, s_lat = feat["geometry"]["coordinates"][:2]
    sport_rows.append({"venue": feat["properties"].get("VENUE", ""), "lat": s_lat, "lon": s_lon})
sports = pd.DataFrame(sport_rows)

sport_dists            = haversine_m(lat, lon, sports["lat"].values, sports["lon"].values)
nearest_sport_idx      = int(np.argmin(sport_dists))
dist_nearest_sportsg_m = float(sport_dists[nearest_sport_idx])
nearest_sportsg_name   = sports.iloc[nearest_sport_idx]["venue"]

print(f"  sport:      {nearest_sportsg_name} — {dist_nearest_sportsg_m:.0f} m")


# --- Shopping malls ---
malls_raw = pd.read_csv(os.path.join(DATA_DIR, "shoppingmalls.csv"))
malls = malls_raw.groupby("name", as_index=False).agg(lat=("lat", "mean"), lon=("lon", "mean"))

mall_dists          = haversine_m(lat, lon, malls["lat"].values, malls["lon"].values)
nearest_mall_idx    = int(np.argmin(mall_dists))
dist_nearest_mall_m = float(mall_dists[nearest_mall_idx])
nearest_mall_name   = malls.iloc[nearest_mall_idx]["name"]

print(f"  mall:       {nearest_mall_name} — {dist_nearest_mall_m:.0f} m")


# --- Healthcare (polyclinics + hospitals) ---
with open(os.path.join(DATA_DIR, "healthcare_geocode_cache.json")) as f:
    hc_cache = json.load(f)

_hc_df = pd.read_csv(os.path.join(DATA_DIR, "healthcare_address.csv"))
_hc_postal_to_name = dict(zip(_hc_df["postal_code"].astype(str), _hc_df["institution"]))
hc_names = [_hc_postal_to_name.get(k, k) for k in hc_cache.keys()]
hc_lats  = np.array([v["lat"] for v in hc_cache.values()])
hc_lons  = np.array([v["lon"] for v in hc_cache.values()])
hc_dists                  = haversine_m(lat, lon, hc_lats, hc_lons)
nearest_hc_idx            = int(np.argmin(hc_dists))
dist_nearest_healthcare_m = float(hc_dists[nearest_hc_idx])
nearest_healthcare_name   = hc_names[nearest_hc_idx]

print(f"  healthcare: nearest={dist_nearest_healthcare_m:.0f} m ({nearest_healthcare_name})")


# =============================================================================
# STEP 4 — Derived features
# =============================================================================
if FLOOR_CATEGORY not in ("Low", "Mid", "High"):
    raise ValueError(f"FLOOR_CATEGORY must be 'Low', 'Mid', or 'High' — got {FLOOR_CATEGORY!r}")
floor_category        = FLOOR_CATEGORY
remaining_lease_years = parse_remaining_lease(REMAINING_LEASE)


# =============================================================================
# STEP 5 — Assembled feature row
# =============================================================================
features = {
    # Continuous features (model inputs)
    "remaining_lease_years":     remaining_lease_years,
    "nearest_train_dist_m":      round(nearest_train_dist_m, 1),
    "dist_nearest_hawker_m":     round(dist_nearest_hawker_m, 1),
    "dist_nearest_primary_m":    round(dist_nearest_primary_m, 1),
    "num_primary_1km":           num_primary_1km,
    "dist_nearest_park_m":       round(dist_nearest_park_m, 1),
    "num_parks_1km":             num_parks_1km,
    "dist_nearest_sportsg_m":    round(dist_nearest_sportsg_m, 1),
    "dist_nearest_mall_m":       round(dist_nearest_mall_m, 1),
    "dist_nearest_healthcare_m": round(dist_nearest_healthcare_m, 1),
    # Categorical features (encoded at prediction time)
    "flat_type":                 FLAT_TYPE,
    "town":                      town,
    "floor_category":            floor_category,
}

info = {
    "dist_cbd_m":              round(dist_cbd_m, 1),
    "nearest_train_name":      nearest_train_name,
    "nearest_train_line":      nearest_train_line,
    "nearest_hawker_name":     nearest_hawker_name,
    "nearest_primary_name":    nearest_primary_name,
    "primary_schools_1km":     primary_schools_1km,
    "nearest_park_name":       nearest_park_name,
    "parks_1km":               parks_1km,
    "nearest_mall_name":       nearest_mall_name,
    "nearest_sportsg_name":    nearest_sportsg_name,
    "nearest_healthcare_name": nearest_healthcare_name,
}

df = pd.DataFrame([{**features, **info}])

print("\n" + "=" * 60)
print("FEATURE ROW")
print("=" * 60)
for k, v in features.items():
    print(f"  {k:<30} {v}")

print("\n  --- informational (not model features) ---")
for k, v in info.items():
    print(f"  {k:<30} {v}")


# =============================================================================
# MODEL PREDICTION (Random Forest) — uncomment to use
# =============================================================================
# PREREQUISITE: First serialize the trained model from random_forest_modelling.ipynb:
#   import joblib
#   joblib.dump(rf_model, 'backend/price_model/random_forest_model.joblib')
#
# The TRAIN_COLUMNS list must exactly match X_train.columns from the notebook.
# To verify, run: list(X_train.columns)  in the notebook after fitting.
#
# import joblib
#
# CONTINUOUS_FEATURES = [
#     "remaining_lease_years", "nearest_train_dist_m",
#     "dist_nearest_hawker_m", "dist_nearest_primary_m", "num_primary_1km",
#     "dist_nearest_park_m", "dist_nearest_sportsg_m",
#     "dist_nearest_mall_m", "dist_nearest_healthcare_m",
# ]
# FLAT_TYPES = ["2 ROOM", "3 ROOM", "4 ROOM", "5 ROOM", "EXECUTIVE"]
# TOWNS = [
#     "ANG MO KIO", "BEDOK", "BISHAN", "BUKIT BATOK", "BUKIT MERAH",
#     "BUKIT PANJANG", "BUKIT TIMAH", "CENTRAL AREA", "CHOA CHU KANG",
#     "CLEMENTI", "GEYLANG", "HOUGANG", "JURONG EAST", "JURONG WEST",
#     "KALLANG/WHAMPOA", "MARINE PARADE", "PASIR RIS", "PUNGGOL",
#     "QUEENSTOWN", "SEMBAWANG", "SENGKANG", "SERANGOON", "TAMPINES",
#     "TOA PAYOH", "WOODLANDS", "YISHUN",
# ]
# FLOOR_CATS = ["High", "Low", "Mid"]
# TRAIN_COLUMNS = (
#     CONTINUOUS_FEATURES
#     + [f"flat_type_{ft}" for ft in FLAT_TYPES]
#     + [f"town_{t}" for t in TOWNS]
#     + [f"floor_category_{fc}" for fc in FLOOR_CATS]
# )
#
# rf_model = joblib.load(
#     os.path.join(BASE_DIR, "backend", "price_model", "random_forest_model.joblib")
# )
#
# # Build a one-row DataFrame with all OHE columns zeroed, then set the active ones
# row = {col: 0 for col in TRAIN_COLUMNS}
# for feat in CONTINUOUS_FEATURES:
#     row[feat] = features[feat]
# row[f"flat_type_{features['flat_type']}"]             = 1
# row[f"town_{features['town']}"]                       = 1
# row[f"floor_category_{features['floor_category']}"]   = 1
#
# X_input = pd.DataFrame([row])[TRAIN_COLUMNS]
# y_log   = rf_model.predict(X_input)
# predicted_price = np.exp(y_log[0])
# print(f"\nPredicted resale price (2025 SGD): ${predicted_price:,.0f}")
