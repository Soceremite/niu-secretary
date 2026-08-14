from __future__ import annotations

import json
from pathlib import Path

from airesearch.db import connect, init_db
from airesearch.admin_server import (
    create_fact as admin_create_fact,
    delete_fact as admin_delete_fact,
    layout_detail as admin_layout_detail,
    update_fact as admin_update_fact,
)
from airesearch.layout_evidence_graph import (
    EXTRACTOR_NAME,
    extract_layout_evidence_graph,
    export_layout_evidence_graph,
    load_paper_evidence_graph,
)


NOW = "2026-08-10T00:00:00+00:00"


def _insert_fact(
    conn,
    *,
    paper_key: str,
    fact_type: str,
    statement: str,
    evidence_quote: str,
    source_path: str = "/tmp/summary.md",
) -> int:
    cursor = conn.execute(
        """
        insert into research_facts (
            paper_key, fact_type, name, statement, confidence, metadata_json,
            provider_name, extractor_version, created_at, updated_at
        ) values (?, ?, ?, ?, 0.91, '{}', 'fixture', 'test-v1', ?, ?)
        """,
        (paper_key, fact_type, fact_type.title(), statement, NOW, NOW),
    )
    fact_id = int(cursor.lastrowid)
    conn.execute(
        """
        insert into research_fact_provenance (
            fact_id, evidence_quote, evidence_artifact_type,
            evidence_source_path, created_at
        ) values (?, ?, 'summary', ?, ?)
        """,
        (fact_id, evidence_quote, source_path, NOW),
    )
    return fact_id


def _insert_block(
    conn,
    *,
    paper_key: str,
    run_id: int,
    block_index: int,
    block_type: str,
    text: str,
    quality: float,
    asset_path: str = "",
    metadata: dict | None = None,
) -> int:
    block_metadata = {
        "quality_score": quality,
        "quality_reasons": ["fixture"],
        "caption": text if block_type in {"image", "chart", "table"} else "",
        **(metadata or {}),
    }
    cursor = conn.execute(
        """
        insert into paper_layout_blocks (
            paper_key, run_id, page_index, block_index, block_type,
            bbox_json, text, asset_path, metadata_json, created_at
        ) values (?, ?, 1, ?, ?, '[10,20,300,220]', ?, ?, ?, ?)
        """,
        (
            paper_key,
            run_id,
            block_index,
            block_type,
            text,
            asset_path,
            json.dumps(block_metadata, sort_keys=True),
            NOW,
        ),
    )
    return int(cursor.lastrowid)


def graph_fixture_db(tmp_path: Path) -> tuple[Path, dict[str, int]]:
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into papers (
                paper_key, title, authors_json, year, venue, ids_json,
                paper_dir, meta_json, created_at, updated_at
            ) values ('paper_a', 'Evidence Graph Paper', '[]', 2026, '', '{}',
                      '/tmp/paper_a', '{}', ?, ?)
            """,
            (NOW, NOW),
        )
        conn.execute(
            """
            insert into kg_nodes (
                node_key, node_type, label, properties_json, extractor_name,
                source_paper_key, created_at, updated_at
            ) values ('paper:paper_a', 'paper', 'Original Paper Label',
                      '{"owner":"paper-card"}', 'deterministic_paper_card',
                      'paper_a', ?, ?)
            """,
            (NOW, NOW),
        )
        run = conn.execute(
            """
            insert into paper_layout_runs (
                paper_key, provider, provider_version, backend, method, status,
                input_pdf_path, output_dir, artifact_json, stats_json,
                started_at, finished_at
            ) values ('paper_a', 'airesearch_layout', 'v2', 'pymupdf', 'native',
                      'completed', '/private/paper.pdf', '/private/layout', '{}', '{}', ?, ?)
            """,
            (NOW, NOW),
        )
        run_id = int(run.lastrowid)
        figure_id = _insert_block(
            conn,
            paper_key="paper_a",
            run_id=run_id,
            block_index=1,
            block_type="image",
            text="Figure 2. The policy predicts complete future action trajectories from visual observations.",
            quality=0.92,
            asset_path="/private/layout/figure-2.png",
        )
        table_id = _insert_block(
            conn,
            paper_key="paper_a",
            run_id=run_id,
            block_index=2,
            block_type="table",
            text="Benchmark results on RoboKitchen show 91.2 success rate for the proposed model.",
            quality=0.88,
            metadata={
                "table_markdown": "| Model | RoboKitchen |\n|---|---|\n| Ours | 91.2 |",
                "table_html": "<table><tr><td>private raw html</td></tr></table>",
                "table_rows": [["Model", "RoboKitchen"], ["Ours", "91.2"]],
            },
        )
        equation_id = _insert_block(
            conn,
            paper_key="paper_a",
            run_id=run_id,
            block_index=3,
            block_type="interline_equation",
            text="L_total = L_action + lambda L_future",
            quality=0.84,
            metadata={"formula_ocr": {"latex": "L_{total}=L_{action}+\\lambda L_{future}"}},
        )
        low_quality_id = _insert_block(
            conn,
            paper_key="paper_a",
            run_id=run_id,
            block_index=4,
            block_type="image",
            text="The policy predicts complete future action trajectories from visual observations.",
            quality=0.31,
            asset_path="/private/layout/low-quality.png",
        )
        direct_fact_id = _insert_fact(
            conn,
            paper_key="paper_a",
            fact_type="method",
            statement="The objective combines action and future losses.",
            evidence_quote="This quote is intentionally different from the visual caption.",
            source_path=f"paper_layout_blocks:{equation_id}",
        )
        dataset_fact_id = _insert_fact(
            conn,
            paper_key="paper_a",
            fact_type="dataset",
            statement="The evaluation uses the RoboKitchen benchmark.",
            evidence_quote="Benchmark results on RoboKitchen show 91.2 success rate for the proposed model.",
        )
        limitation_fact_id = _insert_fact(
            conn,
            paper_key="paper_a",
            fact_type="limitation",
            statement="L total action lambda future",
            evidence_quote="L total action lambda future",
        )
        conn.commit()
    return db_path, {
        "run": run_id,
        "figure": figure_id,
        "table": table_id,
        "equation": equation_id,
        "low_quality": low_quality_id,
        "direct_fact": direct_fact_id,
        "dataset_fact": dataset_fact_id,
        "limitation_fact": limitation_fact_id,
    }


def test_extract_links_direct_provenance_and_compatible_text_matches(tmp_path: Path):
    db_path, ids = graph_fixture_db(tmp_path)

    result = extract_layout_evidence_graph(db_path, paper_key="paper_a")
    graph = load_paper_evidence_graph(db_path, "paper_a")

    assert result.papers_seen == 1
    assert result.fact_nodes_written == 3
    assert result.evidence_nodes_written == 3
    assert result.supported_by_edges == 2
    relations = {
        (relation["source_key"], relation["target_key"]): relation
        for relation in graph["relations"]
        if relation["relation"] == "supported_by"
    }
    direct_key = f"research_fact:paper_a:{ids['direct_fact']}"
    equation_key = f"layout_evidence:paper_a:{ids['run']}:{ids['equation']}"
    assert relations[(direct_key, equation_key)]["match_method"] == "direct_provenance"
    assert relations[(direct_key, equation_key)]["score"] == 1.0

    dataset_key = f"research_fact:paper_a:{ids['dataset_fact']}"
    table_key = f"layout_evidence:paper_a:{ids['run']}:{ids['table']}"
    assert relations[(dataset_key, table_key)]["match_method"] == "normalized_containment"
    assert not any(str(ids["low_quality"]) in item["key"] for item in graph["evidence"])
    limitation = next(item for item in graph["facts"] if item["key"].endswith(f":{ids['limitation_fact']}"))
    assert limitation["evidence"] == []
    assert limitation["linked"] is False


def test_extract_strict_token_match_is_deterministic_and_capped_at_three(tmp_path: Path):
    db_path, ids = graph_fixture_db(tmp_path)
    statement = "policy predicts complete future action trajectories visual observations"
    with connect(db_path) as conn:
        fact_id = _insert_fact(
            conn,
            paper_key="paper_a",
            fact_type="claim",
            statement=statement,
            evidence_quote="policy predicts complete future action trajectories reliably",
        )
        for block_index in range(10, 14):
            _insert_block(
                conn,
                paper_key="paper_a",
                run_id=ids["run"],
                block_index=block_index,
                block_type="chart",
                text=f"Visual observations show the policy reliably predicts complete future action trajectories result {block_index}.",
                quality=0.8 + (block_index - 10) * 0.01,
                asset_path=f"/private/layout/chart-{block_index}.png",
            )
        conn.commit()

    first = extract_layout_evidence_graph(db_path, paper_key="paper_a")
    first_graph = load_paper_evidence_graph(db_path, "paper_a")
    second = extract_layout_evidence_graph(db_path, paper_key="paper_a")
    second_graph = load_paper_evidence_graph(db_path, "paper_a")

    fact = next(item for item in first_graph["facts"] if item["key"].endswith(f":{fact_id}"))
    assert len(fact["evidence"]) == 3
    assert {item["match_method"] for item in fact["evidence"]} == {"strict_token"}
    assert [item["evidence_key"] for item in fact["evidence"]] == [
        item["evidence_key"] for item in second_graph["facts"][-1]["evidence"]
    ]
    assert first.fact_nodes_written == second.fact_nodes_written
    assert first.evidence_nodes_written == second.evidence_nodes_written
    assert first.supported_by_edges == second.supported_by_edges


def test_extract_deduplicates_same_page_evidence_with_identical_content(tmp_path: Path):
    db_path, ids = graph_fixture_db(tmp_path)
    caption = "Figure 9. Alignment stability remains consistent across every evaluation setting."
    with connect(db_path) as conn:
        fact_id = _insert_fact(
            conn,
            paper_key="paper_a",
            fact_type="claim",
            statement="Alignment stability remains consistent across every evaluation setting.",
            evidence_quote=caption,
        )
        duplicate_ids = [
            _insert_block(
                conn,
                paper_key="paper_a",
                run_id=ids["run"],
                block_index=block_index,
                block_type="chart",
                text=caption,
                quality=0.91,
                asset_path=f"/private/layout/figure-9-fragment-{block_index}.png",
            )
            for block_index in range(20, 23)
        ]
        conn.commit()

    extract_layout_evidence_graph(db_path, paper_key="paper_a")
    graph = load_paper_evidence_graph(db_path, "paper_a")

    fact = next(item for item in graph["facts"] if item["fact_id"] == fact_id)
    assert len(fact["evidence"]) == 1
    assert fact["evidence"][0]["evidence_key"].endswith(f":{duplicate_ids[0]}")


def test_extractor_preserves_shared_paper_node_and_other_extractors(tmp_path: Path):
    db_path, _ = graph_fixture_db(tmp_path)
    extract_layout_evidence_graph(db_path, paper_key="paper_a")
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into kg_nodes (
                node_key, node_type, label, properties_json, extractor_name,
                source_paper_key, created_at, updated_at
            ) values ('external:paper_a', 'external', 'Keep Me', '{}',
                      'another_extractor', 'paper_a', ?, ?)
            """,
            (NOW, NOW),
        )
        conn.commit()

    extract_layout_evidence_graph(db_path, paper_key="paper_a")

    with connect(db_path) as conn:
        paper = conn.execute("select * from kg_nodes where node_key = 'paper:paper_a'").fetchone()
        external = conn.execute("select * from kg_nodes where node_key = 'external:paper_a'").fetchone()
        owned = conn.execute(
            "select count(*) as count from kg_nodes where extractor_name = ? and source_paper_key = 'paper_a'",
            (EXTRACTOR_NAME,),
        ).fetchone()["count"]
    assert paper["label"] == "Original Paper Label"
    assert json.loads(paper["properties_json"]) == {"owner": "paper-card"}
    assert paper["extractor_name"] == "deterministic_paper_card"
    assert external["label"] == "Keep Me"
    assert owned == 6


def test_public_projection_is_bounded_and_redacted(tmp_path: Path):
    db_path, _ = graph_fixture_db(tmp_path)
    with connect(db_path) as conn:
        for index in range(30):
            _insert_fact(
                conn,
                paper_key="paper_a",
                fact_type="claim",
                statement=f"Public projection claim {index} with a deliberately long statement " + ("x" * 300),
                evidence_quote=f"unmatched quote {index}",
            )
        conn.commit()
    extract_layout_evidence_graph(db_path, paper_key="paper_a")

    graph = load_paper_evidence_graph(db_path, "paper_a", public=True)

    assert graph["schema_version"] == "evidence-graph-v1"
    assert len(graph["facts"]) == 24
    assert len(graph["evidence"]) <= 48
    assert len(graph["relations"]) <= 72
    assert all(len(fact["statement"]) <= 240 for fact in graph["facts"])
    serialized = json.dumps(graph, ensure_ascii=False)
    assert "/private/" not in serialized
    assert "<table>" not in serialized
    assert "properties_json" not in serialized
    assert "provenance" not in graph["facts"][0]


def test_export_writes_stable_public_graphs_for_all_papers(tmp_path: Path):
    db_path, _ = graph_fixture_db(tmp_path)
    out_path = tmp_path / "layout-evidence-graph.json"
    extract_layout_evidence_graph(db_path)

    count = export_layout_evidence_graph(db_path, out_path)
    first = out_path.read_text(encoding="utf-8")
    export_layout_evidence_graph(db_path, out_path)

    payload = json.loads(first)
    assert count == 1
    assert payload["schema_version"] == "evidence-graph-v1"
    assert payload["papers"][0]["paper_key"] == "paper_a"
    assert out_path.read_text(encoding="utf-8") == first


def test_admin_layout_detail_exposes_diagnostic_evidence_graph(tmp_path: Path):
    db_path, _ = graph_fixture_db(tmp_path)
    extract_layout_evidence_graph(db_path, paper_key="paper_a")

    detail = admin_layout_detail(db_path, "paper_a")

    graph = detail["evidence_graph"]
    assert graph["schema_version"] == "evidence-graph-v1"
    assert graph["summary"]["fact_count"] == 3
    assert graph["summary"]["supported_relation_count"] == 2
    relation = next(item for item in graph["relations"] if item["relation"] == "supported_by")
    assert relation["properties"]["match_method"]
    assert relation["provenance"]
    assert graph["facts"][0]["provenance"]


def test_admin_fact_mutations_refresh_the_affected_paper_graph(tmp_path: Path):
    db_path, ids = graph_fixture_db(tmp_path)
    extract_layout_evidence_graph(db_path, paper_key="paper_a")

    updated = admin_update_fact(
        db_path,
        ids["dataset_fact"],
        {
            "fact_type": "dataset",
            "name": "Updated dataset",
            "statement": "The updated evaluation uses RoboKitchen.",
            "confidence": 0.93,
        },
    )
    created = admin_create_fact(
        db_path,
        "paper_a",
        {
            "fact_type": "claim",
            "name": "Admin claim",
            "statement": "An administrator-authored grounded claim.",
            "confidence": 0.81,
        },
    )
    after_create = load_paper_evidence_graph(db_path, "paper_a")
    deleted = admin_delete_fact(db_path, int(created["id"]))
    after_delete = load_paper_evidence_graph(db_path, "paper_a")

    assert updated["graph_refresh"]["status"] == "completed"
    updated_fact = next(item for item in after_create["facts"] if item["fact_id"] == ids["dataset_fact"])
    assert updated_fact["statement"] == "The updated evaluation uses RoboKitchen."
    assert created["graph_refresh"]["status"] == "completed"
    assert any(item["fact_id"] == created["id"] for item in after_create["facts"])
    assert deleted["graph_refresh"]["status"] == "completed"
    assert not any(item["fact_id"] == created["id"] for item in after_delete["facts"])
