# Etymology — Cognate Detector

<img width="1972" height="1410" alt="image" src="https://github.com/user-attachments/assets/fc3b78de-164f-4803-8cff-33c7f26a9ed3" />


**Live at [shck.dev/etymology](https://shck.dev/etymology/)**

Find shared Indo-European roots between words across 16 languages, visualized as interactive etymology graphs.

Enter two words → see if they share a common ancestor → explore the etymological chain.

<p align="center">
  <strong>water</strong> (English) ← <em>*wódr̥</em> (Proto-Indo-European) → <strong>вода</strong> (Russian)
</p>

## How it works

1. **Data** — 1.6M etymology relationships parsed from [Wiktionary](https://en.wiktionary.org/) via [wiktextract/kaikki.org](https://kaikki.org/), stored in SQLite (~250MB)
2. **Algorithm** — BFS from both words through ancestry edges (`inherited_from`, `derived_from`, `borrowed_from`), intersects ancestor sets, prefers Proto-Indo-European roots
3. **Visualization** — D3.js force-directed graph showing the etymological chain with era-colored nodes (proto-languages gold, ancient amber, medieval brown, modern green) and a diamond-shaped common ancestor

## Features

- **Cognate detection** — finds common proto-language ancestors between word pairs using three-tier BFS: direct ancestor lookup → fuzzy proto-root matching → weak bridge fallback
- **Descendant tree view** — explore full descendant trees from any ancestor node
- **Random cognate pairs** — 398 pre-validated pairs for discovery, served via API
- **Ancestor translations** — shows modern-language reflexes (descendants) on ancestor nodes in the graph
- **Auto language detection** — detects Russian, Armenian, Greek, and Arabic from input script; defaults to English
- **Non-cognate graphs** — displays separate etymology trees even when words aren't related
- **Autocomplete** — prefix search across 1.6M etymology entries
- **Interactive graph** — zoom, pan, drag nodes; era-colored nodes with tooltips and legend

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
- **Data**: [wiktextract/kaikki.org](https://kaikki.org/) (Wiktionary JSONL dump)
- **Deployment**: GitHub Actions → SSH to Hetzner VPS

## Setup

```bash
# Install dependencies
uv sync

# Download & build the etymology database (~2.3GB download → ~250MB SQLite)
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
  database.py    SQLite queries & reflex lookups
  models.py      Pydantic models
  pairs.py       Pre-computed cognate pairs loader
frontend/
  index.html     Single-page UI
  app.v2.js      Form handling, language detection, API calls
  graph.js       D3.js force-directed graph visualization
  style.css      Dark theme styling
data/
  etymology.db         SQLite database (~255MB)
  cognate_pairs.json   398 pre-validated cognate pairs
scripts/
  setup_db.py          JSONL → SQLite pipeline
  generate_pairs.py    Mine & validate cognate pairs from DB
```

## API

```
POST /api/cognates    — { word_a: {term, lang}, word_b: {term, lang} }
GET  /api/search      — ?q=prefix&lang=en
GET  /api/tree        — ?term=*méh₂tēr&lang=ine-pro
GET  /api/random-pair — returns one random cognate pair
GET  /api/pairs       — ?limit=6 — returns N random pairs
```

Languages use Wiktionary codes: `en`, `ru`, `de`, `fr`, `la`, `grc`, `ine-pro`, `gem-pro`, etc.

## License

MIT
