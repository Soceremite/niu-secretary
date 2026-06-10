from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from airesearch.research_gap_analysis import FactTypeCoverage, PaperGap, build_gap_analysis


@dataclass(frozen=True)
class CoverageBand:
    name: str
    fact_types: list[FactTypeCoverage]


@dataclass(frozen=True)
class ExtractionTarget:
    paper_key: str
    title: str
    year: int | None
    venue: str
    missing_fact_types: list[str]
    missing_evidence_source_path_count: int
    has_code_links: bool
    priority_score: int


@dataclass(frozen=True)
class SynthesisNote:
    fact_type: str
    coverage_ratio: float
    paper_count: int
    fact_count: int
    note: str


@dataclass(frozen=True)
class ResearchSynthesis:
    generated_at: str
    paper_count: int
    fact_count: int
    required_fact_types: list[str]
    strong_coverage: CoverageBand
    moderate_coverage: CoverageBand
    weak_coverage: CoverageBand
    papers_missing_fact_types: int
    papers_without_code_links: int
    missing_evidence_source_path_count: int
    extraction_targets: list[ExtractionTarget]
    synthesis_notes: list[SynthesisNote]

    @property
    def extraction_target_count(self) -> int:
        return len(self.extraction_targets)


def _fact_type_title(fact_type: str) -> str:
    return fact_type.replace("_", " ").title()


def _band_name(item: FactTypeCoverage) -> str:
    if item.coverage_ratio >= 0.8:
        return "strong"
    if item.coverage_ratio >= 0.5:
        return "moderate"
    return "weak"


def _note_for_band(name: str) -> str:
    if name == "strong":
        return "Well covered across the current corpus; use these facts as the backbone for synthesis."
    if name == "moderate":
        return "Partially covered; use with paper-level caveats and prioritize missing papers before broad claims."
    return "Under-covered; treat conclusions as provisional until more papers include this fact type."


def _priority_score(paper: PaperGap) -> int:
    score = len(paper.missing_fact_types) * 10
    score += paper.missing_evidence_source_path_count
    if not paper.has_code_links:
        score += 5
    return score


def _build_extraction_target(paper: PaperGap) -> ExtractionTarget:
    return ExtractionTarget(
        paper_key=paper.paper_key,
        title=paper.title,
        year=paper.year,
        venue=paper.venue,
        missing_fact_types=paper.missing_fact_types,
        missing_evidence_source_path_count=paper.missing_evidence_source_path_count,
        has_code_links=paper.has_code_links,
        priority_score=_priority_score(paper),
    )


def _target_sort_key(target: ExtractionTarget) -> tuple[int, str, str]:
    return (-target.priority_score, target.title.lower(), target.paper_key)


def build_research_synthesis(db_path: Path) -> ResearchSynthesis:
    analysis = build_gap_analysis(db_path)
    grouped = {"strong": [], "moderate": [], "weak": []}
    notes: list[SynthesisNote] = []

    for item in analysis.fact_type_coverage:
        band = _band_name(item)
        grouped[band].append(item)
        notes.append(
            SynthesisNote(
                fact_type=item.fact_type,
                coverage_ratio=item.coverage_ratio,
                paper_count=item.paper_count,
                fact_count=item.fact_count,
                note=_note_for_band(band),
            )
        )

    targets = [
        _build_extraction_target(paper)
        for paper in analysis.papers
        if paper.missing_fact_types or paper.missing_evidence_source_path_count or not paper.has_code_links
    ]

    return ResearchSynthesis(
        generated_at=analysis.generated_at,
        paper_count=analysis.paper_count,
        fact_count=analysis.fact_count,
        required_fact_types=analysis.required_fact_types,
        strong_coverage=CoverageBand(name="strong", fact_types=grouped["strong"]),
        moderate_coverage=CoverageBand(name="moderate", fact_types=grouped["moderate"]),
        weak_coverage=CoverageBand(name="weak", fact_types=grouped["weak"]),
        papers_missing_fact_types=len(analysis.papers_missing_fact_types),
        papers_without_code_links=len(analysis.papers_without_code_links),
        missing_evidence_source_path_count=analysis.missing_evidence_source_path_count,
        extraction_targets=sorted(targets, key=_target_sort_key),
        synthesis_notes=notes,
    )


def _format_coverage_item(item: FactTypeCoverage, paper_count: int) -> str:
    return (
        f"- {_fact_type_title(item.fact_type)}: "
        f"{item.paper_count}/{paper_count} papers, {item.fact_count} facts ({item.coverage_ratio:.0%})"
    )


def _render_coverage_band(title: str, band: CoverageBand, paper_count: int, empty_text: str) -> list[str]:
    lines = [f"## {title}", ""]
    if band.fact_types:
        for item in band.fact_types:
            lines.append(_format_coverage_item(item, paper_count))
    else:
        lines.append(empty_text)
    lines.append("")
    return lines


def _paper_label(target: ExtractionTarget) -> str:
    parts = [target.title]
    if target.year:
        parts.append(str(target.year))
    if target.venue:
        parts.append(target.venue)
    parts.append(f"`{target.paper_key}`")
    return " | ".join(parts)


def render_markdown(synthesis: ResearchSynthesis) -> str:
    lines = [
        "# AIResearch Research Synthesis",
        "",
        f"Generated: {synthesis.generated_at}",
        f"Papers: {synthesis.paper_count}",
        f"Facts: {synthesis.fact_count}",
        "Required fact types: " + ", ".join(_fact_type_title(item) for item in synthesis.required_fact_types),
        f"Papers missing fact types: {synthesis.papers_missing_fact_types}",
        f"Papers without code links: {synthesis.papers_without_code_links}",
        f"Missing evidence source paths: {synthesis.missing_evidence_source_path_count}",
        "",
    ]
    lines.extend(
        _render_coverage_band(
            "Strong Coverage",
            synthesis.strong_coverage,
            synthesis.paper_count,
            "No fact types have strong paper coverage yet.",
        )
    )
    lines.extend(
        _render_coverage_band(
            "Moderate Coverage",
            synthesis.moderate_coverage,
            synthesis.paper_count,
            "No fact types have moderate paper coverage.",
        )
    )
    lines.extend(
        _render_coverage_band(
            "Weak Coverage",
            synthesis.weak_coverage,
            synthesis.paper_count,
            "No fact types are below 50% paper coverage.",
        )
    )
    lines.extend(["## Evidence Quality", ""])
    if synthesis.missing_evidence_source_path_count:
        lines.append(
            f"{synthesis.missing_evidence_source_path_count} facts are missing evidence source paths; "
            "prioritize source-path repair before quoting those facts downstream."
        )
    else:
        lines.append("All facts have evidence source paths.")
    lines.extend(["", "## Code Availability", ""])
    if synthesis.papers_without_code_links:
        lines.append(f"{synthesis.papers_without_code_links} papers have no extracted code links.")
    else:
        lines.append("All papers have extracted code links.")
    lines.extend(["", "## Next Extraction Targets", ""])
    if synthesis.extraction_targets:
        for target in synthesis.extraction_targets:
            missing = ", ".join(_fact_type_title(item) for item in target.missing_fact_types) or "none"
            source_paths = target.missing_evidence_source_path_count
            code = "yes" if target.has_code_links else "no"
            lines.append(
                f"- {_paper_label(target)}: priority {target.priority_score}; "
                f"missing fact types: {missing}; missing source paths: {source_paths}; code links: {code}"
            )
    else:
        lines.append("No extraction targets remain under the current deterministic checks.")
    lines.extend(["", "## Fact Type Synthesis Notes", ""])
    for note in synthesis.synthesis_notes:
        lines.append(
            f"- {_fact_type_title(note.fact_type)}: {note.note} "
            f"Coverage {note.paper_count}/{synthesis.paper_count} papers, {note.fact_count} facts."
        )
    return "\n".join(lines).rstrip() + "\n"


def _coverage_band_to_dict(band: CoverageBand) -> dict[str, Any]:
    return {
        "name": band.name,
        "fact_types": [
            {
                "fact_type": item.fact_type,
                "paper_count": item.paper_count,
                "fact_count": item.fact_count,
                "coverage_ratio": item.coverage_ratio,
            }
            for item in band.fact_types
        ],
    }


def research_synthesis_to_dict(synthesis: ResearchSynthesis) -> dict[str, Any]:
    return {
        "generated_at": synthesis.generated_at,
        "paper_count": synthesis.paper_count,
        "fact_count": synthesis.fact_count,
        "required_fact_types": synthesis.required_fact_types,
        "strong_coverage": _coverage_band_to_dict(synthesis.strong_coverage),
        "moderate_coverage": _coverage_band_to_dict(synthesis.moderate_coverage),
        "weak_coverage": _coverage_band_to_dict(synthesis.weak_coverage),
        "papers_missing_fact_types": synthesis.papers_missing_fact_types,
        "papers_without_code_links": synthesis.papers_without_code_links,
        "missing_evidence_source_path_count": synthesis.missing_evidence_source_path_count,
        "extraction_target_count": synthesis.extraction_target_count,
        "extraction_targets": [
            {
                "paper_key": target.paper_key,
                "title": target.title,
                "year": target.year,
                "venue": target.venue,
                "missing_fact_types": target.missing_fact_types,
                "missing_evidence_source_path_count": target.missing_evidence_source_path_count,
                "has_code_links": target.has_code_links,
                "priority_score": target.priority_score,
            }
            for target in synthesis.extraction_targets
        ],
        "synthesis_notes": [
            {
                "fact_type": note.fact_type,
                "coverage_ratio": note.coverage_ratio,
                "paper_count": note.paper_count,
                "fact_count": note.fact_count,
                "note": note.note,
            }
            for note in synthesis.synthesis_notes
        ],
    }


def export_research_synthesis(db_path: Path, out_path: Path, *, output_format: str = "markdown") -> ResearchSynthesis:
    synthesis = build_research_synthesis(db_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "markdown":
        out_path.write_text(render_markdown(synthesis), encoding="utf-8")
    elif output_format == "json":
        payload = json.dumps(research_synthesis_to_dict(synthesis), ensure_ascii=False, indent=2, sort_keys=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        raise ValueError(f"unsupported research synthesis format: {output_format}")
    return synthesis
