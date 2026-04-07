"""
fix_capitalization.py
---------------------
Convert full-caps names in unique_addresses.csv to properly capitalized names.

Columns processed:
  - town
  - street_name
  - nearest_train_name
  - primary_schools_1km  (pipe-separated list)
  - parks_1km            (pipe-separated list)
  - nearest_healthcare_name

Run from project root:
    python frontend/fix_capitalization.py
"""

import json
import os
import re
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIQUE_ADDR = os.path.join(ROOT, "outputs", "unique_addresses.csv")
POSTAL_LOOKUP_OUT = os.path.join(ROOT, "outputs", "postal_lookup.json")
GEOCODE_CACHE = os.path.join(ROOT, "data", "geocode_cache.json")

# ---------------------------------------------------------------------------
# Capitalization rules
# ---------------------------------------------------------------------------

# Official acronyms / initialisms that must stay ALL CAPS
KEEP_UPPER = {
    # Transport
    'MRT', 'LRT',
    # Schools
    'CHIJ',
    # Hospitals
    'KK',
    # NParks / facility initialisms
    'FCP',   # Fort Canning Park (connector label)
    'FC',    # Fitness Corner
    'OS',    # Open Space
    'SBG',   # Singapore Botanic Gardens
    'JLG',   # Jurong Lake Gardens
    'LC',    # Learning Corridor (SBG zone label)
    'CC',    # Community Club / Centre
}

# Abbreviated words → their properly-cased short form (not expanded)
TITLE_ABBREVS = {
    # Street-type suffixes
    'AVE':      'Ave',
    'ST':       'St',
    'RD':       'Rd',
    'DR':       'Dr',
    'CRES':     'Cres',
    'PL':       'Pl',
    'CL':       'Cl',
    'PK':       'Pk',
    'HTS':      'Hts',
    'TER':      'Ter',
    'CTRL':     'Ctrl',
    'GDNS':     'Gdns',
    # Singapore directional / locational prefixes
    'NTH':      'Nth',
    'STH':      'Sth',
    'UPP':      'Upp',
    'BT':       'Bt',       # Bukit
    'KG':       'Kg',       # Kampong
    'TG':       'Tg',       # Tanjong
    'JLN':      'Jln',      # Jalan
    'LOR':      'Lor',      # Lorong
    # C'wealth
    "C'WEALTH": "C'wealth",
    # Company suffixes
    'PTE':      'Pte',
    'LTD':      'Ltd',
}

# Small function words → lowercase unless they are the first token
SMALL_WORDS = {'of', 'and', 'the', 'at', 'in', 'for', 'to', 'a', 'an', 'by'}

# Special-phrase substitutions applied after word-level processing
# (pattern, replacement) — pattern is case-insensitive
SPECIAL_PHRASES = [
    # one-north is the official lowercase spelling of the business park / MRT station
    (re.compile(r'\bone-north\b', re.IGNORECASE), 'one-north'),
]

# Exact-string typo corrections (applied to specific columns after capitalization)
TYPO_FIXES = {
    'Eunos Polyclinc':     'Eunos Polyclinic',
    'Sembawang Polyclinc': 'Sembawang Polyclinic',
}


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _title_case_word(word: str) -> str:
    """
    Title-case a clean word (no surrounding punctuation), handling apostrophes.
    e.g. "WOMEN'S" → "Women's"  (not "Women'S")
    """
    if not word:
        return word
    if "'" in word:
        idx = word.index("'")
        before, after = word[:idx], word[idx:]   # after includes the apostrophe
        return (before[0].upper() + before[1:].lower() + after.lower()) if before else after.lower()
    return word[0].upper() + word[1:].lower()


def _process_token(raw: str, is_first: bool = True) -> str:
    """
    Process one whitespace-delimited token.
    Strips leading/trailing punctuation, applies capitalization rules,
    and recurses for slash- and hyphen-separated compounds.
    """
    # --- Strip surrounding punctuation ---
    LEAD_CHARS = '([{'
    TRAIL_CHARS = ')]}:,'

    leading = ''
    while raw and raw[0] in LEAD_CHARS:
        leading += raw[0]
        raw = raw[1:]

    trailing = ''
    while raw and raw[-1] in TRAIL_CHARS:
        trailing = raw[-1] + trailing
        raw = raw[:-1]

    # Abbreviations like "ST." (period at end)
    has_period = raw.endswith('.')
    if has_period:
        raw = raw[:-1]

    if not raw:
        return leading + trailing

    period_suffix = '.' if has_period else ''

    # --- Slash-separated compound: e.g. KALLANG/WHAMPOA, CC/BTC ---
    if '/' in raw:
        parts = raw.split('/')
        capped = [
            _process_token(p, is_first=(i == 0 and is_first))
            for i, p in enumerate(parts)
        ]
        return leading + '/'.join(capped) + period_suffix + trailing

    # --- Hyphen-separated compound: e.g. BISHAN-ANG, ONE-NORTH ---
    if '-' in raw:
        parts = raw.split('-')
        capped = [_process_token(p, is_first=True) for p in parts]
        return leading + '-'.join(capped) + period_suffix + trailing

    upper = raw.upper()

    # Alphanumeric identifiers like "1A", "4B" — preserve as-is
    if re.match(r'^\d+[A-Za-z]+$', raw):
        return leading + raw + period_suffix + trailing

    # Pure digit strings — preserve as-is
    if raw.isdigit():
        return leading + raw + period_suffix + trailing

    # Official acronyms / initialisms → ALL CAPS
    if upper in KEEP_UPPER:
        return leading + upper + period_suffix + trailing

    # Known abbreviated words → prescribed short form
    if upper in TITLE_ABBREVS:
        return leading + TITLE_ABBREVS[upper] + period_suffix + trailing

    # Small function words → lowercase (unless first token)
    if not is_first and raw.lower() in SMALL_WORDS:
        return leading + raw.lower() + period_suffix + trailing

    # Default: title case
    return leading + _title_case_word(raw) + period_suffix + trailing


def capitalize_name(s) -> str:
    """
    Convert a name string to properly capitalized form.
    Idempotent — safe to call on already-cased input.
    Returns the original value unchanged if it is NaN or the sentinel '0'.
    """
    if not isinstance(s, str) or s == '0':
        return s

    tokens = s.split()
    result_tokens = [_process_token(t, is_first=(i == 0)) for i, t in enumerate(tokens)]
    result = ' '.join(result_tokens)

    # Apply whole-phrase substitutions
    for pattern, replacement in SPECIAL_PHRASES:
        result = pattern.sub(replacement, result)

    return result


def capitalize_pipe_list(s) -> str:
    """Apply capitalize_name to each element of a pipe-separated list."""
    if not isinstance(s, str) or s == '0':
        return s
    return '|'.join(capitalize_name(part) for part in s.split('|'))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("Loading unique_addresses.csv...")
    df = pd.read_csv(UNIQUE_ADDR)

    # Single-value columns
    for col in ['town', 'street_name', 'nearest_train_name', 'nearest_healthcare_name']:
        if col in df.columns:
            df[col] = df[col].apply(capitalize_name)

    # Typo fixes (applied after capitalization)
    df['nearest_healthcare_name'] = df['nearest_healthcare_name'].replace(TYPO_FIXES)

    # Pipe-separated list columns
    for col in ['primary_schools_1km', 'parks_1km']:
        if col in df.columns:
            df[col] = df[col].apply(capitalize_pipe_list)

    # Expand 'Pk' abbreviation to 'Park' in parks_1km only
    if 'parks_1km' in df.columns:
        df['parks_1km'] = df['parks_1km'].str.replace(r'\bPk\b', 'Park', regex=True)

    df.to_csv(UNIQUE_ADDR, index=False)
    print(f"Done. Saved {len(df)} rows to outputs/unique_addresses.csv")

    # Spot-check a variety of cases
    print("\n--- Town names ---")
    print(sorted(df['town'].unique()))

    print("\n--- Sample street names ---")
    sample_streets = df['street_name'].dropna().unique()
    for s in sorted(sample_streets)[:20]:
        print(' ', s)

    print("\n--- Train station names (sample) ---")
    for s in sorted(df['nearest_train_name'].dropna().unique())[:10]:
        print(' ', s)

    print("\n--- ONE-NORTH check ---")
    one_north = df[df['nearest_train_name'].str.contains('one-north', case=False, na=False)]
    if not one_north.empty:
        print(' ', one_north['nearest_train_name'].iloc[0])

    print("\n--- Healthcare names ---")
    for s in sorted(df['nearest_healthcare_name'].dropna().unique()):
        print(' ', s)

    print("\n--- Sample school lists ---")
    for v in df['primary_schools_1km'].dropna().unique()[:5]:
        if v != '0':
            print(' ', v[:100])

    print("\n--- Sample park lists ---")
    for v in df['parks_1km'].dropna().unique()[:5]:
        if v != '0':
            print(' ', v[:120])

    # -------------------------------------------------------------------------
    # Build postal_lookup.json
    # Keys: postal code strings → {block, street_name, town, address}
    # Postal codes sourced from geocode_cache.json (keyed "BLOCK STREET_UPPER")
    # -------------------------------------------------------------------------
    print("\nBuilding postal_lookup.json...")
    with open(GEOCODE_CACHE, encoding="utf-8") as f:
        geocode_cache = json.load(f)

    postal_lookup = {}
    block_street_to_postal = {}  # (block_upper, street_upper) → postal string
    no_postal = 0
    for _, row in df.iterrows():
        block = str(row["block"]).strip()
        street = str(row["street_name"]).strip()
        town = str(row["town"]).strip()

        cache_key = f"{block} {street.upper()}"
        entry = geocode_cache.get(cache_key)
        if not entry or not isinstance(entry, dict) or not entry.get("postal"):
            no_postal += 1
            continue

        postal_raw = str(entry["postal"]).strip()
        # Skip invalid postal codes (e.g. "000NIL", non-6-digit values)
        if not postal_raw.isdigit() or len(postal_raw.lstrip("0") or "0") > 6:
            no_postal += 1
            continue
        postal = postal_raw.zfill(6)
        address = f"Blk {block} {street}"
        # Last-write wins for duplicate postal codes (shouldn't occur for HDB blocks)
        postal_lookup[postal] = {
            "block": block,
            "street_name": street,
            "town": town,
            "address": address,
        }
        block_street_to_postal[(block.upper(), street.upper())] = postal

    with open(POSTAL_LOOKUP_OUT, "w", encoding="utf-8") as f:
        json.dump(postal_lookup, f, ensure_ascii=False, indent=2)

    print(f"  Saved {len(postal_lookup)} postal codes to outputs/postal_lookup.json")
    if no_postal:
        print(f"  Skipped {no_postal} addresses with no postal code in geocode cache")

    # Add postal_code as the first column in unique_addresses.csv
    df["postal_code"] = df.apply(
        lambda r: block_street_to_postal.get(
            (str(r["block"]).strip().upper(), str(r["street_name"]).strip().upper())
        ),
        axis=1,
    )
    cols = ["postal_code"] + [c for c in df.columns if c != "postal_code"]
    df = df[cols]
    df.to_csv(UNIQUE_ADDR, index=False)
    print(f"  Added postal_code column to unique_addresses.csv ({df['postal_code'].notna().sum()} non-null)")
