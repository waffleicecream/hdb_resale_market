"""
General Trends page — Singapore HDB choropleth map by town.
Matches the 'PropertyMinBrothers' mockup with:
  - Growth / Average Price toggle
  - Flat Type checkboxes
  - Year slider
"""

import os
import json
import requests

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, callback

dash.register_page(__name__, path="/general-trends",
                   name="General Trends", title="General Trends")

# ── Import shared data from data_store ────────────────────────────────────────
from data_store import DF, FLAT_TYPES, YEAR_MIN, YEAR_MAX

# ── Load the pre-built town GeoJSON from backend outputs ──────────────────────
#  The backend already produced outputs/town_choropleth.geojson with:
#    properties.town  (title-case town name, e.g. "Ang Mo Kio")
#    properties.median_price_2025, cagr_1yr_pct, cagr_3yr_pct, cagr_5yr_pct …
_GJ_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "town_choropleth.geojson")

def _load_geojson():
    if os.path.exists(_GJ_PATH):
        with open(_GJ_PATH) as f:
            return json.load(f)
    print("town_choropleth.geojson not found — scatter map will be used as fallback")
    return None

GJ = _load_geojson()

# Pre-extract the static CAGR data from GeoJSON properties for the Growth mode
if GJ:
    _cagr_rows = [
        {
            "town_title": f["properties"]["town"],
            "town_upper": f["properties"]["town"].upper(),
            "cagr_1yr":   f["properties"].get("cagr_1yr_pct"),
            "cagr_3yr":   f["properties"].get("cagr_3yr_pct"),
            "cagr_5yr":   f["properties"].get("cagr_5yr_pct"),
            "above_1yr":  f["properties"].get("above_national_1yr", False),
        }
        for f in GJ["features"]
    ]
    DF_CAGR = pd.DataFrame(_cagr_rows)
else:
    DF_CAGR = pd.DataFrame()

# Map HDB town names → planning area names in the GeoJSON
# (GeoJSON uses UPPERCASE 'PLN_AREA_N' or similar)
TOWN_ALIAS = {
    "KALLANG/WHAMPOA": "KALLANG",
    "MARINE PARADE":   "MARINE PARADE",
    "CENTRAL AREA":    "DOWNTOWN CORE",
}

# ── Town centroids (fallback if GeoJSON unavailable) ─────────────────────────
TOWN_CENTROIDS = {
    "ANG MO KIO":    (1.3691, 103.8454),
    "BEDOK":         (1.3236, 103.9273),
    "BISHAN":        (1.3526, 103.8352),
    "BUKIT BATOK":   (1.3490, 103.7495),
    "BUKIT MERAH":   (1.2819, 103.8239),
    "BUKIT PANJANG": (1.3774, 103.7719),
    "BUKIT TIMAH":   (1.3294, 103.8021),
    "CENTRAL AREA":  (1.2894, 103.8497),
    "CHOA CHU KANG": (1.3840, 103.7470),
    "CLEMENTI":      (1.3162, 103.7649),
    "GEYLANG":       (1.3201, 103.8918),
    "HOUGANG":       (1.3612, 103.8863),
    "JURONG EAST":   (1.3329, 103.7436),
    "JURONG WEST":   (1.3404, 103.7090),
    "KALLANG/WHAMPOA": (1.3100, 103.8650),
    "MARINE PARADE": (1.3022, 103.9070),
    "PASIR RIS":     (1.3721, 103.9474),
    "PUNGGOL":       (1.4043, 103.9021),
    "QUEENSTOWN":    (1.2942, 103.7861),
    "SEMBAWANG":     (1.4491, 103.8185),
    "SENGKANG":      (1.3868, 103.8914),
    "SERANGOON":     (1.3554, 103.8679),
    "TAMPINES":      (1.3496, 103.9568),
    "TOA PAYOH":     (1.3343, 103.8563),
    "WOODLANDS":     (1.4382, 103.7890),
    "YISHUN":        (1.4304, 103.8354),
    "BUKIT TIMAH":   (1.3294, 103.8021),
}

# ── Layout ────────────────────────────────────────────────────────────────────
layout = html.Div(
    [
        html.H4(
            "Town Overview of Singapore's HDB Landscape at a glance",
            className="text-center fw-bold my-3",
        ),

        dbc.Row(
            [
                # ── Left controls ─────────────────────────────────────────────
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H6("Flat Type", className="fw-bold mb-2"),
                                dbc.Checklist(
                                    id="gt-flat-type",
                                    options=[{"label": ft.title(), "value": ft}
                                             for ft in FLAT_TYPES],
                                    value=FLAT_TYPES,   # all selected by default
                                    switch=False,
                                    className="small",
                                    input_checked_style={"backgroundColor": "#27ae60",
                                                         "borderColor": "#27ae60"},
                                ),
                            ],
                            className="border rounded p-3 bg-white shadow-sm mb-3",
                        ),
                    ],
                    md=2,
                    className="pe-0",
                ),

                # ── Choropleth / map ──────────────────────────────────────────
                dbc.Col(
                    [
                        dcc.Graph(
                            id="gt-map",
                            style={"height": "520px"},
                            config={"scrollZoom": True, "displayModeBar": True},
                        ),
                    ],
                    md=8,
                    className="px-1",
                ),

                # ── Right legend ──────────────────────────────────────────────
                dbc.Col(
                    [
                        html.H6("Legend", className="fw-bold"),
                        html.Div(id="gt-legend", className="small"),
                    ],
                    md=2,
                    className="ps-0",
                ),
            ],
            className="mb-2 align-items-start",
        ),

        # ── Toggle + Year slider ───────────────────────────────────────────────
        dbc.Row(
            dbc.Col(
                [
                    dbc.ButtonGroup(
                        [
                            dbc.Button("Growth",        id="btn-growth",   n_clicks=0,
                                       color="secondary", outline=True, size="sm"),
                            dbc.Button("Average Price", id="btn-avgprice", n_clicks=0,
                                       color="secondary", outline=True, size="sm",
                                       className="active"),
                        ],
                        id="gt-toggle",
                        className="me-4",
                    ),
                    html.Span("◀", className="me-2 text-muted"),
                    dcc.Slider(
                        id="gt-year",
                        min=YEAR_MIN,
                        max=YEAR_MAX,
                        step=1,
                        value=YEAR_MAX,
                        marks={y: str(y) for y in range(YEAR_MIN, YEAR_MAX + 1, 2)},
                        tooltip={"placement": "bottom", "always_visible": False},
                        className="flex-grow-1",
                    ),
                    html.Span("▶", className="ms-2 text-muted"),
                ],
                className="d-flex align-items-center px-3 py-2",
            )
        ),
    ],
    className="container-fluid px-3 py-2",
)

# ── Callbacks ─────────────────────────────────────────────────────────────────
@callback(
    Output("gt-map", "figure"),
    Output("gt-legend", "children"),
    Input("gt-flat-type", "value"),
    Input("gt-year",      "value"),
    Input("btn-growth",   "n_clicks"),
    Input("btn-avgprice", "n_clicks"),
)
def update_map(flat_types, year, n_growth, n_avgprice):
    # Determine metric from last-clicked button
    ctx = dash.callback_context
    metric = "avg_price"
    if ctx.triggered:
        btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if btn_id == "btn-growth":
            metric = "growth"

    # Filter data
    df = DF.copy()
    if flat_types:
        df = df[df["flat_type"].isin(flat_types)]
    df = df[df["year"] == year]

    if df.empty:
        fig = go.Figure()
        fig.update_layout(title=f"No data for {year}")
        return fig, ""

    # Aggregate by town
    town_agg = (
        df.groupby("town")["resale_price"]
        .agg(avg_price="mean", count="count")
        .reset_index()
    )

    if metric == "growth":
        # YoY price growth vs previous year
        df_prev = DF.copy()
        if flat_types:
            df_prev = df_prev[df_prev["flat_type"].isin(flat_types)]
        df_prev = df_prev[df_prev["year"] == max(YEAR_MIN, year - 1)]
        prev_agg = (
            df_prev.groupby("town")["resale_price"]
            .mean()
            .reset_index()
            .rename(columns={"resale_price": "prev_price"})
        )
        town_agg = town_agg.merge(prev_agg, on="town", how="left")
        town_agg["avg_price"] = town_agg["avg_price"].fillna(0)
        town_agg["prev_price"] = town_agg["prev_price"].fillna(0)
        town_agg["growth"] = (
            (town_agg["avg_price"] - town_agg["prev_price"])
            / town_agg["prev_price"].replace(0, np.nan)
            * 100
        ).round(1)
        color_col   = "growth"
        color_label = "YoY Growth (%)"
        color_scale = "RdYlGn"
        hover_fmt   = "Growth: %{customdata[0]:.1f}%"
        range_color = [-10, 10]
    else:
        color_col   = "avg_price"
        color_label = "Avg Price (SGD)"
        color_scale = "Blues"
        hover_fmt   = "Avg Price: $%{customdata[0]:,.0f}"
        town_agg["avg_price"] = town_agg["avg_price"].round(0)
        range_color = [town_agg["avg_price"].quantile(0.05),
                       town_agg["avg_price"].quantile(0.95)]

    # Add lat/lon from centroids
    town_agg["lat"] = town_agg["town"].map(
        lambda t: TOWN_CENTROIDS.get(t, (1.35, 103.82))[0])
    town_agg["lon"] = town_agg["town"].map(
        lambda t: TOWN_CENTROIDS.get(t, (1.35, 103.82))[1])

    # Build choropleth using the pre-built town GeoJSON (featureidkey = properties.town)
    # The GeoJSON uses title-case town names; normalise our uppercase town names
    if GJ is not None:
        town_agg["town_title"] = town_agg["town"].str.title()
        # Special cases that don't title-case cleanly
        TITLE_FIX = {
            "Kallang/Whampoa": "Kallang/Whampoa",
            "Bukit Merah":     "Bukit Merah",
        }
        town_agg["town_title"] = town_agg["town_title"].replace(TITLE_FIX)

        # Optionally merge CAGR from pre-computed GeoJSON for growth mode
        if metric == "growth" and not DF_CAGR.empty:
            town_agg = town_agg.merge(
                DF_CAGR[["town_title", "cagr_1yr"]],
                on="town_title", how="left",
            )
            town_agg["growth"] = town_agg["cagr_1yr"].round(1)

        try:
            fig = px.choropleth_mapbox(
                town_agg,
                geojson=GJ,
                locations="town_title",
                featureidkey="properties.town",
                color=color_col,
                color_continuous_scale=color_scale,
                range_color=range_color,
                hover_name="town",
                hover_data={color_col: True, "count": True, "town_title": False},
                labels={color_col: color_label, "count": "Transactions"},
                mapbox_style="carto-positron",
                center={"lat": 1.3521, "lon": 103.8198},
                zoom=10.5,
                opacity=0.75,
            )
        except Exception as e:
            print(f"Choropleth failed ({e}), using scatter fallback")
            fig = _scatter_map(town_agg, color_col, color_label, color_scale, range_color)
    else:
        fig = _scatter_map(town_agg, color_col, color_label, color_scale, range_color)

    fig.update_layout(
        margin={"r": 0, "t": 30, "l": 0, "b": 0},
        coloraxis_colorbar=dict(title=color_label, thickness=12, len=0.6),
        title=f"{'Price Growth' if metric == 'growth' else 'Average Price'} by Town — {year}",
        title_font_size=13,
    )

    # Legend HTML
    def _legend_bar(color):
        return html.Div(style={
            "width": "18px", "height": "18px",
            "backgroundColor": color, "display": "inline-block",
            "marginRight": "6px", "borderRadius": "3px",
        })

    legend = [
        _legend_bar("#1a5276"), html.Span("High", className="me-3"), html.Br(),
        _legend_bar("#aed6f1"), html.Span("Low"),
    ] if metric == "avg_price" else [
        _legend_bar("#27ae60"), html.Span("Strong growth", className="me-3"), html.Br(),
        _legend_bar("#e74c3c"), html.Span("Decline"),
    ]

    return fig, legend


def _scatter_map(town_agg, color_col, color_label, color_scale, range_color):
    """Fallback: scatter map using town centroids."""
    fig = px.scatter_mapbox(
        town_agg,
        lat="lat",
        lon="lon",
        size="count",
        color=color_col,
        color_continuous_scale=color_scale,
        range_color=range_color,
        hover_name="town",
        hover_data={color_col: True, "count": True, "lat": False, "lon": False},
        labels={color_col: color_label, "count": "Transactions"},
        mapbox_style="carto-positron",
        center={"lat": 1.3521, "lon": 103.8198},
        zoom=10.5,
        size_max=35,
        opacity=0.8,
    )
    return fig
