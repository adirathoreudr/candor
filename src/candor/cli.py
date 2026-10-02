"""Command-line entrypoints. The Makefile wraps these; the hidden test calls `make run`."""
import argparse

from candor.io import read_jsonl, write_jsonl


def answer_question(q: dict) -> dict:
    # Abstain-everything floor. Replaced by the retrieval + answer pipeline in P2.
    return {"id": q["id"], "answer": "I don't know.", "sources": [], "retrieved": [], "abstained": True}


def cmd_run(args: argparse.Namespace) -> None:
    questions = read_jsonl(args.questions)
    write_jsonl(args.out, [answer_question(q) for q in questions])
    print(f"wrote {len(questions)} answers to {args.out}")


def main() -> None:
    p = argparse.ArgumentParser(prog="candor")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="answer a JSONL file of memory questions")
    run.add_argument("--questions", required=True)
    run.add_argument("--out", required=True)
    run.set_defaults(func=cmd_run)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
