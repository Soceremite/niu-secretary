"""Cron entrypoint for Niu Secretary module jobs.

This module intentionally shells out to the public CLI. Cron should not bypass
module validation or invent a second execution path.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from niu_core import cron


PROJECT_ROOT = Path(__file__).resolve().parents[1]


JOBS = {
    "news.run-daily": ("news", ["news", "run-daily"]),
    "fitness.summarize-day": ("fitness", ["fitness", "summarize-day", "--date", "today"]),
    "schedule.plan-day": ("schedule", ["schedule", "plan-day", "--date", "today"]),
    "schedule.rollover-todos": ("schedule", ["schedule", "rollover-todos"]),
    "leisure.recommend-daily": ("leisure", ["leisure", "recommend-daily"]),
    "airesearch.refresh-weekly": ("airesearch", ["airesearch", "refresh-weekly"]),
    "platform.run-daily": ("platform", ["platform", "run-daily"]),
}

JOB_GROUPS = {
    "daily": [
        "news.run-daily",
        "fitness.summarize-day",
        "schedule.rollover-todos",
        "schedule.plan-day",
        "leisure.recommend-daily",
        "platform.run-daily",
    ],
    "weekly": ["airesearch.refresh-weekly"],
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="niu_secretary.cron")
    parser.add_argument(
        "target",
        choices=sorted(set(JOBS) | set(JOB_GROUPS) | {"list"}),
        help="Job or group to run.",
    )
    parser.add_argument("--keep-going", action="store_true", help="Continue a group after a failed job.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.target == "list":
        print(json.dumps(cron_registry(), ensure_ascii=False, indent=2))
        return 0
    targets = JOB_GROUPS.get(args.target, [args.target])
    results = []
    for job_name in targets:
        try:
            results.append(run_named_job(job_name))
        except Exception as exc:
            results.append({"ok": False, "job": job_name, "error": str(exc)})
            if not args.keep_going:
                print(json.dumps({"ok": False, "target": args.target, "results": results}, ensure_ascii=False, indent=2))
                return 1
    ok = all(item.get("ok") for item in results)
    print(json.dumps({"ok": ok, "target": args.target, "results": results}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def run_named_job(job_name: str) -> dict:
    module, cli_args = JOBS[job_name]
    return cron.run_job(module, job_name, lambda: _run_cli(cli_args)) | {"job": job_name}


def cron_registry() -> dict:
    return {
        "ok": True,
        "jobs": {
            name: {"module": module, "cliArgs": cli_args}
            for name, (module, cli_args) in sorted(JOBS.items())
        },
        "groups": {name: list(jobs) for name, jobs in sorted(JOB_GROUPS.items())},
    }


def _run_cli(cli_args: list[str]) -> dict:
    command = [sys.executable, "-m", "niu_secretary.cli", *cli_args]
    env = dict(os.environ)
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip() or f"CLI exited {completed.returncode}")
    return {
        "command": command[3:],
        "exitCode": completed.returncode,
        "stdout": (completed.stdout or "").strip()[-4000:],
        "stderr": (completed.stderr or "").strip()[-2000:],
    }


if __name__ == "__main__":
    raise SystemExit(main())
