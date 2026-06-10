import json
from pathlib import Path

import pytest

from airesearch.fact_extraction import extract_research_facts
from airesearch.knowledge_graph import extract_paper_cards
from airesearch.paperpipe_sync import sync_paperpipe
from airesearch.research_digest import DigestInputError
from airesearch.research_narrative import (
    build_narrative_report,
    export_narrative_report,
    narrative_report_to_dict,
    render_markdown,
)


FIXTURE = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"


def synced_fact_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    extract_paper_cards(db_path)
    extract_research_facts(db_path, provider_name="fixture", fixture_path=FIXTURE)
    return db_path


def test_build_narrative_report_from_fixture_facts(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)

    report = build_narrative_report(db_path)

    assert report.paper_count == 1
    assert report.fact_count == 2
    assert report.finding_count == 2
    assert report.action_count == 1
    assert any("Method is represented in 1/1 papers" in item for item in report.supported_areas)
    assert any("Claim is represented in 1/1 papers" in item for item in report.supported_areas)
    assert any("Dataset is represented in 0/1 papers" in item for item in report.provisional_areas)
    assert report.representative_findings[0].fact_type == "method"
    assert report.priority_actions[0].paper_key == "1706_03762"
    assert "Dataset, Benchmark, Limitation" in report.priority_actions[0].action


def test_render_markdown_includes_narrative_sections(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    report = build_narrative_report(db_path)

    markdown = render_markdown(report)

    assert "# AIResearch Narrative Report" in markdown
    assert "## Executive Summary" in markdown
    assert "The current corpus contains 1 papers and 2 extracted research facts." in markdown
    assert "## What Is Well Supported" in markdown
    assert "Method is represented in 1/1 papers" in markdown
    assert "## What Is Provisional" in markdown
    assert "Dataset is represented in 0/1 papers" in markdown
    assert "## Representative Findings" in markdown
    assert "Transformer replaces recurrence" in markdown
    assert "## Priority Follow-Up Actions" in markdown
    assert "Review `1706_03762` for missing fact types: Dataset, Benchmark, Limitation" in markdown
    assert "## Evidence Cautions" in markdown


def test_narrative_report_to_dict_and_export_json(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    markdown_path = tmp_path / "research-narrative.md"
    json_path = tmp_path / "research-narrative.json"

    markdown_report = export_narrative_report(db_path, markdown_path)
    json_report = export_narrative_report(db_path, json_path, output_format="json")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    direct_payload = narrative_report_to_dict(json_report)
    assert markdown_report.paper_count == 1
    assert payload["paper_count"] == 1
    assert payload["fact_count"] == 2
    assert payload["finding_count"] == 2
    assert payload["representative_findings"][0]["paper_key"] == "1706_03762"
    assert payload["priority_actions"][0]["priority_score"] == 35
    assert direct_payload["action_count"] == 1
    assert "# AIResearch Narrative Report" in markdown_path.read_text(encoding="utf-8")


def test_build_narrative_report_requires_paper_cards(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"

    with pytest.raises(DigestInputError, match="paper_cards is empty"):
        build_narrative_report(db_path)
