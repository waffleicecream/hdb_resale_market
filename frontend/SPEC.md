# Resale HDB Information & Valuation App — Product Specification

---

## Overview

A resale HDB information and valuation tool designed to help buyers make informed property decisions. The app is positioned as a neutral, data-driven reference tool — not a property agent platform or recommendation engine. It consists of four pages: a Landing Page, a Market Analysis page (Town Explorer), a Flat Valuation page, and an Amenities Comparison page.

The targetted audience of the application is the general public, specifically those intending to purchase resale HDBs in the future and wants a tool that consolidates information, and help them with decision making in the various stages of the purchase - from shortlisting flats from listings, to checking the predicted valuation of the flats.

---

## Page 1: Landing Page

### Purpose
Introduce the app, provide immediate utility via an inline valuation search, surface key market stats, and orient users to the three tools available.

### Layout & Sections

#### 1.1 Hero Section
- Large title: **"Make Your Next Property Decision With Confidence"**
- Short subtitle describing the app as a resale HDB information and valuation tool
- HDB flat image on the right side (OGP-style layout, dark/muted aesthetic)
- Inline search bar below the title for quick valuation access (see 1.2)

#### 1.2 Quick Valuation Search Bar
Allows users to get a flat valuation directly from the landing page without navigating to the valuation page first.

**User Inputs:**
| Field | Type | Required |
|---|---|---|
| Postal Code | Text (6-digit) | Yes |
| Flat Type | Dropdown (3-room, 4-room, 5-room, Executive, etc.) | Yes |
| Floor Level | Dropdown (Low / Mid / High) or numeric | Optional |
| Listed Price | Numeric (SGD) | Optional |

On submission, user is redirected to the Flat Valuation page with results pre-loaded.

#### 1.3 Resale Market Stats Dashboard
A simple, scannable dashboard displaying national-level HDB resale market statistics. Default period is the past 3 months rolling, toggleable to 6 months or 1 year.

**Stats displayed:**
- Total transactions (current period vs previous period, % change)
- Median resale price (current period vs previous period, % change)
- Month-on-month price growth rate (rolling period)
- Hottest region: town with the highest price growth % in the period (shown with transaction count and price growth %)
- Coolest region: town with the largest price decline % in the period (shown with transaction count and price decline %)

**Note:** Hottest and coolest regions require a minimum transaction threshold (e.g. 10 transactions in the period) to filter out statistical noise from low-volume towns.

**Period toggle:** 3 months (default) | 6 months | 1 year

**Backend data required:**
- HDB Resale Flat Prices dataset (data.gov.sg)
- Aggregated by town and period on the backend

#### 1.4 Tool Overview Flowchart
A horizontal flowchart-style graphic (similar to OGP screenshot 2 style) showing how the three tools fit into a typical buyer's research journey. One block per tool, framed as "how buyers typically research" rather than a prescriptive buying funnel.

**Three blocks:**
1. **Town Explorer** — Explore towns by price trends, transaction activity, and local characteristics
2. **Flat Valuation** — Get a data-driven price projection for a specific flat
3. **Amenities Comparison** — Compare nearby amenities across up to 3 flats side by side

Each block links to its respective page.

---

## Page 2: Market Analysis (Town Explorer)

### Purpose
Allow users to explore HDB resale market trends across all Singapore towns using an interactive choropleth map and a statistics panel.

### Layout
Two-column layout: map on the left, statistics panel on the right.

### 2.1 Choropleth Map (Left Panel)
- Displays all HDB towns in Singapore as geographic regions
- Default layer: price change % over the past 3 months
- Clicking a town highlights it and updates the right statistics panel

**Toggleable map layers:**
- Price change % (default)
- Change in number of transactions %
- Median transaction price (SGD)
- Median price per square foot (SGD/sqft)

**Period toggle:** 3 months (default) | 6 months | 1 year (applies to all layers)

**Backend data required:**
- HDB Resale Flat Prices dataset aggregated by town and period
- GeoJSON boundaries for HDB towns (from data.gov.sg or OneMap)

### 2.2 Statistics Panel (Right Panel)
Default state shows national statistics. When a town is clicked on the map, the panel updates to show town-specific statistics.

**Statistics shown (national or town-level):**
- Median resale price and median price per sqft
- Number of transactions
- Period-on-period growth rate for both price and transaction count
- Historical price trend graph with toggleable lines per flat type (3-room, 4-room, 5-room, Executive)
- Most expensive flat in the past period (by total price and by price per sqft), showing address, flat type, and transacted price
- Executive summary of the town (hardcoded text sourced from URA Masterplan and development news), covering unique characteristics such as proximity to transport hubs, schools, nature reserves, or industrial areas
- Summary of notable future developments in the town (hardcoded, sourced from URA Masterplan)

**Period toggle:** 3 months (default) | 6 months | 1 year (consistent with map toggle)

**Backend data required:**
- HDB Resale Flat Prices dataset
- Hardcoded town summaries and development notes (manually maintained)

---

## Page 3: Flat Valuation

### Purpose
Provide a data-driven price projection for a specific HDB resale flat based on user inputs and enriched hedonic features derived from the postal code.

### Layout
Three-panel dashboard revealed after search submission.

### 3.1 Search Bar (Initial State)
The page loads as a clean search bar. After submission, the dashboard appears below or replaces the search bar.

**User Inputs:**
| Field | Type | Required |
|---|---|---|
| Postal Code | Text (6-digit) | Yes |
| Flat Type | Dropdown | Yes |
| Floor Level | Dropdown (Low / Mid / High) or numeric | Optional |
| Listed Price | Numeric (SGD) | Optional |

Floor level mapping for model input (when categorical input is used):
- Low → storey midpoint ~3
- Mid → storey midpoint ~8
- High → storey midpoint ~15

### 3.2 Flat Details (Shown with Valuation Panel)
Automatically populated from postal code lookup (HDB API / OneMap):
- Full address
- Postal code
- Flat type (confirmed)
- Remaining lease (years)

**Backend data required:** HDB API or OneMap API to resolve postal code to block-level details and remaining lease.

### 3.3 Top Left Panel — Price Projection
- Displays the predicted price range (15th to 85th percentile) as a visual range bar
- Labels the range clearly as a "Reasonable Projection" with a disclaimer:
  > *Actual transacted prices may vary based on home condition, renovation quality, facing direction, and negotiation. This projection is based on historical transaction data and should be used as a reference only.*
- If listed price is provided, shows one of three indicators:
  - **Overpriced** — listed price is above the 85th percentile
  - **Fair Price** — listed price falls within the projected range
  - **Underpriced** — listed price is below the 15th percentile

**Backend model required:**
- Two CatBoost models trained with quantile loss (alpha=0.15 and alpha=0.85)
- Features: flat type, remaining lease, town (from postal code), floor level (if provided), hedonic features extracted from postal code (proximity to MRT, storey band, etc.)
- Hedonic features resolved at prediction time via OneMap API
- Training features must match live inference features exactly

### 3.4 Bottom Left Panel — Location Map
- Small embedded map showing the pin location of the flat
- Based on coordinates resolved from postal code via OneMap

### 3.5 Right Panel — Comparable Transactions
Divided into two sub-panels:

**Top sub-panel: Same Block / Nearby Block Transactions**
Past transactions of the same flat type at the same postal code or nearby blocks (partial postal code match or radius-based).

Columns shown per transaction:
- Flat type
- Month of transaction
- Transacted price (SGD)
- Floor range (if available)

**Bottom sub-panel: Similar Flats in Other Towns**
Past transactions of comparable flats in other towns. Similarity is defined by: flat type, remaining lease (within ±5 years), and amenity profile similarity score.

Columns shown per transaction:
- Flat type
- Month of transaction
- Transacted price (SGD)
- Town
- Address

**Backend data required:**
- HDB Resale Flat Prices dataset
- Remaining lease and amenity data for similarity scoring

---

## Page 4: Amenities Comparison

### Purpose
Allow users to compare the amenity profiles of up to 3 HDB flats side by side, with an LLM-generated summary of the comparison.

### Layout
Search bar at top, comparison table in the middle, LLM summary panel at the bottom.

### 4.1 Search Bar
Users enter up to 3 postal codes. Each postal code adds a column to the comparison panel. Columns are labelled Flat A, Flat B, Flat C with the resolved address shown below each label.

### 4.2 Comparison Panel
Two sections displayed side by side for each flat:

**Section 1 — Nearest Amenity (distance and walking time)**
| Amenity | Flat A | Flat B | Flat C |
|---|---|---|---|
| MRT Station | Name, distance, walking time | ... | ... |
| Shopping Mall | Name, distance, walking time | ... | ... |
| Hawker Centre | Name, distance, walking time | ... | ... |
| Polyclinic | Name, distance, walking time | ... | ... |
| Sports Hall | Name, distance, walking time | ... | ... |

For each amenity row, the column with the shortest distance is highlighted with a "Nearest" indicator badge.

**Section 2 — Within 1km**
| Category | Flat A | Flat B | Flat C |
|---|---|---|---|
| Primary Schools | List of names | ... | ... |
| Parks | List of names | ... | ... |

**Backend data required:**
- OneMap API or Google Maps API for distance and walking time calculations
- MOE school register for primary schools within 1km radius
- NParks dataset or OpenStreetMap for parks
- HDB/commercial datasets for malls, hawker centres, polyclinics, sports halls

### 4.3 LLM Summary Panel
An AI-generated paragraph summarising the amenity comparison across the entered flats. The summary is grounded strictly in the amenity data retrieved and does not make subjective lifestyle recommendations.

**Summary structure (example):**
> Flat A, Flat B, and Flat C are all located in the north region of Singapore. Flat A is the closest to an MRT station at Yishun MRT, offering convenient access to public transport. Flat B is situated near Northpoint City, with a major shopping mall within walking distance. Flat C has the highest concentration of primary schools within 1km, including schools such as Huamin Primary and Jiemin Primary.

**LLM prompt constraints:**
- Only reference data returned by the amenities API calls
- Do not infer school quality, mall quality, or neighbourhood character beyond what the data shows
- Use region inference from postal code (north/south/east/west/central) for geographic context
- Output a single concise paragraph, no bullet points

**Backend required:**
- Anthropic Claude API (claude-sonnet) called server-side with the structured amenities data as context

---

## Data Sources Summary

| Data | Source |
|---|---|
| HDB resale transaction history | data.gov.sg — Resale Flat Prices |
| Postal code to address/coordinates | OneMap API (Singapore) |
| Remaining lease | HDB API or computed from lease commencement date |
| Town GeoJSON boundaries | data.gov.sg or OneMap |
| Primary schools | MOE school register (data.gov.sg) |
| Parks | NParks dataset or OpenStreetMap |
| Hawker centres | NEA dataset (data.gov.sg) |
| Polyclinics | MOH dataset (data.gov.sg) |
| MRT stations | LTA DataMall |
| Shopping malls / Sports halls | OneMap POI search or Google Places API |
| Future developments / Town summaries | Hardcoded, sourced from URA Masterplan |
| LLM summary generation | Anthropic Claude API |

---

## Model Summary

| Model | Purpose | Method |
|---|---|---|
| Price projection (lower bound) | 15th percentile price estimate | CatBoost with `Quantile:alpha=0.15` |
| Price projection (upper bound) | 85th percentile price estimate | CatBoost with `Quantile:alpha=0.85` |
| Similarity scoring (comparable flats) | Match flats across towns | Rule-based: flat type + remaining lease (±5 years) + amenity profile |
