"""
General Trends page — Singapore HDB choropleth + town drill-down.

Redesigned with The Architectural Ledger design system:
  - KPI summary cards using kpi-card CSS class
  - Flat type dropdown + metric selector
  - Interactive choropleth — click any town for price trend + flat-type breakdown
  - Town panel includes region/estate type metadata
  - Methodology note distinguishing median transaction price from personalised estimate
"""

import os
import json

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, callback

dash.register_page(__name__, path="/general-trends",
                   name="General Trends", title="Market Analysis")

from data_store import DF, FLAT_TYPES, YEAR_MIN, YEAR_MAX

# ── Load pre-built town GeoJSON ───────────────────────────────────────────────
_GJ_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "outputs", "town_choropleth.geojson"
)


def _load_geojson():
    if os.path.exists(_GJ_PATH):
        with open(_GJ_PATH) as f:
            return json.load(f)
    print("town_choropleth.geojson not found — scatter fallback will be used")
    return None


GJ = _load_geojson()

# Pre-extract CAGR data from GeoJSON properties
if GJ:
    DF_CAGR = pd.DataFrame([
        {
            "town_title": f["properties"]["town"],
            "town_upper": f["properties"]["town"].upper(),
            "cagr_1yr":   f["properties"].get("cagr_1yr_pct"),
            "cagr_3yr":   f["properties"].get("cagr_3yr_pct"),
            "cagr_5yr":   f["properties"].get("cagr_5yr_pct"),
        }
        for f in GJ["features"]
    ])
else:
    DF_CAGR = pd.DataFrame()

# ── Town centroids (scatter fallback) ────────────────────────────────────────
TOWN_CENTROIDS = {
    "ANG MO KIO":      (1.3691, 103.8454),
    "BEDOK":           (1.3236, 103.9273),
    "BISHAN":          (1.3526, 103.8352),
    "BUKIT BATOK":     (1.3490, 103.7495),
    "BUKIT MERAH":     (1.2819, 103.8239),
    "BUKIT PANJANG":   (1.3774, 103.7719),
    "BUKIT TIMAH":     (1.3294, 103.8021),
    "CENTRAL AREA":    (1.2894, 103.8497),
    "CHOA CHU KANG":   (1.3840, 103.7470),
    "CLEMENTI":        (1.3162, 103.7649),
    "GEYLANG":         (1.3201, 103.8918),
    "HOUGANG":         (1.3612, 103.8863),
    "JURONG EAST":     (1.3329, 103.7436),
    "JURONG WEST":     (1.3404, 103.7090),
    "KALLANG/WHAMPOA": (1.3100, 103.8650),
    "MARINE PARADE":   (1.3022, 103.9070),
    "PASIR RIS":       (1.3721, 103.9474),
    "PUNGGOL":         (1.4043, 103.9021),
    "QUEENSTOWN":      (1.2942, 103.7861),
    "SEMBAWANG":       (1.4491, 103.8185),
    "SENGKANG":        (1.3868, 103.8914),
    "SERANGOON":       (1.3554, 103.8679),
    "TAMPINES":        (1.3496, 103.9568),
    "TOA PAYOH":       (1.3343, 103.8563),
    "WOODLANDS":       (1.4382, 103.7890),
    "YISHUN":          (1.4304, 103.8354),
}

# ── Town metadata: region + estate type ──────────────────────────────────────
TOWN_META = {
    "ANG MO KIO":      ("North-East", "Mature Estate",     "Well-connected mature estate near Bishan-Ang Mo Kio Park"),
    "BEDOK":           ("East",       "Mature Estate",     "Established eastern estate with dense amenities and transport links"),
    "BISHAN":          ("Central",    "Mature Estate",     "Central location with premium access to city-fringe areas"),
    "BUKIT BATOK":     ("West",       "Mature Estate",     "Leafy estate with proximity to Bukit Timah Nature Reserve"),
    "BUKIT MERAH":     ("Central",    "Mature Estate",     "City-fringe location with direct access to the CBD"),
    "BUKIT PANJANG":   ("West",       "Non-Mature Estate", "Newer township served by Bukit Panjang LRT"),
    "BUKIT TIMAH":     ("Central",    "Mature Estate",     "Premium area adjacent to nature reserve, limited HDB supply"),
    "CENTRAL AREA":    ("Central",    "Mature Estate",     "Most central HDB flats, closest proximity to the CBD"),
    "CHOA CHU KANG":   ("West",       "Non-Mature Estate", "Western fringe town with Lot One mall and strong community facilities"),
    "CLEMENTI":        ("West",       "Mature Estate",     "Established western town near NUS and the Jurong Lake District"),
    "GEYLANG":         ("Central",    "Mature Estate",     "Dense urban area with excellent food culture and city connectivity"),
    "HOUGANG":         ("North-East", "Mature Estate",     "North-east heartland with great local amenities and Hougang Mall"),
    "JURONG EAST":     ("West",       "Mature Estate",     "Emerging regional hub adjacent to Jurong Lake District development"),
    "JURONG WEST":     ("West",       "Non-Mature Estate", "Largest HDB town by area with strong community infrastructure"),
    "KALLANG/WHAMPOA": ("Central",    "Mature Estate",     "Riverside estate near the Sports Hub and City Fringe"),
    "MARINE PARADE":   ("East",       "Mature Estate",     "Compact coastal estate with East Coast Park access"),
    "PASIR RIS":       ("East",       "Non-Mature Estate", "Coastal eastern town with beach parks and a resort atmosphere"),
    "PUNGGOL":         ("North-East", "Non-Mature Estate", "Modern eco-town with waterfront living and Punggol Digital District"),
    "QUEENSTOWN":      ("Central",    "Mature Estate",     "Singapore's first HDB satellite town, premium central location"),
    "SEMBAWANG":       ("North",      "Non-Mature Estate", "Northern town near Canberra MRT with growing amenities"),
    "SENGKANG":        ("North-East", "Non-Mature Estate", "Young family-oriented town with an extensive LRT network"),
    "SERANGOON":       ("North-East", "Mature Estate",     "Well-established estate with NEX mall and Little India proximity"),
    "TAMPINES":        ("East",       "Mature Estate",     "Self-contained eastern hub with malls, parks, and transport links"),
    "TOA PAYOH":       ("Central",    "Mature Estate",     "Historic heartland estate with a strong community identity"),
    "WOODLANDS":       ("North",      "Non-Mature Estate", "Largest northern town near Causeway Point and Johor Bahru"),
    "YISHUN":          ("North",      "Non-Mature Estate", "Northern town with Khoo Teck Puat Hospital and extensive parks"),
}

# ── Compute national KPIs once at startup ────────────────────────────────────
def _compute_kpis():
    df = DF.copy()
    df["year"] = df["year"].astype(int)
    latest = int(df["year"].max())
    prev   = latest - 1

    med_l = df[df["year"] == latest]["resale_price"].median()
    med_p = df[df["year"] == prev]["resale_price"].median()
    price_chg = (med_l - med_p) / med_p * 100 if med_p else 0.0

    vol_l = len(df[df["year"] == latest])
    vol_p = len(df[df["year"] == prev])

    tl = df[df["year"] == latest].groupby("town")["resale_price"].median()
    tp = df[df["year"] == prev].groupby("town")["resale_price"].median()
    common = tl.index.intersection(tp.index)
    if len(common):
        growth = (tl[common] - tp[common]) / tp[common] * 100
        best_town, best_pct = growth.idxmax(), growth.max()
    else:
        best_town, best_pct = "—", 0.0

    aff_town, aff_psqm = "—", 0.0
    if "floor_area_sqm" in df.columns:
        dl = df[df["year"] == latest].copy()
        dl["psqm"] = dl["resale_price"] / dl["floor_area_sqm"]
        grp = dl.groupby("town")["psqm"].median()
        aff_town  = grp.idxmin()
        aff_psqm  = grp.min()

    return dict(
        latest=latest, prev=prev,
        med_l=med_l, price_chg=price_chg,
        vol_l=vol_l, vol_chg=vol_l - vol_p,
        best_town=best_town, best_pct=best_pct,
        aff_town=aff_town, aff_psqm=aff_psqm,
    )


_KPI = _compute_kpis()


# ── KPI card helper ───────────────────────────────────────────────────────────
def _kpi_card(icon, title, value, delta_str, positive):
    delta_cls = "kpi-delta-pos" if positive else "kpi-delta-neg"
    arrow     = "▲" if positive else "▼"
    return dbc.Card(
        dbc.CardBody([
            html.I(className=f"bi {icon} text-accent",
                   style={"fontSize": "1.4rem"}),
            html.Div(title, className="kpi-label mt-2"),
            html.Div(value, className="kpi-value"),
            html.Span(f"{arrow} {delta_str}", className=delta_cls),
        ]),
        className="kpi-card h-100",
    )


# ── Dropdown options ──────────────────────────────────────────────────────────
_FT_OPTIONS = [{"label": "All Flat Types", "value": "ALL"}] + [
    {"label": ft.title(), "value": ft} for ft in FLAT_TYPES
]

_METRIC_OPTIONS = [
    {"label": "Median Transaction Price ($)",  "value": "median_price"},
    {"label": "Year-on-Year Price Growth (%)", "value": "growth"},
    {"label": "Price per SQM ($/sqm)",         "value": "psqm"},
    {"label": "Market Activity (no. of txns)", "value": "volume"},
]


# ── Placeholder town panel ────────────────────────────────────────────────────
def _placeholder_panel():
    return html.Div(
        [
            html.I(className="bi bi-geo-alt",
                   style={"fontSize": "2.5rem", "color": "#5bc8af", "opacity": "0.5"}),
            html.P(
                "Click any town on the map to explore its price history "
                "and flat-type breakdown.",
                className="mt-3 mb-0",
                style={"color": "#454652", "fontSize": "0.88rem", "maxWidth": "220px",
                       "textAlign": "center", "lineHeight": "1.6"},
            ),
        ],
        style={
            "display": "flex", "flexDirection": "column",
            "alignItems": "center", "justifyContent": "center",
            "minHeight": "490px", "padding": "2rem",
            "background": "#f4f2ff", "borderRadius": "12px",
        },
    )


# ── Layout ────────────────────────────────────────────────────────────────────
def layout():
    k = _KPI

    # ── Page header ───────────────────────────────────────────────────────────
    page_header = html.Div(
        [
            html.Div("Market Analysis", className="page-header-title"),
            html.Div(
                f"Browse price trends, growth rates and market activity across "
                f"all towns from {YEAR_MIN} to {YEAR_MAX}.",
                className="page-header-sub",
            ),
        ],
        className="mb-4",
    )

    # ── KPI row ───────────────────────────────────────────────────────────────
    kpi_row = dbc.Row([
        dbc.Col(_kpi_card(
            "bi-house-fill",
            f"National Median ({k['latest']})",
            f"${k['med_l']:,.0f}",
            f"{abs(k['price_chg']):.1f}% vs {k['prev']}",
            k["price_chg"] >= 0,
        ), xs=12, sm=6, lg=3, className="mb-3"),
        dbc.Col(_kpi_card(
            "bi-arrow-repeat",
            f"Total Transactions ({k['latest']})",
            f"{k['vol_l']:,}",
            f"{abs(k['vol_chg']):,} vs {k['prev']}",
            k["vol_chg"] >= 0,
        ), xs=12, sm=6, lg=3, className="mb-3"),
        dbc.Col(_kpi_card(
            "bi-graph-up-arrow",
            "Fastest Growing Town",
            k["best_town"].title() if k["best_town"] != "—" else "—",
            f"+{k['best_pct']:.1f}% YoY median price",
            True,
        ), xs=12, sm=6, lg=3, className="mb-3"),
        dbc.Col(_kpi_card(
            "bi-tag-fill",
            "Best Value Town ($/sqm)",
            k["aff_town"].title() if k["aff_town"] != "—" else "—",
            f"${k['aff_psqm']:,.0f}/sqm" if k["aff_town"] != "—" else "n/a",
            True,
        ), xs=12, sm=6, lg=3, className="mb-3"),
    ], className="g-3 mb-3")

    # ── Filter controls ───────────────────────────────────────────────────────
    controls = dbc.Card(
        dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.Label("Flat Type", className="kpi-label mb-1"),
                    dcc.Dropdown(
                        id="gt-flat-type", options=_FT_OPTIONS,
                        value="ALL", clearable=False,
                        style={"fontSize": "0.88rem"},
                    ),
                ], xs=12, md=3),
                dbc.Col([
                    html.Label("Map Metric", className="kpi-label mb-1"),
                    dcc.Dropdown(
                        id="gt-metric", options=_METRIC_OPTIONS,
                        value="median_price", clearable=False,
                        style={"fontSize": "0.88rem"},
                    ),
                ], xs=12, md=4),
                dbc.Col([
                    html.Label(id="gt-year-label", className="kpi-label mb-1"),
                    dcc.Slider(
                        id="gt-year",
                        min=YEAR_MIN, max=YEAR_MAX, step=1, value=YEAR_MAX,
                        marks={y: str(y) for y in range(YEAR_MIN, YEAR_MAX + 1, 2)},
                        tooltip={"placement": "bottom", "always_visible": False},
                    ),
                ], xs=12, md=5,
                   className="d-flex flex-column justify-content-end"),
            ], className="g-3 align-items-end"),
        ),
        className="controls-panel mb-3",
    )

    # ── Map + town drill-down ─────────────────────────────────────────────────
    map_section = dbc.Row([
        dbc.Col([
            dcc.Graph(
                id="gt-map",
                config={"scrollZoom": True, "displayModeBar": False},
                style={"height": "490px", "borderRadius": "12px"},
            ),
            html.P(
                "💡 Click any town on the map to see its detailed price trend →",
                className="text-center mt-2 mb-0",
                style={"fontSize": "0.72rem", "color": "#454652"},
            ),
        ], xs=12, lg=7),
        dbc.Col([
            html.Div(id="gt-town-detail", children=_placeholder_panel()),
        ], xs=12, lg=5),
    ], className="g-3 mb-3")

    # ── Methodology note ──────────────────────────────────────────────────────
    distinction = dbc.Card(
        dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Badge("Market Benchmark", color="primary", className="me-2"),
                        html.Strong("Median Transaction Price  (this page)",
                                    style={"fontSize": "0.85rem"}),
                    ], className="mb-1"),
                    html.P(
                        "The map and KPIs show the median price among ALL completed HDB "
                        "resale transactions registered in that town and year — regardless "
                        "of floor level, remaining lease, or exact flat size. "
                        "Use this to understand broad market direction and compare towns.",
                        className="mb-0",
                        style={"fontSize": "0.82rem", "color": "#454652"},
                    ),
                ], md=6, className="mb-3 mb-md-0"),
                dbc.Col(md=1, className="d-none d-md-flex"),
                dbc.Col([
                    html.Div([
                        dbc.Badge("Personalised Estimate", color="dark", className="me-2"),
                        html.Strong("Estimated Current Value  (Flat Valuation tab)",
                                    style={"fontSize": "0.85rem"}),
                    ], className="mb-1"),
                    html.P([
                        "The valuation tool computes a price estimate tailored to your "
                        "specific flat — matching on flat type, floor level, size and "
                        "remaining lease within 1.5 km, over the past 24 months. ",
                        html.A("→ Try Flat Valuation", href="/flat-valuation",
                               style={"color": "#00145d", "fontWeight": "600"}),
                    ], className="mb-0",
                       style={"fontSize": "0.82rem", "color": "#454652"}),
                ], md=5),
            ]),
        ),
        className="methodology-card",
    )

    return html.Div([
        page_header,
        kpi_row,
        controls,
        map_section,
        distinction,
    ], className="container-fluid px-3 py-3",
       style={"backgroundColor": "#fbf8ff", "minHeight": "calc(100vh - 64px)"})


# ── Callbacks ─────────────────────────────────────────────────────────────────

@callback(
    Output("gt-map",        "figure"),
    Output("gt-year-label", "children"),
    Input("gt-flat-type",   "value"),
    Input("gt-metric",      "value"),
    Input("gt-year",        "value"),
)
def update_map(flat_type, metric, year):
    year = int(year)
    df = DF.copy()
    df["year"] = df["year"].astype(int)

    if flat_type and flat_type != "ALL":
        df = df[df["flat_type"] == flat_type]

    df_yr = df[df["year"] == year]
    df_pv = df[df["year"] == year - 1]

    if df_yr.empty:
        fig = go.Figure()
        fig.update_layout(title=f"No data for {year}")
        return fig, f"Year: {year}"

    agg = df_yr.groupby("town").agg(
        median_price=("resale_price", "median"),
        volume=("resale_price", "count"),
    ).reset_index()

    if "floor_area_sqm" in df.columns:
        tmp = df_yr.copy()
        tmp["psqm"] = tmp["resale_price"] / tmp["floor_area_sqm"]
        p = tmp.groupby("town")["psqm"].median().reset_index()
        agg = agg.merge(p, on="town", how="left")
    else:
        agg["psqm"] = np.nan

    prev_med = (
        df_pv.groupby("town")["resale_price"].median()
        .reset_index().rename(columns={"resale_price": "prev_price"})
    )
    agg = agg.merge(prev_med, on="town", how="left")
    agg["growth"] = (
        (agg["median_price"] - agg["prev_price"])
        / agg["prev_price"].replace(0, np.nan) * 100
    ).round(1)

    MCONF = {
        "median_price": (
            "Median Price ($)", "Blues",
            [agg["median_price"].quantile(0.05), agg["median_price"].quantile(0.95)],
        ),
        "growth": ("YoY Growth (%)", "RdYlGn", [-10, 10]),
        "psqm": (
            "Price/SQM ($/sqm)", "Oranges",
            [agg["psqm"].quantile(0.05) if agg["psqm"].notna().any() else 0,
             agg["psqm"].quantile(0.95) if agg["psqm"].notna().any() else 1],
        ),
        "volume": ("Transactions", "Purples", [0, int(agg["volume"].max())]),
    }
    clabel, cscale, rng = MCONF[metric]

    def _hover(r):
        lines = [
            f"<b>{r['town'].title()}</b>",
            f"Median: ${r['median_price']:,.0f}",
            f"YoY: {r['growth']:+.1f}%",
            f"Transactions: {r['volume']:,}",
        ]
        if pd.notna(r.get("psqm", np.nan)):
            lines.append(f"Price/sqm: ${r['psqm']:,.0f}")
        return "<br>".join(lines)

    agg["hover_txt"] = agg.apply(_hover, axis=1)
    year_label = f"Year: {year}"

    if GJ is not None:
        agg["town_title"] = agg["town"].str.title()

        if metric == "growth" and not DF_CAGR.empty:
            agg = agg.merge(
                DF_CAGR[["town_title", "cagr_1yr"]], on="town_title", how="left"
            )
            agg["growth"] = agg["cagr_1yr"].round(1)

        try:
            fig = px.choropleth_mapbox(
                agg,
                geojson=GJ,
                locations="town_title",
                featureidkey="properties.town",
                color=metric,
                color_continuous_scale=cscale,
                range_color=rng,
                mapbox_style="carto-positron",
                center={"lat": 1.3521, "lon": 103.8198},
                zoom=10.5,
                opacity=0.75,
                custom_data=["hover_txt", "town_title"],
                labels={metric: clabel},
            )
            fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
        except Exception as e:
            print(f"Choropleth error ({e}), falling back to scatter")
            fig = _scatter_map(agg, metric, clabel, cscale, rng)
    else:
        fig = _scatter_map(agg, metric, clabel, cscale, rng)

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar=dict(
            title=clabel, thickness=12, len=0.65, title_font_size=11,
        ),
        paper_bgcolor="#fbf8ff",
    )
    return fig, year_label


# ── Town drill-down panel ─────────────────────────────────────────────────────
@callback(
    Output("gt-town-detail", "children"),
    Input("gt-map",       "clickData"),
    Input("gt-flat-type", "value"),
)
def update_town_detail(clickData, flat_type):
    if not clickData:
        return _placeholder_panel()

    try:
        pts = clickData["points"][0]
        cd = pts.get("customdata") or []
        town_raw = (
            pts.get("location")
            or (cd[1] if len(cd) > 1 else None)
            or pts.get("hovertext", "")
        )
        town = str(town_raw).upper().strip()
    except Exception:
        return _placeholder_panel()

    if not town:
        return _placeholder_panel()

    df = DF.copy()
    df["year"] = df["year"].astype(int)
    df_town = df[df["town"] == town]

    if df_town.empty:
        match = next((t for t in df["town"].unique() if town[:6] in t), None)
        if match:
            df_town = df[df["town"] == match]
            town = match
        else:
            return _placeholder_panel()

    latest = int(df["year"].max())

    if flat_type and flat_type != "ALL":
        df_fl = df_town[df_town["flat_type"] == flat_type]
        types_to_plot = [flat_type] if not df_fl.empty else []
    else:
        types_to_plot = df_town["flat_type"].value_counts().head(4).index.tolist()

    df_l = df_town[df_town["year"] == latest]
    df_p = df_town[df_town["year"] == latest - 1]
    med_l = df_l["resale_price"].median()
    med_p = df_p["resale_price"].median()
    chg   = (med_l - med_p) / med_p * 100 if med_p else 0.0
    vol   = len(df_l)

    chg_color = "#27ae60" if chg >= 0 else "#e74c3c"
    chg_arrow = "▲" if chg >= 0 else "▼"

    # Region + estate type metadata
    region, estate_type, note = TOWN_META.get(town, ("—", "—", ""))

    # ── Trend chart ───────────────────────────────────────────────────────────
    COLORS = ["#0f2885", "#5bc8af", "#e67e22", "#8e44ad"]
    fig = go.Figure()
    for i, ft in enumerate(types_to_plot):
        sub = (
            df_town[df_town["flat_type"] == ft]
            .groupby("year")["resale_price"].median()
            .reset_index().sort_values("year")
        )
        fig.add_trace(go.Scatter(
            x=sub["year"], y=sub["resale_price"],
            mode="lines+markers",
            name=ft.title(),
            line=dict(color=COLORS[i % 4], width=2.5),
            marker=dict(size=5),
            hovertemplate="<b>%{fullData.name}</b><br>%{x}: $%{y:,.0f}<extra></extra>",
        ))

    fig.update_layout(
        plot_bgcolor="#fbf8ff", paper_bgcolor="#fbf8ff",
        margin=dict(t=10, b=30, l=55, r=10), height=210,
        xaxis=dict(tickformat="d", showgrid=True, gridcolor="#e5e6ff", title=""),
        yaxis=dict(tickprefix="$", tickformat=",", showgrid=True,
                   gridcolor="#e5e6ff", title=""),
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    xanchor="right", x=1, font=dict(size=9)),
        font=dict(size=10, family="Inter, sans-serif"),
    )

    # ── Flat-type price breakdown ─────────────────────────────────────────────
    ft_med  = df_l.groupby("flat_type")["resale_price"].median().sort_index()
    prev_ft = df_p.groupby("flat_type")["resale_price"].median()

    breakdown_rows = []
    for ft, p in ft_med.items():
        if pd.isna(p):
            continue
        pp = prev_ft.get(ft, np.nan)
        if not pd.isna(pp) and pp > 0:
            ft_chg = (p - pp) / pp * 100
            chg_el = html.Span(
                f"{'▲' if ft_chg >= 0 else '▼'}{abs(ft_chg):.1f}%",
                style={"color": "#27ae60" if ft_chg >= 0 else "#e74c3c",
                       "fontSize": "0.68rem", "fontWeight": "600"},
            )
        else:
            chg_el = html.Span("—", style={"fontSize": "0.68rem", "color": "#454652"})

        breakdown_rows.append(
            dbc.Row([
                dbc.Col(html.Span(ft.title(), style={"fontSize": "0.78rem"}), width=5),
                dbc.Col(html.Span(f"${p:,.0f}", className="fw-semibold",
                                  style={"fontSize": "0.78rem"}), width=4),
                dbc.Col(chg_el, width=3, className="text-end"),
            ], className="py-2 align-items-center",
               style={"borderBottom": "1px solid rgba(197,197,212,0.18)"})
        )

    return html.Div(
        [
            # Town name + badges
            html.Div(
                html.H5(town.title(), className="fw-bold mb-1",
                        style={"fontFamily": "'Manrope', sans-serif",
                               "color": "#08154d", "letterSpacing": "-0.01em"}),
            ),
            html.Div(
                [
                    html.Span(region, className="town-badge-region"),
                    html.Span(estate_type, className="town-badge-type"),
                ],
                className="mb-3",
            ),

            # Mini stat row
            dbc.Row([
                dbc.Col([
                    html.Div("Median Price", className="kpi-label"),
                    html.Div(f"${med_l:,.0f}",
                             style={"fontFamily": "'Manrope', sans-serif",
                                    "fontSize": "1.6rem", "fontWeight": "800",
                                    "color": "#08154d", "letterSpacing": "-0.02em",
                                    "lineHeight": "1.1"}),
                    html.Span(
                        f"{chg_arrow} {abs(chg):.1f}% vs {latest - 1}",
                        style={"color": chg_color, "fontSize": "0.74rem", "fontWeight": "600"},
                    ),
                ], width=7),
                dbc.Col([
                    html.Div(f"Txns ({latest})", className="kpi-label"),
                    html.Div(f"{vol:,}",
                             style={"fontFamily": "'Manrope', sans-serif",
                                    "fontSize": "1.6rem", "fontWeight": "800",
                                    "color": "#08154d", "letterSpacing": "-0.02em",
                                    "lineHeight": "1.1"}),
                ], width=5),
            ], className="mb-3"),

            # Town note
            html.P(note, style={"fontSize": "0.78rem", "color": "#454652",
                                 "lineHeight": "1.5", "marginBottom": "1rem"}),

            # Trend chart
            html.Div("Median price trend by flat type", className="kpi-label mb-1"),
            dcc.Graph(figure=fig, config={"displayModeBar": False},
                      style={"height": "210px"}),

            # Flat-type breakdown
            html.Div(f"Median price by flat type ({latest})", className="kpi-label mt-3 mb-1"),
            dbc.Row([
                dbc.Col(html.Span("Type", style={"fontSize": "0.68rem", "color": "#454652"}), width=5),
                dbc.Col(html.Span("Median", style={"fontSize": "0.68rem", "color": "#454652"}), width=4),
                dbc.Col(html.Span("YoY", style={"fontSize": "0.68rem", "color": "#454652"}), width=3,
                        className="text-end"),
            ], className="pb-1",
               style={"borderBottom": "1px solid rgba(197,197,212,0.35)"}),
            html.Div(
                breakdown_rows or [
                    html.P("No data for selected flat type.",
                           style={"fontSize": "0.82rem", "color": "#454652", "marginTop": "0.5rem"})
                ]
            ),

            # CTA
            dbc.Button(
                "Value a Flat in This Area →",
                href="/flat-valuation",
                className="btn-cta w-100 mt-3",
                style={"fontSize": "0.82rem"},
            ),
        ],
        style={
            "background": "#f4f2ff", "borderRadius": "12px",
            "padding": "1.5rem", "minHeight": "490px",
        },
    )


# ── Scatter map fallback ──────────────────────────────────────────────────────
def _scatter_map(agg, metric, label, cscale, rng):
    if "lat" not in agg.columns:
        agg = agg.copy()
        agg["lat"] = agg["town"].map(
            lambda t: TOWN_CENTROIDS.get(t, (1.35, 103.82))[0])
        agg["lon"] = agg["town"].map(
            lambda t: TOWN_CENTROIDS.get(t, (1.35, 103.82))[1])
        agg["town_title"] = agg["town"].str.title()

    fig = px.scatter_mapbox(
        agg.dropna(subset=["lat", "lon"]),
        lat="lat", lon="lon",
        color=metric, size="volume",
        hover_name="town",
        color_continuous_scale=cscale, range_color=rng,
        mapbox_style="carto-positron",
        center={"lat": 1.3521, "lon": 103.8198},
        zoom=10.5, size_max=35, opacity=0.8,
        custom_data=["hover_txt", "town_title"],
        labels={metric: label},
    )
    fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
    return fig
