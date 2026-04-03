# Market Analysis Page Rebuild — Prompt

You are helping rebuild the **Market Analysis** page of a Dash web application called **PropertyMinBrothers**, a Singapore HDB resale property dashboard.

The current code is in `market_analysis.py` (attached). You will produce two files:
1. `preprocess_market.py` — a standalone preprocessing script
2. A full rewrite of `market_analysis.py`

---

## Context

- Data source: `merged_data/[FINAL]hdb_with_amenities_macro_pre2026.csv`
- Key columns used: `month, town, flat_type, block, street_name, storey_range, floor_area_sqm, resale_price`
- `month` is in `YYYY-MM` format. Derive year from it.
- **Past year = 2025**, **past-past year = 2024**
- Flat type groups: `ALL`, `3 ROOM`, `4 ROOM`, `5 ROOM`, `EXECUTIVE`
  - Exclude all other flat types including `MULTI-GENERATION`
- Scope levels: **national** + each **town** (from the `town` column)

---

## Part 1: `preprocess_market.py`

Write a standalone script that reads the CSV and two auxiliary files, computes all statistics, and writes `outputs/market_stats.json`.

### A. Transaction Counts

For each scope (national + each town) and each flat type group:
- Count of transactions in 2025
- Count of transactions in 2024
- YoY absolute change and percentage change

### B. Mean and Median Prices

For each scope and each flat type group:
- Mean resale price in 2025
- Mean resale price in 2024
- YoY change in mean (absolute and percentage)

For `ALL` flat type group only:
- Median resale price in 2025
- Median resale price in 2024
- YoY change in median (absolute and percentage)

### C. Highest and Lowest Priced Transactions

For each scope and each flat type group, find the single highest and single lowest resale price transaction in 2025. Store the following fields for each:
- `block`, `street_name`, `flat_type`, `storey_range`, `resale_price`

### D. Monthly and Quarterly Average Price

For each scope and each flat type group, compute from 2025 data only:
- Monthly average resale price, keyed by `YYYY-MM` (e.g. `"2025-01"`)
- Quarterly average resale price, keyed by quarter string (e.g. `"2025 Q1"`)

### E. Town Development Descriptions

Read two auxiliary files:

**`outputs/future_mrt_stations_for_frontend.csv`**
Columns: `town, station_name, line, line_code, expected_year, status, lat, lon, notes`

**`outputs/future_transport_hubs_for_frontend.csv`**
Columns: `town, hub_name, hub_type, expected_year, status, notes`

For each town, produce a single human-readable summary string that covers:
- Upcoming MRT stations (name, line, expected year, status, notes if present)
- Upcoming transport hubs (name, type, expected year, status, notes if present)

If a town has no entries in either file, store an empty string `""`.

Store all town descriptions under a top-level `"town_descriptions"` key in the JSON.

### Output JSON Structure

```json
{
  "national": {
    "ALL": {
      "txn_2025": 0,
      "txn_2024": 0,
      "txn_yoy_abs": 0,
      "txn_yoy_pct": 0.0,
      "mean_2025": 0.0,
      "mean_2024": 0.0,
      "mean_yoy_abs": 0.0,
      "mean_yoy_pct": 0.0,
      "median_2025": 0.0,
      "median_2024": 0.0,
      "median_yoy_abs": 0.0,
      "median_yoy_pct": 0.0,
      "highest": {"block": "", "street_name": "", "flat_type": "", "storey_range": "", "resale_price": 0},
      "lowest":  {"block": "", "street_name": "", "flat_type": "", "storey_range": "", "resale_price": 0},
      "monthly_avg": {"2025-01": 0.0, "2025-02": 0.0},
      "quarterly_avg": {"2025 Q1": 0.0, "2025 Q2": 0.0}
    },
    "3 ROOM": { ... },
    "4 ROOM": { ... },
    "5 ROOM": { ... },
    "EXECUTIVE": { ... }
  },
  "ANG MO KIO": { ... },
  "BEDOK": { ... },
  "town_descriptions": {
    "ANG MO KIO": "...",
    "BEDOK": "..."
  }
}
```

Note: `median_*` fields only exist under the `ALL` group. All other flat type groups omit them.

---

## Part 2: Rewrite `market_analysis.py`

Load `outputs/market_stats.json` at module startup. Do not use any hardcoded mock data. The page is split into two equal panels side by side (50/50 width, full viewport height below the navbar).

### Left Panel — Choropleth Map (50% width)

- Use the existing Plotly choropleth with `MasterPlan2019PlanningAreaBoundaryNoSea.geojson`
- Color scale: **blue (low) to red (high)**. Use `RdBu_r` for change metrics (diverging, midpoint at 0) and `Blues_r` to `Reds` for absolute value metrics. Choose the most appropriate scale per metric.
- **Remove** the existing timeframe toggle (3 Months / 6 Months / 1 Year)

**Metric selector** (dropdown):
1. Transaction Count
2. Mean Price
3. YoY Change in Transaction Count
4. YoY Change in Mean Price

**Flat type selector** (segmented button toggle, not a dropdown):
- All Flats | 3 Room | 4 Room | 5 Room | Executive

All map values come from `market_stats.json` using 2025 data (or YoY where applicable).

Clicking a town on the map updates the right panel. The flat type selection also updates the right panel.

### Right Panel — Statistics Panel (50% width)

Show statistics for the selected town, or national statistics if no town is selected. Style consistently with the existing card and box design in the current `market_analysis.py`.

Display in this order:

#### 1. Header
- Town name (e.g. "Bishan") or "National Overview"
- Subtitle: town name in all caps or "ALL REGIONS"

#### 2. Stat Cards (2x2 grid)
- **No. of Transactions**: 2025 value + YoY change with coloured up/down arrow (green up, red down)
- **Mean Price**: 2025 value formatted as `$XXX,XXX` + YoY change
- **Highest Priced Transaction**: formatted as `Block [block] [street_name], [flat_type], [storey_range] — $[price]`
- **Lowest Priced Transaction**: same format

#### 3. Monthly Average Price Chart
- Plotly line chart of monthly average resale price across 2025
- Filtered by the currently selected flat type and scope (town or national)
- Minimal styling, dark background consistent with the panel

#### 4. Quarterly Average Price Chart
- Plotly bar chart of quarterly average resale price across 2025
- Same flat type and scope filtering
- Minimal styling

#### 5. Town Description
- Section label: `ABOUT THIS TOWN`
- Content: the pre-generated string from `town_descriptions` in the JSON
- If the string is empty or the town has no entry, show: `"No upcoming transport developments found."`

### Callbacks

All right panel content must update reactively via Dash callbacks when:
- The user clicks a town on the map
- The user changes the flat type selector
- The user changes the metric selector (map updates only)

The flat type selector drives both the map coloring and the right panel statistics simultaneously.

### Style Notes

- Retain all existing CSS class names from `market_analysis.py` where applicable
- Match the existing dark navy header cards and light stat box styling
- The two panels sit side by side at 50/50 width, filling the viewport below the navbar
- Do not use any external map APIs
- Do not use `dcc.RadioItems` for the flat type selector — use styled `html.Button` elements in a button group with an active state toggled via callback or `dcc.Store`