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


def test_only_interface_types_leave(directory, events):
    raw = [{"type": t, "args": {}} for t in ["memory.ask", "app.open", "confirm", "shell.exec"]]
    assert all(a["type"] in TYPES for a in normalize(raw, directory, events))


def test_events_exclude_cancelled_and_far_away(memory, events):
    cancelled = {u.id for u in memory.corpus.units if u.source == "calendar" and u.meta["status"] == "cancelled"}
    assert not cancelled & set(events)
