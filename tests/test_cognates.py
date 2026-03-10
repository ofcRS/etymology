import pytest

from backend.graph import find_cognates, get_descendant_tree


# --- MUST-PASS COGNATE PAIRS ---
# Each: (word_a, lang_a, word_b, lang_b, expected_ancestor_fragment_or_None)
MUST_PASS_COGNATE = [
    ("мать", "ru", "mother", "en", "méh₂tēr"),
    ("три", "ru", "three", "en", None),
    ("нос", "ru", "nose", "en", None),
    ("новый", "ru", "new", "en", "néw"),
    ("ночь", "ru", "night", "en", "nókʷt"),
    ("вода", "ru", "water", "en", "wed"),
    ("сердце", "ru", "heart", "en", "ḱerd"),
    ("берёза", "ru", "birch", "en", None),
    ("живой", "ru", "vivid", "en", None),
    ("колесо", "ru", "wheel", "en", "kʷel"),
    ("зерно", "ru", "corn", "en", None),
    ("имя", "ru", "name", "en", None),
    ("молоко", "ru", "milk", "en", "h₂melǵ"),
    ("яблоко", "ru", "apple", "en", None),
    ("хлеб", "ru", "loaf", "en", None),
    ("тон", "ru", "tune", "en", None),
    ("церковь", "ru", "church", "en", None),
    ("князь", "ru", "king", "en", None),
]

# --- MUST-PASS NOT-COGNATE PAIRS ---
MUST_PASS_NOT_COGNATE = [
    ("время", "ru", "time", "en"),
    ("большой", "ru", "big", "en"),
    ("стол", "ru", "table", "en"),
    ("хлеб", "ru", "bread", "en"),
    ("правый", "ru", "right", "en"),
]

# --- KNOWN FAILURES (xfail) ---
KNOWN_FAILURES = [
    ("кошка", "ru", "cat", "en", "data gap - stops at *koťьka / *kattu"),
    ("дым", "ru", "fume", "en", "дым has no graph at all"),
    ("звезда", "ru", "star", "en", "conflicting PIE reconstructions"),
]


MODERN_LANGS = {"ru", "en", "de", "fr", "es", "it", "pt", "nl", "pl", "cs", "el", "hy", "fa", "ar"}


def _assert_ancestor_is_proto(result, w1, w2):
    """ancestor_lang must be a proto-language, never a modern language."""
    lang = result.ancestor_lang or ""
    assert lang.startswith("Proto") or lang == "PIE", (
        f"ancestor_lang must be proto-language, got '{lang}' for {w1}/{w2}"
    )


def _assert_no_input_as_ancestor(result, w1, w2):
    """No input node should be marked as ancestor in the graph."""
    if not result.graph:
        return
    input_ids = set()
    ancestor_ids = set()
    for n in result.graph.nodes:
        if n.type == "input":
            input_ids.add(n.id)
        if n.type == "ancestor":
            ancestor_ids.add(n.id)
    overlap = input_ids & ancestor_ids
    assert not overlap, (
        f"Input node(s) marked as ancestor: {overlap} for {w1}/{w2}"
    )


def _assert_graph_structure(result, w1, w2):
    """Graph should have at least 3 nodes (2 inputs + 1 ancestor)."""
    if not result.graph:
        return
    assert len(result.graph.nodes) >= 3, (
        f"Expected at least 3 nodes in graph for {w1}/{w2}, got {len(result.graph.nodes)}"
    )
    assert len(result.graph.links) >= 2, (
        f"Expected at least 2 links in graph for {w1}/{w2}, got {len(result.graph.links)}"
    )


def _assert_ancestor_lang_code_is_proto(result, w1, w2):
    """ancestor_lang_code must be a proto-language code."""
    from backend.graph import PROTO_LANGS
    code = result.ancestor_lang_code
    assert code in PROTO_LANGS, (
        f"ancestor_lang_code must be a proto-lang code, got '{code}' for {w1}/{w2}"
    )


@pytest.mark.parametrize("w1,l1,w2,l2,expected_ancestor", MUST_PASS_COGNATE)
def test_cognate_pair(w1, l1, w2, l2, expected_ancestor):
    result = find_cognates((w1, l1), (w2, l2))

    # 1. Must be cognate
    assert result.is_cognate is True, f"Expected cognate for {w1}/{w2}: {result.message}"

    # 2. ancestor_lang must be a proto-language
    _assert_ancestor_is_proto(result, w1, w2)

    # 3. ancestor_lang_code must be a proto-language code
    _assert_ancestor_lang_code_is_proto(result, w1, w2)

    # 4. No input node should be marked as ancestor in the graph
    _assert_no_input_as_ancestor(result, w1, w2)

    # 5. Graph should have reasonable structure
    _assert_graph_structure(result, w1, w2)

    # 6. If expected ancestor is provided, fuzzy-match it
    if expected_ancestor:
        ancestor = result.common_ancestor or ""
        assert expected_ancestor in ancestor, (
            f"Expected ancestor containing '{expected_ancestor}', got '{ancestor}' for {w1}/{w2}"
        )

    # 7. Summary must exist
    assert result.summary is not None


@pytest.mark.parametrize("w1,l1,w2,l2", MUST_PASS_NOT_COGNATE)
def test_not_cognate_pair(w1, l1, w2, l2):
    result = find_cognates((w1, l1), (w2, l2))
    assert result.is_cognate is False, f"Expected not cognate for {w1}/{w2}: {result.message}"
    assert result.common_ancestor is None, (
        f"Not-cognate should have no common_ancestor, got '{result.common_ancestor}' for {w1}/{w2}"
    )


@pytest.mark.parametrize("w1,l1,w2,l2,issue", KNOWN_FAILURES)
@pytest.mark.xfail(reason="Known data gap")
def test_known_issue(w1, l1, w2, l2, issue):
    result = find_cognates((w1, l1), (w2, l2))
    assert result.is_cognate is True, f"Known issue: {issue}"


# --- TREE VIEW TESTS (unchanged) ---

def test_descendant_tree_mother():
    tree = get_descendant_tree(("*méh₂tēr", "ine-pro"))
    assert len(tree.nodes) > 10
    assert any(n.term == "mother" for n in tree.nodes)
    assert any(n.lang == "ru" for n in tree.nodes)
    ancestor = [n for n in tree.nodes if n.type == "ancestor"]
    assert len(ancestor) == 1
    assert ancestor[0].term == "*méh₂tēr"


def test_descendant_tree_milk():
    tree = get_descendant_tree(("*h₂melǵ-", "ine-pro"))
    assert len(tree.nodes) > 10
    assert any(n.term == "milk" and n.lang == "en" for n in tree.nodes)


def test_descendant_tree_max_nodes():
    """Large trees should be capped at max_nodes."""
    tree = get_descendant_tree(("*per-", "ine-pro"), max_nodes=50)
    assert len(tree.nodes) <= 50


def test_cognate_response_has_lang_code():
    """Cognate responses include ancestor_lang_code for tree expansion."""
    result = find_cognates(("water", "en"), ("вода", "ru"))
    assert result.is_cognate is True
    assert result.ancestor_lang_code == "ine-pro"
