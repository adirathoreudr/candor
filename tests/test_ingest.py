import re
from collections import Counter

from candor import config
from candor.ingest import ASSISTANT, BOT, UNIDENTIFIED
from candor.sanitize import REDACTED, clean


def test_unit_ids_and_times_match_harness(corpus, harness):
    ref, _, _ = harness.load(config.DATA_DIR)
    ours = {u.id: (u.record, u.time) for u in corpus.units}
    theirs = {u.id: (u.record, u.time) for u in ref}
    assert ours == theirs


def test_deletes_and_edits_match_harness(corpus, harness):
    _, deleted, edits = harness.load(config.DATA_DIR)
    assert corpus.deleted == deleted
    assert {k: [t for t, _ in v] for k, v in corpus.edits.items()} == {k: [t for t, _ in v] for k, v in edits.items()}


def test_counts_per_source(corpus):
    assert Counter(u.source for u in corpus.units) == {
        "meeting": 889, "slack": 230, "gmail": 58, "dictation": 42, "calendar": 37, "codex": 4, "chatgpt": 56}


def test_owner_is_detected_from_data(corpus):
    assert corpus.owner == "Alex Rivera"


def test_no_secret_survives_ingest(corpus):
    key_like = re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}")
    url_creds = re.compile(r"://[^\s:/@]+:(?!\[REDACTED)[^\s@/]+@")
    for u in corpus.units:
        assert not key_like.search(u.text), u.id
        assert not url_creds.search(u.text), u.id
        assert not key_like.search(u.meta.get("raw_transcript") or ""), u.id


def test_redaction_keeps_ordinary_prose():
    prose = "For the pilot I can live with email and password. The theme tokens: done."
    assert clean(prose)[0] == prose
    assert clean("POSTGRES_PASSWORD: hunter2")[0] == f"POSTGRES_PASSWORD: {REDACTED}"
    assert clean("postgresql://eta:hunter2@localhost:5432/eta")[0] == f"postgresql://eta:{REDACTED}@localhost:5432/eta"


def test_hidden_html_comments_are_removed(corpus):
    flagged = [u for u in corpus.units if u.meta.get("hidden_markup")]
    assert flagged, "expected at least one record with hidden markup"
    for u in flagged:
        assert "<!--" not in u.text


def test_authorship_kinds(corpus):
    kinds = Counter(u.author_kind for u in corpus.units)
    assert kinds[BOT] == 29
    assert kinds[ASSISTANT] == sum(1 for u in corpus.units if u.source == "chatgpt" and u.meta["role"] == "assistant")
    assert kinds[UNIDENTIFIED] == 9
