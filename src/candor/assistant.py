"""Text and voice assistant over the memory and the action planner.

Every command goes through the same dry-run planner the action eval scores. Then:
- memory.ask      -> answered from memory, with source ids
- clarify         -> the question goes back to the user
- confirm         -> nothing happens without an explicit "yes"; even then the destructive part is
                     only recorded, because no destructive action exists in the action set
- anything else   -> shown as a plan; executed only in execute mode and only after a "yes"

Executing writes to a local sandbox (outbox/<type>.jsonl), never to real Slack, Gmail or Calendar.
Every decision, executed or not, is appended to outbox/audit.jsonl.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from candor import config

OUTBOX = config.ROOT / "outbox"
YES = {"y", "yes", "yeah", "yep", "sure", "ok", "okay", "do it", "go ahead", "confirm"}


def describe(action: dict, names: dict[str, str] | None = None) -> str:
    """One plain sentence per action, for the screen and for speech. `names` maps ids to people/channels."""
    t, a = action["type"], action["args"]
    names = names or {}
    if t == "slack.send_message":
        who = f"{names[a['to']]} ({a['to']})" if a["to"] in names else a["to"]
        return f"Send a Slack message to {who}: \"{a.get('text', '')}\""
    if t == "gmail.send":
        cc = f", cc {', '.join(a['cc'])}" if a.get("cc") else ""
        return f"Email {', '.join(a['to'])}{cc}, subject \"{a.get('subject', '')}\": \"{a.get('body', '')}\""
    if t == "calendar.create_event":
        return f"Create \"{a.get('title', '')}\" from {a['start']} to {a['end']} with {', '.join(a.get('attendees', [])) or 'no one else'}"
    if t == "calendar.update_event":
        changes = ", ".join(f"{k} {v}" for k, v in a.items() if k != "event_id")
        return f"Change {a['event_id']}: {changes}"
    if t == "reminder.create":
        return f"Remind you at {a['due']}: \"{a.get('text', '')}\""
    if t == "app.open":
        return f"Open {a.get('app', '')}"
    if t == "memory.ask":
        return f"Look up: {a.get('question', '')}"
    if t == "clarify":
        return a.get("question", "Can you say more?")
    if t == "confirm":
        summary = a.get("summary", "This cannot be undone.").rstrip()
        return f"{summary}{'' if summary.endswith(('.', '?', '!')) else '.'} Are you sure?"
    return json.dumps(action)


@dataclass
class Reply:
    text: str                                        # what to show / say
    actions: list[dict] = field(default_factory=list)
    needs_yes: bool = False                          # waiting for a confirmation
    sources: list[str] = field(default_factory=list)


class Assistant:
    def __init__(self, candor, execute: bool = False, outbox: Path = OUTBOX):
        self.candor, self.execute, self.outbox = candor, execute, outbox
        self.pending: tuple[str, list[dict]] | None = None   # (command, actions) awaiting a yes
        self.names = {p.slack_id: p.name for p in candor.people if p.slack_id}
        self.names.update({c["id"]: f"#{c['name']}" for c in candor.corpus.channels if not c.get("is_dm")})

    def say(self, action: dict) -> str:
        return describe(action, self.names)

    def _audit(self, command: str, action: dict, decision: str) -> None:
        self.outbox.mkdir(parents=True, exist_ok=True)
        entry = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "command": command,
                 "action": action, "decision": decision}
        with open(self.outbox / "audit.jsonl", "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _run(self, command: str, actions: list[dict]) -> str:
        done = []
        for action in actions:
            if action["type"] == "confirm":
                self._audit(command, action, "confirmed; recorded only (no destructive action is available)")
                done.append("Noted. Nothing was deleted: destructive actions are recorded, not run.")
                continue
            if self.execute:
                self.outbox.mkdir(parents=True, exist_ok=True)
                with open(self.outbox / f"{action['type']}.jsonl", "a") as f:
                    f.write(json.dumps(action["args"], ensure_ascii=False) + "\n")
                self._audit(command, action, "executed in sandbox")
                done.append(f"Done (sandbox): {self.say(action)}")
            else:
                self._audit(command, action, "dry run")
                done.append(f"Dry run, not sent: {self.say(action)}")
        return "\n".join(done)

    def handle(self, text: str, as_of: datetime) -> Reply:
        text = text.strip()
        if self.pending:
            command, actions = self.pending
            self.pending = None
            if text.lower().rstrip(".!") in YES:
                return Reply(self._run(command, actions), actions)
            for action in actions:
                self._audit(command, action, "declined")
            if text.lower().rstrip(".!") in {"n", "no", "nope", "cancel", "stop", "don't"}:
                return Reply("Okay, I won't do that.")
            # Anything else is a new command.
        actions = self.candor.act(text, as_of)
        asks = [a for a in actions if a["type"] == "memory.ask"]
        if asks and len(asks) == len(actions):
            answers = [self.candor.ask(a["args"]["question"], as_of) for a in asks]
            return Reply(" ".join(r["answer"] for r in answers), actions, sources=[s for r in answers for s in r["sources"]])
        if any(a["type"] == "clarify" for a in actions):
            return Reply(" ".join(self.say(a) for a in actions if a["type"] == "clarify"), actions)
        self.pending = (text, actions)
        plan = "\n".join(self.say(a) for a in actions)
        if any(a["type"] == "confirm" for a in actions):
            return Reply(plan, actions, needs_yes=True)
        return Reply(f"{plan}\n{'Do it?' if self.execute else 'Run this as a dry run?'}", actions, needs_yes=True)
