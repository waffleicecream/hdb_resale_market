# Backend - HDB Resale Market Analysis

## Notebook Execution Order

Run the notebooks in this order:

1. **`data_exploration.ipynb`** - Loads raw data, merges RPI, creates real prices, and saves the base merged dataset.
2. **`add_macro_variables.ipynb`** - Adds macroeconomic variables (SORA, inflation, real interest rate) to the merged dataset.

## Raw Data (`../data/`)

| File | Description |
|------|-------------|
| `ResaleflatpricesbasedonregistrationdatefromJan2017onwards.csv` | Main dataset: 224,541 individual HDB resale transactions with property details (town, flat type, floor area, storey, lease, price). |
| `HDBResalePriceIndex1Q2009100Quarterly.csv` | Quarterly HDB Resale Price Index (RPI). Base period: 2009-Q1 = 100. |
| `3MonthCompoundedSORA2017to2026.csv` | Daily 3-month compounded SORA from MAS. Benchmark interest rate for housing loans. |
| `MedianResalePricesforRegisteredApplicationsbyTownandFlatType.csv` | Quarterly median resale prices aggregated by town and flat type. |
| `percentagechangeinCPImonthly.xlsx` | Monthly CPI percentage change data. |

## Output Data (`../merged_data/`)

| File | Description |
|------|-------------|
| `merged_hdb_resale_with_rpi.csv` | Output of notebook 1. Transaction data merged with RPI and real prices. |
| `merged_hdb_resale_with_macro.csv` | Output of notebook 2. Final dataset for modeling, filtered from 2018-Q2 onwards. |
| `quarterly_summary.csv` | Quarterly price statistics (count, mean, median, min, max). |
| `quarterly_macro_summary.csv` | Quarterly macro variables with transaction counts. |
| `MACRO_VARIABLES_DICTIONARY.md` | Detailed documentation of all macro variables added. |

## Final Dataset Columns (`merged_hdb_resale_with_macro.csv`)

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
