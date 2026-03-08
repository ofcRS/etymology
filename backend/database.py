import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "etymology.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def lookup_word(term: str, lang: str) -> bool:
    """Check if a word exists in the database."""
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM etymologies WHERE term = ? AND lang = ? LIMIT 1",
        (term, lang),
    ).fetchone()
    if row:
        conn.close()
        return True

    # Also check as a related_term
    row = conn.execute(
        "SELECT 1 FROM etymologies WHERE related_term = ? AND related_lang = ? LIMIT 1",
        (term, lang),
    ).fetchone()
    conn.close()
    return row is not None



REFLEX_LANGS = ("English", "Russian", "Latin", "Ancient Greek", "Sanskrit", "German", "French")


def get_reflexes(term: str, lang: str, limit: int = 5) -> dict[str, str]:
    """Get modern-language reflexes (descendants) of an ancestor term."""
    conn = get_connection()
    placeholders = ",".join("?" * len(REFLEX_LANGS))
    rows = conn.execute(
        f"""
        SELECT DISTINCT term, lang FROM etymologies
        WHERE related_term = ? AND related_lang = ?
        AND lang IN ({placeholders})
        LIMIT ?
        """,
        (term, lang, *REFLEX_LANGS, limit),
    ).fetchall()
    conn.close()
    return {row["lang"]: row["term"] for row in rows}


def search_words(prefix: str, lang: str, limit: int = 10) -> list[dict]:
    """Autocomplete search by prefix."""
    conn = get_connection()
    pattern = prefix.lower() + "%"

    # Search in term column
    rows = conn.execute(
        """
        SELECT DISTINCT term, lang FROM etymologies
        WHERE lang = ? AND LOWER(term) LIKE ?
        UNION
        SELECT DISTINCT related_term AS term, related_lang AS lang FROM etymologies
        WHERE related_lang = ? AND LOWER(related_term) LIKE ?
        LIMIT ?
        """,
        (lang, pattern, lang, pattern, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
