from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from airesearch.research_digest import FACT_TYPE_ORDER, DigestInputError, build_research_digest


@dataclass(frozen=True)
class FactTypeCoverage:
    fact_type: str
    paper_count: int
    fact_count: int
    coverage_ratio: float


@dataclass(frozen=True)
class PaperGap:
    paper_key: str
    title: str
    year: int | None
    venue: str
    fact_counts: dict[str, int]
    missing_fact_types: list[str]
    total_facts: int
    has_code_links: bool
    missing_evidence_source_path_count: int


@dataclass(frozen=True)
class GapAnalysis:
    generated_at: str
    paper_count: int
    fact_count: int
    required_fact_types: list[str]
    fact_type_coverage: list[FactTypeCoverage]
    papers: list[PaperGap]
    missing_evidence_source_path_count: int

    @property
    def low_coverage_fact_types(self) -> list[FactTypeCoverage]:
        return [item for item in self.fact_type_coverage if item.coverage_ratio < 0.5]

    @property
    def papers_missing_fact_types(self) -> list[PaperGap]:
        return [paper for paper in self.papers if paper.missing_fact_types]

    @property
    def papers_without_code_links(self) -> list[PaperGap]:
        return [paper for paper in self.papers if not paper.has_code_links]


def _fact_type_title(fact_type: str) -> str:
    return fact_type.replace("_", " ").title()


def build_gap_analysis(db_path: Path) -> GapAnalysis:
    digest = build_research_digest(db_path)
    fact_type_papers: dict[str, int] = {fact_type: 0 for fact_type in FACT_TYPE_ORDER}
    fact_type_facts: dict[str, int] = {fact_type: 0 for fact_type in FACT_TYPE_ORDER}
    papers: list[PaperGap] = []
    missing_evidence_source_path_count = 0

    for paper in digest.papers:
        fact_counts = {fact_type: len(paper.facts.get(fact_type, [])) for fact_type in FACT_TYPE_ORDER}
        for fact_type, count in fact_counts.items():
            if count:
                fact_type_papers[fact_type] += 1
                fact_type_facts[fact_type] += count
        missing_fact_types = [fact_type for fact_type, count in fact_counts.items() if count == 0]
        paper_missing_sources = 0
        for facts in paper.facts.values():
            for fact in facts:
                if not fact.evidence_source_path:
                    paper_missing_sources += 1
        missing_evidence_source_path_count += paper_missing_sources
        papers.append(
            PaperGap(
                paper_key=paper.paper_key,
                title=paper.title,
                year=paper.year,
                venue=paper.venue,
                fact_counts=fact_counts,
                missing_fact_types=missing_fact_types,
                total_facts=sum(fact_counts.values()),
                has_code_links=bool(paper.code_links),
                missing_evidence_source_path_count=paper_missing_sources,
            )
        )

    fact_type_coverage = [
        FactTypeCoverage(
            fact_type=fact_type,
            paper_count=fact_type_papers[fact_type],
            fact_count=fact_type_facts[fact_type],
            coverage_ratio=(fact_type_papers[fact_type] / digest.paper_count if digest.paper_count else 0.0),
        )
        for fact_type in FACT_TYPE_ORDER
    ]

    return GapAnalysis(
        generated_at=digest.generated_at,
        paper_count=digest.paper_count,
        fact_count=digest.fact_count,
        required_fact_types=list(FACT_TYPE_ORDER),
        fact_type_coverage=fact_type_coverage,
        papers=papers,
        missing_evidence_source_path_count=missing_evidence_source_path_count,
    )


def _paper_label(paper: PaperGap) -> str:
    parts = [paper.title]
    if paper.year:
        parts.append(str(paper.year))
    if paper.venue:
        parts.append(paper.venue)
    parts.append(f"`{paper.paper_key}`")
    return " | ".join(parts)


def render_markdown(analysis: GapAnalysis) -> str:
    lines = [
        "# AIResearch Gap Analysis",
        "",
        f"Generated: {analysis.generated_at}",
        f"Papers: {analysis.paper_count}",
        f"Facts: {analysis.fact_count}",
        f"Papers missing fact types: {len(analysis.papers_missing_fact_types)}",
        f"Papers without code links: {len(analysis.papers_without_code_links)}",
        f"Missing evidence source paths: {analysis.missing_evidence_source_path_count}",
        "",
        "## Fact Type Coverage",
        "",
        "| Fact Type | Papers | Facts | Coverage |",
        "| --- | ---: | ---: | ---: |",
    ]
    for item in analysis.fact_type_coverage:
        lines.append(
            f"| {_fact_type_title(item.fact_type)} | {item.paper_count} | "
            f"{item.fact_count} | {item.coverage_ratio:.0%} |"
        )

    lines.extend(["", "## Low-Coverage Fact Types", ""])
    if analysis.low_coverage_fact_types:
        for item in analysis.low_coverage_fact_types:
            lines.append(
                f"- {_fact_type_title(item.fact_type)}: "
                f"{item.paper_count}/{analysis.paper_count} papers ({item.coverage_ratio:.0%})"
            )
    else:
        lines.append("No fact types below 50% paper coverage.")

    lines.extend(["", "## Papers Missing Fact Types", ""])
    if analysis.papers_missing_fact_types:
        for paper in analysis.papers_missing_fact_types:
            missing = ", ".join(_fact_type_title(fact_type) for fact_type in paper.missing_fact_types)
            lines.append(f"- {_paper_label(paper)}: missing {missing}")
    else:
        lines.append("No papers are missing required fact types.")

    lines.extend(["", "## Papers Without Code Links", ""])
    if analysis.papers_without_code_links:
        for paper in analysis.papers_without_code_links:
            lines.append(f"- {_paper_label(paper)}")
    else:
        lines.append("All papers have code links.")

    lines.extend(["", "## Evidence Source Path Gaps", ""])
    if analysis.missing_evidence_source_path_count:
        for paper in analysis.papers:
            if paper.missing_evidence_source_path_count:
                lines.append(
                    f"- {_paper_label(paper)}: "
                    f"{paper.missing_evidence_source_path_count} facts missing source paths"
                )
    else:
        lines.append("No evidence source path gaps.")

    return "\n".join(lines).rstrip() + "\n"


def gap_analysis_to_dict(analysis: GapAnalysis) -> dict[str, Any]:
    return {
        "generated_at": analysis.generated_at,
        "paper_count": analysis.paper_count,
        "fact_count": analysis.fact_count,
        "required_fact_types": analysis.required_fact_types,
        "fact_type_coverage": [
            {
                "fact_type": item.fact_type,
                "paper_count": item.paper_count,
                "fact_count": item.fact_count,
                "coverage_ratio": item.coverage_ratio,
            }
            for item in analysis.fact_type_coverage
        ],
        "low_coverage_fact_types": [
            {
                "fact_type": item.fact_type,
                "paper_count": item.paper_count,
                "fact_count": item.fact_count,
                "coverage_ratio": item.coverage_ratio,
            }
            for item in analysis.low_coverage_fact_types
        ],
        "papers": [
            {
                "paper_key": paper.paper_key,
                "title": paper.title,
                "year": paper.year,
                "venue": paper.venue,
                "fact_counts": paper.fact_counts,
                "missing_fact_types": paper.missing_fact_types,
                "total_facts": paper.total_facts,
                "has_code_links": paper.has_code_links,
                "missing_evidence_source_path_count": paper.missing_evidence_source_path_count,
            }
            for paper in analysis.papers
        ],
        "papers_missing_fact_types": [
            {
                "paper_key": paper.paper_key,
                "title": paper.title,
                "missing_fact_types": paper.missing_fact_types,
            }
            for paper in analysis.papers_missing_fact_types
        ],
        "papers_without_code_links": [
            {
                "paper_key": paper.paper_key,
                "title": paper.title,
            }
            for paper in analysis.papers_without_code_links
        ],
        "missing_evidence_source_path_count": analysis.missing_evidence_source_path_count,
    }


def export_gap_analysis(db_path: Path, out_path: Path, *, output_format: str = "markdown") -> GapAnalysis:
    analysis = build_gap_analysis(db_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "markdown":
        out_path.write_text(render_markdown(analysis), encoding="utf-8")
    elif output_format == "json":
        payload = json.dumps(gap_analysis_to_dict(analysis), ensure_ascii=False, indent=2, sort_keys=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        raise ValueError(f"unsupported gap analysis format: {output_format}")
    return analysis
