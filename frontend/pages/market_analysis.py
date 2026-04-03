import json
import os

import dash
import pandas as pd
from dash import html, dcc, callback, Output, Input, ctx
import plotly.graph_objects as go
import plotly.express as px

dash.register_page(__name__, path="/market-analysis", name="Market Analysis")

_BASE = os.path.dirname(os.path.dirname(__file__))

# ── Static assets ─────────────────────────────────────────────────────────────
with open(os.path.join(_BASE, "MasterPlan2019PlanningAreaBoundaryNoSea.geojson"), encoding="utf-8") as f:
    GEOJSON = json.load(f)

with open(os.path.join(_BASE, "..", "outputs", "market_stats.json"), encoding="utf-8") as f:
    STATS = json.load(f)

# ── Constants ──────────────────────────────────────────────────────────────────
FT_BUTTONS = [
    ("All Flats", "ALL"),
    ("3 Room",    "3 ROOM"),
    ("4 Room",    "4 ROOM"),
    ("5 Room",    "5 ROOM"),
    ("Executive", "EXECUTIVE"),
]

METRIC_OPTIONS = [
    {"label": "Transaction Count",                 "value": "txn_2025"},
    {"label": "Median Price",                      "value": "median_2025"},
    {"label": "YoY Change in Transaction Count",   "value": "txn_yoy_pct"},
    {"label": "YoY Change in Median Price",        "value": "median_yoy_pct"},
]

DIVERGING_METRICS = {"txn_yoy_pct", "median_yoy_pct"}

DATA_TOWNS = [k for k in STATS if k not in ("national", "town_about", "town_future_developments")]

_FT_BTN_IDS    = [f"ft-btn-{key.replace(' ', '-')}" for _, key in FT_BUTTONS]
_BTN_ID_TO_KEY = {bid: key for bid, (_, key) in zip(_FT_BTN_IDS, FT_BUTTONS)}


# ── Map ────────────────────────────────────────────────────────────────────────

def _fmt_value(val, metric):
    if metric in DIVERGING_METRICS:
        sign = "+" if val >= 0 else ""
        return f"{sign}{val:.1f}%"
    elif metric == "txn_2025":
        return f"{int(val):,}"
    else:
        return f"${val:,.0f}"


def make_choropleth(metric, flat_type):
    rows = [
        {"PLN_AREA_N": town, "value": STATS[town][flat_type][metric],
         "town_display": town.title()}
        for town in DATA_TOWNS
        if STATS.get(town, {}).get(flat_type, {}).get(metric) is not None
    ]
    df = pd.DataFrame(rows)

    if df.empty:
        return go.Figure(layout=dict(margin={"r": 0, "t": 0, "l": 0, "b": 0}, paper_bgcolor="rgba(0,0,0,0)"))

    # Pre-format hover values so the template can display them as strings
    df["value_fmt"] = df.apply(lambda r: _fmt_value(r["value"], metric), axis=1)

    is_pct = metric in DIVERGING_METRICS
    tick_fmt = ".1f" if is_pct else (",.0f" if metric != "txn_2025" else ",d")
    tick_prefix = "" if is_pct else ("$" if metric != "txn_2025" else "")
    tick_suffix = "%" if is_pct else ""

    kwargs = dict(
        geojson=GEOJSON,
        locations="PLN_AREA_N",
        featureidkey="properties.PLN_AREA_N",
        color="value",
        color_continuous_scale="RdBu_r" if is_pct else "YlOrRd",
        mapbox_style="carto-positron",
        zoom=10.2,
        center={"lat": 1.352, "lon": 103.82},
        opacity=0.75,
        custom_data=["town_display", "value_fmt"],
    )
    if is_pct:
        kwargs["color_continuous_midpoint"] = 0.0

    fig = px.choropleth_mapbox(df, **kwargs)
    fig.update_traces(
        marker_line_width=0.8,
        marker_line_color="#fff",
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
    )
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(
            title=None,
            thicknessmode="pixels", thickness=8,
            lenmode="fraction", len=0.35,
            x=0.01, xanchor="left",
            y=0.5, yanchor="middle",
            tickfont=dict(size=10, color="#888"),
            tickformat=tick_fmt,
            tickprefix=tick_prefix,
            ticksuffix=tick_suffix,
            outlinewidth=0,
        ),
    )
    return fig


# ── Charts ─────────────────────────────────────────────────────────────────────

def _base_chart_layout(height=210):
    return dict(
        margin={"r": 8, "t": 8, "l": 8, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        font=dict(family="Inter, sans-serif"),
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#9CA3AF"),
                   tickangle=-30, linecolor="#E5E7EB"),
        yaxis=dict(showgrid=True, gridcolor="#2D3748", tickformat="$,.0f",
                   tickfont=dict(size=10, color="#9CA3AF"), zeroline=False),
    )


def make_price_chart(grp_data, view):
    if view == "monthly":
        avg = grp_data.get("monthly_avg", {})
        keys = sorted(avg)
        fig = go.Figure(go.Scatter(
            x=keys, y=[avg[k] for k in keys],
            mode="lines+markers",
            line=dict(color="#3B82F6", width=2),
            marker=dict(size=5, color="#3B82F6"),
        ))
    else:
        avg = grp_data.get("quarterly_avg", {})
        keys = sorted(avg)
        fig = go.Figure(go.Scatter(
            x=keys, y=[avg[k] for k in keys],
            mode="lines+markers",
            line=dict(color="#1C4ED8", width=2),
            marker=dict(size=7, color="#1C4ED8"),
        ))
    fig.update_layout(**_base_chart_layout())
    return fig


# ── Stats panel ────────────────────────────────────────────────────────────────

def _change_span(abs_val, pct_val):
    arrow = "↑" if pct_val >= 0 else "↓"
    sign = "+" if abs_val >= 0 else ""
    return html.Span(
        f"{arrow} {abs(pct_val):.1f}% ({sign}{abs_val:,.0f})",
        className="stat-change positive" if pct_val >= 0 else "stat-change negative",
    )


def _txn_card(label, txn_dict):
    if not txn_dict or not txn_dict.get("block"):
        body = [html.P("—", className="txn-address")]
    else:
        body = [
            html.P(f"Block {txn_dict['block']} {txn_dict['street_name']}", className="txn-address"),
            html.P(txn_dict["flat_type"],    className="txn-flat-type"),
            html.P(txn_dict["storey_range"], className="txn-storey"),
            html.P(f"${txn_dict['resale_price']:,}", className="txn-price"),
        ]
    return html.Div(className="stats-mini-card", children=[
        html.P(label, className="stats-mini-label"),
        *body,
    ])


def stats_panel_content(pln_area, flat_type, chart_view="monthly"):
    if pln_area and pln_area in STATS:
        scope_key   = pln_area
        town_name   = pln_area.title()
        about_text  = STATS.get("town_about", {}).get(pln_area, "")
        future_text = STATS.get("town_future_developments", {}).get(pln_area, "")
        about_label = f"About {town_name}"
    else:
        scope_key   = "national"
        town_name   = "National Overview"
        about_text  = STATS.get("town_about", {}).get("NATIONAL", "")
        future_text = STATS.get("town_future_developments", {}).get("NATIONAL", "")
        about_label = "About Singapore"

    subtitle = "In the past year (2025)"

    grp = STATS.get(scope_key, {}).get(flat_type, {})

    txn_2025      = grp.get("txn_2025", 0)
    txn_yoy_abs   = grp.get("txn_yoy_abs", 0)
    txn_yoy_pct   = grp.get("txn_yoy_pct", 0.0)
    median_2025   = grp.get("median_2025", 0.0)
    median_yoy_abs = grp.get("median_yoy_abs", 0.0)
    median_yoy_pct = grp.get("median_yoy_pct", 0.0)

    chart_title = "AVERAGE PRICE BY MONTH (2025)" if chart_view == "monthly" else "AVERAGE PRICE BY QUARTER (2025)"
    chart_fig = make_price_chart(grp, chart_view) if grp else go.Figure()

    return [
        html.Div(className="stats-panel-header", children=[
            html.P(town_name, className="stats-panel-town"),
            html.P(subtitle,  className="stats-panel-region"),
        ]),
        html.Div(className="stats-panel-body", children=[

            # 2×2 stat cards
            html.Div(className="stats-grid-2", children=[
                html.Div(className="stats-mini-card", children=[
                    html.P("NO. OF TRANSACTIONS", className="stats-mini-label"),
                    html.P(f"{txn_2025:,}", className="stats-mini-value"),
                    html.P([_change_span(txn_yoy_abs, txn_yoy_pct)],
                           style={"fontSize": "12px", "marginTop": "3px"}),
                ]),
                html.Div(className="stats-mini-card", children=[
                    html.P("MEDIAN PRICE", className="stats-mini-label"),
                    html.P(f"${median_2025:,.0f}", className="stats-mini-value"),
                    html.P([_change_span(median_yoy_abs, median_yoy_pct)],
                           style={"fontSize": "12px", "marginTop": "3px"}),
                ]),
                _txn_card("HIGHEST PRICED TRANSACTION", grp.get("highest", {})),
                _txn_card("LOWEST PRICED TRANSACTION",  grp.get("lowest", {})),
            ]),

            # Combined Monthly / Quarterly chart
            html.Div(className="chart-section", children=[
                html.Div(style={"display": "flex", "alignItems": "center",
                                "justifyContent": "space-between", "marginBottom": "8px"}, children=[
                    html.P(chart_title, className="chart-section-label",
                           style={"margin": "0"}),
                    html.Div(className="flat-type-btn-group",
                             style={"padding": "2px", "gap": "2px"}, children=[
                        html.Button("Monthly",   id="chart-btn-monthly",
                                    className="ft-btn active" if chart_view == "monthly" else "ft-btn",
                                    n_clicks=0, style={"padding": "3px 10px", "fontSize": "11px"}),
                        html.Button("Quarterly", id="chart-btn-quarterly",
                                    className="ft-btn active" if chart_view == "quarterly" else "ft-btn",
                                    n_clicks=0, style={"padding": "3px 10px", "fontSize": "11px"}),
                    ]),
                ]),
                dcc.Graph(figure=chart_fig, config={"displayModeBar": False},
                          style={"height": "210px"}),
            ]),

            # About section
            html.Div(className="town-summary-section", children=[
                html.P(about_label, className="chart-section-label"),
                html.P(about_text or "No description available.",
                       className="town-summary-text"),
            ]),

            # Future developments section
            html.Div(className="developments-section", children=[
                html.P("Future Developments", className="developments-label"),
                html.P(future_text or "No upcoming developments have been confirmed for this town.",
                       className="developments-text"),
            ]),
        ]),
    ]


# ── Layout ─────────────────────────────────────────────────────────────────────

layout = html.Div(className="market-page", children=[

    html.Div(className="map-panel", children=[
        html.Div(className="map-controls", children=[
            dcc.Dropdown(
                id="map-metric",
                options=METRIC_OPTIONS,
                value="median_2025",
                clearable=False,
                className="form-select",
                style={"width": "270px", "fontSize": "13px"},
            ),
            html.Div(className="flat-type-btn-group", children=[
                html.Button(label, id=bid,
                            className="ft-btn active" if key == "ALL" else "ft-btn",
                            n_clicks=0)
                for bid, (label, key) in zip(_FT_BTN_IDS, FT_BUTTONS)
            ]),
        ]),
        dcc.Store(id="active-flat-type",  data="ALL"),
        dcc.Store(id="active-chart-view", data="monthly"),
        dcc.Graph(
            id="choropleth-map",
            figure=make_choropleth("median_2025", "ALL"),
            config={"displayModeBar": False, "scrollZoom": True},
            style={"height": "100%", "width": "100%"},
        ),
    ]),

    html.Div(id="stats-panel", className="stats-panel",
             children=stats_panel_content(None, "ALL", "monthly")),
])


# ── Callbacks ──────────────────────────────────────────────────────────────────

@callback(
    Output("active-flat-type", "data"),
    [Input(bid, "n_clicks") for bid in _FT_BTN_IDS],
    prevent_initial_call=True,
)
def set_flat_type(*_):
    return _BTN_ID_TO_KEY.get(ctx.triggered_id, "ALL")


@callback(
    [Output(bid, "className") for bid in _FT_BTN_IDS],
    Input("active-flat-type", "data"),
)
def update_ft_btn_styles(active):
    return ["ft-btn active" if key == active else "ft-btn" for _, key in FT_BUTTONS]


@callback(
    Output("active-chart-view", "data"),
    Input("chart-btn-monthly",   "n_clicks"),
    Input("chart-btn-quarterly", "n_clicks"),
    prevent_initial_call=True,
)
def set_chart_view(*_):
    return "quarterly" if ctx.triggered_id == "chart-btn-quarterly" else "monthly"


@callback(
    Output("choropleth-map", "figure"),
    Input("map-metric",       "value"),
    Input("active-flat-type", "data"),
)
def update_map(metric, flat_type):
    return make_choropleth(metric, flat_type)


@callback(
    Output("stats-panel", "children"),
    Input("choropleth-map",    "clickData"),
    Input("active-flat-type",  "data"),
    Input("active-chart-view", "data"),
)
def update_stats_panel(click_data, flat_type, chart_view):
    pln_area = None
    if click_data:
        pts = click_data.get("points", [])
        if pts:
            pln_area = pts[0].get("location")
    return stats_panel_content(pln_area, flat_type, chart_view)
