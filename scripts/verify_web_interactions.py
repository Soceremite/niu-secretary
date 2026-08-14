#!/usr/bin/env python3
"""Verify Niu Secretary web/API interaction boundaries.

The script uses a temporary SQLite database for write tests so it does not
pollute production data. It also optionally loads deployed pages with headless
Chrome to catch broken static delivery.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5199)
    parser.add_argument("--static-base", default="http://124.222.22.171/niu-secretary")
    parser.add_argument("--skip-chrome", action="store_true")
    args = parser.parse_args()

    tmpdir = Path(tempfile.mkdtemp(prefix="niu-secretary-web-e2e-"))
    proc: subprocess.Popen[str] | None = None
    try:
      env = os.environ.copy()
      env["NIU_SECRETARY_DB_PATH"] = str(tmpdir / "niu-secretary.sqlite3")
      env["NIU_SECRETARY_API_PORT"] = str(args.port)
      proc = subprocess.Popen(
          [sys.executable, "-m", "server.niu_secretary_api"],
          cwd=Path(__file__).resolve().parents[1],
          env=env,
          stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT,
          text=True,
      )
      api_base = f"http://127.0.0.1:{args.port}/niu-secretary/api"
      wait_for_api(api_base)
      result = verify_api_interactions(api_base)
      chrome = None if args.skip_chrome else find_chrome()
      static = verify_static_pages(args.static_base, chrome) if chrome else {"chrome": "skipped"}
      print(json.dumps({"ok": True, "api": result, "static": static}, ensure_ascii=False))
      return 0
    finally:
      if proc and proc.poll() is None:
        proc.terminate()
        try:
          proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
          proc.kill()
      shutil.rmtree(tmpdir, ignore_errors=True)


def wait_for_api(api_base: str) -> None:
    deadline = time.time() + 10
    last_error: Exception | None = None
    while time.time() < deadline:
      try:
        request("GET", api_base, "/capabilities")
        return
      except Exception as exc:
        last_error = exc
        time.sleep(0.2)
    raise RuntimeError(f"API did not become ready: {last_error}")


def verify_api_interactions(api_base: str) -> dict:
    today = date.today().isoformat()
    stamp = f"web-e2e-{int(time.time())}"

    def action(name: str, input_: dict) -> dict:
      return request("POST", api_base, "/actions/execute", {
          "action": name,
          "input": input_,
          "context": {"client": "web-e2e", "confirmed": True},
      })

    action("fitness.nutrition.create", {"date": today, "food": f"{stamp} meal", "calories": 520, "proteinG": 42})
    action("fitness.workout.create", {"date": today, "name": f"{stamp} workout", "durationMin": 45, "intensity": "high"})
    action("fitness.body_metric.create", {"date": today, "weightKg": 72.4, "waistCm": 82, "note": stamp})
    action("fitness.recovery.create", {"date": today, "sleepHours": 7.5, "sleepQuality": 4, "stress": 2, "soreness": 3, "lastRpe": 8, "score": 78, "statusAdvice": stamp})
    action("schedule.event.create", {"date": today, "time": "09:30", "title": f"{stamp} event"})
    action("schedule.todo.create", {"date": today, "title": f"{stamp} todo", "priority": "high"})
    action("schedule.important_date.create", {"date": today, "title": f"{stamp} date"})
    action("schedule.goal.create", {"title": f"{stamp} goal", "cadence": "weekly", "streak": 1})
    action("schedule.day.plan", {"date": today})
    action("leisure.item.rate", {"itemId": stamp, "category": "movie", "title": f"{stamp} leisure", "rating": 5})
    request("POST", api_base, "/actions/execute", {"action": "news.recommend", "input": {"limit": 1}, "context": {"client": "web-e2e", "confirmed": True}})

    checks = [
      ("/fitness/nutrition", {"from": today, "to": today, "limit": 20}, "items", "food"),
      ("/fitness/workouts", {"from": today, "to": today, "limit": 20}, "items", "name"),
      ("/fitness/body-metrics", {"from": today, "to": today, "limit": 20}, "items", "note"),
      ("/fitness/recovery", {"from": today, "to": today, "limit": 20}, "items", "statusAdvice"),
      ("/schedule/events", {"from": today, "to": today, "limit": 20}, "items", "title"),
      ("/schedule/todos", {"includeDone": "true", "limit": 20}, "items", "title"),
      ("/schedule/important-dates", {"limit": 20}, "items", "title"),
      ("/schedule/goals", {"limit": 20}, "items", "title"),
      ("/leisure/history", {"q": stamp, "limit": 20}, "items", "title"),
    ]
    for path, params, key, field in checks:
      data = request("GET", api_base, path + "?" + urllib.parse.urlencode(params))
      rows = data.get(key) or []
      if not any(stamp in str(row.get(field, "")) for row in rows):
        raise AssertionError(f"{path} did not return {stamp} in {field}: {rows[:3]}")

    plan = request("GET", api_base, "/schedule/day-plan?" + urllib.parse.urlencode({"date": today}))
    if stamp not in json.dumps(plan.get("plan") or {}, ensure_ascii=False):
      raise AssertionError("schedule day plan did not include e2e rows")

    return {"date": today, "stamp": stamp}


def verify_static_pages(static_base: str, chrome: str) -> dict:
    pages = [
      "fitness/index.html",
      "schedule/index.html",
      "leisure/index.html",
      "news/index.html",
      "index.html",
    ]
    loaded = []
    for page in pages:
      url = f"{static_base.rstrip('/')}/{page}?web-e2e={int(time.time())}"
      body = fetch_text(url)
      if "404 Not Found" in body or "502 Bad Gateway" in body:
        raise AssertionError(f"static page failed: {url}")
      run_chrome_load(chrome, url)
      loaded.append(page)
    return {"chrome": chrome, "loaded": loaded}


def run_chrome_load(chrome: str, url: str) -> None:
    shot = tempfile.NamedTemporaryFile(prefix="niu-web-e2e-", suffix=".png", delete=False)
    shot.close()
    command = [
      chrome,
      "--headless",
      "--disable-gpu",
      "--disable-dev-shm-usage",
      "--no-sandbox",
      "--window-size=1280,900",
      f"--screenshot={shot.name}",
      url,
    ]
    proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
      _, stderr = proc.communicate(timeout=45)
    except subprocess.TimeoutExpired:
      proc.kill()
      proc.communicate()
      size = Path(shot.name).stat().st_size if Path(shot.name).exists() else 0
      Path(shot.name).unlink(missing_ok=True)
      if size > 0:
        return
      raise AssertionError(f"chrome timed out loading {url} screenshotBytes={size}")
    if proc.returncode != 0:
      Path(shot.name).unlink(missing_ok=True)
      raise AssertionError(f"chrome failed loading {url}: {stderr[-1000:] if stderr else proc.returncode}")
    size = Path(shot.name).stat().st_size if Path(shot.name).exists() else 0
    Path(shot.name).unlink(missing_ok=True)
    if size <= 0:
      raise AssertionError(f"chrome produced empty screenshot for {url}")


def find_chrome() -> str | None:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
      path = shutil.which(name)
      if path:
        return path
    return None


def request(method: str, api_base: str, path: str, payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
      data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
      headers["Content-Type"] = "application/json"
    req = urllib.request.Request(api_base + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
      parsed = json.loads(resp.read().decode("utf-8") or "{}")
    if parsed.get("ok") is False:
      raise AssertionError(f"{method} {path} failed: {parsed}")
    return parsed


def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as resp:
      return resp.read().decode("utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
