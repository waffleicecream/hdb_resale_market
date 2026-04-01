# PROGRESS.md — HDB Resale Market Project

_Last updated: 2026-04-01 (session 5)_

---

## What Has Been Built

### Data Pipeline (backend/data_pipeline/)
All pipeline notebooks moved to `backend/data_pipeline/`. All relative paths updated to `../../`. Pipeline is now 4 steps:

1. **`data_pipeline/1_misc_features.ipynb`** — Loads HDB resale transactions, merges with quarterly RPI index, computes `resale_price_real` (BASE_RPI = 203.6, Q4 2025), imputes missing RPI with BASE_RPI (covers 2026-Q1 rows), filters to 2021-Q1 onwards. Derives `remaining_lease_years`, `floor_category`, `year`. Produces `merged_hdb_resale_with_rpi.csv` and `quarterly_summary.csv`.

2. **`data_pipeline/2_train_pipeline.ipynb`** — Geocodes all HDB addresses via OneMap API, finds nearest MRT/LRT station (includes LRT lines: BP, SW, SE, PE, PW). Caches at `data/geocode_cache.json` and `data/train_cache.json`. Produces `hdb_with_train_distances.csv`

3. **`data_pipeline/3_amenities_pipeline.ipynb`** — Computes distances to 7 amenity types (hawker, CBD, primary school, park, SportSG, mall, healthcare). Also computes `num_primary_1km` and `num_parks_1km` (counts from pipe-separated 1km list columns). Produces final `hdb_with_amenities_macro.csv`

**EDA (non-pipeline):** `data_pipeline/data_exploration.ipynb` — visualizations only, loads from `merged_hdb_resale_with_rpi.csv`.

5. **`town_cagr_analysis.ipynb`** — Computes 1yr/3yr/5yr CAGR per town (aggregate + per flat type, no `n_transactions` columns), national benchmarks per flat type, and choropleth GeoJSON. Outputs:
   - `outputs/town_cagr_summary.csv`
   - `outputs/town_cagr_by_flat.csv`
   - `outputs/town_choropleth.geojson`
   - `outputs/national_cagr_benchmarks.json`

6. **`future_mrt_pipeline.ipynb`** — Matches planned MRT stations against URA Master Plan 2025 GeoJSON (`MasterPlan2025RailStationLayer.geojson`) to extract polygon centroids. Combines with transport hub data and builds a town-keyed lookup for the frontend. Independent of main pipeline — re-runnable standalone.
   - **Step 1:** 43/54 stations matched; 11 unmatched (e.g. RTS Link, Tengah Central, JRL extensions not yet in Master Plan 2025) — included with `null` lat/lon
   - **Outputs:** `data/future_mrt_stations_with_coords.csv`, `outputs/town_developments.json` (22 towns: 20 with MRT data, 11 with hub data)
   - **CSV outputs also generated** for frontend: `outputs/future_mrt_stations.csv` (54 rows), `outputs/future_transport_hubs.csv` (13 rows)
   - `shapely` added to `requirements.txt`; `MasterPlan2025RailStationLayer.geojson` and `future_mrt_stations_with_coords.csv` added to `.gitignore`

7. **`price_model/ols_modelling.ipynb`** — OLS baseline model for HDB resale price prediction. Full pipeline: data cleaning, feature engineering, stratified 80/20 split, OLS fit with VIF check, diagnostics, and evaluation. Outputs `ols_model_summary.txt`; diagnostic PNG plots removed (view inline only).
   - **Features (40 total):** 9 continuous (`remaining_lease_years`, `nearest_train_dist_m`, `dist_nearest_hawker_m`, `dist_nearest_primary_m`, `num_primary_1km`, `dist_nearest_park_m`, `dist_nearest_sportsg_m`, `dist_nearest_mall_m`, `dist_nearest_healthcare_m`); flat type × 4, town × 25, floor category × 2 (one-hot)
   - **Excluded:** `floor_area_sqm` (not a user input at inference time), `dist_cbd_m` (VIF 33.1, redundant with town fixed effects)
   - **Target:** `log_resale_price_real` (log-transformed RPI-adjusted price); predictions exponentiated back to SGD at evaluation
   - **Results:** R² = 0.887 (log space), RMSE = $76,377, Linlin Loss = $83,218 (w=2), 80% PI coverage = 82.7%, VIF check clean (no feature > 10)

8. **`price_model/catboost_modelling.ipynb`** — CatBoost gradient-boosted tree model. Same 9 continuous + 3 categorical features as OLS; no scaling needed; categorical features handled natively.
   - **Results:** R² = 0.9647, RMSE = $40,466, MAE = $27,771, MAPE = 4.15% — substantially outperforms OLS
   - **Outputs:** `price_model/catboost_hdb_model.pkl` (13 MB), `price_model/catboost_test_predictions.csv` (19,358 rows); diagnostic PNGs removed (view inline only)

---

## What's Pending / Next Steps

### High Priority
- **Full pipeline re-run needed**: notebooks moved to `data_pipeline/`, paths updated, new derived columns added (`remaining_lease_years`, `floor_category`, `year`, `num_primary_1km`, `num_parks_1km`). Re-run all 3 pipeline notebooks to regenerate CSVs.
- **`download_data.py` path fix**: `DATA_DIR` corrected to `Path(__file__).parent.parent.parent / "data"` — re-run if any raw files landed in `backend/data/` by mistake.

### Price Model (backend/price_model/)
- **Next models to implement:** Random Forest, XGBoost (or other non-linear models) using the same feature set and train/test split as the OLS baseline
- **Model comparison notebook:** Once all models are implemented, build a final comparison notebook computing composite 50/50 RMSE + Linlin scores across models

### Future MRT Pipeline
- **11 unmatched stations** in `future_mrt_stations_with_coords.csv` (null lat/lon). Investigate whether names need to be adjusted to match the GeoJSON, or whether these stations are intentionally absent from Master Plan 2025.

### Medium Priority
- ~~**`download_data.py`**: Script stub exists but not yet implemented.~~ **Done** — `download_data.py` was already fully implemented. Large raw data files and intermediate CSVs have been untracked from git (`git rm --cached`); `requirements.txt` re-encoded to UTF-8; `.env.example` added; `backend/README.md` setup section updated.

### Low Priority
- **merged_data cleanup**: Pipeline now produces 3 sequential CSVs (was 4 — `merged_hdb_resale_with_macro.csv` removed).
