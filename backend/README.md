# Backend - HDB Resale Market Analysis

## Setup

Raw data files from data.gov.sg are not stored in the repo. Download them first:

```bash
python backend/download_data.py
```

This fetches 6 files into `data/` (skips any that already exist). The other data files (`shoppingmalls.csv`, `3MonthCompoundedSORA2017to2026.csv`, `percentagechangeinCPImonthly.xlsx`, `MedianResalePricesforRegisteredApplicationsbyTownandFlatType.csv`) are kept in the repo as they are not available via data.gov.sg.

For notebooks 3 and 4, create `../.env` from the provided template and fill in your OneMap credentials ([register here](https://www.onemap.gov.sg/apidocs/)):
```bash
cp .env.example .env
# then edit .env with your credentials
```

---

## Notebook Execution Order

Run the notebooks in this order:

1. **`data_exploration.ipynb`** - Loads raw data, merges RPI, creates real prices, and saves the base merged dataset.
2. **`add_macro_variables.ipynb`** - Adds macroeconomic variables (SORA, inflation, real interest rate) to the merged dataset.
3. **`train_pipeline.ipynb`** - Geocodes every unique HDB address and finds the nearest MRT or LRT station distance using the OneMap API. Requires `../.env` to be filled in with OneMap credentials before running.
4. **`amenities_pipeline.ipynb`** - Computes amenity distances and names: nearest hawker centre (open at time of transaction), CBD (Raffles Place MRT proxy), nearest MOE primary school + schools within 1 km, nearest park + parks within 1 km, nearest SportSG sport facility, nearest shopping mall, nearest polyclinic/hospital. Geocodes primary schools and healthcare facilities via OneMap API on first run (cached thereafter). All columns accumulated in memory; dataset written once at the end. Saves to `hdb_with_amenities_macro.csv`.

5. **`future_mrt_pipeline.ipynb`** — Matches planned MRT stations to URA Master Plan 2025 GeoJSON polygons to extract centroids (lat/lon). Combines with future transport hub data and outputs a town-keyed JSON for the frontend. Independent of the main pipeline — re-runnable standalone.

## Raw Data (`../data/`)

| File | Description |
|------|-------------|
| `ResaleflatpricesbasedonregistrationdatefromJan2017onwards.csv` | Main dataset: 224,541 individual HDB resale transactions with property details (town, flat type, floor area, storey, lease, price). |
| `HDBResalePriceIndex1Q2009100Quarterly.csv` | Quarterly HDB Resale Price Index (RPI). Base period: 2009-Q1 = 100. |
| `3MonthCompoundedSORA2017to2026.csv` | Daily 3-month compounded SORA from MAS. Benchmark interest rate for housing loans. |
| `MedianResalePricesforRegisteredApplicationsbyTownandFlatType.csv` | Quarterly median resale prices aggregated by town and flat type. |
| `percentagechangeinCPImonthly.xlsx` | Monthly CPI percentage change data. |
| `HawkerCentresGEOJSON.geojson` | Hawker centre point locations with `STATUS` and `EST_ORIGINAL_COMPLETION_DATE` fields. Used by notebook 4. |
| `Generalinformationofschools.csv` | MOE school directory. Filtered to `mainlevel_code == 'PRIMARY'` for primary school distance computation in notebook 4. |
| `Parks.geojson` | NParks managed green space point locations. Non-park features (playgrounds, car parks, terminals, etc.) are excluded before distance computation in notebook 4. |
| `SportSGSportFacilitiesGEOJSON.geojson` | SportSG managed sport facility point locations (45 facilities). Used by notebook 4. |
| `future_mrt_stations.csv` | Planned MRT stations with columns: `station_name`, `line`, `line_code`, `town`, `expected_year`, `status`, `notes`. |
| `future_transport_hubs.csv` | Planned transport hubs with columns: `hub_name`, `hub_type`, `town`, `expected_year`, `status`, `notes`. |
| `MasterPlan2025RailStationLayer.geojson` | URA Master Plan 2025 rail station polygons. `NAME` property in ALL CAPS; interchange stations suffixed with ` INTERCHANGE`. Used by `future_mrt_pipeline.ipynb`. |
| `shoppingmalls.csv` | Shopping mall locations (238 rows, 221 unique malls after deduplication by name). Used by notebook 4. |
| `healthcare_address.csv` | 38 healthcare facilities (27 polyclinics + 11 hospitals) with institution name and postal code. Used by notebook 4. |

## Output Data (`../merged_data/`)

| File | Description |
|------|-------------|
| `merged_hdb_resale_with_rpi.csv` | Output of notebook 1. Transaction data merged with RPI and real prices. |
| `merged_hdb_resale_with_macro.csv` | Output of notebook 2. Final dataset for modeling, filtered from 2020-Q1 onwards. |
| `hdb_with_train_distances.csv` | Output of notebook 3. Full dataset enriched with lat/lon coordinates and nearest MRT/LRT station details (`nearest_train_line`, `nearest_train_dist_m`, `nearest_train_name`). |
| `hdb_with_amenities_macro.csv` | Output of notebook 4. Full dataset enriched with amenity distances, names, within-1km school/park lists, and `resale_price_real`. |
| `future_mrt_stations_with_coords.csv` | Output of `future_mrt_pipeline.ipynb` Step 1. Future MRT stations with `lat`/`lon` columns added from GeoJSON centroid matching. Rows with no GeoJSON match have `null` coords. |
| `quarterly_summary.csv` | Quarterly price statistics (count, mean, median, min, max). |
| `quarterly_macro_summary.csv` | Quarterly macro variables with transaction counts. |
| `MACRO_VARIABLES_DICTIONARY.md` | Detailed documentation of all macro variables added. |

## Cache and Config Files

| File | Description |
|------|-------------|
| `.env` | OneMap API credentials. Fill in `ONEMAP_EMAIL` and `ONEMAP_PASSWORD` before running notebooks 3 and 4. |
| `data/geocode_cache.json` | Auto-created by notebook 3. Caches geocoded lat/lon per HDB address — safe to delete to re-geocode from scratch. |
| `data/train_cache.json` | Auto-created by notebook 3. Caches nearest MRT/LRT results per address — safe to delete to re-fetch from scratch. |
| `data/failed_geocodes.csv` | Auto-created by notebook 3. Lists addresses that could not be geocoded. |
| `data/school_geocode_cache.json` | Auto-created by notebook 4 (Phase 6). Caches geocoded lat/lon per primary school postal code — safe to delete to re-geocode from scratch. |
| `data/healthcare_geocode_cache.json` | Auto-created by notebook 4 (Phase 10). Caches geocoded lat/lon per healthcare facility postal code. |

## Final Dataset Columns (`hdb_with_train_distances.csv`)

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

### Derived and macro variables
| Column | Description |
|--------|-------------|
| `quarter` | Quarter (e.g. 2018-Q2) |
| `rpi` | HDB Resale Price Index for that quarter |
| `resale_price_real` | Real resale price adjusted by RPI (base: 2017-Q1) |
| `sora_3m` | End-of-quarter 3-month compounded SORA (%) |
| `inflation_yoy` | Year-over-year housing price inflation from RPI (%) |
| `real_interest_rate` | Real interest rate: `sora_3m - inflation_yoy` (%) |
| `sora_3m_lag1` | Previous quarter's SORA (%) |
| `real_interest_rate_lag1` | Previous quarter's real interest rate (%) |

### Geocoding and MRT/LRT features
| Column | Description |
|--------|-------------|
| `lat` | Latitude of the flat address (from OneMap geocoding) |
| `lon` | Longitude of the flat address (from OneMap geocoding) |
| `nearest_train_line` | Line of the nearest open MRT or LRT station at time of transaction (e.g. NS, EW, DT, CC, NE, TE, BP, SW, SE, PE, PW). NaN if no station found within 5 km. |
| `nearest_train_dist_m` | Straight-line distance to the nearest MRT/LRT station that was open at transaction time (metres). NaN if none found within 5 km. |
| `nearest_train_name` | Full name of the nearest open MRT/LRT station (e.g. "ANG MO KIO MRT STATION"). NaN if none found. |

### Amenity features (`hdb_with_amenities_macro.csv`)
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
| `resale_price_real` | Real resale price adjusted to Q4 2025 RPI = 203.6. |
