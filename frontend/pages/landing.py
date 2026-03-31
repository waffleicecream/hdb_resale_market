import json, os
import dash
from dash import html, dcc, callback, Output, Input, State, no_update

dash.register_page(__name__, path="/", name="Home")

# ── Load mock market stats ────────────────────────────────────
_BASE = os.path.dirname(os.path.dirname(__file__))
with open(os.path.join(_BASE, "mock_data", "market_stats.json"), encoding="utf-8") as f:
    MARKET_STATS = json.load(f)

FLAT_TYPES    = ["1-Room", "2-Room", "3-Room", "4-Room", "5-Room", "Executive"]
STOREY_RANGES = ["1 to 5", "6 to 10", "11 to 15", "16 to 20", "21 to 25", "26 to 30"]

# ── Helpers ───────────────────────────────────────────────────
def fmt_price(v):
    return f"${v:,.0f}"

def fmt_pct(v, show_plus=True):
    sign = "+" if v > 0 and show_plus else ""
    return f"{sign}{v:.1f}%"

def change_class(v):
    return "stat-change positive" if v >= 0 else "stat-change negative"

def arrow(v):
    return "↑" if v >= 0 else "↓"

def stat_card(label, value, change_pct, sub=None):
    return html.Div(className="stat-card", children=[
        html.P(label, className="stat-label"),
        html.P(value, className="stat-value"),
        html.P([
            html.Span(f"{arrow(change_pct)} {fmt_pct(change_pct)} ", className=change_class(change_pct)),
            html.Span("vs prev period", style={"color": "var(--color-text-muted)", "fontSize": "11px"}),
        ]),
        html.P(sub, className="stat-sub") if sub else None,
    ])

def build_stats_row(period="3m"):
    d = MARKET_STATS[period]
    hot = d["hottest"]
    cool = d["coolest"]
    return html.Div(className="stats-cards-row", id="stats-cards-row", children=[
        stat_card("Total Transactions",
                  f"{d['total_transactions']:,}",
                  d["total_transactions_pct"]),
        stat_card("Median Resale Price",
                  fmt_price(d["median_price"]),
                  d["median_price_pct"]),
        stat_card("Price Growth",
                  f"{d['mom_growth_pct']:.1f}%",
                  d["mom_growth_pct"]),
        html.Div(className="stat-card", children=[
            html.P("HOTTEST REGION", className="stat-label"),
            html.P(hot["town"], className="stat-value", style={"fontSize": "20px", "color": "var(--color-success)"}),
            html.P([
                html.Span(f"↑ {hot['growth_pct']:.1f}%", style={"color": "var(--color-success)", "fontWeight": "600"}),
                html.Span(f"  ·  {hot['transactions']:,} txns", style={"color": "var(--color-text-muted)", "fontSize": "12px"}),
            ]),
        ]),
        html.Div(className="stat-card", children=[
            html.P("COOLEST REGION", className="stat-label"),
            html.P(cool["town"], className="stat-value", style={"fontSize": "20px", "color": "var(--color-danger)"}),
            html.P([
                html.Span(f"↓ {abs(cool['growth_pct']):.1f}%", style={"color": "var(--color-danger)", "fontWeight": "600"}),
                html.Span(f"  ·  {cool['transactions']:,} txns", style={"color": "var(--color-text-muted)", "fontSize": "12px"}),
            ]),
        ]),
    ])

# ── Tool cards ────────────────────────────────────────────────
def tool_card(icon, title, desc, href):
    return html.A(className="tool-card", href=href, children=[
        html.Div(icon, className="tool-icon"),
        html.Div(className="tool-title", children=[title, html.Span("↗", className="arrow")]),
        html.P(desc, className="tool-desc"),
        html.Span("Explore →", className="tool-link"),
    ])

# ── Layout ────────────────────────────────────────────────────
layout = html.Div(className="page-wrapper", children=[

    # ── Hero ──────────────────────────────────────────────────
    html.Section(className="hero", children=[
        html.Div(className="hero-inner", children=[
            html.Div(className="hero-content", children=[
                html.H1(className="hero-title", children=[
                    html.Span("Make Your Next Property Decision "),
                    html.Span("With Confidence", className="accent-word"),
                ]),
                html.P(
                    "A data-driven reference tool for Singapore HDB resale buyers. "
                    "Explore market trends, compare amenities, and get a price projection — "
                    "all in one place.",
                    className="hero-subtitle"
                ),
            ]),
            # ── Right side: valuation search (was hero_visual()) ──
            html.Div(className="hero-search", children=[
                html.P("QUICK FLAT VALUATION", className="hero-search-title"),
                dcc.Input(
                    id="hero-postal", type="text", maxLength=6,
                    placeholder="Postal Code (e.g. 310058)",
                    className="form-input",
                    style={
                        "width": "100%",
                        "boxSizing": "border-box",
                        "marginBottom": "10px",
                        "border": "1px solid rgba(255,255,255,0.15)",
                        "borderRadius": "6px",
                        "background": "#FFFFFF"
                    }
                ),
                html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "10px", "marginBottom": "12px"}, children=[
                    dcc.Dropdown(
                        id="hero-flat-type",
                        options=[{"label": ft, "value": ft} for ft in FLAT_TYPES],
                        placeholder="Flat Type",
                        clearable=False,
                        className="form-select",
                        style={
                            "border": "1px solid rgba(255,255,255,0.15)",
                            "borderRadius": "6px",
                            "background": "#FFFFFF"
                        },
                    ),
                    dcc.Dropdown(
                        id="hero-storey",
                        options=[{"label": s, "value": s} for s in STOREY_RANGES],
                        placeholder="Storey Range (optional)",
                        clearable=True,
                        className="form-select",
                        style={
                            "border": "1px solid rgba(255,255,255,0.15)",
                            "borderRadius": "6px",
                            "background": "#FFFFFF"
                        },
                    ),
                ]),
                html.Button("Get Valuation →", id="hero-search-btn",
                            className="btn btn-primary",
                            style={"width": "100%", "justifyContent": "center", "padding": "11px"}),
            ]),
        ])
    ]),

    # ── Market Stats ───────────────────────────────────────────
    html.Section(className="stats-section", children=[
        html.Div(className="stats-section-inner", children=[
            html.Div(className="stats-header", children=[
                html.Div([
                    html.H2("Resale Market at a Glance", className="section-heading"),
                    html.P("National HDB resale statistics for the selected period.", className="section-sub",
                           style={"marginBottom": "0"}),
                ]),
                # Period toggle via RadioItems
                html.Div(className="dash-period-toggle", children=[
                    html.Button("3 Months", id="period-btn-3m", className="period-btn period-btn-active", **{"data-period": "3m"}),
                    html.Button("6 Months", id="period-btn-6m", className="period-btn", **{"data-period": "6m"}),
                    html.Button("1 Year",   id="period-btn-1y", className="period-btn", **{"data-period": "1y"}),
                ]),
                dcc.Store(id="landing-period", data="3m"),
            ]),
            html.Div(id="landing-stats-row", children=build_stats_row("3m")),
        ])
    ]),

    # ── Tool Overview ──────────────────────────────────────────
    html.Section(className="tools-section", children=[
        html.Div(className="tools-section-inner", children=[
            html.H2("Three Tools for Every Stage of Your Search", className="section-heading"),
            html.P(
                "Whether you're shortlisting towns, sizing up a listing, or comparing flats side-by-side — "
                "we've got you covered.",
                className="section-sub"
            ),
            html.Div(className="tools-grid", children=[
                tool_card("📊", "Market Analysis",
                          "Explore price trends, transaction volumes, and town-level statistics across all HDB towns in Singapore using an interactive choropleth map.",
                          "/market-analysis"),
                tool_card("🏠", "Flat Valuation",
                          "Enter a postal code and flat type to get a data-driven price projection range, comparable nearby transactions, and a listed-price indicator.",
                          "/flat-valuation"),
                tool_card("📍", "Amenities Comparison",
                          "Compare up to three flats side-by-side on distance to MRT, hawker centres, malls, polyclinics, schools, and parks.",
                          "/amenities-comparison"),
            ]),
        ])
    ]),
])

# ── Callbacks ─────────────────────────────────────────────────

@callback(
    Output("landing-period", "data"),
    Output("period-btn-3m", "className"),
    Output("period-btn-6m", "className"),
    Output("period-btn-1y", "className"),
    Input("period-btn-3m", "n_clicks"),
    Input("period-btn-6m", "n_clicks"),
    Input("period-btn-1y", "n_clicks"),
    prevent_initial_call=True,
)
def select_period(_n3m, _n6m, _n1y):
    from dash import ctx
    btn_map = {
        "period-btn-3m": "3m",
        "period-btn-6m": "6m",
        "period-btn-1y": "1y",
    }
    active = btn_map.get(ctx.triggered_id, "3m")
    classes = {p: "period-btn period-btn-active" if p == active else "period-btn"
               for p in ["3m", "6m", "1y"]}
    return active, classes["3m"], classes["6m"], classes["1y"]


@callback(
    Output("landing-stats-row", "children"),
    Input("landing-period", "data"),
)
def update_stats(period):
    return build_stats_row(period)


@callback(
    Output("valuation-prefill", "data"),
    Output("url", "pathname"),
    Input("hero-search-btn", "n_clicks"),
    State("hero-postal", "value"),
    State("hero-flat-type", "value"),
    State("hero-storey", "value"),
    prevent_initial_call=True,
)
def hero_search(n_clicks, postal, flat_type, storey):
    if not postal or len(postal.strip()) != 6 or not postal.strip().isdigit():
        return no_update, no_update
    if not flat_type:
        return no_update, no_update
    data = {"postal_code": postal.strip(), "flat_type": flat_type, "storey": storey}
    return data, "/flat-valuation"
