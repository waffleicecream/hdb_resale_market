import json, os
import dash
from dash import html, dcc, callback, Output, Input, State, no_update
import plotly.graph_objects as go

dash.register_page(__name__, path="/flat-valuation", name="Flat Valuation")

_BASE = os.path.dirname(os.path.dirname(__file__))
with open(os.path.join(_BASE, "mock_data", "valuation_demo.json"), encoding="utf-8") as f:
    DEMO = json.load(f)

FLAT_TYPES = ["2-Room", "3-Room", "4-Room", "5-Room", "Executive"]
STOREY_BINS = [
    {"label": "Low (Floors 01\u201305)", "value": "Low"},
    {"label": "Medium (Floors 06\u201312)", "value": "Medium"},
    {"label": "High (Floors 13+)", "value": "High"},
]
LEASE_BINS = [
    {"label": "Under 60 years", "value": "Under 60 years"},
    {"label": "60\u201375 years", "value": "60-75 years"},
    {"label": "75\u201390 years", "value": "75-90 years"},
    {"label": "Over 90 years", "value": "Over 90 years"},
]

DEMO_LISTING_PRICE = 650000  # above p85=598000 — showcases OVERPRICED state


# ── Verdict logic ──────────────────────────────────────────────
def get_verdict(listing_price, p15, p85):
    if listing_price is None:
        return None
    if listing_price > p85:
        return "OVERPRICED"
    if listing_price < p15:
        return "GOOD DEAL"
    return "FAIR VALUE"


# ── Shared input form ──────────────────────────────────────────
def input_form(prefill=None, compact=False):
    pf = prefill or {}
    grid_cls = "val-input-grid-compact" if compact else "val-input-grid"
    return html.Div([
        html.Div(className=grid_cls, children=[
            html.Div(className="form-group", children=[
                html.Label("Postal Code", className="form-label"),
                dcc.Input(id="val-postal", type="text", maxLength=6,
                          placeholder="e.g. 310058", className="form-input",
                          value=pf.get("postal_code", "")),
            ]),
            html.Div(className="form-group", children=[
                html.Label("Flat Type", className="form-label"),
                dcc.Dropdown(id="val-flat-type",
                             options=[{"label": ft, "value": ft} for ft in FLAT_TYPES],
                             placeholder="Select flat type", clearable=False,
                             value=pf.get("flat_type"),
                             style={"fontSize": "14px"}),
            ]),
            html.Div(className="form-group", children=[
                html.Label("Storey Level", className="form-label"),
                dcc.Dropdown(id="val-storey-bin",
                             options=STOREY_BINS,
                             placeholder="Select storey", clearable=False,
                             value=pf.get("storey_level_bin"),
                             style={"fontSize": "14px"}),
            ]),
            html.Div(className="form-group", children=[
                html.Label("Remaining Lease", className="form-label"),
                dcc.Dropdown(id="val-lease-bin",
                             options=LEASE_BINS,
                             placeholder="Select lease range", clearable=False,
                             value=pf.get("remaining_lease_bin"),
                             style={"fontSize": "14px"}),
            ]),
            html.Div(className="form-group", children=[
                html.Label("Listed Price (optional)", className="form-label"),
                dcc.Input(id="val-listed", type="number", min=0,
                          placeholder="e.g. 638000", className="form-input",
                          debounce=True),
            ]),
            html.Div(className="form-group val-submit-col", children=[
                html.P(id="val-error",
                       style={"color": "var(--color-danger)", "fontSize": "12px",
                              "minHeight": "16px", "marginBottom": "4px"}),
                html.Button("Get Valuation", id="val-submit",
                            className="btn btn-primary val-submit-btn"),
            ]),
        ]),
    ])


# ── Market premium bar ─────────────────────────────────────────
def market_premium_bar(listing_price, p15, p85):
    if not listing_price:
        return html.P(
            "Enter a listed price above to see the market premium.",
            style={"fontSize": "12px", "color": "var(--color-text-muted)",
                   "fontStyle": "italic"},
        )
    midpoint = (p15 + p85) / 2
    pct = (listing_price - midpoint) / midpoint * 100
    verdict = get_verdict(listing_price, p15, p85)

    if verdict == "OVERPRICED":
        pct_color = "var(--color-danger)"
        pct_label = f"+{pct:.1f}%"
        marker_color = "#DC2626"
        sub = f"Listed ${listing_price - p85:,} above the top of the predicted range."
    elif verdict == "GOOD DEAL":
        pct_color = "var(--color-success)"
        pct_label = f"{pct:.1f}%"
        marker_color = "#16A34A"
        sub = f"Listed ${p15 - listing_price:,} below the bottom of the predicted range."
    else:
        pct_color = "var(--color-text-secondary)"
        pct_label = f"{pct:+.1f}%"
        marker_color = "#1C4ED8"
        sub = "Listed price falls within the predicted fair value range."

    # Position: extended range = p15 ± 1×span on each side
    span = p85 - p15
    low = p15 - span
    high = p85 + span
    pos = max(2, min(98, (listing_price - low) / (high - low) * 100))

    return html.Div([
        html.Div([
            html.Span("Market Premium",
                      style={"fontSize": "12px", "fontWeight": "600",
                             "color": "var(--color-text-secondary)"}),
            html.Span(pct_label,
                      style={"fontSize": "15px", "fontWeight": "700",
                             "color": pct_color}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "marginBottom": "8px"}),
        html.Div(className="premium-bar-track", children=[
            html.Div(className="premium-bar-fill",
                     style={"width": f"{pos}%", "background": marker_color,
                            "opacity": "0.25"}),
            html.Div(className="premium-bar-marker",
                     style={"left": f"{pos}%", "background": marker_color}),
        ]),
        html.Div(className="premium-bar-labels", children=[
            html.Span("UNDERPRICED"),
            html.Span("FAIR VALUE"),
            html.Span("OVERPRICED"),
        ]),
        html.P(sub, style={"fontSize": "12px", "color": pct_color,
                           "marginTop": "6px", "marginBottom": "0"}),
    ])


# ── Trend chart ────────────────────────────────────────────────
def make_trend_chart(trend_data, listing_price=None, p15=None, p85=None):
    if not trend_data:
        return go.Figure()
    quarters = [t["quarter"] for t in trend_data]
    prices = [t["avg_price"] for t in trend_data]
    counts = [t["n_transactions"] for t in trend_data]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=quarters, y=prices, mode="lines+markers",
        line=dict(color="#1C4ED8", width=2),
        marker=dict(size=6, color="#1C4ED8"),
        customdata=[[c] for c in counts],
        hovertemplate="%{x} | Avg $%{y:,.0f} | %{customdata[0]} transactions<extra></extra>",
        showlegend=False,
    ))
    # Prominent dot on last point
    fig.add_trace(go.Scatter(
        x=[quarters[-1]], y=[prices[-1]], mode="markers",
        marker=dict(size=11, color="#1C4ED8", line=dict(color="white", width=2)),
        hoverinfo="skip", showlegend=False,
    ))
    if p15 is not None and p85 is not None:
        midpoint = (p15 + p85) // 2
        fig.add_hline(y=midpoint, line_dash="dash", line_color="#16A34A",
                      annotation_text=f"Predicted fair value: ${midpoint:,}",
                      annotation_position="top left",
                      annotation=dict(font_color="#16A34A", font_size=11))
    if listing_price:
        fig.add_hline(y=listing_price, line_dash="dash", line_color="#DC2626",
                      annotation_text=f"Your listing: ${listing_price:,}",
                      annotation_position="top right",
                      annotation=dict(font_color="#DC2626", font_size=11))
    fig.update_layout(
        margin={"t": 16, "b": 8, "l": 56, "r": 16},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, color="#9CA3AF", tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="#E5E7EB", color="#9CA3AF",
                   tickformat="$,.0f", tickfont=dict(size=10)),
        showlegend=False, height=220,
    )
    return fig


# ── Past transactions table (scrollable) ──────────────────────
def past_data_table(data):
    txns = data.get("past_transactions", [])
    town = data.get("town", "this area")
    fallback = len(txns) < 3
    rows = [
        html.Tr([
            html.Td(t["date"],
                    style={"fontSize": "12px", "color": "var(--color-text-secondary)"}),
            html.Td(t["floor"]),
            html.Td(t["flat_type"]),
            html.Td(f"${t['price']:,.0f}", className="td-price"),
        ]) for t in txns[:10]
    ]
    return html.Div([
        html.Div(
            f"\u26a0\ufe0f Limited transactions on this street. "
            f"Showing town-level comparables for {town}.",
            className="fallback-notice",
        ) if fallback else None,
        html.Div(className="val-txn-scroll", children=[
            html.Table(className="data-table", children=[
                html.Thead(html.Tr([
                    html.Th("MONTH"), html.Th("STOREY"),
                    html.Th("FLAT TYPE"), html.Th("PRICE"),
                ])),
                html.Tbody(rows),
            ]),
        ]) if rows else html.P("No recent transactions found.",
                               style={"color": "var(--color-text-muted)",
                                      "fontSize": "13px"}),
    ])


# ── Lease warning ──────────────────────────────────────────────
def lease_warning(lease_bin):
    if lease_bin == "Under 60 years":
        return html.Div(className="lease-warning-red", children=[
            html.Strong("\U0001f6a8 Lease Warning: "),
            "Flats below 60 years remaining lease are not eligible for HDB loans. "
            "CPF usage will be restricted based on buyer\u2019s age. "
            "Seek financial advice before proceeding.",
        ])
    if lease_bin == "60-75 years":
        return html.Div(className="lease-warning-yellow", children=[
            html.Strong("\u26a0\ufe0f Lease Advisory: "),
            "Flats below 75 years remaining lease may face stricter bank loan "
            "conditions. Verify with your bank before proceeding.",
        ])
    return None


# ── Valuation insight text ─────────────────────────────────────
def valuation_insight(data, listing_price, verdict, p15, p85):
    flat_type = data.get("flat_type", "")
    town = data.get("town", "this area")
    txns = data.get("past_transactions", [])
    n_txns = len(txns)

    if verdict == "OVERPRICED" and listing_price:
        gap = listing_price - p85
        prices = [t["price"] for t in txns]
        min_r = f"${min(prices):,}" if prices else "N/A"
        max_r = f"${max(prices):,}" if prices else "N/A"
        text = (
            f"The listed price of ${listing_price:,} is ${gap:,} above our predicted "
            f"fair value range for {flat_type} flats in {town}. Recent transactions "
            f"in this area closed between {min_r} and {max_r}. Consider negotiating "
            f"or exploring the alternatives below."
        )
    elif verdict == "FAIR VALUE" and listing_price:
        text = (
            f"The listed price of ${listing_price:,} falls within our predicted fair "
            f"value range for {flat_type} flats in {town}. This appears reasonably "
            f"priced based on {n_txns} recent transactions in the area."
        )
    elif verdict == "GOOD DEAL" and listing_price:
        gap = p15 - listing_price
        text = (
            f"The listed price of ${listing_price:,} is ${gap:,} below our predicted "
            f"fair value range for {flat_type} flats in {town}. This may represent "
            f"good value \u2014 similar units have transacted at higher prices recently. "
            f"Act promptly as well-priced flats tend to move quickly."
        )
    else:
        text = "Enter a listed price above to receive your valuation verdict."

    return html.Div(className="val-insight-box", children=[
        html.P("\U0001f4ac Valuation Insight",
               style={"fontSize": "11px", "fontWeight": "700",
                      "letterSpacing": "0.06em", "textTransform": "uppercase",
                      "color": "var(--color-text-muted)", "marginBottom": "6px"}),
        html.P(text, style={"fontSize": "13px", "lineHeight": "1.65",
                            "color": "var(--color-text-secondary)", "margin": "0"}),
    ])


# ── Map: all pins ──────────────────────────────────────────────
def make_listings_map(user_lat, user_lon, user_address, listings):
    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(
        lat=[user_lat], lon=[user_lon], mode="markers+text",
        marker=go.scattermapbox.Marker(size=20, color="#1C4ED8"),
        text=["Your flat"],
        textposition="bottom center",
        textfont=dict(size=11, color="#1C4ED8"),
        hovertext=[f"<b>Your flat</b><br>{user_address}"],
        hoverinfo="text", showlegend=False,
    ))
    for lst in listings:
        active = lst.get("listing_active", True)
        color = "#16A34A" if active else "#9CA3AF"
        note = "" if active else "<br><i>Listing may have been sold</i>"
        fig.add_trace(go.Scattermapbox(
            lat=[lst["lat"]], lon=[lst["lon"]], mode="markers+text",
            marker=go.scattermapbox.Marker(size=16, color=color),
            text=[str(lst["rank"])],
            textfont=dict(size=9, color="white"),
            hovertext=[f"<b>#{lst['rank']} Blk {lst['blk']} {lst['street']}</b><br>"
                       f"Asking: ${lst['asking_price']:,}{note}"],
            hoverinfo="text", showlegend=False,
        ))
    all_lats = [user_lat] + [l["lat"] for l in listings]
    all_lons = [user_lon] + [l["lon"] for l in listings]
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)
    fig.update_layout(
        mapbox=dict(style="carto-positron", zoom=14,
                    center={"lat": center_lat, "lon": center_lon}),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
    )
    return fig


# ── Listing cards (scrollable, no HDB link) ────────────────────
def listing_cards(listings, p85):
    cards = []
    for lst in listings:
        active = lst.get("listing_active", True)
        reasons = lst.get("match_reasons", [])

        signal = (
            html.Span("\u26a0\ufe0f Also overpriced",
                      style={"color": "var(--color-danger)", "fontSize": "11px",
                             "fontWeight": "600"})
            if lst["asking_price"] > p85 else
            html.Span("\u2713 Within fair value range",
                      style={"color": "var(--color-success)", "fontSize": "11px",
                             "fontWeight": "600"})
        )

        cards.append(html.Div(
            className="listing-card" + (" listing-card-inactive" if not active else ""),
            children=[
                html.Div(className="listing-card-left", children=[
                    html.Div(str(lst["rank"]), className="listing-card-rank-num"),
                ]),
                html.Div(className="listing-card-body", children=[
                    html.Div(f"Blk {lst['blk']} {lst['street']}",
                             style={"fontWeight": "700", "fontSize": "14px",
                                    "color": "var(--color-text-primary)",
                                    "marginBottom": "3px"}),
                    html.Div([
                        html.Span(lst["flat_type"],
                                  style={"fontSize": "12px",
                                         "color": "var(--color-text-secondary)"}),
                        html.Span(" \u00b7 ",
                                  style={"color": "var(--color-text-muted)"}),
                        html.Span(lst["storey_display"],
                                  style={"fontSize": "12px",
                                         "color": "var(--color-text-secondary)"}),
                        html.Span(" \u00b7 ",
                                  style={"color": "var(--color-text-muted)"}),
                        html.Span(lst["remaining_lease"],
                                  style={"fontSize": "12px",
                                         "color": "var(--color-text-secondary)"}),
                    ]),
                    html.Div(" \u00b7 ".join(reasons),
                             style={"fontSize": "11px", "color": "var(--color-text-muted)",
                                    "fontStyle": "italic", "marginTop": "3px"}),
                    html.Div("Listing may have been sold",
                             style={"fontSize": "11px",
                                    "color": "var(--color-text-muted)",
                                    "fontStyle": "italic", "marginTop": "2px"}
                             ) if not active else None,
                ]),
                html.Div(className="listing-card-price", children=[
                    html.Div(f"${lst['asking_price']:,}",
                             style={"fontFamily": "var(--mono)", "fontWeight": "700",
                                    "fontSize": "16px",
                                    "color": "var(--color-text-primary)",
                                    "whiteSpace": "nowrap"}),
                    signal,
                ]),
            ],
        ))

    return html.Div(className="listings-section", children=[
        html.Div(className="listings-header", children=[
            html.P("CURRENT MARKET ALTERNATIVES",
                   className="listings-header-title"),
            html.P("Matched on flat type \u00b7 storey bin \u00b7 "
                   "remaining lease bin \u00b7 Ranked by similarity",
                   className="listings-header-sub"),
        ]),
        html.Div(className="listings-scroll", children=cards) if cards else
        html.P("No current listings found.",
               style={"padding": "16px", "color": "var(--color-text-muted)",
                      "fontSize": "13px"}),
    ])


# ── Top-left panel ─────────────────────────────────────────────
def top_left_panel(data, listing_price=None):
    p15 = data["projection"]["p15"]
    p85 = data["projection"]["p85"]
    midpoint = (p15 + p85) // 2
    verdict = get_verdict(listing_price, p15, p85)
    if verdict == "OVERPRICED":
        badge = html.Div("\u26a0\ufe0f OVERPRICED",
                         className="verdict-badge verdict-overpriced")
        listed_color = "var(--color-danger)"
    elif verdict == "GOOD DEAL":
        badge = html.Div("\U0001f7e2 GOOD DEAL",
                         className="verdict-badge verdict-gooddeal")
        listed_color = "var(--color-success)"
    elif verdict == "FAIR VALUE":
        badge = html.Div("\u2705 FAIR VALUE",
                         className="verdict-badge verdict-fairvalue")
        listed_color = "var(--color-text-secondary)"
    else:
        badge = None
        listed_color = None

    warn = lease_warning(data.get("remaining_lease_bin", ""))

    return html.Div(className="val-top-left card", children=[
        # Header row
        html.Div([
            html.P("ESTIMATED CURRENT PRICE", className="val-panel-label"),
            badge,
        ], style={"display": "flex", "alignItems": "center",
                  "justifyContent": "space-between", "marginBottom": "12px"}),

        # Big predicted price
        html.Div(f"${midpoint:,}",
                 style={"fontSize": "40px", "fontWeight": "800",
                        "color": "var(--color-text-primary)",
                        "fontFamily": "var(--mono)", "lineHeight": "1.1",
                        "marginBottom": "4px"}),
        html.P(f"Range: ${p15:,} \u2014 ${p85:,}",
               style={"fontSize": "13px", "color": "var(--color-text-secondary)",
                      "marginBottom": "4px"}),
        # Listed price
        html.P(f"Listed at ${listing_price:,}",
               style={"fontSize": "14px", "fontWeight": "600",
                      "color": listed_color, "marginBottom": "12px"}
               ) if listing_price else None,

        # Market premium bar
        market_premium_bar(listing_price, p15, p85),

        html.Div(className="divider", style={"margin": "16px 0"}),

        # Lease warning
        html.Div(warn, style={"marginBottom": "12px"}) if warn else None,

        # Metadata grid
        html.Div(className="flat-detail-grid", children=[
            html.Div([html.P("ADDRESS", className="flat-detail-label"),
                      html.P(data["address"], className="flat-detail-val")]),
            html.Div([html.P("POSTAL CODE", className="flat-detail-label"),
                      html.P(data["postal_code"], className="flat-detail-val")]),
            html.Div([html.P("FLAT TYPE", className="flat-detail-label"),
                      html.P(data["flat_type"], className="flat-detail-val")]),
            html.Div([html.P("REMAINING LEASE", className="flat-detail-label"),
                      html.P(data["remaining_lease"], className="flat-detail-val")]),
            html.Div([html.P("STOREY BIN", className="flat-detail-label"),
                      html.P(data["storey_level_bin"], className="flat-detail-val")]),
            html.Div([html.P("TOWN", className="flat-detail-label"),
                      html.P(data["town"], className="flat-detail-val")]),
        ]),

        html.Div(className="divider", style={"margin": "16px 0"}),

        # Valuation insight
        valuation_insight(data, listing_price, verdict, p15, p85),
    ])


# ── Top-right panel (chart + scrollable table, no tabs) ────────
def top_right_panel(data, listing_price=None):
    p15 = data["projection"]["p15"]
    p85 = data["projection"]["p85"]
    return html.Div(className="val-top-right card", children=[
        html.Div([
            html.P("HISTORICAL PRICE REFERENCE", className="val-panel-label"),
            html.P("Same street \u00b7 same storey bin \u00b7 same flat type",
                   style={"fontSize": "12px", "color": "var(--color-text-secondary)",
                          "fontStyle": "italic", "marginTop": "2px",
                          "marginBottom": "0"}),
        ], style={"marginBottom": "16px"}),

        # Chart on top
        dcc.Graph(
            figure=make_trend_chart(data.get("graph_trend", []),
                                    listing_price=listing_price,
                                    p15=p15, p85=p85),
            config={"displayModeBar": False},
            style={"height": "220px"},
        ),
        html.P(
            "Average transaction price \u2014 same street, same flat type, same storey bin",
            style={"fontSize": "11px", "color": "var(--color-text-muted)",
                   "textAlign": "center", "marginTop": "2px", "fontStyle": "italic",
                   "marginBottom": "16px"},
        ),

        # Past transactions table below (scrollable)
        html.P("PAST TRANSACTIONS", className="val-panel-label",
               style={"paddingTop": "8px",
                      "borderTop": "1px solid var(--color-border)"}),
        past_data_table(data),
    ])


# ── Bottom-left panel: map ─────────────────────────────────────
def bottom_left_panel(data):
    listings = data.get("current_listings", [])
    map_fig = make_listings_map(data["lat"], data["lon"], data["address"], listings)
    return html.Div(className="card val-map-card", children=[
        html.P("LOCATION INTELLIGENCE", className="val-panel-label",
               style={"marginBottom": "12px"}),
        dcc.Graph(
            figure=map_fig,
            config={"displayModeBar": False, "scrollZoom": True},
            style={"height": "360px"},
        ),
        html.Div(className="map-legend", children=[
            html.Span("\U0001f4cd",
                      style={"color": "#1C4ED8", "marginRight": "4px"}),
            html.Span("Your flat",
                      style={"marginRight": "20px", "fontSize": "12px",
                             "color": "var(--color-text-secondary)"}),
            html.Span("\U0001f7e2", style={"marginRight": "4px"}),
            html.Span("Current alternatives (ranked)",
                      style={"fontSize": "12px",
                             "color": "var(--color-text-secondary)"}),
        ]),
    ])


# ── Bottom-right panel: scrollable listings ────────────────────
def bottom_right_panel(data, p85):
    return listing_cards(data.get("current_listings", []), p85)


# ── Overpriced banner (amber style) ───────────────────────────
def overpriced_banner():
    return html.Div(className="overpriced-banner", children=[
        html.P("\u26a0\ufe0f  Overpriced? Check out potential alternatives below",
               className="overpriced-banner-title"),
        html.P("Current listings matched on flat type, storey level, and remaining "
               "lease \u2014 sorted by similarity to your flat.",
               className="overpriced-banner-sub"),
    ])


# ── Valuation dashboard ────────────────────────────────────────
def valuation_dashboard(data, listing_price=None):
    p15 = data["projection"]["p15"]
    p85 = data["projection"]["p85"]

    children = [
        html.Div(className="val-compact-bar", children=[
            html.Div(className="val-compact-inner", children=[
                input_form(prefill=data, compact=True),
            ]),
        ]),
        html.Button(id="val-demo", style={"display": "none"}, n_clicks=0),
        html.Div(className="val-top-row val-content-area", children=[
            top_left_panel(data, listing_price),
            top_right_panel(data, listing_price),
        ]),
    ]

    if get_verdict(listing_price, p15, p85) == "OVERPRICED":
        children.append(
            html.Div(overpriced_banner(),
                     className="val-overpriced-banner-wrap val-content-area"))

    children.append(
        html.Div(className="val-bottom-row val-content-area", children=[
            bottom_left_panel(data),
            bottom_right_panel(data, p85),
        ]))

    return children


# ── Pre-search layout ──────────────────────────────────────────
def pre_search_layout(prefill=None):
    return html.Div(className="valuation-pre", children=[
        html.Div(className="valuation-pre-inner", children=[
            html.H1("How much is this flat worth?", className="valuation-pre-title"),
            html.P(
                "Enter a postal code and flat details to get a data-driven "
                "price projection.",
                className="valuation-pre-sub",
            ),
            html.Div(className="valuation-form-card", children=[
                input_form(prefill=prefill),
                html.Button(
                    "Try Demo \u2014 Blk 58 Toa Payoh", id="val-demo",
                    className="btn btn-secondary",
                    style={"width": "100%", "justifyContent": "center",
                           "marginTop": "8px", "fontSize": "13px"},
                ),
            ]),
            html.Div(className="feature-cards-row", children=[
                html.Div(className="feature-card", children=[
                    html.Div("\U0001f4ca", className="feature-card-icon"),
                    html.P("Price Projection", className="feature-card-title"),
                    html.P(
                        "15th\u201385th percentile range based on historical "
                        "transactions and flat attributes.",
                        className="feature-card-desc",
                    ),
                ]),
                html.Div(className="feature-card", children=[
                    html.Div("\U0001f3e2", className="feature-card-icon"),
                    html.P("Comparable Transactions", className="feature-card-title"),
                    html.P(
                        "Recent transactions on the same street \u2014 same "
                        "storey level and flat type.",
                        className="feature-card-desc",
                    ),
                ]),
                html.Div(className="feature-card", children=[
                    html.Div("\U0001f4b0", className="feature-card-icon"),
                    html.P("Listed Price Indicator", className="feature-card-title"),
                    html.P(
                        "Enter an asking price to see if it is overpriced, "
                        "fair value, or a good deal.",
                        className="feature-card-desc",
                    ),
                ]),
            ]),
        ])
    ])


# ── Layout (entry point) ───────────────────────────────────────
layout = html.Div(className="page-wrapper", id="val-page-root", children=[
    pre_search_layout()
])


# ── Callbacks ──────────────────────────────────────────────────
@callback(
    Output("val-page-root", "children"),
    Output("val-error", "children", allow_duplicate=True),
    Input("val-submit", "n_clicks"),
    Input("val-demo", "n_clicks"),
    State("val-postal", "value"),
    State("val-flat-type", "value"),
    State("val-storey-bin", "value"),
    State("val-lease-bin", "value"),
    State("val-listed", "value"),
    prevent_initial_call=True,
)
def run_valuation(_n_submit, _n_demo, postal, flat_type, storey_bin, lease_bin, listed):
    from dash import ctx
    trig = ctx.triggered_id

    if trig == "val-demo":
        return valuation_dashboard(DEMO, listing_price=DEMO_LISTING_PRICE), ""

    if not postal or len(str(postal).strip()) != 6 or not str(postal).strip().isdigit():
        return no_update, "Please enter a valid 6-digit postal code."
    if not flat_type:
        return no_update, "Please select a flat type."
    if not storey_bin:
        return no_update, "Please select a storey level."
    if not lease_bin:
        return no_update, "Please select a remaining lease range."

    listed_int = int(listed) if listed else None
    return valuation_dashboard(DEMO, listing_price=listed_int), ""


@callback(
    Output("val-page-root", "children", allow_duplicate=True),
    Input("url", "pathname"),
    State("valuation-prefill", "data"),
    prevent_initial_call=True,
)
def prefill_from_store(pathname, prefill_data):
    if pathname == "/flat-valuation" and prefill_data:
        return pre_search_layout(prefill_data)
    return no_update
