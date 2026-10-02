import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_run_writes_one_answer_per_question(tmp_path):
    out = tmp_path / "answers.jsonl"
    subprocess.run([sys.executable, "-m", "candor.cli", "run",
                    "--questions", str(ROOT / "examples/memory_questions.example.jsonl"), "--out", str(out)],
                   check=True, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    questions = [json.loads(l) for l in open(ROOT / "examples/memory_questions.example.jsonl")]
    answers = [json.loads(l) for l in open(out)]
    assert [a["id"] for a in answers] == [q["id"] for q in questions]
    for a in answers:
        assert set(a) == {"id", "answer", "sources", "retrieved", "abstained"}
