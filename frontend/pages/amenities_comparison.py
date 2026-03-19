import json
import dash
from dash import dcc, html, Input, Output, State, callback, ALL
import dash_bootstrap_components as dbc

from .amenities_mock_data import MOCK_DATA

dash.register_page(
    __name__,
    path="/amenities-comparison",
    name="Amenities Comparison",
    title="Amenities Comparison",
)

# ── Layout ────────────────────────────────────────────────────────────────────

layout = html.Div(
    [
        html.H4("Flat Amenities Comparison", className="fw-bold text-center my-3"),

        # Input row
        dbc.Row(
            dbc.Col(
                [
                    dbc.InputGroup(
                        [
                            dbc.Input(
                                id="ac-postal-input",
                                placeholder="Enter 6-digit postal code",
                                type="text",
                                maxLength=6,
                                style={"maxWidth": "260px"},
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-plus-lg me-1"), "Add Flat"],
                                id="ac-add-btn",
                                color="success",
                            ),
                        ],
                        className="mb-1",
                    ),
                    html.Div(id="ac-input-error", className="text-danger small"),
                ],
                md=6,
            ),
            justify="center",
            className="mb-2",
        ),

        # Max-3 warning
        dbc.Alert(
            [html.I(className="bi bi-info-circle me-2"), "Maximum of 3 flats compared."],
            id="ac-max-warning",
            color="warning",
            is_open=False,
            className="text-center small py-2 mx-auto",
            style={"maxWidth": "480px"},
        ),

        # Comparison table (rendered by callback)
        html.Div(id="ac-table-container", className="table-responsive px-2 pb-4"),

        # State store: list of postal code strings, max 3
        dcc.Store(id="ac-flats-store", data=[]),
    ],
    className="container-fluid px-3 py-2",
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _walk_mins(dist_m):
    """Convert metres to walking minutes at 1 km = 20 mins."""
    return round(dist_m / 1000 * 20)


def _find_best_indices(values, lower_is_better=True):
    """
    Return the set of indices that share the tied-best value.
    None values are excluded. Returns empty set if all values are None.
    """
    valid = [(i, v) for i, v in enumerate(values) if v is not None]
    if not valid:
        return set()
    best_val = min(v for _, v in valid) if lower_is_better else max(v for _, v in valid)
    return {i for i, v in valid if v == best_val}


def _header_cell(postal, data):
    return html.Th(
        [
            html.Div(f"Blk {data['block']}", className="fw-bold"),
            html.Div(data["street"], className="small text-muted"),
            html.Div(postal, className="small text-muted"),
            dbc.Button(
                [html.I(className="bi bi-x-lg me-1"), "Remove"],
                id={"type": "ac-remove-btn", "index": postal},
                size="sm",
                color="danger",
                outline=True,
                className="mt-2",
            ),
        ],
        className="text-center ac-flat-col",
    )


def _section_header_row(label, n_flats):
    return html.Tr(
        html.Td(
            label,
            colSpan=1 + n_flats,
            className="fw-bold small text-uppercase text-white py-1 px-2",
            style={"backgroundColor": "#5bc8af", "letterSpacing": "0.06em"},
        ),
        className="ac-section-header",
    )


def _amenity_cell(amenity_dict, is_best):
    if amenity_dict is None:
        return html.Td(
            html.Span("No amenity found", className="text-muted small fst-italic"),
            className="ac-cell text-center",
        )

    dist_m = amenity_dict["dist_m"]
    dist_km = dist_m / 1000
    walk = _walk_mins(dist_m)

    cell_class = "ac-cell text-center ac-best" if is_best else "ac-cell text-center"
    return html.Td(
        [
            html.Div(
                [
                    html.Span(f"{dist_km:.1f} km | {walk} min"),
                    dbc.Badge("Best", color="success", className="ms-2") if is_best else "",
                ],
                className="fw-semibold",
            ),
            html.Div(amenity_dict["name"], className="small text-muted"),
        ],
        className=cell_class,
    )


def _count_cell(name_list, is_best, tip_id):
    count = len(name_list)
    visible = name_list[:5]
    overflow = name_list[5:]

    items = [html.Li(n, className="small") for n in visible]

    extras = []
    if overflow:
        extras.append(
            html.Span(
                f"+{len(overflow)} more",
                id=tip_id,
                className="text-primary small",
                style={"cursor": "pointer", "textDecoration": "underline"},
            )
        )
        extras.append(
            dbc.Tooltip(
                ", ".join(overflow),
                target=tip_id,
                placement="top",
            )
        )

    cell_class = "ac-cell ac-best" if is_best else "ac-cell"
    return html.Td(
        [
            html.Div(
                [
                    html.Strong(str(count)),
                    dbc.Badge("Best", color="success", className="ms-2") if is_best else "",
                ]
            ),
            html.Ul(items, className="ps-3 mb-0 mt-1") if items else html.Span("None", className="text-muted small"),
            *extras,
        ],
        className=cell_class,
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
    """Assemble the full comparison html.Table from a list of postal code strings."""
    flats_data = [MOCK_DATA[p] for p in flats]
    n = len(flats_data)
    show_best = n > 1  # best highlighting only meaningful with ≥ 2 flats

    # Best indices per metric
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
        [html.Th("Metric", className="ac-metric-col")]
        + [_header_cell(p, MOCK_DATA[p]) for p in flats]
    )

    tbody_rows = [
        _section_header_row("Nearest Amenities", n),
        _amenity_row("MRT Station",           "nearest_mrt",          flats_data, _best("nearest_mrt",         True)),
        _amenity_row("Mall",                  "nearest_mall",         flats_data, _best("nearest_mall",        True)),
        _amenity_row("Sports Hall",           "nearest_sports_hall",  flats_data, _best("nearest_sports_hall", True)),
        _amenity_row("Polyclinic / Hospital", "nearest_polyclinic",   flats_data, _best("nearest_polyclinic",  True)),
        _amenity_row("Hawker Centre",         "nearest_hawker",       flats_data, _best("nearest_hawker",      True)),
        _section_header_row("Within 1 km", n),
        _count_row("Primary Schools",         "primary_schools_1km",  flats_data, _best_count("primary_schools_1km")),
        _count_row("Parks",                   "parks_1km",            flats_data, _best_count("parks_1km")),
    ]

    return html.Table(
        [
            html.Thead(header_row),
            html.Tbody(tbody_rows),
        ],
        className="table table-bordered ac-comparison-table w-100",
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

    # ── Add flat ──
    if "ac-add-btn" in trigger_id:
        postal = (postal_input or "").strip()
        if not postal:
            return current_flats, "", dash.no_update
        if postal not in MOCK_DATA:
            return current_flats, "Postal code not found.", postal_input
        if postal in current_flats:
            return current_flats, "This flat is already added.", postal_input
        if len(current_flats) >= 3:
            return current_flats, "", postal_input
        return current_flats + [postal], "", ""

    # ── Remove flat ──
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
        placeholder = html.P(
            [
                html.I(className="bi bi-arrow-up me-2"),
                "Enter a 6-digit postal code above to start comparing flats.",
            ],
            className="text-muted text-center mt-4",
        )
        return placeholder, False, False, False

    table = _build_table(flats)
    return table, at_max, at_max, at_max
