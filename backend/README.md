# Backend - HDB Resale Market Analysis

## Setup

Raw data files from data.gov.sg are not stored in the repo. Download them first:

```bash
python backend/data_pipeline/download_data.py
```

This fetches 6 files into `data/` (skips any that already exist). The other data files (`shoppingmalls.csv`, `healthcare_address.csv`, etc.) are kept in the repo as they are not available via data.gov.sg.

For notebooks 2 and 3, create `.env` at the project root and fill in your OneMap credentials ([register here](https://www.onemap.gov.sg/apidocs/)):
```
ONEMAP_EMAIL=your@email.com
ONEMAP_PASSWORD=yourpassword
```

---

## Notebook Execution Order

Pipeline notebooks live in `data_pipeline/`. Run them in this order:

1. **`data_pipeline/1_misc_features.ipynb`** - Loads raw data, merges RPI, creates real prices (base: Q4 2025, RPI = 203.6), filters to 2021-Q1 onwards, and saves the base merged dataset.
2. **`data_pipeline/2_train_pipeline.ipynb`** - Geocodes every unique HDB address and finds the nearest MRT or LRT station distance using the OneMap API. Requires `.env` with OneMap credentials.
3. **`data_pipeline/3_amenities_pipeline.ipynb`** - Computes amenity distances and names: nearest hawker centre (open at time of transaction), CBD (Raffles Place MRT proxy), nearest MOE primary school + schools within 1 km, nearest park + parks within 1 km, nearest SportSG sport facility, nearest shopping mall, nearest polyclinic/hospital. Geocodes primary schools and healthcare facilities via OneMap API on first run (cached thereafter). Saves to `[FINAL]hdb_with_amenities_macro_2026.csv` (2026 transactions only) and `[FINAL]hdb_with_amenities_macro_pre2026.csv` (2021–2025 transactions).

4. **`future_mrt_pipeline.ipynb`** *(backend root)* — Matches planned MRT stations to URA Master Plan 2025 GeoJSON polygons to extract centroids (lat/lon). Combines with future transport hub data and outputs a town-keyed JSON for the frontend. Independent of the main pipeline — re-runnable standalone.

**EDA (non-pipeline):** `data_pipeline/data_exploration.ipynb` — visualizations and summary statistics. Requires step 1 output.

---

## Price Model (`price_model/`)

Standalone modelling notebooks — not part of the data pipeline. Each notebook trains a different model on the final amenity-enriched dataset.

| File | Description |
|------|-------------|
| `EDA.ipynb` | Exploratory data analysis of model features |
| `ols_modelling.ipynb` | OLS baseline regression model |
| `elastic_net_hdb_tuning_notebook.ipynb` | Elastic Net regression with hyperparameter tuning |
| `catboost_modelling_tidy.ipynb` | CatBoost gradient boosting model |
| `random_forest_modelling.ipynb` | Random Forest model training and evaluation |
| `rf_conformal_quantiles.json` | Quantile values for Random Forest conformal prediction intervals |
| `rf_encoder.pkl` | Scikit-learn encoder for categorical features |
| `rf_feature_cols.pkl` | Ordered list of feature columns used by the Random Forest model |

---

## Backend Scripts

Utility scripts at `backend/` root:

| File | Description |
|------|-------------|
| `hdb_resale_webscraper.py` | Selenium scraper that fetches live HDB resale listings from homes.hdb.gov.sg |
| `user_input.py` | Single-address inference: takes a postal code and computes all amenity features for real-time valuation |
| `similar_past_transactions.py` | Finds and displays historically similar past transactions for a given flat |
| `enrich_missing_blocks.py` | Backfills missing block data for addresses that failed geocoding |

---

## Raw Data (`../data/`)

| File | Description |
|------|-------------|
| `ResaleflatpricesbasedonregistrationdatefromJan2017onwards.csv` | Main dataset: 224,541 individual HDB resale transactions with property details (town, flat type, floor area, storey, lease, price). |
| `HDBResalePriceIndex1Q2009100Quarterly.csv` | Quarterly HDB Resale Price Index (RPI). Base period: 2009-Q1 = 100. |
| `MedianResalePricesforRegisteredApplicationsbyTownandFlatType.csv` | Quarterly median resale prices aggregated by town and flat type. |
| `HawkerCentresGEOJSON.geojson` | Hawker centre point locations with `STATUS` and `EST_ORIGINAL_COMPLETION_DATE` fields. Used by notebook 3. |
| `Generalinformationofschools.csv` | MOE school directory. Filtered to `mainlevel_code == 'PRIMARY'` for primary school distance computation in notebook 3. |
| `Parks.geojson` | NParks managed green space point locations. Non-park features (playgrounds, car parks, terminals, etc.) are excluded before distance computation in notebook 3. |
| `SportSGSportFacilitiesGEOJSON.geojson` | SportSG managed sport facility point locations (45 facilities). Used by notebook 3. |
| `shoppingmalls.csv` | Shopping mall locations (238 rows, 221 unique malls after deduplication by name). Used by notebook 3. |
| `healthcare_address.csv` | 38 healthcare facilities (27 polyclinics + 11 hospitals) with institution name and postal code. Used by notebook 3. |
| `postal_lease.csv` | Mapping of postal codes to lease commencement year. |
| `ura_planning_area_2019.geojson` | URA planning area boundaries. Used by notebook 3 for town detection via spatial join. |
| `hdb_resale_2026.csv` | 2026 HDB resale transactions (pre-enrichment). |
| `hdb_2026_enriched.csv` | 2026 transactions enriched with amenity features (intermediate file). |
| `future_mrt_stations.csv` | Planned MRT stations with columns: `station_name`, `line`, `line_code`, `town`, `expected_year`, `status`, `notes`. |
| `future_mrt_stations_with_coords.csv` | Output of `future_mrt_pipeline.ipynb` Step 1. Future MRT stations with `lat`/`lon` columns added from GeoJSON centroid matching. Rows with no GeoJSON match have `null` coords. |
| `future_transport_hubs.csv` | Planned transport hubs with columns: `hub_name`, `hub_type`, `town`, `expected_year`, `status`, `notes`. |
| `MasterPlan2025RailStationLayer.geojson` | URA Master Plan 2025 rail station polygons. `NAME` property in ALL CAPS; interchange stations suffixed with ` INTERCHANGE`. Used by `future_mrt_pipeline.ipynb`. |

---

## Pipeline Output Data (`../merged_data/`)

| File | Description |
|------|-------------|
| `merged_hdb_resale_with_macro.csv` | Output of notebook 1. Transaction data merged with RPI, real prices (Q4 2025 base), filtered to 2021-Q1 onwards. |
| `hdb_with_train_distances.csv` | Output of notebook 2. Full dataset enriched with lat/lon coordinates and nearest MRT/LRT station details (`nearest_train_line`, `nearest_train_dist_m`, `nearest_train_name`). |
| `[FINAL]hdb_with_amenities_macro_2026.csv` | Output of notebook 3 (2026 transactions only). Full dataset enriched with amenity distances, names, within-1km school/park lists, and `resale_price_real`. |
| `[FINAL]hdb_with_amenities_macro_pre2026.csv` | Output of notebook 3 (2021–2025 transactions). Same schema as above. |
| `[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv` | Historical transactions with amenity features, used for similar-transaction lookups. |

---

## Frontend Outputs (`../outputs/`)

Generated by backend scripts and notebooks; consumed by the frontend.

| File | Description |
|------|-------------|
| `town_choropleth.geojson` | Town boundary polygons with CAGR values for the map choropleth. |
| `town_developments.json` | Upcoming MRT stations and transport hubs grouped by town. Generated by `future_mrt_pipeline.ipynb`. |
| `market_stats.json` | Market statistics aggregated by town and flat type. |
| `postal_lookup.json` | Lookup table mapping postal codes to addresses and flat details. |
| `street_trends.csv` | Price trends by street and town. |
| `unique_addresses.csv` | Deduplicated HDB addresses with their latest enriched attributes. |
| `similar_past_transactions.csv` | Example output from the similar-transactions finder. |
| `future_mrt_stations_for_frontend.csv` | Future MRT stations formatted for frontend display. |
| `future_transport_hubs_for_frontend.csv` | Future transport hubs formatted for frontend display. |

---

## Cache and Config Files

| File | Description |
|------|-------------|
| `.env` | OneMap API credentials (`ONEMAP_EMAIL`, `ONEMAP_PASSWORD`). Required for notebooks 2 and 3. Never commit to git. |
| `data/geocode_cache.json` | Auto-created by notebook 2. Caches geocoded lat/lon per HDB address — safe to delete to re-geocode from scratch. |
| `data/train_cache.json` | Auto-created by notebook 2. Caches nearest MRT/LRT results per address — safe to delete to re-fetch from scratch. |
| `data/failed_geocodes.csv` | Auto-created by notebook 2. Lists addresses that could not be geocoded. |
| `data/school_geocode_cache.json` | Auto-created by notebook 3 (Phase 6). Caches geocoded lat/lon per primary school postal code. |
| `data/healthcare_geocode_cache.json` | Auto-created by notebook 3 (Phase 10). Caches geocoded lat/lon per healthcare facility postal code. |

---

## Final Dataset Columns

### Transaction-level features
| Column | Description |
|--------|-------------|
| `month` | Transaction month (YYYY-MM-DD) |
| `town` | HDB town (e.g. ANG MO KIO, BEDOK) |
| `flat_type` | Flat type (2 ROOM, 3 ROOM, 4 ROOM, 5 ROOM, EXECUTIVE, MULTI-GENERATION) |
| `block` | Block number |
| `street_name` | Street name |
| `storey_range` | Storey range (e.g. 01 TO 03, 10 TO 12) |
| `floor_area_sqm` | Floor area in square metres |
| `flat_model` | Flat model (e.g. Improved, New Generation, DBSS) |
| `lease_commence_date` | Year the lease commenced |
| `remaining_lease` | Remaining lease duration |
| `resale_price` | Nominal resale price (SGD) |

### Derived variables
| Column | Description |
|--------|-------------|
| `quarter` | Quarter (e.g. 2018-Q2) |
| `rpi` | HDB Resale Price Index for that quarter |
| `resale_price_real` | Real resale price adjusted by RPI (base: Q4 2025, RPI = 203.6) |
| `remaining_lease_years` | Remaining lease as a decimal year (e.g. `"61 years 04 months"` → `61.3333`) |
| `floor_category` | Storey bucket derived from lower bound of `storey_range`: Low (1–5), Mid (6–12), High (13+) |
| `year` | Integer year from `month` — used for stratification, not a model feature |

### Geocoding and MRT/LRT features
| Column | Description |
|--------|-------------|
| `lat` | Latitude of the flat address (from OneMap geocoding) |
| `lon` | Longitude of the flat address (from OneMap geocoding) |
| `nearest_train_line` | Line of the nearest open MRT or LRT station at time of transaction (e.g. NS, EW, DT, CC, NE, TE, BP, SW, SE, PE, PW). NaN if no station found within 5 km. |
| `nearest_train_dist_m` | Straight-line distance to the nearest MRT/LRT station that was open at transaction time (metres). NaN if none found within 5 km. |
| `nearest_train_name` | Full name of the nearest open MRT/LRT station (e.g. "ANG MO KIO MRT STATION"). NaN if none found. |

### Amenity features (`[FINAL]hdb_with_amenities_macro_2026.csv` / `[FINAL]hdb_with_amenities_macro_pre2026.csv`)
| Column | Description |
|--------|-------------|
| `dist_nearest_hawker_m` | Straight-line distance (metres) to the nearest hawker centre open at time of transaction. |
| `nearest_hawker_name` | Name of the nearest hawker centre. |
| `dist_cbd_m` | Straight-line distance (metres) to the CBD (Raffles Place MRT proxy). |
| `dist_nearest_primary_m` | Straight-line distance (metres) to the nearest MOE primary school. |
| `primary_schools_1km` | Pipe-separated names of MOE primary schools within 1 km (empty string if none). |
| `dist_nearest_park_m` | Straight-line distance (metres) to the nearest NParks managed green space (playgrounds and non-park features excluded). |
| `parks_1km` | Pipe-separated names of NParks parks within 1 km (empty string if none). |
| `dist_nearest_sportsg_m` | Straight-line distance (metres) to the nearest SportSG managed sport facility. |
| `nearest_sportsg_name` | Name of the nearest SportSG facility. |
| `dist_nearest_mall_m` | Straight-line distance (metres) to the nearest shopping mall (221 unique malls, deduplicated from 238 rows). |
| `nearest_mall_name` | Name of the nearest shopping mall. |
| `dist_nearest_healthcare_m` | Straight-line distance (metres) to the nearest polyclinic or hospital (38 facilities). |
| `nearest_healthcare_name` | Name of the nearest polyclinic or hospital. |
| `num_primary_1km` | Count of MOE primary schools within 1 km. |
| `num_parks_1km` | Count of NParks managed parks within 1 km. |
| `resale_price_real` | Real resale price adjusted to Q4 2025 RPI = 203.6. |
