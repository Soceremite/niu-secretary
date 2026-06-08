from pathlib import Path

from airesearch.db import connect, init_db
from airesearch.provider_cache import (
    cache_key,
    get_cached_response,
    increment_usage,
    monthly_usage,
    put_cached_response,
    quota_available,
)


def test_provider_cache_round_trip(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    key = cache_key("google_scholar", "diffusion_models", '"diffusion model"', 10)

    assert get_cached_response(db_path, "google_scholar", key) is None

    put_cached_response(
        db_path,
        provider="google_scholar",
        cache_key_value=key,
        profile_name="diffusion_models",
        query='"diffusion model"',
        limit=10,
        response_json='{"organic_results": []}',
        ttl_days=30,
    )

    assert get_cached_response(db_path, "google_scholar", key) == '{"organic_results": []}'


def test_expired_provider_cache_misses(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    key = cache_key("google_scholar", "diffusion_models", "query", 5)

    put_cached_response(
        db_path,
        provider="google_scholar",
        cache_key_value=key,
        profile_name="diffusion_models",
        query="query",
        limit=5,
        response_json='{"organic_results": []}',
        ttl_days=-1,
    )

    assert get_cached_response(db_path, "google_scholar", key) is None


def test_provider_usage_counts_by_month(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)

    assert monthly_usage(db_path, "google_scholar", "2026-06") == 0
    assert quota_available(db_path, "google_scholar", "2026-06", 2)

    increment_usage(db_path, "google_scholar", "2026-06")
    increment_usage(db_path, "google_scholar", "2026-06")

    assert monthly_usage(db_path, "google_scholar", "2026-06") == 2
    assert not quota_available(db_path, "google_scholar", "2026-06", 2)


def test_provider_tables_created_by_init_db(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    with connect(db_path) as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
        }

    assert "provider_query_cache" in tables
    assert "provider_usage" in tables
