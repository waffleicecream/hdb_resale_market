import dash
from dash import Dash, html, dcc, callback, Output, Input

app = Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    title="PropertyMinBrothers",
    update_title=None,
)

def navbar():
    return html.Nav(className="navbar", children=[
        html.Div(className="navbar-inner", children=[
            dcc.Link(href="/", className="navbar-brand", children=[
                html.Img(src="/assets/logo.jpg", className="navbar-logo"),
                html.Div([
                    html.Span([
                        html.Span("PropertyMin", className="accent"),
                        "Brothers"
                    ], className="brand-name"),
                    html.P("买房子卖房子找我们", className="brand-slogan"),
                ]),
            ]),
            html.Div(className="navbar-links", children=[
                dcc.Link("Market Analysis",      href="/market-analysis",      className="nav-link", id="nav-market"),
                dcc.Link("Amenities Comparison", href="/amenities-comparison", className="nav-link", id="nav-amenities"),
                dcc.Link("Flat Valuation",       href="/flat-valuation",       className="nav-link", id="nav-valuation"),
            ]),
        ])
    ])

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    # Cross-page store: landing search → valuation page prefill
    dcc.Store(id="valuation-prefill", storage_type="session"),
    navbar(),
    dash.page_container,
])

@callback(
    Output("nav-market",    "className"),
    Output("nav-amenities", "className"),
    Output("nav-valuation", "className"),
    Input("url", "pathname"),
)
def set_active_nav(pathname):
    links = ["/market-analysis", "/amenities-comparison", "/flat-valuation"]
    return ["nav-link active" if pathname == href else "nav-link" for href in links]


if __name__ == "__main__":
    app.run(debug=True, port=8050)
