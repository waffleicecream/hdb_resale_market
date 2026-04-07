# PropertyMinBrothers — Technical Documentation

> **Deployment checklist item**: This document serves as the technical reference for project deployment, graders, and future contributors.

---

## 1. Project Overview

**PropertyMinBrothers** is a Singapore HDB resale market information and valuation tool. It helps buyers at every stage of the purchase journey — from market exploration to shortlisting flats to checking predicted valuations against listed prices.

The app has **4 pages**:
| Page | Route | Purpose |
|------|-------|---------|
| Landing | `/` | National market stats, inline valuation search |
| Market Analysis | `/market-analysis` | Choropleth map, town-level CAGR and price trends |
| Flat Valuation | `/flat-valuation` | ML-powered price prediction + listing verdict |
| Amenities Comparison | `/amenities-comparison` | Side-by-side proximity comparison for up to 3 flats |

**Tech stack:**
- Frontend: Python [Dash](https://dash.plotly.com/) (multi-page, `use_pages=True`)
- Charts: Plotly
- Maps: Plotly Scattermapbox (carto-positron basemap)
- Styling: Custom CSS (`frontend/assets/style.css`)
- ML Model: CatBoost (gradient-boosted trees), trained offline

---

## 2. Repository Structure

```
hdb_resale_market/
├── frontend/                    ← Dash app (entry point: app.py)
│   ├── app.py                   ← App instantiation, navbar, layout
│   ├── pages/
│   │   ├── landing.py           ← Landing page
│   │   ├── market_analysis.py   ← Town Explorer choropleth
│   │   ├── flat_valuation.py    ← Price prediction + valuation verdict
│   │   └── amenities_comparison.py  ← Proximity comparison
│   ├── mock_data/
│   │   ├── valuation_demo.json  ← Demo data for Flat Valuation tab
│   │   └── amenities_demo.json  ← Demo data for Amenities tab
│   ├── assets/
│   │   ├── style.css            ← Global stylesheet (design system)
│   │   └── logo.jpg
│   ├── DESIGN.md                ← Visual design system reference
│   ├── SPEC.md                  ← Full product specification
│   ├── flatvaluationtab.md      ← Flat Valuation tab spec (v4, canonical)
│   └── amenitiestab.md          ← Amenities tab spec (v1, canonical)
│
├── backend/
│   ├── README.md                ← Pipeline setup + column reference
│   ├── data_pipeline/
│   │   ├── 1_misc_features.ipynb
│   │   ├── 2_train_pipeline.ipynb
│   │   ├── 3_amenities_pipeline.ipynb
│   │   ├── download_data.py     ← Fetches raw data from data.gov.sg
│   │   └── data_exploration.ipynb  ← EDA (non-pipeline)
│   ├── price_model/
│   │   ├── ols_modelling.ipynb
│   │   ├── catboost_modelling.ipynb
│   │   ├── random_forest_modelling.ipynb
│   │   └── elastic_net_hdb_tuning_notebook.ipynb
│   ├── town_cagr_analysis.ipynb
│   └── future_mrt_pipeline.ipynb
│
├── data/                        ← Raw source files + API caches (gitignored for large files)
├── merged_data/                 ← Intermediate pipeline CSVs (gitignored)
├── outputs/                     ← Frontend-consumed analysis outputs
│   ├── town_cagr_summary.csv
│   ├── town_cagr_by_flat.csv
│   ├── town_choropleth.geojson
│   ├── national_cagr_benchmarks.json
│   └── town_developments.json
│
├── requirements.txt
└── .env.example                 ← OneMap API credentials template
```

---

## 3. Local Setup

### Prerequisites
- Python 3.10+ (Anaconda recommended)
- OneMap account ([register here](https://www.onemap.gov.sg/apidocs/)) — required only for pipeline re-runs

### Steps

```bash
# 1. Clone the repo
git clone <repo-url>
cd hdb_resale_market

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
cd frontend
python app.py
# → Open http://localhost:8050
```

The app runs on **mock data by default** — no backend pipeline or model inference is required to run the frontend locally.

### Running with real pipeline data (optional)

```bash
# Copy and fill in OneMap credentials
cp .env.example .env

# Download raw data from data.gov.sg
python backend/data_pipeline/download_data.py

# Run pipeline notebooks in order (see backend/README.md for details)
# 1. backend/data_pipeline/1_misc_features.ipynb
# 2. backend/data_pipeline/2_train_pipeline.ipynb
# 3. backend/data_pipeline/3_amenities_pipeline.ipynb
# 4. backend/town_cagr_analysis.ipynb  (produces outputs/ for Market Analysis)
```

---

## 4. Deployment

### Current status
The app runs locally. The mock data (`valuation_demo.json`, `amenities_demo.json`) and `outputs/` directory allow full UI demonstration without backend inference.

### Deployment options

**Option A — Render / Railway (free tier)**
The app is a standard Dash app served via `python app.py`. Deploy by:
1. Set working directory to `frontend/`
2. Start command: `python app.py`
3. Set `PORT` env var if required

Known constraint: The `merged_data/` CSVs (61 MB for pre-2026, 27 MB for RPI-merged) and the CatBoost model (13 MB) are gitignored. A deployment that needs live model inference must either bundle a lightweight model or mount these via cloud storage.

**Option B — Docker**

Sample `Dockerfile` (place at repo root):
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY frontend/ ./frontend/
COPY outputs/ ./outputs/
WORKDIR /app/frontend
EXPOSE 8050
CMD ["python", "app.py"]
```

Build and push:
```bash
docker build -t propertyminbrothers .
docker push <dockerhub-username>/propertyminbrothers
```

Run locally from DockerHub:
```bash
docker pull <dockerhub-username>/propertyminbrothers
docker run -p 8050:8050 propertyminbrothers
```

**Option C — Lightweight / proof-of-concept deployment**
All 4 pages are fully functional on mock data. A lightweight deployment bundles only:
- `frontend/` (app + pages + assets + mock_data)
- `outputs/` (pre-computed CAGR CSVs + GeoJSON, total ~5 MB)
- No large pipeline CSVs required
- No model inference required (flat valuation uses pre-loaded demo JSON)

This is suitable for free-tier hosting on Render, Railway, or HuggingFace Spaces.

> **Deployment link:** *(add public URL here once deployed)*

---

## 5. Data Pipeline

The backend pipeline transforms raw HDB transaction data into model-ready features. It runs in 3 sequential steps:

### Step 1 — `1_misc_features.ipynb`
**Input:** `ResaleflatpricesbasedonregistrationdatefromJan2017onwards.csv` (data.gov.sg), `HDBResalePriceIndex1Q2009100Quarterly.csv`

**Output:** `merged_data/merged_hdb_resale_with_rpi.csv`

Key operations:
- Merges quarterly RPI index onto each transaction by quarter
- Computes `resale_price_real` — nominal price deflated to Q4 2025 base (RPI = 203.6): `resale_price_real = resale_price / rpi * 203.6`
- Derives `remaining_lease_years` (decimal), `floor_category` (Low/Mid/High), `year`
- Filters to 2021-Q1 onwards

### Step 2 — `2_train_pipeline.ipynb`
**Input:** Step 1 output

**Output:** `merged_data/hdb_with_train_distances.csv`

Key operations:
- Geocodes every unique HDB address via OneMap API (cached in `data/geocode_cache.json`)
- Finds the nearest **open** MRT/LRT station at time of transaction (includes LRT lines BP, SW, SE, PE, PW)
- Produces `nearest_train_line`, `nearest_train_dist_m`, `nearest_train_name`
- Uses time-aware station openings (station not counted if not yet open at transaction date)

### Step 3 — `3_amenities_pipeline.ipynb`
**Input:** Step 2 output + GeoJSON/CSV amenity files

**Output:** `merged_data/[FINAL]hdb_with_amenities_macro_2026.csv` (2026 only) and `[FINAL]hdb_with_amenities_macro_pre2026.csv` (2021–2025)

Key operations:
- Computes straight-line distance to 7 amenity types: hawker centre (open at transaction date), CBD (Raffles Place MRT proxy), nearest primary school, nearest park, SportSG facility, shopping mall, polyclinic/hospital
- Computes `num_primary_1km` (count of MOE primary schools within 1 km) and `num_parks_1km`
- Hawker centres filtered by `STATUS == "OPEN"` and `EST_ORIGINAL_COMPLETION_DATE <= transaction date`
- Schools and healthcare geocoded via OneMap on first run (cached thereafter)

### Data sizes
| File | Size | Rows |
|------|------|------|
| `[FINAL]hdb_with_amenities_macro_pre2026.csv` | 61 MB | ~220,000 |
| `[FINAL]hdb_with_amenities_macro_2026.csv` | 2.7 MB | ~8,000 |
| `merged_hdb_resale_with_rpi.csv` | 27 MB | ~224,000 |

> **Large files not in repo.** Download raw data via `python backend/data_pipeline/download_data.py`, then re-run the pipeline notebooks. Full dataset link: *(add Google Drive / OneDrive link here)*

---

## 6. ML Models

### 6.1 Feature Set

All models use the same 9 continuous + 3 categorical features:

**Continuous (9):**
| Feature | Description |
|---------|-------------|
| `remaining_lease_years` | Decimal years of lease remaining at transaction date |
| `nearest_train_dist_m` | Straight-line distance to nearest open MRT/LRT station (m) |
| `dist_nearest_hawker_m` | Distance to nearest open hawker centre (m) |
| `dist_nearest_primary_m` | Distance to nearest MOE primary school (m) |
| `num_primary_1km` | Count of MOE primary schools within 1 km |
| `dist_nearest_park_m` | Distance to nearest NParks green space (m) |
| `dist_nearest_sportsg_m` | Distance to nearest SportSG facility (m) |
| `dist_nearest_mall_m` | Distance to nearest shopping mall (m) |
| `dist_nearest_healthcare_m` | Distance to nearest polyclinic or hospital (m) |

**Categorical (3):**
- `flat_type` (4 dummies after one-hot: 3-Room, 4-Room, 5-Room, Executive vs 2-Room base)
- `town` (25 dummies vs base town)
- `floor_category` (2 dummies: Mid, High vs Low base)

**Excluded features:**
- `floor_area_sqm` — not available as user input at inference time
- `dist_cbd_m` — VIF 33.1, collinear with town fixed effects
- `resale_price_real` (target, not a feature)

**Target:** `log(resale_price_real)` — log-transformed RPI-adjusted price. Predictions are exponentiated back to nominal SGD at evaluation.

### 6.2 Pre-processing

1. Filter to `flat_type` in {2-Room, 3-Room, 4-Room, 5-Room, Executive} — excludes Multi-Generation
2. Drop rows where any model feature is NaN (addresses with failed geocoding or no station within 5 km)
3. Log-transform the target: `log_resale_price_real = log(resale_price_real)`
4. Stratified 80/20 train/test split stratified on `year` — preserves temporal distribution across splits

### 6.3 Cross-Validation

**OLS baseline:** No cross-validation; single 80/20 stratified split. VIF check performed on all features (threshold: VIF < 10); all features passed.

**CatBoost:** Hyperparameter tuning performed using Optuna with 5-fold cross-validation on the training set. Folds created with `StratifiedKFold(n_splits=5, shuffle=True)` stratified on `year`. Best hyperparameters selected by minimising mean RMSE across folds, then refitted on the full training set and evaluated once on the held-out test set.

**Random Forest & Elastic Net:** Same 5-fold CV strategy as CatBoost.

### 6.4 Model Results (test set, stratified 80/20 split)

| Model | R² | RMSE (SGD) | MAE (SGD) | MAPE |
|-------|----|-----------|-----------|------|
| OLS Baseline | 0.887 | $76,377 | — | — |
| Elastic Net | — | — | — | — |
| Random Forest | — | — | — | — |
| **CatBoost (best)** | **0.9647** | **$40,466** | **$27,771** | **4.15%** |

**Linlin asymmetric loss** (weight=2 on overestimates): OLS = $83,218. CatBoost result pending.

**80% PI coverage** (OLS): 82.7% of test transactions fall within the p10–p90 predicted interval.

### 6.5 Flat Valuation Frontend Integration

The frontend Flat Valuation page currently uses **mock data** (`frontend/mock_data/valuation_demo.json`). To integrate with the trained model:

1. Backend receives user inputs: `postal_code`, `flat_type`, `storey_level_bin`, `remaining_lease_bin`
2. Resolves postal code → lat/lon + town via OneMap geocoding cache
3. Looks up amenity distances for that address from the pipeline CSV
4. Calls `catboost_hdb_model.pkl` to predict p15 and p85 (15th/85th percentile of prediction distribution)
5. Returns JSON matching the schema in [Section 8](#8-api-response-schemas) below

---

## 7. Frontend Pages

### 7.1 Landing Page (`/`)
- National market stats dashboard (total transactions, median price, MoM growth, hottest/coolest town)
- Period toggle: 3 months / 6 months / 1 year
- Inline quick-valuation search bar → prefills Flat Valuation page via `dcc.Store(id="valuation-prefill")`
- Data source: `outputs/town_cagr_summary.csv`, `outputs/national_cagr_benchmarks.json`

### 7.2 Market Analysis (`/market-analysis`)
- Choropleth map of Singapore HDB towns, colour-coded by CAGR
- Click a town → right panel updates with town-level CAGR, price trend chart, flat type breakdown, planned developments
- Data sources: `outputs/town_choropleth.geojson`, `outputs/town_cagr_by_flat.csv`, `outputs/town_developments.json`

### 7.3 Flat Valuation (`/flat-valuation`)

**Input bar (always visible):**
- Postal Code · Flat Type · Storey Level (Low/Medium/High) · Remaining Lease bin · Listed Price (optional)

**Layout (4 panels, always visible):**
```
┌──────────────────────┬──────────────────────────────┐
│  Price Prediction    │  Historical Price Reference  │
│  + Market Premium    │  [Chart on top]              │
│  + Lease Warning     │  [Past transactions below]   │
│  + Metadata          │                              │
│  + Insight           │                              │
├──────────────────────┴──────────────────────────────┤
│  [OVERPRICED BANNER — amber, full width, conditional]│
├──────────────────────┬──────────────────────────────┤
│  Location Map        │  Current Market Alternatives │
│                      │  [Scrollable cards]          │
└──────────────────────┴──────────────────────────────┘
```

**Verdict system:**
- OVERPRICED (red): `listing_price > p85`
- FAIR VALUE (grey): `p15 ≤ listing_price ≤ p85`
- GOOD DEAL (green): `listing_price < p15`

**Market Premium Bar:** Shows where listed price sits on UNDERPRICED → OVERPRICED spectrum.
- Extended range: `p15 − span` to `p85 + span` where `span = p85 − p15`
- Position % = `(listing_price − low) / (high − low) × 100`, clamped 2–98%
- Percentage premium = `(listing_price − midpoint) / midpoint × 100`

**Demo mode:** Loads `mock_data/valuation_demo.json` with `listing_price = 650000` (above p85 = 598000) to demonstrate the full OVERPRICED state.

### 7.4 Amenities Comparison (`/amenities-comparison`)

**Input:** Up to 3 postal codes → Flat A / B / C pill tags

**Layout:**
- 3-column flat cards (image placeholder, town, address, demand zone badge)
- 4 category sections: Connectivity · Retail & Food · Wellness · Education
- Each distance metric shows: name, distance, coloured progress bar, rating label (hover tooltip shows thresholds), BEST badge
- Bottom: Plotly map with flat pins + Institutional Verdict (AI summary, avg proximity score, formula)

**Proximity rating thresholds:**
| Amenity | Exceptional | Good | Below Average | Poor |
|---------|------------|------|---------------|------|
| MRT | <400m | 400–800m | 800m–1.2km | >1.2km |
| Shopping Mall | <500m | 500m–1km | 1–1.5km | >1.5km |
| Hawker Centre | <200m | 200–400m | 400–700m | >700m |
| Polyclinic | <500m | 500m–1km | 1–2km | >2km |
| Sports Hall | <600m | 600m–1.2km | 1.2–2km | >2km |

**Proximity Score formula:** Score each metric (Exceptional=3, Good=2, Below Average=1, Poor=0). `score = avg(5 metrics) / 3 × 10`

**Backend swappability:** Set `AMENITIES_DATA_PATH` env var to point to backend output JSON. Same schema, no code changes needed.

---

## 8. API Response Schemas

### Flat Valuation endpoint

When the backend is integrated, it must return a JSON matching this schema:

```json
{
  "postal_code": "310058",
  "block": "58",
  "street": "Lor 4 Toa Payoh",
  "flat_type": "4-Room",
  "storey_level_bin": "Medium",
  "remaining_lease_bin": "60-75 years",
  "address": "Blk 58 Lor 4 Toa Payoh",
  "town": "TOA PAYOH",
  "remaining_lease": "68 years 3 months",
  "lat": 1.3321,
  "lon": 103.8479,
  "projection": {
    "p15": 512000,
    "p85": 598000
  },
  "past_transactions": [
    {
      "blk": "58",
      "street": "Lor 4 Toa Payoh",
      "floor": "11 to 15",
      "flat_type": "4-Room",
      "price": 548000,
      "date": "Dec 2025"
    }
  ],
  "graph_trend": [
    {
      "quarter": "Q1 2023",
      "avg_price": 488000,
      "n_transactions": 3
    }
  ],
  "current_listings": [
    {
      "rank": 1,
      "blk": "60",
      "street": "Lor 4 Toa Payoh",
      "flat_type": "4-Room",
      "storey_display": "Medium 06–12",
      "storey_level_bin": "Medium",
      "remaining_lease": "67 years",
      "remaining_lease_bin": "60-75 years",
      "asking_price": 568000,
      "match_reasons": ["Same storey", "Same lease"],
      "lat": 1.3323,
      "lon": 103.8483,
      "listing_active": true
    }
  ]
}
```

**Notes:**
- `projection.p15` / `p85`: CatBoost model output (15th/85th percentile of prediction interval)
- `past_transactions`: filtered from pipeline CSV — same street + storey_level_bin + flat_type, last 12 months, max 10 rows, most recent first
- `graph_trend`: same CSV grouped by quarter over last 3 years
- `current_listings`: from HDB Resale Portal scraper (to be built). Similarity scoring:
  - Hard filter: `flat_type` exact match
  - Score (max 6): storey_bin (exact=2, adjacent=1) + lease_bin (exact=2, adjacent=1) + distance (<1km=2, 1–3km=1, >3km=0)
  - Sort: descending score, tiebreak lowest price

### Amenities endpoint

```json
{
  "flats": {
    "Flat A": {
      "postal_code": "310058",
      "address": "Blk 58, 310058",
      "town": "Toa Payoh Central",
      "flat_type": "4-Room",
      "demand_zone": "High Demand Zone",
      "image_url": null,
      "lat": 1.3329,
      "lon": 103.8490
    }
  },
  "nearest": {
    "Flat A": {
      "mrt_station":   { "name": "Toa Payoh MRT", "distance_m": 280, "walk_min": 4 },
      "shopping_mall": { "name": "HDB Hub / Mall", "distance_m": 320, "walk_min": 5 },
      "hawker_centre": { "name": "Toa Payoh West Hawker", "distance_m": 150, "walk_min": 2 },
      "polyclinic":    { "name": "Toa Payoh Polyclinic", "distance_m": 450, "walk_min": 7 },
      "sports_hall":   { "name": "TP Sports Hall", "distance_m": 600, "walk_min": 9 }
    }
  },
  "within_1km": {
    "Flat A": {
      "primary_schools": ["Pei Chun Public School", "CHIJ Primary (TP)"],
      "parks": ["Toa Payoh Town Park"]
    }
  },
  "proximity_thresholds": {
    "mrt_station":   [400, 800, 1200],
    "shopping_mall": [500, 1000, 1500],
    "hawker_centre": [200, 400, 700],
    "polyclinic":    [500, 1000, 2000],
    "sports_hall":   [600, 1200, 2000]
  },
  "llm_summary": "AI-generated summary text..."
}
```

`demand_zone` must be one of: `"High Demand Zone"` · `"Market Average"` · `"Limited Supply Area"`

---

## 9. Frontend Implementation Log

### Session 2026-04-02 — Flat Valuation Tab Rebuild

Full rebuild per `flatvaluationtab.md` spec (v4).

**Key changes from previous version:**
- 4-panel layout (top-left: prediction, top-right: historical, bottom-left: map, bottom-right: alternatives) — all 4 panels always visible
- Input fields: storey_level_bin (Low/Medium/High) replaces granular storey range; remaining_lease_bin added; 1-Room and Multi-Generation flat types removed
- Verdict system: OVERPRICED / FAIR VALUE / GOOD DEAL badges based on listing price vs p15/p85
- Market Premium Bar: gradient track, position formula using extended range
- Listing cards: scrollable, no HDB link button, rank circle only (no match% — not interpretable from backend)
- Source text removed: "Calculated based on N recent transactions" removed — predictions come from ML model
- Map: blue pin = user's flat, green numbered pins = alternatives

### Session 2026-04-03 — Amenities Tab Redesign

Full redesign per `amenitiestab.md` spec (v1).

**Key changes from previous version:**
- Replaced plain comparison table with card-based layout per screenshot reference
- Page header: "Premium Editorial Guide" badge + "Location Intelligence Dashboard" H1
- Flat cards: image placeholder, demand zone badge (High Demand Zone / Market Average / Limited Supply Area)
- Category sections: full-width rows with coloured progress bars + proximity rating labels
- Hover tooltip on rating labels: shows threshold ranges for each amenity type
- Institutional Verdict: avg proximity score (formula shown), best MRT walk time, AI summary
- `demand_zone`, `lat`, `lon`, `proximity_thresholds` added to `amenities_demo.json`
- Backend swappability: `AMENITIES_DATA_PATH` env var

### Session 2026-04-03 — LLM Removal + Score UI Improvements

- Removed all HuggingFace LLM code (`generate_llm_summary`, `_call_huggingface`, `HF_TOKEN`)
- "Institutional Verdict" replaced with "Location Summary" card
- Added per-flat proximity score boxes with best-flat highlight and ★ BEST badge
- Added CSS hover tooltip (pure CSS, no JS) on `?` button showing scoring formula and colour-coded point table
- Removed "Best Walk to MRT" stat box and PDF button

### Session 2026-04-03 — Backend Data Wiring (Amenities + Flat Valuation)

#### New datasets generated (originals untouched)

| File | Rows | Description |
|------|------|-------------|
| `outputs/street_trends.csv` | 9,956 | Quarterly median/avg price + transaction count grouped by `street_name × flat_type × floor_category`. Pre-aggregated from `[PAST_TRANSACTIONS]` for fast frontend loads. |
| `data/hdb_2026_enriched.csv` | 2,000 | `data/hdb_resale_2026.csv` enriched with lat/lon (joined from both amenity CSVs by block+street), parsed `price_numeric`, `remaining_lease_years`, `floor_category`, `flat_type_norm`. Coverage: 92.9% matched. |

#### Amenities Comparison — real data wiring
- `lookup_flat_by_postal(postal)` added: looks up block+street from `hdb_2026_enriched`, then fetches amenity distances from `[PAST_TRANSACTIONS]`/`hdb_with_amenities_macro_2026` combined lookup (8,481 unique blocks)
- Walk time = `round(distance_m / 83)` (83 m/min ≈ 5 km/h)
- `primary_schools_1km` pipe-separated string → Python list (title-cased)
- Demo postal codes still load from `amenities_demo.json`; all other postals use real data
- Lookup tables loaded once at startup; no per-request file I/O

#### Flat Valuation — real data wiring (placeholder model)
- `build_real_data(postal, flat_type, storey_bin, lease_bin)` added: resolves postal → block/street/town/lat/lon from `hdb_2026_enriched`
- **Price prediction (placeholder):** historical p15/p85 from `[PAST_TRANSACTIONS]` filtered by `town × flat_type × floor_category`. Falls back to `town × flat_type` if fewer than 3 rows. ⚠ Full RF model pending export.
- **Historical trends:** `outputs/street_trends.csv` filtered by `street × flat_type × floor_category`; falls back to all floor categories if no exact match
- **Past transactions:** `[PAST_TRANSACTIONS]` filtered by `street × flat_type × floor_category`, most recent 10
- **Current listings:** `hdb_2026_enriched` filtered by same street + flat_type + price within [p15, p85]; listings without lat/lon excluded from map
- Visible placeholder notice shown in top-left panel when real data is used
- Historical trends section header upgraded to `<h3>` (more prominent)
- "PAST TRANSACTIONS" label upgraded to `<h3>`

---

## 10. Known Gaps / Next Steps

| Item | Priority | Notes |
|------|----------|-------|
| Export Random Forest model to `outputs/rf_model.pkl` | High | Notebook trained but not serialised. Need to add `joblib.dump(rf_model, 'outputs/rf_model.pkl')` + `joblib.dump(dummy_cols, 'outputs/rf_feature_cols.pkl')` to `random_forest_modelling.ipynb` and re-run. Then replace `get_placeholder_prediction()` in `flat_valuation.py` with RF inference. |
| Lat/lon for remaining 7.1% of listings | Medium | 142 listings in `hdb_2026_enriched.csv` have no lat/lon due to street name abbreviation mismatches. Fix via OneMap geocoding by postal code. |
| Deployment (public URL) | High | Add public link above once deployed |
| Full pipeline re-run | Medium | Notebooks moved to `data_pipeline/`; re-run to regenerate CSVs |
| Data download link (large files) | Medium | Add Google Drive / OneDrive link for `merged_data/` CSVs |
| 11 unmatched future MRT stations | Low | null lat/lon in `future_mrt_stations_with_coords.csv` |
