from datetime import timedelta

import pytest

from candor import config
from candor.index import Index
from candor.io import read_jsonl
from candor.llm import parse_json
from candor.text import tokenize


@pytest.fixture(scope="session")
def index(memory):
    return Index(memory)


def test_search_never_returns_forbidden_ids(index, memory, train_as_ofs):
    for q in read_jsonl(config.ROOT / "evals/memory_train.jsonl"):
        for as_of in train_as_ofs:
            for uid, _ in index.search(q["question"], as_of, k=20):
                assert memory.is_visible(uid, as_of), (q["id"], uid, as_of)


def test_edited_text_is_searchable_only_from_edit_time(index, memory):
    target, history = next(iter(memory.corpus.edits.items()))
    edit_time, new_text = history[-1]
    versions = [d for d in index.docs if d.unit_id == target]
    assert len(versions) == len(history) + 1
    before, after = index.mask(edit_time - timedelta(seconds=1)), index.mask(edit_time)
    new_doc = next(i for i, d in enumerate(index.docs) if d.unit_id == target and d.valid_from == edit_time)
    old_doc = next(i for i, d in enumerate(index.docs) if d.unit_id == target and d.valid_from < edit_time)
    assert not before[new_doc] and after[new_doc]
    assert before[old_doc] and not after[old_doc]


def test_search_ranks_unique_ids(index, train_as_ofs):
    ids = [uid for uid, _ in index.search("launch date", train_as_ofs[-1], k=20)]
    assert len(ids) == len(set(ids)) == 20


def test_tokenize_keeps_numbers_and_drops_stopwords():
    assert tokenize("The p95 latency is 1.8s for 64 cases") == ["p95", "latenc", "1.8s", "64", "case"]


def test_tokenize_stems_and_splits_addresses():
    assert tokenize("dictated a dictation") == ["dictat", "dictat"]
    assert {"sarah", "patel"} <= set(tokenize("to sarah.patel@acme.example.com"))


def test_parse_json_tolerates_fences_and_reasoning():
    assert parse_json('<think>hmm {"x": 0}</think>```json\n{"answer": "ok", "n": 2}\n```') == {"answer": "ok", "n": 2}
    with pytest.raises(ValueError):
        parse_json("no json here")
