"""Audit helpers for module runs, events, actions, and model calls."""

from __future__ import annotations

from server import store


def start_module_run(
    module: str,
    run_type: str,
    source: str,
    input_payload: dict | None = None,
    status: str = "running",
) -> dict:
    return store.start_module_run(module, run_type, source, input_payload, status)


def finish_module_run(
    run_id: str,
    status: str,
    output_payload: dict | None = None,
    error: str = "",
) -> dict:
    return store.finish_module_run(run_id, status, output_payload, error)


def record_module_event(
    module: str,
    event_type: str,
    title: str,
    payload: dict | None = None,
    source: str = "system",
    confidence: float = 1.0,
    requires_review: bool = False,
) -> dict:
    return store.record_module_event(
        module,
        event_type,
        title,
        payload,
        source,
        confidence,
        requires_review,
    )


def create_assistant_action(
    action: str,
    input_payload: dict | None = None,
    requires_confirmation: bool = False,
    source: str = "api",
    request_id: str = "",
    status: str = "running",
) -> dict:
    return store.create_assistant_action(
        action,
        input_payload,
        requires_confirmation,
        source,
        request_id,
        status,
    )


def finish_assistant_action(
    action_id: str,
    status: str,
    result: dict | None = None,
    error: str = "",
) -> dict:
    return store.finish_assistant_action(action_id, status, result, error)


def record_model_call(
    module: str,
    purpose: str,
    model: str,
    input_summary: str,
    output_summary: str,
    status: str,
    latency_ms: int = 0,
) -> dict:
    return store.record_model_call(
        module,
        purpose,
        model,
        input_summary,
        output_summary,
        status,
        latency_ms,
    )

