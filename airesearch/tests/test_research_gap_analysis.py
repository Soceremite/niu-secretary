import json
from pathlib import Path

import pytest

from airesearch.fact_extraction import extract_research_facts
from airesearch.knowledge_graph import extract_paper_cards
from airesearch.paperpipe_sync import sync_paperpipe
from airesearch.research_digest import DigestInputError
from airesearch.research_gap_analysis import (
    build_gap_analysis,
    export_gap_analysis,
    gap_analysis_to_dict,
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


def test_build_gap_analysis_finds_fixture_missing_types(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)

    analysis = build_gap_analysis(db_path)

    assert analysis.paper_count == 1
    assert analysis.fact_count == 2
    assert [item.fact_type for item in analysis.fact_type_coverage] == [
        "method",
        "dataset",
        "benchmark",
        "claim",
        "limitation",
    ]
    assert analysis.fact_type_coverage[0].paper_count == 1
    assert analysis.fact_type_coverage[0].fact_count == 1
    assert analysis.fact_type_coverage[0].coverage_ratio == 1.0
    assert [item.fact_type for item in analysis.low_coverage_fact_types] == [
        "dataset",
        "benchmark",
        "limitation",
    ]
    paper = analysis.papers[0]
    assert paper.paper_key == "1706_03762"
    assert paper.fact_counts == {
        "method": 1,
        "dataset": 0,
        "benchmark": 0,
        "claim": 1,
        "limitation": 0,
    }
    assert paper.missing_fact_types == ["dataset", "benchmark", "limitation"]
    assert paper.has_code_links is False
    assert paper.missing_evidence_source_path_count == 0


def test_render_markdown_includes_missing_types_and_evidence_summary(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    analysis = build_gap_analysis(db_path)

    markdown = render_markdown(analysis)

    assert "# AIResearch Gap Analysis" in markdown
    assert "Papers missing fact types: 1" in markdown
    assert "| Dataset | 0 | 0 | 0% |" in markdown
    assert "## Low-Coverage Fact Types" in markdown
    assert "- Dataset: 0/1 papers (0%)" in markdown
    assert "missing Dataset, Benchmark, Limitation" in markdown
    assert "## Papers Without Code Links" in markdown
    assert "- Attention Is All You Need | 2017 | `1706_03762`" in markdown
    assert "No evidence source path gaps." in markdown


def test_gap_analysis_to_dict_and_export_json(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    markdown_path = tmp_path / "gap-analysis.md"
    json_path = tmp_path / "gap-analysis.json"

    markdown_analysis = export_gap_analysis(db_path, markdown_path)
    json_analysis = export_gap_analysis(db_path, json_path, output_format="json")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    direct_payload = gap_analysis_to_dict(json_analysis)
    assert markdown_analysis.paper_count == 1
    assert payload["paper_count"] == 1
    assert payload["fact_count"] == 2
    assert payload["low_coverage_fact_types"][0]["fact_type"] == "dataset"
    assert payload["papers"][0]["missing_fact_types"] == ["dataset", "benchmark", "limitation"]
    assert direct_payload["papers"][0]["paper_key"] == "1706_03762"
    assert "# AIResearch Gap Analysis" in markdown_path.read_text(encoding="utf-8")


def test_build_gap_analysis_requires_paper_cards(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"

    with pytest.raises(DigestInputError, match="paper_cards is empty"):
        build_gap_analysis(db_path)
