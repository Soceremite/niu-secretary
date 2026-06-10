import json
from pathlib import Path

import pytest

from airesearch.db import connect
from airesearch.fact_extraction import extract_research_facts
from airesearch.knowledge_graph import extract_paper_cards
from airesearch.paperpipe_sync import sync_paperpipe
from airesearch.research_digest import DigestInputError
from airesearch.research_relations import (
    build_research_relations,
    export_research_relations,
    render_markdown,
    research_relations_to_dict,
)


FIXTURE = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"


def relation_fixture_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    extract_research_facts(db_path, provider_name="fixture", fixture_path=FIXTURE)
    now = "2026-06-10T00:00:00+00:00"
    paper_dir = tmp_path / "paper_b"
    paper_dir.mkdir()
    summary_path = paper_dir / "summary.md"
    summary_path.write_text("Paper B uses the Common Robotics Dataset.", encoding="utf-8")
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into papers (
                paper_key, title, authors_json, year, venue, ids_json,
                paper_dir, meta_json, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "paper_b",
                "Paper B",
                json.dumps(["Researcher B"]),
                2026,
                "TestConf",
                json.dumps({"arxiv_id": "2606.00002"}),
                str(paper_dir),
                "{}",
                now,
                now,
            ),
        )
        conn.execute(
            """
            insert into paper_artifacts (
                paper_key, artifact_type, path, sha256, size_bytes, updated_at
            ) values (?, ?, ?, ?, ?, ?)
            """,
            ("paper_b", "summary", str(summary_path), "1" * 64, summary_path.stat().st_size, now),
        )
        conn.execute(
            """
            insert into paper_code_links (
                paper_key, url, host, owner, repo, source_type, source_path,
                context, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "1706_03762",
                "https://github.com/shared/common",
                "github.com",
                "shared",
                "common",
                "meta_json",
                "",
                "",
                now,
                now,
            ),
        )
        conn.execute(
            """
            insert into paper_code_links (
                paper_key, url, host, owner, repo, source_type, source_path,
                context, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "paper_b",
                "https://github.com/shared/common",
                "github.com",
                "shared",
                "common",
                "meta_json",
                "",
                "",
                now,
                now,
            ),
        )
        relation_facts = [
            (
                "1706_03762",
                "dataset",
                "Common Robotics Dataset",
                "The paper evaluates on the Common Robotics Dataset.",
            ),
            (
                "paper_b",
                "dataset",
                "Common Robotics Dataset",
                "Paper B also uses the Common Robotics Dataset.",
            ),
            (
                "1706_03762",
                "method",
                "Shared Attention Planner",
                "The paper uses a Shared Attention Planner.",
            ),
            (
                "paper_b",
                "method",
                "Shared Attention Planner",
                "Paper B adapts the Shared Attention Planner.",
            ),
            (
                "1706_03762",
                "benchmark",
                "RobotBench",
                "The paper reports results on RobotBench.",
            ),
            (
                "paper_b",
                "benchmark",
                "RobotBench",
                "Paper B compares against RobotBench.",
            ),
        ]
        for paper_key, fact_type, name, statement in relation_facts:
            row = conn.execute(
                """
                insert into research_facts (
                    paper_key, fact_type, name, statement, confidence, metadata_json,
                    provider_name, extractor_version, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                returning id
                """,
                (
                    paper_key,
                    fact_type,
                    name,
                    statement,
                    0.88,
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
                    fact_id, evidence_quote, evidence_artifact_type,
                    evidence_source_path, created_at
                ) values (?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    "uses the Common Robotics Dataset",
                    "summary",
                    str(summary_path),
                    now,
                ),
            )
        conn.commit()
    extract_paper_cards(db_path)
    return db_path


def test_build_research_relations_groups_shared_code_and_datasets(tmp_path: Path):
    db_path = relation_fixture_db(tmp_path)

    relations = build_research_relations(db_path)

    assert relations.paper_count == 2
    assert relations.fact_count == 8
    assert relations.code_relation_count >= 1
    assert relations.method_relation_count == 1
    assert relations.dataset_relation_count == 1
    assert relations.benchmark_relation_count == 1
    repo = next(group for group in relations.code_relations if group.key == "repo:github.com/shared/common")
    method = relations.method_relations[0]
    dataset = relations.dataset_relations[0]
    benchmark = relations.benchmark_relations[0]
    assert repo.paper_count == 2
    assert repo.urls == ["https://github.com/shared/common"]
    assert method.label == "Shared Attention Planner"
    assert method.paper_count == 2
    assert dataset.label == "Common Robotics Dataset"
    assert dataset.paper_count == 2
    assert dataset.evidence_count == 2
    assert benchmark.label == "RobotBench"
    assert benchmark.paper_count == 2
    assert relations.citation_status.status == "citation_ledger_missing"
    assert relations.citation_status.missing_citation_artifact_paper_count == 2


def test_build_research_relations_uses_citation_ledger_rows(tmp_path: Path):
    db_path = relation_fixture_db(tmp_path)
    now = "2026-06-10T00:00:00+00:00"
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into paper_citations (
                paper_key, source_path, citation_index, citation_key,
                raw_text, context, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "1706_03762",
                "/tmp/source.tex",
                0,
                "devlin2019bert",
                "\\cite{devlin2019bert}",
                "Prior work includes \\cite{devlin2019bert}.",
                now,
                now,
            ),
        )
        conn.commit()

    relations = build_research_relations(db_path)

    assert relations.citation_status.status == "citation_ledger_available"
    assert relations.citation_status.citation_count == 1
    assert relations.citation_status.citation_artifact_paper_count == 1
    assert relations.citation_status.missing_citation_artifact_paper_count == 1


def test_render_markdown_includes_relation_sections(tmp_path: Path):
    db_path = relation_fixture_db(tmp_path)
    relations = build_research_relations(db_path)

    markdown = render_markdown(relations)

    assert "# AIResearch Cross-Paper Relations" in markdown
    assert "## Code Relations" in markdown
    assert "github.com/shared/common" in markdown
    assert "## Method Relations" in markdown
    assert "Shared Attention Planner" in markdown
    assert "## Dataset Relations" in markdown
    assert "Common Robotics Dataset" in markdown
    assert "## Benchmark Relations" in markdown
    assert "RobotBench" in markdown
    assert "## Citation Ledger Status" in markdown
    assert "True citation edges still require matching citation keys to papers" in markdown


def test_research_relations_to_dict_and_export_json(tmp_path: Path):
    db_path = relation_fixture_db(tmp_path)
    markdown_path = tmp_path / "relations.md"
    json_path = tmp_path / "relations.json"

    markdown_report = export_research_relations(db_path, markdown_path)
    json_report = export_research_relations(db_path, json_path, output_format="json")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    direct_payload = research_relations_to_dict(json_report)
    assert markdown_report.relation_count >= 2
    assert payload["paper_count"] == 2
    assert payload["method_relations"][0]["paper_count"] == 2
    assert payload["dataset_relations"][0]["paper_count"] == 2
    assert payload["benchmark_relations"][0]["paper_count"] == 2
    assert direct_payload["citation_status"]["status"] == "citation_ledger_missing"
    assert direct_payload["citation_status"]["citation_count"] == 0
    assert "# AIResearch Cross-Paper Relations" in markdown_path.read_text(encoding="utf-8")


def test_build_research_relations_requires_paper_cards(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"

    with pytest.raises(DigestInputError, match="paper_cards is empty"):
        build_research_relations(db_path)
