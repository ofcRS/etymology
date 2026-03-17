"""Load and serve pre-computed cognate pairs from JSON."""

import json
import logging
import random
from pathlib import Path

from backend.models import CognatePair

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "cognate_pairs.json"

_pairs: list[dict] = []

if DATA_PATH.exists():
    with open(DATA_PATH, encoding="utf-8") as f:
        _pairs = json.load(f)
    logger.info("Loaded %d cognate pairs from %s", len(_pairs), DATA_PATH)
else:
    logger.warning("Cognate pairs file not found at %s", DATA_PATH)


def get_random_pair() -> CognatePair | None:
    if not _pairs:
        return None
    return CognatePair(**random.choice(_pairs))


def get_random_pairs(n: int) -> list[CognatePair]:
    if not _pairs:
        return []
    selected = random.sample(_pairs, min(n, len(_pairs)))
    return [CognatePair(**p) for p in selected]
