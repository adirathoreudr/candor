"""Plan / search / rerank stages with a fake LLM: no network, deterministic."""
from datetime import date

import pytest

from candor.index import Index
from candor.people import directory
from candor.retrieve import Plan, expand, make_plan, rerank, search


class FakeLLM:
    def __init__(self, reply: dict):
        self.reply, self.prompts = reply, []

    def complete_json(self, system, user):
        self.prompts.append(user)
        return self.reply


@pytest.fixture(scope="module")
def index(memory):
    return Index(memory)


def test_plan_parses_and_sanitizes_llm_output(corpus, train_as_ofs):
    llm = FakeLLM({"queries": ["a b", "", 3, "c", "d", "e", "f"], "date_from": "2026-09-10", "date_to": "not a date",
                   "followup": None})
    plan = make_plan(llm, corpus.owner, directory(corpus), "q?", train_as_ofs[-1])
    assert plan.queries == ["a b", "3", "c", "d"]            # empties dropped, max 4
    assert plan.window == (date(2026, 9, 10), date(2026, 9, 10))
    assert plan.followup == ""
    assert "Sarah Patel" in llm.prompts[0] and "Sarah Kim" in llm.prompts[0]   # planner sees the directory


def test_window_is_ordered_and_optional():
    assert Plan().window is None
    assert Plan(date_from=date(2026, 9, 20), date_to=date(2026, 9, 10)).window == (date(2026, 9, 10), date(2026, 9, 20))


def test_search_without_plans_is_the_index_order(index, train_as_ofs):
    as_of = train_as_ofs[-1]
    assert search(index, "launch date", as_of, [])[:20] == [u for u, _ in index.search("launch date", as_of, k=20)]


def test_date_window_brings_in_that_days_calendar(index, memory, train_as_ofs):
    as_of = train_as_ofs[-1]
    future = next(u for u in memory.visible(as_of) if u.source == "calendar" and not u.meta.get("recurrence")
                  and date.fromisoformat(u.meta["start"][:10]) > as_of.date())
    day = date.fromisoformat(future.meta["start"][:10])
    ranked = search(index, "what is on my calendar", as_of, [Plan(date_from=day, date_to=day)])
    assert future.id in ranked[:10]


def test_search_and_expansion_never_leave_the_visible_set(index, memory, train_as_ofs):
    for as_of in train_as_ofs:
        ranked = search(index, "launch moved", as_of, [Plan(queries=["geocoding regression"])])
        for uid in ranked + expand(index, as_of, ranked):
            assert memory.is_visible(uid, as_of)


def test_rerank_puts_picks_first_and_drops_nothing(memory, train_as_ofs):
    as_of = train_as_ofs[-1]
    units = memory.visible(as_of)[:40]
    ids = [u.id for u in units]
    llm = FakeLLM({"ranked": [ids[5], "NOT-AN-ID", ids[35], ids[5]]})
    out = rerank(llm, "Owner", "q?", as_of, units)
    assert out[:2] == [ids[5], ids[0]]       # ids[35] is outside the pool the judge saw: it cannot be promoted
    assert "NOT-AN-ID" not in out
    assert sorted(out) == sorted(ids)                        # same set: demote, never drop
