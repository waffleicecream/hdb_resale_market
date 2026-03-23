"""
Flat Valuation page — three-panel layout:
  Left:   Select flat form  → Estimated Current Value
  Centre: Nearby flats map
  Right:  Comparables table sorted by price similarity
"""

import re
import os
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback

dash.register_page(__name__, path="/flat-valuation",
                   name="Flat Valuation", title="Flat Valuation")

from data_store import DF, FLAT_TYPES

# ── OneMap geocoder ───────────────────────────────────────────────────────────
ONEMAP_GEOCODE_URL = "https://www.onemap.gov.sg/api/common/elastic/search"


def geocode_postal(postal_code: str):
    """Return (lat, lon) for a Singapore postal code via OneMap, or (None, None)."""
    try:
        r = requests.get(
            ONEMAP_GEOCODE_URL,
            params={"searchVal": postal_code, "returnGeom": "Y",
                    "getAddrDetails": "Y", "pageNum": 1},
            timeout=8,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        if results:
            return float(results[0]["LATITUDE"]), float(results[0]["LONGITUDE"])
    except Exception:
        pass
    return None, None


# ── Haversine distance ────────────────────────────────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
         + math.cos(phi1) * math.cos(phi2)
         * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Valuation logic ───────────────────────────────────────────────────────────
def find_comparables(
    flat_type, floor_area_sqm, floor_level, remaining_lease_yrs,
    lat, lon, n=20, radius_km=1.5, months_back=24,
):
    df = DF.copy()
    cutoff = pd.Timestamp.today() - pd.DateOffset(months=months_back)
    df = df[df["month"] >= cutoff]
    df = df[df["flat_type"] == flat_type.upper().strip()]

    if lat is not None and lon is not None and "lat" in df.columns:
        df = df.dropna(subset=["lat", "lon"])
        df["dist_km"] = df.apply(
            lambda r: haversine_km(lat, lon, r["lat"], r["lon"]), axis=1)
        df = df[df["dist_km"] <= radius_km]
    elif "town" in df.columns:
        df["dist_km"] = np.nan

    if df.empty:
        return df, None, None

    df = df.dropna(subset=["resale_price", "floor_area_sqm"])

    def _norm(col, target, d):
        rng = d[col].max() - d[col].min()
        return 0 if rng == 0 else abs(d[col] - target) / rng

    score = pd.Series(np.zeros(len(df)), index=df.index)
    score += 0.4 * _norm("floor_area_sqm", floor_area_sqm, df)
    if floor_level is not None and "floor_level" in df.columns:
        df_fl = df.dropna(subset=["floor_level"])
        if not df_fl.empty:
            score.loc[df_fl.index] += 0.3 * _norm("floor_level", floor_level, df_fl)
    if remaining_lease_yrs is not None and "remaining_lease" in df.columns:
        def _lease_yrs(s):
            if pd.isna(s): return np.nan
            m = re.search(r"(\d+)\s*year", str(s), re.I)
            return float(m.group(1)) if m else np.nan
        df["_lease_yrs"] = df["remaining_lease"].apply(_lease_yrs)
        df_lk = df.dropna(subset=["_lease_yrs"])
        if not df_lk.empty:
            score.loc[df_lk.index] += 0.2 * _norm("_lease_yrs", remaining_lease_yrs, df_lk)
    if "dist_km" in df.columns:
        df_dk = df.dropna(subset=["dist_km"])
        max_d = df_dk["dist_km"].max()
        if max_d > 0:
            score.loc[df_dk.index] += 0.1 * (df_dk["dist_km"] / max_d)

    df["_score"] = score
    top = df.nsmallest(n, "_score").copy()
    weights = 1 / (top["_score"] + 0.01)
    est_value = (top["resale_price"] * weights).sum() / weights.sum()
    q25, q75 = top["resale_price"].quantile(0.25), top["resale_price"].quantile(0.75)
    return top, est_value, (q25, q75)


# ── Valuation verdict ─────────────────────────────────────────────────────────
def valuation_verdict(listed_price, est_value):
    if listed_price is None or est_value is None or est_value == 0:
        return None, "secondary"
    pct = (listed_price - est_value) / est_value * 100
    if pct > 5:
        return f"Overvalued by {pct:.1f}%", "danger"
    elif pct < -5:
        return f"Undervalued by {abs(pct):.1f}%", "success"
    else:
        return f"Fair value (within {abs(pct):.1f}%)", "warning"


# ── Form row helper ───────────────────────────────────────────────────────────
def _form_row(label, input_el):
    return html.Div(
        [
            html.Label(label, className="form-label"),
            input_el,
        ],
        className="mb-3",
    )


def _empty_map():
    fig = go.Figure(go.Scattermapbox())
    fig.update_layout(
        mapbox={"style": "carto-positron",
                "center": {"lat": 1.3521, "lon": 103.8198}, "zoom": 11.5},
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="#f4f2ff",
    )
    return fig


# ── Layout ────────────────────────────────────────────────────────────────────
layout = html.Div(
    [
        dbc.Row(
            [
                # ── LEFT: Form + result ────────────────────────────────────────
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Div("Flat Details", className="page-header-title mb-3",
                                         style={"fontSize": "1.1rem"}),

                                # Valuation form — surface-form scope for input styling
                                html.Div(
                                    [
                                        _form_row("Flat Type *",
                                            dcc.Dropdown(
                                                id="fv-flat-type",
                                                options=[{"label": ft.title(), "value": ft}
                                                         for ft in FLAT_TYPES],
                                                value="4 ROOM",
                                                clearable=False,
                                            )),
                                        _form_row("Postal Code *",
                                            dbc.Input(id="fv-postal",
                                                      placeholder="e.g. 085201",
                                                      type="text", maxLength=6,
                                                      className="text-center")),
                                        _form_row("Flat Size *",
                                            dbc.InputGroup([
                                                dbc.Input(id="fv-area",
                                                          placeholder="e.g. 100",
                                                          type="number", min=20, max=300,
                                                          className="text-center"),
                                                dbc.InputGroupText("sqm"),
                                            ])),
                                        _form_row("Remaining Lease *",
                                            dbc.InputGroup([
                                                dbc.Input(id="fv-lease",
                                                          placeholder="e.g. 50",
                                                          type="number", min=1, max=99,
                                                          className="text-center"),
                                                dbc.InputGroupText("yrs"),
                                            ])),
                                        _form_row("Floor Level *",
                                            dbc.Input(id="fv-floor",
                                                      placeholder="e.g. 10",
                                                      type="number", min=1, max=50,
                                                      className="text-center")),
                                        _form_row("Listed Price (optional)",
                                            dbc.InputGroup([
                                                dbc.InputGroupText("$"),
                                                dbc.Input(id="fv-listed-price",
                                                          placeholder="e.g. 1,280,000",
                                                          type="number", min=0,
                                                          className="text-center"),
                                            ])),

                                        dbc.Button(
                                            [html.I(className="bi bi-search me-2"),
                                             "Search & Calculate"],
                                            id="fv-search",
                                            className="btn-cta w-100 mt-2",
                                        ),
                                    ],
                                    className="surface-form",
                                ),

                                html.P(
                                    "Estimates are based on the most comparable recent "
                                    "transactions within 1.5 km, matched on flat type, "
                                    "size, floor level, and remaining lease.",
                                    className="mt-3 mb-0",
                                    style={"fontSize": "0.72rem", "color": "#454652",
                                           "lineHeight": "1.5"},
                                ),
                            ],
                            className="valuation-form-panel",
                        ),

                        # Result card (populated by callback)
                        html.Div(id="fv-result-card", className="mt-3"),
                    ],
                    md=3,
                    className="pe-2",
                ),

                # ── CENTRE: Map ────────────────────────────────────────────────
                dbc.Col(
                    [
                        html.Div("Nearby Flats", className="page-header-title mb-3",
                                 style={"fontSize": "1.1rem"}),
                        dcc.Graph(
                            id="fv-map",
                            style={"height": "480px", "borderRadius": "12px"},
                            config={"displayModeBar": False},
                            figure=_empty_map(),
                        ),
                    ],
                    md=5,
                    className="px-2",
                ),

                # ── RIGHT: Comparables ─────────────────────────────────────────
                dbc.Col(
                    [
                        html.Div("Comparable Transactions", className="page-header-title mb-2",
                                 style={"fontSize": "1.1rem"}),

                        dbc.Row(
                            [
                                dbc.Col(
                                    html.Span("Sort by:", style={"fontSize": "0.78rem",
                                                                  "color": "#454652"}),
                                    width="auto", className="d-flex align-items-center",
                                ),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="fv-sort",
                                        options=[
                                            {"label": "Price",      "value": "resale_price"},
                                            {"label": "Similarity", "value": "_score"},
                                            {"label": "Date",       "value": "month"},
                                            {"label": "Distance",   "value": "dist_km"},
                                        ],
                                        value="resale_price",
                                        clearable=False,
                                        style={"fontSize": "0.82rem"},
                                    ),
                                ),
                            ],
                            className="mb-2 align-items-center surface-form",
                        ),

                        # Note on what "comparables" means
                        html.Div(
                            [
                                html.I(className="bi bi-clock-history me-1",
                                       style={"color": "#454652"}),
                                html.Span("Past sold transactions — not current listings.",
                                          style={"fontSize": "0.72rem", "color": "#454652"}),
                            ],
                            className="mb-3",
                        ),

                        html.Div(id="fv-comparables"),
                    ],
                    md=4,
                    className="ps-2",
                ),
            ],
            className="g-3 pt-3",
        ),

        dcc.Store(id="fv-store"),
    ],
    className="container-fluid px-3 py-2",
    style={"backgroundColor": "#fbf8ff", "minHeight": "calc(100vh - 64px)"},
)


# ── Callbacks ─────────────────────────────────────────────────────────────────
@callback(
    Output("fv-map",         "figure"),
    Output("fv-comparables", "children"),
    Output("fv-result-card", "children"),
    Output("fv-store",       "data"),
    Input("fv-search",       "n_clicks"),
    Input("fv-sort",         "value"),
    State("fv-flat-type",    "value"),
    State("fv-postal",       "value"),
    State("fv-area",         "value"),
    State("fv-lease",        "value"),
    State("fv-floor",        "value"),
    State("fv-listed-price", "value"),
    prevent_initial_call=True,
)
def search_flat(n_clicks, sort_col,
                flat_type, postal, area, lease, floor, listed_price):
    if not flat_type or not area:
        return (
            _empty_map(),
            html.P("Fill in Flat Type and Size to search.",
                   style={"fontSize": "0.85rem", "color": "#454652"}),
            "",
            None,
        )

    floor_level         = float(floor) if floor else None
    remaining_lease_yrs = float(lease) if lease else None

    # Geocode
    lat, lon = None, None
    if postal and re.match(r"^\d{6}$", str(postal).strip()):
        lat, lon = geocode_postal(postal.strip())

    comps, est_value, ci = find_comparables(
        flat_type=flat_type,
        floor_area_sqm=float(area),
        floor_level=floor_level,
        remaining_lease_yrs=remaining_lease_yrs,
        lat=lat, lon=lon,
    )

    if comps is None or comps.empty:
        msg = html.P("No comparable transactions found. Try adjusting the inputs.",
                     style={"fontSize": "0.85rem", "color": "#e74c3c"})
        return _empty_map(), msg, "", None

    # ── Map ───────────────────────────────────────────────────────────────────
    fig = _empty_map()

    if lat and lon:
        fig.add_trace(go.Scattermapbox(
            lat=[lat], lon=[lon],
            mode="markers",
            marker=dict(size=16, color="#00145d", symbol="marker"),
            name="Your flat",
            hovertext=f"Your flat | {postal}",
            hoverinfo="text",
        ))

    if "lat" in comps.columns and "lon" in comps.columns:
        comp_plot = comps.dropna(subset=["lat", "lon"])
        fig.add_trace(go.Scattermapbox(
            lat=comp_plot["lat"].tolist(),
            lon=comp_plot["lon"].tolist(),
            mode="markers",
            marker=dict(size=9, color="#5bc8af"),
            name="Comparables",
            text=comp_plot.apply(
                lambda r: f"Blk {r['block']} {r['street_name']}<br>"
                          f"${r['resale_price']:,.0f} | {r['flat_type']} | "
                          f"{r['floor_area_sqm']:.0f} sqm",
                axis=1,
            ).tolist(),
            hoverinfo="text",
        ))
        center = ({"lat": lat, "lon": lon} if lat and lon
                  else {"lat": comp_plot["lat"].mean(), "lon": comp_plot["lon"].mean()})
        fig.update_layout(mapbox_center=center, mapbox_zoom=13.5)

    # ── Result card ───────────────────────────────────────────────────────────
    n_comps = len(comps)
    if est_value:
        verdict_text, verdict_color = valuation_verdict(
            float(listed_price) if listed_price else None, est_value)

        result_card = html.Div([
            # Gradient estimate block
            html.Div(
                [
                    html.Div("Estimated Current Value", className="result-estimate-label"),
                    html.Div(f"${est_value:,.0f}", className="result-estimate-value"),
                    html.Div(f"Range: ${ci[0]:,.0f} – ${ci[1]:,.0f}",
                             className="result-estimate-range"),
                    html.Div(
                        [
                            html.I(className="bi bi-info-circle me-1"),
                            f"Based on {n_comps} comparable transactions",
                        ],
                        style={"fontSize": "0.72rem", "color": "rgba(255,255,255,0.60)",
                               "marginTop": "0.5rem"},
                    ),
                ],
                className="result-card-gradient p-3 text-center mb-2",
            ),

            # Methodology note
            html.Div(
                [
                    html.Div(
                        [
                            dbc.Badge("Personalised Estimate", color="dark",
                                      className="me-1",
                                      style={"fontSize": "0.62rem"}),
                            html.Span("≠ Market Average",
                                      style={"fontSize": "0.70rem", "color": "#454652"}),
                        ],
                        className="mb-1",
                    ),
                    html.Small(
                        [
                            f"Weighted average of {n_comps} similar past sales "
                            "within 1.5 km, last 24 months. Matched on flat type, "
                            "floor level, size and remaining lease. ",
                            html.A(
                                "See market-wide averages →",
                                href="/general-trends",
                                style={"color": "#00145d", "fontWeight": "600"},
                            ),
                        ],
                        style={"fontSize": "0.70rem", "lineHeight": "1.5"},
                    ),
                ],
                style={
                    "background": "#f4f2ff", "borderRadius": "10px",
                    "padding": "0.85rem 1rem", "marginBottom": "0.75rem",
                    "borderLeft": "3px solid #00145d",
                },
            ),

            # Verdict (only shown if listed price provided)
            dbc.Alert(verdict_text, color=verdict_color,
                      className="text-center py-2 mb-0",
                      style={"fontSize": "0.82rem"}) if verdict_text else "",
        ])
    else:
        result_card = ""

    # ── Comparable cards ──────────────────────────────────────────────────────
    sort_asc = sort_col == "_score"
    comps_sorted = comps.sort_values(sort_col, ascending=sort_asc)

    cards = []
    for _, row in comps_sorted.head(10).iterrows():
        addr = f"Blk {row.get('block', '')} {row.get('street_name', '')}".strip()

        month_str = (
            row["month"].strftime("%b %Y")
            if pd.notna(row.get("month")) else "—"
        )

        dist_txt = (
            f" · {row['dist_km']:.2f} km"
            if "dist_km" in row and pd.notna(row["dist_km"]) else ""
        )

        if listed_price:
            lp = float(listed_price)
            diff = lp - row["resale_price"]
            sign = "+" if diff > 0 else ""
            verdict_line = html.Small(
                f"{'↑' if diff > 0 else '↓'} Listed ${abs(diff):,.0f} "
                f"{'above' if diff > 0 else 'below'} this comparable",
                style={"fontSize": "0.70rem", "color": "#454652",
                       "display": "block", "marginTop": "0.25rem"},
            )
        else:
            verdict_line = ""

        cards.append(
            html.Div(
                [
                    # Address + price
                    html.Div(
                        [
                            html.Strong(addr, style={"fontSize": "0.82rem"}),
                            html.Span(
                                f"  ${row['resale_price']:,.0f}",
                                style={"color": "#5bc8af", "fontWeight": "700",
                                       "marginLeft": "0.4rem", "fontSize": "0.88rem"},
                            ),
                        ],
                        className="mb-1",
                    ),
                    # Date + distance
                    html.Div(
                        [
                            html.I(className="bi bi-calendar3 me-1",
                                   style={"color": "#454652"}),
                            html.Span(f"Sold {month_str}{dist_txt}",
                                      style={"fontSize": "0.72rem", "color": "#454652"}),
                        ],
                        className="mb-1",
                    ),
                    # Flat details
                    html.Small(
                        f"{row['flat_type'].title()} · {row['floor_area_sqm']:.0f} sqm",
                        style={"fontSize": "0.72rem", "color": "#454652"},
                    ),
                    verdict_line,
                ],
                className="comp-card",
            )
        )

    return fig, cards, result_card, comps.to_json(date_format="iso")
