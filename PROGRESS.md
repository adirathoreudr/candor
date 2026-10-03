# Progress

Eval log (measured, train set, `make eval`, judge none unless noted) and failures worth reporting.

## Eval log

| Commit | Change | Retrieval | Answers strict | Notes |
|---|---|---|---|---|
| P0 | abstain on everything (floor) | 0.0% | 7.4% | only the 2 unanswerable questions pass |
| P2 | hybrid BM25 + bge-small, RRF; answer.v1 on gpt-oss-120b (Groq) | 60.0% | 74.1% | MRR 0.57; 0 forbidden; 0 hard failures; 27 calls, 38.7K prompt tokens, 294 s; cached rerun identical in 1 s |

### P2 failures by bucket (feeds P3/P4)

Retrieval (10 of 25 scored questions miss):
- Launch-date chain (TR-01, 02, 21, 22): many records mention the product; the specific date-change records rank 11 to 19.
- Cross-source joins (TR-04, 12, 20, 25): one side found, the other not (dictation vs sent email, flight email vs calendar).
- Vocabulary gap (TR-05, 26): "pricing proposal", "signed the contract" don't share words with the evidence.

Answers (7 wrong): 4 follow retrieval misses (TR-01, 02 wrong date; TR-25 no board meeting); 3 abstain because the evidence wasn't retrieved (TR-05, 20, 26); TR-08 misses the reported-speech chain (Dana).

## What didn't work

- NVIDIA NIM: the account key never authenticated (401 on every model).
- Gemini 3.8 Flash free tier: 20 requests per day, exhausted after 8 eval questions (429 with a 15 h reset).
- Local embeddings with library defaults (bge-base, batch 256, all cores) froze an 8 GB MacBook Air twice.
