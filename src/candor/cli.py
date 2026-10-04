"""Command-line entrypoints. The Makefile wraps these; the hidden test calls `make run`."""
import argparse
import json
import sys
import time
from datetime import datetime

from candor.io import read_jsonl, write_jsonl
from candor.llm import LLMError, LLMUnavailable
from candor.pipeline import Candor


def cmd_run(args: argparse.Namespace) -> None:
    questions = read_jsonl(args.questions)
    started = time.time()
    candor = Candor()
    rows = []
    for q in questions:
        result = candor.ask(q["question"], datetime.fromisoformat(q["as_of"]))
        rows.append({"id": q["id"], "answer": result["answer"], "sources": result["sources"],
                     "retrieved": result["retrieved"], "abstained": result["abstained"]})
    write_jsonl(args.out, rows)
    print(f"wrote {len(rows)} answers to {args.out} in {time.time() - started:.0f}s; {candor.report()}",
          file=sys.stderr)


def cmd_act(args: argparse.Namespace) -> None:
    commands = read_jsonl(args.commands)
    started = time.time()
    candor = Candor()
    rows = [{"id": c["id"], "actions": candor.act(c["command"], datetime.fromisoformat(c["as_of"]))} for c in commands]
    write_jsonl(args.out, rows)
    print(f"wrote {len(rows)} action plans to {args.out} in {time.time() - started:.0f}s; {candor.report()}",
          file=sys.stderr)


def cmd_do(args: argparse.Namespace) -> None:
    candor = Candor()
    for action in candor.act(args.command, datetime.fromisoformat(args.as_of)):
        print(json.dumps(action, ensure_ascii=False))


def cmd_assistant(args: argparse.Namespace) -> None:
    """Text or push-to-talk voice assistant. Dry run unless --execute (sandbox outbox, never real services)."""
    from candor.assistant import Assistant
    candor = Candor()
    bot = Assistant(candor, execute=args.execute)
    as_of = datetime.fromisoformat(args.as_of) if args.as_of else candor.data_end
    mode = "execute (sandbox outbox/)" if args.execute else "dry run"
    print(f"Candor assistant for {candor.corpus.owner}. Now = {as_of.isoformat()}. Mode: {mode}. Ctrl-D to quit.")
    device = None
    if args.voice:
        from candor import voice
        device, name = voice.microphone()
        words = voice.vocabulary([p.name for p in candor.people] + [c["name"] for c in candor.corpus.channels
                                                                      if not c.get("is_dm")] + [candor.corpus.owner])
        print(f"Microphone: {name}")
    while True:
        try:
            if args.voice:
                input("\nPress Enter and speak ")
                text = voice.listen(device, words)
                print(f"you> {text}")
            else:
                text = input("\nyou> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text.strip():
            continue
        try:
            reply = bot.handle(text, as_of)
        except LLMError as e:   # quota, key or a bad model reply: say so and keep the session alive
            print(f"candor> I can't reach the language model right now: {e}")
            continue
        print(f"candor> {reply.text}")
        if reply.sources:
            print(f"        sources: {', '.join(reply.sources)}")
        if args.voice:
            voice.speak(reply.text)


def cmd_ask(args: argparse.Namespace) -> None:
    candor = Candor()
    result = candor.ask(args.question, datetime.fromisoformat(args.as_of) if args.as_of else candor.data_end)
    print(result["answer"])
    print("sources:", ", ".join(result["sources"]) or "none")
    print("retrieved:", ", ".join(result["retrieved"][:10]))


def main() -> None:
    p = argparse.ArgumentParser(prog="candor")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="answer a JSONL file of memory questions")
    run.add_argument("--questions", required=True)
    run.add_argument("--out", required=True)
    run.set_defaults(func=cmd_run)

    ask = sub.add_parser("ask", help="answer one question")
    ask.add_argument("question")
    ask.add_argument("--as-of", help="ISO 8601 with offset, e.g. 2026-09-18T18:00:00-07:00; default: end of the data")
    ask.set_defaults(func=cmd_ask)

    act = sub.add_parser("act", help="dry-run a JSONL file of commands into actions")
    act.add_argument("--commands", required=True)
    act.add_argument("--out", required=True)
    act.set_defaults(func=cmd_act)

    do = sub.add_parser("do", help="dry-run one command")
    do.add_argument("command")
    do.add_argument("--as-of", required=True, help="ISO 8601 with offset, e.g. 2026-09-18T09:00:00-07:00")
    do.set_defaults(func=cmd_do)

    assistant = sub.add_parser("assistant", help="interactive assistant (text, or --voice for push-to-talk)")
    assistant.add_argument("--voice", action="store_true", help="speak and listen (macOS: ffmpeg mic + say)")
    assistant.add_argument("--execute", action="store_true", help="run confirmed actions into the sandbox outbox/")
    assistant.add_argument("--as-of", help="the current moment; default: end of the data")
    assistant.set_defaults(func=cmd_assistant)

    args = p.parse_args()
    try:
        args.func(args)
    except LLMError as e:   # missing key, exhausted quota, unusable reply: one clear line, not a traceback
        print(f"candor: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
