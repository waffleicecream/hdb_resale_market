# Amenities Comparison Tab — Design Spec (v1)

Reference layout: screenshot shared 2026-04-03.
This is the canonical spec for the redesigned amenities comparison page.

---

## Page Header

- Small caps label: "PREMIUM EDITORIAL GUIDE" (bordered pill badge)
- H1: "Location Intelligence Dashboard"
- Subtitle: "Analyze lifestyle proximity metrics across multiple properties. Our institutional-grade data evaluates walkability, transport efficiency, and essential service accessibility."

---

## Input Bar

Label: "COMPARE UP TO 3 FLATS"
Layout: horizontal flex, grey background box.

Fields:
1. Postal code text input — with location pin icon on left
2. Flat A / Flat B / Flat C pill tags with × remove button. Active (most recently added) tag is highlighted blue.
3. Buttons: **Add Flat** (primary, dark navy) · **Load Demo** (secondary) · **Clear All** (secondary)

---

## Flat Cards Row (3-column grid)

Appears at the top of the results section, one card per flat (Flat A / B / C).

Each card:
- Image/placeholder (tall rectangle, 160px height; grey placeholder if no image)
- TOWN (small caps, muted)
- Address (bold, 15px)
- Demand zone badge (dot + label):
  - 🟢 "High Demand Zone" — green pill
  - ⚫ "Market Average" — grey pill
  - 🔴 "Limited Supply Area" — red pill

If postal code not found: show "Block not found" with muted placeholder.

---

## Category Sections (4 sections)

Each section: full-width, left label column + 3 flat columns.

### 1. CONNECTIVITY — MRT & LRT Transit
Metric: nearest MRT/LRT station
- Show: name, distance (Xm / X min walk)
- Progress bar + rating label
- BEST badge on lowest distance flat

### 2. RETAIL & FOOD — Shopping & Hawkers
Two sub-rows:
- Shopping Mall (nearest)
- Hawker Centre (nearest)
Same display pattern as above.

### 3. WELLNESS — Health & Sports
Two sub-rows:
- Polyclinic (nearest)
- Sports Hall (nearest)

### 4. EDUCATION — Primary Schools
- Bullet list of schools within 1km
- Filled green dot = within 1km
- Empty circle = not available (shown when fewer than expected)

---

## Proximity Rating System

### Thresholds (for hover tooltip on rating label)
| Amenity | Exceptional | Good | Below Average | Poor |
|---------|------------|------|---------------|------|
| MRT/LRT | < 400m | 400–800m | 800m–1.2km | > 1.2km |
| Shopping Mall | < 500m | 500m–1km | 1–1.5km | > 1.5km |
| Hawker Centre | < 200m | 200–400m | 400–700m | > 700m |
| Polyclinic | < 500m | 500m–1km | 1–2km | > 2km |
| Sports Hall | < 600m | 600m–1.2km | 1.2–2km | > 2km |

### Visual rating display
- Progress bar: Exceptional (100%, green) · Good (75%, blue) · Below Average (45%, amber) · Poor (15%, red)
- Rating label coloured to match

---

## Bottom Section

### Left: Location Map
- Plotly Scattermapbox, carto-positron basemap
- Green pins at each flat's lat/lon
- Hover: address
- Distance legend: green dot = under 500m, blue dot = 500m–1km

### Right: Institutional Verdict
Header: "Institutional Verdict"
- AI-generated summary paragraph; flat names highlighted (bold, blue)
- Two stat boxes:
  - AVG. PROXIMITY SCORE (X.X out of 10)
  - BEST WALK TO MRT (X min)
- Formula breakdown box:
  "Evaluating all metrics equally: (MRT + Shopping + Hawker + Polyclinic + Sports) ÷ 5 metrics × 10"
  Scoring: Exceptional = 3, Good = 2, Below Average = 1, Poor = 0. Score = avg/3 × 10.
- "Generate Full Amenities Report (PDF)" — dark navy full-width button

---

## Proximity Score Calculation

Per flat:
1. Score each of 5 metrics: Exceptional=3, Good=2, Below Average=1, Poor=0
2. avg_raw = sum(scores) / 5
3. proximity_score = avg_raw / 3 × 10 (rounds to 1 decimal)

Displayed as "X.X/10" in stat box. Average proximity score across all loaded flats shown in the verdict section.

---

## Data Contract (API / Output Folder Format)

Backend must produce JSON matching this schema per lookup:

```json
{
  "flats": {
    "Flat A": {
      "postal_code": "string (6 digits)",
      "address": "string e.g. 'Blk 58 Lor 4 Toa Payoh'",
      "town": "string e.g. 'Toa Payoh'",
      "flat_type": "string e.g. '4-Room'",
      "demand_zone": "one of: 'High Demand Zone', 'Market Average', 'Limited Supply Area'",
      "image_url": "string URL or null",
      "lat": "float WGS84",
      "lon": "float WGS84"
    }
  },
  "nearest": {
    "Flat A": {
      "mrt_station":   { "name": "string", "distance_m": int, "walk_min": int },
      "shopping_mall": { "name": "string", "distance_m": int, "walk_min": int },
      "hawker_centre": { "name": "string", "distance_m": int, "walk_min": int },
      "polyclinic":    { "name": "string", "distance_m": int, "walk_min": int },
      "sports_hall":   { "name": "string", "distance_m": int, "walk_min": int }
    }
  },
  "within_1km": {
    "Flat A": {
      "primary_schools": ["string", ...],
      "parks": ["string", ...]
    }
  },
  "proximity_thresholds": {
    "mrt_station":   [400, 800, 1200],
    "shopping_mall": [500, 1000, 1500],
    "hawker_centre": [200, 400, 700],
    "polyclinic":    [500, 1000, 2000],
    "sports_hall":   [600, 1200, 2000]
  },
  "llm_summary": "string — AI generated verdict text"
}
```

### Backend swappability
- Set env var `AMENITIES_DATA_PATH` to point to the backend output JSON.
- Falls back to `frontend/mock_data/amenities_demo.json` if not set.
- The frontend rendering functions only consume the above schema — they are source-agnostic.

---

## Not-Found Handling

If a postal code is not found in the data source:
- Flat card shows "Block not found" address with muted styling
- All metric cells show "—" (dash) in that column
- Flat is excluded from proximity score average
