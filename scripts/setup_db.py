"""Download etymology-db Parquet, filter to relevant languages, write to SQLite."""

import sqlite3
from pathlib import Path

import httpx
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "etymology.db"

PARQUET_URL = (
    "https://github.com/droher/etymology-db/releases/download/2023-12/etymology.parquet"
)
PARQUET_PATH = DATA_DIR / "etymology.parquet"

RELEVANT_LANGS = {
    # Modern
    "English", "Russian",
    # Proto
    "Proto-Indo-European", "Proto-Germanic", "Proto-Slavic",
    "Proto-Balto-Slavic", "Proto-Indo-Iranian",
    "Proto-West Germanic", "Proto-Italic", "Proto-Hellenic",
    # Historical
    "Old English", "Middle English",
    "Latin", "Late Latin", "Medieval Latin", "New Latin",
    "Ancient Greek", "Koine Greek",
    "Old Church Slavonic", "Old Russian", "Old East Slavic",
    "Old Norse", "Old French", "Old Northern French",
    "Middle French", "Sanskrit", "Old High German",
    "Middle High German", "Middle Low German", "Middle Dutch",
    "Old Dutch", "Old Saxon", "Old Latin",
    "Old Persian", "Old Portuguese", "Old Spanish",
    # Additional useful
    "German", "French", "Dutch", "Spanish", "Italian",
    "Portuguese", "Polish", "Czech",
    "Greek", "Armenian", "Old Armenian",
    "Persian", "Arabic",
}


def download_parquet() -> None:
    if PARQUET_PATH.exists():
        print(f"Parquet already exists at {PARQUET_PATH}, skipping download.")
        return

    print("Downloading etymology.parquet (~140MB)...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.stream("GET", PARQUET_URL, follow_redirects=True, timeout=300) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(PARQUET_PATH, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=1024 * 1024):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  {downloaded / 1e6:.1f} / {total / 1e6:.1f} MB ({pct:.0f}%)", end="", flush=True)
    print("\nDownload complete.")


def build_sqlite() -> None:
    print("Reading parquet...")
    df = pd.read_parquet(PARQUET_PATH)

    print(f"Total rows in parquet: {len(df):,}")

    # Filter: at least one side must be in our relevant set
    # (related_lang can be NaN for root entries)
    lang_match = df["lang"].isin(RELEVANT_LANGS)
    related_match = df["related_lang"].isin(RELEVANT_LANGS)
    mask = lang_match & (related_match | df["related_lang"].isna())
    filtered = df[mask].copy()
    print(f"Filtered rows (lang in set): {len(filtered):,}")

    # Drop rows where related_term is NaN (group roots with no actual related word)
    filtered = filtered.dropna(subset=["related_term"])
    # Also require related_lang to be in our set
    filtered = filtered[filtered["related_lang"].isin(RELEVANT_LANGS)]
    print(f"After requiring both sides in set: {len(filtered):,}")

    # Keep only needed columns
    cols = ["term", "lang", "related_term", "related_lang", "reltype"]
    filtered = filtered[cols]

    # Write to SQLite
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    filtered.to_sql("etymologies", conn, index=False, if_exists="replace")

    # Create indexes
    conn.execute("CREATE INDEX idx_term_lang ON etymologies(term, lang)")
    conn.execute("CREATE INDEX idx_related ON etymologies(related_term, related_lang)")
    conn.execute("CREATE INDEX idx_term_prefix ON etymologies(lang, term)")
    conn.commit()

    # Stats
    row_count = conn.execute("SELECT COUNT(*) FROM etymologies").fetchone()[0]
    print(f"SQLite ready at {DB_PATH} — {row_count:,} rows")

    # Sample
    sample = conn.execute(
        "SELECT term, lang, related_term, related_lang, reltype FROM etymologies WHERE lang = 'English' LIMIT 5"
    ).fetchall()
    print("Sample English rows:")
    for r in sample:
        print(f"  {r}")

    conn.close()

    # Clean up parquet
    print("Removing parquet file...")
    PARQUET_PATH.unlink()
    print("Done.")


if __name__ == "__main__":
    download_parquet()
    build_sqlite()
