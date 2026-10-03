"""Command -> actions, dry run.

The LLM proposes actions in human terms; code makes them exact:
- people and channels resolve to the ids in data/ (Slack user ids, channel ids, email addresses),
- local wall-clock times get the America/Los_Angeles offset (the model never does offset math),
- a moved event keeps its length unless a new end is given,
- anything that cannot be resolved becomes a `clarify` instead of a guess,
- only the nine action types of the interface ever leave this module.
"""
from datetime import datetime, timedelta

from candor import config
from candor.answer import format_record
from candor.calendar import LOCAL, occurs_between
from candor.index import Index
from candor.ingest import Corpus
from candor.llm import LLM
from candor.people import Person
from candor.store import Memory

TYPES = {"slack.send_message", "gmail.send", "calendar.create_event", "calendar.update_event", "reminder.create",
         "memory.ask", "app.open", "clarify", "confirm"}
DEFAULT_MEETING = timedelta(minutes=30)   # "book time with Ben" without a length
EVIDENCE_K = 6
DAYS_BACK, DAYS_AHEAD = 7, 21


class Unresolved(ValueError):
    """An argument names something that is not in the data (or names more than one thing)."""


class Directory:
    """Name -> id resolution over people, Slack channels and DMs."""

    def __init__(self, corpus: Corpus, people: list[Person]):
        self.owner = corpus.owner
        self.people = [p for p in people if p.name != corpus.owner]
        self.channels = {c["id"]: c for c in corpus.channels}
        self.slack_users = {u["id"] for u in corpus.people}

    def _person(self, value: str, need: str) -> Person:
        v = value.strip().lstrip("@").lower()
        pool = [p for p in self.people if getattr(p, need)]
        for match in (
            [p for p in pool if p.name.lower() == v],
            [p for p in pool if v in {e.lower() for e in p.emails}],
            [p for p in pool if p.name.lower().split()[0] == v],
            [p for p in pool if v in p.name.lower()],
        ):
            if len(match) == 1:
                return match[0]
            if len(match) > 1:
                raise Unresolved(f"Which {value} do you mean: {' or '.join(p.name for p in match)}?")
        raise Unresolved(f"I couldn't find {value!r} {'on Slack' if need == 'slack_id' else 'in your contacts'}.")

    def slack_target(self, value) -> str:
        v = str(value).strip()
        if v in self.slack_users or v in self.channels:
            return v
        by_name = [cid for cid, c in self.channels.items() if not c.get("is_dm") and c["name"] == v.lstrip("#").lower()]
        if by_name:
            return by_name[0]
        return self._person(v, "slack_id").slack_id

    def email(self, value) -> str:
        v = str(value).strip().lower()
        if "@" in v:
            return v
        return sorted(self._person(str(value), "emails").emails)[0]

    def describe_channels(self) -> str:
        names = {u: p.name for p in self.people for u in [p.slack_id] if u}
        lines = []
        for cid, c in self.channels.items():
            if c.get("is_dm"):
                other = [names.get(m, m) for m in c.get("members", []) if names.get(m)]
                lines.append(f"- {cid}: direct message with {', '.join(other) or 'unknown'}")
            else:
                lines.append(f"- {cid}: #{c['name']}")
        return "\n".join(lines)


def _local(value) -> str:
    """ISO 8601 with the America/Los_Angeles offset; naive times are local wall-clock time."""
    dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    dt = dt.replace(tzinfo=LOCAL) if dt.tzinfo is None else dt.astimezone(LOCAL)
    return dt.isoformat(timespec="seconds")


def _as_list(value) -> list:
    if value in (None, ""):
        return []
    return value if isinstance(value, list) else [value]


def normalize(raw: list[dict], directory: Directory, events: dict) -> list[dict]:
    out = []
    for action in raw if isinstance(raw, list) else []:
        kind, args = action.get("type"), dict(action.get("args") or {})
        try:
            if kind not in TYPES:
                raise Unresolved(f"I can't do {kind!r} yet. What would you like instead?")
            if kind == "slack.send_message":
                args["to"] = directory.slack_target(args.get("to"))
            elif kind == "gmail.send":
                args["to"] = [directory.email(v) for v in _as_list(args.get("to"))]
                args["cc"] = [directory.email(v) for v in _as_list(args.get("cc"))]
                if not args["to"]:
                    raise Unresolved("Who should the email go to?")
            elif kind == "calendar.create_event":
                args["start"] = _local(args["start"])
                args["end"] = _local(args["end"]) if args.get("end") else \
                    (datetime.fromisoformat(args["start"]) + DEFAULT_MEETING).isoformat(timespec="seconds")
                args["attendees"] = [directory.email(v) for v in _as_list(args.get("attendees"))]
            elif kind == "calendar.update_event":
                event = events.get(args.get("event_id"))
                if event is None:
                    raise Unresolved(f"Which event do you mean? I couldn't find {args.get('event_id')!r}.")
                for key in ("start", "end"):
                    if args.get(key):
                        args[key] = _local(args[key])
                if args.get("start") and not args.get("end"):
                    length = datetime.fromisoformat(event["end"]) - datetime.fromisoformat(event["start"])
                    args["end"] = (datetime.fromisoformat(args["start"]) + length).isoformat(timespec="seconds")
            elif kind == "reminder.create":
                args["due"] = _local(args["due"])
        except Unresolved as e:
            kind, args = "clarify", {"question": str(e)}
        except (KeyError, TypeError, ValueError) as e:
            kind, args = "clarify", {"question": f"I couldn't work out the details ({type(e).__name__}). Can you rephrase?"}
        out.append({"type": kind, "args": args})
    return out


def _days(as_of: datetime) -> str:
    today = as_of.astimezone(LOCAL).date()
    lines = []
    for k in range(-DAYS_BACK, DAYS_AHEAD + 1):
        d = today + timedelta(days=k)
        tag = {0: " (today)", 1: " (tomorrow)", -1: " (yesterday)"}.get(k, "")
        lines.append(f"{d.strftime('%a')} {d.isoformat()}{tag}")
    return ", ".join(lines)


def _events(memory: Memory, as_of: datetime) -> dict[str, dict]:
    """Calendar events visible at as_of that happen within the window around now."""
    today = as_of.astimezone(LOCAL).date()
    lo, hi = today - timedelta(days=DAYS_BACK), today + timedelta(days=DAYS_AHEAD)
    return {u.id: u.meta for u in memory.visible(as_of)
            if u.source == "calendar" and u.meta["status"] != "cancelled" and occurs_between(u.meta, lo, hi)}


def plan_actions(llm: LLM, memory: Memory, index: Index, directory: Directory, people: list[Person],
                 command: str, as_of: datetime) -> list[dict]:
    events = _events(memory, as_of)
    evidence = [memory.unit_at(uid, as_of) for uid, _ in index.search(command, as_of, k=EVIDENCE_K)]
    prompt = (config.PROMPTS / "act.v1.md").read_text().format(
        owner=memory.corpus.owner, command=command,
        as_of_local=as_of.astimezone(LOCAL).strftime("%Y-%m-%d %H:%M"), as_of_weekday=as_of.astimezone(LOCAL).strftime("%A"),
        days=_days(as_of),
        people="\n".join(f"- {p.describe()}" for p in people if p.name != memory.corpus.owner),
        channels=directory.describe_channels(),
        events="\n".join(f"- {eid} | {m['summary']} | {m['start']} - {m['end']}"
                         f"{' | repeats ' + ';'.join(m['recurrence']) if m.get('recurrence') else ''}"
                         f" | {', '.join(a['email'] for a in m['attendees'])}" for eid, m in sorted(events.items())),
        records="\n".join(format_record(u, 400) for u in evidence) or "(none)")
    out = llm.complete_json("You are a careful assistant that replies with a single JSON object.", prompt)
    return normalize(out.get("actions") or [], directory, events)
