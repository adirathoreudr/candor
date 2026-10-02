import sys
from datetime import datetime

import pytest

from candor import config, ingest
from candor.io import read_jsonl
from candor.store import Memory

# The organizer's harness is the reference for ids, delivery times and visibility.
sys.path.insert(0, str(config.ROOT / "eval_harness"))
import records  # noqa: E402


@pytest.fixture(scope="session")
def corpus():
    return ingest.load(config.DATA_DIR)


@pytest.fixture(scope="session")
def memory(corpus):
    return Memory(corpus)


@pytest.fixture(scope="session")
def harness():
    return records


@pytest.fixture(scope="session")
def train_as_ofs():
    rows = read_jsonl(config.ROOT / "evals/memory_train.jsonl") + read_jsonl(config.ROOT / "evals/actions_train.jsonl")
    return sorted({datetime.fromisoformat(r["as_of"]) for r in rows})
