from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db


TEXT_ARTIFACT_PRIORITY = ("source_tex", "summary", "notes", "tldr")


@dataclass(frozen=True)
class EvidenceSourceMatch:
    artifact_type: str
    source_path: str
    match_type: str
    score: float


@dataclass(frozen=True)
class EvidenceRepairCandidate:
    provenance_id: int
    fact_id: int
    paper_key: str
    fact_type: str
    fact_name: str
    statement: str
    evidence_artifact_type: str
    evidence_quote: str
    recommended_source_path: str
    recommended_artifact_type: str
    repairable: bool
    applied: bool
    matches: list[EvidenceSourceMatch]


@dataclass(frozen=True)
class EvidenceRepairResult:
    candidates: list[EvidenceRepairCandidate]
    applied_count: int

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    @property
    def repairable_count(self) -> int:
        return sum(1 for candidate in self.candidates if candidate.repairable)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _read_text(path_value: str) -> str:
    path = Path(path_value)
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _matches_for_artifacts(conn, *, paper_key: str, evidence_quote: str) -> list[EvidenceSourceMatch]:
    normalized_quote = _normalize_text(evidence_quote)
    if not normalized_quote:
        return []
    rows = conn.execute(
        """
        select artifact_type, path from paper_artifacts
        where paper_key = ?
          and artifact_type in ('source_tex', 'summary', 'notes', 'tldr')
        order by case artifact_type
            when 'source_tex' then 1
            when 'summary' then 2
            when 'notes' then 3
            when 'tldr' then 4
            else 5
        end, path
        """,
        (paper_key,),
    ).fetchall()
    matches: list[EvidenceSourceMatch] = []
    for row in rows:
        text = _read_text(row["path"])
        if not text:
            continue
        if normalized_quote in _normalize_text(text):
            matches.append(
                EvidenceSourceMatch(
                    artifact_type=row["artifact_type"],
                    source_path=row["path"],
                    match_type="normalized_exact_contains",
                    score=1.0,
                )
            )
    return matches


def _candidate_from_row(conn, row: Any, *, applied: bool = False) -> EvidenceRepairCandidate:
    matches = _matches_for_artifacts(
        conn,
        paper_key=row["paper_key"],
        evidence_quote=row["evidence_quote"],
    )
    recommendation = matches[0] if matches else None
    return EvidenceRepairCandidate(
        provenance_id=int(row["provenance_id"]),
        fact_id=int(row["fact_id"]),
        paper_key=row["paper_key"],
        fact_type=row["fact_type"],
        fact_name=row["fact_name"] or "",
        statement=row["statement"] or "",
        evidence_artifact_type=row["evidence_artifact_type"] or "",
        evidence_quote=row["evidence_quote"] or "",
        recommended_source_path=recommendation.source_path if recommendation else "",
        recommended_artifact_type=recommendation.artifact_type if recommendation else "",
        repairable=recommendation is not None,
        applied=applied and recommendation is not None,
        matches=matches,
    )


def build_evidence_repair_candidates(db_path: Path, *, paper_key: str | None = None) -> list[EvidenceRepairCandidate]:
    init_db(db_path)
    with connect(db_path) as conn:
        params: list[Any] = []
        where = "where p.evidence_source_path = ''"
        if paper_key:
            where += " and f.paper_key = ?"
            params.append(paper_key)
        rows = conn.execute(
            f"""
            select
                p.id as provenance_id,
                f.id as fact_id,
                f.paper_key,
                f.fact_type,
                f.name as fact_name,
                f.statement,
                p.evidence_artifact_type,
                p.evidence_quote
            from research_fact_provenance p
            join research_facts f on f.id = p.fact_id
            {where}
            order by f.paper_key, f.id, p.id
            """,
            params,
        ).fetchall()
        return [_candidate_from_row(conn, row) for row in rows]


def _candidate_to_dict(candidate: EvidenceRepairCandidate) -> dict[str, Any]:
    return {
        "provenance_id": candidate.provenance_id,
        "fact_id": candidate.fact_id,
        "paper_key": candidate.paper_key,
        "fact_type": candidate.fact_type,
        "fact_name": candidate.fact_name,
        "statement": candidate.statement,
        "evidence_artifact_type": candidate.evidence_artifact_type,
        "evidence_quote": candidate.evidence_quote,
        "recommended_source_path": candidate.recommended_source_path,
        "recommended_artifact_type": candidate.recommended_artifact_type,
        "repairable": candidate.repairable,
        "applied": candidate.applied,
        "matches": [
            {
                "artifact_type": match.artifact_type,
                "source_path": match.source_path,
                "match_type": match.match_type,
                "score": match.score,
            }
            for match in candidate.matches
        ],
    }


def _write_jsonl(candidates: list[EvidenceRepairCandidate], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(_candidate_to_dict(candidate), ensure_ascii=False, sort_keys=True) for candidate in candidates]
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def export_evidence_source_path_repairs(
    db_path: Path,
    out_path: Path,
    *,
    apply: bool = False,
    paper_key: str | None = None,
) -> EvidenceRepairResult:
    init_db(db_path)
    applied_ids: set[int] = set()
    with connect(db_path) as conn:
        params: list[Any] = []
        where = "where p.evidence_source_path = ''"
        if paper_key:
            where += " and f.paper_key = ?"
            params.append(paper_key)
        rows = conn.execute(
            f"""
            select
                p.id as provenance_id,
                f.id as fact_id,
                f.paper_key,
                f.fact_type,
                f.name as fact_name,
                f.statement,
                p.evidence_artifact_type,
                p.evidence_quote
            from research_fact_provenance p
            join research_facts f on f.id = p.fact_id
            {where}
            order by f.paper_key, f.id, p.id
            """,
            params,
        ).fetchall()
        candidates = [_candidate_from_row(conn, row) for row in rows]
        if apply:
            for candidate in candidates:
                if not candidate.repairable:
                    continue
                conn.execute(
                    """
                    update research_fact_provenance
                    set evidence_source_path = ?
                    where id = ? and evidence_source_path = ''
                    """,
                    (candidate.recommended_source_path, candidate.provenance_id),
                )
                applied_ids.add(candidate.provenance_id)
            candidates = [
                EvidenceRepairCandidate(
                    provenance_id=candidate.provenance_id,
                    fact_id=candidate.fact_id,
                    paper_key=candidate.paper_key,
                    fact_type=candidate.fact_type,
                    fact_name=candidate.fact_name,
                    statement=candidate.statement,
                    evidence_artifact_type=candidate.evidence_artifact_type,
                    evidence_quote=candidate.evidence_quote,
                    recommended_source_path=candidate.recommended_source_path,
                    recommended_artifact_type=candidate.recommended_artifact_type,
                    repairable=candidate.repairable,
                    applied=candidate.provenance_id in applied_ids,
                    matches=candidate.matches,
                )
                for candidate in candidates
            ]
    _write_jsonl(candidates, out_path)
    return EvidenceRepairResult(candidates=candidates, applied_count=len(applied_ids))
