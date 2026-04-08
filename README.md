---
title: PropertyMinBrothers
emoji: 🏠
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
---

# PropertyMinBrothers — HDB Resale Market Dashboard

An interactive dashboard for exploring the Singapore HDB resale market, comparing flat amenities, and estimating resale prices using machine learning.

- **Market Analysis** — Choropleth map with town-level price and transaction metrics
- **Amenities Comparison** — Compare up to 3 HDB blocks by proximity to MRT/LRT, primary schools, hawker centres, parks, sport facilities, malls, and healthcare
- **Flat Valuation** — Random Forest price prediction with 80% conformal prediction intervals, adjustable by flat type, floor, and remaining lease

---

## Setup

### Prerequisites
- Python 3.10+
- OneMap API credentials (only needed to re-run the data pipeline, not the app)

### 1. Clone and install dependencies

```bash
git clone https://github.com/waffleicecream/hdb_resale_market.git
cd hdb_resale_market
pip install -r requirements.txt
```

### 2. Download raw data

Raw transaction files from data.gov.sg are not stored in the repo. Download them before running the pipeline:

```bash
python backend/data_pipeline/download_data.py
```

This downloads 6 files into `data/` and skips any that already exist.

### 3. Run the app locally

```bash
python frontend/app.py
```

Open [http://127.0.0.1:7860](http://127.0.0.1:7860) in your browser.

The app loads pre-built outputs from `outputs/` and model artifacts from `backend/price_model/` — no pipeline re-run is needed to use the app.

### Running with Docker

```bash
docker build -t propertyminbrothers .
docker run -p 7860:7860 propertyminbrothers
```

---

## Repository Structure

```
hdb_resale_market/
├── frontend/                  # Dash web application
│   ├── app.py                 # Entry point — initialises Dash, serves on port 7860
│   ├── pages/
│   │   ├── landing.py         # Home page with postal code search
│   │   ├── market_analysis.py # Choropleth map + town metrics
│   │   ├── amenities_comparison.py  # Side-by-side amenity comparison
│   │   └── flat_valuation.py  # ML price prediction UI
│   ├── preprocess_market.py   # Data prep for the market analysis page
│   ├── preprocess_amenities.py# Data prep for the amenities page
│   └── assets/                # CSS and images
│
├── backend/                   # Data pipeline, models, and scripts
│   ├── user_input.py          # Real-time feature computation for a single postal code
│   ├── hdbsale.py             # Selenium scraper for live HDB listings
│   ├── similar_past_transactions.py  # Comparable past sales finder
│   ├── enrich_missing_blocks.py      # Backfills failed geocodes
│   ├── future_mrt_pipeline.ipynb     # Matches planned MRT stations to URA boundaries
│   ├── data_pipeline/         # Sequential data-processing notebooks (see backend/README.md)
│   └── price_model/           # Model notebooks and serialised artifacts
│       ├── random_forest_modelling.ipynb
│       ├── catboost_modelling_tidy.ipynb
│       ├── ols_modelling.ipynb
│       ├── elastic_net_hdb_tuning_notebook.ipynb
│       ├── rf_model.pkl               # Production model (Random Forest)
│       ├── rf_encoder.pkl             # OrdinalEncoder for categorical features
│       ├── rf_feature_cols.pkl        # Feature column order
│       └── rf_conformal_quantiles.json# Quantiles for 80% prediction intervals
│
├── data/                      # Reference data: GeoJSONs, CSVs, geocode caches
├── merged_data/               # Intermediate and final pipeline CSVs (training data)
├── outputs/                   # Pre-built frontend outputs (loaded by the app at startup)
│   ├── town_choropleth.geojson
│   ├── market_stats.json
│   ├── postal_lookup.json
│   ├── street_trends.csv
│   ├── unique_addresses.csv
│   └── town_developments.json
│
├── Dockerfile
├── requirements.txt
└── backend/README.md          # Data pipeline execution order and column reference
```

---

## Data Pipeline

The training data is produced by a sequence of notebooks in `backend/data_pipeline/`. See [backend/README.md](backend/README.md) for the full execution order, column schema, and cache file documentation. A re-run is not required to use the app — all outputs are already checked in.

---

## Technical Documentation

### Dataset

The base dataset is sourced from data.gov.sg: HDB resale transactions from January 2021 onwards (~134,000 rows after cleaning). Each transaction is enriched with:

- **RPI adjustment** — Prices are deflated to real Q4 2025 SGD using the quarterly HDB Resale Price Index (base: RPI = 203.6). This removes market-wide appreciation so models learn flat characteristics, not time trends.
- **Geocoding** — Each address is resolved to lat/lon via the OneMap API (cached in `data/geocode_cache.json`).
- **Train station proximity** — Nearest open MRT/LRT station at time of transaction and straight-line distance (metres), via OneMap and the URA Master Plan 2025 rail layer.
- **Amenity distances** — Straight-line haversine distances to: nearest hawker centre (open at time of transaction), CBD proxy (Raffles Place MRT), nearest primary school and count within 1 km, nearest NParks park and count within 1 km, nearest SportSG facility, nearest shopping mall, nearest polyclinic or hospital.

### Features Used by the Models

| Feature | Type | Description |
|---------|------|-------------|
| `flat_type` | Categorical | 2 ROOM / 3 ROOM / 4 ROOM / 5 ROOM / EXECUTIVE / MULTI-GENERATION |
| `town` | Categorical | One of 26 HDB towns |
| `floor_category` | Categorical | Low (floors 1–5), Mid (6–12), High (13+) |
| `remaining_lease_years` | Continuous | Remaining lease as decimal years |
| `nearest_train_dist_m` | Continuous | Distance to nearest open MRT/LRT station (m) |
| `dist_nearest_hawker_m` | Continuous | Distance to nearest open hawker centre (m) |
| `dist_nearest_primary_m` | Continuous | Distance to nearest MOE primary school (m) |
| `num_primary_1km` | Continuous | Count of primary schools within 1 km |
| `dist_nearest_park_m` | Continuous | Distance to nearest NParks park (m) |
| `num_parks_1km` | Continuous | Count of parks within 1 km |
| `dist_nearest_sportsg_m` | Continuous | Distance to nearest SportSG facility (m) |
| `dist_nearest_mall_m` | Continuous | Distance to nearest shopping mall (m) |
| `dist_nearest_healthcare_m` | Continuous | Distance to nearest polyclinic or hospital (m) |

`floor_area_sqm` is deliberately excluded: it is not user-facing at inference time (users select a flat type, not a floor area). `dist_cbd_m` is excluded from the tree-based models because town encodings already capture CBD proximity; including it introduced severe multicollinearity (VIF = 33) in the OLS model.

### Models

Four model families were trained and compared. The **Random Forest** is the production model served by the app.

---

#### Random Forest (Production)

**Algorithm:** `sklearn.ensemble.RandomForestRegressor`, hyperparameter-tuned via Optuna (TPE sampler).

**Preprocessing:**
- Drop rows with null features (primarily failed geocodes): ~134k → ~114k rows.
- Target: `log(resale_price_real)` — log-transform normalises the right-skewed price distribution. Predictions are exponentiated back to SGD at inference.
- Categorical encoding: `OrdinalEncoder` with `handle_unknown='use_encoded_value'` (unknown → -1). No scaling applied — tree-based models are scale-invariant.

**Train / validation split:**
- Stratified 80/20 split on a composite key `town + flat_type + year`, ensuring proportional representation of all towns (price levels vary ~2×), all flat types (4 ROOM accounts for ~43% of transactions), and all years.
- The 2026 dataset is held out as an independent out-of-sample test set.

**Hyperparameter tuning:**
- Optuna TPE sampler minimises RMSE on the validation set.
- Parameters searched: `n_estimators` (50–300), `max_depth` (10–30), `min_samples_split`, `min_samples_leaf`, `max_features` (sqrt / log2).
- No k-fold CV during tuning — the large sample size and stratified hold-out provide stable estimates.

**Loss function:**
- Linlin loss with underpredict weight = 2.0 — underprediction is penalised twice as heavily as overprediction because underestimating market value increases a buyer's risk of paying Cash Over Valuation (COV).

**Conformal prediction intervals (80%):**
- Residuals are computed in price space (after exponentiation) on the validation set.
- The alpha miss budget (20%) is split asymmetrically: 6.67% to the upper tail and 13.33% to the lower tail. This gives a tighter upper bound, protecting against underprediction (COV risk).
- Quantiles are stored in `rf_conformal_quantiles.json` and added to every inference at serving time.

---

#### OLS (Baseline)

**Algorithm:** `statsmodels.api.OLS` on log-transformed prices.

**Preprocessing:**
- One-hot encode all categoricals (reference categories dropped: 2 ROOM, ANG MO KIO, Low floor).
- `StandardScaler` fit on training continuous features only; dummy variables are left as 0/1.
- `dist_cbd_m` excluded after VIF check (VIF = 33.1 with town dummies in the model). All 43 retained features had VIF ≤ 10.

**Train / validation split:** Stratified 80/20 (same strategy as RF).

**Cross-validation:** Not used — single held-out validation set is sufficient given the sample size. Diagnostics performed: Breusch-Pagan test for heteroskedasticity, residuals-vs-fitted plot, Q-Q plot of standardised residuals, and per-town / per-flat-type mean residual inspection.

---

#### CatBoost

**Algorithm:** `CatBoostRegressor` with native categorical feature handling (no explicit encoding needed).

**Preprocessing:**
- Same null removal and log-transform as RF.
- Categorical columns passed directly via the `cat_features` parameter. No scaling.

**Train / validation split:** Same stratified 80/20 outer split as RF. An inner split is used for early stopping during Optuna trials.

**Hyperparameter tuning (Optuna TPE):**
- `iterations` (500–3000), `learning_rate` (0.01–0.1, log scale), `depth` (4–10), `l2_leaf_reg` (1–10), `min_data_in_leaf` (1–30), `subsample` (0.6–1.0), `random_strength`, `bagging_temperature`.
- Objective: minimise RMSE on the early-stopping validation set.
- Four variants evaluated: baseline (default params), Optuna-tuned, and both with/without `dist_cbd_m` as an additional feature.

---

#### Elastic Net

**Algorithm:** `sklearn.linear_model.ElasticNetCV` (L1 + L2 regularisation).

**Preprocessing:**
- Same null removal and log-transform.
- One-hot encode categoricals (`pd.get_dummies`, reference categories dropped).
- `StandardScaler` on continuous features (required — L1 penalty is scale-sensitive).

**Train / validation split:** Stratified 80/20.

**Cross-validation:** `ElasticNetCV` performs internal 5-fold CV (`StratifiedKFold` on the composite `town + flat_type + year` key) over a grid of:
- `l1_ratio`: [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99] — spans from near-Ridge to near-Lasso.
- `alpha`: 120 values on a log scale from 1e-7 to 10 — spans from near-unpenalised to heavy shrinkage.

The best `(alpha, l1_ratio)` pair is selected by mean CV RMSE across folds.

---

### Real-Time Inference Pipeline

When a user enters a postal code in the Flat Valuation page, `backend/user_input.py` computes all 13 model features on the fly:

1. **Geocoding** — postal code → lat/lon from `data/geocode_cache.json`.
2. **Town detection** — point-in-polygon test against `data/ura_planning_area_2019.geojson` (ray-casting); URA area names mapped to HDB town names.
3. **Train station** — nearest centroid from `data/MasterPlan2025RailStationLayer.geojson`; haversine distance.
4. **Amenities** — haversine distances and within-1 km counts computed against each amenity dataset.

The computed feature vector is passed to the serialised Random Forest (`rf_model.pkl`), and the conformal quantiles from `rf_conformal_quantiles.json` are added to produce the 80% prediction interval displayed in the UI.
