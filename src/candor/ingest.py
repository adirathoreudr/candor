"""Load every source in data/ into citable units.

Unit ids and delivery times follow data/README.md and match eval_harness/records.py exactly
(tests/test_ingest.py checks parity). Units carry more structure than the harness needs: who
produced the text and in what role, so attribution never depends on parsing display strings.
"""
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from candor.sanitize import clean

# author_kind values
PERSON, BOT, ASSISTANT, UNIDENTIFIED, SYSTEM = "person", "bot", "assistant", "unidentified", "system"


@dataclass(frozen=True)
class Unit:
    id: str
    record: str               # containing record (meeting, ChatGPT conversation); else same as id
    source: str               # meeting | dictation | slack | gmail | calendar | codex | chatgpt
    time: datetime            # delivery time: the unit does not exist before this
    text: str                 # sanitized content
    speaker: str | None       # who produced the text, None when unidentified
    author_kind: str          # person | bot | assistant | unidentified | system
    context: str              # where it was said: meeting title, channel, subject, ...
    meta: dict = field(default_factory=dict, hash=False, compare=False)


@dataclass
class Corpus:
    units: list[Unit]
    deleted: dict[str, datetime]                  # target id -> deletion time
    edits: dict[str, list[tuple[datetime, str]]]  # target id -> [(edit time, new text)]
    owner: str                                    # the Candor user, e.g. "Alex Rivera"
    owner_email: str
    people: list[dict]                            # Slack users
    channels: list[dict]


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def _read_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _owner(meetings: list[dict], people: list[dict]) -> tuple[str, str]:
    """The Candor user is the one participant present in every captured meeting."""
    counts = Counter(e for m in meetings for e in set(m.get("participants_known") or []))
    email = counts.most_common(1)[0][0]
    name = next((p["real_name"] for p in people if p.get("email") == email), email.split("@")[0])
    return name, email


def _meetings(d: Path) -> tuple[list[dict], list[Unit]]:
    meetings = [json.loads(f.read_text()) for f in sorted((d / "native/meetings").glob("*.json"))]
    units = []
    for m in meetings:
        start = _dt(m["start"])
        for s in m["segments"]:
            text, hidden = clean(s["text"])
            name = s.get("speaker_name")
            units.append(Unit(
                s["seg_id"], m["id"], "meeting", start + timedelta(seconds=s["end_s"]), text,
                name, PERSON if name else UNIDENTIFIED, m["title"],
                {"speaker_label": s.get("speaker_label"), "speaker_confidence": s.get("speaker_confidence"),
                 "channel": s.get("channel"), "meeting_start": m["start"], "offset_s": s["start_s"],
                 "meeting_type": m.get("type"), "calendar_event_id": m.get("calendar_event_id"),
                 "participants": m.get("participants_known") or [], "hidden_markup": hidden}))
    return meetings, units


def _dictation(d: Path, owner: str) -> list[Unit]:
    units = []
    for x in _read_jsonl(d / "native/dictation/dictations.jsonl"):
        text, hidden = clean(x["cleaned_text"])
        raw, _ = clean(x.get("raw_transcript"))
        units.append(Unit(
            x["id"], x["id"], "dictation", _dt(x["timestamp"]), text, owner, PERSON,
            f"Dictation ({x['mode']}) into {x['target_app']}: {x['target_context']}",
            {"mode": x["mode"], "target_app": x["target_app"], "target_context": x["target_context"],
             "delivery_state": x["delivery_state"], "raw_transcript": raw, "hidden_markup": hidden}))
    return units


def _slack(d: Path, people: list[dict], channels: list[dict]):
    names = {u["id"]: u["real_name"] for u in people}
    chans = {c["id"]: c for c in channels}
    units, deleted, edits = [], {}, {}
    for x in _read_jsonl(d / "connectors/slack/messages.jsonl"):
        t = _dt(x["ts"])
        chan = chans.get(x["channel_id"], {})
        where = ("DM " if chan.get("is_dm") else "#") + chan.get("name", x["channel_id"])
        base = {"channel_id": x["channel_id"], "is_dm": bool(chan.get("is_dm")), "user_id": x.get("user")}
        subtype = x.get("subtype")
        if subtype == "message_deleted":
            deleted[x["target_id"]] = t
            units.append(Unit(x["id"], x["id"], "slack", t, f"(message {x['target_id']} was deleted)",
                              names.get(x.get("user")), SYSTEM, f"Slack {where}",
                              {**base, "event": "deleted", "target_id": x["target_id"]}))
            continue
        text, hidden = clean(x.get("text"))
        if subtype == "message_changed":
            edits.setdefault(x["target_id"], []).append((t, text))
            units.append(Unit(x["id"], x["id"], "slack", t, text, names.get(x.get("user")), PERSON,
                              f"Slack {where}", {**base, "event": "edited", "target_id": x["target_id"],
                                                 "hidden_markup": hidden}))
            continue
        is_bot = subtype == "bot_message"
        speaker = (x.get("bot_name") or names.get(x.get("user")) or x.get("user")) if is_bot \
            else names.get(x.get("user"), x.get("user"))
        units.append(Unit(
            x["id"], x["id"], "slack", t, text, speaker, BOT if is_bot else PERSON, f"Slack {where}",
            {**base, "thread_parent_id": x.get("thread_parent_id"), "reactions": x.get("reactions") or [],
             "hidden_markup": hidden}))
    return units, deleted, edits


def _gmail(d: Path) -> list[Unit]:
    units = []
    for x in _read_jsonl(d / "connectors/gmail/messages.jsonl"):
        body, hidden = clean(x.get("body"))
        sender = x["from"]
        name = sender.split("<")[0].strip().strip('"') or sender
        units.append(Unit(
            x["id"], x["id"], "gmail", _dt(x["date"]), body, name, PERSON, f"Email: {x['subject']}",
            {"from": sender, "to": x.get("to") or [], "cc": x.get("cc") or [], "subject": x["subject"],
             "thread_id": x.get("thread_id"), "labels": x.get("labels") or [],
             "attachments": [a.get("filename") for a in x.get("attachments") or []], "hidden_markup": hidden}))
    return units


def _calendar(d: Path) -> list[Unit]:
    units = []
    for x in _read_jsonl(d / "connectors/google_calendar/events.jsonl"):
        st, en = x["start"], x["end"]
        description, hidden = clean(x.get("description"))
        units.append(Unit(
            x["id"], x["id"], "calendar", _dt(x["updated"]), description, x.get("organizer"), SYSTEM,
            f"Calendar: {x['summary']}",
            {"summary": x["summary"], "start": st.get("dateTime") or st.get("date"),
             "end": en.get("dateTime") or en.get("date"), "all_day": "date" in st,
             "location": x.get("location"), "status": x["status"], "organizer": x.get("organizer"),
             "attendees": x.get("attendees") or [], "recurrence": x.get("recurrence"),
             "created": x.get("created"), "hidden_markup": hidden}))
    return units


def _codex(d: Path, owner: str) -> list[Unit]:
    units = []
    for f in sorted((d / "connectors/codex/sessions").glob("*.jsonl")):
        events = _read_jsonl(f)
        meta, body = events[0], events[1:]
        turns = []
        for e in body:
            who = {"user": owner, "assistant": "Codex"}.get(e.get("role"), f"tool:{e.get('tool', e['type'])}")
            turns.append(f"{who}: {e.get('content') or e.get('input', '')}")
        text, hidden = clean("\n".join(turns))
        end = _dt(body[-1]["timestamp"] if body else meta["started_at"])
        units.append(Unit(
            meta["id"], meta["id"], "codex", end, text, owner, PERSON, f"Codex session in repo {meta.get('repo')}",
            {"repo": meta.get("repo"), "cwd": meta.get("cwd"), "started_at": meta.get("started_at"),
             "hidden_markup": hidden}))
    return units


def _chatgpt(d: Path, owner: str) -> list[Unit]:
    units = []
    for c in json.loads((d / "connectors/chatgpt/conversations.json").read_text()):
        for m in c["messages"]:
            text, hidden = clean(m["content"])
            is_user = m["role"] == "user"
            units.append(Unit(
                m["id"], c["id"], "chatgpt", _dt(m["create_time"]), text,
                owner if is_user else "ChatGPT", PERSON if is_user else ASSISTANT, f"ChatGPT: {c['title']}",
                {"role": m["role"], "conversation_title": c["title"], "hidden_markup": hidden}))
    return units


def load(data_dir: str | Path) -> Corpus:
    d = Path(data_dir)
    people = json.loads((d / "connectors/slack/users.json").read_text())
    channels = json.loads((d / "connectors/slack/channels.json").read_text())
    meetings, units = _meetings(d)
    owner, owner_email = _owner(meetings, people)
    slack, deleted, edits = _slack(d, people, channels)
    units += _dictation(d, owner) + slack + _gmail(d) + _calendar(d) + _codex(d, owner) + _chatgpt(d, owner)
    units.sort(key=lambda u: (u.time, u.id))
    for target in edits:
        edits[target].sort()
    return Corpus(units, deleted, edits, owner, owner_email, people, channels)
