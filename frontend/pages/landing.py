import dash
from dash import html

dash.register_page(__name__, path="/", name="Home")


# ── Step strip ────────────────────────────────────────────────
def step_strip():
    steps = [
        ("①", "Where should I buy?"),
        ("②", "Which flat is better?"),
        ("③", "Is it worth the price?"),
    ]
    items = []
    for i, (num, label) in enumerate(steps):
        items.append(
            html.Div(className="step-strip-item", children=[
                html.Span(num, className="step-strip-num"),
                html.Span(label, className="step-strip-label"),
            ])
        )
        if i < len(steps) - 1:
            items.append(html.Span("→", className="step-strip-arrow"))
    return html.Div(className="step-strip", children=items)


# ── Tool cards ────────────────────────────────────────────────
def tool_card(step_label, accent_cls, icon, title, desc, cta, href):
    return html.A(className=f"tool-card-v2 {accent_cls}", href=href, children=[
        html.Div(className="tool-card-step", children=step_label),
        html.Div(icon, className="tool-card-icon"),
        html.Div(title, className="tool-card-title"),
        html.P(desc, className="tool-card-desc"),
        html.Span(cta, className="tool-card-cta"),
    ])


# ── Layout ────────────────────────────────────────────────────
layout = html.Div(className="page-wrapper", children=[

    # ── Hero (compact) ────────────────────────────────────────
    html.Section(className="hero hero-compact", children=[
        html.Div(className="hero-inner hero-inner-compact", children=[
            html.Div(className="hero-content", children=[
                html.H1("Find the Right HDB Resale Flat", className="hero-title hero-title-compact"),
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

    # ── Journey section ───────────────────────────────────────
    html.Section(className="tools-section", children=[
        html.Div(className="tools-section-inner", children=[
            html.H2("Three Tools for Every Stage of Your Search", className="section-heading"),
            html.P("Not sure where to start? Follow the steps below.",
                   className="section-subheading"),
            step_strip(),
            html.Div(className="tools-grid-v2", children=[
                tool_card(
                    "STEP 1 · Where should I buy?", "card-blue",
                    "📊", "Explore towns before choosing a flat",
                    "See price trends, growth, and transaction activity across Singapore.",
                    "Explore →", "/market-analysis",
                ),
                tool_card(
                    "STEP 2 · Which flat is better?", "card-yellow",
                    "📍", "Compare shortlisted flats",
                    "Compare proximity to MRT, hawker centres, schools, malls, and polyclinics side by side.",
                    "Compare →", "/amenities-comparison",
                ),
                tool_card(
                    "STEP 3 · Is it worth the price?", "card-green",
                    "🏠", "Check if a flat is overpriced",
                    "Get a fair price estimate and see similar transactions nearby.",
                    "Evaluate →", "/flat-valuation",
                ),
            ]),
        ])
    ]),
])
