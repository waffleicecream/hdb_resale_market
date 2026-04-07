"""
preprocess_market.py
--------------------
Reads merged_data/hdb_with_amenities_macro_pre2026.csv and auxiliary
transport files, computes all market statistics, and writes
outputs/market_stats.json for consumption by market_analysis.py.

Run from the project root or the frontend/ directory:
    python frontend/preprocess_market.py
"""

import json
import os
import math
from collections import defaultdict

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

CSV_PATH  = os.path.join(_ROOT, "merged_data", "[FINAL]hdb_with_amenities_macro_pre2026.csv")
MRT_PATH  = os.path.join(_ROOT, "outputs", "future_mrt_stations_for_frontend.csv")
HUBS_PATH = os.path.join(_ROOT, "outputs", "future_transport_hubs_for_frontend.csv")
OUT_PATH  = os.path.join(_ROOT, "outputs", "market_stats.json")

# ── Constants ─────────────────────────────────────────────────────────────────
FLAT_TYPES  = ["2 ROOM", "3 ROOM", "4 ROOM", "5 ROOM", "EXECUTIVE"]
FLAT_GROUPS = ["ALL"] + FLAT_TYPES

# ── Town "About" descriptions (hardcoded, one paragraph per town) ─────────────
TOWN_ABOUT = {
    "NATIONAL": (
        "Singapore's HDB resale market spans 26 planning areas islandwide, offering a diverse "
        "range of flat types from compact 3-room units to spacious Executive flats. Resale "
        "prices vary significantly by location, flat type, floor level, and remaining lease, "
        "with mature central estates commanding substantial premiums over newer towns in the "
        "north and west. The market is driven by a combination of upgraders, first-time buyers "
        "ineligible for BTO, and permanent residents, making it a barometer of broader "
        "housing demand and affordability trends in Singapore."
    ),
    "ANG MO KIO": (
        "Ang Mo Kio is a well-established mature estate in the north-central region, "
        "developed from the 1970s and known for its strong community identity and "
        "self-sufficient town centre anchored by AMK Hub. The town enjoys exceptional "
        "MRT connectivity at the North-South and Circle Line interchange, with hawker centres, "
        "wet markets, and parks woven throughout its residential precincts. Its flat stock "
        "spans a wide range of ages and sizes, attracting steady demand from families "
        "seeking proximity to the central corridor without paying full city-fringe premiums."
    ),
    "BEDOK": (
        "Bedok is one of Singapore's largest and most populous towns, stretching across the "
        "eastern flank of the island with direct access to East Coast Park and Bedok Reservoir. "
        "The town offers a comprehensive suite of amenities including Bedok Mall, Bedok Point, "
        "and numerous hawker centres, all well-served by the East-West Line. Its mature "
        "housing stock includes a high proportion of larger flat types, making it popular "
        "among east-side families and those seeking spacious homes at relatively accessible "
        "price points compared to the central region."
    ),
    "BISHAN": (
        "Bishan is a premium centrally-located HDB estate widely regarded as one of the most "
        "desirable towns in Singapore. Flanked by Bishan-Ang Mo Kio Park and the Kallang River, "
        "it offers extensive green recreational space uncommon for a mature town. The North-South "
        "and Circle Line interchange at Bishan MRT gives residents outstanding island-wide "
        "connectivity. These attributes, combined with proximity to quality schools and Junction 8 "
        "mall, sustain some of the highest HDB resale prices in Singapore, attracting "
        "professionals and families who prioritise central access and lifestyle quality."
    ),
    "BUKIT BATOK": (
        "Bukit Batok is a mid-sized residential town in the western region, characterised by "
        "its lush greenery and proximity to Bukit Timah Nature Reserve and Bukit Batok Nature "
        "Park. Served by the North-South Line, the town is anchored by West Mall and features "
        "a mix of older and newer flat types across its precincts. Resale prices are generally "
        "moderate relative to more central towns, making it attractive to buyers seeking "
        "larger floor areas and a quieter suburban environment within reasonable commuting "
        "distance of the city."
    ),
    "BUKIT MERAH": (
        "Bukit Merah is a mature south-central estate with outstanding access to the CBD "
        "and proximity to Alexandra, Harbourfront, and the emerging Greater Southern Waterfront. "
        "Its HDB stock includes some of Singapore's most sought-after units along the "
        "Queensway and Redhill corridors, commanding strong premiums for high-floor views "
        "and city proximity. The town is served by multiple MRT lines and a dense network "
        "of bus routes, and amenities such as Queensway Shopping Centre, Tiong Bahru Plaza, "
        "and numerous hawker centres serve a cosmopolitan mix of residents."
    ),
    "BUKIT PANJANG": (
        "Bukit Panjang is a northwestern residential town known for its proximity to Bukit "
        "Timah Nature Reserve and the Rail Corridor, offering a greener, more suburban "
        "lifestyle. The town is served by the Downtown Line and the Bukit Panjang LRT "
        "network, which connects its dispersed precincts to Hillion Mall and the wider "
        "MRT system. Resale prices are generally accessible, attracting young families "
        "and buyers who value green living and do not need to commute daily to the CBD."
    ),
    "BUKIT TIMAH": (
        "Bukit Timah is a prestige district in the central-western region, home to Singapore's "
        "primary nature reserves and some of the island's most exclusive private residential "
        "addresses. HDB flats in this planning area are limited in number and command "
        "significant premiums owing to their proximity to premier schools, Bukit Timah "
        "Nature Reserve, and the Downtown Line at Beauty World. Demand is driven by "
        "owner-occupiers who prioritise educational catchment areas and the rare combination "
        "of urban convenience and natural surroundings."
    ),
    "CENTRAL AREA": (
        "The Central Area encompasses the historic heart of Singapore, including the CBD, "
        "Tanjong Pagar, and Pearl's Hill, where HDB flats are exceptionally scarce and "
        "command among the highest resale prices on the island. Units here are highly "
        "sought after for their unrivalled connectivity — multiple MRT lines converge "
        "in this precinct — and their proximity to the financial district, Marina Bay, "
        "and the vibrant streetscapes of Chinatown and Outram. Buyers are typically "
        "professionals seeking to minimise commute times or investors attracted by the "
        "perennial scarcity of HDB supply in the urban core."
    ),
    "CHOA CHU KANG": (
        "Choa Chu Kang is a large residential town in the northwestern region offering "
        "good value relative to its amenity offering. Anchored by Lot One Shoppers Mall "
        "and well-served by the North-South Line and Bukit Panjang LRT, the town hosts "
        "a younger demographic drawn by the adjacent Tengah eco-township development "
        "and its spacious, car-lite vision. The flat stock spans older walk-up blocks "
        "to newer BTO developments, giving buyers a range of options at price points "
        "below the island average."
    ),
    "CLEMENTI": (
        "Clementi is a well-regarded mature estate in the west known for its strong "
        "educational ecosystem, sitting adjacent to the National University of Singapore "
        "and numerous primary and secondary schools. Served by the East-West Line and "
        "anchored by Clementi Mall and West Coast Plaza, the town attracts families "
        "who prioritise school proximity and academics. Resale prices are firm, reflecting "
        "sustained demand from both local families and expatriate academics, and the town "
        "benefits from ongoing one-north and Jurong Innovation District spillover activity."
    ),
    "GEYLANG": (
        "Geylang is a distinctive inner-city estate east of the CBD, known for its vibrant "
        "mix of uses, heritage shophouses, and some of Singapore's most celebrated food "
        "streets. Served by the East-West Line at Aljunied and Kallang stations, the town "
        "offers relatively affordable resale prices for its central location, attracting "
        "buyers drawn by proximity to the city fringe and an eclectic urban character. "
        "Its residential precincts are quieter than the commercial strips and house "
        "a diverse mix of long-term residents and newer buyers seeking value near the CBD."
    ),
    "HOUGANG": (
        "Hougang is a well-established northeastern town with a strong local identity built "
        "around its wet markets, hawker centres, and community facilities. Served by the "
        "North-East Line and with Kang Kar Mall and Hougang Mall as its retail anchors, "
        "the town offers a range of flat sizes at competitive prices. Its proximity to "
        "Punggol Park and the Lower Serangoon River corridor adds lifestyle value, "
        "and residents enjoy a tight-knit community atmosphere typical of Singapore's "
        "older new towns developed in the 1980s."
    ),
    "JURONG EAST": (
        "Jurong East is the commercial and transport hub of Singapore's western region, "
        "home to a major MRT interchange where the East-West and North-South Lines meet. "
        "The town is anchored by a dense retail cluster — JCube, IMM, Westgate, JEM, and "
        "Bigbox — and sits at the gateway to the emerging Jurong Lake District, Singapore's "
        "designated second CBD. HDB flats here benefit from outstanding amenity access and "
        "strong connectivity, sustaining healthy resale demand from western-region workers "
        "and families seeking urban convenience without central-region prices."
    ),
    "JURONG WEST": (
        "Jurong West is one of Singapore's most populous HDB towns, offering a wide variety "
        "of flat types across its sprawling precincts in the far west. Anchored by Jurong "
        "Point and served by the East-West Line, the town provides comprehensive amenities "
        "including parks, sports facilities, and a large hawker centre network. Resale prices "
        "are among the more accessible on the island, making Jurong West a popular destination "
        "for first-time buyers, larger families, and those working in the western industrial "
        "and logistics corridor."
    ),
    "KALLANG/WHAMPOA": (
        "Kallang/Whampoa is a central-adjacent estate straddling the Kallang River, known "
        "for its heritage character, vibrant food scene, and strategic location between "
        "the CBD and the eastern regions. Served by the Circle Line and with good bus "
        "connectivity, the town hosts the Singapore Sports Hub and benefits from proximity "
        "to Lavender and Boon Keng MRT stations. Its HDB stock commands firm resale premiums "
        "for a non-mature town, driven by its central positioning and the appeal of "
        "waterfront-adjacent living along the Kallang Basin."
    ),
    "MARINE PARADE": (
        "Marine Parade is a sought-after eastern estate with a strong identity shaped by "
        "its East Coast Park frontage and the nostalgic Parkway Parade shopping mall. "
        "HDB supply in this planning area is limited, confined to the original blocks "
        "developed in the 1970s and 1980s, which drives perennial resale demand and "
        "premium pricing. The town attracts buyers who value coastal living, proximity "
        "to lifestyle amenities along East Coast Road, and improving MRT access via "
        "the Thomson-East Coast Line, which has opened new stations nearby."
    ),
    "PASIR RIS": (
        "Pasir Ris is an established eastern town at the edge of the island, offering "
        "a spacious, low-density residential environment complemented by Pasir Ris Park "
        "and Downtown East. Served by the East-West Line, the town is popular with "
        "families seeking large flats — particularly Executive and 5-room units — at "
        "prices below the island average for comparable sizes. Its coastal character "
        "and park-connector links to Tampines and Changi create a lifestyle appeal "
        "that sustains steady demand despite its peripheral location."
    ),
    "PUNGGOL": (
        "Punggol is Singapore's newest HDB town, purpose-built around a waterway concept "
        "with the Punggol Waterway and Coney Island as central lifestyle features. Served "
        "by the North-East Line and the Punggol LRT network, the town is anchored by "
        "Waterway Point and hosts a young, family-oriented demographic attracted by "
        "modern BTO units and the eco-waterway environment. Punggol Digital District, "
        "an emerging knowledge-economy hub, is adding economic vibrancy, and resale "
        "prices have risen steadily as the town matures and its amenity offering deepens."
    ),
    "QUEENSTOWN": (
        "Queenstown holds a special place in Singapore's housing history as the country's "
        "first satellite HDB town, developed from the late 1950s. Today it commands some "
        "of the highest HDB resale prices island-wide, driven by its central location, "
        "proximity to NUS, one-north, and the Greater Southern Waterfront, and the "
        "consistent regeneration of its housing stock through SERS. Flat types here "
        "tend toward smaller sizes relative to suburban towns, but high-floor units "
        "with city or reservoir views attract buyers willing to pay significant premiums."
    ),
    "SEMBAWANG": (
        "Sembawang is a northern coastal town with a distinct identity shaped by its "
        "former naval base heritage and proximity to the Johor Strait. The town is served "
        "by the North-South Line and anchored by Sun Plaza, with a quieter residential "
        "character than most mature estates. Resale prices are among the more affordable "
        "in Singapore, attracting buyers seeking large units — particularly Executive "
        "flats — and families who prefer a tranquil suburban lifestyle in the north, "
        "with improving amenities at Canberra MRT serving the newer precincts."
    ),
    "SENGKANG": (
        "Sengkang is a major northeastern new town developed from the late 1990s around "
        "a comprehensive LRT feeder network connecting to the North-East Line. The town "
        "is anchored by Compass One and Rivervale Mall and is characterised by modern "
        "flat designs and strong family demand. Its extensive cycling infrastructure "
        "and waterway parks give it a more planned, liveable character than older towns, "
        "and resale prices reflect the combination of relatively newer stock, good "
        "connectivity, and the town's position as a growing residential hub for northeast Singapore."
    ),
    "SERANGOON": (
        "Serangoon is a vibrant mixed-use town anchored by NEX mall — one of Singapore's "
        "largest suburban shopping centres — with a key North-East and Circle Line interchange "
        "at Serangoon MRT. The town's proximity to Little India, heritage shophouses, and "
        "a dense food scene gives it a cosmopolitan character, while its HDB precincts "
        "are dominated by well-established flat types in mid-rise blocks. Resale prices "
        "are firm, underpinned by the town's excellent connectivity, lifestyle offering, "
        "and consistent demand from upgraders and families."
    ),
    "TAMPINES": (
        "Tampines is the anchor town of the eastern region and one of Singapore's largest "
        "HDB estates, built around a comprehensive Regional Centre with Tampines Mall, "
        "Century Square, Tampines 1, and IKEA Tampines. Served by the East-West Line "
        "and with excellent bus interchange connectivity, the town offers a full range "
        "of flat types in both mature and newer precincts. Resale demand is consistently "
        "strong, driven by east-side families, proximity to Tampines Eco Green, and "
        "the town's reputation as a well-planned, self-sufficient community."
    ),
    "TOA PAYOH": (
        "Toa Payoh is one of Singapore's earliest and most iconic HDB towns, developed "
        "in the 1960s and known for its distinctive dragon playground, vibrant wet market, "
        "and central location. Served by the North-South Line and with HDB Hub as its "
        "administrative landmark, the town offers a dense mix of older flat types that "
        "attract buyers seeking centrally-located homes at prices below those of Bishan "
        "or Queenstown. Its heritage character, mature community fabric, and proximity "
        "to Novena and the medical cluster sustain perennial resale demand."
    ),
    "WOODLANDS": (
        "Woodlands is Singapore's northern gateway town, adjacent to the Causeway "
        "and Johor Bahru, positioning it uniquely for cross-border workers and those "
        "with family ties to Johor. Anchored by Causeway Point and served by the "
        "North-South Line, the town is one of Singapore's largest by area and population. "
        "Resale prices are generally accessible, reflecting its peripheral northern "
        "location, though improving transport links and the ongoing Woodlands North "
        "Coast development are gradually lifting the town's investment profile."
    ),
    "YISHUN": (
        "Yishun is a large northern town with a comprehensive amenity base anchored by "
        "Northpoint City — one of Singapore's biggest suburban malls — and served by "
        "the North-South Line. The town offers a wide range of flat types including "
        "spacious Executive and 5-room units at prices below the island average, making "
        "it attractive to families seeking value and space. Lower Seletar Reservoir and "
        "Yishun Park provide recreational greenery, and the town supports a broad demographic "
        "mix from young families in newer BTO blocks to long-term residents in older estates."
    ),
}


# ── Transport development prose builder ───────────────────────────────────────

def _extract_interchange(notes_str):
    """Return ' (interchange with XYZ)' if present in notes, else empty string."""
    if not notes_str or "interchange with" not in notes_str.lower():
        return ""
    part = notes_str.split("interchange with")[-1].strip()
    # Take only the line code — the first all-caps word token
    token = next((w for w in part.split() if w.isupper()), "").strip("();,")
    return f" (interchange with {token})" if token else ""


def build_town_future_developments(mrt_df, hubs_df, town):
    """Build a concise prose summary of upcoming transport for a town."""
    town_mrt  = mrt_df[mrt_df["town"] == town]
    town_hubs = hubs_df[hubs_df["town"] == town]

    if town_mrt.empty and town_hubs.empty:
        return "No upcoming developments have been confirmed for this town."

    sentences = []

    # ── MRT stations: group by (line, year, status) ───────────────────────────
    if not town_mrt.empty:
        groups = defaultdict(list)      # (line, yr, is_uc) -> [(station, interchange)]
        for _, row in town_mrt.iterrows():
            line   = row["line"]
            yr     = str(int(row["expected_year"])) if pd.notna(row["expected_year"]) else "TBC"
            is_uc  = "under construction" in str(row.get("status", "")).lower()
            notes  = str(row["notes"]) if pd.notna(row["notes"]) else ""
            ix     = _extract_interchange(notes)
            groups[(line, yr, is_uc)].append((row["station_name"], ix))

        for (line, yr, is_uc), entries in sorted(groups.items(), key=lambda x: x[0][1]):
            verb = ("are under construction" if is_uc else "are planned") if len(entries) > 1 \
                   else ("is under construction" if is_uc else "is planned")
            yr_str = f", expected {yr}" if yr != "TBC" else ""

            station_strs = [f"{s}{ix}" for s, ix in entries]
            if len(station_strs) == 1:
                joined = station_strs[0]
            elif len(station_strs) == 2:
                joined = f"{station_strs[0]} and {station_strs[1]}"
            else:
                joined = ", ".join(station_strs[:-1]) + f", and {station_strs[-1]}"

            noun = "station" if len(entries) == 1 else "stations"
            sentences.append(f"{joined} {noun} on the {line} {verb}{yr_str}.")

    # ── Transport hubs ────────────────────────────────────────────────────────
    if not town_hubs.empty:
        for _, row in town_hubs.iterrows():
            hub    = row["hub_name"]
            htype  = row["hub_type"]
            yr     = str(int(row["expected_year"])) if pd.notna(row["expected_year"]) else None
            is_uc  = "under construction" in str(row.get("status", "")).lower()
            verb   = "is under construction" if is_uc else "is proposed"
            yr_str = f", expected {yr}" if yr else ""
            sentences.append(f"{hub} ({htype}) {verb}{yr_str}.")

    return " ".join(sentences)


# ── Statistics computation ────────────────────────────────────────────────────

def _safe_pct(new, old):
    if old and old != 0:
        return round((new - old) / abs(old) * 100, 2)
    return 0.0


def _month_key(dt_series):
    return pd.to_datetime(dt_series).dt.strftime("%Y-%m")


def _quarter_key(q_series):
    return q_series.str.replace("-", " ", n=1)


def compute_scope_stats(df_scope):
    result = {}

    for grp in FLAT_GROUPS:
        sub = df_scope if grp == "ALL" else df_scope[df_scope["flat_type"] == grp]
        sub25 = sub[sub["year"] == 2025]
        sub24 = sub[sub["year"] == 2024]

        txn_2025 = len(sub25)
        txn_2024 = len(sub24)

        mean_2025 = round(sub25["resale_price"].mean(), 2) if txn_2025 > 0 else 0.0
        mean_2024 = round(sub24["resale_price"].mean(), 2) if txn_2024 > 0 else 0.0

        entry = {
            "txn_2025":     txn_2025,
            "txn_2024":     txn_2024,
            "txn_yoy_abs":  txn_2025 - txn_2024,
            "txn_yoy_pct":  _safe_pct(txn_2025, txn_2024),
            "mean_2025":    mean_2025 if not math.isnan(mean_2025) else 0.0,
            "mean_2024":    mean_2024 if not math.isnan(mean_2024) else 0.0,
            "mean_yoy_abs": round(mean_2025 - mean_2024, 2) if not (math.isnan(mean_2025) or math.isnan(mean_2024)) else 0.0,
            "mean_yoy_pct": _safe_pct(mean_2025, mean_2024),
        }

        med_2025 = round(sub25["resale_price"].median(), 2) if txn_2025 > 0 else 0.0
        med_2024 = round(sub24["resale_price"].median(), 2) if txn_2024 > 0 else 0.0
        entry.update({
            "median_2025":    med_2025 if not math.isnan(med_2025) else 0.0,
            "median_2024":    med_2024 if not math.isnan(med_2024) else 0.0,
            "median_yoy_abs": round(med_2025 - med_2024, 2),
            "median_yoy_pct": _safe_pct(med_2025, med_2024),
        })

        def _empty_record():
            return {"block": "", "street_name": "", "flat_type": "", "storey_range": "", "resale_price": 0}

        if txn_2025 > 0:
            high = sub25.loc[sub25["resale_price"].idxmax()]
            low  = sub25.loc[sub25["resale_price"].idxmin()]
            entry["highest"] = {k: (str(high[k]) if k != "resale_price" else int(high[k])) for k in ["block", "street_name", "flat_type", "storey_range", "resale_price"]}
            entry["lowest"]  = {k: (str(low[k])  if k != "resale_price" else int(low[k]))  for k in ["block", "street_name", "flat_type", "storey_range", "resale_price"]}
        else:
            entry["highest"] = _empty_record()
            entry["lowest"]  = _empty_record()

        monthly_avg = {}
        quarterly_avg = {}
        if txn_2025 > 0:
            s25 = sub25.copy()
            s25["_mk"] = _month_key(s25["month"])
            s25["_qk"] = _quarter_key(s25["quarter"])
            monthly_avg   = {mk: round(g["resale_price"].mean(), 2) for mk, g in s25.groupby("_mk")}
            quarterly_avg = {qk: round(g["resale_price"].mean(), 2) for qk, g in s25.groupby("_qk")}

        entry["monthly_avg"]   = monthly_avg
        entry["quarterly_avg"] = quarterly_avg

        result[grp] = entry

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Reading {CSV_PATH} ...")
    df = pd.read_csv(
        CSV_PATH,
        usecols=["month", "town", "flat_type", "block", "street_name",
                 "storey_range", "resale_price", "year", "quarter"],
    )
    df = df[df["flat_type"].isin(FLAT_TYPES)].copy()
    df["year"] = df["year"].astype(int)
    print(f"  {len(df):,} rows after filtering flat types")

    output = {}

    print("Computing national stats ...")
    output["national"] = compute_scope_stats(df)

    towns = sorted(df["town"].unique())
    print(f"Computing stats for {len(towns)} towns ...")
    for town in towns:
        output[town] = compute_scope_stats(df[df["town"] == town])

    print("Building town descriptions ...")
    mrt_df  = pd.read_csv(MRT_PATH)
    hubs_df = pd.read_csv(HUBS_PATH)

    town_about = {"NATIONAL": TOWN_ABOUT["NATIONAL"]}
    town_future = {
        "NATIONAL": (
            "Singapore's transport network is undergoing its most ambitious expansion in "
            "decades. The Cross Island Line (CRL), Jurong Region Line (JRL), and Thomson-East "
            "Coast Line (TEL) extensions are adding dozens of stations across the island, with "
            "most under construction and targeted for completion between 2026 and 2035. The "
            "Johor Bahru–Singapore Rapid Transit System (RTS Link) will open at Woodlands North, "
            "providing a new rail connection across the Causeway. Collectively, these projects "
            "will bring MRT access within walking distance of virtually all HDB estates."
        ),
    }

    for town in towns:
        town_about[town]  = TOWN_ABOUT.get(town, "")
        town_future[town] = build_town_future_developments(mrt_df, hubs_df, town)

    output["town_about"]               = town_about
    output["town_future_developments"] = town_future

    print(f"Writing {OUT_PATH} ...")
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Done.")


if __name__ == "__main__":
    main()
