"""
Flat Valuation page — matches the three-panel mockup:
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
from dash import dcc, html, Input, Output, State, callback, dash_table

dash.register_page(__name__, path="/flat-valuation",
                   name="Flat Valuation", title="Flat Valuation")

from data_store import DF, FLAT_TYPES

# ── OneMap geocoder ───────────────────────────────────────────────────────────
ONEMAP_GEOCODE_URL = "https://www.onemap.gov.sg/api/common/elastic/search"

def geocode_postal(postal_code: str):
    """Return (lat, lon) for a Singapore postal code using OneMap, or (None, None)."""
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
    flat_type: str,
    floor_area_sqm: float,
    floor_level: float,
    remaining_lease_yrs: float,
    lat: float,
    lon: float,
    n: int = 20,
    radius_km: float = 1.5,
    months_back: int = 24,
):
    """
    Return the N most similar recent transactions within radius_km.
    Similarity score is a weighted Euclidean distance in feature space.
    """
    df = DF.copy()

    # Time window
    cutoff = pd.Timestamp.today() - pd.DateOffset(months=months_back)
    df = df[df["month"] >= cutoff]

    # Same flat type
    df = df[df["flat_type"] == flat_type.upper().strip()]

    # Spatial filter
    if lat is not None and lon is not None and "lat" in df.columns:
        df = df.dropna(subset=["lat", "lon"])
        df["dist_km"] = df.apply(
            lambda r: haversine_km(lat, lon, r["lat"], r["lon"]), axis=1
        )
        df = df[df["dist_km"] <= radius_km]
    elif "town" in df.columns:
        df["dist_km"] = np.nan

    if df.empty:
        return df, None, None

    df = df.dropna(subset=["resale_price", "floor_area_sqm"])

    # Similarity: normalised feature distance
    def _norm(col, target, df):
        rng = df[col].max() - df[col].min()
        return 0 if rng == 0 else abs(df[col] - target) / rng

    score = pd.Series(np.zeros(len(df)), index=df.index)
    score += 0.4 * _norm("floor_area_sqm", floor_area_sqm, df)
    if floor_level is not None and "floor_level" in df.columns:
        df_fl = df.dropna(subset=["floor_level"])
        if not df_fl.empty:
            score.loc[df_fl.index] += 0.3 * _norm("floor_level", floor_level, df_fl)
    if remaining_lease_yrs is not None and "remaining_lease" in df.columns:
        # Try to parse numeric remaining lease
        def _lease_yrs(s):
            if pd.isna(s):
                return np.nan
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

    # Estimated value
    weights = 1 / (top["_score"] + 0.01)
    est_value = (top["resale_price"] * weights).sum() / weights.sum()

    # Confidence interval (IQR-based)
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


# ── Helper: one form row ──────────────────────────────────────────────────────
def _form_row(label, input_el):
    return html.Div(
        [
            html.Label(label, className="small text-white-50 mb-1"),
            input_el,
        ],
        className="mb-2",
    )


def _empty_map():
    fig = go.Figure(go.Scattermapbox())
    fig.update_layout(
        mapbox={"style": "carto-positron", "center": {"lat": 1.3521, "lon": 103.8198},
                "zoom": 11.5},
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="#f8f9fa",
    )
    return fig


# ── Layout ────────────────────────────────────────────────────────────────────
layout = html.Div(
    [
        dbc.Row(
            [
                # ── LEFT: Select flat + result ─────────────────────────────────
                dbc.Col(
                    [
                        html.H5("Select flat", className="fw-bold text-center border-bottom pb-2"),
                        # Form
                        html.Div(
                            [
                                _form_row("Flat Type *",
                                          dcc.Dropdown(
                                              id="fv-flat-type",
                                              options=[{"label": ft.title(), "value": ft}
                                                       for ft in FLAT_TYPES],
                                              value="4 ROOM",
                                              clearable=False,
                                              className="form-control p-0 border-0",
                                          )),
                                _form_row("Postal Code *",
                                          dbc.Input(id="fv-postal", placeholder="e.g. 085201",
                                                    type="text", maxLength=6, className="text-center")),
                                _form_row("Flat Size *",
                                          dbc.InputGroup([
                                              dbc.Input(id="fv-area", placeholder="e.g. 100",
                                                        type="number", min=20, max=300,
                                                        className="text-center"),
                                              dbc.InputGroupText("SQM"),
                                          ])),
                                _form_row("Remaining Lease *",
                                          dbc.InputGroup([
                                              dbc.Input(id="fv-lease", placeholder="e.g. 50",
                                                        type="number", min=1, max=99,
                                                        className="text-center"),
                                              dbc.InputGroupText("YRS"),
                                          ])),
                                _form_row("Floor Level *",
                                          dbc.Input(id="fv-floor", placeholder="e.g. 10",
                                                    type="number", min=1, max=50,
                                                    className="text-center")),
                                _form_row("Listed Price (optional)",
                                          dbc.InputGroup([
                                              dbc.InputGroupText("$"),
                                              dbc.Input(id="fv-listed-price", placeholder="e.g. 1280000",
                                                        type="number", min=0, className="text-center"),
                                          ])),
                                dbc.Button(
                                    "Search", id="fv-search", color="primary",
                                    className="w-100 mt-3",
                                ),
                            ],
                            className="bg-dark text-white rounded p-3 mb-3",
                            style={"fontSize": "0.85rem"},
                        ),

                        # Result card
                        html.Div(id="fv-result-card"),
                    ],
                    md=3,
                    className="pe-2",
                ),

                # ── CENTRE: Map ────────────────────────────────────────────────
                dbc.Col(
                    [
                        html.H5("Nearby flats", className="fw-bold text-center border-bottom pb-2"),
                        dcc.Graph(
                            id="fv-map",
                            style={"height": "520px"},
                            config={"displayModeBar": False},
                            figure=_empty_map(),
                        ),
                    ],
                    md=5,
                    className="px-1",
                ),

                # ── RIGHT: Comparables ─────────────────────────────────────────
                dbc.Col(
                    [
                        html.H5(
                            "Comparables",
                            className="fw-bold text-center border-bottom pb-2",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(html.Small("Sort by:", className="text-muted"), width="auto"),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="fv-sort",
                                        options=[
                                            {"label": "Price",       "value": "resale_price"},
                                            {"label": "Similarity",  "value": "_score"},
                                            {"label": "Date",        "value": "month"},
                                            {"label": "Distance",    "value": "dist_km"},
                                        ],
                                        value="resale_price",
                                        clearable=False,
                                        style={"fontSize": "0.8rem"},
                                    ),
                                ),
                            ],
                            className="mb-2 align-items-center",
                        ),
                        html.Div(id="fv-comparables"),
                    ],
                    md=4,
                    className="ps-1",
                ),
            ],
            className="g-3 pt-3",
        ),

        dcc.Store(id="fv-store"),  # holds comparables JSON
    ],
    className="container-fluid px-3 py-2",
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
        return _empty_map(), html.P("Fill in Flat Type and Size to search.", className="text-muted small"), "", None

    floor_level          = float(floor) if floor else None
    remaining_lease_yrs  = float(lease) if lease else None

    # Geocode
    lat, lon = None, None
    if postal and re.match(r"^\d{6}$", str(postal).strip()):
        lat, lon = geocode_postal(postal.strip())

    # Find comparables
    comps, est_value, ci = find_comparables(
        flat_type=flat_type,
        floor_area_sqm=float(area),
        floor_level=floor_level,
        remaining_lease_yrs=remaining_lease_yrs,
        lat=lat,
        lon=lon,
    )

    if comps is None or comps.empty:
        msg = html.P("No comparable transactions found. Try adjusting the inputs.", className="text-warning small")
        return _empty_map(), msg, "", None

    # ── Map ───────────────────────────────────────────────────────────────────
    fig = _empty_map()

    # Plot subject property
    if lat and lon:
        fig.add_trace(go.Scattermapbox(
            lat=[lat], lon=[lon],
            mode="markers",
            marker=dict(size=16, color="#2980b9", symbol="marker"),
            name="Your flat",
            hovertext=f"Your flat | {postal}",
            hoverinfo="text",
        ))

    # Plot comparables
    if "lat" in comps.columns and "lon" in comps.columns:
        comp_plot = comps.dropna(subset=["lat", "lon"])
        fig.add_trace(go.Scattermapbox(
            lat=comp_plot["lat"].tolist(),
            lon=comp_plot["lon"].tolist(),
            mode="markers",
            marker=dict(size=9, color="#e74c3c"),
            name="Comparables",
            text=comp_plot.apply(
                lambda r: f"Blk {r['block']} {r['street_name']}<br>"
                          f"${r['resale_price']:,.0f} | {r['flat_type']} | "
                          f"{r['floor_area_sqm']:.0f} sqm",
                axis=1,
            ).tolist(),
            hoverinfo="text",
        ))
        if lat and lon:
            center = {"lat": lat, "lon": lon}
        else:
            center = {"lat": comp_plot["lat"].mean(), "lon": comp_plot["lon"].mean()}
        fig.update_layout(mapbox_center=center, mapbox_zoom=13.5)

    # ── Result card ───────────────────────────────────────────────────────────
    if est_value:
        verdict_text, verdict_color = valuation_verdict(
            float(listed_price) if listed_price else None, est_value)

        result_card = html.Div(
            [
                html.Div(
                    [
                        html.Small("Estimated Current Value:", className="fw-bold"),
                        html.H3(f"${est_value:,.0f}", className="mb-0"),
                        html.Small(f"Range: ${ci[0]:,.0f} – ${ci[1]:,.0f}",
                                   className="text-white-50"),
                    ],
                    className="bg-danger text-white rounded p-3 text-center mb-2",
                ),
                (
                    dbc.Alert(verdict_text, color=verdict_color, className="text-center small py-2")
                    if verdict_text else ""
                ),
            ]
        )
    else:
        result_card = ""

    # ── Comparables table ─────────────────────────────────────────────────────
    sort_asc = sort_col == "_score"  # smaller score = more similar
    comps_sorted = comps.sort_values(sort_col, ascending=sort_asc)

    cards = []
    for _, row in comps_sorted.head(10).iterrows():
        addr = f"Blk {row.get('block', '')} {row.get('street_name', '')}".strip()
        price_diff = ""
        if listed_price and est_value:
            diff = float(listed_price) - row["resale_price"]
            price_diff = html.Small(
                f" ({'+' if diff > 0 else ''}{diff:,.0f})",
                className="text-muted",
            )
        dist_badge = ""
        if "dist_km" in row and pd.notna(row["dist_km"]):
            dist_badge = dbc.Badge(f"{row['dist_km']:.2f} km", color="light",
                                   text_color="dark", className="me-1")

        cards.append(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div(
                            [html.Strong(addr),
                             html.Span(f"  ${row['resale_price']:,.0f}", className="text-success ms-2"),
                             price_diff],
                            className="mb-1",
                        ),
                        html.Div(
                            [
                                dist_badge,
                                html.Small(
                                    f"{row['flat_type']} | {row['floor_area_sqm']:.0f} sqm | "
                                    f"{row['month'].strftime('%b %Y') if pd.notna(row['month']) else ''}",
                                    className="text-muted",
                                ),
                            ]
                        ),
                        html.Ul(
                            [
                                html.Li(f"Ask price {'lower' if (listed_price or 0) < row['resale_price'] else 'higher'} "
                                        f"than this comparable",
                                        className="small text-muted"),
                            ],
                            className="mb-0 ps-3",
                        ),
                    ],
                    className="py-2 px-3",
                ),
                className="mb-2 shadow-sm",
                style={"fontSize": "0.82rem"},
            )
        )

    return fig, cards, result_card, comps.to_json(date_format="iso")
