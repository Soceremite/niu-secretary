from __future__ import annotations

import hashlib
import json
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from airesearch.artifact_ledger import export_artifact_ledger
from airesearch.db import connect, init_db
from airesearch.fact_translations import export_fact_translations
from airesearch.formula_ocr import FormulaOCRValidationError, is_likely_formula, normalize_formula_latex
from airesearch.knowledge_graph import parse_json
from airesearch.layout_evidence_graph import (
    SCHEMA_VERSION as EVIDENCE_GRAPH_SCHEMA_VERSION,
    export_layout_evidence_graph,
    extract_layout_evidence_graph,
)
from airesearch.layout_service import LayoutVisualCandidate, select_representative_visual
from airesearch.paper_blog import export_paper_blogs
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

PAPER_TEXT_ASSETS = {
    "summary.md": "summary_path",
    "tldr.md": "tldr_path",
    "summary.zh.md": "summary_zh_path",
    "tldr.zh.md": "tldr_zh_path",
}

COVER_CANDIDATE_NAMES = (
    "cover.webp",
    "cover.png",
    "cover.jpg",
    "cover.jpeg",
    "cover.svg",
)
LAYOUT_PROVIDER = "airesearch_layout"
LAYOUT_EVIDENCE_LIMITS = {"equations": 6, "tables": 4}
LAYOUT_TABLE_PREVIEW_ROWS = 12
LAYOUT_TABLE_PREVIEW_COLUMNS = 12
LAYOUT_TABLE_PREVIEW_CELL_CHARS = 160



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
        "data_artifacts": [
            {
                "name": "layout-evidence-graph",
                "path": "layout-evidence-graph.json",
                "schema_version": EVIDENCE_GRAPH_SCHEMA_VERSION,
            }
        ],
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


def _copy_file(source: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return str(target)


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:12]


def _cover_source_visual(db_path: Path, paper_key: str, source_dir: Path) -> LayoutVisualCandidate | None:
    return select_representative_visual(
        db_path,
        paper_key,
        source_dir=source_dir,
        cover_names=COVER_CANDIDATE_NAMES,
    )


def _export_paper_assets(db_path: Path, out_dir: Path) -> list[dict[str, Any]]:
    init_db(db_path)
    payload: list[dict[str, Any]] = []
    with connect(db_path) as conn:
        citation_rows = conn.execute(
            "select paper_key, citation_key from paper_citations order by paper_key, citation_index"
        ).fetchall()
        rows = conn.execute(
            """
            select paper_key, title, ids_json, artifact_types_json, source_dir
            from paper_cards
            order by updated_at desc, paper_key
            """
        ).fetchall()
    citations_by_paper: dict[str, list[str]] = {}
    for row in citation_rows:
        paper_key = str(row["paper_key"])
        citations_by_paper.setdefault(paper_key, []).append(str(row["citation_key"]))
    for row in rows:
        source_dir = Path(str(row["source_dir"] or ""))
        if not source_dir.exists() or not source_dir.is_dir():
            continue
        paper_key = str(row["paper_key"])
        asset_entry: dict[str, Any] = {
            "paper_key": paper_key,
            "title": str(row["title"] or ""),
            "ids": parse_json(row["ids_json"], {}),
            "artifact_types": parse_json(row["artifact_types_json"], []),
            "citation_keys": citations_by_paper.get(paper_key, []),
        }
        bundle_paper_dir = out_dir / "paper-assets" / paper_key
        for filename, key in PAPER_TEXT_ASSETS.items():
            source_path = source_dir / filename
            if not source_path.exists() or not source_path.is_file():
                continue
            target_path = bundle_paper_dir / filename
            _copy_file(source_path, target_path)
            asset_entry[key] = str(target_path.relative_to(out_dir))
        cover_visual = _cover_source_visual(db_path, paper_key, source_dir)
        if cover_visual is not None:
            cover_path = cover_visual.source_path
            target_name = f"{paper_key}-{_file_hash(cover_path)}{cover_path.suffix.lower()}"
            target_path = out_dir / "paper-assets" / "covers" / target_name
            _copy_file(cover_path, target_path)
            asset_entry["cover_path"] = str(target_path.relative_to(out_dir))
            asset_entry["cover_source_kind"] = cover_visual.source_kind
            asset_entry["cover_asset_kind"] = cover_visual.asset_kind
            asset_entry["cover_caption"] = cover_visual.caption
            asset_entry["cover_source_reference"] = cover_visual.source_reference
            asset_entry["cover_score"] = round(cover_visual.score, 2)
            asset_entry["cover_reason"] = cover_visual.reason
        payload.append(asset_entry)
    return payload




def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _collapse_text(value: Any, *, limit: int = 900) -> str:
    text = " ".join(str(value or "").replace("\r", "\n").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


def _layout_summary(stats_json: str) -> dict[str, Any]:
    stats = parse_json(stats_json, {})
    if not isinstance(stats, dict):
        return {}
    summary = stats.get("summary")
    if isinstance(summary, dict):
        return summary
    return stats


def _layout_block_score(row: Any, metadata: dict[str, Any]) -> float:
    return max(
        _safe_float(metadata.get("quality_score")),
        _safe_float(metadata.get("evidence_confidence")),
        _safe_float(metadata.get("formula_ocr_confidence")),
    ) + max(0, 20 - _safe_int(row["page_index"])) / 1000


def _layout_block_base(row: Any, metadata: dict[str, Any]) -> dict[str, Any]:
    score = _layout_block_score(row, metadata)
    return {
        "block_id": _safe_int(row["id"]),
        "page": _safe_int(row["page_index"]) + 1,
        "block_index": _safe_int(row["block_index"]),
        "quality_score": round(score, 4),
        "source_reference": f"page {_safe_int(row['page_index']) + 1}, block {_safe_int(row['block_index'])}",
        "asset_path": _collapse_text(row["asset_path"], limit=260),
    }


def _layout_equation_payload(row: Any, metadata: dict[str, Any]) -> dict[str, Any]:
    latex = metadata.get("formula_latex") or metadata.get("formula_ocr_candidate_latex") or row["text"] or ""
    payload = _layout_block_base(row, metadata)
    payload.update(
        {
            "equation_id": _collapse_text(metadata.get("equation_id") or f"eq-{row['id']}", limit=80),
            "role": _collapse_text(metadata.get("equation_role") or "formula", limit=80),
            "latex": _collapse_text(latex, limit=1000),
            "formula_ocr_status": _collapse_text(metadata.get("formula_ocr_status"), limit=80),
            "formula_ocr_model": _collapse_text(metadata.get("formula_ocr_model"), limit=120),
        }
    )
    return payload


def _canonical_equation_payload(row: Any) -> dict[str, Any] | None:
    raw_latex = str(row["latex"] or "").strip()
    if not raw_latex or "�" in raw_latex:
        return None
    try:
        latex = normalize_formula_latex(raw_latex)
    except FormulaOCRValidationError:
        return None
    latex = re.sub(r"\n?\s*\\label\{[^{}]+\}\s*$", "", latex).strip()
    if len(latex) < 8:
        return None

    equation_index = _safe_int(row["equation_index"])
    label = _collapse_text(row["label"], limit=80)
    equation_id = f"equation-{equation_index + 1}"
    source_label = label or f"Equation {equation_index + 1}"
    return {
        "block_id": 0,
        "page": 0,
        "block_index": equation_index,
        "quality_score": 1.0,
        "source_reference": f"equations.md · {source_label}",
        "asset_path": "",
        "equation_id": equation_id,
        "role": "source LaTeX",
        "latex": latex,
        "formula_ocr_status": "",
        "formula_ocr_model": "",
        "source_kind": "paperpipe_equations",
    }


def _layout_table_rows(value: Any) -> tuple[list[list[str]], int, int, bool]:
    if not isinstance(value, list):
        return [], 0, 0, False
    source_rows = [row for row in value if isinstance(row, list)]
    row_count = len(source_rows)
    column_count = max((len(row) for row in source_rows), default=0)
    def preview_cell(value: Any) -> str:
        text = " ".join(str(value or "").replace("\r", "\n").split())
        if len(text) <= LAYOUT_TABLE_PREVIEW_CELL_CHARS:
            return text
        return text[: LAYOUT_TABLE_PREVIEW_CELL_CHARS - 3].rstrip() + "..."

    preview = [
        [preview_cell(cell) for cell in row[:LAYOUT_TABLE_PREVIEW_COLUMNS]]
        for row in source_rows[:LAYOUT_TABLE_PREVIEW_ROWS]
    ]
    preview = [row for row in preview if any(cell for cell in row)]
    truncated = row_count > LAYOUT_TABLE_PREVIEW_ROWS or column_count > LAYOUT_TABLE_PREVIEW_COLUMNS
    return preview, row_count, column_count, truncated


def _layout_table_rows_are_coherent(rows: list[list[str]], *, column_count: int) -> bool:
    if len(rows) < 2 or column_count < 2:
        return False
    first_cell = str(rows[0][0] if rows[0] else "")
    numeric_tokens = len(re.findall(r"\d+(?:\.\d+)?", first_cell))
    if len(first_cell) > 60 and numeric_tokens >= max(4, column_count // 2):
        blank_first_cells = sum(not str(row[0] if row else "").strip() for row in rows[1:])
        if blank_first_cells >= len(rows) - 2:
            return False
    return True


def _layout_table_display_quality(
    *,
    caption: str,
    rows: list[list[str]],
    row_count: int,
    column_count: int,
    reconstruction_method: str,
    metadata: dict[str, Any],
) -> str:
    if not rows or row_count < 2 or column_count < 2:
        return "fallback"
    if not _layout_table_rows_are_coherent(rows, column_count=column_count):
        return "fallback"
    quality_score = max(
        _safe_float(metadata.get("quality_score")),
        _safe_float(metadata.get("evidence_confidence")),
    )
    method = reconstruction_method.lower()
    caption_text = caption.lower()
    has_table_caption = "table" in caption_text or "表格" in caption_text or caption_text.startswith("表 ")
    if "text_spacing" in method or quality_score < 0.72 or not has_table_caption:
        return "review"
    return "good"


def _layout_table_payload(row: Any, metadata: dict[str, Any]) -> dict[str, Any]:
    rows, row_count, column_count, preview_truncated = _layout_table_rows(metadata.get("table_rows"))
    caption = _collapse_text(metadata.get("caption") or row["text"], limit=360)
    reconstruction_method = _collapse_text(
        metadata.get("table_reconstruction_method") or metadata.get("parser"),
        limit=120,
    )
    payload = _layout_block_base(row, metadata)
    payload.update(
        {
            "caption": caption,
            "table_markdown": _collapse_text(metadata.get("table_markdown") or row["text"], limit=1800),
            "table_rows": rows,
            "row_count": row_count,
            "column_count": column_count,
            "reconstruction_method": reconstruction_method,
            "display_quality": _layout_table_display_quality(
                caption=caption,
                rows=rows,
                row_count=row_count,
                column_count=column_count,
                reconstruction_method=reconstruction_method,
                metadata=metadata,
            ),
            "preview_truncated": preview_truncated,
            "has_html": bool(metadata.get("table_html")),
        }
    )
    return payload


def _export_paper_layout_evidence(db_path: Path) -> list[dict[str, Any]]:
    init_db(db_path)
    payload: list[dict[str, Any]] = []
    with connect(db_path) as conn:
        run_rows = conn.execute(
            """
            select r.*
            from paper_layout_runs r
            join (
                select paper_key, max(id) as id
                from paper_layout_runs
                where provider = ?
                group by paper_key
            ) latest on latest.id = r.id
            order by r.paper_key
            """,
            (LAYOUT_PROVIDER,),
        ).fetchall()
        for run in run_rows:
            paper_key = str(run["paper_key"])
            run_id = _safe_int(run["id"])
            summary = _layout_summary(str(run["stats_json"] or "{}"))
            canonical_rows = conn.execute(
                """
                select equation_index, label, latex
                from paper_equations
                where paper_key = ?
                order by equation_index
                """,
                (paper_key,),
            ).fetchall()
            canonical_equations = [
                equation
                for row in canonical_rows
                if (equation := _canonical_equation_payload(row)) is not None
            ]
            block_rows = conn.execute(
                """
                select id, page_index, block_index, block_type, text, asset_path, metadata_json
                from paper_layout_blocks
                where paper_key = ? and run_id = ? and block_type in ('interline_equation', 'table')
                order by page_index, block_index
                """,
                (paper_key, run_id),
            ).fetchall()
            equations: list[tuple[float, dict[str, Any]]] = []
            tables: list[tuple[float, dict[str, Any]]] = []
            for block in block_rows:
                metadata = parse_json(block["metadata_json"], {})
                if not isinstance(metadata, dict):
                    metadata = {}
                if str(block["block_type"]) == "interline_equation":
                    equation = _layout_equation_payload(block, metadata)
                    if len(str(equation["latex"]).strip()) >= 8 and is_likely_formula(str(equation["latex"])):
                        equations.append((_layout_block_score(block, metadata), equation))
                elif str(block["block_type"]) == "table":
                    table = _layout_table_payload(block, metadata)
                    if table["table_markdown"] or table["caption"]:
                        tables.append((_layout_block_score(block, metadata), table))
            equations.sort(key=lambda item: item[0], reverse=True)
            table_quality_rank = {"good": 2, "review": 1, "fallback": 0}
            tables.sort(
                key=lambda item: (table_quality_rank.get(str(item[1].get("display_quality")), 0), item[0]),
                reverse=True,
            )
            block_types = summary.get("block_types") if isinstance(summary.get("block_types"), dict) else {}
            ocr = summary.get("ocr") if isinstance(summary.get("ocr"), dict) else {}
            formula_ocr = summary.get("formula_ocr") if isinstance(summary.get("formula_ocr"), dict) else {}
            payload.append(
                {
                    "paper_key": paper_key,
                    "api_version": "layout-evidence-v1",
                    "latest_run": {
                        "id": run_id,
                        "status": str(run["status"] or ""),
                        "provider": str(run["provider"] or ""),
                        "provider_version": str(run["provider_version"] or ""),
                        "finished_at": str(run["finished_at"] or ""),
                    },
                    "summary": {
                        "document_type": _collapse_text(summary.get("document_type"), limit=80),
                        "page_count": _safe_int(summary.get("page_count")),
                        "block_count": _safe_int(summary.get("block_count")),
                        "asset_count": _safe_int(summary.get("asset_count")),
                        "equation_blocks": _safe_int(summary.get("equation_blocks")),
                        "structured_table_blocks": _safe_int(summary.get("structured_table_blocks")),
                        "high_quality_table_blocks": _safe_int(summary.get("high_quality_table_blocks")),
                        "high_quality_equation_blocks": _safe_int(summary.get("high_quality_equation_blocks")),
                        "high_quality_evidence_blocks": _safe_int(summary.get("high_quality_evidence_blocks")),
                        "canonical_equation_count": len(canonical_equations),
                        "block_types": {str(key): _safe_int(value) for key, value in block_types.items()},
                    },
                    "ocr": {
                        "mode": _collapse_text(ocr.get("mode"), limit=80),
                        "languages": _collapse_text(ocr.get("languages"), limit=80),
                        "available": bool(ocr.get("available")),
                        "pages_attempted": _safe_int(ocr.get("pages_attempted")),
                        "pages_succeeded": _safe_int(ocr.get("pages_succeeded")),
                        "block_count": _safe_int(ocr.get("block_count")),
                        "engines": [str(item) for item in ocr.get("engines", []) if str(item).strip()][:4]
                        if isinstance(ocr.get("engines"), list)
                        else [],
                    },
                    "formula_ocr": {
                        "mode": _collapse_text(formula_ocr.get("mode"), limit=80),
                        "configured": bool(formula_ocr.get("configured")),
                        "blocks_attempted": _safe_int(formula_ocr.get("blocks_attempted")),
                        "blocks_succeeded": _safe_int(formula_ocr.get("blocks_succeeded")),
                        "blocks_rejected": _safe_int(formula_ocr.get("blocks_rejected")),
                        "models": [str(item) for item in formula_ocr.get("models", []) if str(item).strip()][:4]
                        if isinstance(formula_ocr.get("models"), list)
                        else [],
                    },
                    "equations": (
                        canonical_equations[: LAYOUT_EVIDENCE_LIMITS["equations"]]
                        if canonical_equations
                        else [item for _, item in equations[: LAYOUT_EVIDENCE_LIMITS["equations"]]]
                    ),
                    "tables": [item for _, item in tables[: LAYOUT_EVIDENCE_LIMITS["tables"]]],
                    "limits": dict(LAYOUT_EVIDENCE_LIMITS),
                }
            )
    return payload

def export_report_bundle(
    db_path: Path,
    out_dir: Path,
    *,
    review_packet_path: Path | None = None,
    concurrency: int = 1,
) -> ReportBundle:
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_layout_evidence_graph(db_path)
    artifact_tasks = [
        lambda: _export_markdown_and_json(
            db_path,
            out_dir,
            name="digest",
            title="Research Digest",
            markdown_file="digest.md",
            json_file="digest.json",
            exporter=export_research_digest,
            extra_counts=lambda _report: {},
        ),
        lambda: _export_markdown_and_json(
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
        lambda: _export_markdown_and_json(
            db_path,
            out_dir,
            name="map",
            title="Research Map",
            markdown_file="map.md",
            json_file="map.json",
            exporter=export_research_map,
            extra_counts=lambda report: {"item_count": int(report.item_count)},
        ),
        lambda: _export_markdown_and_json(
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
        lambda: _export_markdown_and_json(
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
        lambda: _export_markdown_and_json(
            db_path,
            out_dir,
            name="synthesis",
            title="Research Synthesis",
            markdown_file="synthesis.md",
            json_file="synthesis.json",
            exporter=export_research_synthesis,
            extra_counts=lambda report: {"extraction_target_count": int(report.extraction_target_count)},
        ),
        lambda: _export_markdown_and_json(
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
        lambda: _export_markdown_and_json(
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
    max_workers = max(1, min(concurrency, len(artifact_tasks)))
    if max_workers == 1:
        artifacts = [task() for task in artifact_tasks]
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            artifacts = list(pool.map(lambda task: task(), artifact_tasks))
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
    (out_dir / "paper-assets.json").write_text(
        json.dumps(_export_paper_assets(db_path, out_dir), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "paper-layout-evidence.json").write_text(
        json.dumps(_export_paper_layout_evidence(db_path), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    export_layout_evidence_graph(db_path, out_dir / "layout-evidence-graph.json")
    export_fact_translations(db_path, out_dir / "fact-translations.json")
    export_paper_blogs(db_path, out_dir / "paper-blogs.json")
    return bundle
