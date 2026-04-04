import json, os
import requests
import pandas as pd
import numpy as np
import dash
from dash import html, dcc, callback, Output, Input, State, no_update
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
    """Load malls, schools, healthcare into a dict of lists {lat, lon, name, type}."""
    pins = {"mall": [], "school": [], "healthcare": []}

    # Malls: data/shoppingmalls.csv
    mall_path = os.path.join(_DATA, "shoppingmalls.csv")
    if os.path.exists(mall_path):
        mdf = pd.read_csv(mall_path)
        for _, r in mdf.dropna(subset=["lat", "lon"]).iterrows():
            pins["mall"].append({"lat": float(r["lat"]), "lon": float(r["lon"]),
                                  "name": str(r.get("name", "Mall"))})

    # Schools: data/school_geocode_cache.json — keyed by postal, value {lat, lon}
    school_path = os.path.join(_DATA, "school_geocode_cache.json")
    if os.path.exists(school_path):
        with open(school_path, encoding="utf-8") as f:
            scache = json.load(f)
        for name, v in scache.items():
            if isinstance(v, dict) and v.get("lat") and v.get("lon"):
                pins["school"].append({"lat": float(v["lat"]), "lon": float(v["lon"]),
                                        "name": str(name)})

    # Healthcare: data/healthcare_geocode_cache.json — keyed by postal, value {lat, lon}
    health_path = os.path.join(_DATA, "healthcare_geocode_cache.json")
    if os.path.exists(health_path):
        with open(health_path, encoding="utf-8") as f:
            hcache = json.load(f)
        for postal, v in hcache.items():
            if isinstance(v, dict) and v.get("lat") and v.get("lon"):
                pins["healthcare"].append({"lat": float(v["lat"]), "lon": float(v["lon"]),
                                            "name": f"Clinic/Hospital ({postal})"})
    return pins

_AMENITY_PINS = _load_amenity_pins()

# ── OLS model loaded once at startup ──────────────────────────
_OLS_MODEL  = None
_OLS_SCALER = None
_OLS_COLS   = None

try:
    import joblib
    import statsmodels.api as _sm

    _MODEL_DIR = os.path.join(_BACKEND, "price_model")
    if all(os.path.exists(os.path.join(_MODEL_DIR, f))
           for f in ("ols_model.pkl", "ols_scaler.joblib", "ols_feature_cols.json")):
        _OLS_MODEL  = _sm.load(os.path.join(_MODEL_DIR, "ols_model.pkl"))
        _OLS_SCALER = joblib.load(os.path.join(_MODEL_DIR, "ols_scaler.joblib"))
        with open(os.path.join(_MODEL_DIR, "ols_feature_cols.json")) as _f:
            _OLS_COLS = json.load(_f)
except Exception as _e:
    print(f"[flat_valuation] OLS model not loaded: {_e}")

# Amenity lookup: (block_upper, street_upper) → amenity feature dict
# Built from pipeline CSVs (2026 wins over pre-2026 on duplicate block+street)
_OLS_CONTINUOUS = [
    "remaining_lease_years", "nearest_train_dist_m", "dist_nearest_hawker_m",
    "dist_nearest_primary_m", "num_primary_1km", "dist_nearest_park_m",
    "dist_nearest_sportsg_m", "dist_nearest_mall_m", "dist_nearest_healthcare_m",
    "num_parks_1km",
]

def _build_amenity_lookup():
    lookup = {}
    for path in (
        os.path.join(_MERGED, "[FINAL]hdb_with_amenities_macro_pre2026.csv"),
        os.path.join(_MERGED, "[FINAL]hdb_with_amenities_macro_2026.csv"),
    ):
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, usecols=["block", "street_name", "town"] + _OLS_CONTINUOUS,
                         low_memory=False)
        df["_bk"] = df["block"].astype(str).str.upper().str.strip()
        df["_st"] = df["street_name"].astype(str).str.upper().str.strip()
        for _, r in df.drop_duplicates(subset=["_bk", "_st"], keep="last").iterrows():
            lookup[(r["_bk"], r["_st"])] = r.to_dict()
    return lookup

_AMENITY_LOOKUP = _build_amenity_lookup()


def get_ols_prediction(block, street_upper, town, flat_type_ui, floor_category, remaining_lease_years):
    """
    Run OLS model using pre-computed amenity features from pipeline CSVs.
    Returns (p_low, median, p_high) at 80% PI, or None if unavailable.
    """
    if _OLS_MODEL is None or remaining_lease_years is None:
        return None

    amenity_row = _AMENITY_LOOKUP.get(
        (str(block).upper().strip(), street_upper)
    )
    if amenity_row is None:
        return None

    ft = _FT_MAP.get(flat_type_ui, flat_type_ui.upper())
    fc = _STOREY_MAP.get(floor_category, floor_category)

    try:
        features = {c: amenity_row[c] for c in _OLS_CONTINUOUS}
        features["remaining_lease_years"] = remaining_lease_years

        cont_vals   = np.array([[features[c] for c in _OLS_CONTINUOUS]])
        cont_scaled = _OLS_SCALER.transform(cont_vals)
        cont_df     = pd.DataFrame(cont_scaled, columns=_OLS_CONTINUOUS)

        dummy_cols = [c for c in _OLS_COLS if c not in _OLS_CONTINUOUS]
        row = {col: 0 for col in dummy_cols}
        flat_col  = f"flat_type_{ft}"
        town_col  = f"town_{str(town).upper().strip().replace(' TOWN', '')}"
        floor_col = f"floor_category_{fc}"
        if flat_col  in row: row[flat_col]  = 1
        if town_col  in row: row[town_col]  = 1
        if floor_col in row: row[floor_col] = 1

        import statsmodels.api as sm
        X_new       = pd.concat([cont_df, pd.DataFrame([row])], axis=1)[_OLS_COLS]
        X_new_const = sm.add_constant(X_new, has_constant="add")
        pred  = _OLS_MODEL.get_prediction(X_new_const)
        frame = pred.summary_frame(alpha=0.2)  # 80% PI
        return (
            int(np.exp(frame["obs_ci_lower"].values[0])),
            int(np.exp(frame["mean"].values[0])),
            int(np.exp(frame["obs_ci_upper"].values[0])),
        )
    except Exception:
        return None


def _meta_from_postal(postal):
    """
    Return a meta dict for this postal code.
    Tries enriched CSV first (has flat_type/lease), falls back to geocode cache.
    """
    p = str(postal).strip().zfill(6)
    if not _ENRICHED.empty:
        match = _ENRICHED[_ENRICHED["postal_code"].astype(str).str.zfill(6) == p]
        if not match.empty:
            return match.iloc[0].to_dict()
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
            sub = _PAST_TXN[mask & (_PAST_TXN["flat_type"] == ft)]
            if len(sub) >= 5:
                label = f"{radius}m radius · same flat type"
                return sub, fc, label
        # Use 500m result even if < 5
        label = "500m radius · same flat type"
        return sub, fc, label
    else:
        # Fallback: street name
        sub = _PAST_TXN[
            (_PAST_TXN["street_upper"] == street_upper_fallback) &
            (_PAST_TXN["flat_type"] == ft)
        ]
        return sub, fc, "same street · same flat type"


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
    """Return list of {date, block, street, floor, flat_type, price} for the table."""
    if _PAST_TXN.empty:
        return []
    sub, fc, _ = _get_nearby_txns(lat, lon, flat_type_ui, floor_category, street_upper_fallback)
    sub = sub.sort_values("month", ascending=False).head(n)
    return [
        {"date": r["month"], "block": str(r["block"]), "street": str(r["street_name"]),
         "floor": r["storey_range"], "flat_type": r["flat_type"], "price": int(r["resale_price"])}
        for _, r in sub.iterrows()
    ]


def get_current_listings(town, flat_type_ui, floor_category, p15, p85):
    """
    Same-town listings: same flat_type + floor_category, sorted cheapest first.
    Shows all with lat/lon on map; those without still appear in cards.
    """
    if _ENRICHED.empty:
        return []
    ft_norm = _FT_MAP.get(flat_type_ui, flat_type_ui.upper())
    fc = _STOREY_MAP.get(floor_category, floor_category)
    town_upper = str(town).replace(" Town", "").strip().upper()

    sub = _ENRICHED[
        (_ENRICHED["town"].str.upper().str.replace(" TOWN", "", regex=False).str.strip() == town_upper) &
        (_ENRICHED["flat_type_norm"] == ft_norm) &
        (_ENRICHED["floor_category"] == fc) &
        (_ENRICHED["price_numeric"].notna()) &
        (_ENRICHED["scrape_failed"] == False)
    ].sort_values("price_numeric").head(10)

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

    # Use actual remaining_lease_years if available, else midpoint of the user's lease bin
    _lease_bin_midpoints = {
        "Under 60 years": 55.0, "60-75 years": 67.5,
        "75-90 years": 82.5,    "Over 90 years": 95.0,
    }
    if pd.notna(meta.get("remaining_lease_years")):
        remaining_lease_years = float(meta["remaining_lease_years"])
    else:
        remaining_lease_years = _lease_bin_midpoints.get(lease_bin)

    # Try OLS model first; fall back to historical percentile placeholder
    prediction = get_ols_prediction(meta["block"], street_upper, town, flat_type_ui, storey_bin, remaining_lease_years)
    model_note = None
    if prediction is None:
        prediction = get_placeholder_prediction(town, flat_type_ui, storey_bin)
        model_note = "Placeholder: historical percentile. OLS model unavailable for this address."
    if prediction is None:
        prediction = (400000, 500000, 600000)  # absolute fallback
        model_note = "Placeholder: default range. No data available for this address."
    p15, _, p85 = prediction

    flat_lat = float(meta["lat"]) if pd.notna(meta.get("lat")) else None
    flat_lon = float(meta["lon"]) if pd.notna(meta.get("lon")) else None

    trends, trend_source = get_nearby_trends(flat_lat, flat_lon, flat_type_ui, storey_bin, street_upper)
    txns     = get_past_transactions(flat_lat, flat_lon, flat_type_ui, storey_bin, street_upper)
    listings = get_current_listings(town, flat_type_ui, storey_bin, p15, p85)

    return {
        "address": f"Blk {meta['block']} {meta['street'].title()}",
        "postal_code": str(postal).strip(),
        "town": town.title(),
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
        "current_listings": listings,
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

DEMO_LISTING_PRICE = 650000  # above p85=598000 — showcases OVERPRICED state


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


# ── Past transactions table (scrollable) ──────────────────────
def past_data_table(data):
    txns = data.get("past_transactions", [])
    town = data.get("town", "this area")
    fallback = len(txns) < 3
    rows = [
        html.Tr([
            html.Td(t["date"],
                    style={"fontSize": "12px", "color": "var(--color-text-secondary)"}),
            html.Td(f"Blk {t.get('block', t.get('blk',''))} {t.get('street','').title()}",
                    style={"fontSize": "12px", "color": "var(--color-text-secondary)"}),
            html.Td(t["floor"]),
            html.Td(t["flat_type"]),
            html.Td(f"${t['price']:,.0f}", className="td-price"),
        ]) for t in txns[:10]
    ]
    return html.Div([
        html.Div(
            f"\u26a0\ufe0f Limited transactions on this street. "
            f"Showing town-level comparables for {town}.",
            className="fallback-notice",
        ) if fallback else None,
        html.Div(className="val-txn-scroll", children=[
            html.Table(className="data-table", children=[
                html.Thead(html.Tr([
                    html.Th("MONTH"), html.Th("ADDRESS"),
                    html.Th("STOREY"), html.Th("FLAT TYPE"), html.Th("PRICE"),
                ])),
                html.Tbody(rows),
            ]),
        ]) if rows else html.P("No recent transactions found.",
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


# ── Map: all pins ──────────────────────────────────────────────
_AMENITY_STYLE = {
    "mall":       {"color": "#7C3AED", "symbol": "shop",    "label": "Mall"},
    "school":     {"color": "#D97706", "symbol": "school",  "label": "School"},
    "healthcare": {"color": "#DC2626", "symbol": "hospital","label": "Healthcare"},
}

def make_listings_map(user_lat, user_lon, user_address, listings, amenity_pins=None):
    fig = go.Figure()

    # Amenity pins filtered to within 3km of the subject flat
    if amenity_pins:
        R = 6_371_000
        for atype, style in _AMENITY_STYLE.items():
            pts = amenity_pins.get(atype, [])
            nearby = []
            for p in pts:
                dlat = np.radians(p["lat"] - user_lat)
                dlon = np.radians(p["lon"] - user_lon)
                a = (np.sin(dlat / 2) ** 2
                     + np.cos(np.radians(user_lat)) * np.cos(np.radians(p["lat"]))
                     * np.sin(dlon / 2) ** 2)
                dist = R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
                if dist <= 3000:
                    nearby.append(p)
            if nearby:
                fig.add_trace(go.Scattermapbox(
                    lat=[p["lat"] for p in nearby],
                    lon=[p["lon"] for p in nearby],
                    mode="markers",
                    marker=go.scattermapbox.Marker(size=10, color=style["color"]),
                    hovertext=[f"<b>{style['label']}</b><br>{p['name']}" for p in nearby],
                    hoverinfo="text",
                    name=style["label"],
                    showlegend=True,
                ))

    # Subject flat
    fig.add_trace(go.Scattermapbox(
        lat=[user_lat], lon=[user_lon], mode="markers+text",
        marker=go.scattermapbox.Marker(size=20, color="#1C4ED8"),
        text=["Your flat"],
        textposition="bottom center",
        textfont=dict(size=11, color="#1C4ED8"),
        hovertext=[f"<b>Your flat</b><br>{user_address}"],
        hoverinfo="text",
        name="Your flat",
        showlegend=True,
    ))

    # Current listings
    for lst in [l for l in listings if l.get("lat") is not None]:
        fig.add_trace(go.Scattermapbox(
            lat=[lst["lat"]], lon=[lst["lon"]], mode="markers+text",
            marker=go.scattermapbox.Marker(size=16, color="#16A34A"),
            text=[str(lst["rank"])],
            textfont=dict(size=9, color="white"),
            hovertext=[f"<b>#{lst['rank']} Blk {lst['blk']} {lst['street']}</b><br>"
                       f"Asking: ${lst['asking_price']:,}"],
            hoverinfo="text",
            name="Available listing" if lst["rank"] == 1 else None,
            showlegend=(lst["rank"] == 1),
        ))

    mapped = [l for l in listings if l.get("lat") is not None]
    all_lats = [user_lat] + [l["lat"] for l in mapped]
    all_lons = [user_lon] + [l["lon"] for l in mapped]
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)
    fig.update_layout(
        mapbox=dict(style="carto-positron", zoom=14,
                    center={"lat": center_lat, "lon": center_lon}),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#E5E7EB",
            borderwidth=1,
            font=dict(size=11),
            x=0.01, y=0.99,
            xanchor="left", yanchor="top",
        ),
    )
    return fig


# ── Listing cards ──────────────────────────────────────────────
def listing_cards(listings, p85):
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

    return html.Div(className="listings-section", children=[
        html.Div(className="listings-header", children=[
            html.P("CURRENT MARKET ALTERNATIVES",
                   className="listings-header-title"),
            html.P("Same town \u00b7 same flat type \u00b7 same storey level \u00b7 cheapest first",
                   className="listings-header-sub"),
        ]),
        html.Div(className="listings-scroll", children=cards) if cards else
        html.P("No current listings found.",
               style={"padding": "16px", "color": "var(--color-text-muted)",
                      "fontSize": "13px"}),
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

        # Placeholder model notice (shown when not demo data)
        html.Div(
            "⚠ Price range based on historical percentiles. "
            "Full Random Forest model coming soon.",
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


# ── Bottom-left panel: map ─────────────────────────────────────
def bottom_left_panel(data):
    listings = data.get("current_listings", [])
    town = str(data.get("town", "")).upper()
    map_fig = make_listings_map(data["lat"], data["lon"], data["address"],
                                listings, amenity_pins=_AMENITY_PINS)
    title = f"MAP WITH AVAILABLE FLATS IN {town}" if town else "MAP WITH AVAILABLE FLATS"
    return html.Div(className="card val-map-card", children=[
        html.P(title, className="val-panel-label",
               style={"marginBottom": "12px"}),
        dcc.Graph(
            figure=map_fig,
            config={"displayModeBar": False, "scrollZoom": True},
            style={"height": "360px"},
        ),
    ])


# ── Bottom-right panel: scrollable listings ────────────────────
def bottom_right_panel(data, p85):
    return listing_cards(data.get("current_listings", []), p85)


# ── Overpriced banner (amber style) ───────────────────────────
def overpriced_banner():
    return html.Div(className="overpriced-banner", children=[
        html.P("\u26a0\ufe0f  Overpriced? Check out potential alternatives below",
               className="overpriced-banner-title"),
        html.P("Current listings matched on flat type, storey level, and remaining "
               "lease \u2014 sorted by similarity to your flat.",
               className="overpriced-banner-sub"),
    ])


# ── Valuation dashboard ────────────────────────────────────────
def valuation_dashboard(data, listing_price=None):
    p15 = data["projection"]["p15"]
    p85 = data["projection"]["p85"]

    children = [
        html.Div(className="val-compact-bar", children=[
            html.Div(className="val-compact-inner", children=[
                input_form(prefill=data, compact=True),
            ]),
        ]),
        html.Button(id="val-demo", style={"display": "none"}, n_clicks=0),
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
                html.Button(
                    "Try Demo \u2014 Blk 58 Toa Payoh", id="val-demo",
                    className="btn btn-secondary",
                    style={"width": "100%", "justifyContent": "center",
                           "marginTop": "8px", "fontSize": "13px"},
                ),
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
    from dash import ctx
    trig = ctx.triggered_id

    if trig == "val-demo":
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
        return no_update, "Postal code not found in our database. Try the demo instead."
    return valuation_dashboard(data, listing_price=listed_int), ""


@callback(
    Output("val-flat-type", "value"),
    Output("val-flat-type", "options"),
    Output("val-storey-bin", "value"),
    Output("val-lease-bin", "value"),
    Input("val-postal", "value"),
    prevent_initial_call=True,
)
def autofill_from_postal(postal):
    all_ft_options = [{"label": ft, "value": ft} for ft in FLAT_TYPES]
    if not postal:
        return None, all_ft_options, None, None
    meta = _POSTAL_META.get(str(postal).zfill(6))
    if not meta:
        return None, all_ft_options, None, None
    # Pre-select from enriched data but always keep all options available
    return meta["flat_type"], all_ft_options, meta["storey_level_bin"], meta["remaining_lease_bin"]


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
