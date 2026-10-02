# Decisions

One row per decision. Evidence is measured unless marked otherwise.

| # | Decision | Options considered | Evidence / reason | Status |
|---|---|---|---|---|
| 1 | Python 3.12, uv, Makefile command contract | TypeScript, plain pip | Harness is stdlib Python; uv gives a pinned, one-command setup on a Mac | settled |
| 2 | No editable install; run from `src/` via `PYTHONPATH` | editable install | macOS flagged the venv `.pth` files hidden and Python 3.12 skipped them (`ModuleNotFoundError`, measured) | settled |
| 3 | Retrieval works with no LLM key; LLM layers turn on when a backend exists | LLM-only pipeline | Retrieval is the main score and must survive a missing key on the organizer's machine | settled |
| 4 | LLM backends: OpenAI-compatible (NVIDIA NIM default) and `claude-cli` | one provider | Organizer's own judge uses Claude Code; NIM is free | settled |
| 5 | Every LLM call: temperature 0, JSON output, cached by input hash, cache committed | live calls only | Reruns must match for the hidden-test re-check | settled |
| 6 | Budget ₹0 | paid models | user constraint | settled |
| 7 | Commit the provided data and harness unchanged | data path argument only | one-command run from a clean clone; organizer asked | pending organizer reply |
| 8 | Unit ids, delivery times, deletes and edits reproduce `eval_harness/records.py` exactly | own interpretation of data/README | The scorer judges against that file; parity is a test, at every train `as_of` | settled |
| 9 | Secrets redacted once at ingest, by credential shape (key prefixes, URL passwords, `*_PASSWORD=` style) | filter at answer time | Nothing downstream (index, prompts, answers) can leak what it never saw; prose like "email and password" untouched (test) | settled |
| 10 | HTML comments removed at ingest and the unit flagged | keep as text | A reader never sees them; the planted instruction lives in one | settled |
| 11 | Deletion events are never visible units | index them | They carry no content, only "message X was deleted" | settled |
