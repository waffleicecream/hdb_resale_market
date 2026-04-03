import dash
from dash import html

dash.register_page(__name__, path="/", name="Home")


# ── Tool cards ────────────────────────────────────────────────
def tool_card(icon, title, desc, href):
    return html.A(className="tool-card", href=href, children=[
        html.Div(icon, className="tool-icon"),
        html.Div(className="tool-title", children=[title, html.Span("↗", className="arrow")]),
        html.P(desc, className="tool-desc"),
        html.Span("Explore →", className="tool-link"),
    ])


# ── Layout ────────────────────────────────────────────────────
layout = html.Div(className="page-wrapper", children=[

    # ── Hero ──────────────────────────────────────────────────
    html.Section(className="hero", children=[
        html.Div(className="hero-inner", children=[
            # Left: headline
            html.Div(className="hero-content", children=[
                html.H1(className="hero-title", children=[
                    html.Span("Make Your Next", className="hero-line", style={"display": "block"}),
                    html.Span("Property Decision", className="hero-line", style={"display": "block"}),
                    html.Span("With Confidence", className="accent-word", style={"display": "block"}),
                ]),
            ]),
            # Right: image that bleeds from the dark background
            html.Div(className="hero-image-panel", children=[
                html.Img(src="/assets/bkgrd3.jpeg", className="hero-bg-img"),
            ]),
        ])
    ]),

    # ── Tool Overview ──────────────────────────────────────────
    html.Section(className="tools-section", children=[
        html.Div(className="tools-section-inner", children=[
            html.H2("Three Tools for Every Stage of Your Search", className="section-heading"),
            html.Div(className="tools-grid", children=[
                tool_card("📊", "Market Analysis",
                          "Explore HDB resale price trends, transaction volumes, and town-level statistics across Singapore through an interactive choropleth map.",
                          "/market-analysis"),
                tool_card("📍", "Amenities Comparison",
                          "Compare up to three flats side-by-side on proximity to MRT stations, hawker centres, malls, polyclinics, schools, and parks.",
                          "/amenities-comparison"),
                tool_card("🏠", "Flat Valuation",
                          "Get a data-driven price estimate for any HDB flat by postal code and flat type, with comparable nearby transactions and a listed-price indicator.",
                          "/flat-valuation"),
            ]),
        ])
    ]),
])
