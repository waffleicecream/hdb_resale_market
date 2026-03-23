# PROGRESS.md — Frontend (PropertyMinBrothers Dash App)

_Last updated: 2026-03-20_

---

## App Overview

Multi-page Dash app using `use_pages=True`.
Entry point: `app.py` | Pages auto-discovered from `pages/`

**Design System:** "The Architectural Ledger" — deep oceanic blue primary (#00145d), tonal surface hierarchy, Manrope + Inter typography, no 1px borders.

---

## Existing Pages

| Route | File | Description |
|-------|------|-------------|
| `/` | `pages/user_guide.py` | Premium landing — full-bleed hero, national stats band, feature cards, how-to steps, site footer |
| `/general-trends` | `pages/general_trends.py` | Market Analysis — choropleth map, KPI cards, town drill-down with region/estate metadata, methodology note |
| `/flat-valuation` | `pages/flat_valuation.py` | Flat Valuation — surface-low form panel, gradient result card, tonal comparable cards |
| `/amenities-comparison` | `pages/amenities_comparison.py` | Flat Amenities — postal code comparison matrix for up to 3 flats, primary-colour section headers |

### Shared modules
- `data_store.py` — loads `hdb_with_amenities_macro.csv` (fallback chain), exposes `DF`, `FLAT_TYPES`, `TOWNS`, `YEAR_MIN/MAX`
- `assets/style.css` — complete design token system (`:root` CSS variables), all component classes
- `pages/amenities_mock_data.py` — 8 mock Singapore postal codes with full amenity data

---

## Design System (as implemented)

| Token | Value | Usage |
|-------|-------|-------|
| `--primary` | `#00145d` | Navbar bg, section headers, CTAs, primary headings |
| `--primary-container` | `#0f2885` | Gradient endpoint |
| `--surface` | `#fbf8ff` | Page backgrounds |
| `--surface-low` | `#f4f2ff` | Panel backgrounds, form panels, town detail |
| `--surface-high` | `#e5e6ff` | Input fields, stats band, feature card hover |
| `--accent` | `#5bc8af` | Nav underline, best badges, eyebrow labels |
| `--gradient-primary` | `135deg #00145d→#0f2885` | CTAs, result card, hero |
| Fonts | Manrope / Inter | Display/body dual typeface loaded via Google Fonts |

**CSS classes introduced:**
`.kpi-card`, `.kpi-label`, `.kpi-value`, `.kpi-delta-pos/neg`, `.hero-section`, `.hero-eyebrow`, `.hero-headline`, `.hero-sub`, `.stats-band`, `.stat-item-*`, `.btn-cta`, `.btn-hero-primary`, `.btn-hero-ghost`, `.feature-card`, `.feature-card-alt`, `.feature-icon`, `.step-card`, `.step-number`, `.section-eyebrow`, `.section-title`, `.site-footer`, `.page-header-title`, `.page-header-sub`, `.surface-form`, `.valuation-form-panel`, `.result-card-gradient`, `.result-estimate-*`, `.comp-card`, `.methodology-card`, `.town-badge-*`, `.ac-*`

---

## Completed This Session (2026-03-20)

### Full "Architectural Ledger" Design Redesign

**Files modified:**

`assets/style.css` — complete rewrite:
- Added `:root` design token block (all CSS custom properties)
- Body/heading font overrides (Manrope + Inter)
- New navbar styling (gradient primary bg, brand block with tagline)
- Premium KPI card classes
- Full-bleed hero section with radial gradient accents
- Stats band, feature cards (tonal surfaces), step cards
- CTA button variants (hero-primary, hero-ghost, gradient cta)
- Minimalist form inputs via `.surface-form` scope (handles both Dash v1 `.Select-control` and v2 `.Select__control`)
- Valuation panel, gradient result card, tonal comparable cards
- Amenities table with primary section headers
- `.methodology-card` with accent top border

`app.py`:
- Added Google Fonts to `external_stylesheets`
- Navbar color changed from `#2b2b2b` to `#00145d`
- Brand updated to `"PropertyMinBrothers"` + `"买房子 · 卖房子 · 找我们"` tagline

`pages/user_guide.py` — complete redesign:
- Full-bleed hero section (no outer container constraint)
- National KPIs computed from real DF at module load
- Hero data card (floating glass-effect on right column)
- Stats band with real KPI values
- Three feature cards (tonal surface, no shadows)
- Three step cards (how-to workflow) with ghost step numbers
- Quick reference legend cards
- Site footer with brand + data attribution

`pages/general_trends.py`:
- KPI cards use new `.kpi-card` / `.kpi-label` / `.kpi-value` CSS classes
- Controls panel uses `.controls-panel` class
- Town detail panel redesigned: Manrope headings, region/estate badge chips, town note text, accent chart colours (`#0f2885`, `#5bc8af`)
- Added `TOWN_META` dict: region, estate type, and description for all 26 towns
- Removed Bootstrap `border-bottom` dividers in breakdown rows — replaced with low-opacity border-bottom via inline style
- CTA "Value a Flat in This Area →" added to town panel
- Methodology card uses `.methodology-card` class (accent top border)

`pages/flat_valuation.py`:
- Form panel: replaced `bg-dark text-white` with `valuation-form-panel` + `surface-form`
- Form labels: removed `text-white-50` — now inherits `.form-label` styles
- dcc.Dropdown: removed `form-control border-0` class — styling comes from `.surface-form` scope
- Search button: replaced `color="primary"` with `className="btn-cta"`
- Result card: replaced `bg-danger` with `.result-card-gradient`, uses `.result-estimate-*` text classes
- Methodology note: `bg-light` → `background: #f4f2ff`, `borderLeft: 3px solid #00145d`
- Comparable cards: replaced `shadow-sm` with `.comp-card` tonal surface class
- Price highlight: replaced `text-success` with `color: #5bc8af`

`pages/amenities_comparison.py`:
- Page title uses `.page-header-title` / `.page-header-sub`
- Section header rows: inline `backgroundColor` updated to `#00145d` (literal hex — `var()` not valid in Dash inline style dicts)
- Header cells redesigned: Manrope font, RGBA white text for hierarchy
- Input: surface-high background, no border, `surface-form` scope
- Add button: `btn-cta` class (removed `color="success"`)
- Postal code hint added below input
- Empty state: premium centred layout with icon

---

## Pending / Next Steps

- **Wire up real amenities data**: once `hdb_with_amenities_macro.csv` has name columns populated, replace `MOCK_DATA` with a real geocode + nearest-amenity lookup in `manage_flats` callback.
- **Geocode integration**: OneMap postal-code lookup in the Add-flat callback for real distances.
- **Mobile layout**: currently desktop-first only.
- **Map integration**: Flat Valuation map uses Plotly scattermapbox (functional). General Trends choropleth requires `town_choropleth.geojson` in `outputs/`.
