# Flat Valuation Tab — Design Spec (v4)

Reference layout: screenshot shared 2026-04-03.
This is the canonical spec. Implement against this; ignore previous change-instruction docs.

---

## Layout Overview

```
┌─────────────────────────────────────────────────────────┐
│  INPUT BAR (always visible at top)                       │
├───────────────────────┬─────────────────────────────────┤
│  TOP-LEFT             │  TOP-RIGHT                       │
│  Price Prediction     │  Historical Price Reference      │
│  + Premium Bar        │  [Chart on top]                  │
│  + Metadata           │  [Scrollable transactions below] │
│  + Insight            │                                  │
├───────────────────────┴─────────────────────────────────┤
│  [OVERPRICED BANNER — conditional, amber, full width]    │
├───────────────────────┬─────────────────────────────────┤
│  BOTTOM-LEFT          │  BOTTOM-RIGHT                    │
│  Location Map         │  Current Market Alternatives     │
│                       │  [Scrollable card list]          │
└───────────────────────┴─────────────────────────────────┘
```

- All 4 panels always visible (bottom row is not conditional).
- Overpriced banner renders between top row and bottom row only when verdict = OVERPRICED.
- Grid columns: 45% left / 55% right (both rows).

---

## INPUT BAR

Always visible sticky bar at the top of the results view.

Fields (horizontal, compact):
1. Postal Code — text input
2. Flat Type — dropdown (2-Room, 3-Room, 4-Room, 5-Room, Executive)
3. Storey Level — dropdown (Low 01–05 / Medium 06–12 / High 13+)
4. Remaining Lease — dropdown (Under 60 yrs / 60–75 yrs / 75–90 yrs / Over 90 yrs)
5. Listed Price (optional) — number input
6. Get Valuation — primary button (dark navy, white text)

---

## TOP-LEFT PANEL — Price Prediction

### Header row
- Left: "ESTIMATED CURRENT PRICE" (small caps label)
- Right: Verdict badge (OVERPRICED / FAIR VALUE / GOOD DEAL) — only if listing price entered

### Predicted price (from model)
- Large bold number: midpoint = (p15 + p85) / 2
- Below: "Range: $X — $Y" (p15 to p85)
- Below: italic source line "Calculated based on N recent transactions on this street."

### Listed price row (only if entered)
- "Listed at $X" — colour matches verdict (red / grey / green)

### Market Premium Bar
Shows where the listed price sits on the UNDERPRICED → FAIR VALUE → OVERPRICED spectrum.

- Label row: "Market Premium" (left) | "+X%" or "-X%" (right, coloured by verdict)
- Bar: gradient background (green → blue → red zones), filled from left to marker position
- Marker: vertical line at listing price position (coloured by verdict)
- Labels below bar: UNDERPRICED | FAIR VALUE | OVERPRICED
- Below bar: one-line plain English e.g. "Listed $40,000 above the top of the predicted range."
- If no listing price: italic placeholder "Enter a listed price above to see the market premium."

Position formula:
  - Extended range: from p15 − (p85−p15) to p85 + (p85−p15)
  - Position % = (listing_price − low) / (high − low) × 100, clamped 2–98%

Percentage formula: (listing_price − midpoint) / midpoint × 100

### Lease Warning (conditional, below premium bar)
  - "60-75 years" → yellow banner (#FFF8E1 bg, #F57F17 text):
    "⚠️ Lease Advisory: Flats below 75 years may face stricter bank loan conditions."
  - "Under 60 years" → red banner (#FFEBEE bg, #C62828 text):
    "🚨 Lease Warning: Not eligible for HDB loans. CPF usage restricted."

### Flat Metadata Grid (2×3)
ADDRESS | POSTAL CODE
FLAT TYPE | REMAINING LEASE
STOREY BIN | TOWN

### Valuation Insight Box
Grey background box. Dynamic text:
- OVERPRICED: "The listed price of $X is $Y above our predicted fair value range for [type] flats in [town]. Recent transactions closed between $min and $max. Consider negotiating or exploring the alternatives below."
- FAIR VALUE: "The listed price of $X falls within our predicted fair value range for [type] flats in [town]. This appears reasonably priced based on N recent transactions."
- GOOD DEAL: "The listed price of $X is $Y below our predicted fair value range. This may represent good value — similar units have transacted at higher prices. Act promptly."
- No price entered: "Enter a listed price above to receive your valuation verdict."

---

## TOP-RIGHT PANEL — Historical Price Reference

Header: "HISTORICAL PRICE REFERENCE" (small caps)
Sub: "Same street · same storey bin · same flat type" (italic)

### Chart (top, fixed ~220px height)
- Quarterly avg price line chart, past 3 years
- Green dashed line: predicted fair value midpoint (labelled)
- Red dashed line: listing price (labelled) — only if entered
- Hover: "[Quarter] | Avg $X | N transactions"
- Caption below: "Average transaction price — same street, same flat type, same storey bin"

### Past Transactions Table (below chart, scrollable)
- Section label: "PAST TRANSACTIONS" (small caps divider)
- Columns: MONTH | STOREY | FLAT TYPE | PRICE
- Sort: most recent first. Max 10 rows.
- Scrollable container: max-height ~220px, overflow-y auto
- Fallback: if < 3 rows, show orange notice banner and widen to town-level data

---

## OVERPRICED BANNER (conditional)

Only renders when verdict = OVERPRICED.

Style: amber (#FFF3E0 bg, 4px left border #E65100, dark orange text)
Content:
- "⚠️ Overpriced? Check out potential alternatives below"
- Sub: "Current listings matched on flat type, storey level, and remaining lease — sorted by similarity."

---

## BOTTOM-LEFT PANEL — Location Map

Header: "LOCATION INTELLIGENCE" (small caps)

Pins:
- Blue pin + "Your flat" text label below = user's searched flat
- Green numbered pins = current alternative listings (numbered by similarity rank)

Hover tooltip on green pins:
- "#N Blk X Street"
- "Asking: $X"
- "Y% Match"

Legend below map:
- 📍 Blue = Your flat
- 🟢 Numbered = Current alternatives (ranked)

Basemap: light (carto-positron). Auto-centers on all pins.

---

## BOTTOM-RIGHT PANEL — Current Market Alternatives

Header (dark navy bg, white text):
- "CURRENT MARKET ALTERNATIVES"
- Sub: "Matched on flat type · storey bin · remaining lease bin · Ranked by similarity"

Listing cards (scrollable container, max-height ~460px):

Each card layout (horizontal flex):
```
[RANK CIRCLE] [ADDRESS + TYPE + STOREY + LEASE + MATCH REASONS]  [PRICE + VALUE SIGNAL]
              [MATCH %]
```

Fields per card:
- Rank circle (dark navy bg, white number)
- Match % (green, bold) below rank
- Address: "Blk X Street" (bold)
- Sub-line: "4-Room · Medium 06–12 · 67 years remaining"
- Match reasons: "Same storey · Same lease" (italic, muted)
- Price: large bold monospace
- Value signal: "✓ Within fair value range" (green) or "⚠️ Also overpriced" (red)
- Inactive listing: "Listing may have been sold" (italic, muted)

No "View on HDB" button.

Show all listings returned (scrollable). No expand/collapse needed.

---

## Similarity Ranking (backend)
Hard filter: flat_type must match exactly.
Score (max 6):
- storey_level_bin: exact=2, adjacent=1, no match=0
- remaining_lease_bin: exact=2, adjacent=1, no match=0
- distance: <1km=2, 1–3km=1, >3km=0
Sort: descending score, tiebreak lowest price.
Match % = round(score/6 × 100, nearest 5%).

---

## Flat Types (global)
Only: 2-Room, 3-Room, 4-Room, 5-Room, Executive
Remove 1-Room and Multi-Generation everywhere.
