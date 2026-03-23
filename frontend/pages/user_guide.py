"""
User Guide / Landing page — premium editorial design.
Full-bleed hero + national stats band + feature cards + how-to steps + footer.
"""
import dash
import dash_bootstrap_components as dbc
from dash import html

from data_store import DF, YEAR_MAX

dash.register_page(__name__, path="/", name="User Guide", title="PropertyMinBrothers")


# ── Compute national KPIs once at module load ─────────────────────────────────
def _get_national_kpis():
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
        best_town = growth.idxmax().title()
        best_pct  = growth.max()
    else:
        best_town, best_pct = "—", 0.0

    aff_town, aff_psqm = "—", 0.0
    if "floor_area_sqm" in df.columns:
        dl = df[df["year"] == latest].copy()
        dl["psqm"] = dl["resale_price"] / dl["floor_area_sqm"]
        grp = dl.groupby("town")["psqm"].median()
        aff_town = grp.idxmin().title()
        aff_psqm = grp.min()

    return dict(
        latest=latest, med_l=med_l, price_chg=price_chg,
        vol_l=vol_l, vol_chg=vol_l - vol_p,
        best_town=best_town, best_pct=best_pct,
        aff_town=aff_town, aff_psqm=aff_psqm,
    )


_K = _get_national_kpis()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _stat_col(value, label, delta=None):
    children = [
        html.Div(value, className="stat-item-value"),
        html.Div(label, className="stat-item-label"),
    ]
    if delta:
        children.append(html.Div(delta, className="stat-item-delta"))
    return dbc.Col(
        html.Div(children, className="text-center py-2"),
        xs=6, md=3,
    )


def _feature_card(icon, title, desc, href, btn_text, alt=False):
    cls = "feature-card-alt" if alt else "feature-card"
    return html.Div(
        [
            html.Div(html.I(className=f"bi {icon}"), className="feature-icon"),
            html.Div(title, className="feature-title"),
            html.Div(desc,  className="feature-desc"),
            dbc.Button(
                btn_text, href=href,
                className="btn-cta",
                style={"fontSize": "0.82rem", "padding": "0.5rem 1.2rem"},
            ),
        ],
        className=cls,
    )


def _step_card(number, title, desc):
    return html.Div(
        [
            html.Div(number, className="step-number"),
            html.Div(
                [
                    html.Span(
                        f"Step {number}",
                        style={
                            "fontSize": "0.64rem", "fontWeight": "700",
                            "textTransform": "uppercase", "letterSpacing": "0.08em",
                            "color": "#5bc8af", "marginBottom": "0.5rem",
                            "display": "block",
                        },
                    ),
                    html.Div(title, className="step-title"),
                    html.Div(desc,  className="step-desc"),
                ],
                style={"position": "relative", "zIndex": "1"},
            ),
        ],
        className="step-card",
    )


# ── Layout ────────────────────────────────────────────────────────────────────
layout = html.Div(
    [
        # ── Hero (full-bleed) ─────────────────────────────────────────────────
        html.Div(
            dbc.Container(
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                # Eyebrow
                                html.Div(
                                    [
                                        html.Span(className="hero-eyebrow-dot"),
                                        html.Span(
                                            "Singapore HDB Resale Intelligence",
                                            className="hero-eyebrow-text",
                                        ),
                                    ],
                                    className="hero-eyebrow",
                                ),

                                # Headline
                                html.H1(
                                    "Make Your Next Property Decision With Confidence",
                                    className="hero-headline",
                                ),

                                # Sub-headline
                                html.P(
                                    "Data-driven insights on Singapore's HDB resale market — "
                                    "valuations, market trends, and amenity comparisons "
                                    "for informed buyers.",
                                    className="hero-sub",
                                ),

                                # CTAs
                                html.Div(
                                    [
                                        dbc.Button(
                                            "Explore Market →",
                                            href="/general-trends",
                                            className="btn-hero-primary me-3 mb-2",
                                        ),
                                        dbc.Button(
                                            "Value a Flat",
                                            href="/flat-valuation",
                                            className="btn-hero-ghost mb-2",
                                        ),
                                    ],
                                    className="d-flex flex-wrap align-items-center",
                                ),

                                # Trust line
                                html.P(
                                    f"Powered by HDB Open Data  ·  "
                                    f"{len(DF):,} transactions  ·  "
                                    f"Jan 2017 – present",
                                    className="hero-trust",
                                ),
                            ],
                            md=8, lg=7,
                        ),

                        # Decorative right panel
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                "National Median Price",
                                                style={
                                                    "fontSize": "0.65rem", "fontWeight": "700",
                                                    "textTransform": "uppercase",
                                                    "letterSpacing": "0.08em",
                                                    "color": "rgba(255,255,255,0.55)",
                                                    "marginBottom": "0.4rem",
                                                },
                                            ),
                                            html.Div(
                                                f"${_K['med_l']:,.0f}",
                                                style={
                                                    "fontFamily": "'Manrope', sans-serif",
                                                    "fontSize": "2.8rem", "fontWeight": "800",
                                                    "color": "#ffffff",
                                                    "letterSpacing": "-0.03em",
                                                    "lineHeight": "1.1",
                                                },
                                            ),
                                            html.Div(
                                                f"{'▲' if _K['price_chg'] >= 0 else '▼'} "
                                                f"{abs(_K['price_chg']):.1f}% vs {_K['latest'] - 1}",
                                                style={
                                                    "fontSize": "0.82rem", "fontWeight": "600",
                                                    "color": "#5bc8af" if _K['price_chg'] >= 0
                                                             else "#ff6b6b",
                                                    "marginTop": "0.4rem",
                                                },
                                            ),
                                        ],
                                        style={
                                            "background": "rgba(255,255,255,0.07)",
                                            "borderRadius": "12px",
                                            "padding": "1.5rem 2rem",
                                            "backdropFilter": "blur(10px)",
                                            "marginBottom": "1rem",
                                        },
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                html.Div(
                                                    [
                                                        html.Div(
                                                            str(_K["latest"]),
                                                            style={
                                                                "fontFamily": "'Manrope', sans-serif",
                                                                "fontSize": "1.4rem",
                                                                "fontWeight": "800",
                                                                "color": "#ffffff",
                                                                "letterSpacing": "-0.02em",
                                                            },
                                                        ),
                                                        html.Div(
                                                            "Latest Year",
                                                            style={
                                                                "fontSize": "0.64rem",
                                                                "color": "rgba(255,255,255,0.50)",
                                                                "fontWeight": "600",
                                                                "textTransform": "uppercase",
                                                                "letterSpacing": "0.07em",
                                                            },
                                                        ),
                                                    ],
                                                    style={
                                                        "background": "rgba(255,255,255,0.07)",
                                                        "borderRadius": "10px",
                                                        "padding": "1rem 1.25rem",
                                                    },
                                                ),
                                            ),
                                            dbc.Col(
                                                html.Div(
                                                    [
                                                        html.Div(
                                                            f"{_K['vol_l']:,}",
                                                            style={
                                                                "fontFamily": "'Manrope', sans-serif",
                                                                "fontSize": "1.4rem",
                                                                "fontWeight": "800",
                                                                "color": "#ffffff",
                                                                "letterSpacing": "-0.02em",
                                                            },
                                                        ),
                                                        html.Div(
                                                            f"Txns {_K['latest']}",
                                                            style={
                                                                "fontSize": "0.64rem",
                                                                "color": "rgba(255,255,255,0.50)",
                                                                "fontWeight": "600",
                                                                "textTransform": "uppercase",
                                                                "letterSpacing": "0.07em",
                                                            },
                                                        ),
                                                    ],
                                                    style={
                                                        "background": "rgba(255,255,255,0.07)",
                                                        "borderRadius": "10px",
                                                        "padding": "1rem 1.25rem",
                                                    },
                                                ),
                                            ),
                                        ],
                                        className="g-2",
                                    ),
                                ],
                            ),
                            md=4, lg=5,
                            className="d-none d-md-block",
                        ),
                    ],
                    className="align-items-center",
                ),
                fluid=True,
                className="px-4",
            ),
            className="hero-section",
        ),

        # ── Stats band ────────────────────────────────────────────────────────
        html.Div(
            dbc.Container(
                dbc.Row(
                    [
                        _stat_col(
                            f"${_K['med_l']:,.0f}",
                            f"National Median ({_K['latest']})",
                            f"{'▲' if _K['price_chg'] >= 0 else '▼'} {abs(_K['price_chg']):.1f}% YoY",
                        ),
                        _stat_col(
                            f"{_K['vol_l']:,}",
                            f"Transactions ({_K['latest']})",
                            f"{'▲' if _K['vol_chg'] >= 0 else '▼'} {abs(_K['vol_chg']):,} vs prior year",
                        ),
                        _stat_col(
                            _K["best_town"],
                            "Fastest Growing Town",
                            f"+{_K['best_pct']:.1f}% YoY" if _K["best_town"] != "—" else None,
                        ),
                        _stat_col(
                            _K["aff_town"],
                            "Best Value ($/sqm)",
                            f"${_K['aff_psqm']:,.0f}/sqm" if _K["aff_town"] != "—" else None,
                        ),
                    ],
                    className="g-2 align-items-center",
                ),
                fluid=True,
                className="px-4",
            ),
            className="stats-band",
        ),

        # ── Feature cards section ─────────────────────────────────────────────
        html.Div(
            dbc.Container(
                [
                    html.Div(
                        [
                            html.Div("Tools", className="section-eyebrow text-center"),
                            html.H2("Three Tools, One Platform", className="section-title text-center mb-2"),
                            html.P(
                                "Everything you need to research, compare, and value Singapore HDB flats.",
                                className="text-center mb-5",
                                style={"color": "#454652", "fontSize": "0.95rem"},
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                _feature_card(
                                    icon="bi-map-fill",
                                    title="Market Analysis",
                                    desc=(
                                        "Explore how HDB resale prices and growth rates have changed "
                                        "across Singapore's 26 towns. Interactive choropleth map with "
                                        "flat-type filtering, year selection, and town drill-down."
                                    ),
                                    href="/general-trends",
                                    btn_text="Explore Market →",
                                    alt=False,
                                ),
                                md=4, className="mb-4",
                            ),
                            dbc.Col(
                                _feature_card(
                                    icon="bi-geo-alt-fill",
                                    title="Flat Amenities",
                                    desc=(
                                        "Compare up to 3 shortlisted flats across 7 amenity categories: "
                                        "MRT, mall, hawker centre, sports hall, polyclinic, "
                                        "primary schools, and parks within 1 km."
                                    ),
                                    href="/amenities-comparison",
                                    btn_text="Compare Flats →",
                                    alt=True,
                                ),
                                md=4, className="mb-4",
                            ),
                            dbc.Col(
                                _feature_card(
                                    icon="bi-calculator-fill",
                                    title="Flat Valuation",
                                    desc=(
                                        "Enter your flat's postal code, type, size, floor level, and "
                                        "remaining lease to get a personalised estimated value based on "
                                        "the most comparable recent transactions within 1.5 km."
                                    ),
                                    href="/flat-valuation",
                                    btn_text="Value a Flat →",
                                    alt=False,
                                ),
                                md=4, className="mb-4",
                            ),
                        ],
                        className="g-4",
                    ),
                ]
            ),
            className="py-5",
            style={"backgroundColor": "#fbf8ff"},
        ),

        # ── How-to section (surface-low background) ───────────────────────────
        html.Div(
            dbc.Container(
                [
                    html.Div(
                        [
                            html.Div("How It Works", className="section-eyebrow text-center"),
                            html.H2("Your Property Research Workflow", className="section-title text-center mb-2"),
                            html.P(
                                "Follow these three steps to make a confident, data-backed property decision.",
                                className="text-center mb-5",
                                style={"color": "#454652", "fontSize": "0.95rem"},
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                _step_card(
                                    "1",
                                    "Explore Market Trends",
                                    "Open Market Analysis and browse the interactive choropleth. "
                                    "Toggle between median price, YoY growth, and price per sqm. "
                                    "Click any town to see its historical trend and flat-type breakdown.",
                                ),
                                md=4, className="mb-4",
                            ),
                            dbc.Col(
                                _step_card(
                                    "2",
                                    "Compare Flat Amenities",
                                    "Shortlist 2–3 flats and enter their postal codes in the Amenities "
                                    "Comparison tool. See which flat has the best MRT, mall, school, "
                                    "and hawker access side by side — with walking times.",
                                ),
                                md=4, className="mb-4",
                            ),
                            dbc.Col(
                                _step_card(
                                    "3",
                                    "Get a Personalised Valuation",
                                    "Use Flat Valuation to enter your flat's specific details. "
                                    "Receive an estimated market value matched against comparable "
                                    "recent transactions, with a confidence range and verdict "
                                    "if you have a listed asking price.",
                                ),
                                md=4, className="mb-4",
                            ),
                        ],
                        className="g-4",
                    ),

                    # Quick reference legend
                    html.Div(
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.Div(
                                        [
                                            html.Div("Map Colour Guide", style={
                                                "fontSize": "0.65rem", "fontWeight": "700",
                                                "textTransform": "uppercase", "letterSpacing": "0.07em",
                                                "color": "#454652", "marginBottom": "0.6rem",
                                            }),
                                            html.Div([
                                                html.Span("■ ", style={"color": "#0f2885", "fontWeight": "700"}),
                                                html.Span(" High price / strong growth",
                                                          style={"fontSize": "0.82rem", "color": "#454652"}),
                                            ], className="mb-1"),
                                            html.Div([
                                                html.Span("■ ", style={"color": "#adc8f0", "fontWeight": "700"}),
                                                html.Span(" Lower price / moderate growth",
                                                          style={"fontSize": "0.82rem", "color": "#454652"}),
                                            ]),
                                        ],
                                        style={
                                            "background": "#ffffff",
                                            "borderRadius": "10px",
                                            "padding": "1.25rem 1.5rem",
                                            "boxShadow": "0 4px 20px rgba(8,21,77,0.05)",
                                        },
                                    ),
                                    md=4,
                                ),
                                dbc.Col(
                                    html.Div(
                                        [
                                            html.Div("Valuation Verdict Guide", style={
                                                "fontSize": "0.65rem", "fontWeight": "700",
                                                "textTransform": "uppercase", "letterSpacing": "0.07em",
                                                "color": "#454652", "marginBottom": "0.6rem",
                                            }),
                                            html.Div("✅  Fair value — listed price ≈ ±5% of estimate",
                                                     style={"fontSize": "0.82rem", "color": "#454652", "marginBottom": "0.3rem"}),
                                            html.Div("🔴  Overvalued — listed price > +5% above estimate",
                                                     style={"fontSize": "0.82rem", "color": "#454652", "marginBottom": "0.3rem"}),
                                            html.Div("🟢  Undervalued — listed price > −5% below estimate",
                                                     style={"fontSize": "0.82rem", "color": "#454652"}),
                                        ],
                                        style={
                                            "background": "#ffffff",
                                            "borderRadius": "10px",
                                            "padding": "1.25rem 1.5rem",
                                            "boxShadow": "0 4px 20px rgba(8,21,77,0.05)",
                                        },
                                    ),
                                    md=6,
                                ),
                            ],
                            className="g-4 mt-1",
                        ),
                    ),
                ]
            ),
            className="section-surface-low",
        ),

        # ── Data sources strip ────────────────────────────────────────────────
        html.Div(
            dbc.Container(
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div("Data Sources", style={
                                    "fontSize": "0.65rem", "fontWeight": "700",
                                    "textTransform": "uppercase", "letterSpacing": "0.08em",
                                    "color": "#5bc8af", "marginBottom": "0.5rem",
                                }),
                                html.P(
                                    [
                                        "HDB resale transactions from ",
                                        html.A("data.gov.sg", href="https://data.gov.sg",
                                               target="_blank", style={"color": "#5bc8af"}),
                                        " · MRT/LRT distances via OneMap API "
                                        "· SORA rates from MAS "
                                        "· CPI data from SingStat",
                                    ],
                                    style={"color": "rgba(255,255,255,0.60)", "fontSize": "0.82rem",
                                           "marginBottom": "0"},
                                ),
                            ],
                            md=8,
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div(
                                        "PropertyMinBrothers",
                                        style={
                                            "fontFamily": "'Manrope', sans-serif",
                                            "fontWeight": "800", "fontSize": "1rem",
                                            "color": "#ffffff", "marginBottom": "0.2rem",
                                        },
                                    ),
                                    html.Div(
                                        "买房子 · 卖房子 · 找我们",
                                        style={"color": "#5bc8af", "fontSize": "0.78rem",
                                               "fontWeight": "600"},
                                    ),
                                ],
                                className="text-md-end",
                            ),
                            md=4,
                        ),
                    ],
                    className="align-items-center",
                ),
                fluid=True,
                className="px-4",
            ),
            className="site-footer",
        ),
    ],
)
