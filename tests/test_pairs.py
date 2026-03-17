import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.graph import find_cognates

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "cognate_pairs.json"

client = TestClient(app)


def test_json_file_exists():
    assert DATA_PATH.exists(), "cognate_pairs.json must exist"


def test_json_well_formed():
    with open(DATA_PATH, encoding="utf-8") as f:
        pairs = json.load(f)
    assert isinstance(pairs, list)
    assert len(pairs) >= 50, f"Expected at least 50 pairs, got {len(pairs)}"
    required_keys = {"word_a", "lang_a", "word_b", "lang_b", "ancestor", "confidence"}
    for pair in pairs:
        assert required_keys.issubset(pair.keys()), f"Missing keys in pair: {pair}"


def test_random_pair_endpoint():
    res = client.get("/api/random-pair")
    assert res.status_code == 200
    data = res.json()
    assert "word_a" in data
    assert "word_b" in data
    assert "ancestor" in data


def test_pairs_endpoint_default():
    res = client.get("/api/pairs")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 6


def test_pairs_endpoint_custom_limit():
    res = client.get("/api/pairs?limit=3")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3


def test_spot_check_sample_pairs():
    """Validate a small sample of pairs from the JSON are actually cognates."""
    with open(DATA_PATH, encoding="utf-8") as f:
        pairs = json.load(f)

    # Check first 5 pairs
    sample = pairs[:5]
    for pair in sample:
        result = find_cognates(
            (pair["word_b"], pair["lang_b"]),
            (pair["word_a"], pair["lang_a"]),
        )
        assert result.is_cognate, (
            f"Pair {pair['word_a']}/{pair['word_b']} should be cognate but got: {result.message}"
        )
