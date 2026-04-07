import json
import pandas as pd
import dash
from dash import html, dcc, callback, Output, Input, State, no_update, ALL, ctx
import os

dash.register_page(__name__, path="/amenities-comparison", name="Amenities Comparison")

_BASE = os.path.dirname(os.path.dirname(__file__))
_MERGED = os.path.join(os.path.dirname(_BASE), "merged_data")

# ── Demo data (kept for Load Demo button) ─────────────────────
with open(os.path.join(_BASE, "mock_data", "amenities_demo.json"), encoding="utf-8") as f:
    DEMO = json.load(f)

FLAT_LABELS = ["Block A", "Block B", "Block C"]
DEMO_POSTALS = [fd["postal_code"] for fd in DEMO["flats"].values()]

# ── Backend data: load once at startup ────────────────────────
# Build a block+street → amenity lookup from both enriched datasets
_WALK_SPEED_MPS = 83  # metres per minute (~5 km/h)

def _load_amenity_lookup():
    """Return dict keyed by (block_upper, street_upper) → row dict."""
    frames = []
    for path in [
        os.path.join(_MERGED, "[PAST_TRANSACTIONS]hdb_with_amenities_macro.csv"),
        os.path.join(_MERGED, "hdb_with_amenities_macro_2026.csv"),
    ]:
        if os.path.exists(path):
            df = pd.read_csv(path, low_memory=False)
            frames.append(df)
    if not frames:
        return {}
    combined = pd.concat(frames, ignore_index=True)
    # Keep one row per block+street (latest data wins — 2026 appended last)
    combined = combined.drop_duplicates(subset=["block", "street_name"], keep="last")
    lookup = {}
    for _, row in combined.iterrows():
        key = (str(row["block"]).upper().strip(),
               str(row["street_name"]).upper().strip())
        lookup[key] = row.to_dict()
    return lookup

# postal_code → (block, street) from hdb_2026_enriched
def _load_postal_lookup():
    path = os.path.join(os.path.dirname(_BASE), "data", "hdb_2026_enriched.csv")
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path, usecols=["postal_code", "block", "street", "town"])
    df["postal_code"] = df["postal_code"].astype(str).str.strip()
    lookup = {}
    for _, row in df.iterrows():
        pc = row["postal_code"]
        if pc not in lookup:
            lookup[pc] = {
                "block": str(row["block"]).upper().strip(),
                "street": str(row["street"]).upper().strip(),
                "town": row["town"],
                "address": f"Blk {row['block']} {row['street']}",
                "postal_code": pc,
            }
    return lookup

_AMENITY_LOOKUP = _load_amenity_lookup()
_POSTAL_LOOKUP  = _load_postal_lookup()

_POSTAL_OPTIONS = [
    {"label": f"{p}  —  {meta['address']}, {meta['town']}", "value": p}
    for p, meta in sorted(_POSTAL_LOOKUP.items())
    if (meta["block"], meta["street"]) in _AMENITY_LOOKUP
]


def lookup_flat_by_postal(postal):
    """
    Returns (flat_meta, nearest_dict, within_dict) for a postal code,
    or (None, {}, {}) if not found.
    flat_meta matches the shape used by the UI builders.
    nearest_dict keys: mrt_station, shopping_mall, hawker_centre, polyclinic, sports_hall
    within_dict keys: primary_schools (list of str)
    """
    meta = _POSTAL_LOOKUP.get(str(postal).strip())
    if not meta:
        return None, {}, {}

    row = _AMENITY_LOOKUP.get((meta["block"], meta["street"]))
    if row is None:
        # Return address metadata but no amenity data
        return meta, {}, {}

    def walk_min(dist_m):
        return max(1, round(dist_m / _WALK_SPEED_MPS))

    nearest = {}

    mrt_dist = row.get("nearest_train_dist_m")
    if pd.notna(mrt_dist):
        nearest["mrt_station"] = {
            "name": str(row.get("nearest_train_name", "MRT Station")),
            "distance_m": int(mrt_dist),
            "walk_min": walk_min(mrt_dist),
        }

    hawker_dist = row.get("dist_nearest_hawker_m")
    if pd.notna(hawker_dist):
        nearest["hawker_centre"] = {
            "name": str(row.get("nearest_hawker_name", "Hawker Centre")),
            "distance_m": int(hawker_dist),
            "walk_min": walk_min(hawker_dist),
        }

    mall_dist = row.get("dist_nearest_mall_m")
    if pd.notna(mall_dist):
        nearest["shopping_mall"] = {
            "name": str(row.get("nearest_mall_name", "Shopping Mall")),
            "distance_m": int(mall_dist),
            "walk_min": walk_min(mall_dist),
        }

    sports_dist = row.get("dist_nearest_sportsg_m")
    if pd.notna(sports_dist):
        nearest["sports_hall"] = {
            "name": str(row.get("nearest_sportsg_name", "Sports Hall")),
            "distance_m": int(sports_dist),
            "walk_min": walk_min(sports_dist),
        }

    healthcare_dist = row.get("dist_nearest_healthcare_m")
    if pd.notna(healthcare_dist):
        nearest["polyclinic"] = {
            "name": str(row.get("nearest_healthcare_name", "Polyclinic")),
            "distance_m": int(healthcare_dist),
            "walk_min": walk_min(healthcare_dist),
        }

    # Within 1km
    schools_raw = row.get("primary_schools_1km", "")
    schools = [s.strip().title() for s in str(schools_raw).split("|") if s.strip() and s.strip().lower() != "nan"]

    parks_raw = row.get("parks_1km", "")
    parks = [s.strip().title() for s in str(parks_raw).split("|") if s.strip() and s.strip().lower() != "nan"]

    within = {"primary_schools": schools, "parks": parks}

    return meta, nearest, within

# ── Proximity thresholds (walk minutes) ───────────────────────
# Format: [exceptional_max, good_max, below_average_max]
# Walk time is used for rating (more intuitive than raw metres)
# Thresholds in MINUTES:
#   MRT:      Exceptional <5 min · Good 5–10 min · Below Average 10–15 min · Poor >15 min
#   Shopping: Exceptional <7 min · Good 7–12 min · Below Average 12–18 min · Poor >18 min
#   Hawker:   Exceptional <3 min · Good 3–6 min  · Below Average 6–10 min  · Poor >10 min
#   Polyclinic: Exceptional <7 min · Good 7–13 min · Below Average 13–25 min · Poor >25 min
#   Sports:   Exceptional <8 min · Good 8–15 min · Below Average 15–25 min · Poor >25 min
DEFAULT_THRESHOLDS_MIN = {
    "mrt_station":   [5,  10, 15],
    "shopping_mall": [7,  12, 18],
    "hawker_centre": [3,   6, 10],
    "polyclinic":    [7,  13, 25],
    "sports_hall":   [8,  15, 25],
}

AMENITY_DISPLAY_LABELS = {
    "mrt_station":   "MRT Station",
    "shopping_mall": "Shopping Mall",
    "hawker_centre": "Hawker Centre",
    "polyclinic":    "Polyclinic",
    "sports_hall":   "Sports Hall",
}

# Tooltip shown on hover of each rating label
RATING_TOOLTIP = {
    "mrt_station":   "Exceptional: <5 min walk · Good: 5–10 min · Below Average: 10–15 min · Poor: >15 min",
    "shopping_mall": "Exceptional: <7 min walk · Good: 7–12 min · Below Average: 12–18 min · Poor: >18 min",
    "hawker_centre": "Exceptional: <3 min walk · Good: 3–6 min · Below Average: 6–10 min · Poor: >10 min",
    "polyclinic":    "Exceptional: <7 min walk · Good: 7–13 min · Below Average: 13–25 min · Poor: >25 min",
    "sports_hall":   "Exceptional: <8 min walk · Good: 8–15 min · Below Average: 15–25 min · Poor: >25 min",
}

SECTION_DEFS = [
    ("🚇", "CONNECTIVITY",  "MRT & LRT Transit",  ["mrt_station"]),
    ("🛒", "RETAIL & FOOD", "Shopping & Hawkers", ["shopping_mall", "hawker_centre"]),
    ("🏥", "WELLNESS",      "Health & Sports",     ["polyclinic", "sports_hall", "parks"]),
    ("🎓", "EDUCATION",     "Pri Sch within 1km",  ["primary_schools"]),
]

WITHIN_1KM_KEYS = {"primary_schools", "parks"}


# ── Pure helpers ───────────────────────────────────────────────

def score_rating_min(amenity_key, walk_min, thresholds):
    """Rate by walk minutes. Returns (rating_str, score_int, fill_pct)."""
    t = thresholds.get(amenity_key, [5, 10, 15])
    if walk_min < t[0]:   return ("EXCEPTIONAL",   3, 100)
    elif walk_min < t[1]: return ("GOOD",           2, 75)
    elif walk_min < t[2]: return ("BELOW AVERAGE",  1, 45)
    else:                 return ("POOR",            0, 15)


def rating_css(rating_str):
    return rating_str.lower().replace(" ", "-")


def compute_proximity_score(nearest_dict, thresholds):
    scores = {}
    for key in DEFAULT_THRESHOLDS_MIN:
        info = nearest_dict.get(key)
        if info:
            scores[key] = score_rating_min(key, info["walk_min"], thresholds)
    if not scores:
        return (0.0, scores)
    avg_raw = sum(v[1] for v in scores.values()) / len(scores)
    return (round(avg_raw / 3 * 10, 1), scores)


def best_distance_flat(flat_labels, nearest_data, amenity_key):
    vals = {
        lbl: nearest_data[lbl][amenity_key]["walk_min"]
        for lbl in flat_labels
        if nearest_data.get(lbl, {}).get(amenity_key)
    }
    return min(vals, key=vals.get) if vals else None


def best_school_flat(flat_labels, within_data):
    vals = {
        lbl: len(within_data.get(lbl, {}).get("primary_schools", []) or [])
        for lbl in flat_labels
    }
    mx = max(vals.values()) if vals else 0
    return max(vals, key=vals.get) if mx > 0 else None


# ── Sub-cell builders ──────────────────────────────────────────

def amenity_cell_content(info, is_best, amenity_key, thresholds):
    rating, _, fill_pct = score_rating_min(amenity_key, info["walk_min"], thresholds)
    cls = rating_css(rating)
    return html.Div(className="am-amenity-cell", children=[
        html.Div(className="am-amenity-header-row", children=[
            html.Span(info["name"], className="am-amenity-name"),
            html.Span("★ BEST", className="am-best-badge") if is_best else None,
        ]),
        html.Div(
            f"{info['distance_m']:,}m",
            style={"fontSize": "22px", "fontWeight": "800",
                   "color": "var(--color-text-primary)", "lineHeight": "1.1",
                   "fontFamily": "var(--mono)"}
        ),
        html.Div(
            f"/ {info['walk_min']} min walk",
            style={"fontSize": "12px", "color": "var(--color-text-muted)", "marginBottom": "8px"}
        ),
        html.Div(className="am-progress-bar", children=[
            html.Div(className=f"am-progress-fill {cls}", style={"width": f"{fill_pct}%"}),
        ]),
        html.Div(
            rating,
            className=f"am-rating-label {cls}",
            title=RATING_TOOLTIP.get(amenity_key, ""),
        ),
    ])


def parks_cell_content(parks):
    if not parks:
        return html.Div([
            html.Li(className="am-school-item", children=[
                html.Span(className="am-school-dot outside"),
                html.Span("No parks within 1km",
                          style={"color": "var(--color-text-muted)", "fontStyle": "italic"}),
            ])
        ], className="am-school-list")

    MAX_SHOWN = 5
    items = [
        html.Li(className="am-school-item", children=[
            html.Span(className="am-school-dot within"),
            html.Span(s),
        ])
        for s in parks[:MAX_SHOWN]
    ]
    extra = len(parks) - MAX_SHOWN
    children = [html.Ul(items, className="am-school-list")]
    if extra > 0:
        children.append(html.Div(f"+ {extra} more", className="am-school-more"))
    return html.Div(children)


def school_cell_content(schools, is_best):
    if not schools:
        return html.Div([
            html.Li(className="am-school-item", children=[
                html.Span(className="am-school-dot outside"),
                html.Span("No schools within 1km",
                          style={"color": "var(--color-text-muted)", "fontStyle": "italic"}),
            ])
        ], className="am-school-list")

    MAX_SHOWN = 5
    items = [
        html.Li(className="am-school-item", children=[
            html.Span(className="am-school-dot within"),
            html.Span(s),
        ])
        for s in schools[:MAX_SHOWN]
    ]
    extra = len(schools) - MAX_SHOWN
    children = [html.Ul(items, className="am-school-list")]
    if extra > 0:
        children.append(html.Div(f"+ {extra} more", className="am-school-more"))
    return html.Div(children)


# ── Main table builder ─────────────────────────────────────────

def build_comparison_table(flat_labels, flat_data, nearest_data, within_data, thresholds):
    """
    Single HTML table — flat pill headers in thead, all metric rows in tbody.
    table-layout: fixed guarantees column alignment between header and rows.
    """

    # ── thead: flat pill headers (no image, no demand badge) ──
    card_cells = [html.Th(style={"width": "160px", "borderBottom": "2px solid var(--color-border)"})]
    for label in flat_labels:
        fd = flat_data.get(label)
        if fd is None:
            header_content = html.Div(className="am-flat-pill am-flat-pill-notfound", children=[
                html.Div("📭", style={"fontSize": "20px", "marginBottom": "4px"}),
                html.Div(label, style={"fontWeight": "700", "fontSize": "13px"}),
                html.Div("Block not found",
                         style={"fontSize": "11px", "color": "var(--color-text-muted)",
                                "fontStyle": "italic"}),
            ])
        else:
            header_content = html.Div(className="am-flat-pill", children=[
                html.Div(label,
                         style={"fontSize": "11px", "fontWeight": "700",
                                "color": "var(--color-text-muted)",
                                "textTransform": "uppercase",
                                "letterSpacing": "0.08em", "marginBottom": "4px"}),
                html.Div(fd.get("address", ""),
                         style={"fontSize": "15px", "fontWeight": "700",
                                "color": "var(--color-text-primary)", "lineHeight": "1.25"}),
                html.Div(fd.get("town", ""),
                         style={"fontSize": "11px", "color": "var(--color-text-secondary)",
                                "marginTop": "3px"}),
            ])

        card_cells.append(html.Th(
            header_content,
            style={"padding": "16px 12px", "verticalAlign": "top",
                   "borderBottom": "2px solid var(--color-border)",
                   "borderLeft": "1px solid var(--color-border)"},
        ))

    thead = html.Thead(html.Tr(card_cells))

    # ── tbody: section headers + metric rows ───────────────────
    tbody_rows = []

    for icon, cat_title, metric_title, keys in SECTION_DEFS:
        tbody_rows.append(html.Tr(
            className="am-section-header-row",
            children=[html.Td(
                colSpan=len(flat_labels) + 1,
                className="am-section-header-cell",
                children=[html.Div(className="am-section-label", children=[
                    html.Span(icon, style={"fontSize": "16px"}),
                    html.Span(cat_title,
                              style={"fontSize": "11px", "color": "var(--color-accent)",
                                     "letterSpacing": "0.1em", "fontWeight": "700",
                                     "textTransform": "uppercase"}),
                ])],
            )],
        ))

        nearest_keys = [k for k in keys if k not in WITHIN_1KM_KEYS]
        within_keys = [k for k in keys if k in WITHIN_1KM_KEYS]

        if nearest_keys:
            for key in nearest_keys:
                best_lbl = best_distance_flat(flat_labels, nearest_data, key)
                cells = [html.Td(
                    AMENITY_DISPLAY_LABELS.get(key, key),
                    className="am-metric-label-col",
                    style={"width": "160px"},
                )]
                for lbl in flat_labels:
                    info = nearest_data.get(lbl, {}).get(key)
                    td_content = (
                        amenity_cell_content(info, lbl == best_lbl, key, thresholds)
                        if info else html.Div("—", className="am-not-available")
                    )
                    cells.append(html.Td(
                        td_content,
                        style={"padding": "16px 12px", "verticalAlign": "top",
                               "borderLeft": "1px solid var(--color-border)"},
                    ))
                tbody_rows.append(html.Tr(cells, className="am-metric-data-row"))

        for key in within_keys:
            if key == "primary_schools":
                best_lbl = best_school_flat(flat_labels, within_data)
                cells = [html.Td("Pri Sch within 1km", className="am-metric-label-col", style={"width": "160px"})]
                for lbl in flat_labels:
                    schools = within_data.get(lbl, {}).get("primary_schools", []) or []
                    cells.append(html.Td(
                        school_cell_content(schools, lbl == best_lbl),
                        style={"padding": "16px 12px", "verticalAlign": "top",
                               "borderLeft": "1px solid var(--color-border)"},
                    ))
                tbody_rows.append(html.Tr(cells, className="am-metric-data-row"))
            elif key == "parks":
                cells = [html.Td(
                    "Parks",
                    className="am-metric-label-col",
                    style={"width": "160px"},
                )]
                for lbl in flat_labels:
                    parks = within_data.get(lbl, {}).get("parks", []) or []
                    cells.append(html.Td(
                        parks_cell_content(parks),
                        style={"padding": "16px 12px", "verticalAlign": "top",
                               "borderLeft": "1px solid var(--color-border)"},
                    ))
                tbody_rows.append(html.Tr(cells, className="am-metric-data-row"))

    tbody = html.Tbody(tbody_rows)

    return html.Div(className="am-table-wrap", children=[
        html.Table(className="am-comparison-table", children=[thead, tbody])
    ])


# ── Verdict section ────────────────────────────────────────────

def build_verdict_section(flat_labels, nearest_data, thresholds):
    scores = {}
    for lbl in flat_labels:
        nd = nearest_data.get(lbl, {})
        if nd:
            score, _ = compute_proximity_score(nd, thresholds)
            scores[lbl] = score

    best_flat = max(scores, key=scores.get) if scores else None

    # Per-flat score boxes
    score_boxes = []
    for lbl in flat_labels:
        s = scores.get(lbl)
        is_best = lbl == best_flat
        score_boxes.append(html.Div(className=f"am-stat-box{' am-stat-box-best' if is_best else ''}", children=[
            html.Div(className="am-stat-box-label-row", children=[
                html.Span(lbl, className="am-stat-box-label"),
                html.Span("★ BEST", className="am-best-badge",
                          style={"marginLeft": "6px"}) if is_best else None,
            ]),
            html.Div(
                f"{s}/10" if s is not None else "—",
                className="am-stat-box-value",
                style={"color": "var(--color-accent)"} if is_best else {},
            ),
        ]))

    # Tooltip popup with formula breakdown
    score_tooltip_content = html.Div(className="am-score-tooltip-popup", children=[
        html.Div("How the score is calculated",
                 style={"fontWeight": "700", "fontSize": "11px", "marginBottom": "8px",
                        "textTransform": "uppercase", "letterSpacing": "0.08em"}),
        html.Div("Score = sum of amenity ratings ÷ (5 × 3) × 10",
                 style={"fontSize": "12px", "marginBottom": "8px", "fontFamily": "var(--mono)"}),
        html.Table([
            html.Tr([
                html.Td("Exceptional", style={"paddingRight": "8px"}),
                html.Td("3 pts", style={"fontWeight": "600", "color": "#16A34A"}),
            ]),
            html.Tr([
                html.Td("Good", style={"paddingRight": "8px"}),
                html.Td("2 pts", style={"fontWeight": "600", "color": "#2563EB"}),
            ]),
            html.Tr([
                html.Td("Below Average", style={"paddingRight": "8px"}),
                html.Td("1 pt", style={"fontWeight": "600", "color": "#D97706"}),
            ]),
            html.Tr([
                html.Td("Poor", style={"paddingRight": "8px"}),
                html.Td("0 pts", style={"fontWeight": "600", "color": "#DC2626"}),
            ]),
        ], style={"fontSize": "11px", "borderCollapse": "collapse", "width": "100%",
                  "marginBottom": "8px"}),
        html.Div("All 5 amenities are weighted equally.",
                 style={"fontSize": "11px", "color": "var(--color-text-muted)"}),
    ])

    # Proximity rating legend rows
    _col_w   = "20%"  # equal width for the 4 rating columns
    _amenity_w = "20%"
    _th_style = {"width": _col_w, "padding": "3px 6px", "fontSize": "9px", "fontWeight": "700",
                 "textTransform": "uppercase", "letterSpacing": "0.06em", "whiteSpace": "nowrap",
                 "textAlign": "center"}
    legend_header = html.Tr([
        html.Th("Amenity",     style={**_th_style, "width": _amenity_w, "color": "var(--color-text-secondary)", "textAlign": "left"}),
        html.Th("Exceptional", style={**_th_style, "color": "#16A34A"}),
        html.Th("Good",        style={**_th_style, "color": "#2563EB"}),
        html.Th("Below Avg",   style={**_th_style, "color": "#F59E0B"}),
        html.Th("Poor",        style={**_th_style, "color": "#DC2626"}),
    ])
    _td_val = {"fontSize": "10px", "color": "var(--color-text-muted)",
               "padding": "2px 6px", "whiteSpace": "nowrap", "textAlign": "center"}
    legend_rows = []
    for key, dlabel in AMENITY_DISPLAY_LABELS.items():
        t = thresholds.get(key, [5, 10, 15])
        legend_rows.append(html.Tr([
            html.Td(dlabel,
                    style={"width": _amenity_w, "padding": "2px 6px 2px 0", "fontSize": "10px",
                           "color": "var(--color-text-secondary)", "fontWeight": "600",
                           "whiteSpace": "nowrap"}),
            html.Td(f"<{t[0]} min",        style=_td_val),
            html.Td(f"{t[0]}–{t[1]} min",  style=_td_val),
            html.Td(f"{t[1]}–{t[2]} min",  style=_td_val),
            html.Td(f">{t[2]} min",         style=_td_val),
        ]))

    return html.Div(className="am-verdict-wrap", children=[

        # ── Summary card ───────────────────────────────────────
        html.Div(className="am-verdict-card", children=[
            html.H2("Location Summary", className="am-verdict-title"),

            # Best score badge
            html.Div(className="am-best-score-banner", children=[
                html.Span("★", style={"marginRight": "6px", "color": "var(--color-accent)"}),
                html.Span(
                    f"{best_flat} has the highest overall proximity score ({scores[best_flat]}/10)"
                    if best_flat else "No data available",
                    style={"fontWeight": "700", "fontSize": "13px",
                           "color": "var(--color-text-primary)"},
                ),
            ]) if best_flat else None,

            # Per-flat scores with tooltip trigger
            html.Div(className="am-stat-box-label-row", style={"marginBottom": "8px"}, children=[
                html.Span("PROXIMITY SCORE", className="am-stat-box-label"),
                html.Div(className="am-score-tooltip-wrap", children=[
                    html.Span("?", className="am-score-tooltip-btn"),
                    score_tooltip_content,
                ]),
            ]),
            html.Div(className="am-stat-boxes", children=score_boxes),
        ]),

        # ── Rating thresholds legend ─────────────────────────────
        html.Div(className="am-rating-legend-card", children=[
            html.Div("How proximity ratings are calculated",
                     style={"fontSize": "11px", "fontWeight": "700",
                            "textTransform": "uppercase", "letterSpacing": "0.08em",
                            "color": "var(--color-text-muted)", "marginBottom": "12px"}),
            html.Div("Ratings are based on walking time (minutes) to the nearest amenity.",
                     style={"fontSize": "11px", "color": "var(--color-text-secondary)",
                            "marginBottom": "8px"}),
            html.Table(
                [html.Thead(legend_header), html.Tbody(legend_rows)],
                style={"borderCollapse": "collapse", "width": "100%",
                       "tableLayout": "fixed"},
            ),
        ]),
    ])


def build_results(flat_labels, flat_data, nearest_data, within_data, thresholds):
    table = build_comparison_table(flat_labels, flat_data, nearest_data, within_data, thresholds)
    verdict = build_verdict_section(flat_labels, nearest_data, thresholds)
    return html.Div([table, verdict])


def empty_state():
    return html.Div(
        style={"textAlign": "center", "padding": "80px 32px", "color": "var(--color-text-muted)"},
        children=[
            html.Div("📍", style={"fontSize": "40px", "marginBottom": "12px"}),
            html.P("Enter a postal code above and click Add Block to begin comparing.",
                   style={"fontSize": "15px"}),
        ],
    )


# ── Page header + input bar ────────────────────────────────────

def build_page_header():
    return html.Div([
        html.H1("Amenities Comparison Tool — Block Level", className="am-page-title"),
        html.P(
            "Analyze and compare amenity proximity across up to 3 HDB blocks. "
            "Evaluate walkability, transport access, and essential services side by side.",
            className="am-page-subtitle",
        ),
    ])


def build_input_bar():
    return html.Div(className="am-input-bar", children=[
        html.Div("Compare up to 3 blocks", className="am-input-bar-label"),
        html.Div(className="am-input-controls", children=[
            html.Div(className="am-postal-wrap", children=[
                dcc.Dropdown(
                    id="postal-input",
                    options=_POSTAL_OPTIONS,
                    placeholder="Search by postal code or address...",
                    className="am-postal-dropdown",
                    searchable=True,
                    clearable=True,
                    style={"width": "380px"},
                ),
            ]),
            html.Div(style={"display": "flex", "gap": "8px", "alignItems": "center"}, children=[
                html.Button("Add Block", id="add-btn", className="btn btn-primary",
                            style={"padding": "9px 24px"}),
                html.Button("Load Demo", id="demo-btn", className="btn btn-secondary",
                            style={"padding": "8px 20px", "fontSize": "13px"}),
                html.Button("Clear All", id="clear-btn", className="btn btn-secondary",
                            style={"padding": "8px 20px", "fontSize": "13px"}),
            ]),
        ]),
    ])


def build_flat_tag(label, postal, is_active=False):
    cls = "flat-tag active" if is_active else "flat-tag"
    return html.Div(className=cls, children=[
        html.Span(f"{label}: {postal}"),
        html.Button("×", id={"type": "remove-flat", "index": postal},
                    className="flat-tag-remove", n_clicks=0),
    ])


# ── Layout ────────────────────────────────────────────────────

layout = html.Div(className="page-wrapper", children=[
    html.Div(className="amenities-page", children=[
        build_page_header(),
        dcc.Store(id="flats-store", data=[]),
        build_input_bar(),
        html.Div(id="flat-tags", className="am-tags-row"),
        html.Div(id="comparison-output", children=empty_state()),
    ])
])


# ── Callbacks ─────────────────────────────────────────────────

@callback(
    Output("flats-store", "data"),
    Output("postal-input", "value"),
    Input("add-btn", "n_clicks"),
    Input("demo-btn", "n_clicks"),
    Input("clear-btn", "n_clicks"),
    Input({"type": "remove-flat", "index": ALL}, "n_clicks"),
    State("postal-input", "value"),
    State("flats-store", "data"),
    prevent_initial_call=True,
)
def update_store(n_add, n_demo, n_clear, n_removes, postal, store):
    trig = ctx.triggered_id
    if trig == "clear-btn":
        return [], None
    if trig == "demo-btn":
        return DEMO_POSTALS[:], None
    if isinstance(trig, dict) and trig.get("type") == "remove-flat":
        return [p for p in store if p != trig["index"]], no_update
    if trig == "add-btn":
        if not postal:
            return no_update, no_update
        p = str(postal).strip()
        if p in store or len(store) >= 3:
            return no_update, None
        return store + [p], None
    return no_update, no_update


@callback(
    Output("flat-tags", "children"),
    Output("comparison-output", "children"),
    Input("flats-store", "data"),
)
def render_comparison(store):
    if not store:
        return [], empty_state()

    tags = [
        build_flat_tag(FLAT_LABELS[i], p, is_active=(i == len(store) - 1))
        for i, p in enumerate(store)
    ]

    flat_data, nearest_data, within_data = {}, {}, {}
    thresholds = DEFAULT_THRESHOLDS_MIN

    for i, p in enumerate(store):
        label = FLAT_LABELS[i]

        # Check demo data first (exact postal match in demo)
        demo_key = next(
            (fl for fl, fd in DEMO["flats"].items() if fd["postal_code"] == p), None
        )
        if demo_key:
            flat_data[label]    = DEMO["flats"][demo_key]
            nearest_data[label] = DEMO["nearest"].get(demo_key, {})
            within_data[label]  = DEMO["within_1km"].get(demo_key, {})
        else:
            # Real backend lookup
            meta, nearest, within = lookup_flat_by_postal(p)
            flat_data[label]    = meta
            nearest_data[label] = nearest
            within_data[label]  = within

    active_labels = [FLAT_LABELS[i] for i in range(len(store))]
    results = build_results(active_labels, flat_data, nearest_data, within_data, thresholds)
    return tags, results
