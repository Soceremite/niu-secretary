from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db


TEXT_ARTIFACT_TYPES = {"summary", "tldr", "notes", "source_tex"}
ALLOWED_LEDGER_FORMATS = {"markdown", "json", "jsonl"}
CITE_RE = re.compile(r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]+)\}")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
LABEL_RE = re.compile(r"^\s*([A-Za-z0-9_.:-]+)\s*:\s*(.+?)\s*$")


@dataclass(frozen=True)
class LedgerChunk:
    artifact_type: str
    source_path: str
    chunk_index: int
    heading: str
    text: str
    char_start: int
    char_end: int
    sha256: str


@dataclass(frozen=True)
class LedgerEquation:
    source_path: str
    equation_index: int
    label: str
    latex: str
    context: str


@dataclass(frozen=True)
class LedgerCitation:
    source_path: str
    citation_index: int
    citation_key: str
    raw_text: str
    context: str


@dataclass(frozen=True)
class ArtifactLedgerResult:
    papers_seen: int
    chunks_written: int
    equations_written: int
    citations_written: int


@dataclass(frozen=True)
class LedgerReport:
    generated_at: str
    paper_count: int
    chunk_count: int
    equation_count: int
    citation_count: int
    chunks: list[dict[str, Any]]
    equations: list[dict[str, Any]]
    citations: list[dict[str, Any]]

    @property
    def fact_count(self) -> int:
        return 0


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _read_text(path_value: str) -> str:
    path = Path(path_value)
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _context_window(text: str, start: int, end: int, width: int = 120) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    return _normalize_text(text[left:right])


def extract_chunks_from_text(
    text: str,
    *,
    artifact_type: str,
    source_path: str,
) -> list[LedgerChunk]:
    chunks: list[LedgerChunk] = []
    heading = ""
    paragraph_start: int | None = None
    paragraph_lines: list[str] = []

    def flush(end: int) -> None:
        nonlocal paragraph_start, paragraph_lines
        if paragraph_start is None:
            return
        chunk_text = _normalize_text("\n".join(paragraph_lines))
        if chunk_text:
            chunks.append(
                LedgerChunk(
                    artifact_type=artifact_type,
                    source_path=source_path,
                    chunk_index=len(chunks),
                    heading=heading,
                    text=chunk_text,
                    char_start=paragraph_start,
                    char_end=end,
                    sha256=_sha256_text(chunk_text),
                )
            )
        paragraph_start = None
        paragraph_lines = []

    offset = 0
    for line in text.splitlines(keepends=True):
        raw_line = line.rstrip("\r\n")
        line_start = offset
        line_end = offset + len(line)
        offset = line_end
        match = HEADING_RE.match(raw_line)
        if match:
            flush(line_start)
            heading = match.group(2).strip()
            continue
        if not raw_line.strip():
            flush(line_start)
            continue
        if paragraph_start is None:
            paragraph_start = line_start
        paragraph_lines.append(raw_line)
    flush(len(text))
    return chunks


def extract_equations_from_text(text: str, *, source_path: str) -> list[LedgerEquation]:
    equations: list[LedgerEquation] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or HEADING_RE.match(stripped):
            continue
        label = ""
        latex = stripped
        match = LABEL_RE.match(stripped)
        if match:
            label = match.group(1).strip()
            latex = match.group(2).strip()
        equations.append(
            LedgerEquation(
                source_path=source_path,
                equation_index=len(equations),
                label=label,
                latex=latex,
                context=stripped,
            )
        )
    return equations


def extract_citations_from_text(text: str, *, source_path: str) -> list[LedgerCitation]:
    citations: list[LedgerCitation] = []
    for match in CITE_RE.finditer(text):
        raw_text = match.group(0)
        for key in match.group(1).split(","):
            citation_key = key.strip()
            if not citation_key:
                continue
            citations.append(
                LedgerCitation(
                    source_path=source_path,
                    citation_index=len(citations),
                    citation_key=citation_key,
                    raw_text=raw_text,
                    context=_context_window(text, match.start(), match.end()),
                )
            )
    return citations


def _load_papers(conn, *, limit: int | None, paper_key: str | None):
    sql = "select paper_key from papers"
    params: list[Any] = []
    if paper_key:
        sql += " where paper_key = ?"
        params.append(paper_key)
    sql += " order by updated_at desc, paper_key"
    if limit is not None:
        sql += " limit ?"
        params.append(limit)
    return conn.execute(sql, params).fetchall()


def _artifact_rows(conn, paper_key: str):
    return conn.execute(
        """
        select artifact_type, path from paper_artifacts
        where paper_key = ?
        order by artifact_type, path
        """,
        (paper_key,),
    ).fetchall()


def extract_artifact_ledger(
    db_path: Path,
    *,
    limit: int | None = None,
    paper_key: str | None = None,
) -> ArtifactLedgerResult:
    init_db(db_path)
    now = utc_now()
    chunks_written = 0
    equations_written = 0
    citations_written = 0
    with connect(db_path) as conn:
        papers = _load_papers(conn, limit=limit, paper_key=paper_key)
        for paper in papers:
            key = paper["paper_key"]
            conn.execute("delete from paper_chunks where paper_key = ?", (key,))
            conn.execute("delete from paper_equations where paper_key = ?", (key,))
            conn.execute("delete from paper_citations where paper_key = ?", (key,))
            for artifact in _artifact_rows(conn, key):
                artifact_type = artifact["artifact_type"]
                source_path = artifact["path"]
                text = _read_text(source_path)
                if not text:
                    continue
                if artifact_type in TEXT_ARTIFACT_TYPES:
                    for chunk in extract_chunks_from_text(text, artifact_type=artifact_type, source_path=source_path):
                        conn.execute(
                            """
                            insert into paper_chunks (
                                paper_key, artifact_type, source_path, chunk_index,
                                heading, text, char_start, char_end, sha256,
                                created_at, updated_at
                            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                key,
                                chunk.artifact_type,
                                chunk.source_path,
                                chunk.chunk_index,
                                chunk.heading,
                                chunk.text,
                                chunk.char_start,
                                chunk.char_end,
                                chunk.sha256,
                                now,
                                now,
                            ),
                        )
                        chunks_written += 1
                if artifact_type == "equations":
                    for equation in extract_equations_from_text(text, source_path=source_path):
                        conn.execute(
                            """
                            insert into paper_equations (
                                paper_key, source_path, equation_index, label,
                                latex, context, created_at, updated_at
                            ) values (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                key,
                                equation.source_path,
                                equation.equation_index,
                                equation.label,
                                equation.latex,
                                equation.context,
                                now,
                                now,
                            ),
                        )
                        equations_written += 1
                if artifact_type == "source_tex":
                    for citation in extract_citations_from_text(text, source_path=source_path):
                        conn.execute(
                            """
                            insert into paper_citations (
                                paper_key, source_path, citation_index, citation_key,
                                raw_text, context, created_at, updated_at
                            ) values (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                key,
                                citation.source_path,
                                citation.citation_index,
                                citation.citation_key,
                                citation.raw_text,
                                citation.context,
                                now,
                                now,
                            ),
                        )
                        citations_written += 1
        conn.commit()
    return ArtifactLedgerResult(
        papers_seen=len(papers),
        chunks_written=chunks_written,
        equations_written=equations_written,
        citations_written=citations_written,
    )


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def build_artifact_ledger_report(db_path: Path) -> LedgerReport:
    init_db(db_path)
    with connect(db_path) as conn:
        chunks = [
            _row_to_dict(row)
            for row in conn.execute(
                "select * from paper_chunks order by paper_key, artifact_type, source_path, chunk_index"
            ).fetchall()
        ]
        equations = [
            _row_to_dict(row)
            for row in conn.execute(
                "select * from paper_equations order by paper_key, source_path, equation_index"
            ).fetchall()
        ]
        citations = [
            _row_to_dict(row)
            for row in conn.execute(
                "select * from paper_citations order by paper_key, source_path, citation_index, citation_key"
            ).fetchall()
        ]
        paper_keys = {
            *{str(row["paper_key"]) for row in chunks},
            *{str(row["paper_key"]) for row in equations},
            *{str(row["paper_key"]) for row in citations},
        }
    return LedgerReport(
        generated_at=utc_now(),
        paper_count=len(paper_keys),
        chunk_count=len(chunks),
        equation_count=len(equations),
        citation_count=len(citations),
        chunks=chunks,
        equations=equations,
        citations=citations,
    )


def artifact_ledger_to_dict(report: LedgerReport) -> dict[str, Any]:
    return {
        "generated_at": report.generated_at,
        "paper_count": report.paper_count,
        "fact_count": report.fact_count,
        "chunk_count": report.chunk_count,
        "equation_count": report.equation_count,
        "citation_count": report.citation_count,
        "chunks": report.chunks,
        "equations": report.equations,
        "citations": report.citations,
    }


def render_artifact_ledger_markdown(report: LedgerReport) -> str:
    lines = [
        "# AIResearch Artifact Ledger",
        "",
        f"Generated: {report.generated_at}",
        f"Papers: {report.paper_count}",
        f"Chunks: {report.chunk_count}",
        f"Equations: {report.equation_count}",
        f"Citations: {report.citation_count}",
        "",
        "## Chunks",
        "",
    ]
    if report.chunks:
        for row in report.chunks:
            heading = f" ({row['heading']})" if row.get("heading") else ""
            lines.append(
                f"- `{row['paper_key']}` {row['artifact_type']}#{row['chunk_index']}{heading}: {row['text']}"
            )
    else:
        lines.append("No chunks extracted.")
    lines.extend(["", "## Equations", ""])
    if report.equations:
        for row in report.equations:
            label = f" {row['label']}:" if row.get("label") else ""
            lines.append(f"- `{row['paper_key']}` equation#{row['equation_index']}{label} {row['latex']}")
    else:
        lines.append("No equations extracted.")
    lines.extend(["", "## Citations", ""])
    if report.citations:
        for row in report.citations:
            lines.append(f"- `{row['paper_key']}` {row['citation_key']}: {row['context']}")
    else:
        lines.append("No citation mentions extracted.")
    return "\n".join(lines).rstrip() + "\n"


def export_artifact_ledger(db_path: Path, out_path: Path, *, output_format: str = "markdown") -> LedgerReport:
    if output_format not in ALLOWED_LEDGER_FORMATS:
        raise ValueError("output_format must be one of: json, jsonl, markdown")
    report = build_artifact_ledger_report(db_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "markdown":
        out_path.write_text(render_artifact_ledger_markdown(report), encoding="utf-8")
    elif output_format == "json":
        payload = json.dumps(
            artifact_ledger_to_dict(report),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        rows = [
            *({"kind": "chunk", **row} for row in report.chunks),
            *({"kind": "equation", **row} for row in report.equations),
            *({"kind": "citation", **row} for row in report.citations),
        ]
        out_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
    return report


def find_ledger_matches(
    conn,
    paper_key: str,
    evidence_text: str | None,
    *,
    fallback_text: str | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    needles = [
        _normalize_text(value or "").lower()
        for value in (evidence_text, fallback_text)
    ]
    needles = [needle for needle in needles if needle]
    if not needles:
        return []
    matches: list[dict[str, Any]] = []

    def score_text(value: str) -> float:
        normalized = _normalize_text(value).lower()
        if not normalized:
            return 0.0
        for index, needle in enumerate(needles):
            if needle in normalized:
                return 1.0 - (index * 0.1)
            if normalized in needle:
                return 0.8 - (index * 0.1)
        return 0.0

    for row in conn.execute(
        """
        select * from paper_chunks
        where paper_key = ?
        order by artifact_type, source_path, chunk_index
        """,
        (paper_key,),
    ).fetchall():
        score = score_text(row["text"])
        if score:
            payload = _row_to_dict(row)
            payload["kind"] = "chunk"
            payload["score"] = score
            matches.append(payload)
    for row in conn.execute(
        """
        select * from paper_equations
        where paper_key = ?
        order by source_path, equation_index
        """,
        (paper_key,),
    ).fetchall():
        score = max(score_text(row["latex"]), score_text(row["context"]))
        if score:
            payload = _row_to_dict(row)
            payload["kind"] = "equation"
            payload["score"] = score
            matches.append(payload)
    for row in conn.execute(
        """
        select * from paper_citations
        where paper_key = ?
        order by source_path, citation_index, citation_key
        """,
        (paper_key,),
    ).fetchall():
        score = max(
            score_text(row["citation_key"]),
            score_text(row["raw_text"]),
            score_text(row["context"]),
        )
        if score:
            payload = _row_to_dict(row)
            payload["kind"] = "citation"
            payload["score"] = score
            matches.append(payload)
    return sorted(
        matches,
        key=lambda row: (
            -float(row["score"]),
            str(row["kind"]),
            str(row.get("source_path") or ""),
            int(
                row.get("chunk_index")
                or row.get("equation_index")
                or row.get("citation_index")
                or 0
            ),
        ),
    )[:limit]
