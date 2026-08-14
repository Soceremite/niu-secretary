"""Small audited pipeline runner for module lifecycle steps."""

from __future__ import annotations

from collections.abc import Callable

from niu_core import audit


PipelineStep = Callable[[dict], dict]


class Pipeline:
    """Run named deterministic steps with module_runs/module_events audit records."""

    def __init__(self, module: str, run_type: str, source: str = "cli"):
        self.module = module
        self.run_type = run_type
        self.source = source
        self._steps: list[tuple[str, PipelineStep]] = []

    def step(self, name: str, handler: PipelineStep) -> "Pipeline":
        self._steps.append((name, handler))
        return self

    def run(self, initial: dict | None = None) -> dict:
        payload = dict(initial or {})
        run = audit.start_module_run(self.module, self.run_type, self.source, payload)
        completed: list[str] = []
        try:
            for name, handler in self._steps:
                payload = handler(payload)
                completed.append(name)
                audit.record_module_event(
                    self.module,
                    "pipeline_step",
                    f"{self.run_type}.{name} passed",
                    {"step": name},
                    self.source,
                )
            output = {"status": "passed", "steps": completed, "payload": payload}
            audit.finish_module_run(run["id"], "passed", output)
            output["auditId"] = run["id"]
            return output
        except Exception as exc:
            audit.finish_module_run(run["id"], "failed", {"steps": completed}, str(exc))
            raise
