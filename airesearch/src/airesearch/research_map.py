from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from airesearch.research_digest import FACT_TYPE_ORDER, DigestInputError, build_research_digest


@dataclass(frozen=True)
class MapEvidence:
    paper_key: str
    statement: str
    confidence: float
    evidence_quote: str | None
    evidence_artifact_type: str | None
    evidence_source_path: str | None


@dataclass(frozen=True)
class MapPaperRef:
    paper_key: str
    title: str
    year: int | None
    venue: str
    code_links: list[dict[str, str]]


@dataclass(frozen=True)
class ResearchMapItem:
    key: str
    label: str
    paper_refs: list[MapPaperRef]
    evidence: list[MapEvidence]

    @property
    def paper_count(self) -> int:
        return len(self.paper_refs)

    @property
    def fact_count(self) -> int:
        return len(self.evidence)

    @property
    def average_confidence(self) -> float:
        if not self.evidence:
            return 0.0
        return sum(item.confidence for item in self.evidence) / len(self.evidence)


@dataclass(frozen=True)
class ResearchMap:
    generated_at: str
    paper_count: int
    fact_count: int
    sections: dict[str, list[ResearchMapItem]]

    @property
    def item_count(self) -> int:
        return sum(len(items) for items in self.sections.values())

    @property
    def fact_type_counts(self) -> dict[str, int]:
        return {fact_type: sum(item.fact_count for item in items) for fact_type, items in self.sections.items()}


def _normalize_label(value: str) -> str:
    stripped = value.strip().strip("*_`")
    collapsed = re.sub(r"\s+", " ", stripped)
    return collapsed.lower()


def _fact_type_title(fact_type: str) -> str:
    return fact_type.replace("_", " ").title()


def _paper_sort_key(paper: MapPaperRef) -> tuple[int, str, str]:
    year = paper.year if paper.year is not None else -1
    return (-year, paper.title.lower(), paper.paper_key)


def _item_sort_key(item: ResearchMapItem) -> tuple[int, int, float, str]:
    return (-item.paper_count, -item.fact_count, -item.average_confidence, item.label.lower())


def build_research_map(db_path: Path) -> ResearchMap:
    digest = build_research_digest(db_path)
    grouped: dict[str, dict[str, dict[str, Any]]] = {fact_type: {} for fact_type in FACT_TYPE_ORDER}

    for paper in digest.papers:
        paper_ref = MapPaperRef(
            paper_key=paper.paper_key,
            title=paper.title,
            year=paper.year,
            venue=paper.venue,
            code_links=paper.code_links,
        )
        for fact_type, facts in paper.facts.items():
            if fact_type not in grouped:
                grouped[fact_type] = {}
            for fact in facts:
                label = fact.name.strip() or fact.statement.strip() or "(unnamed fact)"
                key = _normalize_label(label)
                if not key:
                    key = "(unnamed fact)"
                item = grouped[fact_type].setdefault(
                    key,
                    {
                        "label": label,
                        "paper_refs": {},
                        "evidence": [],
                    },
                )
                item["paper_refs"][paper.paper_key] = paper_ref
                item["evidence"].append(
                    MapEvidence(
                        paper_key=paper.paper_key,
                        statement=fact.statement,
                        confidence=fact.confidence,
                        evidence_quote=fact.evidence_quote,
                        evidence_artifact_type=fact.evidence_artifact_type,
                        evidence_source_path=fact.evidence_source_path,
                    )
                )

    sections: dict[str, list[ResearchMapItem]] = {}
    ordered_types = [fact_type for fact_type in FACT_TYPE_ORDER if fact_type in grouped]
    ordered_types.extend(fact_type for fact_type in grouped if fact_type not in ordered_types)
    for fact_type in ordered_types:
        items: list[ResearchMapItem] = []
        for key, payload in grouped[fact_type].items():
            paper_refs = sorted(payload["paper_refs"].values(), key=_paper_sort_key)
            items.append(
                ResearchMapItem(
                    key=key,
                    label=payload["label"],
                    paper_refs=paper_refs,
                    evidence=payload["evidence"],
                )
            )
        if items:
            sections[fact_type] = sorted(items, key=_item_sort_key)

    return ResearchMap(
        generated_at=digest.generated_at,
        paper_count=digest.paper_count,
        fact_count=digest.fact_count,
        sections=sections,
    )


def _format_paper_ref(paper: MapPaperRef) -> str:
    parts = [paper.title]
    if paper.year:
        parts.append(str(paper.year))
    if paper.venue:
        parts.append(paper.venue)
    parts.append(f"`{paper.paper_key}`")
    return " | ".join(parts)


def render_markdown(research_map: ResearchMap) -> str:
    lines = [
        "# AIResearch Research Map",
        "",
        f"Generated: {research_map.generated_at}",
        f"Papers: {research_map.paper_count}",
        f"Facts: {research_map.fact_count}",
        f"Mapped items: {research_map.item_count}",
        "",
        "## Fact Type Counts",
        "",
    ]
    for fact_type in FACT_TYPE_ORDER:
        if fact_type in research_map.fact_type_counts:
            lines.append(f"- {_fact_type_title(fact_type)}: {research_map.fact_type_counts[fact_type]}")
    for fact_type, count in research_map.fact_type_counts.items():
        if fact_type not in FACT_TYPE_ORDER:
            lines.append(f"- {_fact_type_title(fact_type)}: {count}")
    lines.append("")

    ordered_types = [fact_type for fact_type in FACT_TYPE_ORDER if fact_type in research_map.sections]
    ordered_types.extend(fact_type for fact_type in research_map.sections if fact_type not in ordered_types)
    for fact_type in ordered_types:
        lines.extend([f"## {_fact_type_title(fact_type)}", ""])
        for item in research_map.sections[fact_type]:
            lines.extend(
                [
                    f"### {item.label}",
                    "",
                    (
                        f"Papers: {item.paper_count} | Facts: {item.fact_count} | "
                        f"Average confidence: {item.average_confidence:.2f}"
                    ),
                    "",
                    "Papers:",
                ]
            )
            for paper in item.paper_refs:
                lines.append(f"- {_format_paper_ref(paper)}")
                if paper.code_links:
                    lines.append("  Code: " + ", ".join(link["url"] for link in paper.code_links))
            lines.extend(["", "Evidence:"])
            for evidence in item.evidence:
                quote = evidence.evidence_quote or evidence.statement
                detail = f"- `{evidence.paper_key}`: {quote} (confidence: {evidence.confidence:.2f})"
                if evidence.evidence_artifact_type:
                    detail += f" [{evidence.evidence_artifact_type}]"
                if evidence.evidence_source_path:
                    detail += f" {evidence.evidence_source_path}"
                lines.append(detail)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def research_map_to_dict(research_map: ResearchMap) -> dict[str, Any]:
    ordered_types = [fact_type for fact_type in FACT_TYPE_ORDER if fact_type in research_map.sections]
    ordered_types.extend(fact_type for fact_type in research_map.sections if fact_type not in ordered_types)
    return {
        "generated_at": research_map.generated_at,
        "paper_count": research_map.paper_count,
        "fact_count": research_map.fact_count,
        "item_count": research_map.item_count,
        "fact_type_counts": research_map.fact_type_counts,
        "sections": [
            {
                "fact_type": fact_type,
                "title": _fact_type_title(fact_type),
                "items": [
                    {
                        "key": item.key,
                        "label": item.label,
                        "paper_count": item.paper_count,
                        "fact_count": item.fact_count,
                        "average_confidence": item.average_confidence,
                        "papers": [
                            {
                                "paper_key": paper.paper_key,
                                "title": paper.title,
                                "year": paper.year,
                                "venue": paper.venue,
                                "code_links": paper.code_links,
                            }
                            for paper in item.paper_refs
                        ],
                        "evidence": [
                            {
                                "paper_key": evidence.paper_key,
                                "statement": evidence.statement,
                                "confidence": evidence.confidence,
                                "evidence_quote": evidence.evidence_quote,
                                "evidence_artifact_type": evidence.evidence_artifact_type,
                                "evidence_source_path": evidence.evidence_source_path,
                            }
                            for evidence in item.evidence
                        ],
                    }
                    for item in research_map.sections[fact_type]
                ],
            }
            for fact_type in ordered_types
        ],
    }


def export_research_map(db_path: Path, out_path: Path, *, output_format: str = "markdown") -> ResearchMap:
    research_map = build_research_map(db_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "markdown":
        out_path.write_text(render_markdown(research_map), encoding="utf-8")
    elif output_format == "json":
        payload = json.dumps(research_map_to_dict(research_map), ensure_ascii=False, indent=2, sort_keys=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        raise ValueError(f"unsupported research map format: {output_format}")
    return research_map
