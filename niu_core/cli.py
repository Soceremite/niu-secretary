"""Common CLI dispatch and auditing for Niu Secretary modules."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from collections.abc import Callable

from niu_core import audit, db


CommandHandler = Callable[[argparse.Namespace], dict]


class CliCommand:
    def __init__(self, module: str, command: str, handler: CommandHandler):
        self.module = module
        self.command = command
        self.handler = handler


def run_command(module: str, command: str, args: argparse.Namespace, handler: CommandHandler) -> int:
    db.migrate()
    input_payload = {
        key: value
        for key, value in vars(args).items()
        if key not in {"handler", "module", "command"} and _json_safe(value)
    }
    run = audit.start_module_run(module, command, "cli", input_payload)
    try:
        result = handler(args)
        audit.finish_module_run(run["id"], "passed", result)
        print(json.dumps({"ok": True, "auditId": run["id"], "result": result}, ensure_ascii=False, indent=2))
        return 0
    except SystemExit as exc:
        code = int(exc.code or 0)
        status = "passed" if code == 0 else "failed"
        audit.finish_module_run(run["id"], status, {"exitCode": code}, "" if code == 0 else "system_exit")
        return code
    except Exception as exc:
        audit.finish_module_run(run["id"], "failed", {}, str(exc))
        print(
            json.dumps(
                {
                    "ok": False,
                    "auditId": run["id"],
                    "error": type(exc).__name__,
                    "message": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        if getattr(args, "debug", False):
            traceback.print_exc()
        return 1


def _json_safe(value) -> bool:
    try:
        json.dumps(value)
        return True
    except TypeError:
        return False

