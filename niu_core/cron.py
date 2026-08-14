"""Cron-friendly wrappers around audited module work."""

from __future__ import annotations

from collections.abc import Callable

from niu_core import audit, db


CronJob = Callable[[], dict]


def run_job(module: str, job_name: str, handler: CronJob) -> dict:
    db.migrate()
    run = audit.start_module_run(module, job_name, "cron", {})
    try:
        result = handler()
        audit.finish_module_run(run["id"], "passed", result)
        return {"ok": True, "auditId": run["id"], "result": result}
    except Exception as exc:
        audit.finish_module_run(run["id"], "failed", {}, str(exc))
        raise
