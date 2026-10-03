"""The memory end to end: ingest -> visibility -> retrieval -> answer."""
import sys
from datetime import datetime

from candor import config, ingest
from candor.answer import write_answer
from candor.index import Index
from candor.llm import LLM, LLMUnavailable
from candor.store import Memory

RETRIEVE_K = 20
EVIDENCE_K = 12


class Candor:
    def __init__(self, data_dir=config.DATA_DIR):
        self.corpus = ingest.load(data_dir)
        self.memory = Memory(self.corpus)
        self.index = Index(self.memory)
        self.llm = LLM()
        try:
            self.llm.check()
            self.llm_ok = True
        except LLMUnavailable as e:
            self.llm_ok = False
            print(f"WARNING: {e}. Retrieval still runs; answers will abstain.", file=sys.stderr)

    def ask(self, question: str, as_of: datetime) -> dict:
        ranked = [uid for uid, _ in self.index.search(question, as_of, k=RETRIEVE_K)]
        self.memory.assert_visible(ranked, as_of)
        if self.llm_ok:
            evidence = [self.memory.unit_at(uid, as_of) for uid in ranked[:EVIDENCE_K]]
            result = write_answer(self.llm, self.corpus.owner, question, as_of, evidence)
        else:
            result = {"answer": "I don't know: no answer model is configured.", "sources": [], "abstained": True}
        self.memory.assert_visible(result["sources"], as_of)
        return {**result, "retrieved": ranked}
