"""Model call audit helpers.

The platform-specific provider logic still lives in `server.assistant`; this
module gives other pipelines a stable place to record LLM usage summaries.
"""

from __future__ import annotations

from niu_core import audit


def record_call(
    module: str,
    purpose: str,
    model: str,
    input_summary: str,
    output_summary: str,
    status: str,
    latency_ms: int = 0,
) -> dict:
    return audit.record_model_call(
        module,
        purpose,
        model,
        input_summary[:500],
        output_summary[:500],
        status,
        latency_ms,
    )
