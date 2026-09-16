"""Command-line entry: python -m niu_core.llm_client doctor|report [logic_name]"""
from __future__ import annotations

import argparse
import json
import sys

from .client import NiuLLM
from .errors import LLMError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m niu_core.llm_client")
    sub = parser.add_subparsers(dest="cmd", required=True)

    doctor = sub.add_parser("doctor", help="probe endpoints / try a logic model")
    doctor.add_argument("logic", nargs="?", default=None,
                        help="optionally send a tiny live chat to this logic model")

    report = sub.add_parser("report", help="show LLM call-log summary (usage / failure rate)")
    report.add_argument("--days", type=int, default=7)
    report.add_argument("--limit", type=int, default=20)

    args = parser.parse_args(argv)

    if args.cmd == "report":
        from . import call_log

        print(call_log.report(days=args.days, limit=args.limit))
        return 0

    try:
        llm = NiuLLM.load()
    except LLMError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2

    if args.cmd == "doctor":
        report = llm.doctor()
        print(f"{'endpoint':<14} {'status':<10} detail")
        for name, row in report.items():
            print(f"{name:<14} {row['status']:<10} {row['detail'][:80]}")

        if args.logic:
            logic = args.logic
            print(f"\n-- live probe: logic model '{logic}' --")
            try:
                rsp = llm.chat(logic, [{"role": "user", "content": "回复: pong"}])
                print(f"OK  model={rsp.model} endpoint={rsp.endpoint} reply={rsp.text[:60]!r}")
            except LLMError as exc:
                print(f"FAIL {exc}", file=sys.stderr)
                return 1
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
