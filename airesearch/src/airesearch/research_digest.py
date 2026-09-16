from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db
from airesearch.knowledge_graph import code_link_payloads, parse_json


FACT_TYPE_ORDER = ["method", "dataset", "benchmark", "claim", "limitation"]


class DigestInputError(ValueError):
    pass


@dataclass(frozen=True)
class DigestFact:
    fact_id: int
    fact_type: str
    name: str
    statement: str
    confidence: float
    evidence_quote: str | None
    evidence_artifact_type: str | None
    evidence_source_path: str | None


@dataclass(frozen=True)
class DigestPaper:
    paper_key: str
    title: str
    authors: list[str]
    year: int | None
    venue: str
    ids: dict[str, Any]
    artifact_types: list[str]
    code_links: list[dict[str, str]]
    facts: dict[str, list[DigestFact]]
    # 日期标签：published = 论文发表时间（papi meta），added_at = 入库时间（缺失时退回 created_at）
    published_date: str = ""
    added_at: str = ""


@dataclass(frozen=True)
class ResearchDigest:
    generated_at: str
    papers: list[DigestPaper]

    @property
    def paper_count(self) -> int:
        return len(self.papers)

    @property
    def fact_count(self) -> int:
        return sum(len(facts) for paper in self.papers for facts in paper.facts.values())


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _fact_groups(conn, paper_key: str) -> dict[str, list[DigestFact]]:
    rows = conn.execute(
        """
        select
            f.id, f.fact_type, f.name, f.statement, f.confidence,
            p.evidence_quote, p.evidence_artifact_type, p.evidence_source_path
        from research_facts f
        left join research_fact_provenance p on p.fact_id = f.id
        where f.paper_key = ?
        order by f.fact_type, f.confidence desc, f.id
        """,
        (paper_key,),
    ).fetchall()
    groups: dict[str, list[DigestFact]] = {fact_type: [] for fact_type in FACT_TYPE_ORDER}
    for row in rows:
        fact_type = row["fact_type"]
        if fact_type not in groups:
            groups[fact_type] = []
        groups[fact_type].append(
            DigestFact(
                fact_id=int(row["id"]),
                fact_type=fact_type,
                name=row["name"] or "",
                statement=row["statement"] or "",
                confidence=float(row["confidence"] or 0.0),
                evidence_quote=row["evidence_quote"],
                evidence_artifact_type=row["evidence_artifact_type"],
                evidence_source_path=row["evidence_source_path"],
            )
        )
    return {fact_type: facts for fact_type, facts in groups.items() if facts}


def build_research_digest(db_path: Path) -> ResearchDigest:
    init_db(db_path)
    with connect(db_path) as conn:
        card_rows = conn.execute(
            """
            select * from paper_cards
            order by year desc, title, paper_key
            """
        ).fetchall()
        if not card_rows:
            raise DigestInputError("paper_cards is empty; run extract-paper-cards before generating a digest")

        papers: list[DigestPaper] = []
        # 日期标签来源：papers.meta_json 的 published/added，added 缺失时退回 papers.created_at
        date_lookup: dict[str, dict[str, str]] = {}
        for date_row in conn.execute("select paper_key, created_at, meta_json from papers").fetchall():
            meta = parse_json(date_row["meta_json"], {})
            published = ""
            added = ""
            if isinstance(meta, dict):
                published = str(meta.get("published") or "").strip()
                added = str(meta.get("added") or "").strip()
            date_lookup[str(date_row["paper_key"])] = {
                "published_date": published,
                "added_at": added or str(date_row["created_at"] or "").strip(),
            }
        for row in card_rows:
            authors = parse_json(row["authors_json"], [])
            if not isinstance(authors, list):
                authors = []
            ids = parse_json(row["ids_json"], {})
            if not isinstance(ids, dict):
                ids = {}
            artifact_types = parse_json(row["artifact_types_json"], [])
            if not isinstance(artifact_types, list):
                artifact_types = []
            dates = date_lookup.get(str(row["paper_key"]), {})
            papers.append(
                DigestPaper(
                    paper_key=row["paper_key"],
                    title=row["title"] or row["paper_key"],
                    authors=[str(author) for author in authors if str(author).strip()],
                    year=row["year"],
                    venue=row["venue"] or "",
                    ids=ids,
                    artifact_types=[str(item) for item in artifact_types],
                    code_links=code_link_payloads(conn, row["paper_key"]),
                    facts=_fact_groups(conn, row["paper_key"]),
                    published_date=dates.get("published_date", ""),
                    added_at=dates.get("added_at", ""),
                )
            )
    return ResearchDigest(generated_at=utc_now(), papers=papers)


def _fact_type_title(fact_type: str) -> str:
    return fact_type.replace("_", " ").title()


def _metadata_line(paper: DigestPaper) -> str:
    parts = []
    if paper.authors:
        parts.append("authors: " + ", ".join(paper.authors))
    if paper.year:
        parts.append(f"year: {paper.year}")
    if paper.venue:
        parts.append(f"venue: {paper.venue}")
    if paper.artifact_types:
        parts.append("artifacts: " + ", ".join(paper.artifact_types))
    if paper.code_links:
        parts.append("code: " + ", ".join(link["url"] for link in paper.code_links))
    return " | ".join(parts) if parts else "metadata: unavailable"


def render_markdown(digest: ResearchDigest) -> str:
    lines = [
        "# AIResearch Digest",
        "",
        f"Generated: {digest.generated_at}",
        f"Papers: {digest.paper_count}",
        f"Facts: {digest.fact_count}",
        "",
    ]
    for paper in digest.papers:
        lines.extend([f"## {paper.title}", "", f"`{paper.paper_key}` | {_metadata_line(paper)}", ""])
        if not paper.facts:
            lines.extend(["No research facts available.", ""])
            continue
        ordered_types = [fact_type for fact_type in FACT_TYPE_ORDER if fact_type in paper.facts]
        ordered_types.extend(fact_type for fact_type in paper.facts if fact_type not in ordered_types)
        for fact_type in ordered_types:
            lines.extend([f"### {_fact_type_title(fact_type)}", ""])
            for fact in paper.facts[fact_type]:
                name = f"**{fact.name}**: " if fact.name else ""
                lines.append(f"- {name}{fact.statement} (confidence: {fact.confidence:.2f})")
                if fact.evidence_quote:
                    evidence = f"  Evidence: {fact.evidence_quote}"
                    if fact.evidence_artifact_type:
                        evidence += f" [{fact.evidence_artifact_type}]"
                    if fact.evidence_source_path:
                        evidence += f" {fact.evidence_source_path}"
                    lines.append(evidence)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def digest_to_dict(digest: ResearchDigest) -> dict[str, Any]:
    return {
        "generated_at": digest.generated_at,
        "paper_count": digest.paper_count,
        "fact_count": digest.fact_count,
        "papers": [
            {
                "paper_key": paper.paper_key,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "venue": paper.venue,
                "published_date": paper.published_date,
                "added_at": paper.added_at,
                "ids": paper.ids,
                "artifact_types": paper.artifact_types,
                "code_links": paper.code_links,
                "facts": {
                    fact_type: [
                        {
                            "fact_id": fact.fact_id,
                            "fact_type": fact.fact_type,
                            "name": fact.name,
                            "statement": fact.statement,
                            "confidence": fact.confidence,
                            "evidence_quote": fact.evidence_quote,
                            "evidence_artifact_type": fact.evidence_artifact_type,
                            "evidence_source_path": fact.evidence_source_path,
                        }
                        for fact in facts
                    ]
                    for fact_type, facts in paper.facts.items()
                },
            }
            for paper in digest.papers
        ],
    }


def export_research_digest(db_path: Path, out_path: Path, *, output_format: str = "markdown") -> ResearchDigest:
    digest = build_research_digest(db_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "markdown":
        out_path.write_text(render_markdown(digest), encoding="utf-8")
    elif output_format == "json":
        payload = json.dumps(digest_to_dict(digest), ensure_ascii=False, indent=2, sort_keys=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        raise ValueError(f"unsupported digest format: {output_format}")
    return digest
