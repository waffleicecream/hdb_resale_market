"""
User Guide page — explains the two main tools and how to use the dashboard.
"""
import dash
import dash_bootstrap_components as dbc
from dash import html

dash.register_page(__name__, path="/", name="User Guide", title="PropertyMinBrothers")

# ── Layout helpers ────────────────────────────────────────────────────────────
def _card(icon, title, description, href, btn_label):
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(html.I(className=f"bi {icon} fs-1 text-success"), className="mb-3"),
                html.H5(title, className="fw-bold"),
                html.P(description, className="text-muted", style={"minHeight": "70px"}),
                dbc.Button(btn_label, href=href, color="success", outline=True, size="sm"),
            ]
        ),
        className="h-100 shadow-sm text-center p-3",
    )


layout = html.Div(
    [
        # ── Hero ──────────────────────────────────────────────────────────────
        html.Div(
            [
                html.H1(
                    [html.Span("PROPERTY", style={"color": "#2b2b2b"}),
                     html.Span("MIN", style={"color": "#27ae60"}),
                     html.Span("BROTHERS", style={"color": "#2b2b2b"})],
                    className="display-5 fw-bold mb-2",
                    style={"fontFamily": "'Georgia', serif"},
                ),
                html.P(
                    "Your data-driven companion for navigating Singapore's HDB resale market.",
                    className="lead text-muted mb-4",
                ),
                dbc.Badge("Powered by HDB transaction data 2018 – present",
                          color="success", className="me-2"),
                dbc.Badge("Updated quarterly", color="secondary"),
            ],
            className="text-center py-5 px-3",
        ),

        html.Hr(),

        # ── Tool cards ────────────────────────────────────────────────────────
        html.H4("What can you do here?", className="fw-bold mb-4 text-center"),
        dbc.Row(
            [
                dbc.Col(
                    _card(
                        icon="bi-map-fill",
                        title="General Trends",
                        description=(
                            "Explore how HDB resale prices and growth have changed across "
                            "Singapore's towns over the years. Filter by flat type and drag "
                            "the year slider to animate the map."
                        ),
                        href="/general-trends",
                        btn_label="Open Map →",
                    ),
                    md=4,
                ),
                dbc.Col(
                    _card(
                        icon="bi-calculator-fill",
                        title="Flat Valuation",
                        description=(
                            "Enter a flat's details — postal code, flat type, size, "
                            "floor level, and remaining lease — to get an estimated market "
                            "value and a ranked list of the most comparable recent transactions."
                        ),
                        href="/flat-valuation",
                        btn_label="Value a Flat →",
                    ),
                    md=4,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div(html.I(className="bi bi-info-circle-fill fs-1 text-info"),
                                         className="mb-3"),
                                html.H5("Data Sources", className="fw-bold"),
                                html.P(
                                    "Transactions sourced from HDB's open data portal. "
                                    "Amenity distances computed via OneMap API. "
                                    "Macro variables from MAS SORA and CPI data.",
                                    className="text-muted", style={"minHeight": "70px"},
                                ),
                                dbc.Button("HDB Open Data", color="info", outline=True, size="sm",
                                           href="https://data.gov.sg", target="_blank"),
                            ]
                        ),
                        className="h-100 shadow-sm text-center p-3",
                    ),
                    md=4,
                ),
            ],
            className="g-4 mb-5",
        ),

        html.Hr(),

        # ── Decision flow diagram ─────────────────────────────────────────────
        html.H4("How to use this tool", className="fw-bold mb-3"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Alert(
                            [
                                html.H6("🗺️  I'm unsure where to start", className="fw-bold"),
                                html.P(
                                    "Open General Trends → explore the choropleth map → "
                                    "toggle Growth vs Average Price → "
                                    "shortlist promising towns.",
                                    className="mb-0 small",
                                ),
                            ],
                            color="success",
                        ),
                        dbc.Alert(
                            [
                                html.H6("🏠  I have shortlisted listings", className="fw-bold"),
                                html.P(
                                    "Open Flat Valuation → enter the postal code and flat details → "
                                    "compare the asking price against the model estimate and "
                                    "recent comparable transactions.",
                                    className="mb-0 small",
                                ),
                            ],
                            color="primary",
                        ),
                    ],
                    md=8,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Legend", className="fw-bold"),
                                html.Div([html.Span("■ ", style={"color": "#27ae60"}),
                                          " High growth / above-average price"], className="small"),
                                html.Div([html.Span("■ ", style={"color": "#aed6f1"}),
                                          " Low growth / below-average price"], className="small"),
                                html.Hr(className="my-2"),
                                html.Div("✅  Fair value   ≈ ±5% of estimate", className="small"),
                                html.Div("🔴  Overvalued   > +5% above estimate", className="small"),
                                html.Div("🟢  Undervalued  > −5% below estimate", className="small"),
                            ]
                        ),
                        className="shadow-sm",
                    ),
                    md=4,
                ),
            ],
            className="mb-4",
        ),
    ],
    className="container py-4",
    style={"maxWidth": "960px"},
)
