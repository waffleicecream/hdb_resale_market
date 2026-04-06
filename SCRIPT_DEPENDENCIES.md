# Script Dependencies & Outputs

## Backend Python Scripts

### `backend/data_pipeline/download_data.py`
**Inputs:** None (fetches from external API — data.gov.sg)
**Other scripts:** None
**Outputs:**
- `data/ResaleflatpricesbasedonregistrationdatefromJan2017onwards.csv`
- `data/HDBResalePriceIndex1Q2009100Quarterly.csv`
- `data/HawkerCentresGEOJSON.geojson`
- `data/Parks.geojson`
- `data/SportSGSportFacilitiesGEOJSON.geojson`
- `data/Generalinformationofschools.csv`
- `data/MasterPlan2025RailStationLayer.geojson`

---

### `backend/enrich_missing_blocks.py`
**Inputs:**
- `merged_data/[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv`
- `data/hdb_2026_enriched.csv`
- `data/geocode_cache.json`
- `data/train_cache.json`
- `data/mrt_approx_locs.json`
- `data/hawker_approx_locs.json`
- `data/school_name_locs.json`
- `data/park_approx_locs.json`
- `data/sportsg_approx_locs.json`
- `data/shoppingmalls.csv`
- `data/healthcare_address.csv`
- `data/healthcare_geocode_cache.json`
- `.env` (OneMap credentials)

**Other scripts:** None
**Outputs:**
- `merged_data/[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv` (updated in place)
- `data/geocode_cache.json` (updated)
- `data/train_cache.json` (updated)

---

### `backend/user_input.py`
**Inputs:**
- `data/geocode_cache.json`
- `data/train_cache.json`
- `data/MasterPlan2025RailStationLayer.geojson`
- `data/ura_planning_area_2019.geojson`
- `data/HawkerCentresGEOJSON.geojson`
- `data/Parks.geojson`
- `data/SportSGSportFacilitiesGEOJSON.geojson`
- `data/Generalinformationofschools.csv`
- `data/school_geocode_cache.json`
- `data/shoppingmalls.csv`
- `data/healthcare_address.csv`
- `data/healthcare_geocode_cache.json`

**Other scripts:** None
**Outputs:** None (returns feature dict; called as a module)

---

### `backend/trial_predict.py`
**Inputs:**
- `backend/price_model/ols_model.pkl`
- `backend/price_model/ols_scaler.joblib`
- `backend/price_model/ols_feature_cols.json`

**Other scripts:**
- `backend/user_input.py` (imported; calls `compute_features()`)

**Outputs:** None (console print only)

---

### `backend/similar_past_transactions.py`
**Inputs:**
- `data/geocode_cache.json`
- `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv`
- `merged_data/[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv`

**Other scripts:** None
**Outputs:**
- `outputs/similar_past_transactions.csv`

---

## Backend Jupyter Notebooks — Data Pipeline

### `backend/data_pipeline/1_misc_features.ipynb`
**Inputs:**
- `data/ResaleflatpricesbasedonregistrationdatefromJan2017onwards.csv`
- `data/HDBResalePriceIndex1Q2009100Quarterly.csv`

**Other scripts:** None
**Outputs:**
- `merged_data/merged_hdb_resale_with_rpi.csv`

---

### `backend/data_pipeline/2_train_pipeline.ipynb`
**Inputs:**
- `merged_data/merged_hdb_resale_with_rpi.csv`
- `.env` (OneMap credentials)
- `data/geocode_cache.json` (optional, for resume)
- `data/train_cache.json` (optional, for resume)

**Other scripts:** None
**Outputs:**
- `merged_data/hdb_with_train_distances.csv`
- `data/geocode_cache.json`
- `data/train_cache.json`
- `data/failed_geocodes.csv`

---

### `backend/data_pipeline/3_amenities_pipeline.ipynb`
**Inputs:**
- `merged_data/hdb_with_train_distances.csv`
- `data/HawkerCentresGEOJSON.geojson`
- `data/Parks.geojson`
- `data/SportSGSportFacilitiesGEOJSON.geojson`
- `data/Generalinformationofschools.csv`
- `data/school_geocode_cache.json`
- `data/shoppingmalls.csv`
- `data/healthcare_address.csv`
- `data/healthcare_geocode_cache.json`

**Other scripts:** None
**Outputs:**
- `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv`
- `merged_data/[FINAL]hdb_with_amenities_macro_2026.csv`

---

### `backend/data_pipeline/data_exploration.ipynb`
**Inputs:**
- `merged_data/merged_hdb_resale_with_rpi.csv`

**Other scripts:** None
**Outputs:** None (exploratory only)

---

## Backend Jupyter Notebooks — Future MRT

### `backend/future_mrt_pipeline.ipynb`
**Inputs:**
- `data/future_mrt_stations.csv`
- `data/future_transport_hubs.csv`
- `data/MasterPlan2025RailStationLayer.geojson`

**Other scripts:** None
**Outputs:**
- `data/future_mrt_stations_with_coords.csv`
- `outputs/future_mrt_stations_for_frontend.csv`
- `outputs/future_transport_hubs_for_frontend.csv`
- `outputs/town_developments.json`

---

## Backend Jupyter Notebooks — Price Modelling

### `backend/price_model/EDA.ipynb`
**Inputs:**
- `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv`

**Other scripts:** None
**Outputs:** None (exploratory only)

---

### `backend/price_model/ols_modelling.ipynb`
**Inputs:**
- `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv`

**Other scripts:** None
**Outputs:**
- `backend/price_model/ols_model.pkl`
- `backend/price_model/ols_scaler.joblib`
- `backend/price_model/ols_feature_cols.json`

---

### `backend/price_model/random_forest_modelling.ipynb`
**Inputs:**
- `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv`
- `merged_data/[FINAL]hdb_with_amenities_macro_2026.csv`

**Other scripts:** None
**Outputs:**
- `backend/price_model/rf_model.pkl`
- `backend/price_model/rf_encoder.pkl`
- `backend/price_model/rf_feature_cols.pkl`
- `backend/price_model/rf_conformal_quantiles.json`

---

### `backend/price_model/elastic_net_hdb_tuning_notebook.ipynb`
**Inputs:**
- `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv`

**Other scripts:** None
**Outputs:** None (tuning/exploration only, no model serialization)

---

### `backend/price_model/catboost_modelling_tidy.ipynb`
**Inputs:**
- `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv`

**Other scripts:** None
**Outputs:** None (not serialized for production use)

---

## Backend Jupyter Notebooks — CAGR Analysis

### `backend/town_cagr_analysis.ipynb`
**Inputs:**
- `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv`

**Other scripts:** None
**Outputs:**
- `outputs/town_cagr_summary.csv`
- `outputs/town_cagr_by_flat.csv`
- `outputs/national_cagr_benchmarks.json`
- `outputs/street_trends.csv`
- `outputs/town_choropleth.geojson`

---

## Frontend Python Scripts

### `frontend/app.py`
**Inputs:** None
**Other scripts (imported):**
- `frontend/pages/landing.py`
- `frontend/pages/market_analysis.py`
- `frontend/pages/amenities_comparison.py`
- `frontend/pages/flat_valuation.py`

**Outputs:** None (Dash server process)

---

### `frontend/preprocess_market.py`
**Inputs:**
- `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv`
- `outputs/future_mrt_stations_for_frontend.csv`
- `outputs/future_transport_hubs_for_frontend.csv`

**Other scripts:** None
**Outputs:**
- `outputs/market_stats.json`

---

### `frontend/pages/landing.py`
**Inputs:** None
**Other scripts:** None
**Outputs:** None (page layout only)

---

### `frontend/pages/market_analysis.py`
**Inputs:**
- `frontend/MasterPlan2019PlanningAreaBoundaryNoSea.geojson`
- `outputs/market_stats.json`

**Other scripts:** None
**Outputs:** None (page layout + callbacks)

---

### `frontend/pages/amenities_comparison.py`
**Inputs:**
- `merged_data/[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv`
- `merged_data/hdb_with_amenities_macro_2026.csv`
- `data/hdb_2026_enriched.csv`
- `frontend/mock_data/amenities_demo.json`

**Other scripts:** None
**Outputs:** None (page layout)

---

### `frontend/pages/flat_valuation.py`
**Inputs:**
- `data/hdb_2026_enriched.csv`
- `merged_data/[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv`
- `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv`
- `data/geocode_cache.json`
- `data/postal_lease.csv`
- `data/school_name_locs.json`
- `data/healthcare_geocode_cache.json`
- `data/mrt_approx_locs.json`
- `data/hawker_approx_locs.json`
- `data/park_approx_locs.json`
- `backend/price_model/ols_model.pkl`
- `backend/price_model/ols_scaler.joblib`
- `backend/price_model/ols_feature_cols.json`
- `backend/price_model/rf_model.pkl` (optional; auto-downloaded from HuggingFace if missing)
- `backend/price_model/rf_encoder.pkl` (optional)
- `backend/price_model/rf_conformal_quantiles.json` (optional)
- `frontend/mock_data/valuation_demo.json`

**Other scripts:** None
**Outputs:** None (page layout)
