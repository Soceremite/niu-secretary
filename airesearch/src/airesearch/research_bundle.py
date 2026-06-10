from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from airesearch.artifact_ledger import export_artifact_ledger
from airesearch.research_digest import export_research_digest, utc_now
from airesearch.research_clusters import export_research_clusters
from airesearch.research_gap_analysis import export_gap_analysis
from airesearch.research_map import export_research_map
from airesearch.research_narrative import export_narrative_report
from airesearch.research_relations import export_research_relations
from airesearch.research_review_summary import export_reviewed_cluster_summary
from airesearch.research_synthesis import export_research_synthesis


@dataclass(frozen=True)
class ReportArtifact:
    name: str
    title: str
    markdown_path: str
    json_path: str
    paper_count: int
    fact_count: int
    extra_counts: dict[str, int]


@dataclass(frozen=True)
class ReportBundle:
    generated_at: str
    out_dir: str
    paper_count: int
    fact_count: int
    artifacts: list[ReportArtifact]
    manifest_path: str = "manifest.json"
    index_path: str = "index.md"

    @property
    def report_count(self) -> int:
        return len(self.artifacts)

    @property
    def artifact_count(self) -> int:
        return (len(self.artifacts) * 2) + 2


ReportExporter = Callable[[Path, Path], Any]
PacketExporter = Callable[[Path, Path], Any]


def _export_markdown_and_json(
    db_path: Path,
    out_dir: Path,
    *,
    name: str,
    title: str,
    markdown_file: str,
    json_file: str,
    exporter: ReportExporter,
    extra_counts: Callable[[Any], dict[str, int]],
) -> ReportArtifact:
    markdown_result = exporter(db_path, out_dir / markdown_file)
    exporter(db_path, out_dir / json_file, output_format="json")
    return ReportArtifact(
        name=name,
        title=title,
        markdown_path=markdown_file,
        json_path=json_file,
        paper_count=int(markdown_result.paper_count),
        fact_count=int(markdown_result.fact_count),
        extra_counts=extra_counts(markdown_result),
    )


def _export_packet_markdown_and_json(
    packet_path: Path,
    out_dir: Path,
    *,
    name: str,
    title: str,
    markdown_file: str,
    json_file: str,
    exporter: PacketExporter,
    extra_counts: Callable[[Any], dict[str, int]],
) -> ReportArtifact:
    markdown_result = exporter(packet_path, out_dir / markdown_file)
    exporter(packet_path, out_dir / json_file, output_format="json")
    return ReportArtifact(
        name=name,
        title=title,
        markdown_path=markdown_file,
        json_path=json_file,
        paper_count=int(markdown_result.source_paper_count),
        fact_count=int(markdown_result.source_fact_count),
        extra_counts=extra_counts(markdown_result),
    )


def _bundle_to_dict(bundle: ReportBundle) -> dict[str, Any]:
    return {
        "generated_at": bundle.generated_at,
        "out_dir": bundle.out_dir,
        "paper_count": bundle.paper_count,
        "fact_count": bundle.fact_count,
        "report_count": bundle.report_count,
        "artifact_count": bundle.artifact_count,
        "manifest_path": bundle.manifest_path,
        "index_path": bundle.index_path,
        "artifacts": [
            {
                "name": artifact.name,
                "title": artifact.title,
                "markdown_path": artifact.markdown_path,
                "json_path": artifact.json_path,
                "paper_count": artifact.paper_count,
                "fact_count": artifact.fact_count,
                "extra_counts": artifact.extra_counts,
            }
            for artifact in bundle.artifacts
        ],
    }


def render_index(bundle: ReportBundle) -> str:
    lines = [
        "# AIResearch Report Bundle",
        "",
        f"Generated: {bundle.generated_at}",
        f"Papers: {bundle.paper_count}",
        f"Facts: {bundle.fact_count}",
        f"Reports: {bundle.report_count}",
        f"Files: {bundle.artifact_count}",
        "",
        "## Reports",
        "",
        "| Report | Markdown | JSON | Extra Counts |",
        "| --- | --- | --- | --- |",
    ]
    for artifact in bundle.artifacts:
        if artifact.extra_counts:
            extras = ", ".join(f"{key}: {value}" for key, value in artifact.extra_counts.items())
        else:
            extras = "none"
        lines.append(
            f"| {artifact.title} | [{artifact.markdown_path}]({artifact.markdown_path}) | "
            f"[{artifact.json_path}]({artifact.json_path}) | {extras} |"
        )
    lines.extend(["", "## Manifest", "", f"- [{bundle.manifest_path}]({bundle.manifest_path})"])
    return "\n".join(lines).rstrip() + "\n"


def export_report_bundle(
    db_path: Path,
    out_dir: Path,
    *,
    review_packet_path: Path | None = None,
) -> ReportBundle:
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts = [
        _export_markdown_and_json(
            db_path,
            out_dir,
            name="digest",
            title="Research Digest",
            markdown_file="digest.md",
            json_file="digest.json",
            exporter=export_research_digest,
            extra_counts=lambda _report: {},
        ),
        _export_markdown_and_json(
            db_path,
            out_dir,
            name="artifact-ledger",
            title="Artifact Ledger",
            markdown_file="artifact-ledger.md",
            json_file="artifact-ledger.json",
            exporter=export_artifact_ledger,
            extra_counts=lambda report: {
                "chunk_count": int(report.chunk_count),
                "equation_count": int(report.equation_count),
                "citation_count": int(report.citation_count),
            },
        ),
        _export_markdown_and_json(
            db_path,
            out_dir,
            name="map",
            title="Research Map",
            markdown_file="map.md",
            json_file="map.json",
            exporter=export_research_map,
            extra_counts=lambda report: {"item_count": int(report.item_count)},
        ),
        _export_markdown_and_json(
            db_path,
            out_dir,
            name="relations",
            title="Cross-Paper Relations",
            markdown_file="relations.md",
            json_file="relations.json",
            exporter=export_research_relations,
            extra_counts=lambda report: {
                "relation_count": int(report.relation_count),
                "code_relation_count": int(report.code_relation_count),
                "dataset_relation_count": int(report.dataset_relation_count),
                "citation_artifact_paper_count": int(report.citation_status.citation_artifact_paper_count),
            },
        ),
        _export_markdown_and_json(
            db_path,
            out_dir,
            name="gap-analysis",
            title="Gap Analysis",
            markdown_file="gap-analysis.md",
            json_file="gap-analysis.json",
            exporter=export_gap_analysis,
            extra_counts=lambda report: {
                "papers_missing_fact_types": len(report.papers_missing_fact_types),
                "papers_without_code_links": len(report.papers_without_code_links),
                "missing_evidence_source_path_count": int(report.missing_evidence_source_path_count),
            },
        ),
        _export_markdown_and_json(
            db_path,
            out_dir,
            name="synthesis",
            title="Research Synthesis",
            markdown_file="synthesis.md",
            json_file="synthesis.json",
            exporter=export_research_synthesis,
            extra_counts=lambda report: {"extraction_target_count": int(report.extraction_target_count)},
        ),
        _export_markdown_and_json(
            db_path,
            out_dir,
            name="narrative",
            title="Narrative Report",
            markdown_file="narrative.md",
            json_file="narrative.json",
            exporter=export_narrative_report,
            extra_counts=lambda report: {
                "finding_count": int(report.finding_count),
                "action_count": int(report.action_count),
            },
        ),
        _export_markdown_and_json(
            db_path,
            out_dir,
            name="clusters",
            title="Research Clusters",
            markdown_file="clusters.md",
            json_file="clusters.json",
            exporter=export_research_clusters,
            extra_counts=lambda report: {
                "cluster_count": int(report.cluster_count),
                "clustered_fact_count": int(report.clustered_fact_count),
                "singleton_count": int(report.singleton_count),
            },
        ),
    ]
    if review_packet_path is not None:
        artifacts.append(
            _export_packet_markdown_and_json(
                review_packet_path,
                out_dir,
                name="reviewed-clusters",
                title="Reviewed Cluster Summary",
                markdown_file="reviewed-clusters.md",
                json_file="reviewed-clusters.json",
                exporter=export_reviewed_cluster_summary,
                extra_counts=lambda report: {
                    "accepted_count": int(report.accepted_count),
                    "accepted_fact_count": int(report.accepted_fact_count),
                    "accepted_paper_count": int(report.accepted_paper_count),
                },
            )
        )
    paper_count = artifacts[0].paper_count if artifacts else 0
    fact_count = artifacts[0].fact_count if artifacts else 0
    bundle = ReportBundle(
        generated_at=utc_now(),
        out_dir=str(out_dir),
        paper_count=paper_count,
        fact_count=fact_count,
        artifacts=artifacts,
    )
    (out_dir / bundle.manifest_path).write_text(
        json.dumps(_bundle_to_dict(bundle), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / bundle.index_path).write_text(render_index(bundle), encoding="utf-8")
    return bundle
