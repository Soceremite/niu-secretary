#!/usr/bin/env python3
"""HTTP server for the Niu Secretary unified Action Protocol."""

from __future__ import annotations

import json
import os
import base64
import hashlib
import hmac
import sys
import time
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.actions import ActionError, execute_action  # noqa: E402
from server.assistant import handle_message  # noqa: E402
from server.capabilities import capabilities_response  # noqa: E402


MAX_JSON_BYTES = 1024 * 1024
ADMIN_SESSION_TTL_SECONDS = 12 * 60 * 60

ADMIN_READ_ROUTES = {
    "platform.ops": ("platform.ops.center", {"limit": 30}),
    "news.recommend": ("news.recommend", {"limit": 20}),
    "fitness.nutrition": ("fitness.nutrition.list", {"limit": 100}),
    "fitness.workouts": ("fitness.workout.list", {"limit": 100}),
    "fitness.metrics": ("fitness.body_metric.list", {"limit": 100}),
    "fitness.assessments": ("fitness.assessment.list", {"limit": 100}),
    "schedule.events": ("schedule.event.list", {"limit": 100}),
    "schedule.todos": ("schedule.todo.list", {"includeDone": True, "limit": 100}),
    "leisure.items": ("leisure.items.list", {"limit": 100}),
    "leisure.recommendations": ("leisure.recommendations.list", {"limit": 100}),
    "airesearch.overview": ("airesearch.overview", {"limit": 20}),
    "airesearch.papers": ("airesearch.paper.search", {"q": "q", "limit": 20}),
    "airesearch.admin.state": ("airesearch.admin.state", {}),
    "airesearch.admin.paper": ("airesearch.admin.paper_detail", {"paperKey": ""}),
    "airesearch.admin.paper.blog.detail": (
        "airesearch.admin.paper.blog.detail",
        {"paperKey": ""},
    ),
    "airesearch.admin.paper.layout.detail": (
        "airesearch.admin.paper.layout.detail",
        {"paperKey": ""},
    ),
}


class NiuSecretaryApiHandler(BaseHTTPRequestHandler):
    server_version = "NiuSecretaryApi/2.0"

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        path = normalize_path(self.path)
        if path == "/api/health":
            return self.send_json(200, {"ok": True, "service": "niu-secretary-api", "version": "2.0"})
        if path == "/api/admin/session":
            return self.send_json(200, {"ok": True, "authenticated": bool(self.get_admin_identity())})
        if path == "/api/admin/data":
            identity = self.require_admin()
            if not identity:
                return
            return self.handle_admin_data()
        if path == "/api/capabilities":
            return self.send_json(200, capabilities_response())
        route = get_action_route(self.path)
        if route:
            action_name, action_input = route
            try:
                return self.send_json(
                    200,
                    execute_action(
                        action_name,
                        action_input,
                        {"client": "web", "source": "web", "readOnly": True},
                    ),
                )
            except ActionError as exc:
                return self.send_json(exc.status, exc.to_payload())
        return self.send_error_json(404, "not_found", "未知接口。")

    def do_POST(self):
        path = normalize_path(self.path)
        try:
            payload = self.read_json()
        except ValueError as exc:
            return self.send_error_json(400, "invalid_request", str(exc))

        if path == "/api/admin/session":
            return self.handle_admin_login(payload)

        if path == "/api/admin/actions/execute":
            identity = self.require_admin()
            if not identity:
                return
            payload.setdefault("context", {})
            payload["context"].update({"client": "admin-console", "source": "admin-console", "confirmed": True, "admin": identity})
            return self.handle_action_execute(payload)

        if path == "/api/actions/execute":
            return self.handle_action_execute(payload)

        if path == "/api/assistant/message":
            text = str(payload.get("text") or "")
            context = payload.get("context") or {}
            return self.send_json(200, handle_message(text, context))

        return self.send_error_json(404, "not_found", "未知接口。")

    def handle_action_execute(self, payload: dict):
            action_name = str(payload.get("action") or "")
            action_input = payload.get("input") or {}
            context = payload.get("context") or {}
            context.setdefault("client", "web")
            if payload.get("source") and "source" not in context:
                context["source"] = payload.get("source")
            if payload.get("requestId") and "requestId" not in context:
                context["requestId"] = payload.get("requestId")
            try:
                return self.send_json(200, execute_action(action_name, action_input, context))
            except ActionError as exc:
                return self.send_json(exc.status, exc.to_payload())

    def handle_admin_login(self, payload: dict):
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        expected_user = os.environ.get("NIU_SECRETARY_ADMIN_USER", "admin")
        expected_password = os.environ.get("NIU_SECRETARY_ADMIN_PASSWORD", "")
        expected_hash = os.environ.get("NIU_SECRETARY_ADMIN_PASSWORD_SHA256", "")
        if not expected_password and not expected_hash:
            return self.send_error_json(503, "admin_auth_unconfigured", "管理台登录密码未配置。")
        password_ok = False
        if expected_password:
            password_ok = hmac.compare_digest(password, expected_password)
        if expected_hash:
            digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
            password_ok = password_ok or hmac.compare_digest(digest, expected_hash)
        if username != expected_user or not password_ok:
            return self.send_error_json(401, "invalid_credentials", "用户名或密码错误。")
        return self.send_json(200, {"ok": True, "token": sign_admin_token(username), "expiresIn": ADMIN_SESSION_TTL_SECONDS})

    def handle_admin_data(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        resource = _first_query_value(query, "resource")
        route = ADMIN_READ_ROUTES.get(resource)
        if not route:
            return self.send_error_json(404, "not_found", "未知管理台资源。")
        action_name, defaults = route
        payload = dict(defaults)
        for key in ("from", "to", "q", "category", "paperKey", "profile", "status"):
            value = _first_query_value(query, key)
            if value:
                payload[key] = value
        limit = _first_query_value(query, "limit")
        if limit.isdigit():
            payload["limit"] = int(limit)
        try:
            return self.send_json(
                200,
                execute_action(action_name, payload, {"client": "admin-console", "source": "admin-console", "readOnly": True}),
            )
        except ActionError as exc:
            return self.send_json(exc.status, exc.to_payload())

    def read_json(self) -> dict:
        content_type = self.headers.get("content-type", "")
        if "application/json" not in content_type:
            raise ValueError("请使用 application/json 请求。")
        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError as exc:
            raise ValueError("Content-Length 无效。") from exc
        if length > MAX_JSON_BYTES:
            raise ValueError("请求体超过 1MB。")
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("JSON 格式无效。") from exc
        if not isinstance(data, dict):
            raise ValueError("JSON 顶层必须是对象。")
        return data

    def send_error_json(self, status: int, error: str, message: str):
        return self.send_json(status, {"ok": False, "error": error, "message": message})

    def send_json(self, status: int, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def require_admin(self) -> str:
        identity = self.get_admin_identity()
        if identity:
            return identity
        self.send_error_json(401, "admin_auth_required", "请先登录管理台。")
        return ""

    def get_admin_identity(self) -> str:
        header = self.headers.get("authorization", "")
        if not header.lower().startswith("bearer "):
            return ""
        return verify_admin_token(header.split(" ", 1)[1].strip())

    def log_message(self, fmt, *args):
        print(f"[niu-secretary-api] {self.address_string()} {fmt % args}", flush=True)


def normalize_path(raw_path: str) -> str:
    path = urlparse(raw_path).path.rstrip("/") or "/"
    if path.startswith("/niu-secretary/api"):
        return "/api" + path[len("/niu-secretary/api") :]
    return path


def sign_admin_token(username: str) -> str:
    expires_at = int(time.time()) + ADMIN_SESSION_TTL_SECONDS
    payload = f"{username}:{expires_at}"
    signature = hmac.new(admin_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{signature}".encode("utf-8")).decode("ascii")


def verify_admin_token(token: str) -> str:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        username, expires_at_text, signature = raw.rsplit(":", 2)
        expires_at = int(expires_at_text)
    except Exception:
        return ""
    if expires_at < int(time.time()):
        return ""
    payload = f"{username}:{expires_at}"
    expected = hmac.new(admin_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return username if hmac.compare_digest(signature, expected) else ""


def admin_secret() -> bytes:
    value = os.environ.get("NIU_SECRETARY_ADMIN_SESSION_SECRET") or os.environ.get("NIU_SECRETARY_ADMIN_PASSWORD") or "niu-secretary-dev-admin-secret"
    return value.encode("utf-8")


def get_action_route(raw_path: str) -> tuple[str, dict] | None:
    """Map read-only HTTP GET routes to audited Action Protocol calls."""
    path = normalize_path(raw_path)
    query = parse_qs(urlparse(raw_path).query)
    routes = {
        "/api/platform/runs": ("platform.runs.list", {"module": "module", "limit": "limit"}),
        "/api/platform/ops": (
            "platform.ops.center",
            {"module": "module", "status": "status", "requiresReview": "requiresReview", "limit": "limit"},
        ),
        "/api/platform/events": (
            "platform.events.list",
            {"module": "module", "eventType": "eventType", "requiresReview": "requiresReview", "limit": "limit"},
        ),
        "/api/platform/today": ("platform.today.context", {"date": "date", "limit": "limit"}),
        "/api/platform/modules": ("platform.modules.status", {"limit": "limit"}),
        "/api/platform/cron": ("platform.cron.registry", {}),
        "/api/profile": ("profile.get", {"module": "module"}),
        "/api/profile/changes": ("profile.changes", {"module": "module", "limit": "limit"}),
        "/api/news/search": (
            "news.search",
            {
                "q": "q",
                "date": "date",
                "from": "from",
                "to": "to",
                "section": "section",
                "tag": "tag",
                "source": "source",
                "limit": "limit",
            },
        ),
        "/api/news/recommend": ("news.recommend", {"limit": "limit"}),
        "/api/fitness/summary/today": ("fitness.summary.today", {"date": "date"}),
        "/api/fitness/summary/weekly": ("fitness.summary.weekly", {"date": "date"}),
        "/api/fitness/nutrition": (
            "fitness.nutrition.list",
            {"from": "from", "to": "to", "limit": "limit"},
        ),
        "/api/fitness/workouts": (
            "fitness.workout.list",
            {"from": "from", "to": "to", "limit": "limit"},
        ),
        "/api/fitness/body-metrics": (
            "fitness.body_metric.list",
            {"from": "from", "to": "to", "limit": "limit"},
        ),
        "/api/fitness/recovery": (
            "fitness.recovery.list",
            {"from": "from", "to": "to", "limit": "limit"},
        ),
        "/api/fitness/assessments": (
            "fitness.assessment.list",
            {"from": "from", "to": "to", "limit": "limit"},
        ),
        "/api/fitness/consults": (
            "fitness.consult.list",
            {"from": "from", "to": "to", "limit": "limit"},
        ),
        "/api/fitness/daily-summary": ("fitness.daily_summary.get", {"date": "date"}),
        "/api/fitness/recommendations": (
            "fitness.recommendations.list",
            {"date": "date", "type": "type", "limit": "limit"},
        ),
        "/api/schedule/summary/today": ("schedule.today_summary", {"date": "date"}),
        "/api/schedule/events": (
            "schedule.event.list",
            {"from": "from", "to": "to", "limit": "limit"},
        ),
        "/api/schedule/todos": (
            "schedule.todo.list",
            {"from": "from", "to": "to", "includeDone": "includeDone", "limit": "limit"},
        ),
        "/api/schedule/important-dates": ("schedule.important_date.list", {"limit": "limit"}),
        "/api/schedule/goals": ("schedule.goal.list", {"limit": "limit"}),
        "/api/schedule/day-plan": ("schedule.day_plan.get", {"date": "date"}),
        "/api/schedule/day-review": ("schedule.day_review.get", {"date": "date"}),
        "/api/schedule/conflicts": ("schedule.conflicts.detect", {"date": "date"}),
        "/api/schedule/recommend": ("schedule.recommend", {"date": "date"}),
        "/api/schedule/task-history": (
            "schedule.task_history.list",
            {"todoId": "todoId", "id": "id", "limit": "limit"},
        ),
        "/api/leisure/recommend": (
            "leisure.recommend",
            {"limit": "limit", "availableMinutes": "availableMinutes", "scheduleLoad": "scheduleLoad", "mood": "mood"},
        ),
        "/api/leisure/recommendations": (
            "leisure.recommendations.list",
            {"date": "date", "limit": "limit"},
        ),
        "/api/leisure/items": (
            "leisure.items.list",
            {"category": "category", "limit": "limit"},
        ),
        "/api/leisure/history": (
            "leisure.history.search",
            {"q": "q", "category": "category", "itemId": "itemId", "limit": "limit"},
        ),
        "/api/leisure/profile/suggestions": (
            "leisure.profile.suggestions",
            {"limit": "limit"},
        ),
        "/api/airesearch/overview": ("airesearch.overview", {"limit": "limit"}),
        "/api/airesearch/papers/search": ("airesearch.paper.search", {"q": "q", "limit": "limit"}),
    }
    route = routes.get(path)
    if not route:
        return None
    action_name, fields = route
    payload = {}
    for payload_key, query_key in fields.items():
        value = _first_query_value(query, query_key)
        if value != "":
            if payload_key in _INTEGER_QUERY_FIELDS and value.isdigit():
                payload[payload_key] = int(value)
            elif payload_key in _BOOLEAN_QUERY_FIELDS:
                payload[payload_key] = value.lower() in {"1", "true", "yes", "on"}
            else:
                payload[payload_key] = value
    if action_name == "platform.today.context" and "date" not in payload:
        payload["date"] = date.today().isoformat()
    return action_name, payload


def _first_query_value(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or []
    return str(values[0]).strip() if values else ""


_INTEGER_QUERY_FIELDS = {"limit", "availableMinutes", "scheduleLoad"}
_BOOLEAN_QUERY_FIELDS = {"includeDone", "requiresReview"}


def main():
    port = int(os.environ.get("NIU_SECRETARY_API_PORT", "5188"))
    server = ThreadingHTTPServer(("127.0.0.1", port), NiuSecretaryApiHandler)
    print(f"[niu-secretary-api] listening on http://127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
