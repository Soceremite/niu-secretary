import hashlib
import json
from pathlib import Path

from airesearch.db import connect, init_db
from airesearch.evidence_repair import (
    build_evidence_repair_candidates,
    export_evidence_source_path_repairs,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_repair_db(tmp_path: Path, *, matching: bool = True) -> tuple[Path, Path]:
    db_path = tmp_path / "airesearch.sqlite3"
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    summary_path = paper_dir / "summary.md"
    quote = "This exact evidence quote supports the extracted research fact."
    if matching:
        summary_path.write_text(f"# Summary\n\n{quote}\n", encoding="utf-8")
    else:
        summary_path.write_text("# Summary\n\nNo matching evidence appears here.\n", encoding="utf-8")
    now = "2026-06-09T00:00:00+00:00"
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into papers (
                paper_key, title, authors_json, year, venue, ids_json,
                paper_dir, meta_json, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("paper_a", "Paper A", "[]", 2026, "TestConf", "{}", str(paper_dir), "{}", now, now),
        )
        conn.execute(
            """
            insert into paper_artifacts (
                paper_key, artifact_type, path, sha256, size_bytes, updated_at
            ) values (?, ?, ?, ?, ?, ?)
            """,
            ("paper_a", "summary", str(summary_path), _sha256(summary_path), summary_path.stat().st_size, now),
        )
        fact = conn.execute(
            """
            insert into research_facts (
                paper_key, fact_type, name, statement, confidence, metadata_json,
                provider_name, extractor_version, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            returning id
            """,
            (
                "paper_a",
                "claim",
                "Test claim",
                "The paper makes a grounded claim.",
                0.9,
                "{}",
                "fixture",
                "test",
                now,
                now,
            ),
        ).fetchone()
        conn.execute(
            """
            insert into research_fact_provenance (
                fact_id, evidence_quote, evidence_artifact_type, evidence_source_path, created_at
            ) values (?, ?, ?, ?, ?)
            """,
            (fact["id"], quote, "abstract", "", now),
        )
    return db_path, summary_path


def test_build_evidence_repair_candidates_matches_local_artifact(tmp_path: Path):
    db_path, summary_path = make_repair_db(tmp_path)

    candidates = build_evidence_repair_candidates(db_path)

    assert len(candidates) == 1
    assert candidates[0].repairable is True
    assert candidates[0].recommended_source_path == str(summary_path)
    assert candidates[0].recommended_artifact_type == "summary"
    assert candidates[0].matches[0].match_type == "normalized_exact_contains"


def test_export_evidence_source_path_repairs_dry_run_does_not_update_db(tmp_path: Path):
    db_path, summary_path = make_repair_db(tmp_path)
    out_path = tmp_path / "repair.jsonl"

    result = export_evidence_source_path_repairs(db_path, out_path)

    assert result.candidate_count == 1
    assert result.repairable_count == 1
    assert result.applied_count == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["recommended_source_path"] == str(summary_path)
    assert payload["applied"] is False
    with connect(db_path) as conn:
        row = conn.execute("select evidence_source_path from research_fact_provenance").fetchone()
    assert row["evidence_source_path"] == ""


def test_export_evidence_source_path_repairs_apply_updates_db(tmp_path: Path):
    db_path, summary_path = make_repair_db(tmp_path)
    out_path = tmp_path / "repair.jsonl"

    result = export_evidence_source_path_repairs(db_path, out_path, apply=True)

    assert result.candidate_count == 1
    assert result.applied_count == 1
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["applied"] is True
    with connect(db_path) as conn:
        row = conn.execute("select evidence_source_path from research_fact_provenance").fetchone()
    assert row["evidence_source_path"] == str(summary_path)


def test_export_evidence_source_path_repairs_leaves_no_match_unapplied(tmp_path: Path):
    db_path, _summary_path = make_repair_db(tmp_path, matching=False)
    out_path = tmp_path / "repair.jsonl"

    result = export_evidence_source_path_repairs(db_path, out_path, apply=True)

    assert result.candidate_count == 1
    assert result.repairable_count == 0
    assert result.applied_count == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["recommended_source_path"] == ""
    assert payload["matches"] == []
    with connect(db_path) as conn:
        row = conn.execute("select evidence_source_path from research_fact_provenance").fetchone()
    assert row["evidence_source_path"] == ""
