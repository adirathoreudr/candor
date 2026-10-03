"""Hidden-test traps the train set barely covers: secrets, deletions, edits, planted instructions,
unidentified speakers, false premises, future leakage. `make dev` writes the answers; these checks are
rules, not gold answers, so they cannot be tuned against.
"""
from datetime import datetime

import pytest

from candor import config
from candor.io import read_jsonl

QUESTIONS = config.ROOT / "devset/adversarial.jsonl"
ANSWERS = config.ROOT / "outputs/dev/adversarial_answers.jsonl"


def _cases():
    answers = {a["id"]: a for a in read_jsonl(ANSWERS)}
    return [(q, answers[q["id"]]) for q in read_jsonl(QUESTIONS)]


@pytest.mark.parametrize("q,a", _cases(), ids=lambda x: x["id"] if isinstance(x, dict) and "trap" in x else "")
def test_trap(q, a, harness):
    ctx = harness.context(config.DATA_DIR)
    checks, text = q["checks"], a["answer"].lower()
    as_of = datetime.fromisoformat(q["as_of"])
    for i in a["retrieved"] + a["sources"]:
        assert ctx["avail"][i] <= as_of and not (i in ctx["deleted"] and ctx["deleted"][i] <= as_of), i
    for phrase in checks.get("never_say", []):
        assert phrase.lower() not in text, f"{q['trap']}: answer says {phrase!r}"
    for i in checks.get("forbid_ids", []):
        assert i not in a["retrieved"] and i not in a["sources"], f"{q['trap']}: retrieved {i}"
    if checks.get("must_retrieve_any"):
        assert set(checks["must_retrieve_any"]) & set(a["retrieved"][:10]), f"{q['trap']}: evidence not in top 10"
    if checks.get("must_say_any"):
        assert any(p.lower() in text for p in checks["must_say_any"]), f"{q['trap']}: {a['answer']!r}"
    if "expect_abstain" in checks:
        abstained = a["abstained"] or text.startswith("i don't know")
        assert abstained == checks["expect_abstain"], f"{q['trap']}: abstained={abstained}: {a['answer']!r}"
