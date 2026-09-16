"""LLM 调用记录 —— 统一路由层的「记账」收口点（2026-09-16）。

为什么放在这里：`niu_core.llm_client` 是全部 LLM 调用的唯一收口点（服务、cron 管线、
CLI 都经它），所以在这里记一行就能覆盖所有调用，不必新起一个网关服务。

设计约束
--------
1. **绝不影响业务**：`record()` 吞掉一切异常。记账失败绝不能搞挂调用。
2. **只记元信息**：时间/调用方/逻辑路由/端点/真实模型/耗时/tokens/成功失败/错误摘要。
   **不记 prompt 与回复正文**（省空间，也不碰隐私）。
3. **多进程安全**：服务 + cron + CLI 并发写 SQLite → WAL + busy_timeout + timeout。
4. **可关闭/可重定向**：
   - `NIU_LLM_LOG=0|off|false|no` 关闭
   - `NIU_LLM_LOG_DB=<path>` 改落点（默认 `<repo>/data/llm_calls.sqlite3`）
   - `NIU_LLM_CALLER=<name>` 显式标注调用方（默认按进程名推断）

用法
----
调用方通常不需要直接用它（`NiuLLM.chat/embed` 已自动记账）。自建 HTTP 的客户端
（如 airesearch 的 fact/formula_ocr/blog）应在请求结束后调一次：

    from niu_core.llm_client import call_log
    call_log.record(logic_model="fact", status="ok", endpoint="opencode_go",
                    model="deepseek-v4.1-flash", latency_ms=2600,
                    prompt_chars=len(prompt), reply_chars=len(reply))

命令行查看：

    python -m niu_core.llm_client.call_log report [--days 7] [--limit 20]
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

__all__ = ["enabled", "db_path", "caller_name", "record", "track", "report", "recent"]

_DISABLED = {"0", "off", "false", "no", ""}

_SCHEMA = """
create table if not exists llm_calls (
    id            integer primary key autoincrement,
    ts            text    not null,               -- UTC ISO8601 秒精度
    caller        text    not null default '',    -- 进程/模块标识
    logic_model   text    not null default '',    -- 逻辑路由名（管理台里的那个名字）
    attempt       integer not null default 1,     -- 1=主选, 2+=备选第 N-1 个
    is_fallback   integer not null default 0,
    endpoint      text    not null default '',
    model         text    not null default '',    -- 真实模型名
    style         text    not null default '',
    status        text    not null default 'ok',  -- ok | error | skipped_no_key | skipped_cooldown
    error_type    text    not null default '',
    error_msg     text    not null default '',
    latency_ms    integer not null default 0,
    prompt_chars  integer not null default 0,
    reply_chars   integer not null default 0,
    input_tokens  integer,
    output_tokens integer
);
create index if not exists idx_llm_calls_ts        on llm_calls(ts);
create index if not exists idx_llm_calls_logic_ts  on llm_calls(logic_model, ts);
create index if not exists idx_llm_calls_status    on llm_calls(status);
"""


def enabled() -> bool:
    return os.environ.get("NIU_LLM_LOG", "1").strip().lower() not in _DISABLED


def db_path() -> Path:
    override = os.environ.get("NIU_LLM_LOG_DB", "").strip()
    if override:
        return Path(override).expanduser()
    # niu_core/llm_client/call_log.py → parents[2] == 仓库根
    return Path(__file__).resolve().parents[2] / "data" / "llm_calls.sqlite3"


def caller_name() -> str:
    """调用方标识：优先 NIU_LLM_CALLER，其次按 argv[0] 推断（脚本名/模块名）。"""
    explicit = os.environ.get("NIU_LLM_CALLER", "").strip()
    if explicit:
        return explicit[:60]
    argv0 = (sys.argv[0] if sys.argv else "") or ""
    name = Path(argv0).name
    if not name:
        return "unknown"
    return name[:60]


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5)
    conn.execute("pragma journal_mode=wal")
    conn.execute("pragma busy_timeout=4000")
    conn.executescript(_SCHEMA)
    return conn


def _host_of(value: str) -> str:
    """endpoint 归一：自建 HTTP 的调用方只知道 base_url，这里取 host 以与端点名同列可读。"""
    text = str(value or "").strip()
    if text.startswith(("http://", "https://")):
        return text.split("//", 1)[-1].split("/", 1)[0][:60]
    return text[:60]


def record(
    *,
    logic_model: str,
    status: str,
    endpoint: str = "",
    model: str = "",
    attempt: int = 1,
    is_fallback: bool = False,
    style: str = "",
    latency_ms: int = 0,
    prompt_chars: int = 0,
    reply_chars: int = 0,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    error: Optional[BaseException] = None,
    caller: Optional[str] = None,
) -> None:
    """记一条调用。**任何异常都被吞掉** —— 记账绝不能影响业务。"""
    if not enabled():
        return
    try:
        row = (
            datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            (caller or caller_name())[:60],
            str(logic_model)[:60],
            int(attempt),
            1 if is_fallback else 0,
            _host_of(endpoint),
            str(model)[:120],
            str(style)[:40],
            str(status)[:40],
            type(error).__name__[:60] if error else "",
            (str(error)[:300] if error else ""),
            int(latency_ms or 0),
            int(prompt_chars or 0),
            int(reply_chars or 0),
            None if input_tokens is None else int(input_tokens),
            None if output_tokens is None else int(output_tokens),
        )
        conn = _connect()
        try:
            conn.execute(
                "insert into llm_calls (ts, caller, logic_model, attempt, is_fallback, endpoint,"
                " model, style, status, error_type, error_msg, latency_ms, prompt_chars,"
                " reply_chars, input_tokens, output_tokens)"
                " values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                row,
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


class _TrackState:
    """track() 的可回填字段。"""

    def __init__(self) -> None:
        self.reply_chars: int = 0
        self.input_tokens: Optional[int] = None
        self.output_tokens: Optional[int] = None


@contextmanager
def track(
    logic_model: str,
    *,
    endpoint: str = "",
    model: str = "",
    attempt: int = 1,
    is_fallback: bool = False,
    style: str = "",
    prompt_chars: int = 0,
):
    """给「自建 HTTP」的调用方用：包住一次请求，自动记成功/失败/耗时。

        with call_log.track("fact", endpoint="opencode_go", model=m,
                            prompt_chars=len(prompt)) as st:
            reply = do_http(...)
            st.reply_chars = len(reply)                   # 可选回填
            st.input_tokens, st.output_tokens = 7, 3       # 可选回填
    """
    started = time.monotonic()
    state = _TrackState()
    try:
        yield state
    except BaseException as exc:
        record(logic_model=logic_model, status="error", endpoint=endpoint, model=model,
               attempt=attempt, is_fallback=is_fallback, style=style,
               latency_ms=int((time.monotonic() - started) * 1000),
               prompt_chars=prompt_chars, reply_chars=state.reply_chars,
               input_tokens=state.input_tokens, output_tokens=state.output_tokens, error=exc)
        raise
    record(logic_model=logic_model, status="ok", endpoint=endpoint, model=model,
           attempt=attempt, is_fallback=is_fallback, style=style,
           latency_ms=int((time.monotonic() - started) * 1000),
           prompt_chars=prompt_chars, reply_chars=state.reply_chars,
           input_tokens=state.input_tokens, output_tokens=state.output_tokens)


def _size_of(value: Any) -> int:
    """估算体量：字符串取长度；消息列表累加其中 text 部分（不记正文）。"""
    if isinstance(value, str):
        return len(value)
    if isinstance(value, (list, tuple)):
        total = 0
        for item in value:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, str):
                total += len(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        total += len(part["text"])
        return total
    return 0


def tracked(
    logic_model: str,
    *,
    model_param: str = "model",
    prompt_param: str = "prompt",
    endpoint_param: Optional[str] = None,
    fallback_model: str = "",
):
    """装饰器版 track()：自动从被调函数的关键字参数里取 model/prompt/endpoint。

    给「自建 HTTP 客户端」的单一入口用，避免手工埋点：

        @call_log.tracked("fact", endpoint_param="base_url")
        def complete_json(self, *, model, base_url, api_key, prompt): ...
    """
    import functools
    import inspect

    def decorator(func):
        signature = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                values = dict(signature.bind_partial(*args, **kwargs).arguments)
            except Exception:
                values = {}
            model = str(values.get(model_param) or fallback_model)[:120]
            prompt = values.get(prompt_param)
            prompt_chars = _size_of(prompt)
            endpoint = (str(values.get(endpoint_param) or "")[:60] if endpoint_param else "")
            with track(logic_model, endpoint=endpoint, model=model,
                       prompt_chars=prompt_chars) as state:
                result = func(*args, **kwargs)
                try:
                    state.reply_chars = (len(result) if isinstance(result, str)
                                         else len(str(result or "")))
                except Exception:
                    state.reply_chars = 0
                return result

        return wrapper

    return decorator


def recent(limit: int = 20) -> list[dict[str, Any]]:
    """最近 N 条记录（排查用）。失败返回空列表。"""
    try:
        conn = _connect()
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "select ts, caller, logic_model, endpoint, model, status, latency_ms,"
                " input_tokens, output_tokens, error_type from llm_calls"
                " order by id desc limit ?",
                (int(limit),),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    except Exception:
        return []


def summary(days: int = 7, limit: int = 20) -> dict[str, Any]:
    """结构化用量汇总（管理台页面用）。失败返回空结构，绝不抛。"""
    days = int(days)
    limit = int(limit)
    empty: dict[str, Any] = {
        "days": days, "total": 0, "ok": 0, "failed": 0, "skipped": 0, "fallbacks": 0,
        "avgLatencyMs": 0, "inputTokens": 0, "outputTokens": 0,
        "routes": [], "callers": [], "recentFailures": [],
    }
    try:
        conn = _connect()
        try:
            conn.row_factory = sqlite3.Row
            since = f"-{days} days"
            head = conn.execute(
                "select count(*) total,"
                " sum(case when status = 'ok' then 1 else 0 end) ok,"
                " sum(case when status = 'error' then 1 else 0 end) failed,"
                " sum(case when status like 'skipped%' then 1 else 0 end) skipped,"
                " sum(case when is_fallback = 1 then 1 else 0 end) fallbacks,"
                " cast(avg(case when status = 'ok' then latency_ms end) as int) avg_ms,"
                " sum(coalesce(input_tokens, 0)) in_tok,"
                " sum(coalesce(output_tokens, 0)) out_tok"
                " from llm_calls where ts >= datetime('now', ?)",
                (since,),
            ).fetchone()
            routes = [
                dict(r) for r in conn.execute(
                    "select logic_model, endpoint, model, count(*) calls,"
                    " sum(case when status = 'error' then 1 else 0 end) failed,"
                    " sum(case when status like 'skipped%' then 1 else 0 end) skipped,"
                    " sum(case when is_fallback = 1 then 1 else 0 end) fallbacks,"
                    " cast(avg(case when status = 'ok' then latency_ms end) as int) avg_ms,"
                    " sum(coalesce(input_tokens, 0)) in_tok,"
                    " sum(coalesce(output_tokens, 0)) out_tok,"
                    " max(ts) last_ts"
                    " from llm_calls where ts >= datetime('now', ?)"
                    " group by logic_model, endpoint, model order by calls desc limit ?",
                    (since, limit),
                ).fetchall()
            ]
            callers = [
                dict(r) for r in conn.execute(
                    "select caller, count(*) calls,"
                    " sum(case when status = 'error' then 1 else 0 end) failed"
                    " from llm_calls where ts >= datetime('now', ?)"
                    " group by caller order by calls desc limit ?",
                    (since, limit),
                ).fetchall()
            ]
            failures = [
                dict(r) for r in conn.execute(
                    "select ts, caller, logic_model, endpoint, model, status, error_type, error_msg"
                    " from llm_calls where status != 'ok' and ts >= datetime('now', ?)"
                    " order by id desc limit ?",
                    (since, min(limit, 50)),
                ).fetchall()
            ]
            return {
                "days": days,
                "total": head["total"] or 0,
                "ok": head["ok"] or 0,
                "failed": head["failed"] or 0,
                "skipped": head["skipped"] or 0,
                "fallbacks": head["fallbacks"] or 0,
                "avgLatencyMs": head["avg_ms"] or 0,
                "inputTokens": head["in_tok"] or 0,
                "outputTokens": head["out_tok"] or 0,
                "routes": routes,
                "callers": callers,
                "recentFailures": failures,
            }
        finally:
            conn.close()
    except Exception:
        return empty


def report(days: int = 7, limit: int = 20) -> str:
    """终端友好的用量/失败率汇总。"""
    try:
        conn = _connect()
        try:
            conn.row_factory = sqlite3.Row
            since = f"-{int(days)} days"
            total = conn.execute(
                "select count(*) c from llm_calls where ts >= datetime('now', ?)", (since,)
            ).fetchone()["c"]
            lines = [f"最近 {days} 天共 {total} 次调用", ""]
            rows = conn.execute(
                "select logic_model, endpoint, model,"
                " count(*) n, sum(status!='ok') fails,"
                " sum(case when is_fallback=1 then 1 else 0 end) fb,"
                " cast(avg(latency_ms) as int) avg_ms,"
                " sum(coalesce(input_tokens,0)) in_tok, sum(coalesce(output_tokens,0)) out_tok"
                " from llm_calls where ts >= datetime('now', ?)"
                " group by logic_model, endpoint, model order by n desc limit ?",
                (since, int(limit)),
            ).fetchall()
            lines.append(f"{'路由':<14}{'端点':<14}{'模型':<26}{'次数':>6}{'失败':>6}{'备选':>6}{'均耗时':>9}")
            for r in rows:
                lines.append(
                    f"{r['logic_model']:<14}{r['endpoint']:<14}{r['model']:<26}"
                    f"{r['n']:>6}{r['fails']:>6}{r['fb']:>6}{r['avg_ms']:>8}ms"
                )
            by_caller = conn.execute(
                "select caller, count(*) n, sum(status!='ok') fails from llm_calls"
                " where ts >= datetime('now', ?) group by caller order by n desc limit ?",
                (since, int(limit)),
            ).fetchall()
            if by_caller:
                lines += ["", f"{'调用方':<34}{'次数':>6}{'失败':>6}"]
                for r in by_caller:
                    lines.append(f"{r['caller']:<34}{r['n']:>6}{r['fails']:>6}")
            return "\n".join(lines)
        finally:
            conn.close()
    except Exception as exc:  # pragma: no cover - 仅在库损坏时
        return f"读取调用记录失败：{type(exc).__name__}: {exc}"


def _main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "report"
    if cmd == "report":
        days = 7
        if "--days" in argv:
            days = int(argv[argv.index("--days") + 1])
        print(report(days=days))
        return 0
    if cmd == "recent":
        for r in recent(limit=20):
            print(f"{r['ts']}  {r['caller']:<22}{r['logic_model']:<13}{r['endpoint']:<13}"
                  f"{r['model']:<24}{r['status']:<10}{r['latency_ms']}ms")
        return 0
    if cmd == "path":
        print(db_path())
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
