# Frontend Data Flow Documentation

This document describes how data is sourced, preprocessed, and surfaced in each page of the PropertyMinBrothers Dash application. It covers which CSV/JSON files are loaded, when preprocessing happens, what each callback does, and where the expensive operations are.

---

## App Startup — What Happens When the Server Starts

When `python app.py` is run, **all pages are imported immediately**. Every module-level statement in each page file executes at startup — including reading CSV files, building lookup dicts, and loading the RF model. This is a one-time cost. Subsequent user interactions use these in-memory structures.

### `frontend/app.py`

**Purpose:** Entry point. Configures the Dash app, defines the navbar, and provides a session-scoped store for cross-page prefill.

**Data loaded at startup:** None.

**dcc.Store:**
- `valuation-prefill` (session storage) — carries postal + flat type from a search on the landing page into the Flat Valuation form.

**Callbacks:**

| Callback | Trigger | Output | Speed |
|---|---|---|---|
| `set_active_nav` | URL pathname change | Navbar link classNames (highlights active page) | Instant |

---

## Page 1 — Market Analysis (`market_analysis.py`)

### Files Loaded at Startup

| File | Purpose |
|---|---|
| `outputs/MasterPlan2019PlanningAreaBoundaryNoSea.geojson` | Singapore town boundary polygons for choropleth map |
| `outputs/market_stats.json` | All town-level aggregations: median prices, transaction counts, YoY changes, top/bottom towns, monthly/quarterly price series, planned MRT developments |

### Preprocessing at Startup

1. Extract list of town names from `market_stats.json` (excludes meta keys like `"national"`, `"town_about"`, `"town_future_developments"`).
2. Define fixed colour scale ranges per metric (so the gradient is consistent across flat type toggles):
   - `txn_2025`: 0–1,000 transactions (yellow→red)
   - `median_2025`: $300k–$1.2M (yellow→red)
   - `txn_yoy_pct`: ±30% (blue←→white←→red)
   - `median_yoy_pct`: ±15% (blue←→white←→red)
3. Build flat-type button-to-data-key mapping (e.g. `"btn-4room"` → `"4_ROOM"`).

### dcc.Store

- `active-flat-type` — currently selected flat type (default: `"ALL"`). Shared between choropleth and stats panel callbacks.
- `active-chart-view` — `"monthly"` or `"quarterly"`. Controls the price trend chart format.

### Callbacks (all FAST — all data is pre-loaded JSON)

| Callback | Trigger | Output | What it does |
|---|---|---|---|
| `set_flat_type` | Any flat-type button clicked | `active-flat-type` store | Records which flat type is selected |
| `update_ft_btn_styles` | `active-flat-type` changes | 6 button classNames | Highlights the active flat-type button |
| `set_chart_view` | Monthly/Quarterly button clicked | `active-chart-view` store | Toggles chart time granularity |
| `update_metric_info` | Metric dropdown changes | Tooltip visibility + text | Shows info tooltip only for YoY metrics |
| `update_map` | Metric dropdown or flat-type changes | Choropleth figure | Rebuilds map with fixed colour scale; grey overlay for zero-transaction towns |
| `update_stats_panel` | Town clicked on map, or flat-type/chart-view changes | Stats panel children | Shows town breakdown (prices, YoY, planned MRT); falls back to national stats if no town selected |

### No model calls. No external APIs. No slow operations.

---

## Page 2 — Amenities Comparison (`amenities_comparison.py`)

### Files Loaded at Startup

| File | Purpose |
|---|---|
| `mock_data/amenities_demo.json` | Pre-built demo for 3 sample blocks |
| `merged_data/[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv` | Historical HDB transactions enriched with amenity distances (pre-2026) |
| `merged_data/hdb_with_amenities_macro_2026.csv` | 2026 HDB data enriched with amenity distances |
| `data/hdb_2026_enriched.csv` | Current active listings — used to build postal code dropdown |

### Preprocessing at Startup

1. **Build `_AMENITY_LOOKUP`** — combines both CSVs, deduplicates by `(block_upper, street_upper)`, 2026 data wins on conflicts. Key: `(block, street)` → full amenity row dict.
   - Columns used: `dist_nearest_healthcare_m`, `nearest_healthcare_name`, `dist_nearest_sportsg_m`, `nearest_sportsg_name`, `shopping_mall` distance, `hawker_centre` distance, `mrt_station` distance, `primary_schools_1km`, `parks_1km`.

2. **Build `_POSTAL_LOOKUP`** — from `hdb_2026_enriched.csv`. Key: `postal_code` → `{block, street, town, address}`.

3. **Build `_POSTAL_OPTIONS`** — list of dropdown entries `{label, value}` for ~9,000 postcodes. **Filtered** to only include postcodes where `(block, street)` exists in `_AMENITY_LOOKUP` (i.e. blocks with amenity data).

4. Define walk speed constant: **83 metres/minute** (~5 km/h).

5. Define proximity rating thresholds (in walk minutes):

| Amenity | Exceptional | Good | Below Avg | Poor |
|---|---|---|---|---|
| MRT/LRT | < 5 min | 5–10 | 10–15 | > 15 |
| Shopping & Hawkers | < 7 min | 7–12 | 12–18 | > 18 |
| Polyclinic | < 7 min | 7–13 | 13–25 | > 25 |
| Sports Hall | < 8 min | 8–15 | 15–25 | > 25 |
| Pri Schools (within 1km) | count-based | | | |

### dcc.Store

- `flats-store` — array of up to 3 postal codes currently being compared (e.g. `["310058", "529203"]`).

### Callbacks

| Callback | Trigger | Output | Speed | What it does |
|---|---|---|---|---|
| `update_store` | Add Block / Load Demo / Clear / Remove-block buttons, postal dropdown value | `flats-store` data + postal input reset | Fast | Manages the list of selected postcodes (add, remove, clear, load demo). Validates max 3 blocks. |
| `render_comparison` | `flats-store` changes | Flat tags (pills) + comparison output section | **Slow (~1–3s for 3 blocks)** | For each postal: looks up amenity row → computes walk minutes for each amenity → rates each amenity → computes overall proximity score (0–10) → builds HTML comparison table and verdict card |

### How `render_comparison` Works (the slow callback)

For each selected postal code:
1. Look up `(block, street)` from `_POSTAL_LOOKUP`
2. Look up amenity distances from `_AMENITY_LOOKUP`
3. Convert distances to walk minutes: `distance_m / 83`
4. Rate each amenity against thresholds → EXCEPTIONAL / GOOD / BELOW AVERAGE / POOR
5. Count primary schools within 1km, parks within 1km (stored as name lists in CSV)
6. Compute overall proximity score: average of per-amenity scores (0–3 each → normalised to 0–10)
7. Build comparison table with colour-coded ratings
8. Build verdict section showing which block wins per category

### No model calls. No external APIs.

---

## Page 3 — Flat Valuation (`flat_valuation.py`)

This is the most complex page. It loads a machine learning model, ~12 data files, and makes an optional LLM API call.

### Files Loaded at Startup

| File | Purpose |
|---|---|
| `mock_data/valuation_demo.json` | Demo valuation (Blk 87 Dawson Rd, Queenstown) |
| `data/hdb_2026_enriched.csv` (`_ENRICHED`) | Active listings: postal, block, street, town, flat_type, storey, lease |
| `merged_data/[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv` (`_PAST_TXN`) | All historical resale transactions with amenity distances and lat/lon |
| `data/geocode_cache.json` | postal → `{lat, lon, block, street}` for ~9k postcodes |
| `data/postal_lease.csv` | postal_code → `lease_commence_date` (year) |
| `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv` | Pipeline output: used to build town + amenity + lease lookups |
| `merged_data/[FINAL]hdb_with_amenities_macro_2026.csv` | Pipeline output: 2026 data (takes precedence over pre-2026) |
| `data/shoppingmalls.csv` | Mall lat/lon for map pins |
| `data/school_name_locs.json` | School lat/lon for map pins |
| `data/healthcare_geocode_cache.json` | Healthcare lat/lon for map pins |
| `data/mrt_approx_locs.json` | MRT/LRT station lat/lon for map pins |
| `data/hawker_approx_locs.json` | Hawker centre lat/lon for map pins |
| `data/park_approx_locs.json` | Park lat/lon for map pins |
| `backend/price_model/rf_model.pkl` (1.3 GB) | Random Forest model weights — **auto-downloaded from HuggingFace** if not present |
| `backend/price_model/rf_encoder.pkl` | Label encoder for categorical features |
| `backend/price_model/rf_feature_cols.pkl` | Ordered list of feature columns expected by the model |
| `backend/price_model/rf_conformal_quantiles.json` | Conformal prediction interval offsets: `q_low`, `q_high` |

### Preprocessing at Startup

1. **`_ENRICHED`** — loaded as DataFrame; `street_upper` column added.

2. **`_PAST_TXN`** — loaded as DataFrame; `street_upper` column added.

3. **`_GEOCODE_LOOKUP`** — built from `geocode_cache.json`. Key: `postal_code (6-digit str)` → `{lat, lon, block, street}`.

4. **`_POSTAL_OPTIONS`** — 9k+ dropdown entries. Built from `_ENRICHED` first (has flat_type info), then supplemented from `_GEOCODE_LOOKUP` for postcodes not in current listings.

5. **`_POSTAL_META`** — Key: `postal_code` → `{flat_type, storey_level_bin, remaining_lease_bin}`. Sources:
   - Primary: `_ENRICHED` (current listings — has flat_type and storey)
   - Fallback: `_PAST_TXN` (for blocks with no active listing — provides lease bin only, flat_type/storey left None)

6. **`_POSTAL_LEASE`** — Key: `postal_code` → `lease_commence_date (int)`. From `postal_lease.csv`.

7. **`_BLOCK_LEASE`** — Key: `(block_upper, street_upper)` → `lease_commence_date (int)`. Built from both FINAL pipeline CSVs.

8. **`_TOWN_LOOKUP`** — Key: `(block_upper, street_upper)` → `town`. From FINAL pipeline CSVs.

9. **`_AMENITY_LOOKUP`** — Key: `(block_upper, street_upper)` → amenity feature row. Used as RF model input. Columns:
   - `remaining_lease_years`, `nearest_train_dist_m`, `dist_nearest_hawker_m`, `dist_nearest_primary_m`, `num_primary_1km`, `dist_nearest_park_m`, `num_parks_1km`, `dist_nearest_sportsg_m`, `dist_nearest_mall_m`, `dist_nearest_healthcare_m`, `dist_cbd_m`
   - Also stores `lease_commence_date` for computing current lease.

10. **RF Model** — loaded via `joblib`. If `rf_model.pkl` is absent, it is downloaded from HuggingFace (`xiulii/dse3101-rf-model`) on first startup. This download can take several minutes.

11. **`_AMENITY_PINS`** — all amenity locations loaded into lists for map rendering. Loaded once, reused on every map render.

### dcc.Store

- `val-data-store` — valuation results dict (lat, lon, address, town, past_transactions, current_listings, p85). Shared between the main valuation view and the listing scope toggle callback.
- `val-txn-sort` — `{col, asc}` sort state for the past transactions table.
- `val-map-layers` — list of active map overlay layers (e.g. `["current", "past", "mrt"]`).

### Callbacks

| Callback | Trigger | Output | Speed | What it does |
|---|---|---|---|---|
| `autofill_from_postal` | Postal code dropdown changes | `val-flat-type` value, `val-storey-bin` value, `val-lease-bin` value + disabled | **Fast (lookup)** | Reads `_POSTAL_META` for the postal → pre-fills flat type, storey, and lease. Locks lease dropdown (disabled=True) since lease is physically fixed per block. |
| `run_valuation` | "Get Valuation" button clicked | Full page children (dashboard) + error message | **SLOW (~5–15s)** | Runs the full valuation pipeline — see detailed breakdown below. |
| `prefill_from_store` | URL pathname changes | Page children (pre-search layout) | Fast | If navigating from landing page with prefill data, restores the form with pre-filled values. |
| `toggle_map_layer` | Map layer toggle buttons | `val-map-layers` store + map figure | Fast (re-render) | Adds/removes amenity pin layers from map without re-running the model. |
| `toggle_listing_scope` | Block / Town scope buttons | Listings body | Fast (lookup) | Switches current listings between block-level and town-level comparables from `val-data-store`. |
| `sort_past_transactions` | Table column header clicks | Sort state store + table rows | Fast | Re-sorts already-loaded transactions by date, address, floor, flat type, lease, or price. |

---

### Detailed: What Happens When User Clicks "Get Valuation"

This is the critical slow path. Here is the exact sequence:

#### Step 1 — Form Inputs
User provides:
- **Postal code** (e.g. `141087`)
- **Flat type** (e.g. `4-Room`)
- **Storey level** (e.g. `High`)
- **Listed price** (optional, e.g. `$1,258,000`)

Lease is **not a user input** — it is locked and automatically determined from the postal code.

#### Step 2 — `build_real_data()` is called

**2a. Resolve block metadata from postal**

`_meta_from_postal(postal)`:
- Tries `_ENRICHED` first (has lat/lon/flat_type/lease from current listings)
- Falls back to `_GEOCODE_LOOKUP` (lat/lon/block/street from geocode cache)
- Patches missing lat/lon from geocode cache if enriched row lacks it

Result: `{block, street, town, lat, lon, remaining_lease, ...}`

**2b. Compute current remaining lease**

```
lease_commence = _POSTAL_LEASE.get(postal) or _BLOCK_LEASE.get((block, street))
remaining_lease_years = lease_commence + 99 - current_year
```

This is derived from the postal code, not from historical transaction data or user input.

**2c. Generate RF model prediction** — `get_rf_prediction()` — **SLOW**

1. Look up `_AMENITY_LOOKUP[(block_upper, street_upper)]` → get all 11 continuous features
2. Override `remaining_lease_years` with value computed in 2b (current, not historical)
3. Map flat_type UI label → model label (e.g. `"4-Room"` → `"4 ROOM"`)
4. Map storey UI label → floor_category (e.g. `"High"` → `"High"`)
5. Construct feature row with 11 continuous + 3 categorical features
6. Apply `_RF_ENCODER` to categorical columns
7. Cast all to float
8. Call `_RF_MODEL.predict(X)` → returns `log(price)`
9. Apply `exp()` → point estimate
10. Apply conformal offsets: `p_low = point + q_low`, `p_high = point + q_high`
11. Returns `(p_low, median, p_high)`

**RF model features:**

| Feature | Source |
|---|---|
| `remaining_lease_years` | Computed: `lease_commence + 99 - current_year` |
| `nearest_train_dist_m` | `_AMENITY_LOOKUP` (pipeline CSV) |
| `dist_nearest_hawker_m` | `_AMENITY_LOOKUP` |
| `dist_nearest_primary_m` | `_AMENITY_LOOKUP` |
| `num_primary_1km` | `_AMENITY_LOOKUP` |
| `dist_nearest_park_m` | `_AMENITY_LOOKUP` |
| `num_parks_1km` | `_AMENITY_LOOKUP` |
| `dist_nearest_sportsg_m` | `_AMENITY_LOOKUP` |
| `dist_nearest_mall_m` | `_AMENITY_LOOKUP` |
| `dist_nearest_healthcare_m` | `_AMENITY_LOOKUP` |
| `dist_cbd_m` | `_AMENITY_LOOKUP` |
| `flat_type` | User input |
| `floor_category` | User input (storey bin) |
| `town` | Derived from postal lookup |

**Fallback chain if RF model unavailable:**
1. RF model not loaded → `get_placeholder_prediction()` → median/p15/p85 from `_PAST_TXN` for that town × flat_type × floor_category
2. No past transactions for that combination → hardcoded fallback `(400k, 500k, 600k)`

**2d. Get nearby past transactions** — `get_past_transactions()`

Searches `_PAST_TXN` with expanding radius:
1. Within 200m of flat (Haversine distance) + same flat_type + same floor_category
2. If < 5 results: expand to same street + flat_type
3. Returns up to 10 most recent, formatted with date as `Mon YYYY`

**2e. Get price trend data** — `get_nearby_trends()`

Same search logic as above but groups results by quarter → produces `{quarter: avg_price}` dict for the trend chart.

**2f. Get current listings** — `get_current_listings()`

Filters `_ENRICHED` by:
- `town` (or block for block-scope)
- `flat_type`
- `floor_category` (storey bin)
- `remaining_lease_years` range from lease bin
Returns up to 10 cheapest active listings.

#### Step 3 — Render Results

`valuation_dashboard(data)` builds the full results layout:
- Price verdict badge: **OVERPRICED** / **GOOD DEAL** / **FAIR VALUE** (based on whether listed price is above p_high, below p_low, or in between)
- Market premium bar (visual position of listed price relative to predicted range)
- Flat detail grid (address, postal, flat type, lease commence / remaining, storey, town)
- Historical price trend chart (Plotly line chart from `graph_trend`)
- Past transactions table (sortable, 10 rows)
- Current listings cards (block-scope and town-scope toggle)
- If overpriced: alternatives section with cheapest comparable listings

#### Step 4 — Valuation Insights (optional, SLOW)

If a listed price was provided, `generate_valuation_insights()` is called:
- Makes a POST request to **HuggingFace Inference API** (`mistralai/Mistral-7B-Instruct-v0.3`)
- Prompt includes: flat details, asking price, predicted range, market position %, recent transaction summary, comparables summary
- Returns 2 bullet-point insights (≤18 words each)
- Timeout: 15 seconds
- If API is down or returns an error: falls back to rule-based insights (e.g. "Priced X% above predicted ceiling — room to negotiate")

---

## Data Freshness Summary

| Data | Frequency | How Updated |
|---|---|---|
| `market_stats.json` | Re-run `town_cagr_analysis.ipynb` | Manual pipeline re-run |
| `[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv` | Re-run full pipeline (steps 1–3) | Manual |
| `[FINAL]hdb_with_amenities_macro_2026.csv` | Re-run step 3 | Manual |
| `hdb_2026_enriched.csv` | Scraper re-run | Manual |
| `postal_lease.csv` | Static (99-year HDB leases don't change) | Rarely |
| `geocode_cache.json` | Updated by pipeline when new addresses geocoded | Automatic during pipeline |
| RF model weights | Static after training | Re-train only if retraining |

---

## Quick Reference — Where is Each Thing Computed?

| Question | Answer |
|---|---|
| Where does the RF model live? | `backend/price_model/rf_model.pkl` (auto-downloaded from HuggingFace) |
| When is the RF model loaded? | Once at app startup (module import) |
| When is the RF model called? | Each time user clicks "Get Valuation" |
| What inputs does the RF model take? | 11 distance/amenity features (from pipeline CSV) + flat_type + floor_category + town. Lease is computed from postal, not passed by user. |
| How are conformal intervals computed? | `p_low = exp(predict) + q_low`, `p_high = exp(predict) + q_high` where q values are pre-computed quantiles stored in JSON |
| Where do past transactions come from? | `[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv`, searched by Haversine distance at runtime |
| Where do current listings come from? | `hdb_2026_enriched.csv`, filtered in-memory at runtime |
| How is lease determined? | `postal_lease.csv` → `lease_commence_date` → `99 - (current_year - commence)` |
| What triggers a slow response? | Clicking "Get Valuation" (RF inference) or "Load Demo" (reads demo JSON + renders full dashboard) |
| What is pre-computed vs runtime? | Amenity distances are pre-computed in pipeline. Lease, trends, listings, RF prediction are computed at request time. |
