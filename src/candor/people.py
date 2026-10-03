"""Directory of everyone in the data: names, emails, Slack ids, gathered from every source's headers.

Used to tell the query planner who exists (two people can share a first name) and, in the action
planner, to turn a name into a Slack id or email address.
"""
import re
from dataclasses import dataclass, field

from candor.ingest import Corpus

_ADDR_RE = re.compile(r"^\s*\"?([^\"<]*?)\"?\s*<([^>]+)>\s*$")


@dataclass
class Person:
    name: str
    emails: set[str] = field(default_factory=set)
    slack_id: str | None = None
    title: str | None = None

    @property
    def org(self) -> str:
        return next(iter(sorted(e.split("@")[1].split(".")[0] for e in self.emails)), "")

    def describe(self) -> str:
        bits = [self.title] if self.title else []
        bits += sorted(self.emails)
        if self.slack_id:
            bits.append(f"Slack {self.slack_id}")
        return f"{self.name} ({', '.join(bits)})" if bits else self.name


def _name_from_email(email: str) -> str:
    local = email.split("@")[0]
    return " ".join(p.capitalize() for p in re.split(r"[._]", local) if p)


def directory(corpus: Corpus) -> list[Person]:
    by_email: dict[str, Person] = {}

    def add(name: str | None, email: str | None, **extra) -> None:
        if not email or "@" not in email:
            return
        email = email.strip().lower()
        p = by_email.get(email)
        if p is None:
            p = by_email[email] = Person(name=(name or "").strip() or _name_from_email(email), emails={email})
        elif name and p.name == _name_from_email(email):
            p.name = name.strip()          # a real display name beats one guessed from the address
        for k, v in extra.items():
            if v:
                setattr(p, k, v)

    for u in corpus.people:
        add(u.get("real_name"), u.get("email"), slack_id=u.get("id"), title=u.get("title"))
    for unit in corpus.units:
        m = unit.meta
        if unit.source == "gmail":
            for raw in [m["from"], *m["to"], *m["cc"]]:
                hit = _ADDR_RE.match(raw)
                add(hit.group(1), hit.group(2)) if hit else add(None, raw)
        elif unit.source == "calendar":
            for a in m["attendees"]:
                add(None, a.get("email"))
        elif unit.source == "meeting":
            for e in m["participants"]:
                add(None, e)
    people = sorted(by_email.values(), key=lambda p: p.name)
    return [p for p in people if not any(e.split("@")[0] in _AUTOMATED for e in p.emails)]


# Mailbox names used by services and lists, not people.
_AUTOMATED = {"noreply", "no-reply", "notifications", "notify", "digest", "news", "reminders", "events",
              "partners", "hello", "calendar-notification", "all", "team", "support", "info"}
