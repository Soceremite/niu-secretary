from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import stable_json


EXTRACTOR_NAME = "deterministic_paper_card"
EXTRACTOR_VERSION = "2026-06-08.1"


@dataclass(frozen=True)
class ExtractionResult:
    papers_seen: int
    cards_written: int
    nodes_written: int
    edges_written: int
    provenance_written: int


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def parse_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def normalize_key(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "unknown"


def artifact_node_key(paper_key: str, artifact_type: str) -> str:
    return f"artifact:{paper_key}:{normalize_key(artifact_type)}"


def identifier_nodes(ids: dict[str, Any]) -> list[tuple[str, str, str]]:
    nodes: list[tuple[str, str, str]] = []
    for id_type, value in sorted(ids.items()):
        if value in (None, ""):
            continue
        value_text = str(value)
        nodes.append((f"id:{normalize_key(id_type)}:{normalize_key(value_text)}", id_type, value_text))
    return nodes


def upsert_node(conn, *, node_key: str, node_type: str, label: str, properties: dict[str, Any], paper_key: str, now: str) -> None:
    conn.execute(
        """
        insert into kg_nodes (
            node_key, node_type, label, properties_json, extractor_name,
            source_paper_key, created_at, updated_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?)
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


def upsert_edge(conn, *, source_key: str, relation: str, target_key: str, properties: dict[str, Any], paper_key: str, now: str) -> None:
    conn.execute(
        """
        insert into kg_edges (
            source_key, relation, target_key, properties_json, extractor_name,
            source_paper_key, created_at, updated_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(source_key, relation, target_key, extractor_name) do update set
            properties_json = excluded.properties_json,
            source_paper_key = excluded.source_paper_key,
            updated_at = excluded.updated_at
        """,
        (source_key, relation, target_key, stable_json(properties), EXTRACTOR_NAME, paper_key, now, now),
    )


def add_provenance(
    conn,
    *,
    entity_type: str,
    entity_key: str,
    source_table: str,
    source_key: str,
    source_field: str,
    paper_key: str,
    now: str,
) -> None:
    conn.execute(
        """
        insert or ignore into kg_provenance (
            entity_type, entity_key, source_table, source_key, source_field,
            confidence, extractor_name, source_paper_key, created_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (entity_type, entity_key, source_table, source_key, source_field, 1.0, EXTRACTOR_NAME, paper_key, now),
    )


def clear_prior_graph(conn, paper_key: str) -> None:
    conn.execute(
        "delete from kg_provenance where source_paper_key = ? and extractor_name = ?",
        (paper_key, EXTRACTOR_NAME),
    )
    conn.execute(
        "delete from kg_edges where source_paper_key = ? and extractor_name = ?",
        (paper_key, EXTRACTOR_NAME),
    )
    conn.execute(
        "delete from kg_nodes where source_paper_key = ? and extractor_name = ?",
        (paper_key, EXTRACTOR_NAME),
    )


def load_papers(conn, *, limit: int | None, paper_key: str | None):
    sql = "select * from papers"
    params: list[Any] = []
    if paper_key:
        sql += " where paper_key = ?"
        params.append(paper_key)
    sql += " order by updated_at desc, paper_key"
    if limit is not None:
        sql += " limit ?"
        params.append(limit)
    return conn.execute(sql, params).fetchall()


def load_artifacts(conn, paper_key: str):
    return conn.execute(
        "select * from paper_artifacts where paper_key = ? order by artifact_type, path",
        (paper_key,),
    ).fetchall()


def extract_one(conn, paper, now: str) -> tuple[int, int, int, int]:
    paper_key = paper["paper_key"]
    clear_prior_graph(conn, paper_key)
    authors = parse_json(paper["authors_json"], [])
    if not isinstance(authors, list):
        authors = []
    ids = parse_json(paper["ids_json"], {})
    if not isinstance(ids, dict):
        ids = {}
    artifacts = load_artifacts(conn, paper_key)
    artifact_types = sorted({row["artifact_type"] for row in artifacts})
    status = "complete" if paper["title"] and authors else "partial"

    conn.execute(
        """
        insert into paper_cards (
            paper_key, title, authors_json, year, venue, ids_json,
            artifact_types_json, source_dir, status, extractor_version,
            created_at, updated_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(paper_key) do update set
            title = excluded.title,
            authors_json = excluded.authors_json,
            year = excluded.year,
            venue = excluded.venue,
            ids_json = excluded.ids_json,
            artifact_types_json = excluded.artifact_types_json,
            source_dir = excluded.source_dir,
            status = excluded.status,
            extractor_version = excluded.extractor_version,
            updated_at = excluded.updated_at
        """,
        (
            paper_key,
            paper["title"] or "",
            stable_json(authors),
            paper["year"],
            paper["venue"] or "",
            stable_json(ids),
            stable_json(artifact_types),
            paper["paper_dir"] or "",
            status,
            EXTRACTOR_VERSION,
            now,
            now,
        ),
    )
    add_provenance(
        conn,
        entity_type="paper_card",
        entity_key=paper_key,
        source_table="papers",
        source_key=paper_key,
        source_field="*",
        paper_key=paper_key,
        now=now,
    )

    paper_node = f"paper:{paper_key}"
    nodes = 0
    edges = 0
    provenance = 1
    upsert_node(
        conn,
        node_key=paper_node,
        node_type="paper",
        label=paper["title"] or paper_key,
        properties={"year": paper["year"], "paper_key": paper_key},
        paper_key=paper_key,
        now=now,
    )
    add_provenance(conn, entity_type="node", entity_key=paper_node, source_table="papers", source_key=paper_key, source_field="title", paper_key=paper_key, now=now)
    nodes += 1
    provenance += 1

    for position, author in enumerate(authors):
        author_text = str(author).strip()
        if not author_text:
            continue
        node_key = f"author:{normalize_key(author_text)}"
        upsert_node(conn, node_key=node_key, node_type="author", label=author_text, properties={}, paper_key=paper_key, now=now)
        upsert_edge(conn, source_key=paper_node, relation="authored_by", target_key=node_key, properties={"position": position}, paper_key=paper_key, now=now)
        add_provenance(conn, entity_type="node", entity_key=node_key, source_table="papers", source_key=paper_key, source_field="authors_json", paper_key=paper_key, now=now)
        add_provenance(conn, entity_type="edge", entity_key=f"{paper_node}|authored_by|{node_key}", source_table="papers", source_key=paper_key, source_field="authors_json", paper_key=paper_key, now=now)
        nodes += 1
        edges += 1
        provenance += 2

    venue = str(paper["venue"] or "").strip()
    if venue:
        node_key = f"venue:{normalize_key(venue)}"
        upsert_node(conn, node_key=node_key, node_type="venue", label=venue, properties={}, paper_key=paper_key, now=now)
        upsert_edge(conn, source_key=paper_node, relation="published_in", target_key=node_key, properties={}, paper_key=paper_key, now=now)
        add_provenance(conn, entity_type="node", entity_key=node_key, source_table="papers", source_key=paper_key, source_field="venue", paper_key=paper_key, now=now)
        add_provenance(conn, entity_type="edge", entity_key=f"{paper_node}|published_in|{node_key}", source_table="papers", source_key=paper_key, source_field="venue", paper_key=paper_key, now=now)
        nodes += 1
        edges += 1
        provenance += 2

    for node_key, id_type, value in identifier_nodes(ids):
        upsert_node(conn, node_key=node_key, node_type="identifier", label=value, properties={"id_type": id_type}, paper_key=paper_key, now=now)
        upsert_edge(conn, source_key=paper_node, relation="has_identifier", target_key=node_key, properties={"id_type": id_type}, paper_key=paper_key, now=now)
        add_provenance(conn, entity_type="node", entity_key=node_key, source_table="papers", source_key=paper_key, source_field="ids_json", paper_key=paper_key, now=now)
        add_provenance(conn, entity_type="edge", entity_key=f"{paper_node}|has_identifier|{node_key}", source_table="papers", source_key=paper_key, source_field="ids_json", paper_key=paper_key, now=now)
        nodes += 1
        edges += 1
        provenance += 2

    for artifact in artifacts:
        node_key = artifact_node_key(paper_key, artifact["artifact_type"])
        source_key = str(artifact["id"])
        upsert_node(
            conn,
            node_key=node_key,
            node_type="artifact",
            label=artifact["artifact_type"],
            properties={"path": artifact["path"], "sha256": artifact["sha256"], "size_bytes": artifact["size_bytes"]},
            paper_key=paper_key,
            now=now,
        )
        upsert_edge(conn, source_key=paper_node, relation="has_artifact", target_key=node_key, properties={"artifact_type": artifact["artifact_type"]}, paper_key=paper_key, now=now)
        add_provenance(conn, entity_type="node", entity_key=node_key, source_table="paper_artifacts", source_key=source_key, source_field="artifact_type", paper_key=paper_key, now=now)
        add_provenance(conn, entity_type="edge", entity_key=f"{paper_node}|has_artifact|{node_key}", source_table="paper_artifacts", source_key=source_key, source_field="artifact_type", paper_key=paper_key, now=now)
        nodes += 1
        edges += 1
        provenance += 2

    return 1, nodes, edges, provenance


def extract_paper_cards(db_path: Path, limit: int | None = None, paper_key: str | None = None) -> ExtractionResult:
    init_db(db_path)
    started_at = utc_now()
    with connect(db_path) as conn:
        run = conn.execute(
            """
            insert into extraction_runs (
                extractor_name, extractor_version, paper_key, limit_count,
                started_at, status
            ) values (?, ?, ?, ?, ?, ?)
            """,
            (EXTRACTOR_NAME, EXTRACTOR_VERSION, paper_key, limit, started_at, "running"),
        )
        run_id = run.lastrowid
        try:
            papers = load_papers(conn, limit=limit, paper_key=paper_key)
            cards = nodes = edges = provenance = 0
            now = utc_now()
            for paper in papers:
                card_count, node_count, edge_count, provenance_count = extract_one(conn, paper, now)
                cards += card_count
                nodes += node_count
                edges += edge_count
                provenance += provenance_count
            conn.execute(
                """
                update extraction_runs set
                    papers_seen = ?, cards_written = ?, nodes_written = ?,
                    edges_written = ?, provenance_written = ?, finished_at = ?, status = ?
                where id = ?
                """,
                (len(papers), cards, nodes, edges, provenance, utc_now(), "success", run_id),
            )
            conn.commit()
            return ExtractionResult(len(papers), cards, nodes, edges, provenance)
        except Exception as exc:
            conn.execute(
                "update extraction_runs set finished_at = ?, status = ?, error = ? where id = ?",
                (utc_now(), "failed", str(exc), run_id),
            )
            conn.commit()
            raise


def list_paper_cards(db_path: Path, limit: int = 20):
    init_db(db_path)
    with connect(db_path) as conn:
        return conn.execute(
            "select * from paper_cards order by updated_at desc, paper_key limit ?",
            (limit,),
        ).fetchall()


def export_paper_cards(db_path: Path, out_path: Path) -> int:
    init_db(db_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        rows = conn.execute("select * from paper_cards order by updated_at desc, paper_key").fetchall()
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = {
                "paper_key": row["paper_key"],
                "title": row["title"],
                "authors": parse_json(row["authors_json"], []),
                "year": row["year"],
                "venue": row["venue"],
                "ids": parse_json(row["ids_json"], {}),
                "artifact_types": parse_json(row["artifact_types_json"], []),
                "source_dir": row["source_dir"],
                "status": row["status"],
                "extractor_version": row["extractor_version"],
                "updated_at": row["updated_at"],
            }
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)
