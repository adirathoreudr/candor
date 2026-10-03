from datetime import timedelta

from candor import config


def test_visibility_matches_harness_at_every_train_moment(memory, harness, train_as_ofs):
    for as_of in train_as_ofs:
        ours = {u.id: u.text for u in memory.visible(as_of)}
        theirs = {u.id for u in harness.visible(config.DATA_DIR, as_of)}
        # The harness keeps deletion events as units; we drop them (bookkeeping, not content).
        theirs = {i for i in theirs if memory.by_id[i].meta.get("event") != "deleted"}
        assert set(ours) == theirs, as_of


def test_nothing_visible_is_forbidden(memory, harness, train_as_ofs):
    ctx = harness.context(config.DATA_DIR)
    for as_of in train_as_ofs:
        for u in memory.visible(as_of):
            assert ctx["avail"][u.id] <= as_of
            assert not (u.id in ctx["deleted"] and ctx["deleted"][u.id] <= as_of)


def test_deleted_message_disappears_at_deletion_time(memory):
    target, gone = next(iter(memory.corpus.deleted.items()))
    created = memory.by_id[target].time
    assert memory.is_visible(target, created)
    assert memory.is_visible(target, gone - timedelta(seconds=1))
    assert not memory.is_visible(target, gone)


def test_edit_replaces_text_from_edit_time(memory):
    target, history = next(iter(memory.corpus.edits.items()))
    edit_time, new_text = history[-1]
    before = {u.id: u for u in memory.visible(edit_time - timedelta(seconds=1))}[target]
    after = {u.id: u for u in memory.visible(edit_time)}[target]
    assert before.text != new_text
    assert after.text == new_text and after.meta["edited"]


def test_future_is_invisible(memory):
    first = min(u.time for u in memory.corpus.units)
    assert memory.visible(first - timedelta(seconds=1)) == []
    assert [u.id for u in memory.visible(first)] == [u.id for u in memory.corpus.units if u.time == first]
