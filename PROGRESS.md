# PROGRESS.md — HDB Resale Market Project

_Last updated: 2026-03-27 (session 3)_

---

## What Has Been Built

### Data Pipeline (backend/)
All 5 notebooks are implemented and have been run at least once:

1. **`data_exploration.ipynb`** — Loads 224,541 HDB resale transactions (Jan 2017–Feb 2026), merges with quarterly RPI index, produces `merged_hdb_resale_with_rpi.csv`

2. **`add_macro_variables.ipynb`** — Adds SORA interest rates, CPI inflation, real interest rates, and lag variables. Real prices adjusted to Q4 2025 RPI (`BASE_RPI = 203.6`). Produces `merged_hdb_resale_with_macro.csv`

3. **`train_pipeline.ipynb`** — Geocodes all HDB addresses via OneMap API, finds nearest MRT/LRT station (includes LRT lines: BP, SW, SE, PE, PW). Caches at `data/geocode_cache.json` and `data/train_cache.json`. Produces `hdb_with_train_distances.csv`

4. **`amenities_pipeline.ipynb`** — Computes distances to 6 amenity types (hawker, CBD, primary school, park, SportSG, mall) for every flat. Applies RPI real price adjustment. Produces final `hdb_with_amenities_macro.csv`

5. **`town_cagr_analysis.ipynb`** — Computes 1yr/3yr/5yr CAGR per town (aggregate + per flat type, no `n_transactions` columns), national benchmarks per flat type, and choropleth GeoJSON. Outputs:
   - `outputs/town_cagr_summary.csv`
   - `outputs/town_cagr_by_flat.csv`
   - `outputs/town_choropleth.geojson`
   - `outputs/national_cagr_benchmarks.json`

6. **`future_mrt_pipeline.ipynb`** — Matches planned MRT stations against URA Master Plan 2025 GeoJSON (`MasterPlan2025RailStationLayer.geojson`) to extract polygon centroids. Combines with transport hub data and builds a town-keyed lookup for the frontend. Independent of main pipeline — re-runnable standalone.
   - **Step 1:** 43/54 stations matched; 11 unmatched (e.g. RTS Link, Tengah Central, JRL extensions not yet in Master Plan 2025) — included with `null` lat/lon
   - **Outputs:** `data/future_mrt_stations_with_coords.csv`, `outputs/town_developments.json` (22 towns: 20 with MRT data, 11 with hub data)
   - `shapely` added to `requirements.txt`; `MasterPlan2025RailStationLayer.geojson` and `future_mrt_stations_with_coords.csv` added to `.gitignore`

7. **`price_model/ols_modelling.ipynb`** — OLS baseline model for HDB resale price prediction. Full pipeline: data cleaning, feature engineering, stratified 80/20 split, OLS fit with VIF check, diagnostics, and evaluation. Outputs `ols_model_summary.txt` and diagnostic PNG plots.
   - **Features (39 total):** `remaining_lease_years`, `nearest_train_dist_m`, 6 amenity distances (standardised); flat type × 4, town × 25, floor category × 2 (one-hot)
   - **Excluded:** `floor_area_sqm` (not a user input at inference time), `dist_cbd_m` (VIF 33.1, redundant with town fixed effects)
   - **Target:** `log_resale_price_real` (log-transformed RPI-adjusted price); predictions exponentiated back to SGD at evaluation (median prediction, no Duan correction)
   - **Results:** R² = 0.887 (log space), RMSE = $76,377, Linlin Loss = $83,218 (w=2), 80% PI coverage = 82.7%, VIF check clean (no feature > 10)

---

## What's Pending / Next Steps

### High Priority
- **train_pipeline Phase 4 re-run**: 5,752 addresses returned empty results (likely rate-limited during initial LRT rebuild). Re-run with `RETRY_EMPTY = True` to fill these in without re-querying successful entries.
- **train_pipeline Phase 6 re-run**: After Phase 4 completes, re-run Phase 6 to regenerate `hdb_with_train_distances.csv`. Now also outputs `nearest_train_name`.
- **amenities_pipeline re-run**: After `hdb_with_train_distances.csv` is updated, re-run to generate the enriched dataset with all new columns (see New Features below).

### New Features Implemented (code complete, needs re-run)
- **`nearest_train_name`** added to train_pipeline Phase 6 (from existing cache — no new API calls needed)
- **`nearest_hawker_name`** added to amenities Phase 3
- **`nearest_sportsg_name`** added to amenities Phase 8
- **`nearest_mall_name`** added to amenities Phase 9
- **`nearest_healthcare_name` + `dist_nearest_healthcare_m`** — new Phase 10 (geocodes 38 polyclinics/hospitals via OneMap on first run, cached thereafter)
- **`primary_schools_1km`** — pipe-separated school names within 1 km (Phase 6)
- **`parks_1km`** — pipe-separated park names within 1 km (Phase 7)

### Price Model (backend/price_model/)
- **Next models to implement:** Random Forest, XGBoost (or other non-linear models) using the same feature set and train/test split as the OLS baseline
- **Model comparison notebook:** Once all models are implemented, build a final comparison notebook computing composite 50/50 RMSE + Linlin scores across models

### Future MRT Pipeline
- **11 unmatched stations** in `future_mrt_stations_with_coords.csv` (null lat/lon). Investigate whether names need to be adjusted to match the GeoJSON, or whether these stations are intentionally absent from Master Plan 2025.

### Medium Priority
- ~~**`download_data.py`**: Script stub exists but not yet implemented.~~ **Done** — `download_data.py` was already fully implemented. Large raw data files and intermediate CSVs have been untracked from git (`git rm --cached`); `requirements.txt` re-encoded to UTF-8; `.env.example` added; `backend/README.md` setup section updated.

### Low Priority
- **merged_data cleanup**: User mentioned wanting fewer intermediate files. Not yet resolved — current pipeline produces 4 sequential CSVs in `merged_data/`.
