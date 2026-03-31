import json, os
import dash
from dash import html, dcc, callback, Output, Input, State, no_update, ALL, ctx

dash.register_page(__name__, path="/amenities-comparison", name="Amenities Comparison")

_BASE = os.path.dirname(os.path.dirname(__file__))
with open(os.path.join(_BASE, "mock_data", "amenities_demo.json"), encoding="utf-8") as f:
    DEMO = json.load(f)

AMENITY_LABELS = {
    "mrt_station":   "MRT / LRT Station",
    "shopping_mall": "Shopping Mall",
    "hawker_centre": "Hawker Centre",
    "polyclinic":    "Polyclinic",
    "sports_hall":   "Sports Hall",
}
FLAT_LABELS = ["Flat A", "Flat B", "Flat C"]
DEMO_POSTALS = ["310058", "560234", "820412"]

# ── Helpers ───────────────────────────────────────────────────

def best_col(data_dict, key, sub="distance_m"):
    vals = {k: v[key][sub] for k, v in data_dict.items() if key in v}
    if not vals:
        return []
    mn = min(vals.values())
    return [k for k, v in vals.items() if v == mn]


def amenity_cell(info, is_best):
    badge = html.Span("✓ Best", className="best-badge") if is_best else None
    return html.Td(
        className="best-cell" if is_best else "",
        children=[
            html.Div([
                html.Span(info["name"], style={"fontWeight": "600", "fontSize": "13px"}),
                badge,
            ], style={"display": "flex", "alignItems": "center", "flexWrap": "wrap", "gap": "4px"}),
            html.Div(
                f"{info['distance_m']:,} m  ·  {info['walk_min']} min walk",
                className="distance-sub"
            ),
        ]
    )


def list_cell(items):
    if not items:
        return html.Td("—", style={"color": "var(--color-text-muted)"})
    return html.Td(html.Ul(
        [html.Li(s, style={"fontSize": "12px", "marginBottom": "2px"}) for s in items],
        style={"paddingLeft": "16px", "margin": "0"}
    ))


def build_comparison_table(flat_data, nearest_data, within_data):
    flat_labels = list(flat_data.keys())
    cols = len(flat_labels)

    header_cells = [html.Th("METRIC", className="metric-col")]
    for label in flat_labels:
        fd = flat_data[label]
        header_cells.append(html.Th(className="flat-col", children=[
            label,
            html.Span(fd["address"], className="flat-col-sub"),
        ]))

    rows = []

    # ── Nearest amenities section ──
    rows.append(html.Tr(className="section-divider-row", children=[
        html.Td("Nearest Amenity (Distance · Walk Time)", colSpan=cols + 1)
    ]))
    for key, label in AMENITY_LABELS.items():
        best_flats = best_col(nearest_data, key)
        cells = [html.Td(label, className="metric-cell")]
        for fl in flat_labels:
            info = nearest_data.get(fl, {}).get(key)
            if info:
                cells.append(amenity_cell(info, fl in best_flats))
            else:
                cells.append(html.Td("—"))
        rows.append(html.Tr(cells))

    # ── Within 1 km section ──
    rows.append(html.Tr(className="section-divider-row", children=[
        html.Td("Within 1 km", colSpan=cols + 1)
    ]))

    school_cells = [html.Td("Primary Schools", className="metric-cell")]
    for fl in flat_labels:
        schools = within_data.get(fl, {}).get("primary_schools", [])
        school_cells.append(list_cell(schools))
    rows.append(html.Tr(school_cells))

    park_cells = [html.Td("Parks", className="metric-cell")]
    for fl in flat_labels:
        parks = within_data.get(fl, {}).get("parks", [])
        park_cells.append(list_cell(parks))
    rows.append(html.Tr(park_cells))

    return html.Div(className="comparison-table-wrap", children=[
        html.Table(
            className="comparison-table",
            style={"tableLayout": "fixed"},
            children=[
                html.Thead(html.Tr(header_cells)),
                html.Tbody(rows),
            ]
        )
    ])


def empty_state():
    return html.Div(
        style={"textAlign": "center", "padding": "80px 32px", "color": "var(--color-text-muted)"},
        children=[
            html.Div("📍", style={"fontSize": "40px", "marginBottom": "12px"}),
            html.P("Enter a postal code above and click Add Flat to begin comparing.",
                   style={"fontSize": "15px"}),
        ]
    )


def flat_tag(label, postal):
    return html.Div(className="flat-tag", children=[
        html.Span(f"{label}: {postal}"),
        html.Button("×", id={"type": "remove-flat", "index": postal},
                    className="flat-tag-remove", n_clicks=0),
    ])


# ── Layout ────────────────────────────────────────────────────
layout = html.Div(className="page-wrapper", children=[
    html.Div(className="amenities-page", children=[

        html.H1("Amenities Comparison",
                style={"fontSize": "28px", "fontWeight": "700",
                       "color": "var(--color-text-primary)", "marginBottom": "6px"}),
        html.P("Compare the amenity profiles of up to 3 HDB flats side by side.",
               style={"color": "var(--color-text-secondary)", "marginBottom": "28px"}),

        dcc.Store(id="flats-store", data=[]),

        # Search bar
        html.Div(className="amenities-search-bar", children=[
            html.Div(className="postal-input-group", children=[
                html.Label("ADD A FLAT — POSTAL CODE", className="input-label"),
                dcc.Input(id="postal-input", type="text", maxLength=6,
                          placeholder="e.g. 310058", className="form-input",
                          debounce=False, n_submit=0),
            ]),
            html.Div(style={"display": "flex", "flexDirection": "column",
                            "justifyContent": "flex-end", "gap": "6px"}, children=[
                html.Button("Add Flat", id="add-btn",
                            className="btn btn-primary",
                            style={"padding": "9px 28px"}),
                html.Button("Load Demo", id="demo-btn",
                            className="btn btn-secondary",
                            style={"padding": "8px 28px", "fontSize": "13px"}),
            ]),
            html.Div(style={"display": "flex", "flexDirection": "column",
                            "justifyContent": "flex-end"}, children=[
                html.Button("Clear All", id="clear-btn",
                            className="btn btn-secondary",
                            style={"padding": "8px 20px", "fontSize": "13px"}),
            ]),
        ]),

        # Flat tags row
        html.Div(id="flat-tags",
                 style={"display": "flex", "gap": "8px", "marginTop": "12px",
                        "marginBottom": "24px", "flexWrap": "wrap"}),

        # Comparison output
        html.Div(id="comparison-output", children=empty_state()),

        # LLM summary
        html.Div(id="llm-summary-wrap", style={"marginTop": "24px"}),
    ])
])


# ── Callbacks ─────────────────────────────────────────────────

@callback(
    Output("flats-store", "data"),
    Output("postal-input", "value"),
    Input("add-btn", "n_clicks"),
    Input("postal-input", "n_submit"),
    Input("demo-btn", "n_clicks"),
    Input("clear-btn", "n_clicks"),
    Input({"type": "remove-flat", "index": ALL}, "n_clicks"),
    State("postal-input", "value"),
    State("flats-store", "data"),
    prevent_initial_call=True,
)
def update_store(n_add, n_submit, n_demo, n_clear, n_removes, postal, store):
    trig = ctx.triggered_id

    if trig == "clear-btn":
        return [], ""

    if trig == "demo-btn":
        return DEMO_POSTALS[:], ""

    if isinstance(trig, dict) and trig.get("type") == "remove-flat":
        return [p for p in store if p != trig["index"]], no_update

    if trig in ("add-btn", "postal-input"):
        if not postal or len(postal.strip()) != 6 or not postal.strip().isdigit():
            return no_update, no_update
        p = postal.strip()
        if p in store or len(store) >= 3:
            return no_update, ""
        return store + [p], ""

    return no_update, no_update


@callback(
    Output("flat-tags", "children"),
    Output("comparison-output", "children"),
    Output("llm-summary-wrap", "children"),
    Input("flats-store", "data"),
)
def render_comparison(store):
    if not store:
        return [], empty_state(), ""

    tags = [flat_tag(FLAT_LABELS[i], p) for i, p in enumerate(store)]

    flat_data, nearest_data, within_data = {}, {}, {}
    for i, p in enumerate(store):
        label = FLAT_LABELS[i]
        matched = next((fl for fl, fd in DEMO["flats"].items() if fd["postal_code"] == p), None)
        if matched:
            flat_data[label]    = DEMO["flats"][matched]
            nearest_data[label] = DEMO["nearest"][matched]
            within_data[label]  = DEMO["within_1km"][matched]
        else:
            flat_data[label]    = {"postal_code": p, "address": f"Postal {p}", "town": "Unknown", "flat_type": "—"}
            nearest_data[label] = {}
            within_data[label]  = {}

    table = build_comparison_table(flat_data, nearest_data, within_data)

    demo_postals = {fd["postal_code"] for fd in DEMO["flats"].values()}
    llm = html.Div(className="llm-summary-card", children=[
        html.P("AI SUMMARY", className="llm-label"),
        html.P(DEMO["llm_summary"], className="llm-text"),
        html.P("Summary is based on retrieved amenity data only.", className="llm-disclaimer"),
    ]) if any(p in demo_postals for p in store) else ""

    return tags, table, llm
