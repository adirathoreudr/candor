QUESTIONS ?= evals/memory_train.jsonl
ANSWERS   ?= outputs/train/memory_answers.jsonl
COMMANDS  ?= evals/actions_train.jsonl
ACTIONS   ?= outputs/train/action_predictions.jsonl
RESULTS   := results/$(shell git describe --always --dirty 2>/dev/null || echo nogit)
# nice: keep the laptop responsive while embeddings build
PY        := PYTHONPATH=src nice -n 10 uv run --frozen python

.PHONY: all run act eval eval-actions dev dev-actions test setup check-uv

## Everything the hidden test needs: memory answers and action predictions
all: run act

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

## Dry-run a commands file into actions: make act COMMANDS=path ACTIONS=path
act: setup
	@$(PY) -m candor.cli act --commands $(COMMANDS) --out $(ACTIONS)

## Score the train action predictions with the provided harness
eval-actions: act
	@mkdir -p $(RESULTS)
	@$(PY) eval_harness/score_actions.py --gold $(COMMANDS) --predictions $(ACTIONS) --out $(RESULTS)/actions.json

## Hidden-style action dev set, scored with the provided harness
dev-actions: setup
	@$(PY) -m candor.cli act --commands devset/actions_dev.jsonl --out outputs/dev/action_predictions.jsonl
	@$(PY) eval_harness/score_actions.py --gold devset/actions_dev.jsonl --predictions outputs/dev/action_predictions.jsonl --out results/dev_actions.json

## Adversarial dev set (secrets, deletions, edits, planted instructions): answers then rule checks
dev: setup
	@$(PY) -m candor.cli run --questions devset/adversarial.jsonl --out outputs/dev/adversarial_answers.jsonl
	@PYTHONPATH=src uv run --frozen pytest -q tests/test_adversarial.py

test: setup
	@uv run --frozen pytest -q
