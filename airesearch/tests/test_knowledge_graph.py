import json
from pathlib import Path

from airesearch.db import connect, init_db
from airesearch.knowledge_graph import (
    export_paper_cards,
    extract_paper_cards,
    list_paper_cards,
)
from airesearch.paperpipe_sync import sync_paperpipe


def synced_fixture_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    init_db(db_path)
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    return db_path


def test_extract_paper_cards_creates_card_graph_and_provenance(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)

    result = extract_paper_cards(db_path)

    assert result.papers_seen == 1
    assert result.cards_written == 1
    assert result.nodes_written >= 6
    assert result.edges_written >= 5
    assert result.provenance_written >= result.cards_written
    with connect(db_path) as conn:
        card = conn.execute("select * from paper_cards where paper_key = ?", ("1706_03762",)).fetchone()
        paper_node = conn.execute("select * from kg_nodes where node_key = ?", ("paper:1706_03762",)).fetchone()
        author_edge = conn.execute(
            "select * from kg_edges where source_key = ? and relation = ?",
            ("paper:1706_03762", "authored_by"),
        ).fetchone()
        provenance_count = conn.execute("select count(*) as count from kg_provenance").fetchone()["count"]

    assert card["title"] == "Attention Is All You Need"
    assert json.loads(card["authors_json"]) == ["Ashish Vaswani", "Noam Shazeer"]
    assert "summary" in json.loads(card["artifact_types_json"])
    assert paper_node["label"] == "Attention Is All You Need"
    assert author_edge["target_key"].startswith("author:")
    assert provenance_count > 0


def test_extract_paper_cards_is_idempotent(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)

    first = extract_paper_cards(db_path)
    second = extract_paper_cards(db_path)

    assert first.cards_written == 1
    assert second.cards_written == 1
    with connect(db_path) as conn:
        counts = {
            table: conn.execute(f"select count(*) as count from {table}").fetchone()["count"]
            for table in ["paper_cards", "kg_nodes", "kg_edges"]
        }

    assert counts["paper_cards"] == 1
    assert counts["kg_nodes"] == second.nodes_written
    assert counts["kg_edges"] == second.edges_written


def test_list_and_export_paper_cards(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)
    out_path = tmp_path / "paper_cards.jsonl"
    extract_paper_cards(db_path)

    rows = list_paper_cards(db_path, limit=5)
    exported = export_paper_cards(db_path, out_path)

    assert len(rows) == 1
    assert rows[0]["paper_key"] == "1706_03762"
    assert exported == 1
    payload = json.loads(out_path.read_text(encoding="utf-8").strip())
    assert payload["paper_key"] == "1706_03762"
    assert payload["title"] == "Attention Is All You Need"
    assert payload["artifact_types"]


def test_extract_paper_cards_can_filter_single_paper(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)

    missing = extract_paper_cards(db_path, paper_key="missing")
    present = extract_paper_cards(db_path, paper_key="1706_03762")

    assert missing.papers_seen == 0
    assert missing.cards_written == 0
    assert present.papers_seen == 1
    assert present.cards_written == 1
