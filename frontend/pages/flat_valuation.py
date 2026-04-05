import json, os
import requests
import pandas as pd
import numpy as np
import dash
from dash import html, dcc, callback, Output, Input, State, no_update, ctx
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

dash.register_page(__name__, path="/flat-valuation", name="Flat Valuation")

_BASE    = os.path.dirname(os.path.dirname(__file__))
_ROOT    = os.path.dirname(_BASE)
_MERGED  = os.path.join(_ROOT, "merged_data")
_DATA    = os.path.join(_ROOT, "data")
_BACKEND = os.path.join(_ROOT, "backend")

with open(os.path.join(_BASE, "mock_data", "valuation_demo.json"), encoding="utf-8") as f:
    DEMO = json.load(f)

# ── Backend data loaded once at startup ───────────────────────

def _load_df(path, **kwargs):
    return pd.read_csv(path, low_memory=False, **kwargs) if os.path.exists(path) else pd.DataFrame()

_ENRICHED = _load_df(os.path.join(_DATA, "hdb_2026_enriched.csv"))
_PAST_TXN = _load_df(os.path.join(_MERGED, "[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv"))

if not _PAST_TXN.empty:
    _PAST_TXN["street_upper"] = _PAST_TXN["street_name"].str.upper().str.strip()

# ── Geocode cache: postal → {lat, lon, block, street} ──────────
def _build_geocode_lookup():
    path = os.path.join(_DATA, "geocode_cache.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        cache = json.load(f)
    out = {}
    for key, v in cache.items():
        if not isinstance(v, dict):
            continue
        p = str(v.get("postal", "")).strip()
        if not p.isdigit() or len(p) != 6:
            continue
        parts = key.split()
        out[str(v["postal"]).strip().zfill(6)] = {
            "lat":    v.get("lat"),
            "lon":    v.get("lon"),
            "block":  parts[0] if parts else "",
            "street": " ".join(parts[1:]) if len(parts) > 1 else "",
        }
    return out

_GEOCODE_LOOKUP = _build_geocode_lookup()

# ── Town lookup: (block_upper, street_upper) → town ────────────
def _build_town_lookup():
    out = {}
    for path in (
        os.path.join(_MERGED, "[FINAL]hdb_with_amenities_macro_pre2026.csv"),
        os.path.join(_MERGED, "[FINAL]hdb_with_amenities_macro_2026.csv"),
    ):
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, usecols=["block", "street_name", "town"], low_memory=False)
        for _, r in df.drop_duplicates(["block", "street_name"]).iterrows():
            key = (str(r["block"]).upper().strip(), str(r["street_name"]).upper().strip())
            out[key] = str(r["town"]).replace(" Town", "").strip().upper()
    return out

_TOWN_LOOKUP = _build_town_lookup()

# ── Postal dropdown options: all 9k+ geocoded postcodes ────────
def _build_postal_options():
    rows = []
    # Start with enriched CSV (has flat_type info for display)
    enriched_postals = set()
    if not _ENRICHED.empty:
        for _, r in (_ENRICHED[["postal_code", "block", "street", "town"]]
                     .drop_duplicates("postal_code")
                     .dropna(subset=["postal_code"])
                     .iterrows()):
            p = str(r["postal_code"]).zfill(6)
            enriched_postals.add(p)
            rows.append({
                "label": f"{p}  —  Blk {r['block']} {str(r['street']).title()}, {str(r['town']).replace(' Town','').title()}",
                "value": p,
            })
    # Fill remaining from geocode cache
    for postal, g in sorted(_GEOCODE_LOOKUP.items()):
        if postal in enriched_postals:
            continue
        blk = g["block"]
        st  = g["street"].title()
        bk_up = g["block"].upper()
        st_up = g["street"].upper()
        town_raw = _TOWN_LOOKUP.get((bk_up, st_up), "")
        town_disp = town_raw.title() if town_raw else ""
        label = f"{postal}  —  Blk {blk} {st}" + (f", {town_disp}" if town_disp else "")
        rows.append({"label": label, "value": postal})
    return sorted(rows, key=lambda x: x["value"])

_POSTAL_OPTIONS = _build_postal_options()

# ── Autofill meta: postal → {flat_type, storey_level_bin, remaining_lease_bin}
def _build_postal_meta():
    def _lease_bin(s):
        try:
            y = float(str(s).split()[0])
        except Exception:
            return None
        if y < 60:  return "Under 60 years"
        if y < 75:  return "60-75 years"
        if y < 90:  return "75-90 years"
        return "Over 90 years"

    def _storey_bin(fc):
        return {"Low": "Low", "Mid": "Medium", "High": "High"}.get(str(fc), None)

    out = {}
    if not _ENRICHED.empty:
        for _, r in _ENRICHED.drop_duplicates("postal_code").iterrows():
            out[str(r["postal_code"]).zfill(6)] = {
                "flat_type": str(r.get("rooms", "")).strip() or None,
                "storey_level_bin": _storey_bin(r.get("floor_category", "")),
                "remaining_lease_bin": _lease_bin(r.get("remaining_lease", "")),
            }
    return out

_POSTAL_META = _build_postal_meta()

# UI flat_type ("4-Room") → data flat_type ("4 ROOM")
_FT_MAP = {
    "2-Room": "2 ROOM", "3-Room": "3 ROOM", "4-Room": "4 ROOM",
    "5-Room": "5 ROOM", "Executive": "EXECUTIVE",
}
# Storey UI → floor_category
_STOREY_MAP = {"Low": "Low", "Medium": "Mid", "High": "High"}

# ── Amenity pin data loaded once at startup ────────────────────
def _load_amenity_pins():
    """Load malls, schools, healthcare, MRT, hawker into lists of {lat, lon, name}."""
    pins = {"mall": [], "school": [], "healthcare": [], "mrt": [], "hawker": [], "park": []}

    # Malls: data/shoppingmalls.csv
    mall_path = os.path.join(_DATA, "shoppingmalls.csv")
    if os.path.exists(mall_path):
        mdf = pd.read_csv(mall_path)
        for _, r in mdf.dropna(subset=["lat", "lon"]).iterrows():
            pins["mall"].append({"lat": float(r["lat"]), "lon": float(r["lon"]),
                                  "name": str(r.get("name", "Mall"))})

    # Schools: data/school_name_locs.json — keyed by school name, value {lat, lon}
    school_path = os.path.join(_DATA, "school_name_locs.json")
    if os.path.exists(school_path):
        with open(school_path, encoding="utf-8") as f:
            scache = json.load(f)
        for name, v in scache.items():
            if isinstance(v, dict) and v.get("lat") and v.get("lon"):
                pins["school"].append({"lat": float(v["lat"]), "lon": float(v["lon"]),
                                        "name": str(name).title()})

    # Healthcare: data/healthcare_geocode_cache.json — keyed by postal, value {lat, lon}
    health_path = os.path.join(_DATA, "healthcare_geocode_cache.json")
    if os.path.exists(health_path):
        with open(health_path, encoding="utf-8") as f:
            hcache = json.load(f)
        for postal, v in hcache.items():
            if isinstance(v, dict) and v.get("lat") and v.get("lon"):
                pins["healthcare"].append({"lat": float(v["lat"]), "lon": float(v["lon"]),
                                            "name": f"Healthcare ({postal})"})

    # MRT/LRT: data/mrt_approx_locs.json — keyed by station name, value {lat, lon, line}
    mrt_path = os.path.join(_DATA, "mrt_approx_locs.json")
    if os.path.exists(mrt_path):
        with open(mrt_path, encoding="utf-8") as f:
            mcache = json.load(f)
        for name, v in mcache.items():
            if isinstance(v, dict) and v.get("lat") and v.get("lon"):
                line = v.get("line", "")
                label = str(name).title().replace("Mrt Station", "MRT").replace("Lrt Station", "LRT")
                hover = f"{label}" + (f" ({line})" if line else "")
                pins["mrt"].append({"lat": float(v["lat"]), "lon": float(v["lon"]),
                                     "name": hover})

    # Hawker: data/hawker_approx_locs.json — keyed by name, value {lat, lon}
    hawker_path = os.path.join(_DATA, "hawker_approx_locs.json")
    if os.path.exists(hawker_path):
        with open(hawker_path, encoding="utf-8") as f:
            hkcache = json.load(f)
        for name, v in hkcache.items():
            if isinstance(v, dict) and v.get("lat") and v.get("lon"):
                pins["hawker"].append({"lat": float(v["lat"]), "lon": float(v["lon"]),
                                        "name": str(name)})

    # Parks: data/park_approx_locs.json — keyed by name, value {lat, lon}
    park_path = os.path.join(_DATA, "park_approx_locs.json")
    if os.path.exists(park_path):
        with open(park_path, encoding="utf-8") as f:
            pkcache = json.load(f)
        for name, v in pkcache.items():
            if isinstance(v, dict) and v.get("lat") and v.get("lon"):
                pins["park"].append({"lat": float(v["lat"]), "lon": float(v["lon"]),
                                      "name": str(name).title()})

    return pins

_AMENITY_PINS = _load_amenity_pins()

# ── RF model loaded once at startup ───────────────────────────
_RF_MODEL   = None
_RF_ENCODER = None
_RF_COLS    = None
_RF_Q_LOW   = None
_RF_Q_HIGH  = None

try:
    import joblib as _joblib
    from huggingface_hub import hf_hub_download as _hf_hub_download

    _MODEL_DIR  = os.path.join(_BACKEND, "price_model")
    _HF_REPO_ID = "xiulii/dse3101-rf-model"

    # Auto-download rf_model.pkl from HuggingFace if not present locally (1.3 GB, too large for GitHub)
    _rf_model_path = os.path.join(_MODEL_DIR, "rf_model.pkl")
    if not os.path.exists(_rf_model_path):
        print("[flat_valuation] rf_model.pkl not found locally — downloading from HuggingFace...")
        _rf_model_path = _hf_hub_download(repo_id=_HF_REPO_ID, filename="rf_model.pkl",
                                           local_dir=_MODEL_DIR)
        print("[flat_valuation] Download complete.")

    if all(os.path.exists(os.path.join(_MODEL_DIR, f))
           for f in ("rf_encoder.pkl", "rf_feature_cols.pkl", "rf_conformal_quantiles.json")):
        _RF_MODEL   = _joblib.load(_rf_model_path)
        _RF_ENCODER = _joblib.load(os.path.join(_MODEL_DIR, "rf_encoder.pkl"))
        _RF_COLS    = _joblib.load(os.path.join(_MODEL_DIR, "rf_feature_cols.pkl"))
        with open(os.path.join(_MODEL_DIR, "rf_conformal_quantiles.json")) as _f:
            _q = json.load(_f)
            _RF_Q_LOW, _RF_Q_HIGH = _q["q_low"], _q["q_high"]
        print("[flat_valuation] RF model loaded OK")
except Exception as _e:
    print(f"[flat_valuation] RF model not loaded: {_e}")

# Amenity lookup: (block_upper, street_upper) → amenity feature dict
# Built from pipeline CSVs (2026 wins over pre-2026 on duplicate block+street)
_RF_CONTINUOUS = [
    "remaining_lease_years", "nearest_train_dist_m", "dist_nearest_hawker_m",
    "dist_nearest_primary_m", "num_primary_1km", "dist_nearest_park_m",
    "num_parks_1km", "dist_nearest_sportsg_m", "dist_nearest_mall_m",
    "dist_nearest_healthcare_m", "dist_cbd_m",
]
_RF_CATEGORICAL = ["flat_type", "town", "floor_category"]

def _build_amenity_lookup():
    lookup = {}
    load_cols = ["block", "street_name", "town"] + _RF_CONTINUOUS
    for path in (
        os.path.join(_MERGED, "[FINAL]hdb_with_amenities_macro_pre2026.csv"),
        os.path.join(_MERGED, "[FINAL]hdb_with_amenities_macro_2026.csv"),
    ):
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, usecols=load_cols, low_memory=False)
        df["_bk"] = df["block"].astype(str).str.upper().str.strip()
        df["_st"] = df["street_name"].astype(str).str.upper().str.strip()
        for _, r in df.drop_duplicates(subset=["_bk", "_st"], keep="last").iterrows():
            lookup[(r["_bk"], r["_st"])] = r.to_dict()
    return lookup

_AMENITY_LOOKUP = _build_amenity_lookup()


def get_rf_prediction(block, street_upper, town, flat_type_ui, floor_category, remaining_lease_years):
    """
    Run RF model using pre-computed amenity features from pipeline CSVs.
    Returns (p_low, median, p_high) using conformal prediction intervals, or None if unavailable.
    """
    if _RF_MODEL is None or remaining_lease_years is None:
        return None

    amenity_row = _AMENITY_LOOKUP.get(
        (str(block).upper().strip(), street_upper)
    )
    if amenity_row is None:
        return None

    ft = _FT_MAP.get(flat_type_ui, flat_type_ui.upper())
    fc = _STOREY_MAP.get(floor_category, floor_category)

    try:
        cont = {c: amenity_row[c] for c in _RF_CONTINUOUS}
        cont["remaining_lease_years"] = remaining_lease_years

        row = {c: cont[c] for c in _RF_CONTINUOUS}
        row["flat_type"]      = ft
        row["town"]           = str(town).upper().strip()
        row["floor_category"] = fc

        X = pd.DataFrame([row])[_RF_COLS]
        X[_RF_CATEGORICAL] = _RF_ENCODER.transform(X[_RF_CATEGORICAL])
        X = X.astype(float)

        point = float(np.exp(_RF_MODEL.predict(X)[0]))
        return (
            int(point + _RF_Q_LOW),
            int(point),
            int(point + _RF_Q_HIGH),
        )
    except Exception:
        return None


def _meta_from_postal(postal):
    """
    Return a meta dict for this postal code.
    Tries enriched CSV first (has flat_type/lease).
    If lat/lon is missing from enriched, patches from geocode cache.
    Falls back to geocode cache entirely if not in enriched.
    """
    import pandas as _pd
    p = str(postal).strip().zfill(6)
    if not _ENRICHED.empty:
        match = _ENRICHED[_ENRICHED["postal_code"].astype(str).str.zfill(6) == p]
        if not match.empty:
            row = match.iloc[0].to_dict()
            # Patch missing lat/lon from geocode cache
            if not _pd.notna(row.get("lat")) or not _pd.notna(row.get("lon")):
                g = _GEOCODE_LOOKUP.get(p)
                if g:
                    row["lat"] = g.get("lat")
                    row["lon"] = g.get("lon")
            return row
    # Fallback: geocode cache gives lat/lon/block/street; town from amenity lookup
    g = _GEOCODE_LOOKUP.get(p)
    if g is None:
        return None
    bk_up = str(g["block"]).upper().strip()
    st_up = str(g["street"]).upper().strip()
    town  = _TOWN_LOOKUP.get((bk_up, st_up), "")
    return {
        "postal_code":           p,
        "block":                 g["block"],
        "street":                g["street"].title(),
        "town":                  town,
        "lat":                   g.get("lat"),
        "lon":                   g.get("lon"),
        "remaining_lease":       None,
        "remaining_lease_years": None,
        "floor_category":        None,
        "rooms":                 None,
    }



def get_placeholder_prediction(town, flat_type_ui, floor_category):
    """
    Placeholder prediction: median resale_price for this town×flat_type×floor_category
    from PAST_TRANSACTIONS. Returns (p15, median, p85) in SGD, or None if no data.
    """
    if _PAST_TXN.empty:
        return None
    ft = _FT_MAP.get(flat_type_ui, flat_type_ui.upper())
    fc = _STOREY_MAP.get(floor_category, floor_category)
    sub = _PAST_TXN[
        (_PAST_TXN["town"].str.upper() == str(town).upper()) &
        (_PAST_TXN["flat_type"] == ft) &
        (_PAST_TXN["floor_category"] == fc)
    ]["resale_price"].dropna()
    if len(sub) < 3:
        # Widen to town+flat_type only
        sub = _PAST_TXN[
            (_PAST_TXN["town"].str.upper() == str(town).upper()) &
            (_PAST_TXN["flat_type"] == ft)
        ]["resale_price"].dropna()
    if sub.empty:
        return None
    return (
        int(np.percentile(sub, 15)),
        int(np.median(sub)),
        int(np.percentile(sub, 85)),
    )


def _nearby_txn_mask(lat, lon, radius_m=200):
    """Return boolean mask of _PAST_TXN rows within radius_m of (lat, lon)."""
    R = 6_371_000
    dlat = np.radians(_PAST_TXN["lat"] - lat)
    dlon = np.radians(_PAST_TXN["lon"] - lon)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat)) * np.cos(np.radians(_PAST_TXN["lat"]))
         * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)) <= radius_m


def _get_nearby_txns(lat, lon, flat_type_ui, floor_category, street_upper_fallback):
    """
    Return (sub, fc, source_label) where source_label describes the data source used.
    Tries 200m radius → 500m radius → street name fallback.
    """
    ft = _FT_MAP.get(flat_type_ui, flat_type_ui.upper())
    fc = _STOREY_MAP.get(floor_category, floor_category)

    if lat is not None and lon is not None:
        for radius in (200, 500):
            mask = _nearby_txn_mask(lat, lon, radius)
            sub = _PAST_TXN[mask & (_PAST_TXN["flat_type"] == ft) & (_PAST_TXN["floor_category"] == fc)]
            if len(sub) >= 5:
                label = f"Within {radius}m of your flat · {flat_type_ui} · {floor_category} floor"
                return sub, fc, label
        # Widen: drop floor filter if not enough results
        for radius in (200, 500):
            mask = _nearby_txn_mask(lat, lon, radius)
            sub = _PAST_TXN[mask & (_PAST_TXN["flat_type"] == ft)]
            if len(sub) >= 5:
                label = f"Within {radius}m of your flat · {flat_type_ui} · all floors"
                return sub, fc, label
        # Use 500m flat type result even if < 5
        label = f"Within 500m of your flat · {flat_type_ui} · all floors"
        return sub, fc, label
    else:
        # Fallback: street name + floor
        sub = _PAST_TXN[
            (_PAST_TXN["street_upper"] == street_upper_fallback) &
            (_PAST_TXN["flat_type"] == ft) &
            (_PAST_TXN["floor_category"] == fc)
        ]
        if len(sub) < 5:
            sub = _PAST_TXN[
                (_PAST_TXN["street_upper"] == street_upper_fallback) &
                (_PAST_TXN["flat_type"] == ft)
            ]
            return sub, fc, f"Same street · {flat_type_ui}"
        return sub, fc, f"Same street · {flat_type_ui} · {floor_category} floor"


def get_nearby_trends(lat, lon, flat_type_ui, floor_category, street_upper_fallback):
    """Return (trend_list, source_label) aggregated from nearby txns."""
    if _PAST_TXN.empty:
        return [], "no data"
    sub, fc, source_label = _get_nearby_txns(lat, lon, flat_type_ui, floor_category, street_upper_fallback)
    if sub.empty:
        return [], source_label
    agg = (sub.groupby("quarter")
           .agg(avg_price=("resale_price", "mean"), n_transactions=("resale_price", "count"))
           .reset_index()
           .sort_values("quarter"))
    trends = [{"quarter": r["quarter"], "avg_price": int(r["avg_price"]),
               "n_transactions": int(r["n_transactions"])} for _, r in agg.iterrows()]
    return trends, source_label


def get_past_transactions(lat, lon, flat_type_ui, floor_category, street_upper_fallback, n=10):
    """Return list of {date, block, street, floor, flat_type, price, lat, lon} for table + map."""
    if _PAST_TXN.empty:
        return []
    sub, fc, _ = _get_nearby_txns(lat, lon, flat_type_ui, floor_category, street_upper_fallback)
    sub = sub.sort_values("month", ascending=False).head(n)
    return [
        {"date": r["month"], "block": str(r["block"]), "street": str(r["street_name"]),
         "floor": r["storey_range"], "flat_type": r["flat_type"], "price": int(r["resale_price"]),
         "remaining_lease": str(r["remaining_lease"]) if pd.notna(r.get("remaining_lease")) else "—",
         "lat": float(r["lat"]) if pd.notna(r.get("lat")) else None,
         "lon": float(r["lon"]) if pd.notna(r.get("lon")) else None}
        for _, r in sub.iterrows()
    ]


def get_current_listings(town, flat_type_ui, storey_bin=None, lease_bin=None, block=None, scope="town"):
    """
    Current listings filtered by scope:
      scope='town'  — same town, ordered by price (cheapest first)
      scope='block' — same block + same town, ordered by price
    Hard filters: flat_type, floor_category (storey_bin), remaining_lease_years (lease_bin).
    """
    if _ENRICHED.empty:
        return []
    ft_norm = _FT_MAP.get(flat_type_ui, flat_type_ui.upper())
    town_upper = str(town).replace(" Town", "").strip().upper()
    fc = _STOREY_MAP.get(storey_bin, storey_bin) if storey_bin else None

    _lease_bin_ranges = {
        "Under 60 years": (0, 60),
        "60-75 years": (60, 75),
        "75-90 years": (75, 90),
        "Over 90 years": (90, 200),
    }
    lease_range = _lease_bin_ranges.get(lease_bin) if lease_bin else None

    base_mask = (
        (_ENRICHED["flat_type_norm"] == ft_norm) &
        (_ENRICHED["price_numeric"].notna()) &
        (_ENRICHED["scrape_failed"] == False) &
        (_ENRICHED["town"].str.upper().str.replace(" TOWN", "", regex=False).str.strip() == town_upper)
    )
    if fc:
        base_mask &= (_ENRICHED["floor_category"] == fc)
    if lease_range:
        base_mask &= (
            (_ENRICHED["remaining_lease_years"] >= lease_range[0]) &
            (_ENRICHED["remaining_lease_years"] < lease_range[1])
        )
    if scope == "block" and block:
        mask = base_mask & (_ENRICHED["block"].astype(str).str.upper().str.strip() == str(block).upper().strip())
    else:
        mask = base_mask

    sub = _ENRICHED[mask].sort_values("price_numeric").head(10)

    listings = []
    for rank, (_, r) in enumerate(sub.iterrows(), 1):
        listings.append({
            "rank": rank,
            "blk": str(r["block"]),
            "street": str(r["street"]),
            "flat_type": str(r["rooms"]),
            "storey_display": str(r["storey_range"]),
            "remaining_lease": str(r["remaining_lease"]),
            "asking_price": int(r["price_numeric"]),
            "lat": float(r["lat"]) if pd.notna(r.get("lat")) else None,
            "lon": float(r["lon"]) if pd.notna(r.get("lon")) else None,
            "url": str(r["url"]) if pd.notna(r.get("url")) else None,
            "listing_active": True,
            "match_reasons": [],
        })
    return listings


def build_real_data(postal, flat_type_ui, storey_bin, lease_bin):
    """
    Build the data dict consumed by valuation_dashboard().
    Returns None if postal code not found.
    """
    meta = _meta_from_postal(postal)
    if meta is None:
        return None

    town = str(meta.get("town", "")).replace(" Town", "").strip().upper()
    street_upper = str(meta["street"]).upper().strip()
    remaining_lease = str(meta.get("remaining_lease", "")) if meta.get("remaining_lease") else lease_bin

    # Always use the user's selected lease bin for prediction (midpoint of the range)
    _lease_bin_midpoints = {
        "Under 60 years": 55.0, "60-75 years": 67.5,
        "75-90 years": 82.5,    "Over 90 years": 95.0,
    }
    remaining_lease_years = _lease_bin_midpoints.get(lease_bin)

    # Try RF model first; fall back to historical percentile placeholder
    prediction = get_rf_prediction(meta["block"], street_upper, town, flat_type_ui, storey_bin, remaining_lease_years)
    model_note = None
    if prediction is None:
        prediction = get_placeholder_prediction(town, flat_type_ui, storey_bin)
        model_note = "Placeholder: historical percentile. RF model unavailable for this address."
    if prediction is None:
        prediction = (400000, 500000, 600000)  # absolute fallback
        model_note = "Placeholder: default range. No data available for this address."
    p15, _, p85 = prediction

    flat_lat = float(meta["lat"]) if pd.notna(meta.get("lat")) else None
    flat_lon = float(meta["lon"]) if pd.notna(meta.get("lon")) else None

    trends, trend_source = get_nearby_trends(flat_lat, flat_lon, flat_type_ui, storey_bin, street_upper)
    txns          = get_past_transactions(flat_lat, flat_lon, flat_type_ui, storey_bin, street_upper)
    listings_town  = get_current_listings(town, flat_type_ui, storey_bin=storey_bin, lease_bin=lease_bin, block=meta["block"], scope="town")
    listings_block = get_current_listings(town, flat_type_ui, storey_bin=storey_bin, lease_bin=lease_bin, block=meta["block"], scope="block")

    return {
        "address": f"Blk {meta['block']} {meta['street'].title()}",
        "postal_code": str(postal).strip(),
        "town": town.title(),
        "street_upper": street_upper,
        "lat": flat_lat or 1.3521,
        "lon": flat_lon or 103.8198,
        "flat_type": flat_type_ui,
        "storey_level_bin": storey_bin,
        "remaining_lease_bin": lease_bin,
        "remaining_lease": remaining_lease or lease_bin,
        "projection": {"p15": p15, "p85": p85},
        "graph_trend": trends,
        "_trend_source": trend_source,
        "past_transactions": txns,
        "current_listings": listings_town,
        "current_listings_block": listings_block,
        "_model_note": model_note,
    }

FLAT_TYPES = ["2-Room", "3-Room", "4-Room", "5-Room", "Executive"]
STOREY_BINS = [
    {"label": "Low (Floors 01\u201305)", "value": "Low"},
    {"label": "Medium (Floors 06\u201312)", "value": "Medium"},
    {"label": "High (Floors 13+)", "value": "High"},
]
LEASE_BINS = [
    {"label": "Under 60 years", "value": "Under 60 years"},
    {"label": "60\u201375 years", "value": "60-75 years"},
    {"label": "75\u201390 years", "value": "75-90 years"},
    {"label": "Over 90 years", "value": "Over 90 years"},
]

DEMO_LISTING_PRICE = 1258000  # Blk 87 Dawson Rd, QS — above RF p85=1,155,249 by ~$103k (+8.9%)


# ── Verdict logic ──────────────────────────────────────────────
def get_verdict(listing_price, p15, p85):
    if listing_price is None:
        return None
    if listing_price > p85:
        return "OVERPRICED"
    if listing_price < p15:
        return "GOOD DEAL"
    return "FAIR VALUE"


# ── Shared input form ──────────────────────────────────────────
def input_form(prefill=None, compact=False):
    pf = prefill or {}
    grid_cls = "val-input-grid-compact" if compact else "val-input-grid"
    return html.Div([
        html.Div(className=grid_cls, children=[
            html.Div(className="form-group", children=[
                html.Label("Postal Code", className="form-label"),
                dcc.Dropdown(id="val-postal",
                             options=_POSTAL_OPTIONS,
                             placeholder="Type to search postal code...",
                             clearable=True,
                             value=pf.get("postal_code") or None,
                             style={"fontSize": "14px"}),
            ]),
            html.Div(className="form-group", children=[
                html.Label("Flat Type", className="form-label"),
                dcc.Dropdown(id="val-flat-type",
                             options=[{"label": ft, "value": ft} for ft in FLAT_TYPES],
                             placeholder="Select flat type", clearable=False,
                             value=pf.get("flat_type"),
                             style={"fontSize": "14px"}),
            ]),
            html.Div(className="form-group", children=[
                html.Label("Storey Level", className="form-label"),
                dcc.Dropdown(id="val-storey-bin",
                             options=STOREY_BINS,
                             placeholder="Select storey", clearable=False,
                             value=pf.get("storey_level_bin"),
                             style={"fontSize": "14px"}),
            ]),
            html.Div(className="form-group", children=[
                html.Label("Remaining Lease", className="form-label"),
                dcc.Dropdown(id="val-lease-bin",
                             options=LEASE_BINS,
                             placeholder="Select lease range", clearable=False,
                             value=pf.get("remaining_lease_bin"),
                             style={"fontSize": "14px"}),
            ]),
            html.Div(className="form-group", children=[
                html.Label("Listed Price (optional)", className="form-label"),
                dcc.Input(id="val-listed", type="number", min=0,
                          placeholder="e.g. 638000", className="form-input",
                          value=pf.get("listed_price"),
                          debounce=True),
            ]),
            html.Div(className="form-group val-submit-col", children=[
                html.P(id="val-error",
                       style={"color": "var(--color-danger)", "fontSize": "12px",
                              "minHeight": "16px", "marginBottom": "4px"}),
                html.Button("Get Valuation", id="val-submit",
                            className="btn btn-primary val-submit-btn"),
            ]),
        ]),
    ])


# ── Market premium bar ─────────────────────────────────────────
def market_premium_bar(listing_price, p15, p85):
    if not listing_price:
        return html.P(
            "Enter a listed price above to see the market premium.",
            style={"fontSize": "12px", "color": "var(--color-text-muted)",
                   "fontStyle": "italic"},
        )
    midpoint = (p15 + p85) / 2
    pct = (listing_price - midpoint) / midpoint * 100
    verdict = get_verdict(listing_price, p15, p85)

    # Extended range: p15 - 1×span  …  p85 + 1×span
    span = p85 - p15
    bar_low  = p15 - span
    bar_high = p85 + span
    pos = max(2, min(98, (listing_price - bar_low) / (bar_high - bar_low) * 100))
    # Fair-value zone within the bar (grey region to highlight)
    fv_left  = max(0, min(100, (p15 - bar_low) / (bar_high - bar_low) * 100))
    fv_right = max(0, min(100, (p85 - bar_low) / (bar_high - bar_low) * 100))

    if verdict == "OVERPRICED":
        accent      = "#DC2626"
        pct_label   = f"+{pct:.1f}%"
        sub         = f"Listed ${listing_price - p85:,} above the top of the predicted range."
        # Colour only the overpriced segment (fv_right → pos) red; rest grey
        segments = [
            html.Div(style={"position": "absolute", "left": "0", "width": f"{fv_right}%",
                            "height": "100%", "background": "#D1D5DB", "borderRadius": "4px 0 0 4px"}),
            html.Div(style={"position": "absolute", "left": f"{fv_right}%",
                            "width": f"{max(0, pos - fv_right)}%",
                            "height": "100%", "background": accent}),
            html.Div(style={"position": "absolute", "left": f"{pos}%",
                            "width": f"{max(0, 100 - pos)}%",
                            "height": "100%", "background": "#D1D5DB", "borderRadius": "0 4px 4px 0"}),
        ]
    elif verdict == "GOOD DEAL":
        accent      = "#16A34A"
        pct_label   = f"{pct:.1f}%"
        sub         = f"Listed ${p15 - listing_price:,} below the bottom of the predicted range."
        # Colour only the underpriced segment (pos → fv_left) green; rest grey
        segments = [
            html.Div(style={"position": "absolute", "left": "0", "width": f"{pos}%",
                            "height": "100%", "background": "#D1D5DB", "borderRadius": "4px 0 0 4px"}),
            html.Div(style={"position": "absolute", "left": f"{pos}%",
                            "width": f"{max(0, fv_left - pos)}%",
                            "height": "100%", "background": accent}),
            html.Div(style={"position": "absolute", "left": f"{fv_left}%",
                            "width": f"{max(0, 100 - fv_left)}%",
                            "height": "100%", "background": "#D1D5DB", "borderRadius": "0 4px 4px 0"}),
        ]
    else:
        accent      = "#6B7280"
        pct_label   = f"{pct:+.1f}%"
        sub         = "Listed price falls within the predicted fair value range."
        segments = [
            html.Div(style={"position": "absolute", "left": "0", "width": "100%",
                            "height": "100%", "background": "#D1D5DB", "borderRadius": "4px"}),
        ]

    return html.Div([
        html.Div([
            html.Span("Market Premium",
                      style={"fontSize": "12px", "fontWeight": "600",
                             "color": "var(--color-text-secondary)"}),
            html.Span(pct_label,
                      style={"fontSize": "15px", "fontWeight": "700",
                             "color": accent}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "marginBottom": "8px"}),
        # Bar track — overflow visible so dots can poke above
        html.Div(style={"position": "relative", "height": "10px",
                        "marginBottom": "20px", "marginTop": "6px"}, children=[
            # Full grey base
            html.Div(style={"position": "absolute", "left": "0", "right": "0",
                            "top": "0", "height": "10px",
                            "background": "#D1D5DB", "borderRadius": "4px"}),
            # Coloured accent segment
            *segments,
            # p15 boundary dot
            html.Div(style={"position": "absolute", "left": f"{fv_left}%",
                            "top": "-4px", "width": "18px", "height": "18px",
                            "background": "white", "border": "2.5px solid #6B7280",
                            "borderRadius": "50%", "transform": "translateX(-50%)",
                            "zIndex": "3"}),
            # p85 boundary dot
            html.Div(style={"position": "absolute", "left": f"{fv_right}%",
                            "top": "-4px", "width": "18px", "height": "18px",
                            "background": "white", "border": "2.5px solid #6B7280",
                            "borderRadius": "50%", "transform": "translateX(-50%)",
                            "zIndex": "3"}),
            # Listing price marker pin (on top of dots)
            html.Div(style={"position": "absolute", "left": f"{pos}%",
                            "top": "-5px", "width": "5px", "height": "20px",
                            "background": accent, "borderRadius": "3px",
                            "transform": "translateX(-50%)", "zIndex": "4"}),
            # p15 label below
            html.Div(f"${p15:,}",
                     style={"position": "absolute", "left": f"{fv_left}%",
                            "top": "16px", "transform": "translateX(-50%)",
                            "fontSize": "10px", "color": "#6B7280",
                            "whiteSpace": "nowrap"}),
            # p85 label below
            html.Div(f"${p85:,}",
                     style={"position": "absolute", "left": f"{fv_right}%",
                            "top": "16px", "transform": "translateX(-50%)",
                            "fontSize": "10px", "color": "#6B7280",
                            "whiteSpace": "nowrap"}),
        ]),
        html.Div(className="premium-bar-labels", children=[
            html.Span("UNDERPRICED"),
            html.Span("FAIR VALUE"),
            html.Span("OVERPRICED"),
        ]),
        html.P(sub, style={"fontSize": "12px", "color": accent,
                           "marginTop": "6px", "marginBottom": "0"}),
    ])


# ── Trend chart ────────────────────────────────────────────────
def make_trend_chart(trend_data, listing_price=None, p15=None, p85=None):
    if not trend_data:
        return go.Figure()
    quarters = [t["quarter"] for t in trend_data]
    prices = [t["avg_price"] for t in trend_data]
    counts = [t["n_transactions"] for t in trend_data]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=quarters, y=prices, mode="lines+markers",
        line=dict(color="#1C4ED8", width=2),
        marker=dict(size=6, color="#1C4ED8"),
        customdata=[[c] for c in counts],
        hovertemplate="%{x} | Avg $%{y:,.0f} | %{customdata[0]} transactions<extra></extra>",
        showlegend=False,
    ))
    # Prominent dot on last point
    fig.add_trace(go.Scatter(
        x=[quarters[-1]], y=[prices[-1]], mode="markers",
        marker=dict(size=11, color="#1C4ED8", line=dict(color="white", width=2)),
        hoverinfo="skip", showlegend=False,
    ))
    if p15 is not None and p85 is not None:
        midpoint = (p15 + p85) // 2
        fig.add_hline(y=midpoint, line_dash="dash", line_color="#16A34A",
                      annotation_text=f"Predicted fair value: ${midpoint:,}",
                      annotation_position="top left",
                      annotation=dict(font_color="#16A34A", font_size=11))
    if listing_price:
        fig.add_hline(y=listing_price, line_dash="dash", line_color="#DC2626",
                      annotation_text=f"Your listing: ${listing_price:,}",
                      annotation_position="top right",
                      annotation=dict(font_color="#DC2626", font_size=11))
    fig.update_layout(
        margin={"t": 16, "b": 8, "l": 56, "r": 16},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, color="#9CA3AF", tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="#E5E7EB", color="#9CA3AF",
                   tickformat="$,.0f", tickfont=dict(size=10)),
        showlegend=False, height=220,
    )
    return fig


# ── Past transactions table (scrollable, sortable) ────────────
_TXN_COLS = [
    ("date",             "MONTH"),
    ("address",          "ADDRESS"),
    ("floor",            "STOREY"),
    ("flat_type",        "FLAT TYPE"),
    ("remaining_lease",  "LEASE"),
    ("price",            "PRICE"),
]


def _txn_sort_key(txn, col):
    """Return a sortable value for a transaction dict by column key."""
    import re as _re
    if col == "date":
        try:
            import datetime as _dt
            return _dt.datetime.strptime(txn.get("date", "Jan 2000"), "%b %Y")
        except Exception:
            return txn.get("date", "")
    elif col == "address":
        blk = txn.get("block", txn.get("blk", ""))
        return f"{txn.get('street', '')} {blk}".upper()
    elif col == "floor":
        m = _re.search(r"\d+", str(txn.get("floor", "0")))
        return int(m.group()) if m else 0
    elif col == "flat_type":
        return str(txn.get("flat_type", "")).upper()
    elif col == "remaining_lease":
        raw = str(txn.get("remaining_lease", "—"))
        if raw in ("—", "", "nan"):
            return -1.0
        m = _re.search(r"(\d+)\s+year", raw)
        mo = _re.search(r"(\d+)\s+month", raw)
        years = int(m.group(1)) if m else 0
        months = int(mo.group(1)) if mo else 0
        return years + months / 12.0
    elif col == "price":
        return txn.get("price", 0)
    return ""


def _txn_rows(txns, sort_col, sort_asc):
    if sort_col:
        txns = sorted(txns, key=lambda t: _txn_sort_key(t, sort_col), reverse=not sort_asc)
    rows = []
    for t in txns[:10]:
        rows.append(html.Tr([
            html.Td(t["date"],
                    style={"fontSize": "12px", "color": "var(--color-text-secondary)"}),
            html.Td(f"Blk {t.get('block', t.get('blk',''))} {t.get('street','').title()}",
                    style={"fontSize": "12px", "color": "var(--color-text-secondary)"}),
            html.Td(t["floor"]),
            html.Td(t["flat_type"]),
            html.Td(t.get("remaining_lease", "—"),
                    style={"fontSize": "12px", "color": "var(--color-text-secondary)"}),
            html.Td(f"${t['price']:,.0f}", className="td-price"),
        ]))
    return rows


def _sort_icon(col, sort_col, sort_asc):
    if col != sort_col:
        return "\u21c5"   # ⇅
    return "\u2191" if sort_asc else "\u2193"  # ↑ / ↓


def past_data_table(data, sort_col=None, sort_asc=True):
    txns = data.get("past_transactions", [])
    town = data.get("town", "this area")
    fallback = len(txns) < 3
    rows = _txn_rows(txns, sort_col, sort_asc)

    header_cells = [
        html.Th(
            html.Button(
                [label, html.Span(_sort_icon(col_key, sort_col, sort_asc),
                                  style={"marginLeft": "4px", "fontSize": "10px",
                                         "opacity": "0.7" if col_key != sort_col else "1"})],
                id={"type": "txn-sort-col", "col": col_key},
                n_clicks=0,
                style={"background": "none", "border": "none", "cursor": "pointer",
                       "fontWeight": "700", "fontSize": "11px", "letterSpacing": "0.05em",
                       "color": "var(--color-text-muted)" if col_key != sort_col else "var(--color-primary)",
                       "padding": "0", "display": "flex", "alignItems": "center",
                       "gap": "2px", "whiteSpace": "nowrap"},
            )
        )
        for col_key, label in _TXN_COLS
    ]

    return html.Div([
        html.Div(
            f"\u26a0\ufe0f Limited transactions on this street. "
            f"Showing town-level comparables for {town}.",
            className="fallback-notice",
        ) if fallback else None,
        html.Div(className="val-txn-scroll", children=[
            html.Table(className="data-table", children=[
                html.Thead(html.Tr(header_cells)),
                html.Tbody(id="val-txn-tbody", children=rows),
            ]),
        ]) if (rows or txns) else html.P("No recent transactions found.",
                                         style={"color": "var(--color-text-muted)",
                                                "fontSize": "13px"}),
    ])


# ── Lease warning ──────────────────────────────────────────────
def lease_warning(lease_bin):
    if lease_bin == "Under 60 years":
        return html.Div(className="lease-warning-red", children=[
            html.Strong("\U0001f6a8 Lease Warning: "),
            "Flats below 60 years remaining lease are not eligible for HDB loans. "
            "CPF usage will be restricted based on buyer\u2019s age. "
            "Seek financial advice before proceeding.",
        ])
    if lease_bin == "60-75 years":
        return html.Div(className="lease-warning-yellow", children=[
            html.Strong("\u26a0\ufe0f Lease Advisory: "),
            "Flats below 75 years remaining lease may face stricter bank loan "
            "conditions. Verify with your bank before proceeding.",
        ])
    return None


# ── LLM valuation insights ─────────────────────────────────────
def generate_valuation_insights(valuation_context: dict) -> list[str] | None:
    """
    Call HuggingFace Inference API and return a list of 2 insight strings,
    or None on failure.
    """
    hf_token = os.environ.get("HF_TOKEN", "")
    if not hf_token:
        return None

    postal         = valuation_context.get("postal", "")
    flat_type      = valuation_context.get("flat_type", "")
    storey         = valuation_context.get("storey", "")
    lease          = valuation_context.get("lease", "")
    asking_price   = valuation_context.get("asking_price", "N/A")
    fair_value     = valuation_context.get("fair_value", "")
    range_low      = valuation_context.get("range_low", "")
    range_high     = valuation_context.get("range_high", "")
    market_pos_pct = valuation_context.get("market_position_pct", "")
    recent_txns    = valuation_context.get("recent_transactions_text", "None")
    comparables    = valuation_context.get("comparables_text", "None")

    prompt = f"""You are a Singapore residential property analyst.

Based only on the structured valuation facts below, write exactly 2 short dashboard insights.
Each insight must:
- be no more than 18 words
- be factual and specific
- focus on what matters for a buyer
- not repeat the same point
- not use vague phrases like 'appears to' or 'could indicate'
- not invent information beyond the input

Return only 2 bullet points, each starting with "• ".

Valuation facts:
Subject flat:
- Postal: {postal}
- Flat type: {flat_type}
- Storey: {storey}
- Lease remaining: {lease}
- Asking price: {asking_price}
- Estimated fair value: {fair_value}
- Valuation range: {range_low} to {range_high}
- Market position: {market_pos_pct}% vs fair value

Recent transactions:
{recent_txns}

Comparables:
{comparables}"""

    try:
        resp = requests.post(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
            headers={"Authorization": f"Bearer {hf_token}"},
            json={"inputs": prompt, "parameters": {"max_new_tokens": 120, "temperature": 0.3}},
            timeout=15,
        )
        resp.raise_for_status()
        raw = resp.json()
        text = raw[0]["generated_text"] if isinstance(raw, list) else str(raw)
        # Strip the prompt echo if model returns it
        if prompt in text:
            text = text[text.index(prompt) + len(prompt):]
        lines = [l.strip() for l in text.strip().splitlines() if l.strip().startswith("•")]
        return lines[:2] if len(lines) >= 2 else None
    except Exception:
        return None


# ── Valuation insight text ─────────────────────────────────────
def valuation_insight(data, listing_price, verdict, p15, p85):
    flat_type = data.get("flat_type", "")
    town      = data.get("town", "this area")
    txns      = data.get("past_transactions", [])
    listings  = data.get("current_listings", [])
    midpoint  = (p15 + p85) // 2

    if not listing_price:
        return html.Div(className="val-insight-box", children=[
            html.P("\U0001f4ac VALUATION INSIGHT",
                   style={"fontSize": "11px", "fontWeight": "700",
                          "letterSpacing": "0.06em",
                          "color": "var(--color-text-muted)", "marginBottom": "6px"}),
            html.P("Enter a listed price above to receive your valuation insights.",
                   style={"fontSize": "13px", "color": "var(--color-text-muted)",
                          "fontStyle": "italic", "margin": "0"}),
        ])

    # Build context for LLM
    recent_txns_text = "\n".join(
        f"- Blk {t.get('block','')} {t.get('street','')} | {t['floor']} | {t['flat_type']} | ${t['price']:,} ({t['date']})"
        for t in txns[:5]
    ) or "No recent transactions."
    comparables_text = "\n".join(
        f"- Blk {l['blk']} {l['street']} | {l['storey_display']} | ${l['asking_price']:,}"
        for l in listings[:3]
    ) or "No comparables found."
    market_pos_pct = round((listing_price - midpoint) / midpoint * 100, 1)

    llm_lines = generate_valuation_insights({
        "postal": data.get("postal_code", ""),
        "flat_type": flat_type,
        "storey": data.get("storey_level_bin", ""),
        "lease": data.get("remaining_lease", ""),
        "asking_price": f"${listing_price:,}",
        "fair_value": f"${midpoint:,}",
        "range_low": f"${p15:,}",
        "range_high": f"${p85:,}",
        "market_position_pct": market_pos_pct,
        "recent_transactions_text": recent_txns_text,
        "comparables_text": comparables_text,
    })

    # Fallback if LLM unavailable
    if not llm_lines:
        if verdict == "OVERPRICED":
            over_pct = round((listing_price - p85) / p85 * 100, 1)
            llm_lines = [
                f"• Priced {over_pct}% above the predicted ceiling — room to negotiate.",
                f"• {len(txns)} comparable transactions found; check alternatives below.",
            ]
        elif verdict == "GOOD DEAL":
            under_pct = round((p15 - listing_price) / p15 * 100, 1)
            llm_lines = [
                f"• Priced {under_pct}% below the predicted floor — strong value signal.",
                f"• Well-priced {flat_type} in {town}; act quickly as demand is typically high.",
            ]
        else:
            pct_from_mid = round(abs(market_pos_pct), 1)
            llm_lines = [
                f"• Within fair value range, {pct_from_mid}% from the predicted midpoint.",
                f"• {len(txns)} recent comparables confirm market-aligned pricing in {town}.",
            ]

    ICONS = ["\U0001f4ca", "\U0001f3e0"]  # 📊 🏠
    insight_rows = [
        html.Div(style={"display": "flex", "alignItems": "flex-start",
                        "gap": "8px", "marginBottom": "8px"}, children=[
            html.Span(ICONS[i % 2],
                      style={"fontSize": "16px", "lineHeight": "1.4", "flexShrink": "0"}),
            html.P(line.lstrip("• ").strip(),
                   style={"fontSize": "13px", "lineHeight": "1.55",
                          "color": "var(--color-text-secondary)", "margin": "0"}),
        ])
        for i, line in enumerate(llm_lines)
    ]

    return html.Div(className="val-insight-box", children=[
        html.P("\U0001f4ac VALUATION INSIGHT",
               style={"fontSize": "11px", "fontWeight": "700",
                      "letterSpacing": "0.06em",
                      "color": "var(--color-text-muted)", "marginBottom": "10px"}),
        *insight_rows,
    ])


# ── Map layer config (palette: no blue — that's reserved for subject flat) ──
# Maki symbols via Scattermap (Plotly 6.x / MapLibre — no Mapbox token needed)
_LAYER_STYLE = {
    "mrt":        {"color": "#3D9FA8", "size": 16, "symbol": "rail",       "label": "MRT/LRT"},
    "school":     {"color": "#C8A800", "size": 14, "symbol": "school",     "label": "School"},
    "mall":       {"color": "#D45B8A", "size": 14, "symbol": "shop",       "label": "Mall"},
    "healthcare": {"color": "#8B5DB0", "size": 14, "symbol": "hospital",   "label": "Healthcare"},
    "hawker":     {"color": "#4A9EC2", "size": 14, "symbol": "restaurant", "label": "Hawker"},
    "park":       {"color": "#4AAF5A", "size": 14, "symbol": "park",       "label": "Park"},
}

def _nearby_amenity_pts(pts, user_lat, user_lon, radius_m=3000):
    """Filter a list of {lat, lon, name} to within radius_m of (user_lat, user_lon)."""
    R = 6_371_000
    out = []
    for p in pts:
        dlat = np.radians(p["lat"] - user_lat)
        dlon = np.radians(p["lon"] - user_lon)
        a = (np.sin(dlat / 2) ** 2
             + np.cos(np.radians(user_lat)) * np.cos(np.radians(p["lat"]))
             * np.sin(dlon / 2) ** 2)
        if R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)) <= radius_m:
            out.append(p)
    return out


def make_listings_map(user_lat, user_lon, user_address, listings,
                       past_txns=None, active_layers=None, amenity_pins=None):
    """
    Build the interactive map using Scattermap (Plotly 6.x / MapLibre).
    Maki symbols render correctly without a Mapbox token on carto-positron.
    active_layers: set of 'current', 'past', 'mrt', 'school', 'mall',
                   'healthcare', 'hawker', 'park'
    """
    if active_layers is None:
        active_layers = {"current", "mrt", "school", "mall", "healthcare", "hawker", "park"}
    active_layers = set(active_layers)

    fig = go.Figure()

    # ── Amenity layers (Maki symbols via Scattermap) ────────────
    if amenity_pins:
        for atype, style in _LAYER_STYLE.items():
            if atype not in active_layers:
                continue
            pts = _nearby_amenity_pts(amenity_pins.get(atype, []), user_lat, user_lon)
            if not pts:
                continue
            fig.add_trace(go.Scattermap(
                lat=[p["lat"] for p in pts],
                lon=[p["lon"] for p in pts],
                mode="markers",
                marker=go.scattermap.Marker(
                    size=style["size"],
                    color=style["color"],
                    symbol=style["symbol"],
                    opacity=0.9,
                ),
                hovertext=[f"<b>{style['label']}</b><br>{p['name']}" for p in pts],
                hoverinfo="text",
                name=style["label"],
                showlegend=False,
            ))

    # ── Past transactions (grey circles) ───────────────────────
    if "past" in active_layers and past_txns:
        valid_past = [t for t in past_txns if t.get("lat") and t.get("lon")]
        if valid_past:
            fig.add_trace(go.Scattermap(
                lat=[t["lat"] for t in valid_past],
                lon=[t["lon"] for t in valid_past],
                mode="markers",
                marker=go.scattermap.Marker(size=9, color="#9CA3AF", opacity=0.7),
                hovertext=[
                    f"<b>Past: Blk {t['block']} {t['street']}</b><br>"
                    f"{t['floor']} · {t['flat_type']} · ${t['price']:,} ({t['date']})"
                    for t in valid_past
                ],
                hoverinfo="text",
                name="Past transactions",
                showlegend=False,
            ))

    # ── Current listings (green numbered circles) ──────────────
    if "current" in active_layers:
        for lst in [l for l in listings if l.get("lat") is not None]:
            fig.add_trace(go.Scattermap(
                lat=[lst["lat"]], lon=[lst["lon"]], mode="markers+text",
                marker=go.scattermap.Marker(size=16, color="#16A34A"),
                text=[str(lst["rank"])],
                textfont=dict(size=9, color="white"),
                hovertext=[f"<b>#{lst['rank']} Blk {lst['blk']} {lst['street']}</b><br>"
                           f"Asking: ${lst['asking_price']:,}"],
                hoverinfo="text",
                showlegend=False,
            ))

    # ── Subject flat (always shown, red circle) ─────────────────
    fig.add_trace(go.Scattermap(
        lat=[user_lat], lon=[user_lon], mode="markers+text",
        marker=go.scattermap.Marker(size=22, color="#DC2626", symbol="circle"),
        text=["Your flat"],
        textposition="bottom center",
        textfont=dict(size=11, color="#DC2626"),
        hovertext=[f"<b>Your flat</b><br>{user_address}"],
        hoverinfo="text",
        showlegend=False,
    ))

    fig.update_layout(
        map=dict(style="carto-positron", zoom=14,
                 center={"lat": user_lat, "lon": user_lon}),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


# ── Listing cards ──────────────────────────────────────────────
def listing_cards(listings, p85, scope="town"):
    sub_label = (
        "Same block \u00b7 same flat type \u00b7 cheapest first"
        if scope == "block" else
        "Same town \u00b7 same flat type \u00b7 cheapest first"
    )
    cards = []
    for lst in listings:
        signal = (
            html.Span("\u26a0\ufe0f Above fair value range",
                      style={"color": "var(--color-danger)", "fontSize": "11px",
                             "fontWeight": "600"})
            if lst["asking_price"] > p85 else
            html.Span("\u2713 Within fair value range",
                      style={"color": "var(--color-success)", "fontSize": "11px",
                             "fontWeight": "600"})
        )
        url = lst.get("url")
        address_el = (
            html.A(f"Blk {lst['blk']} {lst['street']}",
                   href=url, target="_blank",
                   style={"fontWeight": "700", "fontSize": "14px",
                          "color": "var(--color-primary)",
                          "textDecoration": "none", "marginBottom": "3px",
                          "display": "block"})
            if url else
            html.Div(f"Blk {lst['blk']} {lst['street']}",
                     style={"fontWeight": "700", "fontSize": "14px",
                            "color": "var(--color-text-primary)",
                            "marginBottom": "3px"})
        )
        cards.append(html.Div(
            className="listing-card",
            children=[
                html.Div(className="listing-card-left", children=[
                    html.Div(str(lst["rank"]), className="listing-card-rank-num"),
                ]),
                html.Div(className="listing-card-body", children=[
                    address_el,
                    html.Div([
                        html.Span(lst["flat_type"],
                                  style={"fontSize": "12px",
                                         "color": "var(--color-text-secondary)"}),
                        html.Span(" \u00b7 ",
                                  style={"color": "var(--color-text-muted)"}),
                        html.Span(lst["storey_display"],
                                  style={"fontSize": "12px",
                                         "color": "var(--color-text-secondary)"}),
                        html.Span(" \u00b7 ",
                                  style={"color": "var(--color-text-muted)"}),
                        html.Span(lst["remaining_lease"],
                                  style={"fontSize": "12px",
                                         "color": "var(--color-text-secondary)"}),
                    ]),
                ]),
                html.Div(className="listing-card-price", children=[
                    html.Div(f"${lst['asking_price']:,}",
                             style={"fontFamily": "var(--mono)", "fontWeight": "700",
                                    "fontSize": "16px",
                                    "color": "var(--color-text-primary)",
                                    "whiteSpace": "nowrap"}),
                    signal,
                ]),
            ],
        ))

    # Scope toggle buttons
    scope_toggle = html.Div(style={"display": "flex", "gap": "6px", "marginBottom": "0"}, children=[
        html.Button("Same Block", id="val-scope-block",
                    className="scope-btn" + (" scope-btn-active" if scope == "block" else ""),
                    n_clicks=0),
        html.Button("Same Town", id="val-scope-town",
                    className="scope-btn" + (" scope-btn-active" if scope == "town" else ""),
                    n_clicks=0),
    ])

    return html.Div(className="listings-section", children=[
        html.Div(className="listings-header", children=[
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "alignItems": "center", "marginBottom": "4px"}, children=[
                html.P("CURRENT MARKET ALTERNATIVES", className="listings-header-title",
                       style={"margin": "0"}),
                scope_toggle,
            ]),
            html.P(sub_label, className="listings-header-sub"),
        ]),
        html.Div(id="val-listings-body", children=[
            html.Div(className="listings-scroll", children=cards) if cards else
            html.P("No current listings found.",
                   style={"padding": "16px", "color": "var(--color-text-muted)",
                          "fontSize": "13px"}),
        ]),
    ])


# ── Top-left panel ─────────────────────────────────────────────
def top_left_panel(data, listing_price=None):
    p15 = data["projection"]["p15"]
    p85 = data["projection"]["p85"]
    midpoint = (p15 + p85) // 2
    verdict = get_verdict(listing_price, p15, p85)
    if verdict == "OVERPRICED":
        badge = html.Div("\u26a0\ufe0f OVERPRICED",
                         className="verdict-badge verdict-overpriced")
        listed_color = "var(--color-danger)"
    elif verdict == "GOOD DEAL":
        badge = html.Div("\U0001f7e2 GOOD DEAL",
                         className="verdict-badge verdict-gooddeal")
        listed_color = "var(--color-success)"
    elif verdict == "FAIR VALUE":
        badge = html.Div("\u2705 FAIR VALUE",
                         className="verdict-badge verdict-fairvalue")
        listed_color = "var(--color-text-secondary)"
    else:
        badge = None
        listed_color = None

    warn = lease_warning(data.get("remaining_lease_bin", ""))

    return html.Div(className="val-top-left card", children=[
        # Header row
        html.Div([
            html.P("ESTIMATED CURRENT PRICE",
                   style={"fontSize": "13px", "fontWeight": "800",
                          "letterSpacing": "0.07em", "textTransform": "uppercase",
                          "color": "var(--color-text-secondary)", "margin": "0"}),
            badge,
        ], style={"display": "flex", "alignItems": "center",
                  "justifyContent": "space-between", "marginBottom": "12px"}),

        # Big predicted price
        html.Div(f"${midpoint:,}",
                 style={"fontSize": "40px", "fontWeight": "800",
                        "color": "var(--color-text-primary)",
                        "fontFamily": "var(--mono)", "lineHeight": "1.1",
                        "marginBottom": "4px"}),
        html.P(f"Range: ${p15:,} \u2014 ${p85:,}",
               style={"fontSize": "13px", "color": "var(--color-text-secondary)",
                      "marginBottom": "4px"}),
        # Listed price
        html.P(f"Listed at ${listing_price:,}",
               style={"fontSize": "14px", "fontWeight": "600",
                      "color": listed_color, "marginBottom": "12px"}
               ) if listing_price else None,

        # Market premium bar
        market_premium_bar(listing_price, p15, p85),

        # Placeholder model notice (shown when RF model unavailable for this address)
        html.Div(
            "⚠ Price range based on historical percentiles. "
            "RF model unavailable for this address.",
            style={"fontSize": "11px", "color": "var(--color-text-muted)",
                   "fontStyle": "italic", "marginTop": "8px"}
        ) if data.get("_model_note") else None,

        html.Div(className="divider", style={"margin": "16px 0"}),

        # Lease warning
        html.Div(warn, style={"marginBottom": "12px"}) if warn else None,

        # Metadata grid
        html.Div(className="flat-detail-grid", children=[
            html.Div([html.P("ADDRESS", className="flat-detail-label"),
                      html.P(data["address"], className="flat-detail-val")]),
            html.Div([html.P("POSTAL CODE", className="flat-detail-label"),
                      html.P(data["postal_code"], className="flat-detail-val")]),
            html.Div([html.P("FLAT TYPE", className="flat-detail-label"),
                      html.P(data["flat_type"], className="flat-detail-val")]),
            html.Div([html.P("REMAINING LEASE", className="flat-detail-label"),
                      html.P(data["remaining_lease"], className="flat-detail-val")]),
            html.Div([html.P("STOREY BIN", className="flat-detail-label"),
                      html.P(data["storey_level_bin"], className="flat-detail-val")]),
            html.Div([html.P("TOWN", className="flat-detail-label"),
                      html.P(data["town"], className="flat-detail-val")]),
        ]),

        html.Div(className="divider", style={"margin": "16px 0"}),

        # Valuation insight
        valuation_insight(data, listing_price, verdict, p15, p85),
    ])


# ── Top-right panel (chart + scrollable table, no tabs) ────────
def top_right_panel(data, listing_price=None):
    p15 = data["projection"]["p15"]
    p85 = data["projection"]["p85"]
    trend_source = data.get("_trend_source", "same street · same flat type")
    return html.Div(className="val-top-right card", style={"padding": "0", "overflow": "hidden"}, children=[
        # Dark header
        html.Div(style={
            "background": "var(--color-navy, #1E2A3B)",
            "padding": "14px 20px",
            "borderRadius": "var(--radius) var(--radius) 0 0",
        }, children=[
            html.H3("HISTORICAL PRICE TRENDS",
                    style={"fontSize": "13px", "fontWeight": "800",
                           "letterSpacing": "0.07em",
                           "color": "#FFFFFF", "margin": "0 0 2px 0"}),
            html.P(trend_source,
                   style={"fontSize": "12px", "color": "rgba(255,255,255,0.6)",
                          "margin": "0"}),
        ]),
        html.Div(style={"padding": "16px 20px"}, children=[
            # Chart on top
            dcc.Graph(
                figure=make_trend_chart(data.get("graph_trend", []),
                                        listing_price=listing_price,
                                        p15=p15, p85=p85),
                config={"displayModeBar": False},
                style={"height": "220px"},
            ),
            html.P(
                f"Average transaction price \u2014 {trend_source}",
                style={"fontSize": "11px", "color": "var(--color-text-muted)",
                       "textAlign": "center", "marginTop": "2px", "fontStyle": "italic",
                       "marginBottom": "16px"},
            ),
            # Past transactions table below (scrollable)
            html.H3("Past Transactions",
                    style={"fontSize": "15px", "fontWeight": "700",
                           "color": "var(--color-text-primary)",
                           "paddingTop": "12px", "marginBottom": "8px",
                           "borderTop": "1px solid var(--color-border)"}),
            past_data_table(data),
        ]),
    ])


# ── Layer toggle config ────────────────────────────────────────
_MAP_LAYERS = [
    ("current",    "Current Listings", "#16A34A"),
    ("past",       "Past Transactions","#9CA3AF"),
    ("mrt",        "MRT/LRT",          "#3D9FA8"),
    ("school",     "Schools",          "#C8A800"),
    ("mall",       "Malls",            "#D45B8A"),
    ("healthcare", "Healthcare",       "#8B5DB0"),
    ("hawker",     "Hawker Centres",   "#4A9EC2"),
    ("park",       "Parks",            "#4AAF5A"),
]
_DEFAULT_LAYERS = {"current", "past", "mrt", "school", "mall", "healthcare", "hawker", "park"}


# Icon/emoji for each layer used in the legend
_LAYER_EMOJI = {
    "current":    "\U0001f7e2",   # 🟢
    "past":       "\u26aa",       # ⚪
    "mrt":        "\U0001f687",   # 🚇
    "school":     "\U0001f393",   # 🎓
    "mall":       "\U0001f6cd\ufe0f", # 🛍️
    "healthcare": "\U0001f3e5",   # 🏥
    "hawker":     "\U0001f35c",   # 🍜
    "park":       "\U0001f333",   # 🌳
}

def layer_toggles(active_layers):
    """Icon + label toggle buttons — active = coloured bg, inactive = white bg with border."""
    btns = []
    for key, label, color in _MAP_LAYERS:
        emoji = _LAYER_EMOJI.get(key, "\u25cf")
        is_active = key in active_layers
        btns.append(html.Button(
            children=[
                html.Span(emoji, style={"fontSize": "13px", "lineHeight": "1",
                                        "marginRight": "5px"}),
                html.Span(label, style={"fontSize": "11px", "fontWeight": "600"}),
            ],
            id={"type": "map-layer-btn", "layer": key},
            n_clicks=0,
            style={
                "display": "flex", "alignItems": "center",
                "padding": "4px 10px", "borderRadius": "20px",
                "border": f"1.5px solid {color}",
                "cursor": "pointer",
                "background": color if is_active else "white",
                "color": "white" if is_active else color,
                "transition": "all 0.15s",
                "fontFamily": "var(--sans)",
            },
        ))
    return html.Div(style={
        "display": "flex", "flexWrap": "wrap", "gap": "6px",
        "marginBottom": "10px",
    }, children=btns)


# ── Bottom-left panel: map ─────────────────────────────────────
def bottom_left_panel(data):
    listings = data.get("current_listings", [])
    past_txns = data.get("past_transactions", [])
    town = str(data.get("town", "")).upper()
    title = f"INTERACTIVE MAP — {town}" if town else "INTERACTIVE MAP"

    map_fig = make_listings_map(
        data["lat"], data["lon"], data["address"],
        listings, past_txns=past_txns,
        active_layers=_DEFAULT_LAYERS,
        amenity_pins=_AMENITY_PINS,
    )

    return html.Div(className="card val-map-card", children=[
        html.P(title, className="val-panel-label", style={"marginBottom": "8px"}),
        layer_toggles(_DEFAULT_LAYERS),
        dcc.Graph(
            id="val-map-graph",
            figure=map_fig,
            config={"displayModeBar": False, "scrollZoom": True},
            style={"height": "360px"},
        ),
        dcc.Store(id="val-map-layers", data=list(_DEFAULT_LAYERS)),
    ])


# ── Bottom-right panel: scrollable listings ────────────────────
def bottom_right_panel(data, p85):
    return listing_cards(data.get("current_listings", []), p85, scope="town")


# ── Overpriced banner (amber style) ───────────────────────────
def overpriced_banner():
    return html.Div(className="overpriced-banner", children=[
        html.P("\u26a0\ufe0f  Overpriced? Explore potential alternatives below",
               className="overpriced-banner-title"),
        html.P([
            "Alternatives are matched on flat type, storey level, and remaining lease \u2014 "
            "sorted by price. Some may be in nearby towns. "
            "Note their postal codes and use the ",
            dcc.Link("Amenities Comparison", href="/amenities-comparison",
                     style={"color": "inherit", "fontWeight": "600",
                            "textDecoration": "underline"}),
            " tool to weigh location trade-offs before deciding.",
        ], className="overpriced-banner-sub"),
    ])


# ── Valuation dashboard ────────────────────────────────────────
def valuation_dashboard(data, listing_price=None):
    p15 = data["projection"]["p15"]
    p85 = data["projection"]["p85"]
    prefill_data = dict(data, listed_price=listing_price)

    children = [
        # Hidden data store for callbacks
        dcc.Store(id="val-data-store", data={
            "lat":                    data["lat"],
            "lon":                    data["lon"],
            "address":                data["address"],
            "town":                   data.get("town", ""),
            "past_transactions":      data.get("past_transactions", []),
            "current_listings":       data.get("current_listings", []),
            "current_listings_block": data.get("current_listings_block", []),
            "p85":                    p85,
        }),
        dcc.Store(id="val-txn-sort", data={"col": None, "asc": True}),
        html.Div(className="val-compact-bar", children=[
            html.Div(className="val-compact-inner", children=[
                input_form(prefill=prefill_data, compact=True),
            ]),
        ]),
        html.Button("Load Demo", id="val-demo",
                    className="btn btn-secondary val-demo-btn",
                    n_clicks=0,
                    style={"display": "none"}),  # hidden in compact bar — accessible via pre-search
        html.Div(className="val-top-row val-content-area", children=[
            top_left_panel(data, listing_price),
            top_right_panel(data, listing_price),
        ]),
    ]

    if get_verdict(listing_price, p15, p85) == "OVERPRICED":
        children.append(
            html.Div(overpriced_banner(),
                     className="val-overpriced-banner-wrap val-content-area"))

    children.append(
        html.Div(className="val-bottom-row val-content-area", children=[
            bottom_left_panel(data),
            bottom_right_panel(data, p85),
        ]))

    return children


# ── Pre-search layout ──────────────────────────────────────────
def pre_search_layout(prefill=None):
    return html.Div(className="valuation-pre", children=[
        html.Div(className="valuation-pre-inner", children=[
            html.H1("How much is this flat worth?", className="valuation-pre-title"),
            html.P(
                "Enter a postal code and flat details to get a data-driven "
                "price projection.",
                className="valuation-pre-sub",
            ),
            html.Div(className="valuation-form-card", children=[
                input_form(prefill=prefill),
                html.Div(style={"display": "flex", "gap": "8px", "marginTop": "8px"}, children=[
                    html.Button("Load Demo", id="val-demo",
                                className="btn btn-secondary val-demo-btn",
                                n_clicks=0,
                                title="Load a real overpriced listing in Queenstown as a demo"),
                ]),
            ]),
        ])
    ])


# ── Layout (entry point) ───────────────────────────────────────
layout = html.Div(className="page-wrapper", id="val-page-root", children=[
    pre_search_layout()
])


# ── Callbacks ──────────────────────────────────────────────────
@callback(
    Output("val-page-root", "children"),
    Output("val-error", "children", allow_duplicate=True),
    Input("val-submit", "n_clicks"),
    Input("val-demo", "n_clicks"),
    State("val-postal", "value"),
    State("val-flat-type", "value"),
    State("val-storey-bin", "value"),
    State("val-lease-bin", "value"),
    State("val-listed", "value"),
    prevent_initial_call=True,
)
def run_valuation(n_submit, n_demo, postal, flat_type, storey_bin, lease_bin, listed):  # noqa: ARG001
    # Demo short-circuit: bypass form validation and use pre-built DEMO data
    if ctx.triggered_id == "val-demo":
        return valuation_dashboard(DEMO, listing_price=DEMO_LISTING_PRICE), ""

    if not postal:
        return no_update, "Please select a postal code."
    if not flat_type:
        return no_update, "Please select a flat type."
    if not storey_bin:
        return no_update, "Please select a storey level."
    if not lease_bin:
        return no_update, "Please select a remaining lease range."

    listed_int = int(listed) if listed else None
    data = build_real_data(postal.strip(), flat_type, storey_bin, lease_bin)
    if data is None:
        return no_update, "Postal code not found in our database."
    return valuation_dashboard(data, listing_price=listed_int), ""


@callback(
    Output("val-flat-type", "value"),
    Output("val-flat-type", "options"),
    Output("val-storey-bin", "value"),
    Output("val-lease-bin", "value"),
    Input("val-postal", "value"),
    State("val-flat-type", "value"),
    State("val-storey-bin", "value"),
    State("val-lease-bin", "value"),
    prevent_initial_call=True,
)
def autofill_from_postal(postal, current_ft, current_storey, current_lease):
    all_ft_options = [{"label": ft, "value": ft} for ft in FLAT_TYPES]
    if not postal:
        return None, all_ft_options, None, None
    meta = _POSTAL_META.get(str(postal).zfill(6))
    if not meta:
        return None, all_ft_options, None, None
    # Only autofill fields the user hasn't already set
    return (
        meta["flat_type"] if not current_ft else current_ft,
        all_ft_options,
        meta["storey_level_bin"] if not current_storey else current_storey,
        meta["remaining_lease_bin"] if not current_lease else current_lease,
    )


@callback(
    Output("val-page-root", "children", allow_duplicate=True),
    Input("url", "pathname"),
    State("valuation-prefill", "data"),
    prevent_initial_call=True,
)
def prefill_from_store(pathname, prefill_data):
    if pathname == "/flat-valuation" and prefill_data:
        return pre_search_layout(prefill_data)
    return no_update


# ── Map layer toggle callback ──────────────────────────────────
@callback(
    Output("val-map-layers", "data"),
    Output("val-map-graph", "figure"),
    Input({"type": "map-layer-btn", "layer": dash.ALL}, "n_clicks"),
    State("val-map-layers", "data"),
    State("val-data-store", "data"),
    prevent_initial_call=True,
)
def toggle_map_layer(_n, active_layers, store):  # noqa: ARG001
    from dash import ctx
    if not ctx.triggered_id or store is None:
        return no_update, no_update
    triggered_layer = ctx.triggered_id["layer"]
    active = set(active_layers or list(_DEFAULT_LAYERS))
    if triggered_layer in active:
        active.discard(triggered_layer)
    else:
        active.add(triggered_layer)
    fig = make_listings_map(
        store["lat"], store["lon"], store["address"],
        store.get("current_listings", []),
        past_txns=store.get("past_transactions", []),
        active_layers=active,
        amenity_pins=_AMENITY_PINS,
    )
    return list(active), fig


# ── Listing scope toggle callback ──────────────────────────────
@callback(
    Output("val-listings-body", "children"),
    Input("val-scope-block", "n_clicks"),
    Input("val-scope-town", "n_clicks"),
    State("val-data-store", "data"),
    prevent_initial_call=True,
)
def toggle_listing_scope(_n_block, _n_town, store):  # noqa: ARG001
    from dash import ctx
    if store is None:
        return no_update
    trig = ctx.triggered_id
    scope = "block" if trig == "val-scope-block" else "town"
    p85 = store.get("p85", 600000)
    listings = (
        store.get("current_listings_block", [])
        if scope == "block" else
        store.get("current_listings", [])
    )
    # Re-render just the cards list (not the full listing_cards wrapper)
    return (
        html.Div(className="listings-scroll", children=[
            _listing_card(lst, p85) for lst in listings
        ]) if listings else
        html.P("No current listings found.",
               style={"padding": "16px", "color": "var(--color-text-muted)",
                      "fontSize": "13px"})
    )


# ── Past transactions sort callback ───────────────────────────
@callback(
    Output("val-txn-sort",  "data"),
    Output("val-txn-tbody", "children"),
    Input({"type": "txn-sort-col", "col": dash.ALL}, "n_clicks"),
    State("val-txn-sort",  "data"),
    State("val-data-store", "data"),
    prevent_initial_call=True,
)
def sort_past_transactions(_n, sort_state, store):
    if not ctx.triggered_id or store is None:
        return no_update, no_update
    col = ctx.triggered_id["col"]
    prev_col = sort_state.get("col")
    prev_asc = sort_state.get("asc", True)
    if col == prev_col:
        new_asc = not prev_asc
    else:
        new_asc = True
    txns = store.get("past_transactions", [])
    rows = _txn_rows(txns, col, new_asc)
    return {"col": col, "asc": new_asc}, rows


def _listing_card(lst, p85):
    signal = (
        html.Span("\u26a0\ufe0f Above fair value range",
                  style={"color": "var(--color-danger)", "fontSize": "11px", "fontWeight": "600"})
        if lst["asking_price"] > p85 else
        html.Span("\u2713 Within fair value range",
                  style={"color": "var(--color-success)", "fontSize": "11px", "fontWeight": "600"})
    )
    url = lst.get("url")
    address_el = (
        html.A(f"Blk {lst['blk']} {lst['street']}", href=url, target="_blank",
               style={"fontWeight": "700", "fontSize": "14px", "color": "var(--color-primary)",
                      "textDecoration": "none", "marginBottom": "3px", "display": "block"})
        if url else
        html.Div(f"Blk {lst['blk']} {lst['street']}",
                 style={"fontWeight": "700", "fontSize": "14px",
                        "color": "var(--color-text-primary)", "marginBottom": "3px"})
    )
    return html.Div(className="listing-card", children=[
        html.Div(className="listing-card-left", children=[
            html.Div(str(lst["rank"]), className="listing-card-rank-num"),
        ]),
        html.Div(className="listing-card-body", children=[
            address_el,
            html.Div([
                html.Span(lst["flat_type"],
                          style={"fontSize": "12px", "color": "var(--color-text-secondary)"}),
                html.Span(" \u00b7 ", style={"color": "var(--color-text-muted)"}),
                html.Span(lst["storey_display"],
                          style={"fontSize": "12px", "color": "var(--color-text-secondary)"}),
                html.Span(" \u00b7 ", style={"color": "var(--color-text-muted)"}),
                html.Span(lst["remaining_lease"],
                          style={"fontSize": "12px", "color": "var(--color-text-secondary)"}),
            ]),
        ]),
        html.Div(className="listing-card-price", children=[
            html.Div(f"${lst['asking_price']:,}",
                     style={"fontFamily": "var(--mono)", "fontWeight": "700", "fontSize": "16px",
                            "color": "var(--color-text-primary)", "whiteSpace": "nowrap"}),
            signal,
        ]),
    ])
