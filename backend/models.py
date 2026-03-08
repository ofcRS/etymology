from pydantic import BaseModel


class WordInput(BaseModel):
    term: str
    lang: str  # Full name: "English", "Russian", etc.


class CognateRequest(BaseModel):
    word_a: WordInput
    word_b: WordInput


class GraphNode(BaseModel):
    id: str
    term: str
    lang: str
    type: str  # "input", "ancestor", "intermediate"
    translations: dict[str, str] | None = None


class GraphLink(BaseModel):
    source: str
    target: str
    reltype: str


class GraphData(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]


class CognateResponse(BaseModel):
    is_cognate: bool
    common_ancestor: str | None = None
    ancestor_lang: str | None = None
    graph: GraphData | None = None
    graph_a: GraphData | None = None
    graph_b: GraphData | None = None
    message: str


class SearchResult(BaseModel):
    term: str
    lang: str
