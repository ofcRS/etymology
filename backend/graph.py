import re
import unicodedata
from collections import deque

from backend.database import get_connection, get_reflexes, resolve_term
from backend.models import CognateResponse, GraphData, GraphLink, GraphNode

PROTO_LANGS = {
    "ine-pro", "gem-pro", "sla-pro", "ine-bsl-pro",
    "iir-pro", "gmw-pro", "itc-pro", "grk-pro",
}

LANG_NAMES = {
    "en": "English",
    "ru": "Russian",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "cs": "Czech",
    "el": "Greek",
    "hy": "Armenian",
    "fa": "Persian",
    "ar": "Arabic",
    "ine-pro": "Proto-Indo-European",
    "gem-pro": "Proto-Germanic",
    "sla-pro": "Proto-Slavic",
    "ine-bsl-pro": "Proto-Balto-Slavic",
    "iir-pro": "Proto-Indo-Iranian",
    "gmw-pro": "Proto-West Germanic",
    "itc-pro": "Proto-Italic",
    "grk-pro": "Proto-Hellenic",
    "ang": "Old English",
    "enm": "Middle English",
    "la": "Latin",
    "lla": "Late Latin",
    "grc": "Ancient Greek",
    "cu": "Old Church Slavonic",
    "orv": "Old East Slavic",
    "non": "Old Norse",
    "fro": "Old French",
    "xno": "Old Northern French",
    "frm": "Middle French",
    "sa": "Sanskrit",
    "goh": "Old High German",
    "gmh": "Middle High German",
    "gml": "Middle Low German",
    "dum": "Middle Dutch",
    "odt": "Old Dutch",
    "osx": "Old Saxon",
    "peo": "Old Persian",
    "xcl": "Old Armenian",
    "la-med": "Medieval Latin",
    "la-new": "New Latin",
    "la-lat": "Late Latin",
}

ERA_APPROX = {
    "ine-pro": "around 4500\u20132500 BCE",
    "gem-pro": "around 500 BCE",
    "sla-pro": "around 500 CE",
    "ine-bsl-pro": "around 1500 BCE",
    "iir-pro": "around 2000 BCE",
    "gmw-pro": "around 200 CE",
    "itc-pro": "around 1000 BCE",
    "grk-pro": "around 2000 BCE",
}

MAX_BFS_DEPTH = 12

STRONG_RELTYPES = {
    "inherited_from", "derived_from", "borrowed_from", "has_root",
    "learned_borrowing_from", "semi_learned_borrowing_from",
    "unadapted_borrowing_from", "orthographic_borrowing_from",
}
WEAK_RELTYPES = {"cognate_of", "doublet_with", "etymologically_related_to"}


def _strip_diacritics(text: str) -> str:
    """Strip combining diacritical marks (accents) from text."""
    nfd = unicodedata.normalize("NFD", text)
    return re.sub(r"[\u0300-\u036f]", "", nfd)


def _lang_display(code: str) -> str:
    return LANG_NAMES.get(code, code)


def _deepest_proto_ancestor(word, ancestors):
    """Find the most ancestral proto-language node."""
    best = None
    best_score = (3, 0)
    for node, path in ancestors.items():
        if node == word:
            continue
        if node[1] == "ine-pro":
            priority = 0
        elif node[1] in PROTO_LANGS:
            priority = 1
        else:
            continue
        score = (priority, len(path))
        if score < best_score:
            best_score = score
            best = node
    return best


def _bfs_ancestors(start: tuple[str, str]) -> dict[tuple[str, str], list]:
    """BFS from start node via SQLite queries. Only follows strong etymology edges."""
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

        # Proto-language terms: try without *, and also without diacritics
        if lang in PROTO_LANGS:
            bare = term.lstrip("*")
            stripped = _strip_diacritics(bare)
            variants = {bare, stripped} - {term}
            for variant in variants:
                extra = conn.execute(
                    "SELECT related_term, related_lang, reltype FROM etymologies WHERE term = ? AND lang = ?",
                    (variant, lang),
                ).fetchall()
                rows = list(rows) + list(extra)

        for row in rows:
            if row["reltype"] not in STRONG_RELTYPES:
                continue
            neighbor = (row["related_term"], row["related_lang"])
            if neighbor not in visited:
                visited[neighbor] = current_path + [(current, row["reltype"])]
                queue.append((neighbor, depth + 1))

    conn.close()
    return visited


_PIE_SUFFIXES = [
    "yos", "tis", "tos", "nos", "men", "ter", "tēr", "tōr",
    "os", "om", "is", "us", "ēr", "ōr",
    "ā",
]


def _normalize_proto_root(term: str) -> str:
    """Strip reconstructed marker, PIE suffix, and diacritics to get a bare root."""
    t = term.strip("*-")
    for suffix in _PIE_SUFFIXES:
        if t.endswith(suffix) and len(t) > len(suffix):
            t = t[: -len(suffix)]
            break
    # Strip PIE laryngeals (h₁, h₂, h₃)
    t = re.sub(r'h[₁₂₃]', '', t)
    # Strip subscript digits
    t = re.sub(r'[₀₁₂₃₄₅₆₇₈₉]', '', t)
    # Strip diacritics: NFD decompose then remove combining marks
    nfd = unicodedata.normalize("NFD", t)
    t = re.sub(r"[\u0300-\u036f]", "", nfd)
    return t


def _fuzzy_match_proto_ancestors(
    ancestors_a: dict[tuple[str, str], list],
    ancestors_b: dict[tuple[str, str], list],
) -> tuple[tuple[str, str], tuple[str, str]] | None:
    """Find two proto-language ancestor nodes that share the same normalized root."""
    # Build index: (normalized_root, lang) -> list of (term, lang) nodes
    def _build_index(ancestors):
        index: dict[tuple[str, str], list[tuple[str, str]]] = {}
        for node in ancestors:
            if node[1] in PROTO_LANGS:
                key = (_normalize_proto_root(node[0]), node[1])
                index.setdefault(key, []).append(node)
        return index

    index_a = _build_index(ancestors_a)
    index_b = _build_index(ancestors_b)

    common_keys = set(index_a.keys()) & set(index_b.keys())
    if not common_keys:
        # Cross-language fallback: match on normalized root only (ignoring lang)
        cross_a: dict[str, list[tuple[str, str]]] = {}
        for (root, lang), nodes in index_a.items():
            if len(root) >= 3:
                cross_a.setdefault(root, []).extend(nodes)
        cross_b: dict[str, list[tuple[str, str]]] = {}
        for (root, lang), nodes in index_b.items():
            if len(root) >= 3:
                cross_b.setdefault(root, []).extend(nodes)
        cross_common = set(cross_a.keys()) & set(cross_b.keys())
        if not cross_common:
            return None

        def cross_score(root):
            best_len = min(len(ancestors_a[n]) for n in cross_a[root]) + min(
                len(ancestors_b[n]) for n in cross_b[root]
            )
            return best_len

        best_root = min(cross_common, key=cross_score)
        node_a = min(cross_a[best_root], key=lambda n: len(ancestors_a[n]))
        node_b = min(cross_b[best_root], key=lambda n: len(ancestors_b[n]))
        return (node_a, node_b)

    def score(key):
        lang = key[1]
        if lang == "ine-pro":
            priority = 0
        elif lang in PROTO_LANGS:
            priority = 1
        else:
            priority = 2
        # Pick shortest combined path
        best_len = min(len(ancestors_a[n]) for n in index_a[key]) + min(
            len(ancestors_b[n]) for n in index_b[key]
        )
        return (priority, best_len)

    best_key = min(common_keys, key=score)

    node_a = min(index_a[best_key], key=lambda n: len(ancestors_a[n]))
    node_b = min(index_b[best_key], key=lambda n: len(ancestors_b[n]))
    return (node_a, node_b)


def _build_fuzzy_graph_data(
    word_a: tuple[str, str],
    word_b: tuple[str, str],
    proto_a: tuple[str, str],
    proto_b: tuple[str, str],
    ancestors_a: dict,
    ancestors_b: dict,
) -> GraphData:
    """Build graph connecting two words through two different proto-forms linked by same_root."""
    nodes_set: dict[tuple[str, str], str] = {}
    links: list[GraphLink] = []

    nodes_set[word_a] = "input"
    nodes_set[word_b] = "input"
    nodes_set[proto_a] = "ancestor"
    nodes_set[proto_b] = "ancestor"

    _add_path_to_graph(ancestors_a[proto_a], proto_a, nodes_set, links)
    _add_path_to_graph(ancestors_b[proto_b], proto_b, nodes_set, links)

    # Add the same_root link between the two proto nodes
    links.append(
        GraphLink(
            source=f"{proto_a[0]}|{proto_a[1]}",
            target=f"{proto_b[0]}|{proto_b[1]}",
            reltype="same_root",
        )
    )

    nodes = [
        GraphNode(id=f"{term}|{lang}", term=term, lang=lang, type=node_type)
        for (term, lang), node_type in nodes_set.items()
    ]
    graph = GraphData(nodes=nodes, links=links)
    _enrich_with_translations(graph)
    return graph


def _find_weak_bridge(
    ancestors_a: dict[tuple[str, str], list],
    ancestors_b: dict[tuple[str, str], list],
) -> tuple[tuple[str, str], tuple[str, str], str] | None:
    """Check if any node in ancestors_a has a cognate_of edge to any node in ancestors_b."""
    conn = get_connection()
    set_a = set(ancestors_a.keys())
    set_b = set(ancestors_b.keys())

    best = None
    best_score = (3, float("inf"))

    placeholders = ",".join("?" * len(WEAK_RELTYPES))
    weak_params = tuple(WEAK_RELTYPES)

    for node in set_a:
        term, lang = node
        rows = conn.execute(
            f"SELECT related_term, related_lang, reltype FROM etymologies "
            f"WHERE term = ? AND lang = ? AND reltype IN ({placeholders})",
            (term, lang, *weak_params),
        ).fetchall()
        for row in rows:
            neighbor = (row["related_term"], row["related_lang"])
            if neighbor in set_b:
                if node[1] == "ine-pro" or neighbor[1] == "ine-pro":
                    priority = 0
                elif node[1] in PROTO_LANGS or neighbor[1] in PROTO_LANGS:
                    priority = 1
                else:
                    priority = 2
                path_len = len(ancestors_a[node]) + len(ancestors_b[neighbor])
                score = (priority, path_len)
                if score < best_score:
                    best_score = score
                    best = (node, neighbor, row["reltype"])

    # Also check reverse direction: nodes in B having weak edges to nodes in A
    for node in set_b:
        term, lang = node
        rows = conn.execute(
            f"SELECT related_term, related_lang, reltype FROM etymologies "
            f"WHERE term = ? AND lang = ? AND reltype IN ({placeholders})",
            (term, lang, *weak_params),
        ).fetchall()
        for row in rows:
            neighbor = (row["related_term"], row["related_lang"])
            if neighbor in set_a:
                if node[1] == "ine-pro" or neighbor[1] == "ine-pro":
                    priority = 0
                elif node[1] in PROTO_LANGS or neighbor[1] in PROTO_LANGS:
                    priority = 1
                else:
                    priority = 2
                path_len = len(ancestors_b[node]) + len(ancestors_a[neighbor])
                score = (priority, path_len)
                if score < best_score:
                    best_score = score
                    best = (neighbor, node, row["reltype"])

    conn.close()
    return best


def _build_weak_bridge_graph_data(
    word_a: tuple[str, str],
    word_b: tuple[str, str],
    bridge_a: tuple[str, str],
    bridge_b: tuple[str, str],
    reltype: str,
    ancestors_a: dict,
    ancestors_b: dict,
) -> GraphData:
    """Build graph connecting two words through a cognate_of bridge."""
    nodes_set: dict[tuple[str, str], str] = {}
    links: list[GraphLink] = []

    nodes_set[word_a] = "input"
    nodes_set[word_b] = "input"
    # Only mark proto-lang bridge nodes as ancestor; modern words stay intermediate
    if bridge_a not in nodes_set:
        nodes_set[bridge_a] = "ancestor" if bridge_a[1] in PROTO_LANGS else "intermediate"
    if bridge_b not in nodes_set:
        nodes_set[bridge_b] = "ancestor" if bridge_b[1] in PROTO_LANGS else "intermediate"

    _add_path_to_graph(ancestors_a[bridge_a], bridge_a, nodes_set, links)
    _add_path_to_graph(ancestors_b[bridge_b], bridge_b, nodes_set, links)

    # When bridge nodes are modern words, also show ancestry paths to proto ancestors
    if bridge_a[1] not in PROTO_LANGS:
        proto_a = _deepest_proto_ancestor(word_a, ancestors_a)
        if proto_a and proto_a not in nodes_set:
            nodes_set[proto_a] = "ancestor"
            _add_path_to_graph(ancestors_a[proto_a], proto_a, nodes_set, links)
    if bridge_b[1] not in PROTO_LANGS:
        proto_b = _deepest_proto_ancestor(word_b, ancestors_b)
        if proto_b and proto_b not in nodes_set:
            nodes_set[proto_b] = "ancestor"
            _add_path_to_graph(ancestors_b[proto_b], proto_b, nodes_set, links)

    links.append(
        GraphLink(
            source=f"{bridge_a[0]}|{bridge_a[1]}",
            target=f"{bridge_b[0]}|{bridge_b[1]}",
            reltype=reltype,
        )
    )

    nodes = [
        GraphNode(id=f"{term}|{lang}", term=term, lang=lang, type=node_type)
        for (term, lang), node_type in nodes_set.items()
    ]
    graph = GraphData(nodes=nodes, links=links)
    _enrich_with_translations(graph)
    return graph


def find_cognates(word_a: tuple[str, str], word_b: tuple[str, str]) -> CognateResponse:
    resolved_a = resolve_term(word_a[0], word_a[1])
    if not resolved_a:
        return CognateResponse(
            is_cognate=False,
            message=f"Word '{word_a[0]}' ({_lang_display(word_a[1])}) not found in etymology database.",
        )
    word_a = (resolved_a, word_a[1])

    resolved_b = resolve_term(word_b[0], word_b[1])
    if not resolved_b:
        return CognateResponse(
            is_cognate=False,
            message=f"Word '{word_b[0]}' ({_lang_display(word_b[1])}) not found in etymology database.",
        )
    word_b = (resolved_b, word_b[1])

    ancestors_a = _bfs_ancestors(word_a)
    ancestors_b = _bfs_ancestors(word_b)

    common = set(ancestors_a.keys()) & set(ancestors_b.keys())

    if not common:
        # Fuzzy proto-root matching: same root with variant reconstructions (e.g. *néwyos vs *néwos)
        fuzzy = _fuzzy_match_proto_ancestors(ancestors_a, ancestors_b)
        if fuzzy:
            proto_a, proto_b = fuzzy
            graph_data = _build_fuzzy_graph_data(
                word_a, word_b, proto_a, proto_b, ancestors_a, ancestors_b
            )
            same_lang = proto_a[1] == proto_b[1]
            path_len = len(ancestors_a[proto_a]) + len(ancestors_b[proto_b])
            if same_lang and proto_a[1] in PROTO_LANGS and path_len <= 8:
                fuzzy_confidence = "high"
            elif same_lang:
                fuzzy_confidence = "medium"
            else:
                fuzzy_confidence = "low"
            era = ERA_APPROX.get(proto_a[1], "")
            era_str = f", spoken {era}" if era else ""
            if fuzzy_confidence == "high":
                summary = f"\u00ab{word_a[0]}\u00bb and \u00ab{word_b[0]}\u00bb are related! Both descend from the {_lang_display(proto_a[1])} root {proto_a[0]}{era_str}."
            else:
                summary = f"\u00ab{word_a[0]}\u00bb and \u00ab{word_b[0]}\u00bb likely share the same root: {proto_a[0]} / {proto_b[0]} ({_lang_display(proto_a[1])})."
            return CognateResponse(
                is_cognate=True,
                common_ancestor=proto_a[0],
                ancestor_lang=_lang_display(proto_a[1]),
                graph=graph_data,
                message=f"Cognates! Common ancestor: '{proto_a[0]}' ({_lang_display(proto_a[1])})",
                summary=summary,
                confidence=fuzzy_confidence,
                ancestor_lang_code=proto_a[1],
            )

        # Weak bridge fallback: check cognate_of edges between ancestor sets
        bridge = _find_weak_bridge(ancestors_a, ancestors_b)
        if bridge:
            bridge_a, bridge_b, bridge_reltype = bridge
            graph_data = _build_weak_bridge_graph_data(
                word_a, word_b, bridge_a, bridge_b, bridge_reltype,
                ancestors_a, ancestors_b,
            )
            # Find the real proto-language ancestor (not a modern word)
            if bridge_a[1] in PROTO_LANGS:
                real_ancestor = bridge_a
            elif bridge_b[1] in PROTO_LANGS:
                real_ancestor = bridge_b
            else:
                # Neither bridge node is proto — find deepest proto ancestor from either side
                real_ancestor = _deepest_proto_ancestor(word_a, ancestors_a) or _deepest_proto_ancestor(word_b, ancestors_b)
            if real_ancestor:
                ancestor_term = real_ancestor[0]
                ancestor_lang = _lang_display(real_ancestor[1])
                ancestor_code = real_ancestor[1]
                confidence = "medium"
            else:
                ancestor_term = bridge_a[0]
                ancestor_lang = _lang_display(bridge_a[1])
                ancestor_code = bridge_a[1]
                confidence = "low"
            return CognateResponse(
                is_cognate=True,
                common_ancestor=ancestor_term,
                ancestor_lang=ancestor_lang,
                graph=graph_data,
                message=f"Cognates! '{bridge_a[0]}' ({_lang_display(bridge_a[1])}) \u2194 '{bridge_b[0]}' ({_lang_display(bridge_b[1])}) via {bridge_reltype.replace('_', ' ')}",
                summary=f"\u00ab{word_a[0]}\u00bb and \u00ab{word_b[0]}\u00bb share a common origin \u2014 connected through {ancestor_lang} {ancestor_term}.",
                confidence=confidence,
                ancestor_lang_code=ancestor_code,
            )

        graph_a = _build_single_tree(word_a, ancestors_a)
        graph_b = _build_single_tree(word_b, ancestors_b)
        root_a = _deepest_proto_ancestor(word_a, ancestors_a)
        root_b = _deepest_proto_ancestor(word_b, ancestors_b)
        if root_a and root_b:
            not_cognate_summary = (
                f"\u00ab{word_a[0]}\u00bb and \u00ab{word_b[0]}\u00bb have separate origins. "
                f"\u00ab{word_a[0]}\u00bb traces back to {root_a[0]} ({_lang_display(root_a[1])}), "
                f"while \u00ab{word_b[0]}\u00bb comes from {root_b[0]} ({_lang_display(root_b[1])})."
            )
        else:
            not_cognate_summary = f"No common ancestor found between \u00ab{word_a[0]}\u00bb and \u00ab{word_b[0]}\u00bb."
        return CognateResponse(
            is_cognate=False,
            graph_a=graph_a,
            graph_b=graph_b,
            message=f"No common ancestor found between '{word_a[0]}' and '{word_b[0]}'.",
            summary=not_cognate_summary,
        )

    def score(node: tuple[str, str]) -> tuple[int, int]:
        if node[1] == "ine-pro":
            priority = 0
        elif node[1] in PROTO_LANGS:
            priority = 1
        else:
            priority = 2
        path_len = len(ancestors_a[node]) + len(ancestors_b[node])
        return (priority, path_len)

    best = min(common, key=score)
    graph_data = _build_graph_data(word_a, word_b, best, ancestors_a, ancestors_b)

    era = ERA_APPROX.get(best[1], "")
    era_str = f", spoken {era}" if era else ""
    path_len = len(ancestors_a[best]) + len(ancestors_b[best])
    direct_confidence = "high" if best[1] in PROTO_LANGS and path_len <= 8 else "medium"
    return CognateResponse(
        is_cognate=True,
        common_ancestor=best[0],
        ancestor_lang=_lang_display(best[1]),
        graph=graph_data,
        message=f"Cognates! Common ancestor: '{best[0]}' ({_lang_display(best[1])})",
        summary=f"\u00ab{word_a[0]}\u00bb and \u00ab{word_b[0]}\u00bb are related! Both descend from the {_lang_display(best[1])} root {best[0]}{era_str}.",
        confidence=direct_confidence,
        ancestor_lang_code=best[1],
    )


def _enrich_with_translations(graph: GraphData) -> None:
    """Add modern-language reflexes to ancestor/intermediate nodes."""
    for node in graph.nodes:
        if node.type in ("ancestor", "intermediate"):
            reflexes = get_reflexes(node.term, node.lang)
            if reflexes:
                node.translations = reflexes


def _build_single_tree(
    word: tuple[str, str],
    ancestors: dict[tuple[str, str], list],
) -> GraphData | None:
    """Build a graph from a word to its deepest proto-ancestor."""
    # Find the best ancestor (prefer PIE, then other proto-langs)
    best = None
    best_score = (3, 0)
    for node, path in ancestors.items():
        if node == word:
            continue
        if node[1] == "ine-pro":
            priority = 0
        elif node[1] in PROTO_LANGS:
            priority = 1
        else:
            continue  # Only show paths to proto-langs
        score = (priority, len(path))
        if score < best_score:
            best_score = score
            best = node

    if best is None:
        return None

    path = ancestors[best]
    nodes_set: dict[tuple[str, str], str] = {}
    links: list[GraphLink] = []

    nodes_set[word] = "input"
    nodes_set[best] = "ancestor"
    _add_path_to_graph(path, best, nodes_set, links)

    nodes = [
        GraphNode(id=f"{term}|{lang}", term=term, lang=lang, type=node_type)
        for (term, lang), node_type in nodes_set.items()
    ]
    graph = GraphData(nodes=nodes, links=links)
    _enrich_with_translations(graph)
    return graph


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
    graph = GraphData(nodes=nodes, links=links)
    _enrich_with_translations(graph)
    return graph


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


def get_descendant_tree(
    root: tuple[str, str], max_nodes: int = 300, max_depth: int = 6,
) -> GraphData:
    """Reverse BFS from ancestor node to find all descendants.

    Uses a two-pass approach:
      Pass 1 – BFS with derivation reltypes only (no has_root) to build a
               proper hierarchy.
      Pass 2 – Fallback sweep for has_root edges from the root, adding only
               nodes not already discovered.
    Each node gets exactly one parent link (tree invariant).
    """
    conn = get_connection()

    nodes_set: dict[tuple[str, str], str] = {root: "ancestor"}
    parent_link: dict[tuple[str, str], GraphLink] = {}
    queue = deque([(root, 0)])
    visited = {root}

    # Pass 1: BFS without has_root — builds proper derivation hierarchy
    tree_reltypes = STRONG_RELTYPES - {"has_root"}
    placeholders = ",".join("?" * len(tree_reltypes))
    params = tuple(tree_reltypes)

    def _proto_variants(term: str, lang: str) -> list[str]:
        variants = [term]
        if lang in PROTO_LANGS:
            if term.startswith("*"):
                variants.append(term.lstrip("*"))
            else:
                variants.append("*" + term)
        return variants

    while queue and len(nodes_set) < max_nodes:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue

        term, lang = current
        variants = _proto_variants(term, lang)

        all_rows = []
        for t in variants:
            rows = conn.execute(
                f"SELECT term, lang, reltype FROM etymologies "
                f"WHERE related_term = ? AND related_lang = ? AND reltype IN ({placeholders})",
                (t, lang, *params),
            ).fetchall()
            all_rows.extend(rows)

        seen = set()
        for row in all_rows:
            child = (row["term"], row["lang"])
            key = (child, row["reltype"])
            if key in seen:
                continue
            seen.add(key)

            if child not in visited:
                visited.add(child)
                if len(nodes_set) >= max_nodes:
                    break
                nodes_set[child] = "intermediate"
                source_id = f"{current[0]}|{current[1]}"
                target_id = f"{row['term']}|{row['lang']}"
                parent_link[child] = GraphLink(
                    source=source_id, target=target_id, reltype=row["reltype"],
                )
                queue.append((child, depth + 1))

    # Pass 2: has_root fallback — pick up nodes only reachable via has_root
    root_variants = _proto_variants(root[0], root[1])
    for rt in root_variants:
        fallback_rows = conn.execute(
            "SELECT term, lang FROM etymologies "
            "WHERE related_term = ? AND related_lang = ? AND reltype = 'has_root'",
            (rt, root[1]),
        ).fetchall()
        for row in fallback_rows:
            child = (row["term"], row["lang"])
            if child not in visited and len(nodes_set) < max_nodes:
                visited.add(child)
                nodes_set[child] = "intermediate"
                source_id = f"{root[0]}|{root[1]}"
                target_id = f"{row['term']}|{row['lang']}"
                parent_link[child] = GraphLink(
                    source=source_id, target=target_id, reltype="has_root",
                )

    conn.close()

    links = list(parent_link.values())
    nodes = [
        GraphNode(id=f"{t}|{l}", term=t, lang=l, type=ntype)
        for (t, l), ntype in nodes_set.items()
    ]
    graph = GraphData(nodes=nodes, links=links)
    _enrich_with_translations(graph)
    return graph
