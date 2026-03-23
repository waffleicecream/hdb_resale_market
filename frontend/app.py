"""
PropertyMinBrothers — HDB Resale Dashboard
==========================================
Multi-page Dash app:
  - User Guide       (/)
  - General Trends   (/general-trends)
  - Flat Valuation   (/flat-valuation)
  - Amenities        (/amenities-comparison)

Run:
    cd frontend
    python app.py
Then open http://127.0.0.1:8050 in your browser.
"""

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from data_store import DF, FLAT_TYPES, TOWNS, YEAR_MIN, YEAR_MAX

# ── App init ──────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.FLATLY,
        dbc.icons.BOOTSTRAP,
        # Google Fonts — loaded before style.css to avoid FOUT
        "https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap",
    ],
    suppress_callback_exceptions=True,
    title="PropertyMinBrothers",
)
server = app.server   # expose for gunicorn / Render

# ── Navbar ────────────────────────────────────────────────────────────────────
navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.NavbarBrand(
                html.Div(
                    [
                        html.Span("PropertyMinBrothers", className="navbar-brand-title"),
                        html.Span("买房子 · 卖房子 · 找我们", className="navbar-brand-tagline"),
                    ],
                    className="navbar-brand-block",
                ),
                href="/",
                style={"textDecoration": "none"},
            ),
            dbc.Nav(
                [
                    dbc.NavItem(dbc.NavLink(
                        "User Guide", href="/", active="exact",
                        className="nav-link-custom")),
                    dbc.NavItem(dbc.NavLink(
                        "Market Analysis", href="/general-trends", active="exact",
                        className="nav-link-custom")),
                    dbc.NavItem(dbc.NavLink(
                        "Flat Valuation", href="/flat-valuation", active="exact",
                        className="nav-link-custom")),
                    dbc.NavItem(dbc.NavLink(
                        "Amenities", href="/amenities-comparison", active="exact",
                        className="nav-link-custom")),
                ],
                navbar=True,
                className="ms-auto",
            ),
        ],
        fluid=True,
    ),
    # color= sets an inline background-color; this wins over CSS bg rules
    color="#00145d",
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
        dcc.Store(id="store-year-range", data={"min": YEAR_MIN, "max": YEAR_MAX}),
        dash.page_container,
    ]
)

if __name__ == "__main__":
    app.run(debug=True, port=8050)
