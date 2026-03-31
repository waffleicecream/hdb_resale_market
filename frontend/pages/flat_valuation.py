import json, os
import dash
from dash import html, dcc, callback, Output, Input, State, no_update
import plotly.graph_objects as go

dash.register_page(__name__, path="/flat-valuation", name="Flat Valuation")

_BASE = os.path.dirname(os.path.dirname(__file__))
with open(os.path.join(_BASE, "mock_data", "valuation_demo.json"), encoding="utf-8") as f:
    DEMO = json.load(f)

FLAT_TYPES    = ["1-Room", "2-Room", "3-Room", "4-Room", "5-Room", "Executive"]
STOREY_RANGES = ["1 to 5", "6 to 10", "11 to 15", "16 to 20", "21 to 25", "26 to 30"]


# ── Map figure ────────────────────────────────────────────────
def make_pin_map(lat=1.3321, lon=103.8479, address=""):
    fig = go.Figure(go.Scattermapbox(
        lat=[lat], lon=[lon],
        mode="markers",
        marker=go.scattermapbox.Marker(size=16, color="#1C4ED8"),
        text=[address],
        hoverinfo="text",
    ))
    fig.update_layout(
        mapbox=dict(style="carto-positron", zoom=14,
                    center={"lat": lat, "lon": lon}),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


# ── Price range bar ───────────────────────────────────────────
def price_range_bar(low, high, listed=None):
    span = high - low
    listed_pct = ((listed - low) / span * 100) if listed else None

    if listed:
        if listed < low:
            verdict = html.Span([
                html.Span("⬇ Underpriced", className="badge badge-info"),
                html.Span(f" Listed at ${listed:,.0f} — below the projected range",
                          style={"fontSize": "12px", "color": "var(--color-text-muted)", "marginLeft": "6px"}),
            ])
        elif listed > high:
            verdict = html.Span([
                html.Span("⬆ Overpriced", className="badge badge-danger"),
                html.Span(f" Listed at ${listed:,.0f} — above the projected range",
                          style={"fontSize": "12px", "color": "var(--color-text-muted)", "marginLeft": "6px"}),
            ])
        else:
            verdict = html.Span([
                html.Span("✓ Fair Price", className="badge badge-success"),
                html.Span(f" Listed at ${listed:,.0f} — within the projected range",
                          style={"fontSize": "12px", "color": "var(--color-text-muted)", "marginLeft": "6px"}),
            ])
    else:
        verdict = None

    marker = None
    if listed_pct is not None:
        clamped = max(0, min(100, listed_pct))
        marker = html.Div(className="price-listed-marker",
                          style={"left": f"{clamped}%"})

    return html.Div([
        html.Div(className="price-range-labels", children=[
            html.Span("15th Percentile", className="price-range-label"),
            html.Span("85th Percentile", className="price-range-label"),
        ]),
        html.Div(className="price-range-values", children=[
            html.Span(f"${low:,.0f}", className="price-range-val"),
            html.Span(f"${high:,.0f}", className="price-range-val"),
        ]),
        html.Div(className="price-range-track", children=[
            html.Div(className="price-range-fill", style={"width": "100%"}),
            marker,
        ]),
        html.Div(className="projection-label-row", children=[
            html.Span("ℹ", style={"color": "var(--color-text-muted)"}),
            html.Span("Reasonable Projection", style={"fontWeight": "600", "color": "var(--color-text-secondary)"}),
            html.Span("· Actual prices may vary based on condition, renovation, and negotiation.",
                      style={"color": "var(--color-text-muted)", "fontSize": "11px"}),
        ]),
        html.Div(verdict, style={"marginTop": "12px"}) if verdict else None,
    ])


# ── Valuation dashboard ───────────────────────────────────────
def valuation_dashboard(data, listed_price=None):
    proj = data["projection"]
    nearby = data["nearby_transactions"]
    similar = data["similar_flats"]

    nearby_rows = [
        html.Tr([
            html.Td(t["flat_type"]),
            html.Td(t["floor_range"]),
            html.Td(t["month"]),
            html.Td(f"${t['price']:,.0f}", className="td-price"),
        ]) for t in nearby
    ]

    similar_rows = [
        html.Tr([
            html.Td(t["flat_type"]),
            html.Td(t["month"]),
            html.Td(f"${t['price']:,.0f}", className="td-price"),
            html.Td(t["town"]),
            html.Td(t["address"], style={"fontSize": "12px", "color": "var(--color-text-muted)"}),
        ]) for t in similar
    ]

    return html.Div(className="valuation-dashboard", children=[

        # Top-left: Price projection
        html.Div(className="projection-card", children=[
            html.H3("Price Projection", className="projection-title"),
            price_range_bar(proj["lower_bound"], proj["upper_bound"], listed_price),
            html.Div(className="flat-detail-grid", children=[
                html.Div([html.P("ADDRESS",         className="flat-detail-label"),
                          html.P(data["address"],   className="flat-detail-val")]),
                html.Div([html.P("POSTAL CODE",     className="flat-detail-label"),
                          html.P(data["postal_code"], className="flat-detail-val")]),
                html.Div([html.P("FLAT TYPE",       className="flat-detail-label"),
                          html.P(data["flat_type"], className="flat-detail-val")]),
                html.Div([html.P("REMAINING LEASE", className="flat-detail-label"),
                          html.P(data["remaining_lease"], className="flat-detail-val")]),
            ]),
        ]),

        # Right panel: comparable transactions (spans 2 rows)
        html.Div(className="comps-card", children=[
            html.P("SAME BLOCK / NEARBY TRANSACTIONS", className="comps-section-label"),
            html.Table(className="data-table", children=[
                html.Thead(html.Tr([
                    html.Th("Flat Type"), html.Th("Storey"), html.Th("Month"), html.Th("Price"),
                ])),
                html.Tbody(nearby_rows),
            ]),
            html.Div(className="divider comps-divider"),
            html.P("SIMILAR FLATS IN OTHER TOWNS", className="comps-section-label"),
            html.Table(className="data-table", children=[
                html.Thead(html.Tr([
                    html.Th("Flat Type"), html.Th("Month"),
                    html.Th("Price"), html.Th("Town"), html.Th("Address"),
                ])),
                html.Tbody(similar_rows),
            ]),
        ]),

        # Bottom-left: location map
        html.Div(className="map-card", children=[
            dcc.Graph(
                figure=make_pin_map(data["lat"], data["lon"], data["address"]),
                config={"displayModeBar": False, "scrollZoom": False},
                style={"height": "280px"},
            ),
        ]),
    ])


# ── Pre-search state ──────────────────────────────────────────
def pre_search_layout(prefill=None):
    pf = prefill or {}
    return html.Div(className="valuation-pre", children=[
        html.Div(className="valuation-pre-inner", children=[
            html.H1("How much is this flat worth?", className="valuation-pre-title"),
            html.P("Enter a postal code and flat type to get a data-driven price projection.",
                   className="valuation-pre-sub"),

            html.Div(className="valuation-form-card", children=[
                html.Div(className="valuation-form-grid", children=[
                    html.Div(className="form-group", children=[
                        html.Label("Postal Code *", className="form-label"),
                        dcc.Input(id="val-postal", type="text", maxLength=6,
                                  placeholder="e.g. 310058", className="form-input",
                                  value=pf.get("postal_code", "")),
                    ]),
                    html.Div(className="form-group", children=[
                        html.Label("Flat Type *", className="form-label"),
                        dcc.Dropdown(id="val-flat-type",
                                     options=[{"label": ft, "value": ft} for ft in FLAT_TYPES],
                                     placeholder="Select flat type", clearable=False,
                                     value=pf.get("flat_type"),
                                     style={"fontSize": "14px"}),
                    ]),
                    html.Div(className="form-group", children=[
                        html.Label("Storey Range (optional)", className="form-label"),
                        dcc.Dropdown(id="val-storey",
                                     options=[{"label": s, "value": s} for s in STOREY_RANGES],
                                     placeholder="Any storey", clearable=True,
                                     value=pf.get("storey"),
                                     style={"fontSize": "14px"}),
                    ]),
                    html.Div(className="form-group", children=[
                        html.Label("Listed Price (optional)", className="form-label"),
                        dcc.Input(id="val-listed", type="number", min=0,
                                  placeholder="e.g. 560000", className="form-input",
                                  debounce=True),
                    ]),
                ]),
                html.P(id="val-error",
                       style={"color": "var(--color-danger)", "fontSize": "13px",
                              "marginBottom": "12px", "minHeight": "18px"}),
                html.Button("Get Valuation →", id="val-submit",
                            className="btn btn-primary",
                            style={"width": "100%", "justifyContent": "center", "padding": "12px"}),
                html.Button("Try Demo (Blk 58 Toa Payoh)", id="val-demo",
                            className="btn btn-secondary",
                            style={"width": "100%", "justifyContent": "center",
                                   "padding": "11px", "marginTop": "8px", "fontSize": "13px"}),
            ]),

            html.Div(className="feature-cards-row", children=[
                html.Div(className="feature-card", children=[
                    html.Div("📊", className="feature-card-icon"),
                    html.P("Price Projection", className="feature-card-title"),
                    html.P("15th–85th percentile range based on historical transactions and flat attributes.",
                           className="feature-card-desc"),
                ]),
                html.Div(className="feature-card", children=[
                    html.Div("🏢", className="feature-card-icon"),
                    html.P("Comparable Transactions", className="feature-card-title"),
                    html.P("Recent transactions at the same block and similar flats across other towns.",
                           className="feature-card-desc"),
                ]),
                html.Div(className="feature-card", children=[
                    html.Div("💰", className="feature-card-icon"),
                    html.P("Listed Price Indicator", className="feature-card-title"),
                    html.P("Enter an asking price to see if it is overpriced, fair, or underpriced.",
                           className="feature-card-desc"),
                ]),
            ]),
        ])
    ])


# ── Layout (entry point) ──────────────────────────────────────
layout = html.Div(className="page-wrapper", id="val-page-root", children=[
    pre_search_layout()
])


# ── Callbacks ─────────────────────────────────────────────────

@callback(
    Output("val-page-root", "children"),
    Output("val-error",      "children", allow_duplicate=True),
    Input("val-submit",  "n_clicks"),
    Input("val-demo",    "n_clicks"),
    State("val-postal",    "value"),
    State("val-flat-type", "value"),
    State("val-storey",    "value"),
    State("val-listed",    "value"),
    prevent_initial_call=True,
)
def run_valuation(n_submit, n_demo, postal, flat_type, storey, listed):
    from dash import ctx
    trig = ctx.triggered_id

    if trig == "val-demo":
        return valuation_dashboard(DEMO), ""

    # Validate
    if not postal or len(str(postal).strip()) != 6 or not str(postal).strip().isdigit():
        return no_update, "Please enter a valid 6-digit postal code."
    if not flat_type:
        return no_update, "Please select a flat type."

    # For any valid input → return mock dashboard
    # (In production this would call the model API)
    return valuation_dashboard(DEMO, listed_price=int(listed) if listed else None), ""


@callback(
    Output("val-page-root", "children", allow_duplicate=True),
    Input("url", "pathname"),
    State("valuation-prefill", "data"),
    prevent_initial_call=True,
)
def prefill_from_store(pathname, prefill_data):
    """When navigating here from the landing page search, pre-fill the form."""
    if pathname == "/flat-valuation" and prefill_data:
        return pre_search_layout(prefill_data)
    return no_update
