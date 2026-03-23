# amenities_mock_data.py
# Mock dataset for the Flat Amenities Comparison page.
# Uses realistic-looking Singapore addresses and amenity names but is demo/mock data only.
# dist_m values are approximate walking distances in metres.
# None values exercise the "No amenity found" display path.

MOCK_DATA = {
    # ── Ang Mo Kio ──────────────────────────────────────────────────────────────
    "560123": {
        "block": "123",
        "street": "Ang Mo Kio Ave 3",
        "postal_code": "560123",
        "nearest_mrt":          {"name": "Ang Mo Kio MRT",              "dist_m": 420},
        "nearest_mall":         {"name": "AMK Hub",                     "dist_m": 510},
        "nearest_sports_hall":  {"name": "Ang Mo Kio CC Sports Hall",   "dist_m": 880},
        "nearest_polyclinic":   {"name": "Ang Mo Kio Polyclinic",       "dist_m": 650},
        "nearest_hawker":       {"name": "AMK 628 Hawker Centre",       "dist_m": 230},
        "primary_schools_1km":  [
            "CHIJ St Nicholas Girls' School",
            "Mayflower Primary School",
            "Ang Mo Kio Primary School",
        ],
        "parks_1km": [
            "Bishan-Ang Mo Kio Park",
            "AMK Town Garden",
        ],
    },

    # ── Choa Chu Kang ────────────────────────────────────────────────────────────
    "650221": {
        "block": "221",
        "street": "Choa Chu Kang Ave 1",
        "postal_code": "650221",
        "nearest_mrt":          {"name": "Choa Chu Kang MRT",           "dist_m": 310},
        "nearest_mall":         {"name": "Lot One Shoppers' Mall",      "dist_m": 370},
        "nearest_sports_hall":  {"name": "Choa Chu Kang Sports Hall",   "dist_m": 950},
        "nearest_polyclinic":   {"name": "Choa Chu Kang Polyclinic",    "dist_m": 820},
        "nearest_hawker":       {"name": "CCK 302 Hawker Centre",       "dist_m": 480},
        "primary_schools_1km":  [
            "Yew Tee Primary School",
            "Choa Chu Kang Primary School",
        ],
        "parks_1km": [
            "Choa Chu Kang Park",
        ],
    },

    # ── Woodlands ────────────────────────────────────────────────────────────────
    "730418": {
        "block": "418",
        "street": "Woodlands Ave 6",
        "postal_code": "730418",
        "nearest_mrt":          {"name": "Woodlands MRT",               "dist_m": 560},
        "nearest_mall":         {"name": "Causeway Point",              "dist_m": 620},
        "nearest_sports_hall":  {"name": "Woodlands Sports Hall",       "dist_m": 1100},
        "nearest_polyclinic":   {"name": "Woodlands Polyclinic",        "dist_m": 740},
        "nearest_hawker":       {"name": "Woodlands 888 Plaza Hawker",  "dist_m": 390},
        "primary_schools_1km":  [
            "Woodlands Primary School",
            "Innova Primary School",
            "Si Ling Primary School",
            "Fuchun Primary School",
            "Woodgrove Primary School",
            "Admiralty Primary School",
        ],
        "parks_1km": [
            "Woodlands Waterfront Park",
            "Woodlands Town Garden",
            "Republic Polytechnic Green",
        ],
    },

    # ── Geylang ──────────────────────────────────────────────────────────────────
    "380033": {
        "block": "33",
        "street": "Geylang Bahru",
        "postal_code": "380033",
        "nearest_mrt":          {"name": "Kallang MRT",                 "dist_m": 750},
        "nearest_mall":         {"name": "City Square Mall",            "dist_m": 1400},
        "nearest_sports_hall":  {"name": "Geylang CC Sports Hall",      "dist_m": 680},
        "nearest_polyclinic":   {"name": "Geylang Polyclinic",          "dist_m": 910},
        "nearest_hawker":       {"name": "Geylang Serai Market",        "dist_m": 190},
        "primary_schools_1km":  [
            "Geylang Methodist School (Primary)",
            "Macpherson Primary School",
        ],
        "parks_1km": [
            "Geylang Park Connector",
        ],
    },

    # ── Serangoon ────────────────────────────────────────────────────────────────
    "530151": {
        "block": "151",
        "street": "Serangoon Ave 2",
        "postal_code": "530151",
        "nearest_mrt":          {"name": "Serangoon MRT",               "dist_m": 480},
        "nearest_mall":         {"name": "NEX",                         "dist_m": 530},
        "nearest_sports_hall":  {"name": "Serangoon CC Sports Hall",    "dist_m": 720},
        "nearest_polyclinic":   {"name": "Serangoon Polyclinic",        "dist_m": 590},
        "nearest_hawker":       {"name": "Serangoon 212 Hawker Centre", "dist_m": 260},
        "primary_schools_1km":  [
            "Zhonghua Primary School",
            "Serangoon Garden Primary School",
            "St Gabriel's Primary School",
        ],
        "parks_1km": [
            "Serangoon Garden Park",
            "Lorong Chuan Park",
        ],
    },

    # ── Toa Payoh ────────────────────────────────────────────────────────────────
    "310078": {
        "block": "78",
        "street": "Toa Payoh Lor 4",
        "postal_code": "310078",
        "nearest_mrt":          {"name": "Toa Payoh MRT",               "dist_m": 340},
        "nearest_mall":         {"name": "HDB Hub / Junction 8",        "dist_m": 420},
        "nearest_sports_hall":  {"name": "Toa Payoh Sports Hall",       "dist_m": 500},
        "nearest_polyclinic":   {"name": "Toa Payoh Polyclinic",        "dist_m": 460},
        "nearest_hawker":       {"name": "Toa Payoh 93 Hawker Centre",  "dist_m": 150},
        "primary_schools_1km":  [
            "Kheng Cheng School",
            "CHIJ Primary (Toa Payoh)",
            "Marymount Convent School",
            "Pei Chun Public School",
        ],
        "parks_1km": [
            "Toa Payoh Town Park",
            "Toa Payoh Stadium Grounds",
        ],
    },

    # ── Tampines ────────────────────────────────────────────────────────────────
    "820201": {
        "block": "201",
        "street": "Tampines St 21",
        "postal_code": "820201",
        "nearest_mrt":          {"name": "Tampines MRT",                "dist_m": 670},
        "nearest_mall":         {"name": "Tampines Mall",               "dist_m": 720},
        "nearest_sports_hall":  {"name": "Tampines Sports Hall",        "dist_m": 830},
        "nearest_polyclinic":   {"name": "Tampines Polyclinic",         "dist_m": 950},
        "nearest_hawker":       {"name": "Tampines 137 Hawker Centre",  "dist_m": 280},
        "primary_schools_1km":  [
            "Poi Ching School",
            "Gongshang Primary School",
            "Tampines Primary School",
            "St Hilda's Primary School",
            "Yu Neng Primary School",
            "Angsana Primary School",
        ],
        "parks_1km": [
            "Tampines Eco Green",
            "Tampines Central Park",
            "Bedok Reservoir Park",
        ],
    },

    # ── Jurong West (nearest_polyclinic = None → exercises "No amenity found") ──
    "680323": {
        "block": "323",
        "street": "Jurong West St 32",
        "postal_code": "680323",
        "nearest_mrt":          {"name": "Boon Lay MRT",                "dist_m": 1200},
        "nearest_mall":         {"name": "Jurong Point",                "dist_m": 1350},
        "nearest_sports_hall":  {"name": "Jurong West Sports Centre",   "dist_m": 880},
        "nearest_polyclinic":   None,   # no polyclinic within reasonable distance
        "nearest_hawker":       {"name": "Jurong West 505 Hawker Centre", "dist_m": 340},
        "primary_schools_1km":  [
            "Jurong West Primary School",
            "Rulang Primary School",
        ],
        "parks_1km": [
            "Jurong Lake Gardens",
            "Pandan Reservoir Park",
        ],
    },
}
