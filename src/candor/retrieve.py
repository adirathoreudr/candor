"""Question -> ranked evidence ids.

1. Plan (LLM): keyword rewrites in the records' own vocabulary, a date window if the question names
   one, and whether a second hop is needed ("the day I fly" -> find the flight date first).
2. Search: every query through the hybrid index, plus every visible record inside the date window
   (calendar events by when they occur, everything else by when it was delivered), fused by RRF.
3. Rerank (LLM): the top candidates, judged against the question; anything it leaves out keeps its
   fused order after the ones it picked, so a reranker mistake can demote but never drop a record.

Without an LLM only step 2 runs, on the question alone.
"""
from dataclasses import dataclass, field
from datetime import date, datetime

from candor import config
from candor.answer import format_record
from candor.calendar import LOCAL, occurs_between
from candor.index import Index
from candor.llm import LLM
from candor.people import Person

SEARCH_DEPTH = 50          # per-query list length fed into fusion
RRF_K = 60
# A question that names a day is about that day: being in the window weighs as much as all the
# text queries together (the question plus up to four rewrites), not as one more list among them.
WINDOW_WEIGHT = 3.0
# Records linked to a top hit (its thread, the message a dictation became) join the rerank pool, so
# a cause stated in different words (a thread root, an earlier reply) can still be judged relevant.
EXPAND_FROM = 10
EXPAND_MAX = 10
RERANK_POOL = 30           # candidates the reranker sees
RERANK_SNIPPET = 300       # characters per candidate
FOLLOWUP_EVIDENCE = 8      # first-hop records shown to the follow-up planner


@dataclass
class Plan:
    queries: list[str] = field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None
    followup: str = ""

    @property
    def window(self) -> tuple[date, date] | None:
        if not (self.date_from or self.date_to):
            return None
        start, end = self.date_from or self.date_to, self.date_to or self.date_from
        return (start, end) if start <= end else (end, start)


def _date(value) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def _queries(value) -> list[str]:
    return [str(q).strip() for q in (value or []) if str(q).strip()][:4]


def _prompt(name: str, **fields) -> str:
    return (config.PROMPTS / f"{name}.md").read_text().format(**fields)


def make_plan(llm: LLM, owner: str, people: list[Person], question: str, as_of: datetime) -> Plan:
    out = llm.complete_json("You are a careful assistant that replies with a single JSON object.", _prompt(
        "plan.v1", owner=owner, as_of=as_of.isoformat(), as_of_weekday=as_of.strftime("%A"), question=question,
        people="\n".join(f"- {p.describe()}" for p in people)))
    return Plan(_queries(out.get("queries")), _date(out.get("date_from")), _date(out.get("date_to")),
                str(out.get("followup") or "").strip())


def make_followup(llm: LLM, owner: str, question: str, as_of: datetime, plan: Plan, evidence) -> Plan:
    out = llm.complete_json("You are a careful assistant that replies with a single JSON object.", _prompt(
        "followup.v1", owner=owner, as_of=as_of.isoformat(), as_of_weekday=as_of.strftime("%A"), question=question,
        followup=plan.followup, records="\n".join(format_record(u, RERANK_SNIPPET) for u in evidence)))
    return Plan(_queries(out.get("queries")), _date(out.get("date_from")), _date(out.get("date_to")))


def _in_window(unit, window: tuple[date, date]) -> bool:
    if unit.source == "calendar":
        return occurs_between(unit.meta, *window)
    return window[0] <= unit.time.astimezone(LOCAL).date() <= window[1]


def search(index: Index, question: str, as_of: datetime, plans: list[Plan]) -> list[str]:
    """Fuse the question's own ranking, every planned query, and each plan's date window."""
    lists = [(1.0, [uid for uid, _ in index.search(question, as_of, k=SEARCH_DEPTH)])]
    for plan in plans:
        lists += [(1.0, [uid for uid, _ in index.search(q, as_of, k=SEARCH_DEPTH)]) for q in plan.queries]
        if plan.window:
            probe = " ".join([question, *plan.queries])
            ranked_all = index.search(probe, as_of, k=len(index.docs))
            in_window = [uid for uid, _ in ranked_all if _in_window(index.memory.by_id[uid], plan.window)]
            lists.append((WINDOW_WEIGHT, in_window[:SEARCH_DEPTH]))
    fused: dict[str, float] = {}
    for weight, ranked in lists:
        for rank, uid in enumerate(ranked):
            fused[uid] = fused.get(uid, 0.0) + weight / (RRF_K + rank + 1)
    return sorted(fused, key=lambda uid: -fused[uid])


def expand(index: Index, as_of: datetime, ranked: list[str]) -> list[str]:
    """Linked records of the top hits that are not already in the rerank pool."""
    pool, extra = set(ranked[:RERANK_POOL]), []
    for uid in ranked[:EXPAND_FROM]:
        for partner in index.links.get(uid, {}):
            if partner not in pool and partner not in extra and index.memory.is_visible(partner, as_of) \
                    and index.memory.by_id[partner].source != "calendar":   # one event per meeting: no signal
                extra.append(partner)
    return extra[:EXPAND_MAX]


def rerank(llm: LLM, owner: str, question: str, as_of: datetime, units, extra=()) -> list[str]:
    """`units`: fused order. `extra`: linked records shown to the judge but kept last unless picked."""
    pool = list(units[:RERANK_POOL]) + list(extra)
    out = llm.complete_json("You are a careful assistant that replies with a single JSON object.", _prompt(
        "rerank.v1", owner=owner, as_of=as_of.isoformat(), as_of_weekday=as_of.strftime("%A"), question=question,
        records="\n".join(format_record(u, RERANK_SNIPPET) for u in pool)))
    allowed = {u.id for u in pool}
    picked = []
    for uid in out.get("ranked") or []:
        if uid in allowed and uid not in picked:
            picked.append(uid)
    rest = [u.id for u in units if u.id not in picked]
    return picked + rest
