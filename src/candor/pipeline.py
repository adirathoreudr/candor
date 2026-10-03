"""The memory end to end: ingest -> visibility -> plan -> search -> rerank -> answer."""
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
        try:
            self.llm.check()
            self.llm_ok = True
        except LLMUnavailable as e:
            self.llm_ok = False
            print(f"WARNING: {e}. Retrieval still runs on the question alone; answers will abstain.", file=sys.stderr)

    def retrieve(self, question: str, as_of: datetime) -> list[str]:
        owner = self.corpus.owner
        plans = []
        if self.llm_ok and USE_PLAN:
            plan = make_plan(self.llm_plan, owner, self.people, question, as_of)
            plans.append(plan)
            if plan.followup:
                first = search(self.index, question, as_of, plans)[:FOLLOWUP_EVIDENCE]
                evidence = [self.memory.unit_at(uid, as_of) for uid in first]
                plans.append(make_followup(self.llm_plan, owner, question, as_of, plan, evidence))
        ranked = search(self.index, question, as_of, plans)
        if self.llm_ok and USE_RERANK:
            at = lambda ids: [self.memory.unit_at(u, as_of) for u in ids]   # noqa: E731
            ranked = rerank(self.llm_rerank, owner, question, as_of, at(ranked), at(expand(self.index, as_of, ranked)))
        ranked = ranked[:RETRIEVE_K]
        self.memory.assert_visible(ranked, as_of)
        return ranked

    def ask(self, question: str, as_of: datetime) -> dict:
        ranked = self.retrieve(question, as_of)
        if self.llm_ok:
            evidence = [self.memory.unit_at(uid, as_of) for uid in ranked[:EVIDENCE_K]]
            result = write_answer(self.llm, self.corpus.owner, question, as_of, evidence)
        else:
            result = {"answer": "I don't know: no answer model is configured.", "sources": [], "abstained": True}
        self.memory.assert_visible(result["sources"], as_of)
        return {**result, "retrieved": ranked}

    def act(self, command: str, as_of: datetime) -> list[dict]:
        """Dry run: the actions the command would take. Needs an LLM; fails loud without one."""
        if not self.llm_ok:
            raise LLMUnavailable("actions need an LLM backend: set LLM_API_KEY in .env (see .env.example)")
        return plan_actions(self.llm_act, self.memory, self.index, self.directory, self.people, command, as_of)

    def usage(self) -> str:
        return " | ".join(f"{name} {llm.model}: {llm.usage.summary()}" for name, llm in (
            ("plan", self.llm_plan), ("rerank", self.llm_rerank), ("answer", self.llm), ("act", self.llm_act))
            if llm.usage.calls or llm.usage.cache_hits)
