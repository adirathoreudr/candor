---
name: claude-code-playbook
version: 2.0.0
purpose: Single source of truth for Claude Code behavior, plus project-type requirements for a memory-system take-home (Part II). Same file, same output.
owner: Adi Singh
---

# Claude Code Playbook

One file. Skills, rules, frameworks, stack defaults, and checks. Load it once, get the same behavior as the owner.

## 0. How to use

1. Copy the skill folders listed in section 2 into `.claude/skills/` inside the shared repo. Commit them. Do not rewrite them.
2. Paste the block in section 1 into the repo-root `CLAUDE.md`. Replace `<YOUR NAME>` only.
3. Install the same `everything-claude-code` setup at the pinned commit `<PINNED_COMMIT>` (ask the owner for the hash).
4. Run the smoke tests in section 9. All must pass before you start work.
5. For the memory-system take-home, also follow Part II (sections 14 to 26). Part I is the behavior layer, Part II is the project layer.
6. Check the take-home rules on collaboration before sharing work with anyone. If it must be solo, share this playbook as setup only and each person builds their own submission.

Precedence when files disagree: the organizer's email, then BRIEF.md, then REQUIREMENTS.md, then this playbook.

Rule of thumb: if the repo contains `CLAUDE.md` and `.claude/skills/`, both machines behave the same. This file explains them, the repo enforces them.

Limit: model output is not byte-identical run to run. This setup removes drift in style, process, stack, and format. It cannot remove sampling noise.

---

## 1. CLAUDE.md block (paste as is)

```markdown
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
- Commit author: <YOUR NAME>. No AI attribution anywhere: no Co-Authored-By trailer, no "generated with" line, no bot mentions in messages or PR bodies.
- Small commits. Imperative subject under 72 chars. Body explains why.

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
```

---

## 2. Skill stack

Copy these folders exactly. The digests below summarize them, they do not replace them.

| Skill folder | Trigger | What it enforces |
|---|---|---|
| `superpowers` | Start of every task | Check for a matching skill before any response, including clarifying questions. If a skill applies, use it. |
| `caveman` | Always on | Terse output, full technical accuracy. Levels lite, full, ultra. |
| `prompt-engineer` | Writing or tuning any prompt, system prompt, agent prompt | Pattern choice, templates, evals, token and cost discipline. See section 4. |
| `humanizer` | Any prose meant for humans: posts, README copy, docs, emails | Strips AI writing tells, adds voice. See section 5. |
| `backend-claudde` (backend-architect) | New service, API, schema, scaling, observability | Contract-first design, bounded contexts, observability baked in. See section 6. |
| `frontend-claudde` (frontend-design) | Any UI, page, component, landing page | Bold committed aesthetic, no generic AI look. See section 7. |
| `code-reviewer` | Before merge, after any significant change | Severity-tagged findings, fixed output format. See section 8. |
| `llm-council` | High-stakes or ambiguous decisions, or "Use Council Workflow" | Three-stage deliberation. See section 3. |
| `agent-development` | Creating Claude Code subagents | Frontmatter spec, system prompt structure. See section 4.5. |
| `engineering:system-design` | Before building the memory system | Requirements, high-level design, deep dive, scale and reliability, explicit trade-offs, what to revisit. See sections 16 and 20. |
| `engineering:testing-strategy` | Designing tests and the eval harness | Test pyramid, data pipeline tests (input validation, transformation correctness, idempotency), cover critical paths and edge cases. See section 17. |
| `engineering:documentation` | README and architecture write-up | Reader first, quick start under 5 minutes, key decisions and trade-offs, link do not duplicate. See section 21. |
| `hackathon-strategist` | Time-boxing a deadline project | Phase budgets with go/no-go gates, cut decisions, demo reliability checklist. See sections 22 to 24. |

### Skill priority (from superpowers)

1. Process skills first: brainstorming, debugging, council. They decide how to approach.
2. Implementation skills second: backend, frontend, prompt-engineer.
3. Review skills last: code-reviewer, humanizer.

Instructions say what, not how. "Add X" does not mean skip the workflow.

---

## 3. Core workflow

Use this order on every project task.

1. **Frame.** One line: goal, constraint, done condition.
2. **Decide.** If ambiguous or high-stakes, run Council (3.1). Otherwise pick and go.
3. **Design.** Backend contract first (section 6). Frontend aesthetic direction first (section 7).
4. **Build.** Line edits only. pnpm. Stack defaults (section 10).
5. **Test.** Deterministic tests for logic and policy. Fake-LLM tests for LLM constraints.
6. **Review.** `code-reviewer` on the diff. Fix CRITICAL and HIGH before merge.
7. **Write.** Docs and copy through `humanizer`.
8. **Commit.** Author is you, no AI attribution.

### 3.1 Council deliberation (llm-council)

Use for architecture forks, tool selection, risky migrations. Three stages, in order, no leakage between them.

**Stage 1, First Opinions.** Create 3 to 4 expert personas tailored to the question. Each writes a full standalone answer. They do not reference each other or a council.

**Stage 2, Anonymized Peer Review.** Strip persona titles. Label Response A, B, C. Critique each on accuracy (facts, logic, no hallucination) and insight (depth, strategic value, usefulness). Give a short blunt critique per response, then a numbered final ranking.

**Stage 3, Chairman's Synthesis.** Build the final answer mainly on the #1 ranked response. Pull in non-redundant, accurate points from the others. No process summary, no meta-commentary.

Required output headers, exactly:

```
## Stage 1: First Opinions
### [Persona title]
...
---
## Stage 2: Anonymized Peer Review
**Critique A:** ...
**FINAL RANKING:**
1. Response [Letter]
## Stage 3: Chairman's Final Synthesis
...
```

---

## 4. Prompt engineering framework (prompt-engineer)

### 4.1 Process

1. Requirements: use case, accuracy target, cost limit, latency limit, safety needs, success metric.
2. Review any existing prompt and its failures.
3. Start simple. Add structure only when a test fails.
4. Test on a fixed set, including edge cases. Measure before and after every change.
5. Version the prompt. Log what changed and the score delta.

### 4.2 Pattern selection

| Pattern | Use when |
|---|---|
| Zero-shot | Task is clear, format is simple |
| Few-shot | Format or tone must match exactly. Use diverse examples, consistent format, include an edge case |
| Chain-of-thought | Multi-step reasoning. Add verification points and self-check |
| ReAct | Tool use with reasoning between calls |
| Role-based | Domain voice or boundaries matter |
| Constitutional | Output must follow explicit rules, with a critique-and-revise pass |

### 4.3 Template structure

Every production prompt has these sections, in this order:

```
ROLE:        who the model is
CONTEXT:     only what it needs, compressed
TASK:        one clear instruction
CONSTRAINTS: hard rules, safety, scope
FORMAT:      exact output schema (JSON when parsed by code)
EXAMPLES:    few-shot if needed
FALLBACK:    what to output when unsure or input is invalid
```

Rules:
- Variables are named placeholders, never string-glued ad hoc.
- JSON-only output when code parses it. Validate and discard garbage, fall back to a safe default.
- Require evidence citations when the model asserts facts.
- Compress context, prune dead instructions, cap output length. Track tokens and cost per call.

### 4.4 Checklist before shipping a prompt

- Accuracy on the test set at or above target
- Edge cases covered: empty, malformed, adversarial, very long
- Injection defense: user input never overrides system rules
- Output parsed and validated, not trusted
- Version tagged, score recorded
- Cost per query known

### 4.5 Agent authoring (agent-development)

Agents live in `agents/<name>.md` with YAML frontmatter.

```markdown
---
name: agent-identifier          # 3-50 chars, lowercase, hyphens, starts and ends alphanumeric
description: Use this agent when [conditions]. Examples:
  <example>
  Context: ...
  user: "..."
  assistant: "..."
  <commentary>why this agent triggers</commentary>
  </example>
model: inherit                  # inherit | sonnet | opus | haiku
color: blue                     # blue cyan green yellow magenta red
tools: ["Read", "Grep"]         # least privilege
---

You are [role] specializing in [domain].

**Core Responsibilities:** ...
**Analysis Process:** numbered steps
**Quality Standards:** ...
**Output Format:** ...
**Edge Cases:** ...
```

- Description is the trigger. Include 2 to 4 examples, proactive and reactive, plus when not to use it.
- System prompt in second person, 500 to 3000 chars is the sweet spot, 10000 max.
- Read-only agents get `Read, Grep, Glob`. Give Write or Bash only when needed.

---

## 5. Writing rules (humanizer)

Applies to anything a human reads: README, posts, docs, emails, portfolio copy. Not to code or commit bodies.

### 5.1 Ban list

- Em-dashes
- Significance inflation: "testament", "pivotal", "vital role", "evolving landscape", "marks a shift"
- Promotional words: "groundbreaking", "seamless", "powerful", "nestled"
- Tacked-on -ing analysis: "highlighting...", "ensuring...", "showcasing..."
- Vague attribution: "experts say", "industry observers"
- Rule of three and synonym cycling
- Negative parallelism: "not just X, it's Y"
- Copula avoidance: "serves as", "stands as" (write "is")
- Signposting: "let's dive in", "here's what you need to know"
- Fragmented headers: a heading followed by a line that restates it
- Chatbot leftovers: "Great question", "I hope this helps", "let me know if"
- Hedge stacking: "could potentially perhaps"
- Generic upbeat closers: "the future looks bright"
- Emoji bullets, bold-label bullet spam

### 5.2 Add a pulse

- Specific over vague. Name the number, the tool, the date.
- Vary sentence length.
- Say what you think. Allow one honest uncertainty.
- Use "I" when it fits.

### 5.3 Final pass (always)

1. Draft.
2. Ask: "What makes this obviously AI generated?" List remaining tells in a few bullets.
3. Ask: "Now make it not obviously AI generated." Revise.
4. Ship the revised version.

Voice target: natural, confident, not over-engineered.

---

## 6. Backend architecture framework (backend-claudde)

Use before writing a service. Output is a design, not code.

### 6.1 Approach

1. Define bounded contexts and data ownership before drawing service lines.
2. Contract first: OpenAPI 3.1, Protobuf, or AsyncAPI.
3. Pick API paradigm (REST, gRPC, GraphQL, WebSocket) by use case, with the trade-off stated.
4. Set consistency per aggregate: strong or eventual.
5. Stateless services, externalized state, horizontal scaling from day one.
6. Observability designed in, not added later.
7. Keep it simple. No premature microservice splits.

### 6.2 Required observability

- Structured logs with correlation and trace IDs across boundaries
- OpenTelemetry spans on every external call (DB, cache, downstream)
- RED metrics per endpoint (Rate, Errors, Duration), Prometheus format
- `/health` (liveness), `/ready` (readiness), `/metrics`
- SLO alerts, for example p99 under 200ms, error rate under 0.1%

### 6.3 Security baseline

- OWASP API Top 10 checked per endpoint
- Secrets from env or a vault, never in source
- mTLS between services
- JWT validated at the gateway, RBAC or ABAC behind it
- Schema validation and sanitization at every boundary

### 6.4 Deliverables

1. Architecture diagram (Mermaid or ASCII) with boundaries and flows
2. Endpoint definitions with example request, response, status codes
3. OpenAPI 3.1 YAML or Protobuf IDL
4. DB schema: relationships, indexes, sharding strategy
5. Event schemas for async paths
6. Tech choices with one-line rationale and trade-off
7. Bottlenecks, failure modes, scaling notes
8. Security notes per layer: gateway, service, data

---

## 7. Frontend and design framework (frontend-claudde)

### 7.1 Before any code

Answer in four lines:
- **Purpose:** what problem, who uses it
- **Tone:** pick one committed direction (brutalist, editorial, retro-terminal, industrial, refined minimal, and so on)
- **Constraints:** framework, performance, accessibility
- **Memorable thing:** the one detail someone will remember

Commit to the direction. Bold maximalism and refined minimalism both work. Timid mixes do not.

### 7.2 Execution rules

- **Type:** distinctive display font plus refined body font. Never Inter, Roboto, Arial, or system defaults. Do not converge on the same font every project.
- **Color:** CSS variables. Dominant color with sharp accents. No purple gradient on white.
- **Motion:** CSS-first. One strong staggered page-load reveal beats scattered micro-effects. Scroll triggers and hover surprises where they fit.
- **Layout:** asymmetry, overlap, grid breaks, or controlled density. Avoid cookie-cutter cards.
- **Atmosphere:** grain, noise, mesh gradients, layered transparency, textured backgrounds. No flat solid default.
- Match code complexity to the vision. Maximal designs need elaborate effects, minimal designs need exact spacing and type.

### 7.3 Owner house taste (default unless the project says otherwise)

- Raw, gritty terminal and hacker visuals
- Retro terminal and matrix feel: CSS-animated SVG, typewriter effects
- Rejects flat badges and broken gif embeds as basic
- Tech icons via skillicons.dev, stats cards for GitHub profiles
- Portfolio exception: vintage editorial magazine concept

Keep the whole project on one direction so both contributors ship a consistent UI.

---

## 8. Code review framework (code-reviewer)

### 8.1 Setup

1. Scope the diff: `git diff --name-only HEAD~1` or the files named.
2. Read conventions from `CLAUDE.md`, `.editorconfig`.
3. Pre-checks, skip any missing tool: `npm audit` or `pnpm audit`, `pip-audit`, `cargo audit`, a grep for hardcoded secrets in changed files, `git log --oneline -5`.

### 8.2 Reading strategy

- Under 20 files: read each in full.
- 20 to 100 files: read the diff first, then deep-read auth, payments, config, migrations, shared utilities.
- Over 100 files: ask for a narrower scope.

### 8.3 Checklist

- **Security:** injection (SQL, command, path), auth bypass, secrets or PII in logs or responses, hand-rolled crypto
- **Errors:** every external call handled, useful logs without leaking internals, cleanup in finally
- **Tests:** assert behavior not implementation, edge cases, no mock bleed
- **Dependencies:** audit results, stale or suspicious packages, license changes
- **Performance:** N+1 queries, unpaginated loads, missing FK indexes

### 8.4 Language flags

- **TypeScript:** every `any`, missing `strict: true`, floating Promises, unchecked null
- **Python:** mutable default args, bare `except:`, missing type hints on public fns, `eval` or `exec` on user input
- **Rust:** `.unwrap()` or `.expect()` outside tests, `unsafe` without `// SAFETY:`
- **Go:** discarded errors, goroutines without ctx cancellation, `defer` in loops
- **SQL:** `UPDATE` or `DELETE` without `WHERE`, N+1, unindexed join columns

### 8.5 Output format (exact)

```
**[CRITICAL] `file:line` - short description**
Risk: what breaks if not fixed
Fix: concrete change

**[HIGH] ...   **[MEDIUM] ...   **[LOW / SUGGESTION] ...
```

Close with:

> Review Summary: examined [N] files, found [N] CRITICAL, [N] HIGH, [N] MEDIUM, [N] LOW findings. Top priority: [item]. Merge recommendation: **BLOCK** / **APPROVE WITH SUGGESTIONS** / **APPROVE**.

Feedback style: specific example per finding, explain the risk, offer the fix, note what is done well, state priority.

---

## 9. Smoke tests (run once, compare)

Paste each prompt into a fresh session. Both of you must get the expected behavior.

| # | Prompt | Expected |
|---|---|---|
| 1 | "Why does my React component re-render?" | Caveman full. No greeting. Fragments. Cause plus fix in 2 to 3 lines. |
| 2 | "Commit these changes." | Normal-prose message. Author is you. No Co-Authored-By, no AI mention. |
| 3 | "Rename `foo` to `bar` on line 42 of x.ts." | Only line 42 changes. No other lines touched. |
| 4 | "Install zod." | `pnpm add zod`. |
| 5 | "Write a LinkedIn post about our launch." | No em-dashes, no "let's dive in", no rule of three. Humanizer final pass done. |
| 6 | "REST or gRPC for service X?" | Trade-off stated for this use case, or Council format if asked to deliberate. |
| 7 | "Build a landing page." | Four-line design framing first. No Inter, no purple gradient. |
| 8 | "Review this PR." | Severity-tagged findings and the Review Summary line. |
| 9 | "Solve two-sum." | Constraints, brute force, optimized, complexity, edge cases, code. |
| 10 | "Our MTTR dropped 60%." (with no data) | Asks for the measurement or labels it as a target. |

If a test fails, the cause is almost always a missing `CLAUDE.md` or a skill folder not copied. Fix that before debugging anything else.

---

## 10. Stack defaults

Use these unless the project overrides.

| Area | Default |
|---|---|
| Web | Next.js 15, Tailwind v4 |
| ORM | Prisma 7 |
| Data | Postgres, Mongo, Redis |
| Infra | AWS, Kubernetes, Terraform |
| Chain | Solana (Anchor, Token-2022), Ethereum, Base |
| LLM | NVIDIA NIM through an OpenAI-compatible endpoint |
| Deploy | Vercel |
| Package manager | pnpm |
| Primary DB for study and interviews | PostgreSQL |

### Known gotchas

- **Prisma 7 datasource:** connection config lives in `prisma.config.ts`, not in `schema.prisma`. Check the repo version before editing either.
- **Prisma client imports:** import from the generated client output path set in the generator block. Do not assume `@prisma/client`.
- **Tailwind v4 and `globals.css`:** font `@import` lines go first, before `@import "tailwindcss"` and any other rule. Wrong order breaks fonts silently.
- **Stale `.next` cache:** if the UI ignores a change, stop dev, delete `.next`, restart. Do this before debugging code.

---

## 11. Agentic system pattern (policy-gated actions)

Use for any agent that can change real systems. Pattern proven in the AIOps Incident Commander project.

### 11.1 Service split

- **Collector:** dedupe and enrich inputs, attach logs and history.
- **Agent:** LLM reasoning with retrieval. Must cite evidence. JSON-only output.
- **Executor:** policy gate, then typed API action, then health verify, then audit.

### 11.2 Three layers of LLM safety

1. **Prompt level:** cite evidence, JSON-only, explicit refusal path.
2. **Reasoner level:** take scope values (namespace, target) from the trusted input, never from the LLM output. Discard non-numeric or garbage output and fall back to notify-only.
3. **Policy level:** action allowlist, blocked targets, confidence thresholds per environment, bounds on scale actions, human approval for destructive actions.

Invariant: the LLM can only escalate to a human. It can never bypass one.

### 11.3 Execution rules

- Typed API calls only. No shell exec, no pod exec.
- Small fixed action allowlist.
- Append-only audit trail with atomic writes (for example Redis `RPUSH`) so concurrent writers never clobber each other.

### 11.4 Test split

- Deterministic policy-engine tests with no LLM in the loop.
- LLM safety-constraint tests using a fake LLM.
- Input normalization tests.

### 11.5 Claims discipline

Do not call a system "production-proven" without production data. Say "production-ready" or "design target" and label every metric as measured, estimated, or target.

---

## 12. Research and study output rules

- Explain in simple terms first. Assume beginner level unless told otherwise.
- Deliver notes as clean, organized markdown with hyperlinks, ready to paste into Notion.
- Order: core concepts first, deep dive second. Skip advanced topics unless asked.
- Interview-oriented material: gist-level answers, then one worked example.
- Check every factual claim against a source before it goes in a note. Fix errors by rebuilding the section, not patching around them.
- Cite sources with links. Mark anything unverified as unverified.

---

## 13. Anti-patterns

- Rewriting a whole file for a one-line change
- Using npm or yarn in a pnpm repo
- Shipping a prompt with no test set
- Letting LLM output set the target of an action
- Stating targets as results
- Default fonts and purple gradients
- AI-flavored prose in README or posts
- Adding AI attribution to commits
- Skipping the skill check "because it is simple"
- Editing skill files locally. Change the shared copy, tell the other person.

---

# PART II: Memory-system take-home

Framework-neutral. No architecture, model, or topic is chosen here. Part II lists what the project must satisfy and the slots where you decide, with the evidence rule for deciding.

## 14. Project type and day-zero

### 14.1 What the project is

Source: the organizer's email. BRIEF.md in the zip is the full spec and wins on any conflict, except the deadline, where the email wins.

- **Input:** about two weeks of one startup VP's work life: meetings, dictation, Slack, email, calendar, Codex sessions, ChatGPT sessions.
- **Build:** a memory that answers questions about that data correctly. Four things are graded: what is true now, what was true then, who said what, and when to say "I don't know".
- **Optional bonus:** a voice or text assistant that takes actions.
- **Hidden test:** run on the submitted commit. Either the organizer runs it, or sends questions and you return outputs within 24 hours.
- **Tools and models:** any. Cost is yours. List everything used in the README.

### 14.2 Deadline

Monday, October 5, 2026, 2:00 pm IST (08:30 UTC). Ignore the Friday deadline in BRIEF.md. Target submission at 12:00 pm IST, two hours early.

### 14.3 Day-zero checklist (before any code)

1. Read BRIEF.md in full, twice. Extract every MUST, SHOULD, and format rule into REQUIREMENTS.md with the line it came from.
2. Inventory the data and write DATA.md: file types, sizes, record counts per source, date range, time zones, encodings, schemas, which parts carry labels or answers.
3. Identify train versus hidden. Find the question format, answer format, and output file format. Note any scoring hints.
4. Write the list of ambiguities. Send one email to the organizer (14.4).
5. Create the empty public repo now. Add `.gitignore`, `.env.example`, and a stub README.
6. Run the pre-flight in section 19.

### 14.4 Questions to send the organizer (one email, early)

The organizer invited questions. Ask only what changes your design:

- During the hidden test, who supplies API keys and which model? May the pipeline call external APIs at all?
- Is the hidden test the same data with new questions, or new data in the same format?
- What is "now" for "what's true now"? A fixed reference timestamp, or the end of the data?
- Exact question input format, answer output format, file naming, and how an abstention must be written.
- Time zone to assume for relative dates ("yesterday", "last Friday").
- May the raw data be committed to a public repo?
- Runtime and cost limits for their run. Python version or container expectations.
- Is collaboration or outside help allowed?

---

## 15. Requirements the system must meet

| ID | Requirement | What it means in practice |
|---|---|---|
| R1 | Temporal correctness | Every fact has a valid-from and a valid-to, or a supersession link. Latest-wins is wrong by default. Handle corrections, retractions, cancellations, reschedules, tentative versus confirmed, planned versus happened. |
| R2 | Attribution | Store who said, decided, asked, or did each thing. Keep the VP's words apart from others'. Assistant output in ChatGPT and Codex is not the VP's statement. Handle quoted and forwarded text. |
| R3 | Provenance | Every answer lists its source ids: document, timestamp, speaker. A reader can verify any answer. |
| R4 | Abstention | Say "I don't know" when evidence is missing, when sources conflict without a resolution rule, or when the question assumes something false. Do not over-abstain. Track both error types. |
| R5 | Entity resolution | Same person or project under different names: nicknames, first names, emails, Slack handles, dictation misspellings. |
| R6 | Conflict handling | Sources disagree. Apply explicit rules (source reliability, recency, authorship). Surface the conflict when the rules cannot decide. |
| R7 | Noise tolerance | Speech-to-text errors, diarization errors, informal Slack, truncated or duplicated email threads, code and CLI output in Codex sessions. |
| R8 | Multi-hop and aggregation | Questions that join sources, count, list attendees, or ask what changed since a date. |
| R9 | Relative time | Resolve "yesterday", "next week", "by Friday" against the timestamp of the message that said it, in the right time zone. |
| R10 | Reproducibility | Pinned dependencies, pinned model ids, temperature 0, seeds, cached LLM calls keyed by input hash. A rerun gives the same outputs. |
| R11 | Cost and latency | Budget per question and for ingestion. Measure both. Report them. |
| R12 | Privacy | Treat the data as sensitive. No keys in the repo. Publish raw data only if allowed. Send data only to services you are allowed to use. |
| R13 | Generalization | No hardcoded names, dates, or ids from the train data. The pipeline works on any dataset in the same format. |

---

## 16. Design decision slots

Fill each slot by measurement, not preference. Record the choice, the options tried, and the evidence in DECISIONS.md. Start with the simplest option that could pass. Use `engineering:system-design` for the trade-off write-up and list what you would revisit with more time.

| Slot | Options to consider | Decide by measuring |
|---|---|---|
| Ingestion and parsing | Per-source parsers, unified record schema, timestamp and speaker normalization | Parse success rate, field coverage per source |
| Memory representation | Raw chunks, atomic claims with metadata, entity graph, event timeline, rolling summaries, hybrid | Accuracy per question category |
| Storage | SQLite, Postgres, vector index, graph store, flat files | Setup friction, one-command fit, query speed |
| Retrieval | Keyword, dense, hybrid, reranking, structured queries over extracted facts | Retrieval recall on dev questions |
| Temporal handling | Valid-from and valid-to fields, supersession edges, as-of queries | Accuracy on current versus past questions |
| Answer synthesis | Single call, tool-using agent loop, draft then verify | Accuracy, latency, cost |
| Abstention | Evidence threshold, verifier pass, self-consistency, explicit unanswerable class | False answer rate and false abstain rate |
| Models | One strong model, small plus strong split, local versus hosted | Accuracy per dollar |

Keep a provider-agnostic LLM interface (OpenAI-compatible base URL and key from env). The organizer may swap the model or key for their run.

---

## 17. Evaluation framework

Use `engineering:testing-strategy` for the harness and `prompt-engineer` for prompt versioning and A/B discipline.

### 17.1 Dev set

- If the train set has labeled questions, split it. Hold out a slice you never tune on.
- If it has none, write questions by hand until every category below has at least 10.
- Never tune on hidden-test style questions you invent after seeing the organizer's examples, then call it held out.

### 17.2 Question categories

| Category | Failure it exposes |
|---|---|
| Current state | Returns an outdated fact |
| Past state ("as of date D") | Returns the current fact instead |
| Change over time | Misses a supersession |
| Who said what | Wrong speaker, or assistant text attributed to the VP |
| Multi-source | Uses one source and misses the correction in another |
| Aggregation and counts | Misses items or double counts |
| Relative date | Resolves against the wrong anchor |
| Entity alias | Splits one person into two |
| Unanswerable | Hallucinated answer |
| False premise | Accepts the premise |
| Conflicting sources | Picks silently |

### 17.3 Metrics

Report per category, not only the aggregate.

- Accuracy (exact or normalized match where possible, rubric-based LLM judge otherwise)
- False answer rate on unanswerable questions
- False abstain rate on answerable questions
- Citation accuracy: cited sources actually support the answer
- Latency and cost per question
- Judge check: label 20 answers by hand, report judge agreement

### 17.4 Discipline

- `make eval` runs the full set and writes `results/<commit>.json` plus a markdown table.
- Ablate each component (on versus off) and keep the table. It goes in the README.
- Label every failure with a root cause: retrieval miss, temporal error, attribution error, entity split, hallucination, over-abstain, parse failure. Fix the largest bucket first.
- Do not hardcode answers to train questions. Do not edit the dev set to make a score go up.
- Label every number in the README as measured, estimated, or target.

---

## 18. Repo and one-command spec

### 18.1 Layout

```
repo/
  README.md
  REQUIREMENTS.md  DECISIONS.md  DATA.md  PROGRESS.md
  Makefile (or run.sh)
  pyproject.toml + lockfile   (pinned Python version)
  .env.example  .gitignore
  Dockerfile                  (recommended for the one-command promise)
  prompts/                    (versioned prompt files)
  schemas/                    (record, fact, answer schemas)
  src/
    ingest/  memory/  retrieve/  answer/  eval/  assistant/
  tests/
  outputs/train/              (submitted output files)
  results/                    (eval runs)
```

### 18.2 Command contract

| Command | Does |
|---|---|
| `make run` | Install, ingest, build memory, answer the questions file, write outputs. One command from a clean clone. |
| `make eval` | Run the dev set, print the per-category table, write `results/`. |
| `make ask Q="..."` | Answer one question with sources. |
| `make test` | Unit and pipeline tests. |

### 18.3 Rules

- Works on a fresh clone with zero manual steps.
- Questions file path and output path are arguments. The hidden test must run without code edits.
- Missing key gives one clear message, not a traceback.
- Idempotent. A second run reuses the cache and gives identical outputs.
- Runtime is stated in the README.
- Test it in a fresh temp directory and a fresh container before submitting. Do this twice, once at 70% of the time and once before sending.
- Public repo hygiene: scan history for secrets before the first push, confirm data publication is allowed, keep large artifacts out of git.

---

## 19. Pre-flight prerequisites

Do this before the clock matters.

**Accounts and keys**
- LLM provider and embedding provider. Test each key with a one-call script.
- Spend cap set. Daily cost budget written in PROGRESS.md.
- Voice bonus only: speech-to-text and text-to-speech accounts.

**Local tools**
- Git, GitHub CLI authenticated, Make, Docker, jq, SQLite, Python at the pinned version with a lockfile tool. Node and pnpm only if a UI is needed. ffmpeg only if audio is needed.

**Repo**
- Empty public repo created. `.gitignore` covers `.env`, caches, raw data if not allowed.
- Optional CI running tests and a tiny smoke run.

**Claude Code**
- Skills copied to `.claude/skills/`. `CLAUDE.md` from section 1 plus the Project mode block.
- Shared `.claude/settings.json` with permissions and hooks: pre-commit secret scan, formatter, tests on commit.
- GitHub MCP server if you use one. Same server list on every machine.

**Pins**
- Exact model ids, package versions, Python version, and the `everything-claude-code` commit.

---

## 20. Operating rules inside Claude Code

1. **Session start:** skill check (superpowers), then read REQUIREMENTS.md, DECISIONS.md, PROGRESS.md.
2. **Process order:** brainstorm and design with `engineering:system-design`, build, test with `engineering:testing-strategy`, review with `code-reviewer`, write docs with `engineering:documentation` and `humanizer`.
3. **Plan before code** for anything touching more than one module. State the change, the expected eval effect, and the rollback.
4. **One variable per experiment.** Change one thing, rerun eval, record the delta in PROGRESS.md and the commit body.
5. **Commit small and often.** Line edits only. Tag every commit that passes eval, for example `eval-v3`.
6. **Context hygiene.** Large data never goes into the chat. Profile with scripts. Keep summaries in DATA.md. Start a fresh session when the context gets heavy and reload the three project files.
7. **Subagents.** Use read-only agents (`Read, Grep, Glob`) for data profiling and for failure analysis. Keep write access in the main session. Author them per section 4.5.
8. **LLM safety.** Prompts require evidence ids and a fallback of "unknown". Parse model output against a schema. Discard malformed output and fall back to abstention.
9. **Parallel work between two people.** Split by module boundary (ingest, memory and retrieval, answering and eval, assistant and docs). The contract is the files in `schemas/`. One owner per file. Merge by pull request and review with `code-reviewer`. Skip this if the take-home is solo.

---

## 21. README template

Graders asked for: architecture, key decisions, what did not work, and eval results. Reader first. Quick start in the first screen.

```markdown
# <name>

<Three lines: what it is, what it answers, how it handles time, attribution, and unknowns.>

## Quick start
<Clone, set env vars, one command. Expected runtime and cost.>

## Architecture
<One diagram. Components and data flow. How a question becomes an answer with sources.>

## Key decisions
| Decision | Options tried | Evidence | Choice |
|---|---|---|---|

## What did not work
<Honest list. Each item: what you tried, what happened, the number, why you dropped it.>

## Eval results
<Dataset, split, n, commit hash, date, command. Per-category table. Abstention table. Ablations. Cost and latency.>

## Limitations and known failures
<Where it still breaks, with examples.>

## Tools and models used
<Every model, provider, and tool, with approximate cost.>

## Reproducing the outputs
<Exact commands that regenerate outputs/train/.>

## Bonus: assistant
<What it does, actions it can take, safety gates. Link to the demo video.>

## Submission
<Commit hash.>
```

Writing rules: `humanizer` pass, no em-dashes, no claim without a number, every number labeled measured, estimated, or target.

---

## 22. Bonus: action-taking assistant (optional)

Start only when the core passes eval and the one-command run is clean on a fresh clone.

- **Interface:** text first. Add voice if time allows, with text as the fallback. Name the speech-to-text and text-to-speech providers in the README.
- **Actions:** typed tool calls from a small allowlist (for example draft an email, create a calendar event, post a Slack message), run against a mock or sandbox.
- **Safety:** reuse the policy-gate pattern from section 11. Confirm any action with an external effect before executing. Support dry-run. Write every action to an append-only audit log.
- **Memory use:** read memory before acting. Resolve people and times from memory. If the recipient or time is ambiguous, ask or abstain. Do not guess.
- **Demo video, 5 minutes max:** one temporal question, one attribution question, one "I don't know", one action with confirmation. Record a backup take. Run the demo reliability checklist from `hackathon-strategist`: seeded data, rehearsed path, closed tabs, tested audio.

---

## 23. Time-boxing

Proportions of the time left, not a plan. Adjust to the clock.

| Phase | Share | Gate |
|---|---|---|
| Read the brief, inventory data, email the organizer | 10% | REQUIREMENTS.md and DATA.md written |
| Dev set and eval harness | 10% | `make eval` runs on a stub |
| End-to-end baseline | 20% | Full pipeline writes outputs on the train set by 30% elapsed. If not, cut scope. |
| Improve by error bucket | 35% | Eval table moves each cycle. Stop a direction after two flat cycles. |
| Bonus assistant | 10% | Only if the baseline is stable. Otherwise give the time to the improve loop. |
| README, outputs, video | 10% | Drafted incrementally, finalized here |
| Buffer | 5% | Untouched until needed |

Fixed rules:
- Feature freeze at 85% elapsed. After that, only bug fixes and docs.
- Final fresh-clone test at 90% elapsed.
- No code changes after the submission hash is recorded.
- Write README sections as you learn things, not at the end.

---

## 24. Submission checklist

Reply to the organizer's email with these five items.

1. Public repo URL. Open it in a logged-out browser.
2. README covering architecture, key decisions, what did not work, eval results, tools and models used.
3. Full 40-character commit hash. Tag it `submission`. Confirm `git rev-parse HEAD` matches. Push nothing after.
4. Output files on the train sets, in the required format, committed under `outputs/train/`. Count matches the question count. No empty answers.
5. Demo video link (public or unlisted, 5:00 maximum). Optional, strongly worth it if the bonus exists.

Hidden test readiness:
- If they run it: one command works with their key, env vars documented, no code edits needed.
- If they send questions: keep the environment ready for the 24-hour window. The pipeline takes a questions file and writes the same output format. Do not retune.
- Keep the email short: the five items, the tools used, and any caveat the graders must know.

---

## 25. Project smoke tests

Run on a fresh clone. All must pass before submitting.

| # | Check | Expected |
|---|---|---|
| 1 | `make run` on a clean clone | Completes with no manual steps. Outputs written. |
| 2 | `make eval` | Per-category table printed. Results file written. |
| 3 | Ask about a fact that was later corrected | Current value, with date and source ids. |
| 4 | Ask for the same fact "as of" an earlier date | The older value, with its source. |
| 5 | Ask what person B said, where A said something similar | B's statement, not A's. |
| 6 | Ask something the data cannot answer | "I don't know" with a short reason. |
| 7 | Ask a question with a false premise | Premise rejected or abstention. |
| 8 | Ask with a relative date ("last Friday") | Resolved against the fixed reference date. |
| 9 | Remove the API key and run | One clear error message, no traceback. |
| 10 | Rerun with the cache | Identical outputs. |
| 11 | Secret scan over full git history | No hits. |

---

## 26. Project anti-patterns

- Starting the UI or the bonus before the baseline exists
- Vector search over raw chunks with no time or speaker metadata
- Latest-wins overwrite of facts
- Treating assistant text from ChatGPT or Codex as the VP's own words
- Answering from model prior knowledge instead of retrieved evidence
- Always answering, or always abstaining
- Tuning on the holdout, or hardcoding train answers
- Names, dates, or ids from the train data baked into code
- Unpinned dependencies, or a crash on a missing key
- Raw data committed against the terms
- README claims with no numbers
- The fresh-clone test left to the last hour
- Editing code after recording the commit hash
- Skipping the organizer questions because asking feels like a weakness

---

## 27. Change log

| Version | Change |
|---|---|
| 1.0.0 | Initial playbook: skills digest, CLAUDE.md block, frameworks, smoke tests |
| 2.0.0 | Added Part II for the memory-system take-home: requirements, decision slots, eval framework, repo spec, README template, bonus assistant, time-boxing, submission checklist, project smoke tests. Added Project mode block to CLAUDE.md. Added system-design, testing-strategy, documentation, hackathon-strategist skills. |

When either of you changes a rule, bump the version, add a row here, and commit.
