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
    ("2 Room",    "2 ROOM"),
    ("3 Room",    "3 ROOM"),
    ("4 Room",    "4 ROOM"),
    ("5 Room",    "5 ROOM"),
    ("Executive", "EXECUTIVE"),
]

METRIC_OPTIONS = [
    {"label": "Transaction Count",                 "value": "txn_2025"},
    {"label": "Average Price",                     "value": "median_2025"},
    {"label": "YoY Change in Transaction Count",   "value": "txn_yoy_pct"},
    {"label": "YoY Change in Average Price",       "value": "median_yoy_pct"},
]

METRIC_TOOLTIPS = {
    "txn_yoy_pct":    "Refers to % change in transaction count across the 2 latest full years (from 2024 to 2025), by town",
    "median_yoy_pct": "Refers to % change in average price across the 2 latest full years (from 2024 to 2025), by town",
}

DIVERGING_METRICS = {"txn_yoy_pct", "median_yoy_pct"}

# ── Fixed colour-scale ranges (consistent across all flat types) ───────────────
# Derived from p90/p95 analysis to avoid outlier dominance:
#   txn_2025:      cap at 1,000 (p90 across flat types ~490, ALL goes to 1,920)
#   median_2025:   $300K–$1.2M  (p95 = $1.1M; tighter than $1.5M for better contrast)
#   txn_yoy_pct:   ±30%         (p95 = ±47%; 200% outliers are tiny-base anomalies)
#   median_yoy_pct: −10%→+15%  (asymmetric; almost all towns in this band)
_SCALE = {
    "txn_2025":      (0,        1_000),
    "median_2025":   (300_000,  1_200_000),
    "txn_yoy_pct":   (-30.0,    30.0),
    "median_yoy_pct":(-15.0,    15.0),
}
# Blue(neg)→White(0)→Red(pos), white pinned at position 0.5
_BWR = [
    [0.0,  "#2166AC"],
    [0.25, "#92C5DE"],
    [0.5,  "#F7F7F7"],
    [0.75, "#F4A582"],
    [0.875,"#D6604D"],
    [1.0,  "#B2182B"],
]

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
    active, zero = [], []
    for town in DATA_TOWNS:
        d = STATS.get(town, {}).get(flat_type, {})
        val = d.get(metric)
        txn = d.get("txn_2025", 0)
        if val is None:
            continue
        row = {"PLN_AREA_N": town, "value": val, "town_display": town.title()}
        (zero if txn == 0 else active).append(row)

    df_active = pd.DataFrame(active)
    df_zero   = pd.DataFrame(zero)
    empty_layout = dict(margin={"r": 0, "t": 0, "l": 0, "b": 0}, paper_bgcolor="rgba(0,0,0,0)")

    if df_active.empty and df_zero.empty:
        return go.Figure(layout=empty_layout)

    is_pct  = metric in DIVERGING_METRICS
    tick_fmt    = ".1f"  if is_pct else (",.0f" if metric != "txn_2025" else ",d")
    tick_prefix = ""     if is_pct else ("$"    if metric != "txn_2025" else "")
    tick_suffix = "%"    if is_pct else ""

    scale_min, scale_max = _SCALE[metric]
    scale_kwargs = dict(
        color_continuous_scale=_BWR if is_pct else "YlOrRd",
        range_color=[scale_min, scale_max],
    )

    common = dict(
        geojson=GEOJSON,
        featureidkey="properties.PLN_AREA_N",
        mapbox_style="carto-positron",
        zoom=10.2,
        center={"lat": 1.352, "lon": 103.82},
        opacity=0.75,
    )

    if not df_active.empty:
        df_active["value_fmt"] = df_active.apply(lambda r: _fmt_value(r["value"], metric), axis=1)
        fig = px.choropleth_mapbox(
            df_active, locations="PLN_AREA_N", color="value",
            custom_data=["town_display", "value_fmt"],
            **common, **scale_kwargs,
        )
        fig.update_traces(
            marker_line_width=0.8, marker_line_color="#fff",
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
        )
    else:
        fig = go.Figure(layout=empty_layout)

    # Grey layer for towns with 0 transactions
    if not df_zero.empty:
        fig.add_trace(go.Choroplethmapbox(
            geojson=GEOJSON,
            featureidkey="properties.PLN_AREA_N",
            locations=df_zero["PLN_AREA_N"].tolist(),
            z=[0] * len(df_zero),
            colorscale=[[0, "#CBD5E1"], [1, "#CBD5E1"]],
            showscale=False,
            marker_line_width=0.8, marker_line_color="#fff", marker_opacity=0.75,
            customdata=list(zip(df_zero["town_display"], ["No transactions in 2025"] * len(df_zero))),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
            showlegend=False,
        ))

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
        about_label = "About SG's HDB Resale Market"

    subtitle = "In the past year (2025)"

    grp = STATS.get(scope_key, {}).get(flat_type, {})

    txn_2025      = grp.get("txn_2025", 0)
    txn_yoy_abs   = grp.get("txn_yoy_abs", 0)
    txn_yoy_pct   = grp.get("txn_yoy_pct", 0.0)
    median_2025   = grp.get("median_2025", 0.0)
    median_yoy_abs = grp.get("median_yoy_abs", 0.0)
    median_yoy_pct = grp.get("median_yoy_pct", 0.0)

    chart_title = "AVERAGE PRICE BY MONTH" if chart_view == "monthly" else "AVERAGE PRICE BY QUARTER"
    chart_fig = make_price_chart(grp, chart_view) if grp else go.Figure()

    # Concise national about text
    if scope_key == "national":
        about_text = (
            "Singapore's HDB resale market covers 26 towns, with prices shaped by location, "
            "flat type, floor level, and remaining lease. Mature central estates command significant "
            "premiums over newer towns. Buyers include upgraders, first-timers ineligible for BTO, "
            "and PRs — making this market a key indicator of housing affordability."
        )

    return [
        html.Div(className="stats-panel-header", children=[
            html.P(town_name, className="stats-panel-town"),
            html.P(subtitle,  className="stats-panel-region",
                   style={"fontSize": "13px"}),
        ]),
        html.Div(className="stats-panel-body", children=[

            # 2×2 stat cards
            html.Div(className="stats-grid-2", children=[
                html.Div(className="stats-mini-card", children=[
                    html.P("NO. OF TRANSACTIONS", className="stats-mini-label"),
                    html.P(f"{txn_2025:,}", className="stats-mini-value"),
                    html.P([_change_span(txn_yoy_abs, txn_yoy_pct),
                            html.Span(" from 2024", style={"fontSize": "11px", "color": "#9CA3AF"})],
                           style={"fontSize": "12px", "marginTop": "3px"}),
                ]),
                html.Div(className="stats-mini-card", children=[
                    html.P("AVERAGE PRICE", className="stats-mini-label"),
                    html.P(f"${median_2025:,.0f}", className="stats-mini-value"),
                    html.P([_change_span(median_yoy_abs, median_yoy_pct),
                            html.Span(" from 2024", style={"fontSize": "11px", "color": "#9CA3AF"})],
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
                html.P(about_label, className="chart-section-label",
                       style={"color": "#1E293B"}),
                html.P(about_text or "No description available.",
                       className="town-summary-text"),
            ]),

            # Future developments section
            html.Div(className="developments-section", children=[
                html.P("Future Developments", className="developments-label",
                       style={"color": "#1E293B"}),
                html.P(future_text or "No upcoming developments have been confirmed for this town.",
                       className="developments-text"),
            ]),
        ]),
    ]


# ── Layout ─────────────────────────────────────────────────────────────────────

layout = html.Div(className="market-page", children=[

    html.Div(className="map-panel", children=[
        html.Div(className="map-controls", children=[
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "6px"}, children=[
                dcc.Dropdown(
                    id="map-metric",
                    options=METRIC_OPTIONS,
                    value="median_2025",
                    clearable=False,
                    className="form-select",
                    style={"width": "330px", "fontSize": "13px"},
                ),
                # Info icon — shown only when a YoY metric is selected
                html.Div(id="metric-info-wrap", className="metric-info-wrap", children=[
                    html.Span("ℹ", className="metric-info-icon", id="metric-info-icon"),
                    html.Div(id="metric-info-tooltip", className="metric-info-tooltip"),
                ]),
            ]),
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
    Output("metric-info-wrap",    "style"),
    Output("metric-info-tooltip", "children"),
    Input("map-metric", "value"),
)
def update_metric_info(metric):
    tip = METRIC_TOOLTIPS.get(metric)
    if tip:
        return {"display": "flex"}, tip
    return {"display": "none"}, ""


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
