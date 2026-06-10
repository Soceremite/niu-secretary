from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from airesearch.db import connect
from airesearch.research_digest import DigestFact, DigestPaper, ResearchDigest, build_research_digest


@dataclass(frozen=True)
class RelationPaperRef:
    paper_key: str
    title: str
    year: int | None
    venue: str


@dataclass(frozen=True)
class RelationEvidence:
    paper_key: str
    statement: str
    confidence: float
    evidence_quote: str | None
    evidence_source_path: str | None


@dataclass(frozen=True)
class RelationGroup:
    relation_type: str
    key: str
    label: str
    papers: list[RelationPaperRef]
    evidence: list[RelationEvidence]
    urls: list[str]

    @property
    def paper_count(self) -> int:
        return len(self.papers)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)


@dataclass(frozen=True)
class CitationLedgerStatus:
    status: str
    paper_count: int
    citation_count: int
    papers_with_citations: list[RelationPaperRef]
    papers_missing_citations: list[RelationPaperRef]
    note: str

    @property
    def citation_artifact_paper_count(self) -> int:
        return len(self.papers_with_citations)

    @property
    def missing_citation_artifact_paper_count(self) -> int:
        return len(self.papers_missing_citations)


@dataclass(frozen=True)
class ResearchRelations:
    generated_at: str
    paper_count: int
    fact_count: int
    code_relations: list[RelationGroup]
    method_relations: list[RelationGroup]
    dataset_relations: list[RelationGroup]
    benchmark_relations: list[RelationGroup]
    citation_status: CitationLedgerStatus

    @property
    def code_relation_count(self) -> int:
        return len(self.code_relations)

    @property
    def dataset_relation_count(self) -> int:
        return len(self.dataset_relations)

    @property
    def method_relation_count(self) -> int:
        return len(self.method_relations)

    @property
    def benchmark_relation_count(self) -> int:
        return len(self.benchmark_relations)

    @property
    def relation_count(self) -> int:
        return (
            self.code_relation_count
            + self.method_relation_count
            + self.dataset_relation_count
            + self.benchmark_relation_count
        )


def _normalize_text(value: str) -> str:
    text = value.lower().strip()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\b(the|a|an|dataset|data|benchmark|uses|use|contains|contains)\b", " ", text)
    return " ".join(text.split())


def _paper_ref(paper: DigestPaper) -> RelationPaperRef:
    return RelationPaperRef(
        paper_key=paper.paper_key,
        title=paper.title,
        year=paper.year,
        venue=paper.venue,
    )


def _paper_sort_key(paper: RelationPaperRef) -> tuple[int, str, str]:
    year = paper.year if paper.year is not None else -1
    return (-year, paper.title.lower(), paper.paper_key)


def _relation_sort_key(group: RelationGroup) -> tuple[int, int, str]:
    return (-group.paper_count, -group.evidence_count, group.label.lower())


def _paper_label(paper: RelationPaperRef) -> str:
    parts = [paper.title]
    if paper.year:
        parts.append(str(paper.year))
    if paper.venue:
        parts.append(paper.venue)
    parts.append(f"`{paper.paper_key}`")
    return " | ".join(parts)


def _add_group_item(
    groups: dict[str, dict[str, Any]],
    *,
    key: str,
    relation_type: str,
    label: str,
    paper: DigestPaper,
    evidence: RelationEvidence | None = None,
    url: str = "",
) -> None:
    group = groups.setdefault(
        key,
        {
            "relation_type": relation_type,
            "label": label,
            "papers": {},
            "evidence": [],
            "urls": set(),
        },
    )
    group["papers"][paper.paper_key] = _paper_ref(paper)
    if evidence is not None:
        group["evidence"].append(evidence)
    if url:
        group["urls"].add(url)


def _materialize_groups(groups: dict[str, dict[str, Any]]) -> list[RelationGroup]:
    result = []
    for key, payload in groups.items():
        papers = sorted(payload["papers"].values(), key=_paper_sort_key)
        if len(papers) < 2:
            continue
        result.append(
            RelationGroup(
                relation_type=payload["relation_type"],
                key=key,
                label=payload["label"],
                papers=papers,
                evidence=list(payload["evidence"]),
                urls=sorted(payload["urls"]),
            )
        )
    return sorted(result, key=_relation_sort_key)


def _build_code_relations(digest: ResearchDigest) -> list[RelationGroup]:
    groups: dict[str, dict[str, Any]] = {}
    for paper in digest.papers:
        for link in paper.code_links:
            host = str(link.get("host") or "").lower().strip()
            owner = str(link.get("owner") or "").lower().strip()
            repo = str(link.get("repo") or "").lower().strip()
            url = str(link.get("url") or "").strip()
            if host and owner and repo:
                _add_group_item(
                    groups,
                    key=f"repo:{host}/{owner}/{repo}",
                    relation_type="code_repository",
                    label=f"{host}/{owner}/{repo}",
                    paper=paper,
                    url=url,
                )
            if host and owner:
                _add_group_item(
                    groups,
                    key=f"owner:{host}/{owner}",
                    relation_type="code_owner",
                    label=f"{host}/{owner}",
                    paper=paper,
                    url=url,
                )
            if host:
                _add_group_item(
                    groups,
                    key=f"host:{host}",
                    relation_type="code_host",
                    label=host,
                    paper=paper,
                    url=url,
                )
    return _materialize_groups(groups)


def _fact_label(fact: DigestFact, fact_type: str) -> str:
    fallback = f"(unnamed {fact_type})"
    return fact.name.strip() or fact.statement.strip() or fallback


def _build_fact_relations(digest: ResearchDigest, fact_type: str) -> list[RelationGroup]:
    groups: dict[str, dict[str, Any]] = {}
    for paper in digest.papers:
        for fact in paper.facts.get(fact_type, []):
            label = _fact_label(fact, fact_type)
            key = _normalize_text(label) or _normalize_text(fact.statement) or f"(unnamed {fact_type})"
            _add_group_item(
                groups,
                key=f"{fact_type}:{key}",
                relation_type=fact_type,
                label=label,
                paper=paper,
                evidence=RelationEvidence(
                    paper_key=paper.paper_key,
                    statement=fact.statement,
                    confidence=fact.confidence,
                    evidence_quote=fact.evidence_quote,
                    evidence_source_path=fact.evidence_source_path,
                ),
            )
    return _materialize_groups(groups)


def _build_citation_status(db_path: Path, digest: ResearchDigest) -> CitationLedgerStatus:
    citation_counts: dict[str, int] = {}
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            select paper_key, count(*) as citation_count
            from paper_citations
            group by paper_key
            """
        ).fetchall()
    for row in rows:
        citation_counts[str(row["paper_key"])] = int(row["citation_count"])
    with_citations = []
    missing = []
    for paper in digest.papers:
        if citation_counts.get(paper.paper_key, 0) > 0:
            with_citations.append(_paper_ref(paper))
        else:
            missing.append(_paper_ref(paper))
    citation_count = sum(citation_counts.values())
    return CitationLedgerStatus(
        status="citation_ledger_available" if citation_count else "citation_ledger_missing",
        paper_count=digest.paper_count,
        citation_count=citation_count,
        papers_with_citations=sorted(with_citations, key=_paper_sort_key),
        papers_missing_citations=sorted(missing, key=_paper_sort_key),
        note=(
            "Citation mentions are available from the artifact ledger. "
            "True citation edges still require matching citation keys to papers."
        ),
    )


def build_research_relations(db_path: Path) -> ResearchRelations:
    digest = build_research_digest(db_path)
    return ResearchRelations(
        generated_at=digest.generated_at,
        paper_count=digest.paper_count,
        fact_count=digest.fact_count,
        code_relations=_build_code_relations(digest),
        method_relations=_build_fact_relations(digest, "method"),
        dataset_relations=_build_fact_relations(digest, "dataset"),
        benchmark_relations=_build_fact_relations(digest, "benchmark"),
        citation_status=_build_citation_status(db_path, digest),
    )


def _render_relation_group(group: RelationGroup) -> list[str]:
    lines = [
        f"### {group.label}",
        "",
        f"Type: {group.relation_type} | Papers: {group.paper_count} | Evidence: {group.evidence_count}",
        "",
        "Papers:",
    ]
    for paper in group.papers:
        lines.append(f"- {_paper_label(paper)}")
    if group.urls:
        lines.extend(["", "URLs:"])
        for url in group.urls:
            lines.append(f"- {url}")
    if group.evidence:
        lines.extend(["", "Evidence:"])
        for evidence in group.evidence:
            quote = evidence.evidence_quote or evidence.statement
            detail = f"- `{evidence.paper_key}`: {quote} (confidence: {evidence.confidence:.2f})"
            if evidence.evidence_source_path:
                detail += f" {evidence.evidence_source_path}"
            lines.append(detail)
    lines.append("")
    return lines


def render_markdown(relations: ResearchRelations) -> str:
    lines = [
        "# AIResearch Cross-Paper Relations",
        "",
        f"Generated: {relations.generated_at}",
        f"Papers: {relations.paper_count}",
        f"Facts: {relations.fact_count}",
        f"Cross-paper relations: {relations.relation_count}",
        "",
        "## Code Relations",
        "",
    ]
    if relations.code_relations:
        for group in relations.code_relations:
            lines.extend(_render_relation_group(group))
    else:
        lines.append("No shared code relations found across multiple papers.")
        lines.append("")
    lines.extend(["## Method Relations", ""])
    if relations.method_relations:
        for group in relations.method_relations:
            lines.extend(_render_relation_group(group))
    else:
        lines.append("No shared method relations found across multiple papers.")
        lines.append("")
    lines.extend(["## Dataset Relations", ""])
    if relations.dataset_relations:
        for group in relations.dataset_relations:
            lines.extend(_render_relation_group(group))
    else:
        lines.append("No shared dataset relations found across multiple papers.")
        lines.append("")
    lines.extend(["## Benchmark Relations", ""])
    if relations.benchmark_relations:
        for group in relations.benchmark_relations:
            lines.extend(_render_relation_group(group))
    else:
        lines.append("No shared benchmark relations found across multiple papers.")
        lines.append("")
    status = relations.citation_status
    lines.extend(
        [
            "## Citation Ledger Status",
            "",
            f"Status: {status.status}",
            f"Citation mentions: {status.citation_count}",
            f"Papers with citation mentions: {status.citation_artifact_paper_count}/{status.paper_count}",
            f"Papers missing citation mentions: {status.missing_citation_artifact_paper_count}",
            status.note,
            "",
        ]
    )
    if status.papers_missing_citations:
        lines.append("Missing citation mentions:")
        for paper in status.papers_missing_citations:
            lines.append(f"- {_paper_label(paper)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _paper_ref_to_dict(paper: RelationPaperRef) -> dict[str, Any]:
    return {
        "paper_key": paper.paper_key,
        "title": paper.title,
        "year": paper.year,
        "venue": paper.venue,
    }


def _group_to_dict(group: RelationGroup) -> dict[str, Any]:
    return {
        "relation_type": group.relation_type,
        "key": group.key,
        "label": group.label,
        "paper_count": group.paper_count,
        "evidence_count": group.evidence_count,
        "papers": [_paper_ref_to_dict(paper) for paper in group.papers],
        "evidence": [
            {
                "paper_key": item.paper_key,
                "statement": item.statement,
                "confidence": item.confidence,
                "evidence_quote": item.evidence_quote,
                "evidence_source_path": item.evidence_source_path,
            }
            for item in group.evidence
        ],
        "urls": group.urls,
    }


def research_relations_to_dict(relations: ResearchRelations) -> dict[str, Any]:
    status = relations.citation_status
    return {
        "generated_at": relations.generated_at,
        "paper_count": relations.paper_count,
        "fact_count": relations.fact_count,
        "relation_count": relations.relation_count,
        "code_relation_count": relations.code_relation_count,
        "method_relation_count": relations.method_relation_count,
        "dataset_relation_count": relations.dataset_relation_count,
        "benchmark_relation_count": relations.benchmark_relation_count,
        "code_relations": [_group_to_dict(group) for group in relations.code_relations],
        "method_relations": [_group_to_dict(group) for group in relations.method_relations],
        "dataset_relations": [_group_to_dict(group) for group in relations.dataset_relations],
        "benchmark_relations": [_group_to_dict(group) for group in relations.benchmark_relations],
        "citation_status": {
            "status": status.status,
            "paper_count": status.paper_count,
            "citation_count": status.citation_count,
            "citation_artifact_paper_count": status.citation_artifact_paper_count,
            "missing_citation_artifact_paper_count": status.missing_citation_artifact_paper_count,
            "papers_with_citation_artifacts": [
                _paper_ref_to_dict(paper) for paper in status.papers_with_citations
            ],
            "papers_missing_citation_artifacts": [
                _paper_ref_to_dict(paper) for paper in status.papers_missing_citations
            ],
            "papers_with_citations": [
                _paper_ref_to_dict(paper) for paper in status.papers_with_citations
            ],
            "papers_missing_citations": [
                _paper_ref_to_dict(paper) for paper in status.papers_missing_citations
            ],
            "note": status.note,
        },
    }


def export_research_relations(db_path: Path, out_path: Path, *, output_format: str = "markdown") -> ResearchRelations:
    relations = build_research_relations(db_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "markdown":
        out_path.write_text(render_markdown(relations), encoding="utf-8")
    elif output_format == "json":
        payload = json.dumps(research_relations_to_dict(relations), ensure_ascii=False, indent=2, sort_keys=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        raise ValueError(f"unsupported research relations format: {output_format}")
    return relations
