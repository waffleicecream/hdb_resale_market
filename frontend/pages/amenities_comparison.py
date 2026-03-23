"""
Flat Amenities Comparison page.
Up to 3 postal codes → side-by-side amenity matrix with best-value highlighting.
"""
import json
import dash
from dash import dcc, html, Input, Output, State, callback, ALL
import dash_bootstrap_components as dbc

from .amenities_mock_data import MOCK_DATA

dash.register_page(
    __name__,
    path="/amenities-comparison",
    name="Amenities Comparison",
    title="Flat Amenities",
)

# ── Layout ────────────────────────────────────────────────────────────────────
layout = html.Div(
    [
        # Page header
        html.Div(
            [
                html.Div("Flat Amenities Comparison", className="page-header-title"),
                html.Div(
                    "Compare up to 3 shortlisted flats across MRT, mall, hawker, "
                    "sports hall, polyclinic, schools, and parks.",
                    className="page-header-sub",
                ),
            ],
            className="mb-4",
        ),

        # Input row
        dbc.Row(
            dbc.Col(
                [
                    html.Div(
                        [
                            dbc.InputGroup(
                                [
                                    dbc.Input(
                                        id="ac-postal-input",
                                        placeholder="Enter 6-digit postal code",
                                        type="text",
                                        maxLength=6,
                                        style={"maxWidth": "260px",
                                               "background": "#e5e6ff",
                                               "border": "none",
                                               "borderRadius": "8px 0 0 8px"},
                                    ),
                                    dbc.Button(
                                        [html.I(className="bi bi-plus-lg me-1"), "Add Flat"],
                                        id="ac-add-btn",
                                        className="btn-cta",
                                        style={"borderRadius": "0 8px 8px 0"},
                                    ),
                                ],
                                className="mb-1",
                            ),
                            html.Div(
                                id="ac-input-error",
                                style={"fontSize": "0.78rem", "color": "#e74c3c",
                                       "marginTop": "0.3rem"},
                            ),
                        ],
                        className="surface-form",
                    ),

                    # Available postal code hint
                    html.Div(
                        [
                            html.I(className="bi bi-lightbulb me-1",
                                   style={"color": "#5bc8af"}),
                            html.Span(
                                "Try: 560123 · 310078 · 820201 · 650221 · 530151 · 730418 · 380033",
                                style={"fontSize": "0.72rem", "color": "#454652"},
                            ),
                        ],
                        className="mt-2",
                    ),
                ],
                md=8,
            ),
            justify="start",
            className="mb-3",
        ),

        # Max-3 warning
        dbc.Alert(
            [html.I(className="bi bi-info-circle me-2"),
             "Maximum of 3 flats can be compared at once."],
            id="ac-max-warning",
            color="warning",
            is_open=False,
            className="py-2 mb-3",
            style={"maxWidth": "440px", "fontSize": "0.82rem"},
        ),

        # Comparison table
        html.Div(id="ac-table-container", className="table-responsive pb-4"),

        # State store
        dcc.Store(id="ac-flats-store", data=[]),
    ],
    className="container-fluid px-3 py-3",
    style={"backgroundColor": "#fbf8ff", "minHeight": "calc(100vh - 64px)"},
)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _walk_mins(dist_m):
    return round(dist_m / 1000 * 20)


def _find_best_indices(values, lower_is_better=True):
    valid = [(i, v) for i, v in enumerate(values) if v is not None]
    if not valid:
        return set()
    best_val = min(v for _, v in valid) if lower_is_better else max(v for _, v in valid)
    return {i for i, v in valid if v == best_val}


def _header_cell(postal, data):
    return html.Th(
        [
            html.Div(
                f"Blk {data['block']}",
                style={"fontFamily": "'Manrope', sans-serif",
                       "fontWeight": "700", "fontSize": "1rem", "color": "#ffffff"},
            ),
            html.Div(data["street"],
                     style={"fontSize": "0.78rem", "color": "rgba(255,255,255,0.70)",
                             "marginTop": "0.1rem"}),
            html.Div(postal,
                     style={"fontSize": "0.72rem", "color": "rgba(255,255,255,0.50)"}),
            dbc.Button(
                [html.I(className="bi bi-x-lg me-1"), "Remove"],
                id={"type": "ac-remove-btn", "index": postal},
                size="sm",
                color="light",
                outline=True,
                className="mt-2",
                style={"fontSize": "0.72rem", "padding": "0.2rem 0.6rem",
                       "borderColor": "rgba(255,255,255,0.30)",
                       "color": "rgba(255,255,255,0.75)"},
            ),
        ],
        className="text-center ac-flat-col",
    )


def _section_header_row(label, n_flats):
    return html.Tr(
        html.Td(
            label,
            colSpan=1 + n_flats,
            # Literal hex — var() does not work in inline Dash style dicts
            style={"backgroundColor": "#00145d", "color": "#ffffff",
                   "fontFamily": "'Manrope', sans-serif", "fontWeight": "700",
                   "fontSize": "0.70rem", "letterSpacing": "0.07em",
                   "textTransform": "uppercase", "padding": "0.5rem 1rem"},
        ),
        className="ac-section-header",
    )


def _amenity_cell(amenity_dict, is_best):
    if amenity_dict is None:
        return html.Td(
            html.Span("No amenity found",
                      style={"fontSize": "0.78rem", "color": "#454652",
                             "fontStyle": "italic"}),
            className="ac-cell text-center",
        )

    dist_m  = amenity_dict["dist_m"]
    dist_km = dist_m / 1000
    walk    = _walk_mins(dist_m)
    cell_cls = "ac-cell text-center ac-best" if is_best else "ac-cell text-center"

    return html.Td(
        [
            html.Div(
                [
                    html.Span(
                        f"{dist_km:.1f} km",
                        style={"fontFamily": "'Manrope', sans-serif",
                               "fontWeight": "700", "fontSize": "0.92rem"},
                    ),
                    html.Span(
                        f" · {walk} min walk",
                        style={"fontSize": "0.75rem", "color": "#454652"},
                    ),
                    dbc.Badge("Best", color="success", className="ms-2",
                              style={"fontSize": "0.62rem"}) if is_best else "",
                ],
                className="mb-1",
            ),
            html.Div(amenity_dict["name"],
                     style={"fontSize": "0.78rem", "color": "#454652"}),
        ],
        className=cell_cls,
    )


def _count_cell(name_list, is_best, tip_id):
    count   = len(name_list)
    visible = name_list[:5]
    overflow = name_list[5:]

    items = [html.Li(n, style={"fontSize": "0.78rem"}) for n in visible]
    extras = []
    if overflow:
        extras.append(
            html.Span(
                f"+{len(overflow)} more",
                id=tip_id,
                style={"color": "#00145d", "fontSize": "0.75rem",
                       "cursor": "pointer", "textDecoration": "underline"},
            )
        )
        extras.append(dbc.Tooltip(", ".join(overflow), target=tip_id, placement="top"))

    cell_cls = "ac-cell ac-best" if is_best else "ac-cell"
    return html.Td(
        [
            html.Div(
                [
                    html.Strong(str(count),
                                style={"fontFamily": "'Manrope', sans-serif",
                                       "fontWeight": "800", "fontSize": "1.1rem"}),
                    dbc.Badge("Best", color="success", className="ms-2",
                              style={"fontSize": "0.62rem"}) if is_best else "",
                ]
            ),
            html.Ul(items, style={"paddingLeft": "1rem", "margin": "0.4rem 0 0"})
            if items else html.Span("None", style={"fontSize": "0.78rem", "color": "#454652"}),
            *extras,
        ],
        className=cell_cls,
    )


def _amenity_row(label, key, flats_data, best_indices):
    cells = [html.Td(label, className="ac-metric-col")]
    for i, data in enumerate(flats_data):
        cells.append(_amenity_cell(data[key], i in best_indices))
    return html.Tr(cells)


def _count_row(label, key, flats_data, best_indices):
    cells = [html.Td(label, className="ac-metric-col")]
    for i, data in enumerate(flats_data):
        tip_id = f"ac-tip-{key}-{data['postal_code']}"
        cells.append(_count_cell(data[key], i in best_indices, tip_id))
    return html.Tr(cells)


def _build_table(flats):
    flats_data = [MOCK_DATA[p] for p in flats]
    n = len(flats_data)
    show_best = n > 1

    def _best(key, lower):
        if not show_best:
            return set()
        values = [d[key]["dist_m"] if d[key] else None for d in flats_data]
        return _find_best_indices(values, lower_is_better=lower)

    def _best_count(key):
        if not show_best:
            return set()
        values = [len(d[key]) for d in flats_data]
        return _find_best_indices(values, lower_is_better=False)

    header_row = html.Tr(
        [html.Th("Amenity", className="ac-metric-col",
                 style={"backgroundColor": "#00145d", "color": "rgba(255,255,255,0.70)",
                        "fontSize": "0.68rem", "fontWeight": "700",
                        "textTransform": "uppercase", "letterSpacing": "0.07em"})]
        + [_header_cell(p, MOCK_DATA[p]) for p in flats]
    )

    tbody_rows = [
        _section_header_row("Nearest Amenities", n),
        _amenity_row("MRT Station",           "nearest_mrt",         flats_data, _best("nearest_mrt",         True)),
        _amenity_row("Shopping Mall",         "nearest_mall",        flats_data, _best("nearest_mall",        True)),
        _amenity_row("Sports Hall",           "nearest_sports_hall", flats_data, _best("nearest_sports_hall", True)),
        _amenity_row("Polyclinic / Hospital", "nearest_polyclinic",  flats_data, _best("nearest_polyclinic",  True)),
        _amenity_row("Hawker Centre",         "nearest_hawker",      flats_data, _best("nearest_hawker",      True)),
        _section_header_row("Within 1 km", n),
        _count_row("Primary Schools",         "primary_schools_1km", flats_data, _best_count("primary_schools_1km")),
        _count_row("Parks",                   "parks_1km",           flats_data, _best_count("parks_1km")),
    ]

    return html.Table(
        [html.Thead(header_row), html.Tbody(tbody_rows)],
        className="table ac-comparison-table w-100",
    )


# ── Empty state ───────────────────────────────────────────────────────────────
def _empty_state():
    return html.Div(
        [
            html.I(className="bi bi-geo-alt",
                   style={"fontSize": "3rem", "color": "#5bc8af", "opacity": "0.45"}),
            html.P(
                "Enter a postal code above to start comparing flats.",
                className="mt-3 mb-1",
                style={"color": "#454652", "fontSize": "0.90rem"},
            ),
            html.P(
                "Try: 560123 · 310078 · 820201",
                style={"fontSize": "0.78rem", "color": "#8a8a9a"},
            ),
        ],
        style={
            "display": "flex", "flexDirection": "column",
            "alignItems": "center", "justifyContent": "center",
            "minHeight": "280px", "padding": "2rem",
            "background": "#f4f2ff", "borderRadius": "12px",
        },
    )


# ── Callbacks ─────────────────────────────────────────────────────────────────
@callback(
    Output("ac-flats-store",  "data"),
    Output("ac-input-error",  "children"),
    Output("ac-postal-input", "value"),
    Input("ac-add-btn",       "n_clicks"),
    Input({"type": "ac-remove-btn", "index": ALL}, "n_clicks"),
    State("ac-postal-input",  "value"),
    State("ac-flats-store",   "data"),
    prevent_initial_call=True,
)
def manage_flats(add_clicks, remove_clicks, postal_input, current_flats):
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_flats, "", dash.no_update

    trigger_id = ctx.triggered[0]["prop_id"]

    if "ac-add-btn" in trigger_id:
        postal = (postal_input or "").strip()
        if not postal:
            return current_flats, "", dash.no_update
        if postal not in MOCK_DATA:
            return current_flats, f'"{postal}" not found. Try one of the suggested codes.', postal_input
        if postal in current_flats:
            return current_flats, "This flat is already in the comparison.", postal_input
        if len(current_flats) >= 3:
            return current_flats, "", postal_input
        return current_flats + [postal], "", ""

    try:
        prop = json.loads(trigger_id.split(".")[0])
        postal_to_remove = prop["index"]
        updated = [p for p in current_flats if p != postal_to_remove]
        return updated, "", dash.no_update
    except Exception:
        return current_flats, "", dash.no_update


@callback(
    Output("ac-table-container", "children"),
    Output("ac-max-warning",     "is_open"),
    Output("ac-add-btn",         "disabled"),
    Output("ac-postal-input",    "disabled"),
    Input("ac-flats-store",      "data"),
)
def render_table(flats):
    at_max = len(flats) >= 3
    if not flats:
        return _empty_state(), False, False, False
    return _build_table(flats), at_max, at_max, at_max
