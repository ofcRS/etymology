"""Generate validated cognate pairs from the etymology database.

Mines the SQLite DB for PIE roots that have both English and Russian
descendants, validates each candidate via find_cognates(), and outputs
a curated JSON file for the API to serve.

Usage:
    uv run python scripts/generate_pairs.py
"""

import json
import sqlite3
import sys
from pathlib import Path

# Add project root to path so we can import backend modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import DB_PATH
from backend.graph import find_cognates

OUTPUT_PATH = PROJECT_ROOT / "data" / "cognate_pairs.json"

# Relation types that indicate genuine etymological descent
STRONG_RELTYPES = ("inherited_from", "derived_from", "has_root")

# Words to exclude (too obscure, affixes, etc.)
MIN_WORD_LEN = 2


def get_candidates(conn: sqlite3.Connection) -> list[dict]:
    """Find (en_word, ru_word) pairs sharing the same ine-pro ancestor.

    For each PIE root, pick the shortest single-word EN and RU terms
    to prefer common, recognizable words over compounds and obscurities.
    """
    placeholders = ",".join("?" * len(STRONG_RELTYPES))
    query = f"""
    WITH en_words AS (
        SELECT term, related_term, related_lang,
               ROW_NUMBER() OVER (
                   PARTITION BY related_term
                   ORDER BY LENGTH(term), term
               ) AS rn
        FROM etymologies
        WHERE lang = 'en'
          AND related_lang = 'ine-pro'
          AND reltype IN ({placeholders})
          AND LENGTH(term) >= ?
          AND term NOT LIKE '%-%'
          AND term NOT LIKE '% %'
          AND LOWER(term) = term
    ),
    ru_words AS (
        SELECT term, related_term, related_lang,
               ROW_NUMBER() OVER (
                   PARTITION BY related_term
                   ORDER BY LENGTH(term), term
               ) AS rn
        FROM etymologies
        WHERE lang = 'ru'
          AND related_lang = 'ine-pro'
          AND reltype IN ({placeholders})
          AND LENGTH(term) >= ?
          AND term NOT LIKE '%-%'
          AND term NOT LIKE '% %'
    )
    SELECT
        en.term AS en_word,
        ru.term AS ru_word,
        en.related_term AS ancestor,
        en.related_lang AS ancestor_lang
    FROM en_words en
    JOIN ru_words ru
        ON en.related_term = ru.related_term
    WHERE en.rn = 1 AND ru.rn = 1
    ORDER BY LENGTH(en.term) + LENGTH(ru.term)
    """
    params = (*STRONG_RELTYPES, MIN_WORD_LEN, *STRONG_RELTYPES, MIN_WORD_LEN)
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def validate_pair(en_word: str, ru_word: str) -> dict | None:
    """Validate a pair via find_cognates and return pair data if cognate."""
    try:
        result = find_cognates((en_word, "en"), (ru_word, "ru"))
    except Exception as e:
        print(f"  ERROR validating {en_word}/{ru_word}: {e}")
        return None

    if not result.is_cognate:
        return None

    return {
        "word_a": ru_word,
        "lang_a": "ru",
        "word_b": en_word,
        "lang_b": "en",
        "ancestor": result.common_ancestor,
        "ancestor_lang": result.ancestor_lang,
        "confidence": result.confidence,
    }


def main():
    print(f"Reading database from {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    candidates = get_candidates(conn)
    conn.close()
    print(f"Found {len(candidates)} candidate pairs from DB")

    validated = []
    seen_pairs = set()

    for i, cand in enumerate(candidates):
        en_word = cand["en_word"]
        ru_word = cand["ru_word"]

        # Skip duplicates
        pair_key = (en_word, ru_word)
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        result = validate_pair(en_word, ru_word)
        if result:
            validated.append(result)
            print(f"  [{len(validated)}] {ru_word} ↔ {en_word} ({result['ancestor']})")

        if (i + 1) % 100 == 0:
            print(f"  ... processed {i + 1}/{len(candidates)}, {len(validated)} valid so far")

    print(f"\nValidated {len(validated)} cognate pairs")

    # Sort by confidence (high first), then alphabetically
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    validated.sort(key=lambda p: (confidence_order.get(p["confidence"], 3), p["word_b"]))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(validated, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(validated)} pairs to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
