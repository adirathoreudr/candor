# Candor

A memory over two weeks of one person's work life (meetings, dictation, Slack, email, calendar, Codex, ChatGPT). It answers questions with the right answer for the moment asked, says who said what, cites the exact source records, and says "I don't know" when the data doesn't have it.

Work in progress. The full write-up (architecture, decisions, eval results) lands at the end of the build.

## Quick start

```bash
make run    # answers evals/memory_train.jsonl into outputs/train/memory_answers.jsonl
make eval   # scores it with the provided harness, results in results/<commit>/
make test
```

Needs [uv](https://docs.astral.sh/uv/) (`brew install uv`). Python 3.12 is installed by uv.
