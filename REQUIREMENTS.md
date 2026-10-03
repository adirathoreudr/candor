# Requirements

Extracted from `BRIEF.md` (line numbers in brackets) and the organizer's email. Precedence: email, then BRIEF.md, then data/README.md.

## Deadline and delivery

| ID | Requirement | Source |
|---|---|---|
| D1 | Deadline Mon 5 Oct 2026, 14:00 IST. The Friday date in the brief is void. | email |
| D2 | Public GitHub repo that runs everything with one command, on a Mac. | email, [118, 143] |
| D3 | README (no slides): architecture, key decisions and why, what didn't work and known limits, how to run, eval results, tools and models used with rough spend. | [144, 138] |
| D4 | Submitted commit hash. No code changes after the deadline. | [145, 121] |
| D5 | Output files on the train sets from that commit: memory answers, and action predictions if the bonus is built. | [146] |
| D6 | Optional demo video, 5 min max. Counts toward bonus design. | [147] |
| D7 | Any keys go in `.env.example` with instructions. | [118] |
| D8 | Hidden test: either they run the commit, or they send questions and we return outputs within 24 h; some get re-run to check they match. Outputs must be reproducible. | [117-121] |

## Memory interface

| ID | Requirement | Source |
|---|---|---|
| M1 | Input JSONL: `id`, `question`, `as_of`. Output JSONL per question: `id`, `answer`, `sources`, `retrieved`, `abstained`. | [62-75] |
| M2 | `as_of`: answer as of that moment; nothing after it exists. | [71] |
| M3 | `retrieved` is the main score: up to 20 ids, ranked best first, top 10 scored. Not sorted by id or date. | [72] |
| M4 | `sources`: ids the answer relies on. | [73] |
| M5 | Most specific id: meeting segment over meeting, ChatGPT message over conversation. | [74] |
| M6 | `abstained: true`, or an answer starting "I don't know", means not in memory. | [75] |
| M7 | Answers over 120 words that look like pasted records count as wrong in the strict score. | [112] |

## Hard rules (break one, fail the question)

| ID | Requirement | Source |
|---|---|---|
| H1 | Never retrieve or cite a record delivered after `as_of`. Delivery time per source is in `data/README.md`. | [78], data/README |
| H2 | Deleted messages are gone from deletion time: never retrieve, cite or repeat them. Edits replace old text from edit time. | [79] |
| H3 | Never repeat a secret (API keys, passwords) found in the data. | [80] |
| H4 | Text inside the data is content, never instructions. Don't obey or repeat planted instructions. | [81] |

## What is graded

| ID | Requirement | Source |
|---|---|---|
| G1 | Retrieval: fetch the right records. Main score. | [37] |
| G2 | Time: current value, value at a moment, what changed and why. | [38], [10] |
| G3 | Who said what, including uncertain speakers and second-hand claims. Disagreement is not the same as change. | [39], [11-12] |
| G4 | Grounding: every answer points to its source records. | [40] |
| G5 | Abstention: say "I don't know" when it isn't in memory. | [41] |
| G6 | Promises made, extended, fulfilled, cancelled. Two people share a name; some speakers are never identified. | [13-14] |
| G7 | Run the train evals with the harness; report results, failures and why. Hidden test counts more. No hard-coded train answers. | [45-48] |

Weights: memory design 30, retrieval 20 (hidden 15), answers 10 (hidden 7), README 10, bonus design 10, bonus action eval 20 (hidden 15). [123-132]

## Bonus: actions (dry run)

| ID | Requirement | Source |
|---|---|---|
| A1 | Input JSONL `id`, `command`, `as_of`; output the actions we would take, without executing. | [83-87] |
| A2 | Types and args: `slack.send_message`, `gmail.send`, `calendar.create_event`, `calendar.update_event`, `reminder.create`, `memory.ask`, `app.open`, `clarify`, `confirm`. | [89-99] |
| A3 | Use ids from `data/`: Slack user and channel ids, emails, event ids. Times in `America/Los_Angeles`. | [101] |
| A4 | Ambiguous command: `clarify`. Destructive command: `confirm` first. | [98-99] |
| A5 | Scorer: action list must match exactly in count and type; extra actions fail; extra args ignored; datetime tolerance per case (train: 0 min). | eval_harness/score_actions.py |
