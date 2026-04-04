# Market Analysis Page — Amendments

Apply the following amendments to the previously generated `preprocess_market.py` and `market_analysis.py`.

---

## Amendment 1: Panel Width Ratio

Change the left/right panel split from 50/50 to **40/60** (map on left at 40%, stats panel on right at 60%).

---

## Amendment 2: Combined Monthly/Quarterly Price Chart

Replace the two separate monthly and quarterly price charts with a **single combined chart** that is toggle-able between the two views.

- Add a small toggle (two styled buttons: "Monthly" and "Quarterly") above or inside the chart card
- Switching the toggle swaps the data displayed in the same Plotly figure
- The chart title should update to reflect the active view
- Both monthly and quarterly data are still read from `market_stats.json` as previously computed — no changes to the preprocessing output needed

---

## Amendment 3: Town Description and Future Developments (Two Separate Sections)

Replace the single "About This Town" section with **two distinct sections**:

### Section 1 — "About [Town Name]"

- Title format: `About [Town Name]` (e.g. "About Bishan"), or `About Singapore` for national view
- Content: a pre-generated paragraph describing the town's character and qualities, covering aspects such as:
  - General location and character (mature/new estate, residential density)
  - Notable amenities, landmarks, and green spaces
  - MRT/transport connectivity
  - Community identity and lifestyle
  - Typical resident profile or demand profile
- This description must be **generated and stored during the preprocessing step**, not at runtime
- Add a new top-level key `"town_about"` in `market_stats.json` with town names as keys and the paragraph string as values
- For the national view, store a general overview of the Singapore HDB resale market under the key `"NATIONAL"`
- Write these descriptions directly in `preprocess_market.py` as a hardcoded dictionary (one paragraph per town, covering all HDB towns), then write them into the JSON — do not call an external API

### Section 2 — "Future Developments"

- Title: `Future Developments`
- Content: a pre-generated fluent prose summary of upcoming transport infrastructure for the town, drawn from:
  - `outputs/future_mrt_stations_for_frontend.csv` (columns: `town, station_name, line, line_code, expected_year, status, lat, lon, notes`)
  - `outputs/future_transport_hubs_for_frontend.csv` (columns: `town, hub_name, hub_type, expected_year, status, notes`)
- The summary should read as natural prose, not a bullet list — e.g. "Bishan is set to benefit from the upcoming [Station] on the [Line], expected to open in [Year]. Additionally, a new [hub type] at [hub name] is planned..."
- This summary must also be **generated and stored during the preprocessing step** under the existing `"town_descriptions"` key (rename this key to `"town_future_developments"` for clarity)
- If a town has no entries in either file, store: `"No upcoming transport developments have been announced for this town."`
- For the national view, store a general sentence about the national transport development pipeline under key `"NATIONAL"`

Both sections should be displayed in the right panel below the charts, in order: About section first, Future Developments second. Style both as labelled text sections consistent with the existing panel design.

---

## Amendment 4: Highest/Lowest Priced Transaction Card Formatting

Reformat the highest and lowest priced transaction display from a single inline string into a **structured stacked layout**:

```
Block [block] [street_name]          ← slightly larger font, e.g. font-size: 14px, font-weight: 600
[flat_type]                          ← standard label font, e.g. font-size: 12px, color: muted
[storey_range]                       ← standard label font
$[resale_price formatted with commas] ← slightly larger font, e.g. font-size: 14px, font-weight: 700, accent colour
```

- Each of the four rows is a separate `html.P` or `html.Div` element with its own className for styling
- Suggested classNames: `txn-address`, `txn-flat-type`, `txn-storey`, `txn-price`
- Apply this formatting to both the highest and lowest transaction cards
- The card headers ("HIGHEST PRICED TRANSACTION" and "LOWEST PRICED TRANSACTION") remain unchanged