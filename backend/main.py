from contextlib import asynccontextmanager

import networkx as nx
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles

from backend.graph import build_graph, find_cognates
from backend.models import CognateRequest, CognateResponse, SearchResult
from backend.database import search_words

graph: nx.DiGraph | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    print("Building etymology graph...")
    graph = build_graph()
    print("Graph ready.")
    yield


app = FastAPI(title="Etymology Cognate Detector", lifespan=lifespan)


@app.post("/api/cognates", response_model=CognateResponse)
async def check_cognates(req: CognateRequest):
    word_a = (req.word_a.term.lower().strip(), req.word_a.lang)
    word_b = (req.word_b.term.lower().strip(), req.word_b.lang)
    return find_cognates(graph, word_a, word_b)


@app.get("/api/search", response_model=list[SearchResult])
async def search(q: str = Query(min_length=1), lang: str = Query(default="English")):
    results = search_words(q.lower().strip(), lang)
    return [SearchResult(term=r["term"], lang=r["lang"]) for r in results]


# Serve frontend as static files (mount last so API routes take priority)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
