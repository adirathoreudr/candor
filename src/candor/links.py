"""Links between records that belong together, built deterministically from the data's own structure.

Kinds:
- email_thread:   messages that share a Gmail thread id
- dictation_sent: a dictation and the owner's email or Slack message with near-identical text sent
                  within a day after it (so "did it go out" can find both halves)
- slack_thread:   a Slack reply and its thread root
- meeting_event:  a meeting segment and the calendar event the meeting was scheduled as
"""
from collections import defaultdict
from datetime import timedelta

from candor.ingest import Corpus
from candor.text import tokenize

EMAIL_THREAD, DICTATION_SENT, SLACK_THREAD, MEETING_EVENT = "email_thread", "dictation_sent", "slack_thread", "meeting_event"

DICTATION_WINDOW = timedelta(hours=24)
DICTATION_MIN_OVERLAP = 0.6   # Jaccard over content terms; the sent text is the cleaned dictation, maybe lightly edited


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def build(corpus: Corpus) -> dict[str, dict[str, str]]:
    """unit id -> {linked unit id: link kind}, symmetric."""
    links: dict[str, dict[str, str]] = defaultdict(dict)

    def link(a: str, b: str, kind: str) -> None:
        if a != b:
            links[a][b] = kind
            links[b][a] = kind

    by_id = {u.id: u for u in corpus.units}
    threads = defaultdict(list)
    for u in corpus.units:
        if u.source == "slack" and u.meta.get("thread_parent_id") in by_id:
            link(u.id, u.meta["thread_parent_id"], SLACK_THREAD)
        elif u.source == "gmail" and u.meta.get("thread_id"):
            threads[u.meta["thread_id"]].append(u.id)
        elif u.source == "meeting" and u.meta.get("calendar_event_id") in by_id:
            link(u.id, u.meta["calendar_event_id"], MEETING_EVENT)
    for ids in threads.values():
        for a in ids:
            for b in ids:
                link(a, b, EMAIL_THREAD)

    sent = [u for u in corpus.units if u.source in ("gmail", "slack") and u.speaker == corpus.owner]
    for d in (u for u in corpus.units if u.source == "dictation" and u.meta["mode"] == "dictation"):
        terms = set(tokenize(d.text))
        for u in sent:
            if d.time <= u.time <= d.time + DICTATION_WINDOW and _jaccard(terms, set(tokenize(u.text))) >= DICTATION_MIN_OVERLAP:
                link(d.id, u.id, DICTATION_SENT)
    return dict(links)
