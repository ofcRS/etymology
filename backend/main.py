from fastapi import FastAPI, Query, Response
from fastapi.staticfiles import StaticFiles

from backend.graph import find_cognates, get_descendant_tree
from backend.models import CognateRequest, CognateResponse, CognatePair, GraphData, SearchResult
from backend.database import search_words
from backend.pairs import get_random_pair, get_random_pairs

app = FastAPI(title="Etymology Cognate Detector")


@app.post("/api/cognates", response_model=CognateResponse)
async def check_cognates(req: CognateRequest):
    word_a = (req.word_a.term.strip(), req.word_a.lang)
    word_b = (req.word_b.term.strip(), req.word_b.lang)
    return find_cognates(word_a, word_b)


@app.get("/api/tree", response_model=GraphData)
async def tree(term: str, lang: str):
    return get_descendant_tree((term, lang))


@app.get("/api/random-pair", response_model=CognatePair | None)
async def random_pair(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return get_random_pair()


@app.get("/api/pairs", response_model=list[CognatePair])
async def pairs(response: Response, limit: int = Query(default=6, ge=1, le=50)):
    response.headers["Cache-Control"] = "no-store"
    return get_random_pairs(limit)


@app.get("/api/search", response_model=list[SearchResult])
async def search(q: str = Query(min_length=1), lang: str = Query(default="en")):
    results = search_words(q.lower().strip(), lang)
    return [SearchResult(term=r["term"], lang=r["lang"]) for r in results]


# Serve frontend as static files (mount last so API routes take priority)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
