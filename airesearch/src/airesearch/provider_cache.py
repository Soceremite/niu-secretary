from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import utc_now


def utc_datetime() -> datetime:
    return datetime.now(UTC)


def cache_key(provider: str, profile_name: str, query: str, limit: int) -> str:
    normalized = "\n".join(
        [
            provider.strip().lower(),
            profile_name.strip().lower(),
            " ".join(query.split()).lower(),
            str(limit),
        ]
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_cached_response(db_path: Path, provider: str, cache_key_value: str) -> str | None:
    init_db(db_path)
    now = utc_now()
    with connect(db_path) as conn:
        row = conn.execute(
            """
            select response_json from provider_query_cache
            where provider = ? and cache_key = ? and expires_at > ?
            """,
            (provider, cache_key_value, now),
        ).fetchone()
    if row is None:
        return None
    return str(row["response_json"])


def put_cached_response(
    db_path: Path,
    *,
    provider: str,
    cache_key_value: str,
    profile_name: str,
    query: str,
    limit: int,
    response_json: str,
    ttl_days: int,
) -> None:
    init_db(db_path)
    created_at = utc_now()
    expires_at = (utc_datetime() + timedelta(days=ttl_days)).isoformat(timespec="seconds")
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into provider_query_cache (
                provider, cache_key, profile_name, query, limit_count,
                response_json, created_at, expires_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(provider, cache_key) do update set
                profile_name = excluded.profile_name,
                query = excluded.query,
                limit_count = excluded.limit_count,
                response_json = excluded.response_json,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at
            """,
            (
                provider,
                cache_key_value,
                profile_name,
                query,
                limit,
                response_json,
                created_at,
                expires_at,
            ),
        )
        conn.commit()


def monthly_usage(db_path: Path, provider: str, period: str) -> int:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "select request_count from provider_usage where provider = ? and period = ?",
            (provider, period),
        ).fetchone()
    if row is None:
        return 0
    return int(row["request_count"])


def quota_available(db_path: Path, provider: str, period: str, monthly_limit: int) -> bool:
    return monthly_usage(db_path, provider, period) < monthly_limit


def increment_usage(db_path: Path, provider: str, period: str) -> None:
    init_db(db_path)
    now = utc_now()
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into provider_usage (provider, period, request_count, updated_at)
            values (?, ?, 1, ?)
            on conflict(provider, period) do update set
                request_count = provider_usage.request_count + 1,
                updated_at = excluded.updated_at
            """,
            (provider, period, now),
        )
        conn.commit()
