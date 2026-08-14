from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import stable_json


EXTRACTOR_NAME = "layout_evidence_graph"
EXTRACTOR_VERSION = "2026-08-10.1"
SCHEMA_VERSION = "evidence-graph-v1"

ELIGIBLE_BLOCK_TYPES = {"image", "chart", "table", "interline_equation"}
EVIDENCE_NODE_TYPES = {
    "image": "layout_figure",
    "chart": "layout_figure",
    "table": "layout_table",
    "interline_equation": "layout_equation",
}
FACT_EVIDENCE_COMPATIBILITY = {
    "dataset": {"layout_figure", "layout_table"},
    "benchmark": {"layout_figure", "layout_table"},
    "method": {"layout_figure", "layout_table", "layout_equation"},
    "claim": {"layout_figure", "layout_table", "layout_equation"},
    "limitation": {"layout_figure", "layout_table"},
}
MATCH_PRIORITY = {
    "direct_provenance": 0,
    "normalized_containment": 1,
    "strict_token": 2,
}

PUBLIC_FACT_LIMIT = 24
PUBLIC_EVIDENCE_LIMIT = 48
PUBLIC_RELATION_LIMIT = 72
ADMIN_NODE_LIMIT = 200
ADMIN_RELATION_LIMIT = 200
MAX_EVIDENCE_PER_FACT = 3
PUBLIC_PREVIEW_LIMIT = 240


@dataclass(frozen=True)
class LayoutEvidenceGraphResult:
    papers_seen: int
    fact_nodes_written: int
    evidence_nodes_written: int
    edges_written: int
    supported_by_edges: int
    provenance_written: int


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _json_loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _compact(value: Any) -> str:
    return " ".join(str(value or "").split())


def _clip(value: Any, limit: int) -> str:
    text = _compact(value)
    return text if len(text) <= limit else text[: max(0, limit - 1)].rstrip() + "…"


def _normalize_text(value: Any) -> str:
    text = _compact(value).casefold()
    text = re.sub(r"[^\w\u3400-\u9fff]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def _tokens(value: Any) -> set[str]:
    normalized = _normalize_text(value)
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+(?:_[a-z0-9]+)*", normalized)
        if len(token) >= 2
    }
    for sequence in re.findall(r"[\u3400-\u9fff]+", normalized):
        if len(sequence) == 1:
            tokens.add(sequence)
        else:
            tokens.update(sequence[index : index + 2] for index in range(len(sequence) - 1))
    return tokens


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _formula_text(value: Any) -> str:
    if isinstance(value, dict):
        return _compact(value.get("latex") or value.get("text") or value.get("normalized_text"))
    return _compact(value)


def _flatten_table_rows(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    cells: list[str] = []
    for row in value:
        if isinstance(row, list):
            cells.extend(_compact(cell) for cell in row if _compact(cell))
    return " ".join(cells)


def _evidence_text(row: Any, metadata: dict[str, Any]) -> str:
    parts = [
        metadata.get("caption"),
        row["text"],
        metadata.get("table_markdown"),
        _flatten_table_rows(metadata.get("table_rows")),
        _formula_text(metadata.get("formula_ocr")),
    ]
    seen: set[str] = set()
    values: list[str] = []
    for part in parts:
        text = _compact(part)
        if text and text not in seen:
            seen.add(text)
            values.append(text)
    return " ".join(values)


def _evidence_preview(row: Any, metadata: dict[str, Any]) -> str:
    return _compact(
        metadata.get("caption")
        or metadata.get("table_markdown")
        or _formula_text(metadata.get("formula_ocr"))
        or row["text"]
    )


def _usable_evidence(row: Any, metadata: dict[str, Any]) -> bool:
    block_type = str(row["block_type"] or "")
    if block_type in {"image", "chart"}:
        return bool(_compact(row["asset_path"]) or _evidence_preview(row, metadata))
    if block_type == "table":
        return bool(
            _compact(row["text"])
            or _compact(metadata.get("table_markdown"))
            or _flatten_table_rows(metadata.get("table_rows"))
        )
    if block_type == "interline_equation":
        return bool(_compact(row["text"]) or _formula_text(metadata.get("formula_ocr")))
    return False


def _quality_score(metadata: dict[str, Any]) -> float:
    return max(0.0, min(1.0, _safe_float(metadata.get("quality_score"))))


def _fact_node_key(paper_key: str, fact_id: int) -> str:
    return f"research_fact:{paper_key}:{fact_id}"


def _evidence_node_key(paper_key: str, run_id: int, block_id: int) -> str:
    return f"layout_evidence:{paper_key}:{run_id}:{block_id}"


def _edge_key(source_key: str, relation: str, target_key: str) -> str:
    return f"{source_key}|{relation}|{target_key}"


def _insert_shared_paper_node(conn: Any, paper: Any, now: str) -> None:
    paper_key = str(paper["paper_key"])
    conn.execute(
        """
        insert or ignore into kg_nodes (
            node_key, node_type, label, properties_json, extractor_name,
            source_paper_key, created_at, updated_at
        ) values (?, 'paper', ?, ?, 'deterministic_paper_card', ?, ?, ?)
        """,
        (
            f"paper:{paper_key}",
            _compact(paper["title"]) or paper_key,
            stable_json({"paper_key": paper_key, "year": paper["year"]}),
            paper_key,
            now,
            now,
        ),
    )


def _upsert_owned_node(
    conn: Any,
    *,
    node_key: str,
    node_type: str,
    label: str,
    properties: dict[str, Any],
    paper_key: str,
    now: str,
) -> None:
    conn.execute(
        """
        insert into kg_nodes (
            node_key, node_type, label, properties_json, extractor_name,
            source_paper_key, created_at, updated_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(node_key) do update set
            node_type = excluded.node_type,
            label = excluded.label,
            properties_json = excluded.properties_json,
            extractor_name = excluded.extractor_name,
            source_paper_key = excluded.source_paper_key,
            updated_at = excluded.updated_at
        """,
        (node_key, node_type, label, stable_json(properties), EXTRACTOR_NAME, paper_key, now, now),
    )


def _upsert_owned_edge(
    conn: Any,
    *,
    source_key: str,
    relation: str,
    target_key: str,
    properties: dict[str, Any],
    paper_key: str,
    now: str,
) -> None:
    conn.execute(
        """
        insert into kg_edges (
            source_key, relation, target_key, properties_json, extractor_name,
            source_paper_key, created_at, updated_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(source_key, relation, target_key, extractor_name) do update set
            properties_json = excluded.properties_json,
            source_paper_key = excluded.source_paper_key,
            updated_at = excluded.updated_at
        """,
        (source_key, relation, target_key, stable_json(properties), EXTRACTOR_NAME, paper_key, now, now),
    )


def _add_provenance(
    conn: Any,
    *,
    entity_type: str,
    entity_key: str,
    source_table: str,
    source_key: str,
    source_field: str,
    confidence: float,
    paper_key: str,
    now: str,
) -> None:
    conn.execute(
        """
        insert or ignore into kg_provenance (
            entity_type, entity_key, source_table, source_key, source_field,
            confidence, extractor_name, source_paper_key, created_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity_type,
            entity_key,
            source_table,
            source_key,
            source_field,
            confidence,
            EXTRACTOR_NAME,
            paper_key,
            now,
        ),
    )


def _clear_owned_graph(conn: Any, paper_key: str) -> None:
    conn.execute(
        "delete from kg_provenance where source_paper_key = ? and extractor_name = ?",
        (paper_key, EXTRACTOR_NAME),
    )
    conn.execute(
        "delete from kg_edges where source_paper_key = ? and extractor_name = ?",
        (paper_key, EXTRACTOR_NAME),
    )
    conn.execute(
        """
        delete from kg_nodes
        where source_paper_key = ? and extractor_name = ? and node_type != 'paper'
        """,
        (paper_key, EXTRACTOR_NAME),
    )


def _load_papers(conn: Any, paper_key: str | None, limit: int | None) -> list[Any]:
    sql = "select paper_key, title, year from papers"
    params: list[Any] = []
    if paper_key:
        sql += " where paper_key = ?"
        params.append(paper_key)
    sql += " order by paper_key"
    if limit is not None:
        sql += " limit ?"
        params.append(max(0, int(limit)))
    return list(conn.execute(sql, params).fetchall())


def _latest_layout_run(conn: Any, paper_key: str) -> Any:
    return conn.execute(
        """
        select * from paper_layout_runs
        where paper_key = ? and status in ('completed', 'reused')
        order by coalesce(finished_at, started_at) desc, id desc
        limit 1
        """,
        (paper_key,),
    ).fetchone()


def _load_facts(conn: Any, paper_key: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "select * from research_facts where paper_key = ? order by id",
        (paper_key,),
    ).fetchall()
    facts: list[dict[str, Any]] = []
    for row in rows:
        provenance = [
            dict(item)
            for item in conn.execute(
                """
                select * from research_fact_provenance
                where fact_id = ? order by id
                """,
                (row["id"],),
            ).fetchall()
        ]
        facts.append({"row": row, "provenance": provenance})
    return facts


def _load_evidence(conn: Any, paper_key: str, run_id: int | None) -> list[dict[str, Any]]:
    if run_id is None:
        return []
    rows = conn.execute(
        """
        select * from paper_layout_blocks
        where paper_key = ? and run_id = ?
          and block_type in ('image', 'chart', 'table', 'interline_equation')
        order by page_index, block_index, id
        """,
        (paper_key, run_id),
    ).fetchall()
    evidence: list[dict[str, Any]] = []
    for row in rows:
        metadata = _json_loads(row["metadata_json"], {})
        if not isinstance(metadata, dict):
            metadata = {}
        quality = _quality_score(metadata)
        if quality < 0.55 or not _usable_evidence(row, metadata):
            continue
        evidence.append(
            {
                "row": row,
                "metadata": metadata,
                "quality_score": quality,
                "node_type": EVIDENCE_NODE_TYPES[str(row["block_type"])],
                "match_text": _evidence_text(row, metadata),
            }
        )
    return evidence


def _direct_block_ids(provenance: Iterable[dict[str, Any]]) -> set[int]:
    block_ids: set[int] = set()
    for item in provenance:
        match = re.fullmatch(r"paper_layout_blocks:(\d+)", _compact(item.get("evidence_source_path")))
        if match:
            block_ids.add(int(match.group(1)))
    return block_ids


def _compatible(fact_type: str, evidence_type: str) -> bool:
    return evidence_type in FACT_EVIDENCE_COMPATIBILITY.get(fact_type, set())


def _text_candidates(fact: dict[str, Any]) -> list[str]:
    row = fact["row"]
    values = [item.get("evidence_quote") for item in fact["provenance"]]
    values.extend([row["statement"], row["name"]])
    seen: set[str] = set()
    candidates: list[str] = []
    for value in values:
        normalized = _normalize_text(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)
    return candidates


def _match_fact_to_evidence(fact: dict[str, Any], evidence: dict[str, Any]) -> tuple[str, float] | None:
    row = fact["row"]
    evidence_row = evidence["row"]
    if int(evidence_row["id"]) in _direct_block_ids(fact["provenance"]):
        return "direct_provenance", 1.0
    if not _compatible(str(row["fact_type"]), str(evidence["node_type"])):
        return None
    if float(evidence["quality_score"]) < 0.72:
        return None

    evidence_normalized = _normalize_text(evidence["match_text"])
    evidence_tokens = _tokens(evidence_normalized)
    best_token_score = 0.0
    for source in _text_candidates(fact):
        if len(source) >= 24 and len(evidence_normalized) >= 24:
            if source in evidence_normalized or evidence_normalized in source:
                return "normalized_containment", 0.96
        source_tokens = _tokens(source)
        if not source_tokens or not evidence_tokens:
            continue
        shared = source_tokens & evidence_tokens
        union = source_tokens | evidence_tokens
        source_coverage = len(shared) / len(source_tokens)
        jaccard = len(shared) / len(union)
        if len(shared) >= 4 and source_coverage >= 0.72 and jaccard >= 0.30:
            best_token_score = max(best_token_score, (source_coverage + jaccard) / 2)
    if best_token_score:
        return "strict_token", round(best_token_score, 4)
    return None


def _rank_matches(fact: dict[str, Any], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for item in evidence:
        match = _match_fact_to_evidence(fact, item)
        if match is None:
            continue
        method, score = match
        matches.append({"evidence": item, "method": method, "score": score})
    matches.sort(
        key=lambda item: (
            MATCH_PRIORITY[item["method"]],
            -float(item["score"]),
            -float(item["evidence"]["quality_score"]),
            int(item["evidence"]["row"]["page_index"]),
            int(item["evidence"]["row"]["block_index"]),
            int(item["evidence"]["row"]["id"]),
        )
    )
    ranked: list[dict[str, Any]] = []
    seen_content: set[tuple[Any, ...]] = set()
    for match in matches:
        item = match["evidence"]
        row = item["row"]
        normalized = _normalize_text(item["match_text"])
        signature = (
            str(item["node_type"]),
            int(row["page_index"]),
            normalized,
        ) if normalized else ("block", int(row["id"]))
        if signature in seen_content:
            continue
        seen_content.add(signature)
        ranked.append(match)
        if len(ranked) == MAX_EVIDENCE_PER_FACT:
            break
    return ranked


def _write_paper_graph(conn: Any, paper: Any, now: str) -> tuple[int, int, int, int, int]:
    paper_key = str(paper["paper_key"])
    paper_node_key = f"paper:{paper_key}"
    _clear_owned_graph(conn, paper_key)
    _insert_shared_paper_node(conn, paper, now)

    facts = _load_facts(conn, paper_key)
    run = _latest_layout_run(conn, paper_key)
    run_id = int(run["id"]) if run is not None else None
    evidence = _load_evidence(conn, paper_key, run_id)
    edge_count = 0
    supported_count = 0

    for fact in facts:
        row = fact["row"]
        fact_id = int(row["id"])
        node_key = _fact_node_key(paper_key, fact_id)
        _upsert_owned_node(
            conn,
            node_key=node_key,
            node_type="research_fact",
            label=_clip(row["name"] or row["statement"], 180),
            properties={
                "fact_id": fact_id,
                "paper_key": paper_key,
                "fact_type": row["fact_type"],
                "name": row["name"],
                "statement": row["statement"],
                "confidence": row["confidence"],
                "metadata": _json_loads(row["metadata_json"], {}),
                "provider_name": row["provider_name"],
                "extractor_version": row["extractor_version"],
            },
            paper_key=paper_key,
            now=now,
        )
        _add_provenance(
            conn,
            entity_type="node",
            entity_key=node_key,
            source_table="research_facts",
            source_key=str(fact_id),
            source_field="statement",
            confidence=_safe_float(row["confidence"], 1.0),
            paper_key=paper_key,
            now=now,
        )
        for provenance in fact["provenance"]:
            _add_provenance(
                conn,
                entity_type="node",
                entity_key=node_key,
                source_table="research_fact_provenance",
                source_key=str(provenance["id"]),
                source_field="evidence_quote",
                confidence=_safe_float(row["confidence"], 1.0),
                paper_key=paper_key,
                now=now,
            )
        _upsert_owned_edge(
            conn,
            source_key=paper_node_key,
            relation="has_research_fact",
            target_key=node_key,
            properties={"fact_id": fact_id, "fact_type": row["fact_type"]},
            paper_key=paper_key,
            now=now,
        )
        _add_provenance(
            conn,
            entity_type="edge",
            entity_key=_edge_key(paper_node_key, "has_research_fact", node_key),
            source_table="research_facts",
            source_key=str(fact_id),
            source_field="fact_type",
            confidence=_safe_float(row["confidence"], 1.0),
            paper_key=paper_key,
            now=now,
        )
        edge_count += 1

    for item in evidence:
        row = item["row"]
        metadata = item["metadata"]
        block_id = int(row["id"])
        node_key = _evidence_node_key(paper_key, int(row["run_id"]), block_id)
        preview = _evidence_preview(row, metadata)
        _upsert_owned_node(
            conn,
            node_key=node_key,
            node_type=str(item["node_type"]),
            label=_clip(preview or f"{row['block_type']} page {int(row['page_index']) + 1}", 180),
            properties={
                "paper_key": paper_key,
                "run_id": int(row["run_id"]),
                "block_id": block_id,
                "block_type": row["block_type"],
                "evidence_type": item["node_type"],
                "page_index": int(row["page_index"]),
                "page_number": int(row["page_index"]) + 1,
                "block_index": int(row["block_index"]),
                "bbox": _json_loads(row["bbox_json"], []),
                "text": row["text"],
                "preview": preview,
                "caption": _compact(metadata.get("caption")),
                "asset_path": row["asset_path"],
                "quality_score": item["quality_score"],
                "quality_reasons": metadata.get("quality_reasons") or [],
                "metadata": metadata,
            },
            paper_key=paper_key,
            now=now,
        )
        _add_provenance(
            conn,
            entity_type="node",
            entity_key=node_key,
            source_table="paper_layout_blocks",
            source_key=str(block_id),
            source_field="metadata_json",
            confidence=float(item["quality_score"]),
            paper_key=paper_key,
            now=now,
        )
        _upsert_owned_edge(
            conn,
            source_key=paper_node_key,
            relation="has_layout_evidence",
            target_key=node_key,
            properties={
                "run_id": int(row["run_id"]),
                "block_id": block_id,
                "evidence_type": item["node_type"],
                "quality_score": item["quality_score"],
            },
            paper_key=paper_key,
            now=now,
        )
        _add_provenance(
            conn,
            entity_type="edge",
            entity_key=_edge_key(paper_node_key, "has_layout_evidence", node_key),
            source_table="paper_layout_blocks",
            source_key=str(block_id),
            source_field="block_type",
            confidence=float(item["quality_score"]),
            paper_key=paper_key,
            now=now,
        )
        edge_count += 1

    for fact in facts:
        fact_row = fact["row"]
        fact_key = _fact_node_key(paper_key, int(fact_row["id"]))
        for match in _rank_matches(fact, evidence):
            evidence_item = match["evidence"]
            evidence_row = evidence_item["row"]
            evidence_key = _evidence_node_key(
                paper_key,
                int(evidence_row["run_id"]),
                int(evidence_row["id"]),
            )
            properties = {
                "match_method": match["method"],
                "score": match["score"],
                "fact_type": fact_row["fact_type"],
                "evidence_type": evidence_item["node_type"],
                "evidence_quality": evidence_item["quality_score"],
            }
            _upsert_owned_edge(
                conn,
                source_key=fact_key,
                relation="supported_by",
                target_key=evidence_key,
                properties=properties,
                paper_key=paper_key,
                now=now,
            )
            relation_key = _edge_key(fact_key, "supported_by", evidence_key)
            _add_provenance(
                conn,
                entity_type="edge",
                entity_key=relation_key,
                source_table="research_facts",
                source_key=str(fact_row["id"]),
                source_field="statement",
                confidence=float(match["score"]),
                paper_key=paper_key,
                now=now,
            )
            _add_provenance(
                conn,
                entity_type="edge",
                entity_key=relation_key,
                source_table="paper_layout_blocks",
                source_key=str(evidence_row["id"]),
                source_field="text",
                confidence=float(match["score"]),
                paper_key=paper_key,
                now=now,
            )
            edge_count += 1
            supported_count += 1

    provenance_count = int(
        conn.execute(
            """
            select count(*) as count from kg_provenance
            where source_paper_key = ? and extractor_name = ?
            """,
            (paper_key, EXTRACTOR_NAME),
        ).fetchone()["count"]
    )
    return len(facts), len(evidence), edge_count, supported_count, provenance_count


def extract_layout_evidence_graph(
    db_path: Path,
    paper_key: str | None = None,
    limit: int | None = None,
) -> LayoutEvidenceGraphResult:
    init_db(db_path)
    with connect(db_path) as conn:
        papers = _load_papers(conn, paper_key, limit)
        fact_nodes = evidence_nodes = edges = supported = provenance = 0
        now = _utc_now()
        for paper in papers:
            counts = _write_paper_graph(conn, paper, now)
            fact_nodes += counts[0]
            evidence_nodes += counts[1]
            edges += counts[2]
            supported += counts[3]
            provenance += counts[4]
        conn.commit()
    return LayoutEvidenceGraphResult(
        papers_seen=len(papers),
        fact_nodes_written=fact_nodes,
        evidence_nodes_written=evidence_nodes,
        edges_written=edges,
        supported_by_edges=supported,
        provenance_written=provenance,
    )


def _load_provenance(conn: Any, paper_key: str) -> dict[str, list[dict[str, Any]]]:
    rows = conn.execute(
        """
        select entity_key, source_table, source_key, source_field, confidence
        from kg_provenance
        where source_paper_key = ? and extractor_name = ?
        order by entity_key, source_table, source_key, source_field, id
        """,
        (paper_key, EXTRACTOR_NAME),
    ).fetchall()
    result: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        result.setdefault(str(row["entity_key"]), []).append(
            {
                "source_table": row["source_table"],
                "source_key": row["source_key"],
                "source_field": row["source_field"],
                "confidence": row["confidence"],
            }
        )
    return result


def _fact_payload(row: Any, properties: dict[str, Any], provenance: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "key": row["node_key"],
        "fact_id": properties.get("fact_id"),
        "fact_type": properties.get("fact_type") or "",
        "name": _compact(properties.get("name")),
        "statement": _compact(properties.get("statement")),
        "confidence": _safe_float(properties.get("confidence")),
        "provider_name": _compact(properties.get("provider_name")),
        "extractor_version": _compact(properties.get("extractor_version")),
        "metadata": properties.get("metadata") if isinstance(properties.get("metadata"), dict) else {},
        "provenance": provenance,
        "evidence": [],
        "linked": False,
    }


def _evidence_payload(row: Any, properties: dict[str, Any], provenance: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "key": row["node_key"],
        "evidence_type": properties.get("evidence_type") or row["node_type"],
        "block_type": properties.get("block_type") or "",
        "run_id": properties.get("run_id"),
        "block_id": properties.get("block_id"),
        "page_index": properties.get("page_index"),
        "page_number": properties.get("page_number"),
        "block_index": properties.get("block_index"),
        "preview": _compact(properties.get("preview") or properties.get("text")),
        "caption": _compact(properties.get("caption")),
        "text": _compact(properties.get("text")),
        "quality_score": _safe_float(properties.get("quality_score")),
        "quality_reasons": properties.get("quality_reasons") if isinstance(properties.get("quality_reasons"), list) else [],
        "bbox": properties.get("bbox") if isinstance(properties.get("bbox"), list) else [],
        "asset_path": _compact(properties.get("asset_path")),
        "metadata": properties.get("metadata") if isinstance(properties.get("metadata"), dict) else {},
        "provenance": provenance,
    }


def _relation_payload(row: Any, provenance: list[dict[str, Any]]) -> dict[str, Any]:
    properties = _json_loads(row["properties_json"], {})
    if not isinstance(properties, dict):
        properties = {}
    return {
        "source_key": row["source_key"],
        "relation": row["relation"],
        "target_key": row["target_key"],
        "match_method": properties.get("match_method") or "",
        "score": _safe_float(properties.get("score")),
        "properties": properties,
        "provenance": provenance,
    }


def _public_fact(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": item["key"],
        "fact_id": item["fact_id"],
        "fact_type": item["fact_type"],
        "name": _clip(item["name"], PUBLIC_PREVIEW_LIMIT),
        "statement": _clip(item["statement"], PUBLIC_PREVIEW_LIMIT),
        "confidence": item["confidence"],
        "evidence": item["evidence"],
        "linked": item["linked"],
    }


def _public_evidence(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": item["key"],
        "evidence_type": item["evidence_type"],
        "block_type": item["block_type"],
        "run_id": item["run_id"],
        "block_id": item["block_id"],
        "page_index": item["page_index"],
        "page_number": item["page_number"],
        "block_index": item["block_index"],
        "preview": _clip(item["preview"], PUBLIC_PREVIEW_LIMIT),
        "caption": _clip(item["caption"], PUBLIC_PREVIEW_LIMIT),
        "quality_score": item["quality_score"],
    }


def _public_relation(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_key": item["source_key"],
        "relation": item["relation"],
        "target_key": item["target_key"],
        "match_method": item["match_method"],
        "score": item["score"],
    }


def load_paper_evidence_graph(db_path: Path, paper_key: str, public: bool = False) -> dict[str, Any]:
    init_db(db_path)
    with connect(db_path) as conn:
        paper_exists = conn.execute("select 1 from papers where paper_key = ?", (paper_key,)).fetchone() is not None
        provenance = _load_provenance(conn, paper_key)
        node_rows = conn.execute(
            """
            select * from kg_nodes
            where source_paper_key = ? and extractor_name = ? and node_type != 'paper'
            order by case node_type when 'research_fact' then 0 else 1 end, node_key
            """,
            (paper_key, EXTRACTOR_NAME),
        ).fetchall()
        edge_rows = conn.execute(
            """
            select * from kg_edges
            where source_paper_key = ? and extractor_name = ?
            order by case relation when 'supported_by' then 0 when 'has_research_fact' then 1 else 2 end,
                     source_key, target_key, id
            """,
            (paper_key, EXTRACTOR_NAME),
        ).fetchall()

    facts: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    for row in node_rows:
        properties = _json_loads(row["properties_json"], {})
        if not isinstance(properties, dict):
            properties = {}
        node_provenance = provenance.get(str(row["node_key"]), [])
        if row["node_type"] == "research_fact":
            facts.append(_fact_payload(row, properties, node_provenance))
        else:
            evidence.append(_evidence_payload(row, properties, node_provenance))

    relations = [
        _relation_payload(
            row,
            provenance.get(_edge_key(str(row["source_key"]), str(row["relation"]), str(row["target_key"])), []),
        )
        for row in edge_rows
    ]
    total_fact_count = len(facts)
    total_evidence_count = len(evidence)
    total_relation_count = len(relations)

    fact_limit = PUBLIC_FACT_LIMIT if public else ADMIN_NODE_LIMIT
    evidence_limit = PUBLIC_EVIDENCE_LIMIT if public else ADMIN_NODE_LIMIT
    relation_limit = PUBLIC_RELATION_LIMIT if public else ADMIN_RELATION_LIMIT
    facts = facts[:fact_limit]
    fact_keys = {item["key"] for item in facts}

    supported = [
        relation
        for relation in relations
        if relation["relation"] == "supported_by" and relation["source_key"] in fact_keys
    ]
    linked_evidence_keys = {relation["target_key"] for relation in supported}
    evidence.sort(key=lambda item: (item["key"] not in linked_evidence_keys, item["key"]))
    evidence = evidence[:evidence_limit]
    evidence_keys = {item["key"] for item in evidence}
    relations = [
        relation
        for relation in relations
        if (
            relation["relation"] == "supported_by"
            and relation["source_key"] in fact_keys
            and relation["target_key"] in evidence_keys
        )
        or (
            relation["relation"] == "has_research_fact" and relation["target_key"] in fact_keys
        )
        or (
            relation["relation"] == "has_layout_evidence" and relation["target_key"] in evidence_keys
        )
    ][:relation_limit]

    supported_by_fact: dict[str, list[dict[str, Any]]] = {}
    for relation in relations:
        if relation["relation"] != "supported_by":
            continue
        supported_by_fact.setdefault(relation["source_key"], []).append(
            {
                "evidence_key": relation["target_key"],
                "match_method": relation["match_method"],
                "score": relation["score"],
            }
        )
    for fact in facts:
        fact["evidence"] = supported_by_fact.get(fact["key"], [])[:MAX_EVIDENCE_PER_FACT]
        fact["linked"] = bool(fact["evidence"])

    if public:
        facts = [_public_fact(item) for item in facts]
        evidence = [_public_evidence(item) for item in evidence]
        relations = [_public_relation(item) for item in relations]

    unlinked_fact_keys = [item["key"] for item in facts if not item["linked"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "extractor_name": EXTRACTOR_NAME,
        "extractor_version": EXTRACTOR_VERSION,
        "paper_key": paper_key,
        "available": paper_exists and bool(facts or evidence),
        "summary": {
            "fact_count": total_fact_count,
            "evidence_count": total_evidence_count,
            "relation_count": total_relation_count,
            "supported_relation_count": sum(1 for item in relations if item["relation"] == "supported_by"),
            "unlinked_fact_count": len(unlinked_fact_keys),
            "truncated": (
                total_fact_count > len(facts)
                or total_evidence_count > len(evidence)
                or total_relation_count > len(relations)
            ),
        },
        "facts": facts,
        "evidence": evidence,
        "relations": relations,
        "unlinked_fact_keys": unlinked_fact_keys,
    }


def export_layout_evidence_graph(db_path: Path, out_path: Path) -> int:
    init_db(db_path)
    with connect(db_path) as conn:
        paper_keys = [
            str(row["paper_key"])
            for row in conn.execute("select paper_key from papers order by paper_key").fetchall()
        ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "extractor_name": EXTRACTOR_NAME,
        "extractor_version": EXTRACTOR_VERSION,
        "papers": [load_paper_evidence_graph(db_path, paper_key, public=True) for paper_key in paper_keys],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(paper_keys)
