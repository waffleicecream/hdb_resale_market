import dash
from dash import Dash, html, dcc, callback, Output, Input

import numpy as np

class LogToPriceWrapper:
    def __init__(self, model):
        self.model = model
    
    def predict(self, X):
        log_pred = self.model.predict(X)
        return np.exp(log_pred)

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


<<<<<<< HEAD
server = app.server  # expose Flask server for gunicorn

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=7860)
=======
if __name__ == "__main__":
    app.run(debug=True, port=8050)
>>>>>>> ry_claude
    