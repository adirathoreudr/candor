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
| 22 | LLM query planner: rewrites, date window, optional second hop | question-only search | Alone: retrieval flat at 88.0% but top-5 coverage 68% -> 84%; fixes date-bound and two-hop questions (measured) | settled |
| 23 | Date window list weighted 3x in fusion; calendar events count on the days they occur | window as one more list | At 1x the board meeting on the flight day ranked 40th (measured) | settled |
| 24 | LLM reranker over top 30 + linked records of the top 10; unpicked keep fused order | no rerank; rerank that drops | Retrieval 88.0% -> 96.0%, MRR 0.569 -> 0.900 (measured). Demote-never-drop keeps a judge mistake recoverable | settled |
| 25 | One model per role: plan gpt-oss-20b, rerank qwen3.8-27b, answer gpt-oss-120b (Groq) | one model | Each has its own 200K tokens/day free quota; one full eval spends ~30K / ~85K / ~50K | settled |
| 26 | answer.v2: a status short of the asked state is an answer; separate first-hand from reported speech; give each side's reason | answer.v1 | Answers 81.5% -> 96.3% (measured) | settled |
| 28 | Action planner: LLM proposes in human terms, code resolves ids, offsets, durations; unresolvable -> clarify | LLM emits final ids and ISO times | Train 12/12 on first run (measured). The LLM never does offset math; a name that is not in the data cannot become an id | settled |
| 29 | Deterministic weekday guard and next-occurrence event listing | trust the LLM's dates | Hidden-style dev set: "Monday" became Friday and a past Friday was used (10/12); both fixed by code, not prompt (measured) | settled |
| 30 | Action role on gpt-oss-20b | gpt-oss-120b | 120b: train 12/12 (before the guard). 20b with the guard: train 12/12, dev 11/12 (measured). Separate quota from the answer model, which ran out (200K tokens/day) | settled; revisit 120b on dev when quota allows |
| 27 | Adversarial dev set checked by rules, not gold answers | train set only | Train has one injection question and no secret, deletion or edit-boundary questions; rule checks cannot be tuned against | settled |
