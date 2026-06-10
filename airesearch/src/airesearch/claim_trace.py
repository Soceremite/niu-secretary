from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from airesearch.artifact_ledger import find_ledger_matches
from airesearch.db import connect, init_db


ALLOWED_TRACE_FORMATS = {"json", "markdown"}


class ClaimTraceNotFound(LookupError):
    pass


def parse_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def row_to_dict(row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def find_fact_row(
    conn,
    *,
    fact_id: int | None = None,
    paper_key: str | None = None,
    fact_type: str | None = None,
    query: str | None = None,
):
    if fact_id is not None:
        return conn.execute("select * from research_facts where id = ?", (fact_id,)).fetchone()
    if not paper_key:
        raise ValueError("paper_key is required when fact_id is not provided")
    sql = "select * from research_facts where paper_key = ?"
    params: list[Any] = [paper_key]
    if fact_type:
        sql += " and fact_type = ?"
        params.append(fact_type)
    if query:
        pattern = f"%{query.lower()}%"
        sql += " and (lower(statement) like ? or lower(name) like ?)"
        params.extend([pattern, pattern])
    sql += " order by paper_key, fact_type, id limit 1"
    return conn.execute(sql, params).fetchone()


def load_paper(conn, paper_key: str) -> dict[str, Any]:
    row = conn.execute("select * from papers where paper_key = ?", (paper_key,)).fetchone()
    if row is None:
        return {"paper_key": paper_key}
    payload = row_to_dict(row)
    payload["authors"] = parse_json(payload.pop("authors_json", None), [])
    payload["ids"] = parse_json(payload.pop("ids_json", None), {})
    payload["meta"] = parse_json(payload.pop("meta_json", None), {})
    return payload


def load_fact_provenance(conn, fact_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select * from research_fact_provenance
        where fact_id = ?
        order by id
        """,
        (fact_id,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def load_matching_artifacts(conn, paper_key: str, provenance_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    artifacts: dict[int, dict[str, Any]] = {}
    for provenance in provenance_rows:
        source_path = str(provenance.get("evidence_source_path") or "")
        artifact_type = str(provenance.get("evidence_artifact_type") or "")
        rows = []
        if source_path:
            rows = conn.execute(
                """
                select * from paper_artifacts
                where paper_key = ? and path = ?
                order by artifact_type, path
                """,
                (paper_key, source_path),
            ).fetchall()
        if not rows and artifact_type:
            rows = conn.execute(
                """
                select * from paper_artifacts
                where paper_key = ? and artifact_type = ?
                order by path
                """,
                (paper_key, artifact_type),
            ).fetchall()
        for row in rows:
            artifacts[int(row["id"])] = row_to_dict(row)
    return [artifacts[key] for key in sorted(artifacts)]


def load_code_links(conn, paper_key: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select id, paper_key, url, host, owner, repo, source_type, source_path, context
        from paper_code_links
        where paper_key = ?
        order by host, owner, repo, url, id
        """,
        (paper_key,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def load_graph_relations(conn, paper_key: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select
            e.id, e.source_key, e.relation, e.target_key, e.properties_json,
            e.extractor_name, e.source_paper_key,
            source.node_type as source_type, source.label as source_label,
            target.node_type as target_type, target.label as target_label
        from kg_edges e
        left join kg_nodes source on source.node_key = e.source_key
        left join kg_nodes target on target.node_key = e.target_key
        where e.source_paper_key = ?
        order by e.relation, e.source_key, e.target_key, e.id
        """,
        (paper_key,),
    ).fetchall()
    result = []
    for row in rows:
        payload = row_to_dict(row)
        payload["properties"] = parse_json(payload.pop("properties_json", None), {})
        result.append(payload)
    return result


def load_graph_provenance(
    conn,
    *,
    paper_key: str,
    artifacts: list[dict[str, Any]],
    code_links: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    artifact_ids = {str(row["id"]) for row in artifacts}
    code_link_ids = {str(row["id"]) for row in code_links}
    rows = conn.execute(
        """
        select *
        from kg_provenance
        where source_paper_key = ?
        order by entity_type, entity_key, source_table, source_key, id
        """,
        (paper_key,),
    ).fetchall()
    result = []
    for row in rows:
        payload = row_to_dict(row)
        source_table = str(payload.get("source_table") or "")
        source_key = str(payload.get("source_key") or "")
        payload["matches_trace_source"] = (
            (source_table == "paper_artifacts" and source_key in artifact_ids)
            or (source_table == "paper_code_links" and source_key in code_link_ids)
            or source_table in {"papers", "research_facts", "research_fact_provenance"}
        )
        result.append(payload)
    return result


def trace_claim(
    db_path: Path,
    *,
    fact_id: int | None = None,
    paper_key: str | None = None,
    fact_type: str | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    init_db(db_path)
    with connect(db_path) as conn:
        fact_row = find_fact_row(
            conn,
            fact_id=fact_id,
            paper_key=paper_key,
            fact_type=fact_type,
            query=query,
        )
        if fact_row is None:
            selector = f"fact_id={fact_id}" if fact_id is not None else f"paper_key={paper_key}"
            raise ClaimTraceNotFound(f"claim_trace_not_found {selector}")
        fact = row_to_dict(fact_row)
        fact["metadata"] = parse_json(fact.pop("metadata_json", None), {})
        selected_paper_key = str(fact["paper_key"])
        provenance = load_fact_provenance(conn, int(fact["id"]))
        artifacts = load_matching_artifacts(conn, selected_paper_key, provenance)
        code_links = load_code_links(conn, selected_paper_key)
        evidence_text = provenance[0]["evidence_quote"] if provenance else ""
        return {
            "fact": fact,
            "paper": load_paper(conn, selected_paper_key),
            "provenance": provenance,
            "artifacts": artifacts,
            "ledger_matches": find_ledger_matches(
                conn,
                selected_paper_key,
                evidence_text,
                fallback_text=str(fact.get("statement") or ""),
            ),
            "code_links": code_links,
            "graph_relations": load_graph_relations(conn, selected_paper_key),
            "graph_provenance": load_graph_provenance(
                conn,
                paper_key=selected_paper_key,
                artifacts=artifacts,
                code_links=code_links,
            ),
        }


def render_claim_trace_markdown(trace: dict[str, Any]) -> str:
    fact = trace["fact"]
    paper = trace["paper"]
    lines = [
        "# Claim Trace",
        "",
        "## Fact",
        "",
        f"- id: {fact['id']}",
        f"- paper_key: {fact['paper_key']}",
        f"- type: {fact['fact_type']}",
        f"- name: {fact.get('name') or ''}",
        f"- confidence: {float(fact.get('confidence') or 0):.2f}",
        f"- statement: {fact.get('statement') or ''}",
        "",
        "## Paper",
        "",
        f"- title: {paper.get('title') or ''}",
        f"- year: {paper.get('year') or ''}",
        f"- venue: {paper.get('venue') or ''}",
        f"- source_dir: {paper.get('paper_dir') or ''}",
        f"- ids: {json.dumps(paper.get('ids') or {}, ensure_ascii=False, sort_keys=True)}",
        "",
        "## Evidence",
        "",
    ]
    if trace["provenance"]:
        for item in trace["provenance"]:
            lines.extend([
                f"- quote: {item.get('evidence_quote') or ''}",
                f"  artifact_type: {item.get('evidence_artifact_type') or ''}",
                f"  source_path: {item.get('evidence_source_path') or ''}",
            ])
    else:
        lines.append("- none")
    lines.extend(["", "## Artifact Ledger Matches", ""])
    if trace.get("ledger_matches"):
        for match in trace["ledger_matches"]:
            kind = match.get("kind") or ""
            source_path = match.get("source_path") or ""
            score = float(match.get("score") or 0.0)
            if kind == "chunk":
                detail = match.get("text") or ""
                locator = f"{match.get('artifact_type') or ''}#{match.get('chunk_index')}"
            elif kind == "equation":
                detail = match.get("latex") or ""
                locator = f"equation#{match.get('equation_index')}"
            else:
                detail = match.get("context") or match.get("citation_key") or ""
                locator = f"citation#{match.get('citation_index')}"
            lines.append(f"- {kind} {locator} score={score:.2f}: {detail} ({source_path})")
    else:
        lines.append("- none")
    lines.extend(["", "## Artifacts", ""])
    if trace["artifacts"]:
        for artifact in trace["artifacts"]:
            lines.append(
                "- {artifact_type}: {path} sha256={sha256} size_bytes={size_bytes}".format(
                    artifact_type=artifact.get("artifact_type") or "",
                    path=artifact.get("path") or "",
                    sha256=artifact.get("sha256") or "",
                    size_bytes=artifact.get("size_bytes") or 0,
                )
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Code Links", ""])
    if trace["code_links"]:
        for link in trace["code_links"]:
            lines.append(f"- {link.get('url') or ''} ({link.get('source_type') or ''}: {link.get('source_path') or ''})")
    else:
        lines.append("- none")
    lines.extend(["", "## Graph Relations", ""])
    if trace["graph_relations"]:
        for relation in trace["graph_relations"]:
            lines.append(
                "- {source} [{relation}] {target}".format(
                    source=relation.get("source_label") or relation.get("source_key") or "",
                    relation=relation.get("relation") or "",
                    target=relation.get("target_label") or relation.get("target_key") or "",
                )
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Graph Provenance", ""])
    if trace["graph_provenance"]:
        for provenance in trace["graph_provenance"]:
            marker = "matched" if provenance.get("matches_trace_source") else "paper"
            lines.append(
                "- {marker}: {entity_type} {entity_key} from {source_table}:{source_key}.{source_field}".format(
                    marker=marker,
                    entity_type=provenance.get("entity_type") or "",
                    entity_key=provenance.get("entity_key") or "",
                    source_table=provenance.get("source_table") or "",
                    source_key=provenance.get("source_key") or "",
                    source_field=provenance.get("source_field") or "",
                )
            )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def render_claim_trace(trace: dict[str, Any], *, output_format: str = "markdown") -> str:
    if output_format not in ALLOWED_TRACE_FORMATS:
        raise ValueError("output_format must be one of: json, markdown")
    if output_format == "json":
        return json.dumps(trace, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return render_claim_trace_markdown(trace)


def export_claim_trace(
    db_path: Path,
    *,
    out_path: Path | None = None,
    output_format: str = "markdown",
    fact_id: int | None = None,
    paper_key: str | None = None,
    fact_type: str | None = None,
    query: str | None = None,
) -> str:
    trace = trace_claim(
        db_path,
        fact_id=fact_id,
        paper_key=paper_key,
        fact_type=fact_type,
        query=query,
    )
    rendered = render_claim_trace(trace, output_format=output_format)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
    return rendered
