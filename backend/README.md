# Backend - HDB Resale Market Analysis

## Notebook Execution Order

Run the notebooks in this order:

1. **`data_exploration.ipynb`** - Loads raw data, merges RPI, creates real prices, and saves the base merged dataset.
2. **`add_macro_variables.ipynb`** - Adds macroeconomic variables (SORA, inflation, real interest rate) to the merged dataset.
3. **`mrt_pipeline.ipynb`** - Geocodes every unique HDB address and finds the nearest MRT station distance using the OneMap API. Requires `../.env` to be filled in with OneMap credentials before running.
4. **`amenities_pipeline.ipynb`** - Computes amenity distances: nearest hawker centre (open at time of transaction), CBD (Raffles Place MRT proxy), nearest MOE primary school, nearest park, and nearest SportSG sport facility. Geocodes primary schools via OneMap API on first run (cached thereafter). All columns accumulated in memory; dataset written once at the end. Saves to `hdb_with_amenities_macro.csv`.

## Raw Data (`../data/`)

| File | Description |
|------|-------------|
| `ResaleflatpricesbasedonregistrationdatefromJan2017onwards.csv` | Main dataset: 224,541 individual HDB resale transactions with property details (town, flat type, floor area, storey, lease, price). |
| `HDBResalePriceIndex1Q2009100Quarterly.csv` | Quarterly HDB Resale Price Index (RPI). Base period: 2009-Q1 = 100. |
| `3MonthCompoundedSORA2017to2026.csv` | Daily 3-month compounded SORA from MAS. Benchmark interest rate for housing loans. |
| `MedianResalePricesforRegisteredApplicationsbyTownandFlatType.csv` | Quarterly median resale prices aggregated by town and flat type. |
| `percentagechangeinCPImonthly.xlsx` | Monthly CPI percentage change data. |
| `HawkerCentresGEOJSON.geojson` | Hawker centre point locations with `STATUS` and `EST_ORIGINAL_COMPLETION_DATE` fields. Used by notebook 4. |
| `general-information-of-schools.csv` | MOE school directory. Filtered to `mainlevel_code == 'PRIMARY'` for primary school distance computation in notebook 4. |
| `Parks.geojson` | NParks managed green space point locations. Non-park features (playgrounds, car parks, terminals, etc.) are excluded before distance computation in notebook 4. |
| `SportSGSportFacilitiesGEOJSON.geojson` | SportSG managed sport facility point locations (45 facilities). Used by notebook 4. |
| `shoppingmalls.csv` | Shopping mall locations (238 rows, 221 unique malls after deduplication by name). Used by notebook 4. |

## Output Data (`../merged_data/`)

| File | Description |
|------|-------------|
| `merged_hdb_resale_with_rpi.csv` | Output of notebook 1. Transaction data merged with RPI and real prices. |
| `merged_hdb_resale_with_macro.csv` | Output of notebook 2. Final dataset for modeling, filtered from 2018-Q2 onwards. |
| `hdb_with_mrt_distances.csv` | Output of notebook 3. Full dataset enriched with lat/lon coordinates and nearest MRT station details. |
| `hdb_with_amenities_macro.csv` | Output of notebook 4. Full dataset enriched with `dist_nearest_hawker_m`, `dist_cbd_m`, `dist_nearest_primary_m`, `dist_nearest_park_m`, `dist_nearest_sportsg_m`, and `dist_nearest_mall_m`. |
| `quarterly_summary.csv` | Quarterly price statistics (count, mean, median, min, max). |
| `quarterly_macro_summary.csv` | Quarterly macro variables with transaction counts. |
| `MACRO_VARIABLES_DICTIONARY.md` | Detailed documentation of all macro variables added. |

## Cache and Config Files

| File | Description |
|------|-------------|
| `.env` | OneMap API credentials. Fill in `ONEMAP_EMAIL` and `ONEMAP_PASSWORD` before running notebooks 3 and 4. |
| `data/geocode_cache.json` | Auto-created by notebook 3. Caches geocoded lat/lon per HDB address — safe to delete to re-geocode from scratch. |
| `data/mrt_cache.json` | Auto-created by notebook 3. Caches nearest MRT results per address — safe to delete to re-fetch from scratch. |
| `data/failed_geocodes.csv` | Auto-created by notebook 3. Lists addresses that could not be geocoded. |
| `data/school_geocode_cache.json` | Auto-created by notebook 4 (Phase 6). Caches geocoded lat/lon per primary school postal code — safe to delete to re-geocode from scratch. |

## Final Dataset Columns (`hdb_with_mrt_distances.csv`)

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

### Geocoding and MRT features
| Column | Description |
|--------|-------------|
| `lat` | Latitude of the flat address (from OneMap geocoding) |
| `lon` | Longitude of the flat address (from OneMap geocoding) |
| `nearest_mrt_line` | MRT line of the nearest open station at time of transaction (e.g. NS, EW, DT, CC, NE, TE). NaN if no open MRT found within 5 km. |
| `nearest_mrt_dist_m` | Straight-line distance to the nearest MRT station that was open at transaction time (metres). NaN if none found within 5 km. |

### Amenity features (`hdb_with_amenities_macro.csv`)
| Column | Description |
|--------|-------------|
| `dist_nearest_hawker_m` | Straight-line distance (metres) to the nearest hawker centre open at time of transaction. NaN for failed geocodes. |
| `dist_cbd_m` | Straight-line distance (metres) to the CBD (Raffles Place MRT proxy). NaN for failed geocodes. |
| `dist_nearest_primary_m` | Straight-line distance (metres) to the nearest MOE primary school. NaN for failed geocodes. |
| `dist_nearest_park_m` | Straight-line distance (metres) to the nearest NParks managed green space (playgrounds and non-park features excluded). NaN for failed geocodes. |
| `dist_nearest_sportsg_m` | Straight-line distance (metres) to the nearest SportSG managed sport facility. NaN for failed geocodes. |
| `dist_nearest_mall_m` | Straight-line distance (metres) to the nearest shopping mall (221 unique malls, deduplicated from 238 rows). NaN for failed geocodes. |
