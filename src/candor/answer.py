"""Answer writer: question + ranked evidence -> short grounded answer with cited ids, or "I don't know"."""
from datetime import datetime

from candor import config
from candor.ingest import ASSISTANT, BOT, UNIDENTIFIED, Unit
from candor.llm import LLM

PROMPT_VERSION = "answer.v2"
MAX_CHARS = {"codex": 2500}
DEFAULT_MAX_CHARS = 1200


def _speaker(u: Unit) -> str:
    if u.author_kind == UNIDENTIFIED:
        return f"unidentified speaker ({u.meta.get('speaker_label')})"
    role = {ASSISTANT: " (AI assistant)", BOT: " (bot)"}.get(u.author_kind, "")
    return f"{u.speaker}{role}"


def format_record(u: Unit, limit: int | None = None) -> str:
    text = u.text
    limit = limit or MAX_CHARS.get(u.source, DEFAULT_MAX_CHARS)
    if len(text) > limit:
        text = text[:limit] + " [...]"
    m, extra = u.meta, ""
    if u.source == "gmail":
        extra = f" | from {m['from']} to {', '.join(m['to'])}{' cc ' + ', '.join(m['cc']) if m['cc'] else ''}"
    elif u.source == "calendar":
        extra = (f" | {m['summary']} | {m['start']} to {m['end']} | status {m['status']} | "
                 f"attendees {', '.join(a['email'] + ':' + a.get('responseStatus', '') for a in m['attendees'])}"
                 f"{' | repeats ' + str(m['recurrence']) if m.get('recurrence') else ''}")
    elif u.source == "dictation":
        extra = f" | delivery state: {m['delivery_state']}"
    edited = " (edited)" if m.get("edited") else ""
    when = u.time.strftime("%a %b %d %Y %H:%M")
    return f"[{u.id}] {when} | {u.context}{extra} | {_speaker(u)}{edited}: {text}"


def write_answer(llm: LLM, owner: str, question: str, as_of: datetime, evidence: list[Unit]) -> dict:
    template = (config.PROMPTS / f"{PROMPT_VERSION}.md").read_text()
    prompt = template.format(owner=owner, as_of=as_of.isoformat(), as_of_weekday=as_of.strftime("%A"),
                             question=question, records="\n".join(format_record(u) for u in evidence) or "(none)")
    system = "You are a careful assistant that replies with a single JSON object."
    out = llm.complete_json(system, prompt)
    allowed = {u.id for u in evidence}
    sources = [s for s in out.get("sources") or [] if s in allowed]
    answer = str(out.get("answer") or "").strip()
    abstained = bool(out.get("abstained")) or answer.lower().startswith("i don't know")
    if abstained:
        sources = []
    return {"answer": answer or "I don't know.", "sources": sources, "abstained": abstained}
