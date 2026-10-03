"""Command-line entrypoints. The Makefile wraps these; the hidden test calls `make run`."""
import argparse
import json
import sys
import time
from datetime import datetime

from candor.io import read_jsonl, write_jsonl
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
    print(f"wrote {len(rows)} answers to {args.out} in {time.time() - started:.0f}s; {candor.usage()}",
          file=sys.stderr)


def cmd_act(args: argparse.Namespace) -> None:
    commands = read_jsonl(args.commands)
    started = time.time()
    candor = Candor()
    rows = [{"id": c["id"], "actions": candor.act(c["command"], datetime.fromisoformat(c["as_of"]))} for c in commands]
    write_jsonl(args.out, rows)
    print(f"wrote {len(rows)} action plans to {args.out} in {time.time() - started:.0f}s; {candor.usage()}",
          file=sys.stderr)


def cmd_do(args: argparse.Namespace) -> None:
    candor = Candor()
    for action in candor.act(args.command, datetime.fromisoformat(args.as_of)):
        print(json.dumps(action, ensure_ascii=False))


def cmd_ask(args: argparse.Namespace) -> None:
    candor = Candor()
    result = candor.ask(args.question, datetime.fromisoformat(args.as_of))
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
    ask.add_argument("--as-of", required=True, help="ISO 8601 with offset, e.g. 2026-09-18T18:00:00-07:00")
    ask.set_defaults(func=cmd_ask)

    act = sub.add_parser("act", help="dry-run a JSONL file of commands into actions")
    act.add_argument("--commands", required=True)
    act.add_argument("--out", required=True)
    act.set_defaults(func=cmd_act)

    do = sub.add_parser("do", help="dry-run one command")
    do.add_argument("command")
    do.add_argument("--as-of", required=True, help="ISO 8601 with offset, e.g. 2026-09-18T09:00:00-07:00")
    do.set_defaults(func=cmd_do)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
