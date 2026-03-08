from collections import deque

import networkx as nx

from backend.database import get_all_relationships
from backend.models import CognateResponse, GraphData, GraphLink, GraphNode


def build_graph() -> nx.DiGraph:
    """Build a directed graph from all etymology relationships."""
    rows = get_all_relationships()
    G = nx.DiGraph()

    for row in rows:
        src = (row["term"], row["lang"])
        tgt = (row["related_term"], row["related_lang"])
        G.add_edge(src, tgt, reltype=row["reltype"])

    print(f"Graph built: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    return G


def _bfs_ancestors(G: nx.DiGraph, start: tuple[str, str]) -> dict[tuple[str, str], list]:
    """BFS from start node following edges to collect all ancestors with paths.

    Returns dict mapping ancestor node -> list of (node, reltype) path steps.
    """
    visited = {}
    queue = deque()

    visited[start] = []
    queue.append(start)

    while queue:
        current = queue.popleft()
        current_path = visited[current]

        for neighbor in G.successors(current):
            edge_data = G.edges[current, neighbor]
            reltype = edge_data.get("reltype", "related")

            if neighbor not in visited:
                new_path = current_path + [(current, reltype)]
                visited[neighbor] = new_path
                queue.append(neighbor)

    return visited


# Proto-languages to prefer as common ancestors, in priority order
PROTO_LANGS = {
    "Proto-Indo-European",
    "Proto-Germanic",
    "Proto-Slavic",
    "Proto-Balto-Slavic",
    "Proto-Indo-Iranian",
    "Proto-West Germanic",
    "Proto-Italic",
    "Proto-Hellenic",
}


def find_cognates(G: nx.DiGraph, word_a: tuple[str, str], word_b: tuple[str, str]) -> CognateResponse:
    """Find if two words are cognates by looking for common ancestors."""
    if word_a not in G:
        return CognateResponse(
            is_cognate=False,
            message=f"Word '{word_a[0]}' ({word_a[1]}) not found in etymology database.",
        )
    if word_b not in G:
        return CognateResponse(
            is_cognate=False,
            message=f"Word '{word_b[0]}' ({word_b[1]}) not found in etymology database.",
        )

    # BFS from both words
    ancestors_a = _bfs_ancestors(G, word_a)
    ancestors_b = _bfs_ancestors(G, word_b)

    # Find common ancestors
    common = set(ancestors_a.keys()) & set(ancestors_b.keys())

    if not common:
        return CognateResponse(
            is_cognate=False,
            message=f"No common ancestor found between '{word_a[0]}' and '{word_b[0]}'.",
        )

    # Prefer PIE ancestors, then other proto-languages, then shortest path
    def score(node: tuple[str, str]) -> tuple[int, int]:
        if node[1] == "Proto-Indo-European":
            priority = 0
        elif node[1] in PROTO_LANGS:
            priority = 1
        else:
            priority = 2
        path_len = len(ancestors_a[node]) + len(ancestors_b[node])
        return (priority, path_len)

    best = min(common, key=score)

    graph_data = _build_graph_data(word_a, word_b, best, ancestors_a, ancestors_b)

    return CognateResponse(
        is_cognate=True,
        common_ancestor=best[0],
        ancestor_lang=best[1],
        graph=graph_data,
        message=f"Cognates! Common ancestor: '{best[0]}' ({best[1]})",
    )


def _build_graph_data(
    word_a: tuple[str, str],
    word_b: tuple[str, str],
    ancestor: tuple[str, str],
    ancestors_a: dict,
    ancestors_b: dict,
) -> GraphData:
    """Build D3.js-compatible graph data from the two paths to common ancestor."""
    nodes_set: dict[tuple[str, str], str] = {}
    links: list[GraphLink] = []

    nodes_set[word_a] = "input"
    nodes_set[word_b] = "input"
    nodes_set[ancestor] = "ancestor"

    path_a = ancestors_a[ancestor]
    _add_path_to_graph(path_a, ancestor, nodes_set, links)

    path_b = ancestors_b[ancestor]
    _add_path_to_graph(path_b, ancestor, nodes_set, links)

    nodes = [
        GraphNode(
            id=f"{term}|{lang}",
            term=term,
            lang=lang,
            type=node_type,
        )
        for (term, lang), node_type in nodes_set.items()
    ]

    return GraphData(nodes=nodes, links=links)


def _add_path_to_graph(
    path: list[tuple[tuple[str, str], str]],
    ancestor: tuple[str, str],
    nodes_set: dict,
    links: list[GraphLink],
) -> None:
    """Add path nodes and edges to the graph data."""
    all_nodes = [step[0] for step in path] + [ancestor]

    for i, (node, reltype) in enumerate(path):
        if node not in nodes_set:
            nodes_set[node] = "intermediate"
        next_node = all_nodes[i + 1]
        if next_node not in nodes_set:
            nodes_set[next_node] = "intermediate"

        link = GraphLink(
            source=f"{node[0]}|{node[1]}",
            target=f"{next_node[0]}|{next_node[1]}",
            reltype=reltype,
        )
        if not any(l.source == link.source and l.target == link.target for l in links):
            links.append(link)
