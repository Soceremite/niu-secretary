from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Protocol

from airesearch.db import connect
from airesearch.formula_ocr import FormulaOCRResult, normalize_formula_latex
from airesearch.paper_blog import (
    BLOG_PROMPT_VERSION,
    BlogVersionConflictError,
    _mask_markdown_code,
    ensure_blog_schema,
    parse_json,
    publish_blog_version,
    utc_now,
)
from airesearch.paperpipe_sync import stable_json


@dataclass(frozen=True)
class FormulaSpan:
    ordinal: int
    delimiter: str
    start: int
    end: int
    content_start: int
    content_end: int
    latex: str
    digest: str

    def locator(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "delimiter": self.delimiter,
            "start": self.start,
            "end": self.end,
            "content_start": self.content_start,
            "content_end": self.content_end,
            "digest": self.digest,
        }


@dataclass(frozen=True)
class FormulaValidation:
    valid: bool
    status: str
    error: str = ""


@dataclass(frozen=True)
class FormulaEvidence:
    pdf_page: int
    bbox: list[float]
    crop_path: str
    crop_bytes: bytes
    context: str
    selection_method: str


@dataclass(frozen=True)
class FormulaRepairRun:
    paper_key: str
    source_version_id: int
    applied_version_id: int | None
    status: str
    formulas_seen: int
    compile_failures: int
    repairs_validated: int
    repairs_failed: int


class FormulaCompiler(Protocol):
    def validate(self, latex: str) -> FormulaValidation: ...


class FormulaRepairProvider(Protocol):
    config: Any

    def repair(
        self,
        image_bytes: bytes,
        *,
        failed_latex: str,
        context: str = "",
        mime_type: str = "image/png",
    ) -> FormulaOCRResult: ...


class MathJaxBrowserCompiler:
    def __init__(self, script_path: Path | None = None, *, timeout_seconds: float = 35.0):
        root = Path(__file__).resolve().parents[3]
        self.script_path = script_path or root / "scripts" / "validate_mathjax_formula.mjs"
        self.timeout_seconds = timeout_seconds

    def validate(self, latex: str) -> FormulaValidation:
        return self.validate_many([latex])[0]

    def validate_many(self, formulas: list[str]) -> list[FormulaValidation]:
        try:
            result = subprocess.run(
                ["node", str(self.script_path)],
                input=json.dumps({"formulas": formulas}, ensure_ascii=False),
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            payload = json.loads(result.stdout)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            return [FormulaValidation(False, "validator_unavailable", str(exc)[:500]) for _ in formulas]
        if not isinstance(payload, dict) or payload.get("status") == "unavailable":
            error = str(payload.get("error") or "")[:500] if isinstance(payload, dict) else "invalid validator response"
            return [FormulaValidation(False, "validator_unavailable", error) for _ in formulas]
        results = payload.get("results")
        if not isinstance(results, list) or len(results) != len(formulas):
            return [FormulaValidation(False, "validator_unavailable", "invalid validator result count") for _ in formulas]
        validations = []
        for item in results:
            valid = bool(item.get("valid")) if isinstance(item, dict) else False
            validations.append(
                FormulaValidation(
                    valid,
                    "compiled" if valid else "compile_failed",
                    str(item.get("error") or "")[:1000] if isinstance(item, dict) else "invalid validator result",
                )
            )
        return validations


MATH_PATTERNS = (
    ("display_dollar", re.compile(r"\$\$(.+?)\$\$", re.S), 2, 2),
    ("display_bracket", re.compile(r"\\\[(.+?)\\\]", re.S), 2, 2),
    ("inline_paren", re.compile(r"\\\((.+?)\\\)", re.S), 2, 2),
    ("inline_dollar", re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", re.S), 1, 1),
)


def extract_math_spans(markdown: str) -> list[FormulaSpan]:
    visible = _mask_markdown_code(markdown)
    raw: list[tuple[int, int, str, int, int]] = []
    for delimiter, pattern, prefix, suffix in MATH_PATTERNS:
        raw.extend(
            (match.start(), match.end(), delimiter, prefix, suffix)
            for match in pattern.finditer(visible)
        )
    raw.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    spans: list[FormulaSpan] = []
    last_end = -1
    for start, end, delimiter, prefix, suffix in raw:
        if start < last_end:
            continue
        content_start = start + prefix
        content_end = end - suffix
        latex = markdown[content_start:content_end].strip()
        if not latex:
            continue
        spans.append(
            FormulaSpan(
                ordinal=len(spans) + 1,
                delimiter=delimiter,
                start=start,
                end=end,
                content_start=content_start,
                content_end=content_end,
                latex=latex,
                digest=hashlib.sha256(latex.encode("utf-8")).hexdigest(),
            )
        )
        last_end = end
    return spans


def ensure_formula_repair_schema(db_path: Path) -> None:
    ensure_blog_schema(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            create table if not exists paper_blog_formula_repairs (
                id integer primary key autoincrement,
                paper_key text not null references papers(paper_key) on delete cascade,
                source_version_id integer not null references paper_blog_versions(id) on delete cascade,
                applied_version_id integer references paper_blog_versions(id) on delete set null,
                formula_locator_json text not null default '{}',
                original_latex text not null,
                repaired_latex text not null default '',
                pdf_page integer,
                bbox_json text not null default '[]',
                crop_path text not null default '',
                context text not null default '',
                model text not null default '',
                confidence real not null default 0,
                initial_validation_status text not null default '',
                initial_validation_error text not null default '',
                validation_status text not null default '',
                validation_error text not null default '',
                repair_status text not null default 'pending',
                input_hash text not null,
                created_at text not null,
                updated_at text not null,
                unique(paper_key, source_version_id, input_hash)
            )
            """
        )
        columns = {str(row["name"]) for row in conn.execute("pragma table_info(paper_blog_formula_repairs)")}
        if "initial_validation_status" not in columns:
            conn.execute(
                "alter table paper_blog_formula_repairs add column initial_validation_status text not null default ''"
            )
        if "initial_validation_error" not in columns:
            conn.execute(
                "alter table paper_blog_formula_repairs add column initial_validation_error text not null default ''"
            )
        conn.execute(
            "create index if not exists idx_blog_formula_repairs_paper "
            "on paper_blog_formula_repairs(paper_key, source_version_id, repair_status)"
        )
        conn.commit()


def _normalized_latex(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", value).casefold()


def _layout_equations(conn: Any, paper_key: str) -> list[dict[str, Any]]:
    latest = conn.execute(
        """
        select id from paper_layout_runs
        where paper_key = ? and status = 'completed'
        order by coalesce(finished_at, started_at) desc, id desc limit 1
        """,
        (paper_key,),
    ).fetchone()
    if latest is None:
        return []
    rows = conn.execute(
        """
        select page_index, block_index, bbox_json, text, metadata_json
        from paper_layout_blocks
        where paper_key = ? and run_id = ? and block_type = 'interline_equation'
        order by page_index, block_index, id
        """,
        (paper_key, int(latest["id"])),
    ).fetchall()
    result = []
    for row in rows:
        metadata = parse_json(row["metadata_json"], {})
        metadata = metadata if isinstance(metadata, dict) else {}
        result.append(
            {
                "page_index": int(row["page_index"]),
                "block_index": int(row["block_index"]),
                "bbox": parse_json(row["bbox_json"], []),
                "text": str(metadata.get("formula_latex") or metadata.get("formula_ocr_candidate_latex") or row["text"] or ""),
            }
        )
    return result


def _paper_pdf(conn: Any, paper_key: str) -> Path | None:
    rows = conn.execute(
        "select path from paper_artifacts where paper_key = ? and artifact_type = 'paper_pdf' order by length(path), path",
        (paper_key,),
    ).fetchall()
    for row in rows:
        path = Path(str(row["path"] or ""))
        if path.exists() and path.is_file():
            return path.resolve()
    paper = conn.execute("select paper_dir from papers where paper_key = ?", (paper_key,)).fetchone()
    candidate = Path(str(paper["paper_dir"] or "")) / "paper.pdf" if paper is not None else None
    return candidate.resolve() if candidate is not None and candidate.is_file() else None


def _match_layout(span: FormulaSpan, rows: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    if not rows:
        return None, "page-fallback"
    source = _normalized_latex(span.latex)
    scored = [
        (SequenceMatcher(None, source, _normalized_latex(str(row.get("text") or ""))).ratio(), row)
        for row in rows
    ]
    score, best = max(scored, key=lambda item: item[0])
    if score >= 0.42:
        return best, f"layout-similarity:{score:.3f}"
    ordinal = dict(rows[min(span.ordinal - 1, len(rows) - 1)])
    ordinal["bbox"] = []
    return ordinal, "layout-ordinal-page-fallback"


def _local_context(markdown: str, span: FormulaSpan, layout_text: str) -> str:
    before = markdown[max(0, span.start - 700):span.start].strip()
    after = markdown[span.end:min(len(markdown), span.end + 700)].strip()
    return "\n\n".join(value for value in (before, after, layout_text.strip()) if value)[:2200]


def _render_evidence(
    pdf_path: Path,
    *,
    page_index: int,
    bbox: list[Any],
    output_path: Path,
) -> tuple[bytes, list[float], str]:
    import fitz

    document = fitz.open(pdf_path)
    try:
        page_index = page_index if 0 <= page_index < len(document) else 0
        page = document[page_index]
        clip = page.rect
        normalized_bbox: list[float] = []
        method = "page"
        if len(bbox) == 4:
            try:
                x0, y0, x1, y1 = (float(value) for value in bbox)
            except (TypeError, ValueError):
                pass
            else:
                if x1 > x0 and y1 > y0:
                    pad_x = max(8.0, (x1 - x0) * 0.08)
                    pad_y = max(8.0, (y1 - y0) * 0.35)
                    clip = fitz.Rect(
                        max(page.rect.x0, x0 - pad_x),
                        max(page.rect.y0, y0 - pad_y),
                        min(page.rect.x1, x1 + pad_x),
                        min(page.rect.y1, y1 + pad_y),
                    )
                    normalized_bbox = [x0, y0, x1, y1]
                    method = "bbox"
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2.2, 2.2), clip=clip, alpha=False)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(output_path)
        return output_path.read_bytes(), normalized_bbox, method
    finally:
        document.close()


def build_formula_evidence(db_path: Path, paper_key: str, markdown: str, span: FormulaSpan) -> FormulaEvidence:
    with connect(db_path) as conn:
        matched, selection = _match_layout(span, _layout_equations(conn, paper_key))
        pdf_path = _paper_pdf(conn, paper_key)
        paper = conn.execute("select paper_dir from papers where paper_key = ?", (paper_key,)).fetchone()
    if pdf_path is None:
        raise FileNotFoundError("paper PDF is unavailable")
    page_index = int(matched.get("page_index") or 0) if matched else 0
    bbox = matched.get("bbox") if matched and isinstance(matched.get("bbox"), list) else []
    paper_dir = Path(str(paper["paper_dir"] or "")) if paper is not None else pdf_path.parent
    output_path = paper_dir / "blog-assets" / "formula-repairs" / f"formula-{span.ordinal}-{span.digest[:16]}.png"
    crop_bytes, normalized_bbox, crop_method = _render_evidence(
        pdf_path,
        page_index=page_index,
        bbox=bbox,
        output_path=output_path,
    )
    layout_text = str(matched.get("text") or "") if matched else ""
    return FormulaEvidence(
        pdf_page=page_index + 1,
        bbox=normalized_bbox,
        crop_path=str(output_path),
        crop_bytes=crop_bytes,
        context=_local_context(markdown, span, layout_text),
        selection_method=f"{selection}:{crop_method}",
    )


def _input_hash(span: FormulaSpan, source_version_id: int) -> str:
    return hashlib.sha256(
        stable_json({"source_version_id": source_version_id, "locator": span.locator(), "latex": span.latex}).encode()
    ).hexdigest()


def _audit_row(db_path: Path, paper_key: str, source_version_id: int, input_hash: str) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "select * from paper_blog_formula_repairs where paper_key = ? and source_version_id = ? and input_hash = ?",
            (paper_key, source_version_id, input_hash),
        ).fetchone()
    return dict(row) if row is not None else None


def _write_audit(
    db_path: Path,
    *,
    paper_key: str,
    source_version_id: int,
    span: FormulaSpan,
    input_hash: str,
    evidence: FormulaEvidence | None,
    repaired_latex: str = "",
    model: str = "",
    confidence: float = 0.0,
    initial_validation: FormulaValidation,
    validation_status: str,
    validation_error: str = "",
    repair_status: str,
) -> int:
    now = utc_now()
    locator = span.locator()
    if evidence:
        locator["evidence_selection"] = evidence.selection_method
    values = (
        paper_key, source_version_id, stable_json(locator), span.latex, repaired_latex,
        evidence.pdf_page if evidence else None, stable_json(evidence.bbox if evidence else []),
        evidence.crop_path if evidence else "", evidence.context if evidence else "", model,
        confidence, initial_validation.status, initial_validation.error[:2000], validation_status,
        validation_error[:2000], repair_status, input_hash, now, now,
    )
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into paper_blog_formula_repairs (
                paper_key, source_version_id, formula_locator_json, original_latex, repaired_latex,
                pdf_page, bbox_json, crop_path, context, model, confidence,
                initial_validation_status, initial_validation_error, validation_status,
                validation_error, repair_status, input_hash, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(paper_key, source_version_id, input_hash) do update set
                formula_locator_json=excluded.formula_locator_json, repaired_latex=excluded.repaired_latex,
                pdf_page=excluded.pdf_page, bbox_json=excluded.bbox_json, crop_path=excluded.crop_path,
                context=excluded.context, model=excluded.model, confidence=excluded.confidence,
                initial_validation_status=excluded.initial_validation_status,
                initial_validation_error=excluded.initial_validation_error,
                validation_status=excluded.validation_status, validation_error=excluded.validation_error,
                repair_status=excluded.repair_status, updated_at=excluded.updated_at
            """,
            values,
        )
        row = conn.execute(
            "select id from paper_blog_formula_repairs where paper_key = ? and source_version_id = ? and input_hash = ?",
            (paper_key, source_version_id, input_hash),
        ).fetchone()
        conn.commit()
    return int(row["id"])


def repair_blog_formulas(
    db_path: Path,
    paper_key: str,
    *,
    compiler: FormulaCompiler,
    provider: FormulaRepairProvider | None,
    evidence_builder=build_formula_evidence,
    min_confidence: float = 0.7,
    force_retry: bool = False,
) -> FormulaRepairRun:
    ensure_formula_repair_schema(db_path)
    with connect(db_path) as conn:
        post = conn.execute("select * from paper_blog_posts where paper_key = ?", (paper_key,)).fetchone()
        if post is None or str(post["status"] or "") != "published":
            raise KeyError(paper_key)
        source_version_id = int(post["current_version_id"])
        version = conn.execute("select * from paper_blog_versions where id = ?", (source_version_id,)).fetchone()
    markdown = str(post["markdown"] or "")
    spans = extract_math_spans(markdown)
    validate_many = getattr(compiler, "validate_many", None)
    validations = validate_many([span.latex for span in spans]) if callable(validate_many) else [
        compiler.validate(span.latex) for span in spans
    ]
    if len(validations) != len(spans):
        return FormulaRepairRun(paper_key, source_version_id, None, "validator_unavailable", len(spans), 0, 0, 1)
    failures: list[tuple[FormulaSpan, FormulaValidation]] = []
    for span, validation in zip(spans, validations, strict=True):
        if validation.status == "validator_unavailable":
            return FormulaRepairRun(paper_key, source_version_id, None, "validator_unavailable", len(spans), 0, 0, 1)
        if not validation.valid:
            failures.append((span, validation))
    if not failures:
        return FormulaRepairRun(paper_key, source_version_id, None, "clean", len(spans), 0, 0, 0)

    repairs: list[tuple[FormulaSpan, str, int]] = []
    failed_count = 0
    configured_model = str(getattr(getattr(provider, "config", None), "model", "")) if provider else ""
    for span, initial_validation in failures:
        input_hash = _input_hash(span, source_version_id)
        existing = _audit_row(db_path, paper_key, source_version_id, input_hash)
        if existing and not force_retry:
            if existing["repair_status"] == "validated":
                repairs.append((span, str(existing["repaired_latex"]), int(existing["id"])))
            else:
                failed_count += 1
            continue
        try:
            evidence = evidence_builder(db_path, paper_key, markdown, span)
        except Exception as exc:
            _write_audit(
                db_path, paper_key=paper_key, source_version_id=source_version_id, span=span,
                input_hash=input_hash, evidence=None, model=configured_model,
                initial_validation=initial_validation,
                validation_status="evidence_unavailable", validation_error=str(exc), repair_status="failed",
            )
            failed_count += 1
            continue
        if provider is None:
            _write_audit(
                db_path, paper_key=paper_key, source_version_id=source_version_id, span=span,
                input_hash=input_hash, evidence=evidence, initial_validation=initial_validation,
                validation_status="provider_unavailable",
                validation_error="formula repair provider is not configured", repair_status="failed",
            )
            failed_count += 1
            continue
        try:
            result = provider.repair(
                evidence.crop_bytes, failed_latex=span.latex, context=evidence.context, mime_type="image/png"
            )
            repaired = normalize_formula_latex(result.latex)
            candidate_validation = compiler.validate(repaired)
        except Exception as exc:
            _write_audit(
                db_path, paper_key=paper_key, source_version_id=source_version_id, span=span,
                input_hash=input_hash, evidence=evidence, model=configured_model,
                initial_validation=initial_validation,
                validation_status="provider_failed", validation_error=str(exc), repair_status="failed",
            )
            failed_count += 1
            continue
        if not candidate_validation.valid or result.confidence < min_confidence:
            error = candidate_validation.error or f"confidence {result.confidence:.3f} below {min_confidence:.3f}"
            _write_audit(
                db_path, paper_key=paper_key, source_version_id=source_version_id, span=span,
                input_hash=input_hash, evidence=evidence, repaired_latex=repaired, model=result.model,
                confidence=result.confidence, initial_validation=initial_validation,
                validation_status=candidate_validation.status,
                validation_error=error, repair_status="failed",
            )
            failed_count += 1
            continue
        audit_id = _write_audit(
            db_path, paper_key=paper_key, source_version_id=source_version_id, span=span,
            input_hash=input_hash, evidence=evidence, repaired_latex=repaired, model=result.model,
            confidence=result.confidence, initial_validation=initial_validation,
            validation_status="compiled", repair_status="validated",
        )
        repairs.append((span, repaired, audit_id))

    if failed_count or len(repairs) != len(failures):
        return FormulaRepairRun(
            paper_key, source_version_id, None, "failed", len(spans), len(failures), len(repairs), failed_count
        )

    repaired_markdown = markdown
    repaired_html = str(post["html"] or "")
    for span, repaired, _audit_id in sorted(repairs, key=lambda item: item[0].content_start, reverse=True):
        raw = repaired_markdown[span.content_start:span.content_end]
        if raw.strip() != span.latex:
            raise RuntimeError("formula locator became stale before apply")
        replacement = raw[:len(raw) - len(raw.lstrip())] + repaired + raw[len(raw.rstrip()):]
        repaired_markdown = repaired_markdown[:span.content_start] + replacement + repaired_markdown[span.content_end:]
        if span.latex in repaired_html:
            repaired_html = repaired_html.replace(span.latex, repaired, 1)
        elif html.escape(span.latex) in repaired_html:
            repaired_html = repaired_html.replace(html.escape(span.latex), html.escape(repaired), 1)
    meta = parse_json(version["generation_meta_json"], {}) if version is not None else {}
    meta = meta if isinstance(meta, dict) else {}
    meta["formula_repairs"] = {
        "source_version_id": source_version_id,
        "audit_ids": [audit_id for _span, _latex, audit_id in repairs],
        "count": len(repairs),
        "timestamp": utc_now(),
    }
    try:
        published = publish_blog_version(
            db_path, paper_key=paper_key, title=str(post["title"] or ""), slug=str(post["slug"] or paper_key),
            markdown=repaired_markdown, html=repaired_html, outline=parse_json(post["outline_json"], {}),
            image_refs=parse_json(post["image_refs_json"], []), generation_meta=meta,
            model=str(post["model"] or ""), prompt_version=str(post["prompt_version"] or BLOG_PROMPT_VERSION),
            source_hash=str(post["source_hash"] or ""), expected_source_version_id=source_version_id,
        )
    except BlogVersionConflictError:
        return FormulaRepairRun(
            paper_key, source_version_id, None, "stale", len(spans), len(failures), len(repairs), 1
        )
    with connect(db_path) as conn:
        conn.executemany(
            "update paper_blog_formula_repairs set repair_status='applied', applied_version_id=?, updated_at=? where id=?",
            [(published.version_id, utc_now(), audit_id) for _span, _latex, audit_id in repairs],
        )
        conn.commit()
    return FormulaRepairRun(
        paper_key, source_version_id, published.version_id, "applied", len(spans), len(failures), len(repairs), 0
    )


__all__ = [
    "FormulaEvidence", "FormulaRepairRun", "FormulaSpan", "FormulaValidation",
    "MathJaxBrowserCompiler", "ensure_formula_repair_schema", "extract_math_spans", "repair_blog_formulas",
]
