import json
from pathlib import Path

import pytest

from airesearch.artifact_ledger import extract_artifact_ledger
from airesearch.db import connect, init_db
from airesearch.fact_extraction import extract_research_facts
from airesearch.knowledge_graph import extract_paper_cards
from airesearch.paperpipe_sync import sync_paperpipe
from airesearch.research_bundle import _layout_table_display_quality, export_report_bundle
from airesearch.research_digest import DigestInputError


FIXTURE = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
EXPECTED_FILES = {
    "digest.md",
    "digest.json",
    "artifact-ledger.md",
    "artifact-ledger.json",
    "map.md",
    "map.json",
    "relations.md",
    "relations.json",
    "gap-analysis.md",
    "gap-analysis.json",
    "synthesis.md",
    "synthesis.json",
    "narrative.md",
    "narrative.json",
    "clusters.md",
    "clusters.json",
    "manifest.json",
    "index.md",
    "paper-assets",
    "paper-assets.json",
    "paper-layout-evidence.json",
    "layout-evidence-graph.json",
    "paper-blogs.json",
    "fact-translations.json",
}


def synced_fact_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    extract_artifact_ledger(db_path)
    extract_paper_cards(db_path)
    extract_research_facts(db_path, provider_name="fixture", fixture_path=FIXTURE)
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into research_fact_translations (
                fact_id, lang, statement, evidence_quote, model, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "zh",
                "Transformer 使用基于注意力的序列建模。",
                "中文证据。",
                "fixture",
                "2026-06-10T00:00:00+00:00",
                "2026-06-10T00:00:00+00:00",
            ),
        )
        stats_json = json.dumps(
            {
                "summary": {
                    "document_type": "digital",
                    "page_count": 8,
                    "block_count": 120,
                    "asset_count": 3,
                    "equation_blocks": 1,
                    "structured_table_blocks": 1,
                    "high_quality_table_blocks": 1,
                    "high_quality_equation_blocks": 1,
                    "high_quality_evidence_blocks": 2,
                    "block_types": {"text": 118, "interline_equation": 1, "table": 1},
                    "ocr": {
                        "mode": "auto",
                        "languages": "eng+chi_sim",
                        "available": True,
                        "pages_attempted": 1,
                        "pages_succeeded": 1,
                        "block_count": 4,
                        "engines": ["tesseract"],
                    },
                    "formula_ocr": {
                        "mode": "auto",
                        "configured": True,
                        "blocks_attempted": 1,
                        "blocks_succeeded": 1,
                        "blocks_rejected": 0,
                        "models": ["fixture-formula"],
                    },
                }
            },
            ensure_ascii=False,
        )
        run_id = conn.execute(
            """
            insert into paper_layout_runs (
                paper_key, provider, provider_version, backend, method, status,
                input_pdf_path, output_dir, artifact_json, stats_json, started_at, finished_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "1706_03762",
                "airesearch_layout",
                "fixture",
                "fixture",
                "fixture",
                "completed",
                "/tmp/1706_03762/paper.pdf",
                "/tmp/1706_03762/layout",
                "{}",
                stats_json,
                "2026-06-10T00:00:00+00:00",
                "2026-06-10T00:01:00+00:00",
            ),
        ).lastrowid
        conn.execute(
            """
            insert into paper_layout_blocks (
                paper_key, run_id, page_index, block_index, block_type,
                bbox_json, text, asset_path, metadata_json, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "1706_03762",
                run_id,
                2,
                4,
                "interline_equation",
                "[]",
                "Attention(Q,K,V)=softmax(QK^T)V",
                "assets/equation.png",
                json.dumps({"quality_score": 0.96, "equation_id": "eq-attn", "formula_ocr_status": "completed"}),
                "2026-06-10T00:01:00+00:00",
            ),
        )
        conn.execute(
            """
            insert into paper_layout_blocks (
                paper_key, run_id, page_index, block_index, block_type,
                bbox_json, text, asset_path, metadata_json, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "1706_03762",
                run_id,
                5,
                2,
                "table",
                "[]",
                "BLEU result table",
                "assets/table.png",
                json.dumps(
                    {
                        "quality_score": 0.91,
                        "caption": "Table 1. Benchmark results on translation tasks.",
                        "table_markdown": "| Model | BLEU |\n| --- | --- |\n| Transformer | 28.4 |",
                        "table_rows": [
                            ["Model", "BLEU", "Metric 3", "Metric 4", "Metric 5", "Metric 6", "Metric 7", "Metric 8", "Ignored"],
                            ["<Transformer>", "28.4", "3", "4", "5", "6", "7", "8", "9"],
                            *[[f"Model {index}", "x" * 180] for index in range(2, 14)],
                        ],
                        "table_reconstruction_method": "geometry+text",
                    }
                ),
                "2026-06-10T00:01:00+00:00",
            ),
        )
        conn.execute(
            """
            insert into paper_layout_blocks (
                paper_key, run_id, page_index, block_index, block_type,
                bbox_json, text, asset_path, metadata_json, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "1706_03762",
                run_id,
                6,
                3,
                "table",
                "[]",
                "Unstructured table-like text",
                "",
                json.dumps(
                    {
                        "quality_score": 0.42,
                        "caption": "Low-confidence parser fallback.",
                        "table_markdown": "Unstructured table-like text",
                        "table_reconstruction_method": "text_spacing_v1",
                    }
                ),
                "2026-06-10T00:01:00+00:00",
            ),
        )
        conn.commit()
    return db_path


def test_export_report_bundle_writes_manifest_index_and_reports(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    out_dir = tmp_path / "bundle"

    bundle = export_report_bundle(db_path, out_dir)

    assert bundle.paper_count == 1
    assert bundle.fact_count == 2
    assert bundle.report_count == 8
    assert bundle.artifact_count == 18
    assert {path.name for path in out_dir.iterdir()} == EXPECTED_FILES
    payload = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert payload["paper_count"] == 1
    assert payload["fact_count"] == 2
    assert payload["report_count"] == 8
    assert payload["artifact_count"] == 18
    assert payload["data_artifacts"] == [
        {
            "name": "layout-evidence-graph",
            "path": "layout-evidence-graph.json",
            "schema_version": "evidence-graph-v1",
        }
    ]
    assert [artifact["name"] for artifact in payload["artifacts"]] == [
        "digest",
        "artifact-ledger",
        "map",
        "relations",
        "gap-analysis",
        "synthesis",
        "narrative",
        "clusters",
    ]
    assert payload["artifacts"][1]["extra_counts"]["equation_count"] == 1
    assert payload["artifacts"][2]["extra_counts"]["item_count"] == 2
    assert payload["artifacts"][3]["extra_counts"]["relation_count"] == 0
    assert payload["artifacts"][6]["extra_counts"]["action_count"] == 1
    assert payload["artifacts"][7]["extra_counts"]["singleton_count"] == 2
    index = (out_dir / "index.md").read_text(encoding="utf-8")
    assert "# AIResearch Report Bundle" in index
    assert "[digest.md](digest.md)" in index
    assert "[manifest.json](manifest.json)" in index
    paper_assets = json.loads((out_dir / "paper-assets.json").read_text(encoding="utf-8"))
    assert paper_assets[0]["summary_zh_path"] == "paper-assets/1706_03762/summary.zh.md"
    assert paper_assets[0]["cover_path"].startswith("paper-assets/covers/1706_03762-")
    assert paper_assets[0]["cover_path"].endswith(".svg")
    fact_translations = json.loads((out_dir / "fact-translations.json").read_text(encoding="utf-8"))
    assert fact_translations[0]["lang"] == "zh"
    paper_blogs = json.loads((out_dir / "paper-blogs.json").read_text(encoding="utf-8"))
    assert paper_blogs["blog_count"] == 0
    assert paper_blogs["blogs"] == []
    layout_evidence = json.loads((out_dir / "paper-layout-evidence.json").read_text(encoding="utf-8"))
    assert layout_evidence[0]["paper_key"] == "1706_03762"
    assert layout_evidence[0]["summary"]["equation_blocks"] == 1
    assert layout_evidence[0]["ocr"]["block_count"] == 4
    assert layout_evidence[0]["summary"]["canonical_equation_count"] == 1
    assert layout_evidence[0]["equations"][0]["equation_id"] == "equation-1"
    assert layout_evidence[0]["equations"][0]["source_kind"] == "paperpipe_equations"
    assert layout_evidence[0]["equations"][0]["latex"] == "Attention(Q, K, V) = softmax(QK^T / sqrt(d_k))V"
    assert "Transformer | 28.4" in layout_evidence[0]["tables"][0]["table_markdown"]
    structured_table = layout_evidence[0]["tables"][0]
    assert structured_table["row_count"] == 14
    assert structured_table["column_count"] == 9
    assert len(structured_table["table_rows"]) == 12
    assert all(len(row) <= 12 for row in structured_table["table_rows"])
    assert max(len(cell) for row in structured_table["table_rows"] for cell in row) <= 160
    assert structured_table["preview_truncated"] is True
    assert structured_table["display_quality"] == "good"
    assert layout_evidence[0]["tables"][1]["display_quality"] == "fallback"
    assert layout_evidence[0]["tables"][1]["table_rows"] == []
    evidence_graph = json.loads((out_dir / "layout-evidence-graph.json").read_text(encoding="utf-8"))
    assert evidence_graph["schema_version"] == "evidence-graph-v1"
    assert evidence_graph["papers"][0]["paper_key"] == "1706_03762"
    assert len(evidence_graph["papers"][0]["facts"]) == 2
    assert len(evidence_graph["papers"][0]["evidence"]) == 2
    serialized_graph = json.dumps(evidence_graph, ensure_ascii=False)
    assert "/tmp/1706_03762" not in serialized_graph
    assert "table_html" not in serialized_graph


def test_layout_table_quality_rejects_rows_collapsed_into_first_cell():
    rows = [
        ["Model A 10.0 20.0 30.0 Model B 11.0 21.0 31.0 Model C 12.0 22.0 32.0", "", "", ""],
        ["", "11.0", "21.0", "31.0"],
        ["", "12.0", "22.0", "32.0"],
    ]

    quality = _layout_table_display_quality(
        caption="Table 2: Results.",
        rows=rows,
        row_count=3,
        column_count=4,
        reconstruction_method="pymupdf_table_lines",
        metadata={"quality_score": 0.99},
    )

    assert quality == "fallback"


def test_export_report_bundle_can_include_reviewed_clusters(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    out_dir = tmp_path / "bundle"
    review_path = tmp_path / "review.json"
    review_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-09T00:00:00+00:00",
                "paper_count": 1,
                "fact_count": 2,
                "mode": "token",
                "semantic_threshold": None,
                "items": [
                    {
                        "cluster_id": "method:attention-world",
                        "fact_type": "method",
                        "label": "Attention World",
                        "token_signature": ["attention", "world"],
                        "paper_count": 1,
                        "fact_count": 2,
                        "average_confidence": 0.91,
                        "recommended_status": "accept_candidate",
                        "review_status": "accepted",
                        "review_notes": "Confirmed.",
                        "rationale": "Cross-paper support.",
                        "facts": [
                            {
                                "paper_key": "1706_03762",
                                "paper_title": "Attention Is All You Need",
                                "year": 2017,
                                "fact_name": "Transformer",
                                "statement": "Uses attention.",
                                "confidence": 0.91,
                                "evidence_source_path": "/tmp/summary.md",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    bundle = export_report_bundle(db_path, out_dir, review_packet_path=review_path)

    assert bundle.report_count == 9
    assert bundle.artifact_count == 20
    assert (out_dir / "reviewed-clusters.md").exists()
    assert (out_dir / "reviewed-clusters.json").exists()
    payload = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert payload["artifacts"][3]["name"] == "relations"
    assert payload["artifacts"][-1]["name"] == "reviewed-clusters"
    assert payload["artifacts"][-1]["extra_counts"]["accepted_count"] == 1
    assert payload["artifacts"][-1]["extra_counts"]["accepted_fact_count"] == 2
    index = (out_dir / "index.md").read_text(encoding="utf-8")
    assert "[reviewed-clusters.md](reviewed-clusters.md)" in index


def test_export_report_bundle_requires_paper_cards(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"

    with pytest.raises(DigestInputError, match="paper_cards is empty"):
        export_report_bundle(db_path, tmp_path / "bundle")
