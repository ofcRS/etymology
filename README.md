# Etymology — Cognate Detector

Find shared Indo-European roots between English and Russian words, visualized as interactive etymology graphs.

Enter two words → see if they share a common ancestor → explore the etymological chain.

<p align="center">
  <strong>water</strong> (English) ← <em>*wódr̥</em> (Proto-Indo-European) → <strong>вода</strong> (Russian)
</p>

## How it works

1. **Data** — 1.8M etymology relationships parsed from [Wiktionary](https://en.wiktionary.org/) via [etymology-db](https://github.com/droher/etymology-db), stored in SQLite (~250MB)
2. **Algorithm** — BFS from both words through ancestry edges (`inherited_from`, `derived_from`, `borrowed_from`), intersects ancestor sets, prefers Proto-Indo-European roots
3. **Visualization** — D3.js force-directed graph showing the etymological chain: input words (blue) → intermediates (gray) → common ancestor (gold)

## Example cognate pairs

| English | Russian | Common Ancestor | Proto-Language |
|---------|---------|----------------|----------------|
| water | вода | \*wódr̥ | Proto-Indo-European |
| mother | мать | \*méh₂tēr | Proto-Indo-European |
| three | три | \*tréyes | Proto-Indo-European |
| night | ночь | \*nókʷts | Proto-Indo-European |

## Stack

- **Backend**: Python, FastAPI, SQLite
- **Frontend**: Vanilla JS, D3.js
- **Data**: [etymology-db](https://github.com/droher/etymology-db) (Wiktionary parquet dump)
- **Memory**: ~60MB (BFS runs against SQLite, no in-memory graph)

## Setup

```bash
# Install dependencies
uv sync

# Download & build the etymology database (~140MB download → ~250MB SQLite)
uv run python scripts/setup_db.py

# Run
uv run uvicorn backend.main:app --reload --port 8000
```

Open [localhost:8000](http://localhost:8000).

## Project structure

```
backend/
  main.py        FastAPI app + endpoints
  graph.py       BFS cognate detection against SQLite
  database.py    SQLite queries
  models.py      Pydantic models
frontend/
  index.html     Single-page UI
  app.js         Form handling + API calls
  graph.js       D3.js force-directed graph
scripts/
  setup_db.py    Parquet → SQLite pipeline
```

## API

```
POST /api/cognates  — { word_a: {term, lang}, word_b: {term, lang} }
GET  /api/search    — ?q=prefix&lang=English
```

Languages use full names: `English`, `Russian`, `Proto-Indo-European`, `Old English`, `Latin`, etc.
