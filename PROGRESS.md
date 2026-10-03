# Progress

Eval log (measured, train set, `make eval`, judge none unless noted) and failures worth reporting.

## Eval log

| Commit | Change | Retrieval | Answers strict | Notes |
|---|---|---|---|---|
| P0 | abstain on everything (floor) | 0.0% | 7.4% | only the 2 unanswerable questions pass |
| P2 | hybrid BM25 + bge-small, RRF; answer.v1 on gpt-oss-120b (Groq) | 60.0% | 74.1% | MRR 0.57; 0 forbidden; 0 hard failures; 27 calls, 38.7K prompt tokens, 294 s; cached rerun identical in 1 s |

| P3 | stemming + address split | 68.0% | | retrieval-only step |
| P3 | content/header BM25 fields | 80.0% | | flat across header weights 0.0 to 1.0 |
| P3 | near-empty records ranked last | 84.0% | | plateau at thresholds 3 to 5 |
| P3 | link graph (email thread, dictation->sent) | 88.0% | 81.5% | MRR 0.569; 0 forbidden; 0 hard failures; source precision 0.91; 27 calls, 42.3K prompt tokens |

| P4 | planner (plan.v1) only | 88.0% | | top-5 coverage 68% -> 84%; fixes TR-20, TR-25; loses TR-09, TR-12 |
| P4 | + reranker (rerank.v1) | 96.0% | | MRR 0.900; top-5 92%; 0 forbidden |
| P4 | + answer.v2 | 96.0% | 96.3% | source precision 0.951; 0 hard failures; answer model 46.8K prompt tokens |

### P4 failures

Retrieval: TR-21 ("why did the launch slip from Sep 30") misses the root cause record; the answer is still right from other evidence.
Answers: TR-08 leaves out that "John agreed" came second-hand from Dana.

### P3 failures (fed P4)

Retrieval (3 miss): TR-21 vocabulary gap ("slip" vs "geocoding regression"); TR-25 two-hop (flight date, then that day's calendar); TR-20 date-bound ("on Sep 10"), the dictation ranks 48.
Answers (5 wrong): TR-20, 21, 25 follow those misses; TR-26 abstains although its evidence is retrieved; TR-08 misses that Dana reported John's agreement.

### P2 failures by bucket (fed P3)

Retrieval (10 of 25 scored questions miss):
- Launch-date chain (TR-01, 02, 21, 22): many records mention the product; the specific date-change records rank 11 to 19.
- Cross-source joins (TR-04, 12, 20, 25): one side found, the other not (dictation vs sent email, flight email vs calendar).
- Vocabulary gap (TR-05, 26): "pricing proposal", "signed the contract" don't share words with the evidence.

Answers (7 wrong): 4 follow retrieval misses (TR-01, 02 wrong date; TR-25 no board meeting); 3 abstain because the evidence wasn't retrieved (TR-05, 20, 26); TR-08 misses the reported-speech chain (Dana).

## What didn't work

- NVIDIA NIM: the account key never authenticated (401 on every model).
- Gemini 3.8 Flash free tier: 20 requests per day, exhausted after 8 eval questions (429 with a 15 h reset).
- Local embeddings with library defaults (bge-base, batch 256, all cores) froze an 8 GB MacBook Air twice.
- Lifting all linked records: meeting -> calendar links flooded the top 10 with one event (76.0%), Slack thread links pulled in off-topic replies (80.0%). Kept only email-thread and dictation links.
- A planner rule to add a second hop for "why" questions (plan.v2): the planner model ignored it, and a forced second hop wrote generic queries that ranked the cause record lower (31st -> 80th). Reverted to plan.v1.
