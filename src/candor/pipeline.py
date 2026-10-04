"""The memory end to end: ingest -> visibility -> plan -> search -> rerank -> answer.

LLM stages fail per question, not per run. With no key (or an exhausted quota) every call that is in
the committed cache still replays, so a clean clone reproduces the committed outputs exactly; a stage
that needs a live call falls back for that one question (search on the question alone, keep the fused
order, or answer "I don't know") and is counted and reported, never hidden.
"""
import os
import sys
from datetime import datetime

from candor import config, ingest, people
from candor.actions import Directory, plan_actions
from candor.answer import write_answer
from candor.index import Index
from candor.llm import LLM, LLMUnavailable
from candor.retrieve import FOLLOWUP_EVIDENCE, expand, make_followup, make_plan, rerank, search
from candor.store import Memory

RETRIEVE_K = 20
EVIDENCE_K = 12
# Ablation switches (README eval tables): set to 0 to turn a stage off.
USE_PLAN = os.environ.get("CANDOR_PLAN", "1") != "0"
USE_RERANK = os.environ.get("CANDOR_RERANK", "1") != "0"
NO_ANSWER = "I don't know: no answer model is available for this question."


class Candor:
    def __init__(self, data_dir=config.DATA_DIR):
        self.corpus = ingest.load(data_dir)
        self.memory = Memory(self.corpus)
        self.index = Index(self.memory)
        self.people = people.directory(self.corpus)
        self.llm = LLM()
        self.llm_plan = LLM(model=config.LLM_MODEL_PLAN, max_tokens=2000)
        self.llm_rerank = LLM(model=config.LLM_MODEL_RERANK, max_tokens=2000)
        self.llm_act = LLM(model=config.LLM_MODEL_ACT, max_tokens=2000)
        self.directory = Directory(self.corpus, self.people)
        self.degraded: dict[str, str] = {}   # stage -> last reason, for the end-of-run report
        self.degraded_count = 0
        try:
            self.llm.check()
        except LLMUnavailable as e:
            print(f"WARNING: {e}. Cached LLM calls still replay; anything else falls back per question "
                  f"(search on the question alone, answers abstain).", file=sys.stderr)

    def _fallback(self, stage: str, error: LLMUnavailable) -> None:
        self.degraded[stage] = str(error)
        self.degraded_count += 1

    def retrieve(self, question: str, as_of: datetime) -> list[str]:
        owner = self.corpus.owner
        plans = []
        if USE_PLAN:
            try:
                plan = make_plan(self.llm_plan, owner, self.people, question, as_of)
                plans.append(plan)
                if plan.followup:
                    first = search(self.index, question, as_of, plans)[:FOLLOWUP_EVIDENCE]
                    evidence = [self.memory.unit_at(uid, as_of) for uid in first]
                    plans.append(make_followup(self.llm_plan, owner, question, as_of, plan, evidence))
            except LLMUnavailable as e:
                self._fallback("plan", e)
        ranked = search(self.index, question, as_of, plans)
        if USE_RERANK:
            at = lambda ids: [self.memory.unit_at(u, as_of) for u in ids]   # noqa: E731
            try:
                ranked = rerank(self.llm_rerank, owner, question, as_of, at(ranked), at(expand(self.index, as_of, ranked)))
            except LLMUnavailable as e:
                self._fallback("rerank", e)
        ranked = ranked[:RETRIEVE_K]
        self.memory.assert_visible(ranked, as_of)
        return ranked

    def ask(self, question: str, as_of: datetime) -> dict:
        ranked = self.retrieve(question, as_of)
        evidence = [self.memory.unit_at(uid, as_of) for uid in ranked[:EVIDENCE_K]]
        try:
            result = write_answer(self.llm, self.corpus.owner, question, as_of, evidence)
        except LLMUnavailable as e:
            self._fallback("answer", e)
            result = {"answer": NO_ANSWER, "sources": [], "abstained": True}
        self.memory.assert_visible(result["sources"], as_of)
        return {**result, "retrieved": ranked}

    @property
    def data_end(self) -> datetime:
        """The last moment anything was said or written: a sensible 'now' for the interactive assistant.
        Calendar events are excluded because they carry future dates."""
        return max(u.time for u in self.corpus.units if u.source != "calendar")

    def act(self, command: str, as_of: datetime) -> list[dict]:
        """Dry run: the actions the command would take. Needs an LLM (or a cached plan); fails loud without."""
        return plan_actions(self.llm_act, self.memory, self.index, self.directory, self.people, command, as_of)

    def report(self) -> str:
        """Usage per role, plus any per-question fallbacks (empty string when nothing fell back)."""
        lines = [" | ".join(f"{name} {llm.model}: {llm.usage.summary()}" for name, llm in (
            ("plan", self.llm_plan), ("rerank", self.llm_rerank), ("answer", self.llm), ("act", self.llm_act))
            if llm.usage.calls or llm.usage.cache_hits)]
        if self.degraded:
            lines.append(f"WARNING: {self.degraded_count} LLM step(s) fell back "
                         f"({', '.join(sorted(self.degraded))}): {next(iter(self.degraded.values()))}")
        return "\n".join(lines)
