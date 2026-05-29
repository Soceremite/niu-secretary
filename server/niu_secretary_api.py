#!/usr/bin/env python3
"""HTTP server for the Niu Secretary unified Action Protocol."""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.actions import ActionError, execute_action  # noqa: E402
from server.assistant import handle_message  # noqa: E402
from server.capabilities import capabilities_response  # noqa: E402


MAX_JSON_BYTES = 1024 * 1024


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
        if path == "/api/capabilities":
            return self.send_json(200, capabilities_response())
        return self.send_error_json(404, "not_found", "未知接口。")

    def do_POST(self):
        path = normalize_path(self.path)
        try:
            payload = self.read_json()
        except ValueError as exc:
            return self.send_error_json(400, "invalid_request", str(exc))

        if path == "/api/actions/execute":
            action_name = str(payload.get("action") or "")
            action_input = payload.get("input") or {}
            context = payload.get("context") or {}
            try:
                return self.send_json(200, execute_action(action_name, action_input, context))
            except ActionError as exc:
                return self.send_json(exc.status, exc.to_payload())

        if path == "/api/assistant/message":
            text = str(payload.get("text") or "")
            context = payload.get("context") or {}
            return self.send_json(200, handle_message(text, context))

        return self.send_error_json(404, "not_found", "未知接口。")

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

    def log_message(self, fmt, *args):
        print(f"[niu-secretary-api] {self.address_string()} {fmt % args}", flush=True)


def normalize_path(raw_path: str) -> str:
    path = urlparse(raw_path).path.rstrip("/") or "/"
    if path.startswith("/niu-secretary/api"):
        return "/api" + path[len("/niu-secretary/api") :]
    return path


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
