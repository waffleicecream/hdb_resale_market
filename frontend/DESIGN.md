# DESIGN.md — Resale HDB Information & Valuation App

---

## 1. Global Design System

This document defines the visual language for all pages of the app. Every page must feel like part of the same product. Do not deviate from the global system unless explicitly noted as a page-specific override.

### 1.1 Color Palette

| Token | Hex | Usage |
|---|---|---|
| `--color-bg-primary` | `#FFFFFF` | Page backgrounds, cards, panels |
| `--color-bg-secondary` | `#F5F6F7` | Section breaks, alternating rows, canvas |
| `--color-accent` | `#1C4ED8` | CTA buttons, active states, links, badges |
| `--color-accent-hover` | `#1E40AF` | Button hover state |
| `--color-text-primary` | `#1A2E4A` | Headings, bold values |
| `--color-text-secondary` | `#6B7280` | Labels, captions, secondary info |
| `--color-text-muted` | `#9CA3AF` | Placeholder text, minor annotations |
| `--color-success` | `#16A34A` | Best badge, fair price, positive trend |
| `--color-success-bg` | `#F0FDF4` | Winning cell background tint |
| `--color-danger` | `#DC2626` | Overpriced indicator, negative trend |
| `--color-border` | `#E5E7EB` | Card borders, row dividers, input borders |
| `--color-shadow` | `rgba(0,0,0,0.06)` | Card and panel shadows |

### 1.2 Typography

- **Font family:** Inter (primary), fallback to system-ui, sans-serif
- **Headings:** Bold to ExtraBold weight, dark navy (`--color-text-primary`)
- **Body:** Regular weight, 15–16px, muted grey (`--color-text-secondary`)
- **Labels / small caps:** Uppercase, letter-spacing 0.08em, 11–12px, muted grey
- **Monospace:** Used sparingly for numeric data values (e.g. prices, distances)

| Element | Size | Weight |
|---|---|---|
| Page title (hero) | 48–56px | 800 |
| Section heading | 28–32px | 700 |
| Card title | 18–20px | 600 |
| Body text | 15–16px | 400 |
| Label / caption | 11–13px | 500, uppercase |
| Stat value (large) | 28–36px | 700 |

### 1.3 Spacing

- Base unit: 8px
- Section vertical padding: 80–96px
- Card internal padding: 24px
- Component gap (between cards): 24px
- Inline element gap: 8–12px

### 1.4 Components

**Navbar**
- White background, 1px bottom border (`--color-border`)
- Logo on the left, horizontal nav links in the center/right
- One solid CTA button in `--color-accent` on the far right
- Sticky on scroll

**Buttons**
- Primary: solid `--color-accent` background, white text, 6px border radius, 12px 24px padding
- Secondary: white background, `--color-border` border, dark text
- No rounded-full pill buttons except for filter tags and badges

**Cards**
- White background, `--color-border` border or subtle `--color-shadow`
- 8–12px border radius
- 24px internal padding
- No heavy drop shadows — keep it flat and clean

**Input / Search bar**
- White background, `--color-border` border, 6px border radius
- Search icon on the left inside the input
- Focus state: `--color-accent` border ring
- Paired with a solid blue CTA button on the right

**Badges**
- "Best" badge: small green pill, `--color-success` text, `--color-success-bg` background, checkmark icon, inline with value
- Period toggle: pill-style tab group, active state filled with `--color-accent`, inactive ghost

**Tables**
- No vertical column borders
- Thin horizontal row dividers (`--color-border`)
- Alternating row background: white / `--color-bg-secondary`
- Metric label column: small caps, `--color-text-secondary`
- Column headers: bold, dark navy, with sub-labels in muted grey below
- Winning cell: `--color-success-bg` tint on full cell

---

## 2. Page 1 — Landing Page

**Inspiration:** Open Government Products website (open.gov.sg)

### Hero Section
- Full-width dark gradient background (near-black left, fading to dark grey right)
- Large bold white headline on the left: `"Make Your Next Property Decision With Confidence"`
- Short white subtitle below the headline (1–2 lines)
- Inline search bar below the subtitle for quick valuation access (postal code + flat type + optional floor level)
- Right side of hero: floating HDB flat image or app UI preview screenshots, partially cropped at the bottom edge
- Generous vertical padding, headline font size 48–56px, ExtraBold

### Quick Valuation Search Bar (in hero)
- Dark-themed input fields consistent with the hero background
- Fields: Postal Code, Flat Type (dropdown), Floor Level (optional dropdown), Listed Price (optional)
- Solid blue "Get Valuation" button on the right
- On submission: redirect to Flat Valuation page with results pre-loaded

### Market Stats Dashboard
- White background section below the hero
- Section heading: bold navy, left-aligned
- 4–5 stat cards in a horizontal row, each card: white, subtle border, 24px padding
- Each card shows: small caps label, large bold value, period-on-period change in green or red with arrow
- Period toggle (3 months / 6 months / 1 year) as a pill tab group, top right of the section
- Stats: total transactions, median resale price, MoM price growth, hottest region (name + growth %), coolest region (name + decline %)

### Tool Overview Section
- Light grey background (`--color-bg-secondary`), generous vertical padding
- Section heading: bold navy, centered or left-aligned
- Three-column card layout, one card per tool
- Each card: image or icon at top, bold linked tool name with arrow (↗), short description below
- Cards link to respective tool pages
- Tools: Town Explorer, Flat Valuation, Amenities Comparison

---

## 3. Page 2 — Market Analysis (Town Explorer)

Two style options are provided. Choose one before implementation.

### Style A — Clean Data Journalism (Elections Map style; USE THIS ONE BY DEFAULT)

**Inspiration:** CNA / Straits Times GE2025 elections map

- White/light grey page background, no dark base map tiles
- Map rendered as flat filled SVG or GeoJSON polygons with white region borders
- Unselected regions: muted single-hue fill (light teal or light blue gradient scale)
- Selected/hovered region: full intensity color, slightly elevated with a subtle border highlight
- Color scale: single-hue gradient for directional metrics (e.g. light to dark blue for price growth); diverging red-to-blue for metrics that can go negative (e.g. price change %)
- Map controls: dropdown filter top-center, zoom +/- and reset buttons top-left of map, small and minimal
- Legend: bottom-left of map, gradient color bar with min/max labels
- Right statistics panel: white, slides in or is always visible, dark header bar with town name, structured stat cards and charts below
- Overall feel: newspaper data journalism, clean and trustworthy

### Style B — Dark Ops Dashboard (Global Threat Map style)

**Inspiration:** Valyu Global Threat Map

- Full dark Mapbox base map, street-level detail visible in dark grey
- Map occupies the full page width and height
- Right panel: dark floating drawer (#1A1A1A background), monospace or condensed sans-serif labels
- Filter tags: pill-shaped, outlined, white text on dark background
- Region highlights rendered as semi-transparent overlays on the dark base map
- Town markers or region fills in accent colors with glow effect on hover
- Panel typography: small caps labels, large bold stat values in white or teal
- Overall feel: technical ops dashboard, data-dense

### Shared Elements (both styles)
- Left: choropleth map of Singapore HDB towns
- Right: statistics panel — default shows national stats, updates to town stats on click
- Toggleable map layers: price change %, transaction count change %, median price, median price per sqft
- Period toggle: 3 months (default) / 6 months / 1 year
- Statistics panel content: median price, median psf, transaction count, period-on-period growth, historical trend graph with flat type toggles, most expensive flat, town executive summary, future developments

---

## 4. Page 3 — Flat Valuation

**Inspiration:** 99.co Property Value Tool / SRX X-Value

### Initial State (Pre-search)
- Light grey background with subtle dot/speckle texture pattern
- Centered layout, max-width content column
- Large bold dark navy title: e.g. `"How much is this flat worth?"`
- Smaller muted subtitle below
- Wide search bar: search icon left, postal code input, flat type dropdown, optional floor level dropdown, optional listed price field, solid blue "Get Valuation" button on the right
- Below search bar: 2–3 feature highlight cards in a row
  - White cards, subtle shadow, small icon top-center, bold navy card title, short grey description, blue "Read more" link at bottom
  - Cards describe what the tool does: price projection, comparable transactions, listed price indicator
- Typography: dark navy headings, muted grey body, blue accents

### Post-search State (Valuation Dashboard)
Inherits the same navy/white/blue color palette. Three-panel layout:

**Top Left Panel — Price Projection**
- White card, bold navy heading
- Price range displayed as a visual horizontal range bar (15th to 85th percentile)
- Range endpoints labeled in large bold navy text (e.g. `$480,000 — $540,000`)
- "Reasonable Projection" label with a small info icon that shows the disclaimer tooltip on hover
- If listed price provided: inline badge below the range — `Overpriced` (red), `Fair Price` (green), or `Underpriced` (blue)
- Flat details below: address, postal code, flat type, remaining lease — in a clean label/value grid

**Bottom Left Panel — Location Map**
- Embedded map (Mapbox or Leaflet) with a single pin at the flat's location
- Minimal map style (light grey tiles), no clutter
- Fixed height, full width of the left column

**Right Panel — Comparable Transactions**
- Divided into two sub-panels with a section label each
- Top: "Same Block / Nearby Transactions" — table with columns: flat type, floor range, month, price
- Bottom: "Similar Flats in Other Towns" — table with columns: flat type, month, price, town, address
- Tables: clean, alternating row shading, thin dividers, no vertical borders
- Muted grey column headers in small caps

---

## 5. Page 4 — Amenities Comparison

**Inspiration:** HDB comparison tools, cameradecision.com style side-by-side comparison tables

### Search Bar
- Centered at top of page, white background section
- Allows entry of up to 3 postal codes
- Each entered postal code adds a column (Flat A, Flat B, Flat C) to the comparison table below
- Input styled consistently with global search bar component

### Tab Navigation
- Pill-style tab bar below the search bar
- Tabs: "Nearest Amenities" and "Within 1km" (or toggles between comparison table and LLM summary)
- Active tab: filled `--color-accent` background, white text
- Inactive tabs: ghost style, `--color-text-secondary`

### Comparison Table
- Full-width white card with subtle border
- Small caps "METRIC" label for the left column header
- Column headers: bold all-caps street/block name, flat type and address in smaller muted text below
- Row structure:
  - Left column: metric name in muted grey (`--color-text-secondary`)
  - Data columns: value in dark navy, bold
  - Winning cell: `--color-success-bg` background tint, inline green "✓ Best" badge next to value
- Alternating row shading: white / `--color-bg-secondary`
- Thin horizontal dividers between rows, no vertical borders
- Positive trends: green text with upward arrow icon
- Sections divided by a slightly bolder divider row with a section label

**Section 1 rows (Nearest Amenity):** MRT Station, Shopping Mall, Hawker Centre, Polyclinic, Sports Hall — each showing name, distance, walking time

**Section 2 rows (Within 1km):** Primary Schools (list of names), Parks (list of names)

### LLM Summary Panel
- White card below the comparison table, full width
- Small caps label: "AI SUMMARY"
- Single paragraph of generated text in regular body style, dark navy
- Subtle left border accent in `--color-accent` (like a blockquote style)
- Small disclaimer below in muted grey: "Summary is based on retrieved amenity data only."

---

## 6. Design Don'ts

- Do not use rounded-full pill shapes for primary buttons or cards
- Do not use heavy drop shadows — keep elevation flat and subtle
- Do not use gradients in content sections (hero gradient is the only exception)
- Do not mix font families — Inter only
- Do not use red as a primary color — red is reserved strictly for negative indicators
- Do not add decorative illustrations or icons beyond simple functional icons
- Do not let any page feel visually disconnected from the others — navbar, typography, and card styles must be consistent across all four pages