import json
from pathlib import Path

import pytest

from airesearch.fact_extraction import extract_research_facts
from airesearch.knowledge_graph import extract_paper_cards
from airesearch.paperpipe_sync import sync_paperpipe
from airesearch.research_digest import DigestInputError
from airesearch.research_map import (
    build_research_map,
    export_research_map,
    render_markdown,
    research_map_to_dict,
)


FIXTURE = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"


def synced_fact_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    extract_paper_cards(db_path)
    extract_research_facts(db_path, provider_name="fixture", fixture_path=FIXTURE)
    return db_path


def test_build_research_map_groups_fixture_facts(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)

    research_map = build_research_map(db_path)

    assert research_map.paper_count == 1
    assert research_map.fact_count == 2
    assert research_map.item_count == 2
    assert research_map.fact_type_counts == {"method": 1, "claim": 1}
    method_item = research_map.sections["method"][0]
    assert method_item.key == "transformer attention architecture"
    assert method_item.label == "Transformer attention architecture"
    assert method_item.paper_count == 1
    assert method_item.fact_count == 1
    assert method_item.average_confidence == 0.92
    assert method_item.paper_refs[0].paper_key == "1706_03762"


def test_render_markdown_includes_summary_items_papers_and_evidence(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    research_map = build_research_map(db_path)

    markdown = render_markdown(research_map)

    assert "# AIResearch Research Map" in markdown
    assert "Mapped items: 2" in markdown
    assert "## Method" in markdown
    assert "### Transformer attention architecture" in markdown
    assert "Papers: 1 | Facts: 1 | Average confidence: 0.92" in markdown
    assert "Attention Is All You Need | 2017" in markdown
    assert "1706_03762" in markdown
    assert "The Transformer uses attention" in markdown


def test_research_map_to_dict_and_export_json(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    markdown_path = tmp_path / "research-map.md"
    json_path = tmp_path / "research-map.json"

    markdown_map = export_research_map(db_path, markdown_path)
    json_map = export_research_map(db_path, json_path, output_format="json")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    direct_payload = research_map_to_dict(json_map)
    assert markdown_map.item_count == 2
    assert payload["paper_count"] == 1
    assert payload["fact_count"] == 2
    assert payload["item_count"] == 2
    assert payload["sections"][0]["fact_type"] == "method"
    assert payload["sections"][0]["items"][0]["papers"][0]["paper_key"] == "1706_03762"
    assert direct_payload["sections"][1]["fact_type"] == "claim"
    assert "# AIResearch Research Map" in markdown_path.read_text(encoding="utf-8")


def test_build_research_map_requires_paper_cards(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"

    with pytest.raises(DigestInputError, match="paper_cards is empty"):
        build_research_map(db_path)
