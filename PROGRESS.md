# PROGRESS.md — HDB Resale Market Project

_Last updated: 2026-03-20_

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

### Medium Priority
- **`download_data.py`**: Script stub exists but not yet implemented. Goal: download raw data files from data.gov.sg dynamically instead of committing large CSVs to git. Dataset IDs are known for the main resale file and several amenity datasets.

### Low Priority
- **merged_data cleanup**: User mentioned wanting fewer intermediate files. Not yet resolved — current pipeline produces 4 sequential CSVs in `merged_data/`.
