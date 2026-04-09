import dash
from dash import html

dash.register_page(__name__, path="/", name="Home")


# ── OGP-style tool card ───────────────────────────────────────
def ogp_card(image_src, tagline, description, tool_name, href):
    return html.A(className="ogp-card", href=href, children=[
        html.Div(className="ogp-card-image-wrap", children=[
            html.Img(src=image_src, className="ogp-card-image"),
        ]),
        html.Div(className="ogp-card-body", children=[
            html.H3(tagline, className="ogp-card-tagline"),
            html.P(description, className="ogp-card-desc"),
            html.Span(className="ogp-card-tool-name", children=[
                tool_name,
                html.Span(" ↗", className="ogp-card-arrow"),
            ]),
        ]),
    ])


# ── Layout ────────────────────────────────────────────────────
layout = html.Div(className="page-wrapper", children=[

    # ── Hero (compact) ────────────────────────────────────────
    html.Section(className="hero hero-compact", children=[
        html.Div(className="hero-inner hero-inner-compact", children=[
            html.Div(className="hero-content", children=[
                html.H1([
                    "Find the right HDB Resale Flat",
                    html.Br(),
                    "for ", html.Span("all your needs.", className="accent-word"),
                ], className="hero-title hero-title-compact"),
                html.P(
                    "Compare towns, evaluate amenities, and check if a flat is fairly priced — all in one place.",
                    className="hero-subtitle",
                ),
            ]),
            html.Div(className="hero-image-panel", children=[
                html.Img(src="/assets/bkgrd3.jpeg", className="hero-bg-img"),
            ]),
        ])
    ]),

    # ── OGP-style tools section ───────────────────────────────
    html.Section(className="ogp-section", children=[
        html.Div(className="ogp-section-inner", children=[
            html.H2("Three tools for every stage of your search:", className="ogp-section-heading"),
            html.Div(className="ogp-cards-grid", children=[
                ogp_card(
                    image_src="/assets/town.jpg",
                    tagline="Which town should I buy in?",
                    description="Explore resale price trends and demand patterns across Singapore to find a town that matches your budget and investment goals.",
                    tool_name="Market Analysis",
                    href="/market-analysis",
                ),
                ogp_card(
                    image_src="/assets/amenities.jpg",
                    tagline="What amenities are near this flat?",
                    description="Compare resale flats side by side on proximity to MRT stations, schools, hawker centres and more.",
                    tool_name="Amenities Comparison",
                    href="/amenities-comparison",
                ),
                ogp_card(
                    image_src="/assets/valuation.jpg",
                    tagline="Is this flat listing priced fairly?",
                    description="Estimate the market value of any HDB resale flat using our state-of-the-art machine learning algorithm, so you can negotiate with confidence.",
                    tool_name="Flat Valuation",
                    href="/flat-valuation",
                ),
            ]),
        ])
    ]),

    # ── Footer ────────────────────────────────────────────────
    html.Footer(className="landing-footer", children=[
        html.P([
            "Also available at ",
            html.A(
                "huggingface.co/spaces/qyoon/propertyMB",
                href="https://huggingface.co/spaces/qyoon/propertyMB",
                target="_blank",
                className="footer-link",
            ),
        ]),
    ]),
])
