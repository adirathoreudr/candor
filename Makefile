QUESTIONS ?= evals/memory_train.jsonl
ANSWERS   ?= outputs/train/memory_answers.jsonl
RESULTS   := results/$(shell git describe --always --dirty 2>/dev/null || echo nogit)
# nice: keep the laptop responsive while embeddings build
PY        := PYTHONPATH=src nice -n 10 uv run --frozen python

.PHONY: run eval dev test setup check-uv

check-uv:
	@command -v uv >/dev/null || { echo "uv is required: brew install uv  (or see https://docs.astral.sh/uv/)"; exit 1; }

setup: check-uv
	@uv sync --frozen --quiet

## Answer a questions file: make run QUESTIONS=path ANSWERS=path
run: setup
	@$(PY) -m candor.cli run --questions $(QUESTIONS) --out $(ANSWERS)

## Score the train answers with the provided harness; results land in results/<commit>/
eval: run
	@mkdir -p $(RESULTS)
	@$(PY) eval_harness/score_retrieval.py --gold $(QUESTIONS) --answers $(ANSWERS) --out $(RESULTS)/retrieval.json --quiet
	@$(PY) eval_harness/score_memory.py --gold $(QUESTIONS) --answers $(ANSWERS) --judge none --out $(RESULTS)/memory.json --quiet

## Adversarial dev set (secrets, deletions, edits, planted instructions): answers then rule checks
dev: setup
	@$(PY) -m candor.cli run --questions devset/adversarial.jsonl --out outputs/dev/adversarial_answers.jsonl
	@PYTHONPATH=src uv run --frozen pytest -q tests/test_adversarial.py

test: setup
	@uv run --frozen pytest -q
