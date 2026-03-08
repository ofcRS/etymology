from collections import deque

from backend.database import get_connection, lookup_word
from backend.models import CognateResponse, GraphData, GraphLink, GraphNode

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

MAX_BFS_DEPTH = 12


def _bfs_ancestors(start: tuple[str, str]) -> dict[tuple[str, str], list]:
    """BFS from start node via SQLite queries. No in-memory graph needed."""
    conn = get_connection()
    visited = {start: []}
    queue = deque([(start, 0)])

    while queue:
        current, depth = queue.popleft()
        if depth >= MAX_BFS_DEPTH:
            continue

        current_path = visited[current]
        term, lang = current

        rows = conn.execute(
            "SELECT related_term, related_lang, reltype FROM etymologies WHERE term = ? AND lang = ?",
            (term, lang),
        ).fetchall()

        for row in rows:
            neighbor = (row["related_term"], row["related_lang"])
            if neighbor not in visited:
                visited[neighbor] = current_path + [(current, row["reltype"])]
                queue.append((neighbor, depth + 1))

    conn.close()
    return visited


def find_cognates(word_a: tuple[str, str], word_b: tuple[str, str]) -> CognateResponse:
    if not lookup_word(word_a[0], word_a[1]):
        return CognateResponse(
            is_cognate=False,
            message=f"Word '{word_a[0]}' ({word_a[1]}) not found in etymology database.",
        )
    if not lookup_word(word_b[0], word_b[1]):
        return CognateResponse(
            is_cognate=False,
            message=f"Word '{word_b[0]}' ({word_b[1]}) not found in etymology database.",
        )

    ancestors_a = _bfs_ancestors(word_a)
    ancestors_b = _bfs_ancestors(word_b)

    common = set(ancestors_a.keys()) & set(ancestors_b.keys())

    if not common:
        return CognateResponse(
            is_cognate=False,
            message=f"No common ancestor found between '{word_a[0]}' and '{word_b[0]}'.",
        )

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
    nodes_set: dict[tuple[str, str], str] = {}
    links: list[GraphLink] = []

    nodes_set[word_a] = "input"
    nodes_set[word_b] = "input"
    nodes_set[ancestor] = "ancestor"

    _add_path_to_graph(ancestors_a[ancestor], ancestor, nodes_set, links)
    _add_path_to_graph(ancestors_b[ancestor], ancestor, nodes_set, links)

    nodes = [
        GraphNode(id=f"{term}|{lang}", term=term, lang=lang, type=node_type)
        for (term, lang), node_type in nodes_set.items()
    ]
    return GraphData(nodes=nodes, links=links)


def _add_path_to_graph(
    path: list[tuple[tuple[str, str], str]],
    ancestor: tuple[str, str],
    nodes_set: dict,
    links: list[GraphLink],
) -> None:
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
