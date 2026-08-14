import sqlite3
from pathlib import Path

from airesearch.db import connect, init_db


def test_init_db_creates_expected_tables(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        names = {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }

    assert {
        "papers",
        "paper_sources",
        "paper_artifacts",
        "ingest_runs",
        "ingest_items",
        "sync_events",
        "research_profiles",
        "discovery_runs",
        "research_candidates",
    }.issubset(names)


def test_connect_returns_row_mapping(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)

    with connect(db_path) as conn:
        row = conn.execute("select count(*) as count from papers").fetchone()

    assert row["count"] == 0


def test_knowledge_graph_edges_index_foreign_key_targets(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)

    with connect(db_path) as conn:
        indexes = {
            row["name"]
            for row in conn.execute("pragma index_list(kg_edges)").fetchall()
        }

    assert "idx_kg_edges_target_key" in indexes


def test_init_db_creates_paper_archive_state(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)

    with connect(db_path) as conn:
        columns = {
            row["name"]
            for row in conn.execute("pragma table_info(paper_archives)")
        }

    assert {
        "paper_key",
        "provider",
        "remote_name",
        "remote_path",
        "archive_sha256",
        "archive_size_bytes",
        "source_manifest_json",
        "status",
        "verified_at",
        "evicted_at",
        "restored_at",
        "last_error",
        "pinned",
        "updated_at",
    } == columns

def test_init_db_creates_fact_extraction_cache(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)

    with connect(db_path) as conn:
        columns = {
            row["name"]
            for row in conn.execute("pragma table_info(fact_extraction_cache)").fetchall()
        }

    assert {
        "id",
        "paper_key",
        "provider_name",
        "extractor_version",
        "model",
        "evidence_hash",
        "prompt_json",
        "response_json",
        "status",
        "error",
        "created_at",
        "updated_at",
    }.issubset(columns)
