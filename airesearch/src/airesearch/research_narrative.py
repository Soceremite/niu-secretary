from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from airesearch.research_digest import FACT_TYPE_ORDER, DigestFact, DigestPaper, build_research_digest
from airesearch.research_synthesis import ExtractionTarget, ResearchSynthesis, build_research_synthesis


@dataclass(frozen=True)
class NarrativeFinding:
    fact_type: str
    paper_key: str
    paper_title: str
    fact_name: str
    statement: str
    confidence: float
    evidence_quote: str | None
    evidence_source_path: str | None


@dataclass(frozen=True)
class PriorityAction:
    paper_key: str
    title: str
    priority_score: int
    action: str


@dataclass(frozen=True)
class NarrativeReport:
    generated_at: str
    paper_count: int
    fact_count: int
    executive_summary: list[str]
    supported_areas: list[str]
    provisional_areas: list[str]
    representative_findings: list[NarrativeFinding]
    priority_actions: list[PriorityAction]
    evidence_cautions: list[str]

    @property
    def finding_count(self) -> int:
        return len(self.representative_findings)

    @property
    def action_count(self) -> int:
        return len(self.priority_actions)


def _fact_type_title(fact_type: str) -> str:
    return fact_type.replace("_", " ").title()


def _coverage_phrase(fact_type: str, paper_count: int, total_papers: int) -> str:
    return f"{_fact_type_title(fact_type)} is represented in {paper_count}/{total_papers} papers"


def _supported_areas(synthesis: ResearchSynthesis) -> list[str]:
    return [
        _coverage_phrase(item.fact_type, item.paper_count, synthesis.paper_count)
        + "; use it as a backbone for corpus-level reading."
        for item in synthesis.strong_coverage.fact_types
    ]


def _provisional_areas(synthesis: ResearchSynthesis) -> list[str]:
    areas = []
    for item in synthesis.moderate_coverage.fact_types:
        areas.append(
            _coverage_phrase(item.fact_type, item.paper_count, synthesis.paper_count)
            + "; keep paper-level caveats attached."
        )
    for item in synthesis.weak_coverage.fact_types:
        areas.append(
            _coverage_phrase(item.fact_type, item.paper_count, synthesis.paper_count)
            + "; treat broad conclusions as provisional."
        )
    return areas


def _finding_sort_key(item: tuple[DigestPaper, DigestFact]) -> tuple[float, str, str, str]:
    paper, fact = item
    return (-fact.confidence, paper.title.lower(), fact.name.lower(), fact.statement.lower())


def _select_representative_findings(papers: list[DigestPaper]) -> list[NarrativeFinding]:
    findings: list[NarrativeFinding] = []
    for fact_type in FACT_TYPE_ORDER:
        candidates: list[tuple[DigestPaper, DigestFact]] = []
        for paper in papers:
            for fact in paper.facts.get(fact_type, []):
                candidates.append((paper, fact))
        for paper, fact in sorted(candidates, key=_finding_sort_key)[:2]:
            findings.append(
                NarrativeFinding(
                    fact_type=fact_type,
                    paper_key=paper.paper_key,
                    paper_title=paper.title,
                    fact_name=fact.name,
                    statement=fact.statement,
                    confidence=fact.confidence,
                    evidence_quote=fact.evidence_quote,
                    evidence_source_path=fact.evidence_source_path,
                )
            )
    return findings


def _missing_fact_text(target: ExtractionTarget) -> str:
    if not target.missing_fact_types:
        return "no required fact types"
    return ", ".join(_fact_type_title(item) for item in target.missing_fact_types)


def _action_text(target: ExtractionTarget) -> str:
    code_text = "code links present" if target.has_code_links else "code links missing"
    return (
        f"Review `{target.paper_key}` for missing fact types: {_missing_fact_text(target)}; "
        f"repair {target.missing_evidence_source_path_count} missing evidence source paths; {code_text}."
    )


def _priority_actions(synthesis: ResearchSynthesis) -> list[PriorityAction]:
    return [
        PriorityAction(
            paper_key=target.paper_key,
            title=target.title,
            priority_score=target.priority_score,
            action=_action_text(target),
        )
        for target in synthesis.extraction_targets[:5]
    ]


def _evidence_cautions(synthesis: ResearchSynthesis) -> list[str]:
    cautions = []
    if synthesis.missing_evidence_source_path_count:
        cautions.append(
            f"{synthesis.missing_evidence_source_path_count} facts lack evidence source paths; do not quote them downstream until repaired."
        )
    else:
        cautions.append("All stored facts include evidence source paths.")
    if synthesis.papers_without_code_links:
        cautions.append(
            f"{synthesis.papers_without_code_links} papers have no extracted code links; implementation availability is incomplete."
        )
    else:
        cautions.append("All papers have extracted code links.")
    if synthesis.papers_missing_fact_types:
        cautions.append(
            f"{synthesis.papers_missing_fact_types} papers are missing at least one required fact type."
        )
    else:
        cautions.append("All papers include every required fact type.")
    return cautions


def _executive_summary(synthesis: ResearchSynthesis) -> list[str]:
    strong = ", ".join(_fact_type_title(item.fact_type) for item in synthesis.strong_coverage.fact_types) or "none"
    moderate = ", ".join(_fact_type_title(item.fact_type) for item in synthesis.moderate_coverage.fact_types) or "none"
    weak = ", ".join(_fact_type_title(item.fact_type) for item in synthesis.weak_coverage.fact_types) or "none"
    return [
        f"The current corpus contains {synthesis.paper_count} papers and {synthesis.fact_count} extracted research facts.",
        f"Strongly represented fact types: {strong}. Moderately represented: {moderate}. Under-covered: {weak}.",
        (
            f"Follow-up work should prioritize {synthesis.extraction_target_count} extraction targets, "
            f"{synthesis.papers_without_code_links} papers without code links, and "
            f"{synthesis.missing_evidence_source_path_count} missing evidence source paths."
        ),
    ]


def build_narrative_report(db_path: Path) -> NarrativeReport:
    digest = build_research_digest(db_path)
    synthesis = build_research_synthesis(db_path)
    return NarrativeReport(
        generated_at=synthesis.generated_at,
        paper_count=synthesis.paper_count,
        fact_count=synthesis.fact_count,
        executive_summary=_executive_summary(synthesis),
        supported_areas=_supported_areas(synthesis),
        provisional_areas=_provisional_areas(synthesis),
        representative_findings=_select_representative_findings(digest.papers),
        priority_actions=_priority_actions(synthesis),
        evidence_cautions=_evidence_cautions(synthesis),
    )


def render_markdown(report: NarrativeReport) -> str:
    lines = [
        "# AIResearch Narrative Report",
        "",
        f"Generated: {report.generated_at}",
        f"Papers: {report.paper_count}",
        f"Facts: {report.fact_count}",
        "",
        "## Executive Summary",
        "",
    ]
    for item in report.executive_summary:
        lines.append(f"- {item}")
    lines.extend(["", "## What Is Well Supported", ""])
    if report.supported_areas:
        for item in report.supported_areas:
            lines.append(f"- {item}")
    else:
        lines.append("No fact type is strongly represented yet.")
    lines.extend(["", "## What Is Provisional", ""])
    if report.provisional_areas:
        for item in report.provisional_areas:
            lines.append(f"- {item}")
    else:
        lines.append("No moderate or weak coverage areas are currently flagged.")
    lines.extend(["", "## Representative Findings", ""])
    if report.representative_findings:
        for finding in report.representative_findings:
            name = f"{finding.fact_name}: " if finding.fact_name else ""
            lines.append(
                f"- {_fact_type_title(finding.fact_type)} | `{finding.paper_key}` | "
                f"{name}{finding.statement} (confidence: {finding.confidence:.2f})"
            )
            if finding.evidence_quote:
                evidence = f"  Evidence: {finding.evidence_quote}"
                if finding.evidence_source_path:
                    evidence += f" {finding.evidence_source_path}"
                lines.append(evidence)
    else:
        lines.append("No representative findings are available.")
    lines.extend(["", "## Priority Follow-Up Actions", ""])
    if report.priority_actions:
        for action in report.priority_actions:
            lines.append(f"- {action.title} | priority {action.priority_score}: {action.action}")
    else:
        lines.append("No priority actions remain under the current deterministic checks.")
    lines.extend(["", "## Evidence Cautions", ""])
    for caution in report.evidence_cautions:
        lines.append(f"- {caution}")
    return "\n".join(lines).rstrip() + "\n"


def narrative_report_to_dict(report: NarrativeReport) -> dict[str, Any]:
    return {
        "generated_at": report.generated_at,
        "paper_count": report.paper_count,
        "fact_count": report.fact_count,
        "executive_summary": report.executive_summary,
        "supported_areas": report.supported_areas,
        "provisional_areas": report.provisional_areas,
        "finding_count": report.finding_count,
        "representative_findings": [
            {
                "fact_type": finding.fact_type,
                "paper_key": finding.paper_key,
                "paper_title": finding.paper_title,
                "fact_name": finding.fact_name,
                "statement": finding.statement,
                "confidence": finding.confidence,
                "evidence_quote": finding.evidence_quote,
                "evidence_source_path": finding.evidence_source_path,
            }
            for finding in report.representative_findings
        ],
        "action_count": report.action_count,
        "priority_actions": [
            {
                "paper_key": action.paper_key,
                "title": action.title,
                "priority_score": action.priority_score,
                "action": action.action,
            }
            for action in report.priority_actions
        ],
        "evidence_cautions": report.evidence_cautions,
    }


def export_narrative_report(db_path: Path, out_path: Path, *, output_format: str = "markdown") -> NarrativeReport:
    report = build_narrative_report(db_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "markdown":
        out_path.write_text(render_markdown(report), encoding="utf-8")
    elif output_format == "json":
        payload = json.dumps(narrative_report_to_dict(report), ensure_ascii=False, indent=2, sort_keys=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        raise ValueError(f"unsupported narrative report format: {output_format}")
    return report
