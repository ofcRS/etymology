import pytest

from backend.graph import find_cognates, get_descendant_tree


COGNATE_PAIRS = [
    ("мать", "ru", "mother", "en"),
    ("три", "ru", "three", "en"),
    ("нос", "ru", "nose", "en"),
    ("новый", "ru", "new", "en"),
    ("ночь", "ru", "night", "en"),
    ("вода", "ru", "water", "en"),
    ("сердце", "ru", "heart", "en"),
    ("берёза", "ru", "birch", "en"),
    ("живой", "ru", "vivid", "en"),
    ("колесо", "ru", "wheel", "en"),
    ("зерно", "ru", "corn", "en"),
    ("имя", "ru", "name", "en"),
    ("молоко", "ru", "milk", "en"),
    ("яблоко", "ru", "apple", "en"),
    ("хлеб", "ru", "loaf", "en"),
    ("тон", "ru", "tune", "en"),
    ("церковь", "ru", "church", "en"),
    ("князь", "ru", "king", "en"),
]

NOT_COGNATE_PAIRS = [
    ("время", "ru", "time", "en"),
    ("большой", "ru", "big", "en"),
    ("стол", "ru", "table", "en"),
    ("хлеб", "ru", "bread", "en"),
    ("правый", "ru", "right", "en"),
]

KNOWN_ISSUES = [
    ("кошка", "ru", "cat", "en", "data gap - stops at *koťьka / *kattu"),
    ("дым", "ru", "fume", "en", "дым has no graph at all"),
    ("звезда", "ru", "star", "en", "conflicting PIE reconstructions"),
]


@pytest.mark.parametrize("w1,l1,w2,l2", COGNATE_PAIRS)
def test_cognate_pair(w1, l1, w2, l2):
    result = find_cognates((w1, l1), (w2, l2))
    assert result.is_cognate is True, f"Expected cognate for {w1}/{w2}: {result.message}"
    assert result.summary is not None
    assert result.ancestor_lang_code is not None


@pytest.mark.parametrize("w1,l1,w2,l2", NOT_COGNATE_PAIRS)
def test_not_cognate_pair(w1, l1, w2, l2):
    result = find_cognates((w1, l1), (w2, l2))
    assert result.is_cognate is False, f"Expected not cognate for {w1}/{w2}: {result.message}"


@pytest.mark.parametrize("w1,l1,w2,l2,issue", KNOWN_ISSUES)
@pytest.mark.xfail(reason="Known data gap")
def test_known_issue(w1, l1, w2, l2, issue):
    result = find_cognates((w1, l1), (w2, l2))
    assert result.is_cognate is True, f"Known issue: {issue}"


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
