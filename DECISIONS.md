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
| 12 | Hybrid retrieval: BM25 + dense, reciprocal rank fusion, over versioned docs (one per edit, each valid over a time window) | BM25 only, dense only | Exact names/numbers need BM25, paraphrase needs dense; versioning makes edits searchable only from edit time (test) | settled |
| 13 | Embeddings: `BAAI/bge-small-en-v1.5`, batch 8, 2 threads, text capped at 2,000 chars, checkpointed chunks, committed | bge-base with library defaults | bge-base at batch 256 froze an 8 GB MacBook Air M2 (observed twice). Small model: 50 s, peak RSS 431 MB (measured) | settled; revisit base vs small on recall |
| 14 | LLM provider: Groq free tier, `openai/gpt-oss-120b` | NVIDIA NIM, Gemini 3.8 Flash | NIM account key never authenticated (401). Gemini free tier = 20 requests/day (measured 429). Groq free: 30 RPM, 1K RPD, 8K TPM, 200K TPD (published) | settled for now |
| 15 | Daily-quota 429 stops the run with one clear message; per-minute 429 waits for `retry-after` | blind retries | Retrying a daily quota just burns time | settled |
| 16 | Explicit `User-Agent` on LLM requests | urllib default | Groq's Cloudflare returns 403 "error code: 1010" for `Python-urllib` (measured) | settled |
| 17 | P3 builds memory structure deterministically; LLM query planning and reranking move to P4 | LLM extraction pass over the whole corpus | Groq free tier is 200K tokens/day per model; one eval is ~49K. A full-corpus extraction (~150K input tokens) would cost a day of budget. Retrieval-only experiments cost 0 tokens and ~2 s each | settled |
| 18 | Snowball stemming, addresses split into name parts | light suffix rules | +8.0 pts retrieval (measured) | settled |
| 19 | Content and header as separate BM25 fields | one text field | +12.0 pts; flat across header weights 0.0 to 1.0, so the split matters, not the weight (measured) | settled |
| 20 | Records with < 3 content terms rank after all others | no demotion | +4.0 pts; plateau at thresholds 3 to 5; no train evidence demoted (measured) | settled |
| 21 | Link graph; ranking uses email-thread and dictation->sent links only, weight 0.3 | all links, weight 0.5 | +4.0 pts. Meeting->calendar links: 76.0%; Slack thread links: 80.0% (ablation, measured) | settled |
