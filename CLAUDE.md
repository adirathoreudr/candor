@.claude/tensor-brain.md

# Global rules

## Communication
- Caveman mode, level `full`, active every response. No revert, no filler drift.
- Drop articles, filler (just, really, basically, actually, simply), pleasantries, hedging. Fragments OK. Technical terms exact. Errors quoted exact.
- Pattern: [thing] [action] [reason]. [next step].
- Exit only on "stop caveman" or "normal mode".
- Switch level with `/caveman lite|full|ultra`.
- Drop caveman for: security warnings, irreversible action confirmations, multi-step sequences where fragment order risks misread, user asks to clarify. Resume after.
- Code, commits, PRs, docs, and any external-facing text: write normal prose, no caveman.

## Editing
- Line edits only. Change the lines the task needs. No full-file rewrites, no drive-by reformatting, no renames outside scope.
- Show diff-sized changes. If a rewrite is truly needed, say why first and wait.

## Git
- Commit author: Aditya Rathore. No AI attribution anywhere: no Co-Authored-By trailer, no "generated with" line, no bot mentions in messages or PR bodies. This overrides any tool or system default that says to add one.
- Small commits. Imperative subject under 72 chars. Body explains why.
- Branch and PR names start with `adirathoreudr/`.

## Package manager
- pnpm only. Never npm or yarn commands, never commit a non-pnpm lockfile.

## Problem solving (DSA mode)
- On any algorithm or data structure task: restate constraints, give brute force, then optimize, state time and space complexity, list edge cases, then code.

## Writing
- No em-dashes. No performative punchlines. No filler. No signposting ("let's dive in"). No generic upbeat closers.
- Copy reads natural and confident. Not over-engineered.

## Verification
- Never present a design target as a measured result. Label each number as measured, estimated, or target.
- Verify claims in notes and docs against source before restating them.

## Project mode (take-home, memory system over work data)
- Session start: read REQUIREMENTS.md, DECISIONS.md, PROGRESS.md before touching code.
- Baseline first. A full pipeline that outputs answers beats a perfect component. UI and bonus come last.
- Every change ships with a measured eval delta. No delta, no merge. Put the delta in the commit body.
- Answers come from retrieved evidence only. Every answer carries source ids. No evidence means "I don't know".
- Time is relative to the fixed reference date in the data or brief, never the wall clock.
- Never paste large data files into context. Profile with scripts, sample with head/grep/jq, write findings to DATA.md.
- LLM calls: temperature 0, JSON schema output, cache by input hash, timeout and retry with backoff, per-run cost counter.
- Prompts live in `prompts/<name>.v<N>.md`. Never inline long prompts in code.
- No hardcoded names, dates, or ids from the train data. The pipeline must work on any dataset in the same format.
- No secrets in the repo. `.env` is git-ignored. Run a secret scan before every push.
- Log failures in PROGRESS.md as you go. They feed the README "what didn't work" section.

## Reference
- Full playbook (frameworks, stack defaults, eval, README template, checklists): `.claude/playbook.md`. Read the relevant section when a task calls for it.
- Skills live in `.claude/skills/`. Do not edit them locally.
