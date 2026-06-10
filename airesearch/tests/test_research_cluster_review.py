import json
from pathlib import Path

from airesearch.research_cluster_review import (
    build_cluster_review_packet,
    cluster_review_packet_to_dict,
    export_cluster_review_packet,
    render_markdown,
)
from test_research_clusters import FixtureEmbeddingProvider, make_cluster_db


def test_build_cluster_review_packet_creates_pending_review_items(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)

    packet = build_cluster_review_packet(db_path)

    assert packet.paper_count == 2
    assert packet.fact_count == 4
    assert packet.cluster_count == 1
    assert packet.review_item_count == 1
    assert packet.accept_candidate_count == 1
    assert packet.needs_review_count == 0
    item = packet.items[0]
    assert item.cluster_id.startswith("method:")
    assert item.recommended_status == "accept_candidate"
    assert item.review_status == "pending"
    assert item.review_notes == ""
    assert "cross-paper support" in item.rationale
    assert {fact.paper_key for fact in item.facts} == {"paper_a", "paper_b"}


def test_build_cluster_review_packet_semantic_mode(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)

    packet = build_cluster_review_packet(
        db_path,
        mode="semantic",
        embedding_provider=FixtureEmbeddingProvider(),
        semantic_threshold=0.9,
    )

    assert packet.mode == "semantic"
    assert packet.semantic_threshold == 0.9
    assert packet.review_item_count == 1
    assert packet.items[0].recommended_status == "accept_candidate"


def test_render_markdown_includes_review_fields(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)
    packet = build_cluster_review_packet(db_path)

    markdown = render_markdown(packet)

    assert "# AIResearch Cluster Review Packet" in markdown
    assert "Review items: 1" in markdown
    assert "Recommended status: `accept_candidate`" in markdown
    assert "Review status: `pending`" in markdown
    assert "Review notes: " in markdown
    assert "`paper_a` Attention World Model" in markdown


def test_cluster_review_packet_to_dict_and_export_json(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)
    markdown_path = tmp_path / "cluster-review.md"
    json_path = tmp_path / "cluster-review.json"

    markdown_packet = export_cluster_review_packet(db_path, markdown_path)
    json_packet = export_cluster_review_packet(db_path, json_path, output_format="json")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    direct_payload = cluster_review_packet_to_dict(json_packet)
    assert markdown_packet.review_item_count == 1
    assert "# AIResearch Cluster Review Packet" in markdown_path.read_text(encoding="utf-8")
    assert payload["review_item_count"] == 1
    assert payload["accept_candidate_count"] == 1
    assert payload["items"][0]["review_status"] == "pending"
    assert payload["items"][0]["review_notes"] == ""
    assert direct_payload["items"][0]["facts"][0]["paper_key"] in {"paper_a", "paper_b"}

