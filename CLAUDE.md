# CLAUDE.md — HDB Resale Market Project

## Session Workflow
- **Start of every session**: Read `PROGRESS.md` to understand where things left off
- **End of every session**: Update `PROGRESS.md` with what was completed and what's next

---

## Project Overview
Singapore HDB resale transaction data pipeline + analysis. The pipeline enriches raw transactions with geospatial features (nearest MRT/LRT, amenity distances), and produces CAGR analysis outputs consumed by a frontend.

---

## Pipeline Execution Order
Notebooks must be run sequentially — each produces input for the next:

| Step | Notebook | Output |
|------|----------|--------|
| 1 | `backend/data_pipeline/1_misc_features.ipynb` | `merged_data/merged_hdb_resale_with_rpi.csv` (2021-Q1+, BASE_RPI=203.6) |
| 2 | `backend/data_pipeline/2_train_pipeline.ipynb` | `merged_data/hdb_with_train_distances.csv` |
| 3 | `backend/data_pipeline/3_amenities_pipeline.ipynb` | `merged_data/[FINAL]hdb_with_amenities_macro_2026.csv` (2026 only) and `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv` (2021–2025) |
| 4 | `backend/town_cagr_analysis.ipynb` | `outputs/` (independent, re-runnable standalone) |

**EDA (non-pipeline):** `backend/data_pipeline/data_exploration.ipynb` — visualizations only, requires step 1 output.

---

## Environment Setup
- `.env` at project root must contain `ONEMAP_EMAIL` and `ONEMAP_PASSWORD`
- Required for `data_pipeline/2_train_pipeline.ipynb` (geocoding + nearest station) and `data_pipeline/3_amenities_pipeline.ipynb` (school geocoding)
- Never commit `.env` to git

---

## Directory Conventions
| Directory | Contents |
|-----------|----------|
| `data/` | Raw source files, cache JSONs, GeoJSONs |
| `merged_data/` | Intermediate and final pipeline CSV outputs |
| `outputs/` | Analysis results consumed by the frontend |
| `backend/` | Top-level notebooks (`town_cagr_analysis.ipynb`, `future_mrt_pipeline.ipynb`) and scripts |
| `backend/data_pipeline/` | Data pipeline and EDA notebooks |

---

## Documentation Requirements
- **Always update `backend/README.md`** when: adding/renaming notebooks, changing column names, adding new output files, changing pipeline order, or adding new dependencies
- **Always update `requirements.txt`** when adding new package dependencies

---

## Naming & Column Conventions
- Train station columns: `nearest_train_line` / `nearest_train_dist_m` (not MRT — includes LRT)
- LRT prefixes included: BP, SW, SE, PE, PW (Bukit Panjang, Sengkang, Punggol)
- RPI real-price anchor: `BASE_RPI = 203.6` (Q4 2025) in `data_pipeline/1_misc_features.ipynb`

---

## API Caching
- Geocode results cached in `data/geocode_cache.json`
- Nearest train results cached in `data/train_cache.json`
- Do not delete cache files unless doing a structural rebuild (e.g. adding new station types)
- `RETRY_EMPTY = True` in `2_train_pipeline.ipynb` Phase 4 re-processes only cached-empty entries — use this to resume failed runs without re-querying successful addresses

---

## CAGR Output Conventions
- `town_cagr_by_flat.csv` columns: `town`, `flat_type`, `median_price_2025`, `median_price_2024`, `cagr_1yr_pct`, `median_price_2022`, `cagr_3yr_pct`, `median_price_2020`, `cagr_5yr_pct`
- **No `n_transactions` columns** in any CAGR CSV output
- Flat type CAGR is CSV-only — do not embed flat type data in the choropleth GeoJSON

---

## Frontend Outputs
The `outputs/` directory is consumed by the frontend:
- `town_cagr_summary.csv` — town-level aggregate CAGR for choropleth
- `town_cagr_by_flat.csv` — CAGR by town × flat type
- `town_choropleth.geojson` — town boundaries with CAGR values for map rendering
- `national_cagr_benchmarks.json` — national medians and CAGR benchmarks (including per flat type)
- `town_developments.json` — planned MRT stations and transport hubs grouped by town (from `future_mrt_pipeline.ipynb`)

---

## Development Practices
- **After writing notebook code**: Run all cells and fix any issues before considering the task done
- **Before planning implementation**: Ask clarifying questions to resolve ambiguities (output paths, file formats, edge case handling) upfront rather than making assumptions
