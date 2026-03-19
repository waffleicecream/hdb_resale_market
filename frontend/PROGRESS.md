# PROGRESS.md — Frontend (PropertyMinBrothers Dash App)

_Last updated: 2026-03-19_

---

## App Overview

Multi-page Dash app using `use_pages=True` (FLATLY Bootstrap theme + Bootstrap Icons).
Entry point: `app.py` | Pages auto-discovered from `pages/`

---

## Existing Pages

| Route | File | Description |
|-------|------|-------------|
| `/` | `pages/user_guide.py` | Landing page — hero, tool cards, how-to guide |
| `/general-trends` | `pages/general_trends.py` | Choropleth map of HDB prices / CAGR by town, flat-type filter, year slider |
| `/flat-valuation` | `pages/flat_valuation.py` | Postal code + form → geocode → comparable flats → estimated value + map |

### Shared modules
- `data_store.py` — loads `hdb_with_amenities_macro.csv` (fallback chain), exposes `DF`, `FLAT_TYPES`, `TOWNS`, `YEAR_MIN/MAX`
- `assets/style.css` — global tokens, dark form theming, `.nav-link-custom`, `.ac-*` comparison table rules

---

## Completed This Session (2026-03-19)

### New page: Flat Amenities Comparison (`/amenities-comparison`)

**Files added:**
- `pages/amenities_mock_data.py` — 8 mock Singapore postal codes with full amenity data
- `pages/amenities_comparison.py` — full page implementation

**Files modified:**
- `app.py` — added "AMENITIES" NavItem to navbar
- `assets/style.css` — appended `.ac-*` CSS rules for comparison table

**Feature summary:**
- Postal code input → add up to 3 flat columns
- Side-by-side `html.Table` comparison (5 nearest-amenity rows + 2 within-1km rows)
- Best-value highlighting (green tint + "Best" badge); ties all highlighted
- Walking time computed at 1 km = 20 mins
- >5 school/park names truncated with `dbc.Tooltip` overflow
- Remove button per column; input/button disabled at 3 flats
- "Postal code not found" inline error for unknown codes

---

## Pending / Next Steps

- **Wire up real data**: once `hdb_with_amenities_macro.csv` has `nearest_train_name`, `nearest_hawker_name`, `nearest_mall_name`, `nearest_healthcare_name`, `primary_schools_1km`, `parks_1km` columns populated, replace `MOCK_DATA` lookup with a real geocode + nearest-amenity query.
- **Geocode integration**: consider adding a OneMap geocode call in the Add-flat callback to look up the postal code and pull real distances from the dataset.
- **Mobile layout**: currently desktop-first only; no responsive work done.
