"""Action normalization: the deterministic layer between the planner LLM and the dry-run output."""
from datetime import datetime

import pytest

from candor.actions import TYPES, Directory, _events, normalize
from candor.people import directory as people_directory


@pytest.fixture(scope="module")
def directory(corpus):
    return Directory(corpus, people_directory(corpus))


@pytest.fixture(scope="module")
def events(memory):
    return _events(memory, datetime.fromisoformat("2026-09-17T12:00:00-07:00"))


def one(raw, directory, events):
    [action] = normalize([raw], directory, events)
    return action


def test_slack_targets_resolve_to_ids(directory, events):
    assert one({"type": "slack.send_message", "args": {"to": "#route-planner", "text": "x"}}, directory, events)["args"]["to"] == "C10RP"
    assert one({"type": "slack.send_message", "args": {"to": "Ben Carter", "text": "x"}}, directory, events)["args"]["to"] == "U06BEN"
    assert one({"type": "slack.send_message", "args": {"to": "U06BEN", "text": "x"}}, directory, events)["args"]["to"] == "U06BEN"


def test_slack_only_considers_people_on_slack(directory, events):
    # Two Sarahs exist, but only one is on Slack, so "Sarah" on Slack is not ambiguous.
    assert one({"type": "slack.send_message", "args": {"to": "Sarah", "text": "x"}}, directory, events)["args"]["to"] == "U03SARAHK"


def test_ambiguous_email_recipient_becomes_clarify(directory, events):
    action = one({"type": "gmail.send", "args": {"to": ["Sarah"], "subject": "s", "body": "b"}}, directory, events)
    assert action["type"] == "clarify"
    assert "Sarah Kim" in action["args"]["question"] and "Sarah Patel" in action["args"]["question"]


def test_email_names_resolve_and_lists_are_lists(directory, events):
    args = one({"type": "gmail.send", "args": {"to": "John Okafor", "subject": "s", "body": "b"}}, directory, events)["args"]
    assert args["to"] == ["john@brightline.example.com"] and args["cc"] == []


def test_local_times_get_the_la_offset(directory, events):
    args = one({"type": "reminder.create", "args": {"text": "x", "due": "2026-09-25T09:00"}}, directory, events)["args"]
    assert args["due"] == "2026-09-25T09:00:00-07:00"
    args = one({"type": "reminder.create", "args": {"text": "x", "due": "2026-09-25T16:00:00Z"}}, directory, events)["args"]
    assert args["due"] == "2026-09-25T09:00:00-07:00"


def test_moved_event_keeps_its_length(directory, events):
    event_id, meta = next((i, m) for i, m in events.items() if not m.get("recurrence") and not m.get("all_day"))
    length = datetime.fromisoformat(meta["end"]) - datetime.fromisoformat(meta["start"])
    args = one({"type": "calendar.update_event", "args": {"event_id": event_id, "start": "2026-09-18T15:00"}},
               directory, events)["args"]
    assert datetime.fromisoformat(args["end"]) - datetime.fromisoformat(args["start"]) == length


def test_unknown_event_and_unknown_type_become_clarify(directory, events):
    assert one({"type": "calendar.update_event", "args": {"event_id": "CAL-NOPE", "start": "2026-09-18T15:00"}},
               directory, events)["type"] == "clarify"
    assert one({"type": "email.delete_all", "args": {}}, directory, events)["type"] == "clarify"


def test_new_event_defaults_to_thirty_minutes(directory, events):
    args = one({"type": "calendar.create_event", "args": {"title": "t", "start": "2026-09-17T14:00", "attendees": ["Ben"]}},
               directory, events)["args"]
    assert args["end"] == "2026-09-17T14:30:00-07:00" and args["attendees"] == ["ben@brightline.example.com"]


WED = datetime.fromisoformat("2026-09-16T10:00:00-07:00")


def test_named_weekday_corrects_a_wrong_date(directory, events):
    raw = {"type": "calendar.create_event", "args": {"title": "t", "start": "2026-09-18T10:00", "end": "2026-09-18T11:00"}}
    [a] = normalize([raw], directory, events, "Set up an hour on Monday at 10", WED)
    assert (a["args"]["start"], a["args"]["end"]) == ("2026-09-21T10:00:00-07:00", "2026-09-21T11:00:00-07:00")


def test_named_weekday_moves_a_past_date_forward(directory, events):
    event_id = next(i for i, m in events.items() if not m.get("recurrence") and not m.get("all_day"))
    raw = {"type": "calendar.update_event", "args": {"event_id": event_id, "start": "2026-09-11T14:00", "end": "2026-09-11T15:30"}}
    [a] = normalize([raw], directory, events, "Push my Friday block to 2pm", WED)
    assert a["args"]["start"] == "2026-09-18T14:00:00-07:00" and a["args"]["end"] == "2026-09-18T15:30:00-07:00"


def test_weekday_guard_leaves_correct_past_and_ambiguous_alone(directory, events):
    ok = {"type": "reminder.create", "args": {"text": "x", "due": "2026-09-21T09:00"}}
    assert normalize([ok], directory, events, "Remind me Monday at 9", WED)[0]["args"]["due"] == "2026-09-21T09:00:00-07:00"
    past = {"type": "reminder.create", "args": {"text": "x", "due": "2026-09-14T09:00"}}
    assert normalize([past], directory, events, "What did I do last Monday", WED)[0]["args"]["due"] == "2026-09-14T09:00:00-07:00"
    two = {"type": "reminder.create", "args": {"text": "x", "due": "2026-09-18T09:00"}}
    assert normalize([two], directory, events, "Monday or Friday", WED)[0]["args"]["due"] == "2026-09-18T09:00:00-07:00"


def test_right_weekday_today_or_later_is_never_moved(directory, events):
    for due in ("2026-09-16T15:00", "2026-09-23T15:00"):     # today, or a week out: both valid readings
        raw = {"type": "reminder.create", "args": {"text": "x", "due": due}}
        assert normalize([raw], directory, events, "Wednesday at 3pm", WED)[0]["args"]["due"] == due + ":00-07:00"


def test_weekday_shift_recomputes_the_offset_across_dst(directory, events):
    sat = datetime.fromisoformat("2026-10-31T10:00:00-07:00")
    raw = {"type": "reminder.create", "args": {"text": "x", "due": "2026-10-30T09:00"}}   # a Friday, in the past
    assert normalize([raw], directory, events, "Monday at 9", sat)[0]["args"]["due"] == "2026-11-02T09:00:00-08:00"


def test_empty_clarify_and_confirm_still_say_something(directory, events):
    cmd = "Message Sarah Patel on Slack that the proposal is coming"
    [c, f] = normalize([{"type": "clarify", "args": {}}, {"type": "confirm", "args": {"summary": " "}}],
                       directory, events, cmd, WED)
    assert cmd in c["args"]["question"] and cmd in f["args"]["summary"]


def test_only_interface_types_leave(directory, events):
    raw = [{"type": t, "args": {}} for t in ["memory.ask", "app.open", "confirm", "shell.exec"]]
    assert all(a["type"] in TYPES for a in normalize(raw, directory, events))


def test_events_exclude_cancelled_and_far_away(memory, events):
    cancelled = {u.id for u in memory.corpus.units if u.source == "calendar" and u.meta["status"] == "cancelled"}
    assert not cancelled & set(events)
