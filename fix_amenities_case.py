"""
Fix all-caps names in outputs/amenities_by_postal.csv.

Converts ALL CAPS place names to proper Singapore-aware capitalization:
- Acronyms (MRT, LRT, CHIJ, KK, SBG, LC) stay uppercase
- Abbreviations expand (PK→Park, OS→Open Space, JLN→Jalan, UPP→Upper, etc.)
- Phrase expansions applied first ((FCP)→(Fort Canning Park), JLG:→Jurong Lake Gardens:)
- Lowercase particles (of, and, the) when not the first word
- Hyphenated words: each segment capitalized independently
- Already-mixed-case values are left untouched
"""

import csv

# ── Constants ─────────────────────────────────────────────────────────────────

# These stay ALL CAPS even when embedded in a name
ALWAYS_CAPS = {
    'MRT', 'LRT', 'CHIJ', 'KK', 'IMM', 'JEM', 'SBG', 'LC',
}

# Standalone word abbreviations → expansion (already properly cased)
WORD_EXPANSIONS = {
    'PK':  'Park',
    'OS':  'Open Space',
    'FC':  'Fitness Corner',
    'JLN': 'Jalan',
    'AVE': 'Avenue',
    'RD':  'Road',
    'DR':  'Drive',
    'LOR': 'Lorong',
    'MT':  'Mount',
    'UPP': 'Upper',
    'PTE': 'Pte',
    'LTD': 'Ltd',
}

# String-level replacements applied before word processing.
# More-specific patterns first.
PHRASE_EXPANSIONS = [
    ('(FCP)',  '(Fort Canning Park)'),
    ('JLG:',   'Jurong Lake Gardens:'),
]

# Lowercase particles when not the first word
LOWERCASE_PARTICLES = {'of', 'and', 'the', 'at', 'in', 'on', 'to', 'for', 'a', 'an'}

# Exact values that look all-caps but are intentional brand names → leave untouched
PRESERVE_EXACT = {
    '100AM',
    'STELLAR@TE2',
}

# Columns → True if pipe-separated list, False if single value
COLUMNS = {
    'nearest_train_name':     False,
    'primary_schools_1km':    True,
    'parks_1km':              True,
    'nearest_mall_name':      False,
    'nearest_healthcare_name': False,
}

# ── Conversion helpers ────────────────────────────────────────────────────────

def is_all_caps(text: str) -> bool:
    """True if every alphabetic character in text is uppercase."""
    alpha = [c for c in text if c.isalpha()]
    return bool(alpha) and all(c.isupper() for c in alpha)


def _convert_core(core: str, is_first: bool) -> str:
    """
    Convert the stripped alphabetic/hyphenated core of a single token.
    Handles hyphens and apostrophes recursively.
    """
    if not core:
        return core

    # ── Hyphenated word: convert each segment independently ──────────────────
    if '-' in core:
        parts = core.split('-')
        # All hyphen-joined segments are treated as "first" (always capitalize)
        return '-'.join(_convert_core(p, True) for p in parts)

    # ── Apostrophe: convert prefix, lowercase suffix ─────────────────────────
    # e.g. WOMEN'S → Women's, KING'S → King's, PEARL'S → Pearl's
    if "'" in core:
        idx = core.index("'")
        before = core[:idx]       # e.g. "WOMEN"
        after  = core[idx:]       # e.g. "'S"
        converted_before = _convert_core(before, is_first)
        after_proper = after[0] + after[1:].lower()   # "'" + "s" → "'s"
        return converted_before + after_proper

    # ── Always-caps acronyms ──────────────────────────────────────────────────
    if core in ALWAYS_CAPS:
        return core

    # ── Abbreviation expansions ───────────────────────────────────────────────
    if core in WORD_EXPANSIONS:
        return WORD_EXPANSIONS[core]   # already correctly cased in the table

    # ── Lowercase particles (not the first word) ──────────────────────────────
    if not is_first and core.lower() in LOWERCASE_PARTICLES:
        return core.lower()

    # ── Default: title-case (capitalize first letter, lowercase rest) ─────────
    return core[0].upper() + core[1:].lower()


def convert_word(token: str, is_first: bool) -> str:
    """
    Convert one whitespace-free token from a name, preserving outer
    parentheses and trailing punctuation.
    """
    # Detect wrapping parenthesis
    prefix = '(' if token.startswith('(') else ''
    suffix = ')' if token.endswith(')')  else ''
    core = token[len(prefix): len(token) - len(suffix)] if (prefix or suffix) else token

    # Detect trailing punctuation (colon, comma, period, semicolon)
    trail = ''
    while core and core[-1] in ',.;:':
        trail = core[-1] + trail
        core = core[:-1]

    converted = _convert_core(core, is_first)
    return prefix + converted + trail + suffix


def convert_name(text: str) -> str:
    """
    Convert a single name string from ALL CAPS to proper Singapore case.
    Mixed-case values are returned unchanged.
    """
    if not text or text == '0':
        return text
    if text in PRESERVE_EXACT:
        return text
    if not is_all_caps(text):
        return text

    # Apply phrase-level expansions first (they inject mixed-case text)
    for old, new in PHRASE_EXPANSIONS:
        text = text.replace(old, new)

    # Tokenise on whitespace; tokens that already have lowercase
    # (injected by phrase expansion) are left as-is
    tokens = text.split()
    result = []
    for i, token in enumerate(tokens):
        if any(c.islower() for c in token):
            result.append(token)       # already converted by phrase expansion
        else:
            result.append(convert_word(token, i == 0))
    return ' '.join(result)


def convert_pipe_list(text: str) -> str:
    """Convert each item in a pipe-separated list."""
    items = text.split('|')
    return '|'.join(convert_name(item.strip()) for item in items)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    path = 'outputs/amenities_by_postal.csv'

    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            for col, is_list in COLUMNS.items():
                if col in row:
                    row[col] = convert_pipe_list(row[col]) if is_list else convert_name(row[col])
            rows.append(row)

    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. Wrote {len(rows)} rows to {path}\n")

    # ── Spot-check sample conversions ────────────────────────────────────────
    for col in ['nearest_train_name', 'nearest_healthcare_name', 'nearest_mall_name']:
        print(f"--- {col} (first 15 unique) ---")
        seen = set()
        with open(path, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                v = row[col]
                if v and v not in seen:
                    seen.add(v)
                    print(f"  {v}")
                if len(seen) >= 15:
                    break
        print()

    print("--- parks_1km sample (first 25 unique items) ---")
    seen = set()
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            for item in row['parks_1km'].split('|'):
                item = item.strip()
                if item and item != '0' and item not in seen:
                    seen.add(item)
                    print(f"  {item}")
                if len(seen) >= 25:
                    break
            if len(seen) >= 25:
                break
    print()

    print("--- primary_schools_1km sample (CHIJ entries) ---")
    seen = set()
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            for item in row['primary_schools_1km'].split('|'):
                item = item.strip()
                if 'CHIJ' in item and item not in seen:
                    seen.add(item)
                    print(f"  {item}")


if __name__ == '__main__':
    main()
