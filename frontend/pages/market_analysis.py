import json, os
import dash
from dash import html, dcc, callback, Output, Input
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

dash.register_page(__name__, path="/market-analysis", name="Market Analysis")

_BASE = os.path.dirname(os.path.dirname(__file__))

with open(os.path.join(_BASE, "MasterPlan2019PlanningAreaBoundaryNoSea.geojson"), encoding="utf-8") as f:
    GEOJSON = json.load(f)

# ── Mock town data ────────────────────────────────────────────
# Each entry: base_price (Q4 2025 median), price changes, transactions
TOWNS = {
    "ANG MO KIO":    {"name": "Ang Mo Kio",       "region": "NORTH-EAST REGION", "bp": 548000, "c3": 3.2,  "c6": 5.8,  "c1y": 9.1,  "t3": 412,  "t6": 798,  "t1y": 1587},
    "BEDOK":         {"name": "Bedok",             "region": "EAST REGION",       "bp": 538000, "c3": 2.8,  "c6": 5.1,  "c1y": 8.4,  "t3": 387,  "t6": 751,  "t1y": 1498},
    "BISHAN":        {"name": "Bishan",            "region": "CENTRAL REGION",    "bp": 680000, "c3": 8.2,  "c6": 12.4, "c1y": 18.2, "t3": 234,  "t6": 445,  "t1y": 892},
    "BUKIT BATOK":   {"name": "Bukit Batok",       "region": "WEST REGION",       "bp": 462000, "c3": 1.5,  "c6": 3.2,  "c1y": 6.1,  "t3": 298,  "t6": 578,  "t1y": 1143},
    "BUKIT MERAH":   {"name": "Bukit Merah",       "region": "CENTRAL REGION",    "bp": 720000, "c3": 5.4,  "c6": 9.2,  "c1y": 14.3, "t3": 423,  "t6": 812,  "t1y": 1621},
    "BUKIT PANJANG": {"name": "Bukit Panjang",     "region": "WEST REGION",       "bp": 478000, "c3": 2.1,  "c6": 4.0,  "c1y": 7.2,  "t3": 276,  "t6": 534,  "t1y": 1065},
    "DOWNTOWN CORE": {"name": "Central",           "region": "CENTRAL REGION",    "bp": 825000, "c3": 7.1,  "c6": 11.2, "c1y": 16.8, "t3": 48,   "t6": 91,   "t1y": 178},
    "CHOA CHU KANG": {"name": "Choa Chu Kang",     "region": "WEST REGION",       "bp": 445000, "c3": -0.8, "c6": 0.5,  "c1y": 4.2,  "t3": 312,  "t6": 601,  "t1y": 1198},
    "CLEMENTI":      {"name": "Clementi",          "region": "WEST REGION",       "bp": 638000, "c3": 4.3,  "c6": 7.8,  "c1y": 12.1, "t3": 198,  "t6": 378,  "t1y": 754},
    "GEYLANG":       {"name": "Geylang",           "region": "CENTRAL REGION",    "bp": 612000, "c3": 3.7,  "c6": 6.5,  "c1y": 10.4, "t3": 167,  "t6": 321,  "t1y": 643},
    "HOUGANG":       {"name": "Hougang",           "region": "NORTH-EAST REGION", "bp": 488000, "c3": 1.8,  "c6": 3.8,  "c1y": 7.0,  "t3": 342,  "t6": 659,  "t1y": 1312},
    "JURONG EAST":   {"name": "Jurong East",       "region": "WEST REGION",       "bp": 498000, "c3": 2.4,  "c6": 4.6,  "c1y": 8.2,  "t3": 289,  "t6": 553,  "t1y": 1102},
    "JURONG WEST":   {"name": "Jurong West",       "region": "WEST REGION",       "bp": 438000, "c3": -1.5, "c6": -0.2, "c1y": 3.8,  "t3": 567,  "t6": 1089, "t1y": 2167},
    "KALLANG":       {"name": "Kallang/Whampoa",   "region": "CENTRAL REGION",    "bp": 698000, "c3": 6.2,  "c6": 10.4, "c1y": 15.6, "t3": 234,  "t6": 449,  "t1y": 896},
    "MARINE PARADE": {"name": "Marine Parade",     "region": "EAST REGION",       "bp": 752000, "c3": 6.8,  "c6": 11.1, "c1y": 16.2, "t3": 87,   "t6": 167,  "t1y": 334},
    "PASIR RIS":     {"name": "Pasir Ris",         "region": "EAST REGION",       "bp": 512000, "c3": 2.9,  "c6": 5.4,  "c1y": 9.3,  "t3": 312,  "t6": 599,  "t1y": 1192},
    "PUNGGOL":       {"name": "Punggol",           "region": "NORTH-EAST REGION", "bp": 528000, "c3": 3.5,  "c6": 6.2,  "c1y": 10.8, "t3": 456,  "t6": 878,  "t1y": 1745},
    "QUEENSTOWN":    {"name": "Queenstown",        "region": "CENTRAL REGION",    "bp": 782000, "c3": 12.4, "c6": 17.8, "c1y": 24.6, "t3": 423,  "t6": 812,  "t1y": 1621},
    "SEMBAWANG":     {"name": "Sembawang",         "region": "NORTH REGION",      "bp": 418000, "c3": 1.2,  "c6": 2.8,  "c1y": 5.9,  "t3": 223,  "t6": 430,  "t1y": 856},
    "SENGKANG":      {"name": "Sengkang",          "region": "NORTH-EAST REGION", "bp": 518000, "c3": 2.6,  "c6": 5.0,  "c1y": 9.0,  "t3": 489,  "t6": 941,  "t1y": 1873},
    "SERANGOON":     {"name": "Serangoon",         "region": "NORTH-EAST REGION", "bp": 558000, "c3": 4.1,  "c6": 7.2,  "c1y": 11.8, "t3": 178,  "t6": 342,  "t1y": 682},
    "TAMPINES":      {"name": "Tampines",          "region": "EAST REGION",       "bp": 502000, "c3": 2.2,  "c6": 4.5,  "c1y": 8.1,  "t3": 512,  "t6": 984,  "t1y": 1956},
    "TOA PAYOH":     {"name": "Toa Payoh",         "region": "CENTRAL REGION",    "bp": 648000, "c3": 5.8,  "c6": 9.8,  "c1y": 14.9, "t3": 267,  "t6": 514,  "t1y": 1023},
    "WOODLANDS":     {"name": "Woodlands",         "region": "NORTH REGION",      "bp": 428000, "c3": -3.1, "c6": -2.4, "c1y": 2.1,  "t3": 312,  "t6": 601,  "t1y": 1196},
    "YISHUN":        {"name": "Yishun",            "region": "NORTH REGION",      "bp": 448000, "c3": 0.9,  "c6": 2.3,  "c1y": 5.4,  "t3": 398,  "t6": 765,  "t1y": 1523},
}

SUMMARIES = {
    "ANG MO KIO":    ("Ang Mo Kio is a mature estate in the north-central region, well-connected via the North-South and Circle Lines. It offers AMK Hub, multiple hawker centres, and a strong community identity.",
                      "The URA Masterplan designates Ang Mo Kio as a major commercial hub with planned town centre upgrades and improved cycling infrastructure."),
    "BEDOK":         ("Bedok is one of Singapore's largest towns, with extensive amenities and proximity to East Coast Park and Bedok Reservoir.",
                      "Planned enhancements include Bedok Town Centre rejuvenation and improved park connector links to East Coast Park."),
    "BISHAN":        ("Bishan is a centrally located premium HDB estate known for Bishan-Ang Mo Kio Park and excellent MRT connectivity. It commands some of Singapore's highest HDB resale prices.",
                      "The URA Masterplan envisions Bishan as a complementary commercial node to AMK Hub, with expanded recreational amenities along the Kallang River."),
    "BUKIT BATOK":   ("Bukit Batok is a residential town in the west known for its greenery. It is served by the North-South Line with West Mall providing major retail.",
                      "A new MRT station at Bukit Batok West under the Jurong Region Line will improve accessibility. Tengah new town development is adjacent."),
    "BUKIT MERAH":   ("Bukit Merah is a mature south-central town with excellent CBD connectivity and proximity to Vivocity and Alexandra Retail Centre.",
                      "The Greater Southern Waterfront initiative will enhance the Keppel corridor. SERS redevelopment is ongoing for older estates."),
    "BUKIT PANJANG": ("Bukit Panjang is a northwest town served by the Downtown Line and Bukit Panjang LRT, known for proximity to Bukit Timah Nature Reserve.",
                      "Improved park connector links to the Rail Corridor are planned. Hillion Mall adds commercial vibrancy."),
    "DOWNTOWN CORE": ("Central Singapore has limited HDB stock — primarily in Tanjong Pagar and Pearl's Hill — highly sought after for CBD proximity and comprehensive transport access.",
                      "The Greater Southern Waterfront and Long-Term Plan Review designate Central Singapore as a major live-work-play hub with upcoming developments in Marina South."),
    "CHOA CHU KANG": ("Choa Chu Kang is a large northwest town offering good value, served by the North-South Line and Bukit Panjang LRT. Lot One provides major retail.",
                      "The Tengah new town development brings a car-free eco-township adjacent to Choa Chu Kang. Jurong Region Line stations are planned."),
    "CLEMENTI":      ("Clementi is a mature west-side estate known for excellent educational institutions near NUS. Served by the East-West Line with Clementi Mall and West Coast Plaza.",
                      "One-North and the Jurong Innovation District are nearby. Planned Clementi Town Centre upgrades and improved cycling links are in the URA Masterplan."),
    "GEYLANG":       ("Geylang is an eclectic neighbourhood east of the CBD with good East-West Line connectivity and a rich cultural heritage of wet markets and shophouses.",
                      "URA plans for Geylang include improving residential liveability while managing its mixed-use character. Geylang River corridor redevelopment is planned."),
    "HOUGANG":       ("Hougang is a well-established northeast town served by the North-East Line with a strong community identity, wet markets, and Punggol Park proximity.",
                      "Cross Island Line infrastructure will enhance Hougang's connectivity. Home Improvement Programme upgrades and new mixed-use nodes are in progress."),
    "JURONG EAST":   ("Jurong East is a major commercial hub anchored by JCube, IMM, Westgate, and JEM, with a key MRT interchange on the East-West and North-South Lines.",
                      "The Jurong Lake District will become Singapore's second CBD, bringing significant investment including expanded commercial space and lakeside promenades."),
    "JURONG WEST":   ("Jurong West is one of Singapore's most populous towns offering wide flat-type variety at accessible prices, served by the East-West Line and Jurong Point.",
                      "The Jurong Region Line will provide enhanced connectivity across the western region, with several stations planned within Jurong West."),
    "KALLANG":       ("Kallang/Whampoa is a central-adjacent town with strong heritage character and excellent Circle Line connectivity. Home to the Singapore Sports Hub.",
                      "The Kallang Alive Masterplan envisions a sports, arts, and lifestyle precinct with new parks along the Kallang River and mixed-use waterfront developments."),
    "MARINE PARADE": ("Marine Parade is a sought-after east coast estate with limited HDB supply, excellent coastal access, and proximity to East Coast Park and Parkway Parade.",
                      "The Marine Parade MRT station on the Thomson-East Coast Line will significantly enhance accessibility. Waterfront residential and recreational developments are planned."),
    "PASIR RIS":     ("Pasir Ris is an established east town offering spacious flats and a suburban lifestyle, served by the East-West Line with Pasir Ris Park and White Sands mall.",
                      "Pasir Ris is earmarked for major urban renewal. The Cross Island Line will provide a new direct rail connection to other parts of Singapore."),
    "PUNGGOL":       ("Punggol is Singapore's newest HDB town built around an eco-waterway concept, served by the North-East Line and Punggol LRT with Waterway Point as the anchor.",
                      "Punggol Digital District, a knowledge-based economic hub, is under development. Plans include expanded waterway recreational facilities and a new polyclinic."),
    "QUEENSTOWN":    ("Queenstown is Singapore's first HDB satellite town and one of the most expensive, centrally located near NUS, one-north, and the Greater Southern Waterfront.",
                      "The Greater Southern Waterfront transformation will bring new promenades, parks, and mixed-use developments along the Keppel waterfront."),
    "SEMBAWANG":     ("Sembawang is a quiet northern town near the Johor Strait, offering relatively affordable prices. Served by the North-South Line with Sembawang Park nearby.",
                      "New mixed-use developments are planned at Canberra. The North-South Corridor expressway will improve connectivity, and commercial facilities are planned near Canberra MRT."),
    "SENGKANG":      ("Sengkang is a major north-east HDB town served by the North-East Line and Sengkang LRT. A family-oriented community with Compass One and Rivervale Mall.",
                      "The Cross Island Line will pass through Sengkang. Sengkang General Hospital expansion and new community facilities are in the pipeline."),
    "SERANGOON":     ("Serangoon offers a vibrant mix of uses centred around NEX mall with a key North-East and Circle Line interchange, near Little India and heritage shophouses.",
                      "URA plans emphasise enhancing Serangoon Town Centre and improving heritage character. Cross Island Line infrastructure nearby will enhance regional connectivity."),
    "TAMPINES":      ("Tampines is the anchor town of the east with one of Singapore's largest town centres — Tampines Mall, Century Square, and IKEA — served by the East-West Line.",
                      "The Cross Island Line will add a station at Tampines. A new Tampines North estate is under development, and Tampines Regional Centre upgrades are planned."),
    "TOA PAYOH":     ("Toa Payoh is a mature, well-connected central estate known for its HDB Hub, sports facilities, and iconic dragon playground. Strong and consistent resale demand.",
                      "Major SERS redevelopment is planned, replacing older flats with new higher-density blocks. Enhanced commercial and community facilities are part of the renewal plan."),
    "WOODLANDS":     ("Woodlands is the northern gateway with Causeway access to Johor Bahru, served by the North-South Line and hosting Causeway Point and Woodlands Regional Centre.",
                      "The Woodlands North Coast will become a live-work-play zone. The JB-Singapore Rapid Transit System (RTS Link) will open a new rail connection at Woodlands North."),
    "YISHUN":        ("Yishun is a large northern town served by the North-South Line with comprehensive amenities at Northpoint City and proximity to Lower Seletar Reservoir.",
                      "Northpoint City Phase 2 has added significant retail and community space. Enhanced park connector links and new mixed-use developments near Yishun MRT are planned."),
}

MOST_EXP = {
    "ANG MO KIO":    ("Blk 574 Ang Mo Kio Ave 3", "5-Room",    "21 to 25", 920000,  "Dec 2025"),
    "BEDOK":         ("Blk 134 Bedok North Ave 3", "Executive", "16 to 20", 988000,  "Nov 2025"),
    "BISHAN":        ("Blk 270 Bishan St 24",      "5-Room",    "21 to 25", 1180000, "Dec 2025"),
    "BUKIT BATOK":   ("Blk 665 Bukit Batok W Ave 6","Executive","11 to 15", 778000,  "Nov 2025"),
    "BUKIT MERAH":   ("Blk 1 Jalan Bukit Merah",   "Executive", "21 to 25", 1320000, "Dec 2025"),
    "BUKIT PANJANG": ("Blk 508 Jelapang Rd",       "Executive", "16 to 20", 798000,  "Nov 2025"),
    "DOWNTOWN CORE": ("Blk 1 Cantonment Rd",       "4-Room",    "26 to 30", 1480000, "Dec 2025"),
    "CHOA CHU KANG": ("Blk 693 Choa Chu Kang Cres","Executive", "16 to 20", 738000,  "Oct 2025"),
    "CLEMENTI":      ("Blk 411 Clementi Ave 1",    "5-Room",    "21 to 25", 1050000, "Dec 2025"),
    "GEYLANG":       ("Blk 14 Geylang Lor 3",      "5-Room",    "21 to 25", 980000,  "Nov 2025"),
    "HOUGANG":       ("Blk 682 Hougang Ave 4",     "Executive", "16 to 20", 848000,  "Dec 2025"),
    "JURONG EAST":   ("Blk 240 Jurong East St 24", "5-Room",    "21 to 25", 878000,  "Nov 2025"),
    "JURONG WEST":   ("Blk 726 Jurong W St 71",    "Executive", "16 to 20", 758000,  "Dec 2025"),
    "KALLANG":       ("Blk 11 Whampoa Dr",         "5-Room",    "21 to 25", 1150000, "Dec 2025"),
    "MARINE PARADE": ("Blk 36 Marine Crescent",    "Executive", "16 to 20", 1280000, "Nov 2025"),
    "PASIR RIS":     ("Blk 789 Pasir Ris Dr 10",   "Executive", "16 to 20", 868000,  "Dec 2025"),
    "PUNGGOL":       ("Blk 412 Punggol Place",     "5-Room",    "16 to 20", 898000,  "Dec 2025"),
    "QUEENSTOWN":    ("Blk 1 Queens Rd",           "5-Room",    "26 to 30", 1560000, "Dec 2025"),
    "SEMBAWANG":     ("Blk 367 Sembawang Cres",    "Executive", "11 to 15", 728000,  "Nov 2025"),
    "SENGKANG":      ("Blk 322 Compassvale Bow",   "5-Room",    "16 to 20", 928000,  "Dec 2025"),
    "SERANGOON":     ("Blk 415 Serangoon Ave 1",   "5-Room",    "21 to 25", 968000,  "Dec 2025"),
    "TAMPINES":      ("Blk 872 Tampines St 84",    "Executive", "16 to 20", 908000,  "Nov 2025"),
    "TOA PAYOH":     ("Blk 190 Lor 6 Toa Payoh",  "5-Room",    "21 to 25", 1080000, "Dec 2025"),
    "WOODLANDS":     ("Blk 688 Woodlands Dr 75",   "Executive", "16 to 20", 748000,  "Nov 2025"),
    "YISHUN":        ("Blk 679 Yishun Ave 4",      "Executive", "16 to 20", 768000,  "Dec 2025"),
}

QUARTERS = ["2024 Q1","2024 Q2","2024 Q3","2024 Q4","2025 Q1","2025 Q2","2025 Q3","2025 Q4"]
FLAT_TYPE_OFFSETS = {"3-Room": 0.64, "4-Room": 0.94, "5-Room": 1.15, "Executive": 1.36}
COLORS = {"3-Room": "#3B82F6", "4-Room": "#1C4ED8", "5-Room": "#16A34A", "Executive": "#D97706"}

# ── Data helpers ──────────────────────────────────────────────
def get_town_df(period, layer):
    rows = []
    chg_key = {"3m": "c3", "6m": "c6", "1y": "c1y"}[period]
    txn_key = {"3m": "t3", "6m": "t6", "1y": "t1y"}[period]
    for pln, td in TOWNS.items():
        bp = td["bp"]
        chg = td[chg_key]
        txn = td[txn_key]
        prev_bp = round(bp / (1 + chg / 100))
        txn_prev = round(txn / 1.09)
        txn_chg = round((txn - txn_prev) / txn_prev * 100, 1)
        psf = round(bp / 850)
        if layer == "price_change":
            val = chg
        elif layer == "txn_change":
            val = txn_chg
        elif layer == "median_price":
            val = bp / 1000  # in $K for display
        else:  # median_psf
            val = psf
        rows.append({"PLN_AREA_N": pln, "value": val, "town_name": td["name"]})
    return pd.DataFrame(rows)


def make_choropleth(period="3m", layer="price_change"):
    df = get_town_df(period, layer)

    layer_meta = {
        "price_change":  {"title": "Price Change (%)",       "scale": "RdYlGn", "fmt": ".1f"},
        "txn_change":    {"title": "Txn Count Change (%)",   "scale": "RdYlGn", "fmt": ".1f"},
        "median_price":  {"title": "Median Price ($K)",       "scale": "Blues",  "fmt": ".0f"},
        "median_psf":    {"title": "Median Price / sqft ($)", "scale": "Blues",  "fmt": ".0f"},
    }
    meta = layer_meta[layer]

    fig = px.choropleth_mapbox(
        df,
        geojson=GEOJSON,
        locations="PLN_AREA_N",
        featureidkey="properties.PLN_AREA_N",
        color="value",
        color_continuous_scale=meta["scale"],
        mapbox_style="carto-positron",
        zoom=10.2,
        center={"lat": 1.352, "lon": 103.82},
        opacity=0.75,
        hover_name="town_name",
        hover_data={"value": f":.{meta['fmt'][-1]}f", "PLN_AREA_N": False},
        labels={"value": meta["title"]},
    )
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(
            title=dict(text=meta["title"], font=dict(size=11, color="#6B7280")),
            thicknessmode="pixels", thickness=12,
            lenmode="fraction", len=0.5,
            x=0.01, xanchor="left",
            y=0.02, yanchor="bottom",
            tickfont=dict(size=11, color="#6B7280"),
        ),
    )
    fig.update_traces(marker_line_width=0.8, marker_line_color="#fff")
    return fig


def make_trend_chart(pln_area):
    td = TOWNS.get(pln_area)
    bp = td["bp"] if td else 548000
    traces = []
    for ft, offset in FLAT_TYPE_OFFSETS.items():
        end_price = bp * offset
        # 7 quarters back with ~1.5% growth per quarter
        prices = [round(end_price / (1.015 ** (7 - i))) for i in range(8)]
        traces.append(go.Scatter(
            x=QUARTERS, y=prices, name=ft,
            line=dict(color=COLORS[ft], width=2),
            mode="lines+markers",
            marker=dict(size=4),
        ))
    fig = go.Figure(data=traces)
    fig.update_layout(
        margin={"r": 8, "t": 8, "l": 8, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.2, x=0, font=dict(size=11)),
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#9CA3AF"),
                   tickangle=-30, linecolor="#E5E7EB"),
        yaxis=dict(showgrid=True, gridcolor="#F3F4F6",
                   tickformat="$,.0f", tickfont=dict(size=10, color="#9CA3AF"),
                   zeroline=False),
        height=200,
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def stats_panel_content(pln_area=None, period="3m"):
    chg_key = {"3m": "c3", "6m": "c6", "1y": "c1y"}[period]
    txn_key = {"3m": "t3", "6m": "t6", "1y": "t1y"}[period]

    if pln_area and pln_area in TOWNS:
        td = TOWNS[pln_area]
        name = td["name"]
        region = td["region"]
        bp = td["bp"]
        chg = td[chg_key]
        txn = td[txn_key]
        psf = round(bp / 850)
        summary_txt, dev_txt = SUMMARIES.get(pln_area, ("No summary available.", "No developments data."))
        me = MOST_EXP.get(pln_area)
    else:
        # National defaults
        name = "National Overview"
        region = "ALL REGIONS"
        bp = 548000
        chg = 5.2
        txn = 7842
        psf = 645
        summary_txt = "Singapore HDB resale market overview. Select a town on the map for town-specific statistics."
        dev_txt = "National-level planning includes the Long-Term Plan Review, Greater Southern Waterfront, and the Rail Corridor enhancement."
        me = None
        pln_area = None

    prev_bp = round(bp / (1 + chg / 100))
    prev_psf = round(psf / (1 + chg / 100))
    chg_class = "stat-change positive" if chg >= 0 else "stat-change negative"
    chg_arrow = "↑" if chg >= 0 else "↓"

    return html.Div([
        # Header
        html.Div(className="stats-panel-header", children=[
            html.P(name, className="stats-panel-town"),
            html.P(region, className="stats-panel-region"),
        ]),
        html.Div(className="stats-panel-body", children=[
            # 2×2 stat grid
            html.Div(className="stats-grid-2", children=[
                html.Div(className="stats-mini-card", children=[
                    html.P("MEDIAN PRICE", className="stats-mini-label"),
                    html.P(f"${bp:,.0f}", className="stats-mini-value"),
                    html.P([
                        html.Span(f"{chg_arrow} {abs(chg):.1f}%", className=chg_class),
                    ], style={"fontSize": "12px", "marginTop": "3px"}),
                ]),
                html.Div(className="stats-mini-card", children=[
                    html.P("MEDIAN PSF", className="stats-mini-label"),
                    html.P(f"${psf:,.0f}", className="stats-mini-value"),
                    html.P(f"vs ${prev_psf:,.0f} prev", style={"fontSize": "11px", "color": "var(--color-text-muted)", "marginTop": "3px"}),
                ]),
                html.Div(className="stats-mini-card", children=[
                    html.P("TRANSACTIONS", className="stats-mini-label"),
                    html.P(f"{txn:,}", className="stats-mini-value"),
                    html.P(f"Past {period}", style={"fontSize": "11px", "color": "var(--color-text-muted)", "marginTop": "3px"}),
                ]),
                html.Div(className="stats-mini-card", children=[
                    html.P("PREV PERIOD PRICE", className="stats-mini-label"),
                    html.P(f"${prev_bp:,.0f}", className="stats-mini-value"),
                    html.P("Reference period", style={"fontSize": "11px", "color": "var(--color-text-muted)", "marginTop": "3px"}),
                ]),
            ]),

            # Price trend chart
            html.Div(className="chart-section", children=[
                html.P("PRICE TREND BY FLAT TYPE", className="chart-section-label"),
                dcc.Graph(
                    figure=make_trend_chart(pln_area),
                    config={"displayModeBar": False},
                    style={"height": "200px"},
                ),
            ]),

            # Most expensive flat
            html.Div(className="most-expensive-card", children=[
                html.P("MOST EXPENSIVE RECENT TRANSACTION", className="me-label"),
                *([
                    html.P(f"${me[3]:,.0f}", className="me-price"),
                    html.P(me[0], className="me-addr"),
                    html.P(f"{me[1]}  ·  Storey {me[2]}  ·  {me[4]}", className="me-meta"),
                ] if me else [html.P("—", className="me-price")]),
            ]),

            # Town summary
            html.Div(className="town-summary-section", children=[
                html.P("ABOUT THIS TOWN", className="chart-section-label"),
                html.P(summary_txt, className="town-summary-text"),
            ]),

            # Developments
            html.Div(className="developments-section", children=[
                html.P("NOTABLE DEVELOPMENTS", className="developments-label"),
                html.P(dev_txt, className="developments-text"),
            ]),
        ]),
    ])


# ── Layout ────────────────────────────────────────────────────
layout = html.Div(className="market-page", children=[

    # Left: map
    html.Div(className="map-panel", children=[
        html.Div(className="map-controls", children=[
            dcc.Dropdown(
                id="map-layer",
                options=[
                    {"label": "Price Change %",          "value": "price_change"},
                    {"label": "Transaction Count Change %","value": "txn_change"},
                    {"label": "Median Price",            "value": "median_price"},
                    {"label": "Median Price / sqft",     "value": "median_psf"},
                ],
                value="price_change",
                clearable=False,
                className="form-select",
                style={"width": "230px", "fontSize": "13px"},
            ),
            dcc.RadioItems(
                id="map-period",
                options=[
                    {"label": "3 Months", "value": "3m"},
                    {"label": "6 Months", "value": "6m"},
                    {"label": "1 Year",   "value": "1y"},
                ],
                value="3m",
                inline=True,
                className="dash-period-toggle",
                inputStyle={"display": "none"},
                labelStyle={"fontSize": "12px", "fontWeight": "600", "padding": "5px 14px",
                            "borderRadius": "16px", "cursor": "pointer"},
            ),
        ]),
        dcc.Graph(
            id="choropleth-map",
            figure=make_choropleth("3m", "price_change"),
            config={"displayModeBar": False, "scrollZoom": True},
            style={"height": "100%", "width": "100%"},
        ),
    ]),

    # Right: stats panel
    html.Div(id="stats-panel", className="stats-panel",
             children=stats_panel_content(None, "3m")),
])


# ── Callbacks ─────────────────────────────────────────────────

@callback(
    Output("choropleth-map", "figure"),
    Input("map-period", "value"),
    Input("map-layer", "value"),
)
def update_map(period, layer):
    return make_choropleth(period, layer)


@callback(
    Output("stats-panel", "children"),
    Input("choropleth-map", "clickData"),
    Input("map-period", "value"),
)
def update_stats_panel(click_data, period):
    pln_area = None
    if click_data:
        pts = click_data.get("points", [])
        if pts:
            pln_area = pts[0].get("location")
    return stats_panel_content(pln_area, period)
