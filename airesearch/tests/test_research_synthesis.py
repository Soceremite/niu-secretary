import json
from pathlib import Path

import pytest

from airesearch.fact_extraction import extract_research_facts
from airesearch.knowledge_graph import extract_paper_cards
from airesearch.paperpipe_sync import sync_paperpipe
from airesearch.research_digest import DigestInputError
from airesearch.research_synthesis import (
    build_research_synthesis,
    export_research_synthesis,
    render_markdown,
    research_synthesis_to_dict,
)


FIXTURE = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"


def synced_fact_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    extract_paper_cards(db_path)
    extract_research_facts(db_path, provider_name="fixture", fixture_path=FIXTURE)
    return db_path


def test_build_research_synthesis_classifies_fixture_coverage(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)

    synthesis = build_research_synthesis(db_path)

    assert synthesis.paper_count == 1
    assert synthesis.fact_count == 2
    assert [item.fact_type for item in synthesis.strong_coverage.fact_types] == ["method", "claim"]
    assert synthesis.moderate_coverage.fact_types == []
    assert [item.fact_type for item in synthesis.weak_coverage.fact_types] == [
        "dataset",
        "benchmark",
        "limitation",
    ]
    assert synthesis.papers_missing_fact_types == 1
    assert synthesis.papers_without_code_links == 1
    assert synthesis.extraction_target_count == 1
    target = synthesis.extraction_targets[0]
    assert target.paper_key == "1706_03762"
    assert target.missing_fact_types == ["dataset", "benchmark", "limitation"]
    assert target.priority_score == 35


def test_render_markdown_includes_snapshot_and_targets(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    synthesis = build_research_synthesis(db_path)

    markdown = render_markdown(synthesis)

    assert "# AIResearch Research Synthesis" in markdown
    assert "Papers: 1" in markdown
    assert "Facts: 2" in markdown
    assert "## Strong Coverage" in markdown
    assert "- Method: 1/1 papers, 1 facts (100%)" in markdown
    assert "## Weak Coverage" in markdown
    assert "- Dataset: 0/1 papers, 0 facts (0%)" in markdown
    assert "## Code Availability" in markdown
    assert "1 papers have no extracted code links." in markdown
    assert "## Next Extraction Targets" in markdown
    assert "priority 35; missing fact types: Dataset, Benchmark, Limitation" in markdown


def test_research_synthesis_to_dict_and_export_json(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    markdown_path = tmp_path / "research-synthesis.md"
    json_path = tmp_path / "research-synthesis.json"

    markdown_synthesis = export_research_synthesis(db_path, markdown_path)
    json_synthesis = export_research_synthesis(db_path, json_path, output_format="json")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    direct_payload = research_synthesis_to_dict(json_synthesis)
    assert markdown_synthesis.paper_count == 1
    assert payload["paper_count"] == 1
    assert payload["fact_count"] == 2
    assert payload["weak_coverage"]["fact_types"][0]["fact_type"] == "dataset"
    assert payload["extraction_targets"][0]["paper_key"] == "1706_03762"
    assert direct_payload["extraction_target_count"] == 1
    assert "# AIResearch Research Synthesis" in markdown_path.read_text(encoding="utf-8")


def test_build_research_synthesis_requires_paper_cards(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"

    with pytest.raises(DigestInputError, match="paper_cards is empty"):
        build_research_synthesis(db_path)
