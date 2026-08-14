from __future__ import annotations

import json
from pathlib import Path

from airesearch.cli import build_parser, main
from airesearch.db import connect, init_db
from airesearch.layout_parse import parse_paper_layout
from airesearch.layout_parser import LayoutParserOptions
from airesearch.knowledge_graph import extract_paper_cards
from airesearch.paper_blog import publish_blog_version
from airesearch.paperpipe_sync import sha256_file, utc_now
from airesearch.research_bundle import export_report_bundle
from airesearch.research_site import export_report_site
from airesearch.workflow_check import REQUIRED_FACT_TYPES, run_full_workflow_check

from test_layout_parse import insert_paper


def add_required_facts(conn, paper_key: str) -> None:
    now = utc_now()
    for fact_type in REQUIRED_FACT_TYPES:
        conn.execute(
            """
            insert into research_facts (
                paper_key, fact_type, name, statement, confidence, metadata_json,
                provider_name, extractor_version, created_at, updated_at
            ) values (?, ?, ?, ?, 0.90, '{}', 'fixture', 'workflow-test', ?, ?)
            """,
            (
                paper_key,
                fact_type,
                fact_type,
                f"{fact_type} statement for workflow validation.",
                now,
                now,
            ),
        )


def add_translation_artifact(conn, paper_key: str, paper_dir: Path) -> None:
    now = utc_now()
    path = paper_dir / "summary.zh.md"
    path.write_text("中文摘要：这是一篇用于完整流程验收的论文。", encoding="utf-8")
    conn.execute(
        """
        insert into paper_artifacts (
            paper_key, artifact_type, path, sha256, size_bytes, updated_at
        ) values (?, 'summary_zh', ?, ?, ?, ?)
        """,
        (paper_key, str(path), sha256_file(path), path.stat().st_size, now),
    )


def publish_fixture_blog(db_path: Path, paper_key: str) -> None:
    publish_blog_version(
        db_path,
        paper_key=paper_key,
        title="Workflow 深度解读",
        slug="workflow-check",
        markdown="# 深度解读\n\n" + ("这是一段中文深度解读。" * 120),
        html="<h1>Workflow 深度解读</h1>",
        outline={"sections": [{"section_key": "method", "title": "核心方法"}]},
        image_refs=[],
        generation_meta={"sections": [{"section_key": "method", "title": "核心方法"}]},
        model="fixture",
        prompt_version="workflow-test",
        source_hash="workflow-source",
    )


def build_complete_workflow_fixture(tmp_path: Path) -> tuple[Path, str]:
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    paper_key = "workflow-paper"
    with connect(db_path) as conn:
        insert_paper(conn, tmp_path, paper_key)
        paper_dir = tmp_path / "paperpipe" / "papers" / paper_key
        add_required_facts(conn, paper_key)
        add_translation_artifact(conn, paper_key, paper_dir)
        conn.commit()
    parse_paper_layout(
        db_path=db_path,
        paper_key=paper_key,
        options=LayoutParserOptions(output_dir=tmp_path / "layout"),
        force=True,
    )
    publish_fixture_blog(db_path, paper_key)
    return db_path, paper_key


def test_full_workflow_check_passes_complete_fixture(tmp_path: Path):
    db_path, paper_key = build_complete_workflow_fixture(tmp_path)

    payload = run_full_workflow_check(db_path, paper_key)

    assert payload["ok"] is True
    assert payload["summary"]["failed"] == 0
    keys = {item["key"] for item in payload["checks"]}
    assert {
        "paper.search",
        "facts.required_types",
        "translation.zh_artifacts",
        "layout.equations",
        "layout.tables",
        "layout.visuals",
        "blog.deep_reading",
    }.issubset(keys)
    checks = {item["key"]: item for item in payload["checks"]}
    assert checks["layout.evidence_blocks"]["details"]["high_quality_evidence_blocks"] >= 2
    assert checks["layout.tables"]["details"]["high_quality_tables"] >= 1
    assert checks["layout.equations"]["details"]["high_quality_equations"] >= 1


def test_full_workflow_check_reports_missing_capabilities(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    with connect(db_path) as conn:
        insert_paper(conn, tmp_path, "incomplete-paper")
        conn.commit()

    payload = run_full_workflow_check(db_path, "incomplete-paper")

    assert payload["ok"] is False
    failed = {item["key"] for item in payload["checks"] if not item["ok"]}
    assert "facts.required_types" in failed
    assert "translation.zh_artifacts" in failed
    assert "layout.completed" in failed
    assert "blog.deep_reading" in failed


def test_full_workflow_check_accepts_canonical_formula_without_layout_equation(tmp_path: Path):
    db_path, paper_key = build_complete_workflow_fixture(tmp_path)
    with connect(db_path) as conn:
        run = conn.execute(
            "select id, stats_json from paper_layout_runs where paper_key = ? order by id desc limit 1",
            (paper_key,),
        ).fetchone()
        stats = json.loads(run["stats_json"])
        summary = stats["summary"]
        summary["equation_blocks"] = 0
        summary["high_quality_equation_blocks"] = 0
        summary["block_types"]["interline_equation"] = 0
        conn.execute(
            "delete from paper_layout_blocks where run_id = ? and block_type = 'interline_equation'",
            (run["id"],),
        )
        conn.execute(
            "update paper_layout_runs set stats_json = ? where id = ?",
            (json.dumps(stats), run["id"]),
        )
        now = utc_now()
        conn.execute(
            """
            insert into paper_equations (
                paper_key, source_path, equation_index, label, latex, context, created_at, updated_at
            ) values (?, ?, 0, 'Equation 1', ?, '', ?, ?)
            """,
            (paper_key, "equations.md", r"E = mc^2", now, now),
        )
        conn.commit()

    payload = run_full_workflow_check(db_path, paper_key)

    check = next(item for item in payload["checks"] if item["key"] == "layout.equations")
    assert check["ok"] is True
    assert check["details"]["canonical_equations"] == 1
    assert check["details"]["high_quality_equations"] == 0


def test_full_workflow_check_uses_complete_summary_evidence_count(
    tmp_path: Path, monkeypatch
):
    db_path, paper_key = build_complete_workflow_fixture(tmp_path)
    from airesearch import workflow_check

    actual_detail = workflow_check.admin_layout_detail(db_path, paper_key)
    truncated_detail = {
        **actual_detail,
        "evidence_blocks": [],
        "summary": {
            **(actual_detail.get("summary") or {}),
            "high_quality_evidence_blocks": 7,
        },
    }
    monkeypatch.setattr(workflow_check, "admin_layout_detail", lambda *_args: truncated_detail)

    payload = run_full_workflow_check(db_path, paper_key)

    check = next(item for item in payload["checks"] if item["key"] == "layout.evidence_blocks")
    assert check["ok"] is True
    assert check["details"]["high_quality_evidence_blocks"] == 7
    assert check["details"]["sample_high_quality_evidence_blocks"] == 0


def test_full_workflow_check_treats_tables_as_not_applicable_when_none_detected(
    tmp_path: Path, monkeypatch
):
    db_path, paper_key = build_complete_workflow_fixture(tmp_path)
    from airesearch import workflow_check

    actual_detail = workflow_check.admin_layout_detail(db_path, paper_key)
    summary = {
        **(actual_detail.get("summary") or {}),
        "structured_table_blocks": 0,
        "geometry_table_blocks": 0,
        "text_fallback_table_blocks": 0,
        "spanning_table_blocks": 0,
        "high_quality_table_blocks": 0,
    }
    block_counts = {**(actual_detail.get("block_counts") or {}), "table": 0}
    evidence_blocks = [
        block for block in actual_detail.get("evidence_blocks") or [] if block.get("block_type") != "table"
    ]
    no_table_detail = {
        **actual_detail,
        "summary": summary,
        "block_counts": block_counts,
        "evidence_blocks": evidence_blocks,
        "capabilities": {
            **(actual_detail.get("capabilities") or {}),
            "has_high_quality_tables": False,
        },
    }
    monkeypatch.setattr(workflow_check, "admin_layout_detail", lambda *_args: no_table_detail)

    payload = run_full_workflow_check(db_path, paper_key)

    check = next(item for item in payload["checks"] if item["key"] == "layout.tables")
    assert check["ok"] is True
    assert check["details"]["required"] is False


def test_cli_workflow_check_command_parse_and_exit_code(tmp_path: Path, capsys):
    db_path, paper_key = build_complete_workflow_fixture(tmp_path)
    parser = build_parser()

    args = parser.parse_args(["--db", str(db_path), "workflow-check", "--paper-key", paper_key])

    assert args.command == "workflow-check"
    assert args.paper_key == paper_key
    assert main(["--db", str(db_path), "workflow-check", "--paper-key", paper_key]) == 0
    output = capsys.readouterr().out
    assert '"ok": true' in output


def test_full_workflow_check_verifies_public_api_and_page(tmp_path: Path):
    db_path, paper_key = build_complete_workflow_fixture(tmp_path)
    bundle_dir = tmp_path / "bundle"
    extract_paper_cards(db_path)
    export_report_bundle(db_path, bundle_dir)
    export_report_site(bundle_dir)

    payload = run_full_workflow_check(db_path, paper_key, site_dir=bundle_dir)

    assert payload["ok"] is True
    checks = {item["key"]: item for item in payload["checks"]}
    assert checks["public.api"]["ok"] is True
    assert checks["public.page"]["ok"] is True


def test_full_workflow_check_rejects_public_output_without_evidence_graph(tmp_path: Path):
    db_path, paper_key = build_complete_workflow_fixture(tmp_path)
    bundle_dir = tmp_path / "bundle"
    extract_paper_cards(db_path)
    export_report_bundle(db_path, bundle_dir)
    export_report_site(bundle_dir)
    api_path = bundle_dir / "api" / "papers" / f"{paper_key}.json"
    html_path = bundle_dir / "papers" / f"{paper_key}.html"
    api_payload = json.loads(api_path.read_text(encoding="utf-8"))
    api_payload.pop("evidence_graph", None)
    api_path.write_text(json.dumps(api_payload), encoding="utf-8")
    html_path.write_text(
        html_path.read_text(encoding="utf-8").replace("证据关系", "关联已移除"),
        encoding="utf-8",
    )

    payload = run_full_workflow_check(db_path, paper_key, site_dir=bundle_dir)

    checks = {item["key"]: item for item in payload["checks"]}
    assert checks["public.api"]["ok"] is False
    assert checks["public.page"]["ok"] is False
