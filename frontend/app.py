"""
PropertyMinBrothers — HDB Resale Dashboard
==========================================
Multi-page Dash app matching the mockup:
  - User Guide
  - General Trends  (choropleth overview)
  - Flat Valuation  (comparables + predicted price)

Run:
    cd frontend
    python app.py
Then open http://127.0.0.1:8050 in your browser.
"""

import os
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output

# ── Data loading (shared via data_store) ──────────────────────────────────────
from data_store import DF, FLAT_TYPES, TOWNS, YEAR_MIN, YEAR_MAX

# ── App init ──────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="PropertyMinBrothers",
)
server = app.server   # expose for gunicorn / Render

# ── Navbar ────────────────────────────────────────────────────────────────────
NAV_BRAND_STYLE = {
    "fontFamily": "'Georgia', serif",
    "fontWeight": "700",
    "fontSize": "1.15rem",
    "letterSpacing": "0.04em",
    "color": "#ffffff",
}

navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.NavbarBrand(
                [html.Span("PROPERTY", style={"color": "#ffffff"}),
                 html.Span("MIN", style={"color": "#5bc8af"}),
                 html.Span("BROTHERS", style={"color": "#ffffff"})],
                style=NAV_BRAND_STYLE,
                href="/",
            ),
            dbc.Nav(
                [
                    dbc.NavItem(dbc.NavLink("USER GUIDE",      href="/",               active="exact",
                                            className="nav-link-custom")),
                    dbc.NavItem(dbc.NavLink("GENERAL TRENDS",  href="/general-trends",  active="exact",
                                            className="nav-link-custom")),
                    dbc.NavItem(dbc.NavLink("FLAT VALUATION",  href="/flat-valuation",  active="exact",
                                            className="nav-link-custom")),
                ],
                navbar=True,
                className="ms-auto",
            ),
        ],
        fluid=True,
    ),
    color="#2b2b2b",
    dark=True,
    sticky="top",
    className="mb-0 py-2",
)

# ── Layout ────────────────────────────────────────────────────────────────────
app.layout = html.Div(
    [
        dcc.Location(id="url"),
        navbar,
        dcc.Store(id="store-flat-type", data=FLAT_TYPES),
        dcc.Store(id="store-towns",     data=TOWNS),
        dcc.Store(id="store-year-range",data={"min": YEAR_MIN, "max": YEAR_MAX}),
        dash.page_container,
    ]
)

if __name__ == "__main__":
    app.run(debug=True, port=8050)
