import json
from pathlib import Path

import pytest

from airesearch.fact_extraction import extract_research_facts
from airesearch.knowledge_graph import extract_paper_cards
from airesearch.paperpipe_sync import sync_paperpipe
from airesearch.research_digest import (
    DigestInputError,
    build_research_digest,
    export_research_digest,
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


def test_build_research_digest_groups_fixture_facts(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)

    digest = build_research_digest(db_path)

    assert digest.paper_count == 1
    assert digest.fact_count == 2
    paper = digest.papers[0]
    assert paper.paper_key == "1706_03762"
    assert paper.title == "Attention Is All You Need"
    assert paper.facts["method"][0].name == "Transformer attention architecture"
    assert paper.facts["claim"][0].confidence == 0.85


def test_render_markdown_includes_metadata_facts_and_evidence(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    digest = build_research_digest(db_path)

    markdown = render_markdown(digest)

    assert "# AIResearch Digest" in markdown
    assert "## Attention Is All You Need" in markdown
    assert "### Method" in markdown
    assert "The Transformer replaces recurrence and convolution" in markdown
    assert "confidence: 0.92" in markdown
    assert "Evidence: The Transformer uses attention" in markdown


def test_export_research_digest_writes_markdown_and_json(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    markdown_path = tmp_path / "digest.md"
    json_path = tmp_path / "digest.json"

    markdown_digest = export_research_digest(db_path, markdown_path)
    json_digest = export_research_digest(db_path, json_path, output_format="json")

    assert markdown_digest.paper_count == 1
    assert json_digest.fact_count == 2
    assert "Attention Is All You Need" in markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["paper_count"] == 1
    assert payload["fact_count"] == 2
    assert payload["papers"][0]["facts"]["method"][0]["evidence_artifact_type"] == "summary"


def test_build_research_digest_requires_paper_cards(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"

    with pytest.raises(DigestInputError, match="paper_cards is empty"):
        build_research_digest(db_path)
