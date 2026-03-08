"""Download kaikki.org wiktextract JSONL, extract etymology edges, write to SQLite."""

import gzip
import json
import sqlite3
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "etymology.db"

JSONL_URL = "https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz"
JSONL_GZ_PATH = DATA_DIR / "raw-wiktextract-data.jsonl.gz"

RELEVANT_LANGS = {
    # Modern
    "en", "ru", "de", "fr", "es", "it", "pt", "nl", "pl", "cs", "el", "hy", "fa", "ar",
    # Proto
    "ine-pro", "gem-pro", "sla-pro", "ine-bsl-pro", "iir-pro", "gmw-pro", "itc-pro", "grk-pro",
    # Historical
    "ang", "enm", "la", "lla", "grc", "cu", "orv", "non", "fro", "xno", "frm", "sa",
    "goh", "gmh", "gml", "dum", "odt", "osx", "peo", "xcl",
    # Medieval/New/Late Latin variants used by wiktextract
    "la-med", "la-new", "la-lat",
}

# 3-arg templates: args.1=self_lang, args.2=source_lang, args.3=source_term
THREE_ARG_TEMPLATES = {
    "inh": "inherited_from",
    "inh+": "inherited_from",
    "der": "derived_from",
    "bor": "borrowed_from",
    "bor+": "borrowed_from",
    "lbor": "learned_borrowing_from",
    "slbor": "semi_learned_borrowing_from",
    "ubor": "unadapted_borrowing_from",
    "obor": "orthographic_borrowing_from",
    "root": "has_root",
    "cal": "calque_of",
    "bf": "back_formation_from",
}

# 2-arg templates: args.1=other_lang, args.2=other_term
TWO_ARG_TEMPLATES = {
    "cog": "cognate_of",
    "rel": "etymologically_related_to",
}

# Self-lang templates: args.1=self_lang, args.2=term in same lang
SELF_LANG_TEMPLATES = {
    "doublet": "doublet_with",
    "clipping": "clipping_of",
    "blend": "blend_of",
}

# Multi-arg templates: args.1=self_lang, args.2+ = components in same lang
MULTI_ARG_TEMPLATES = {
    "af": "has_affix",
    "affix": "has_affix",
    "suffix": "has_affix",
    "prefix": "has_affix",
    "com": "compound_of",
    "compound": "compound_of",
    "con": "has_confix",
}

SKIP_TEMPLATES = {"dercat", "noncog", "ncog", "desc"}


def download_jsonl_gz() -> None:
    if JSONL_GZ_PATH.exists():
        print(f"JSONL.gz already exists at {JSONL_GZ_PATH}, skipping download.")
        return

    print("Downloading raw-wiktextract-data.jsonl.gz (~2.3GB)...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.stream("GET", JSONL_URL, follow_redirects=True, timeout=600) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(JSONL_GZ_PATH, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=1024 * 1024):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  {downloaded / 1e6:.1f} / {total / 1e6:.1f} MB ({pct:.0f}%)", end="", flush=True)
    print("\nDownload complete.")


def _extract_edges_from_entry(entry: dict) -> list[tuple[str, str, str, str, str]]:
    """Extract etymology edges from a single wiktextract entry."""
    word = entry.get("word")
    lang_code = entry.get("lang_code")
    if not word or not lang_code:
        return []
    if lang_code not in RELEVANT_LANGS:
        return []

    templates = entry.get("etymology_templates", [])
    edges = []

    for tmpl in templates:
        name = tmpl.get("name", "")
        args = tmpl.get("args", {})

        if name in SKIP_TEMPLATES:
            continue

        if name in THREE_ARG_TEMPLATES:
            # args: 1=self_lang, 2=source_lang, 3=source_term
            source_lang = args.get("2", "")
            source_term = args.get("3", "")
            if source_lang and source_term and source_lang in RELEVANT_LANGS:
                edges.append((word, lang_code, source_term, source_lang, THREE_ARG_TEMPLATES[name]))

        elif name in TWO_ARG_TEMPLATES:
            # args: 1=other_lang, 2=other_term
            other_lang = args.get("1", "")
            other_term = args.get("2", "")
            if other_lang and other_term and other_lang in RELEVANT_LANGS:
                edges.append((word, lang_code, other_term, other_lang, TWO_ARG_TEMPLATES[name]))

        elif name in SELF_LANG_TEMPLATES:
            # args: 1=self_lang, 2=term in same lang
            other_term = args.get("2", "")
            if other_term:
                edges.append((word, lang_code, other_term, lang_code, SELF_LANG_TEMPLATES[name]))

        elif name in MULTI_ARG_TEMPLATES:
            # args: 1=component_lang, 2+ = components
            reltype = MULTI_ARG_TEMPLATES[name]
            component_lang = args.get("1", lang_code)
            if component_lang not in RELEVANT_LANGS:
                continue
            for key in sorted(args.keys()):
                if not key.isdigit() or key == "1":
                    continue
                component = args[key]
                if component and not component.startswith("-"):
                    edges.append((word, lang_code, component, component_lang, reltype))

    return edges


def build_sqlite() -> None:
    print("Parsing JSONL and building SQLite...")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE etymologies (
            term TEXT NOT NULL,
            lang TEXT NOT NULL,
            related_term TEXT NOT NULL,
            related_lang TEXT NOT NULL,
            reltype TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX idx_unique_edge
        ON etymologies(term, lang, related_term, related_lang, reltype)
    """)

    batch = []
    total_inserted = 0
    entries_processed = 0

    with gzip.open(JSONL_GZ_PATH, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entries_processed += 1
            if entries_processed % 500_000 == 0:
                print(f"  Processed {entries_processed:,} entries, {total_inserted:,} edges inserted...")

            edges = _extract_edges_from_entry(entry)
            batch.extend(edges)

            if len(batch) >= 10_000:
                conn.executemany(
                    "INSERT OR IGNORE INTO etymologies VALUES (?, ?, ?, ?, ?)",
                    batch,
                )
                total_inserted += len(batch)
                batch.clear()
                conn.commit()

    # Flush remaining
    if batch:
        conn.executemany(
            "INSERT OR IGNORE INTO etymologies VALUES (?, ?, ?, ?, ?)",
            batch,
        )
        total_inserted += len(batch)
        conn.commit()

    print(f"  Total entries processed: {entries_processed:,}")

    # Create query indexes
    print("Creating indexes...")
    conn.execute("CREATE INDEX idx_term_lang ON etymologies(term, lang)")
    conn.execute("CREATE INDEX idx_related ON etymologies(related_term, related_lang)")
    conn.execute("CREATE INDEX idx_term_prefix ON etymologies(lang, term)")
    conn.commit()

    # Stats
    row_count = conn.execute("SELECT COUNT(*) FROM etymologies").fetchone()[0]
    print(f"SQLite ready at {DB_PATH} — {row_count:,} rows")

    # Sample
    sample = conn.execute(
        "SELECT term, lang, related_term, related_lang, reltype FROM etymologies WHERE lang = 'en' LIMIT 5"
    ).fetchall()
    print("Sample English rows:")
    for r in sample:
        print(f"  {r}")

    conn.close()

    # Clean up .gz
    print("Removing .gz file...")
    JSONL_GZ_PATH.unlink()
    print("Done.")


if __name__ == "__main__":
    download_jsonl_gz()
    build_sqlite()
