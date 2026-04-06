# Data Sources by Python File

All paths are relative to the project root (`hdb_resale_market/`).

---

## Frontend

### `frontend/preprocess_market.py`
Script that pre-processes data and writes `outputs/market_stats.json`. Run offline before starting the app.

| File | Role |
|------|------|
| `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv` | Main transaction + amenity data (2021–2025) |
| `outputs/future_mrt_stations_for_frontend.csv` | Planned MRT stations |
| `outputs/future_transport_hubs_for_frontend.csv` | Planned transport hubs |

---

### `frontend/pages/market_analysis.py`

| File | Role |
|------|------|
| `frontend/MasterPlan2019PlanningAreaBoundaryNoSea.geojson` | Town boundary polygons for choropleth map |
| `outputs/market_stats.json` | Pre-computed market statistics (written by `preprocess_market.py`) |

---

### `frontend/pages/amenities_comparison.py`

| File | Role |
|------|------|
| `frontend/mock_data/amenities_demo.json` | Demo data for the Load Demo button |
| `merged_data/[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv` | Amenity lookup (tried first) |
| `merged_data/hdb_with_amenities_macro_2026.csv` | Amenity lookup fallback path |
| `data/hdb_2026_enriched.csv` | Postal code → block/street/town mapping for dropdown |

---

### `frontend/pages/flat_valuation.py`

| File | Role |
|------|------|
| `frontend/mock_data/valuation_demo.json` | Demo data for the Load Demo button |
| `data/hdb_2026_enriched.csv` | Block/street lookup for 2026 listings |
| `merged_data/[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv` | Historical transactions for similar past sales |
| `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv` | Enriched transactions 2021–2025 |
| `merged_data/[FINAL]hdb_with_amenities_macro_2026.csv` | Enriched transactions 2026 |
| `data/geocode_cache.json` | Cached geocode results (postal → lat/lon) |
| `data/postal_lease.csv` | Postal code → lease commence date |
| `data/shoppingmalls.csv` | Shopping mall locations |
| `data/school_name_locs.json` | Primary school name → lat/lon |
| `data/healthcare_geocode_cache.json` | Polyclinic/hospital postal → lat/lon |
| `data/mrt_approx_locs.json` | MRT/LRT station name → lat/lon/line |
| `data/hawker_approx_locs.json` | Hawker centre name → lat/lon |
| `data/park_approx_locs.json` | Park name → lat/lon |
| `backend/price_model/rf_conformal_quantiles.json` | Conformal prediction quantiles for price intervals |

---

### `frontend/app.py` · `frontend/pages/landing.py`
No data file reads.

---

## Backend

### `backend/similar_past_transactions.py`

| File | Role |
|------|------|
| `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv` | Enriched transactions 2021–2025 |
| `merged_data/[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv` | Historical transactions fallback |
| `data/geocode_cache.json` | Cached geocode results |

---

### `backend/user_input.py`

| File | Role |
|------|------|
| `data/geocode_cache.json` | Cached geocode results |
| `data/train_cache.json` | Cached nearest train station results |
| `data/MasterPlan2025RailStationLayer.geojson` | MRT/LRT station geometries |
| `data/ura_planning_area_2019.geojson` | URA planning area boundaries (town lookup) |
| `data/HawkerCentresGEOJSON.geojson` | Hawker centre locations |
| `data/Parks.geojson` | Park locations |
| `data/SportSGSportFacilitiesGEOJSON.geojson` | Sport facility locations |
| `data/Generalinformationofschools.csv` | Primary school list with addresses |
| `data/shoppingmalls.csv` | Shopping mall locations |
| `data/school_geocode_cache.json` | Cached school geocode results |
| `data/healthcare_geocode_cache.json` | Cached polyclinic/hospital geocode results |
| `data/healthcare_address.csv` | Polyclinic/hospital address list |

---

### `backend/enrich_missing_blocks.py`

| File | Role |
|------|------|
| `merged_data/[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv` | Transactions to enrich |
| `data/hdb_2026_enriched.csv` | 2026 enriched listings |
| `data/shoppingmalls.csv` | Shopping mall locations |
| `data/healthcare_address.csv` | Polyclinic/hospital address list |
| `data/geocode_cache.json` | Cached geocode results |
| `data/train_cache.json` | Cached nearest train station results |
| `data/mrt_approx_locs.json` | MRT/LRT station name → lat/lon/line |
| `data/hawker_approx_locs.json` | Hawker centre name → lat/lon |
| `data/park_approx_locs.json` | Park name → lat/lon |
| `data/school_name_locs.json` | Primary school name → lat/lon |
| `data/school_geocode_cache.json` | Cached school geocode results |
| `data/healthcare_geocode_cache.json` | Cached polyclinic/hospital geocode results |
| `data/sportsg_approx_locs.json` | Sport facility name → lat/lon |

---

### `backend/trial_predict.py`

| File | Role |
|------|------|
| `backend/price_model/ols_feature_cols.json` | OLS model feature column list |

---

### `backend/data_pipeline/download_data.py`
No data file reads (downloads raw data via HTTP).
