from __future__ import annotations

import html
import hashlib
import json
import os
import posixpath
import re
import shutil
import urllib.parse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from airesearch.canonical_candidates import extract_arxiv_id
from airesearch.db import connect, init_db
from airesearch.formula_ocr import is_likely_formula
from airesearch.image_selection import image_dimensions
from airesearch.layout_service import visual_candidates as layout_service_visual_candidates
from airesearch.paper_figures import resolve_paper_figures
from airesearch.paper_tables import resolve_paper_tables
from airesearch.paperpipe_sync import stable_json
from airesearch.provider_config import api_root, responses_url


BLOG_PROMPT_VERSION = "paper_blog.zh_engineer.v1"
BLOG_TARGET_AUDIENCE = "ai_engineer"
BLOG_LANGUAGE = "zh"
MIN_BLOG_CHARS = 3000
MAX_BLOG_CHARS = 8000
DEFAULT_TARGET_CHARS = 5000
MAX_SECTIONS = 8
MAX_IMAGES = 6
MIN_SECTION_CHARS = 300
MAX_SECTION_CHARS = 1400
SECTION_PROVIDER_RETRIES = 2
OUTLINE_SOURCE_CHAR_LIMIT = 8000
SECTION_SOURCE_CHAR_LIMIT = 6000
MAX_EQUATIONS = 6
HIGH_QUALITY_EVIDENCE_THRESHOLD = 0.72
MIN_OUTLINE_FACT_COVERAGE = 0.5
DEFAULT_OUTLINE_FACTS_PER_SECTION = 4
DEFAULT_BLOG_MODEL = "deepseek-v4-pro"
DEFAULT_BLOG_BASE_URL = "https://api.deepseek.com"
OUTLINE_MAX_OUTPUT_TOKENS = 4000
SECTION_MAX_OUTPUT_TOKENS = 5000
IMAGE_SUFFIXES = {".svg", ".png", ".jpg", ".jpeg", ".webp"}
EQUATION_ENV_RE = re.compile(
    r"\\begin\{(equation|align|gather|multline)\*?\}(.*?)\\end\{\1\*?\}",
    re.S,
)
FENCED_LATEX_RE = re.compile(r"```latex\s*(.*?)```", re.S)
LABEL_COMMAND_RE = re.compile(r"\\label\{([^}]+)\}")
OUTER_EQUATION_END_RE = re.compile(r"\\end\{(?:equation|align|gather|multline)\*?\}")
SECTION_H2_RE = re.compile(r"^##[ \t]+\S")
MODEL_CONTROL_TOKEN_RE = re.compile(
    r"<(?P<closing>/)?(?P<name>[A-Za-z][A-Za-z0-9_]*_\d[A-Za-z0-9_]*)>"
)
MARKDOWN_ESCAPABLE = frozenset(r'''!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~''')
MAX_MARKDOWN_DESTINATION_NESTING = 32


@dataclass(frozen=True)
class PublishedBlogVersion:
    paper_key: str
    version_id: int
    version_number: int
    word_count: int
    status: str


class BlogVersionConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class MarkdownImageMatch:
    start: int
    end: int
    destination_start: int
    destination_end: int
    path: str


@dataclass(frozen=True)
class BlogEvidencePack:
    paper_key: str
    title: str
    authors: list[str]
    year: int | None
    venue: str
    ids: dict[str, Any]
    paper_card: dict[str, Any]
    facts: list[dict[str, Any]]
    artifact_texts: dict[str, str]
    code_links: list[dict[str, str]]
    citations: list[dict[str, str]]
    image_candidates: list[dict[str, Any]]
    equations: list[dict[str, Any]]
    source_hash: str

    def as_prompt_payload(self) -> dict[str, Any]:
        prompt_images = [
            {
                key: value
                for key, value in image.items()
                if key not in {"source_path", "content_fingerprint"}
            }
            for image in self.image_candidates
        ]
        return {
            "paper_key": self.paper_key,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "ids": self.ids,
            "paper_card": self.paper_card,
            "facts": self.facts,
            "artifact_texts": self.artifact_texts,
            "code_links": self.code_links,
            "citations": self.citations,
            "image_candidates": prompt_images,
            "equations": [
                {key: value for key, value in equation.items() if key != "source_path"}
                for equation in self.equations
            ],
            "evidence_quality_policy": {
                "high_quality_threshold": 0.72,
                "use_high_quality_first": True,
            },
            "source_hash": self.source_hash,
        }


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def parse_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _quality_score(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def slugify(value: str) -> str:
    safe: list[str] = []
    for char in value.lower():
        if char.isalnum():
            safe.append(char)
        elif char in {"_", "-", "."} or char.isspace():
            safe.append("-")
    slug = "".join(safe).strip("-._")
    return slug or "paper-blog"


def chinese_char_count(markdown: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", markdown))


def display_math_block_count(markdown: str) -> int:
    return len(re.findall(r"\$\$\s*.+?\s*\$\$", markdown, re.S))


def render_markdown_fallback(markdown: str) -> str:
    blocks = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# "):
            blocks.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            blocks.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            blocks.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        else:
            blocks.append(f"<p>{html.escape(line)}</p>")
    return "\n".join(blocks)


def _read_text(path_value: str, max_chars: int) -> str:
    path = _existing_file(path_value)
    if path is None or max_chars <= 0:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:max_chars]


def _artifact_texts(conn: Any, paper_key: str, max_source_chars: int) -> dict[str, str]:
    rows = conn.execute(
        """
        select artifact_type, path from paper_artifacts
        where paper_key = ? and artifact_type in ('summary', 'tldr', 'notes', 'source_tex', 'layout_markdown')
        order by case artifact_type
            when 'summary' then 1
            when 'tldr' then 2
            when 'notes' then 3
            when 'source_tex' then 4
            when 'layout_markdown' then 5
            else 5
        end, path
        """,
        (paper_key,),
    ).fetchall()
    remaining = max_source_chars
    result: dict[str, str] = {}
    for row in rows:
        text = _read_text(str(row["path"] or ""), remaining)
        if text:
            result[str(row["artifact_type"])] = text
            remaining -= len(text)
        if remaining <= 0:
            break
    return result


def _latest_completed_layout_run_id(conn: Any, paper_key: str) -> int | None:
    row = conn.execute(
        """
        select id from paper_layout_runs
        where paper_key = ? and provider = 'airesearch_layout' and status = 'completed'
        order by id desc
        limit 1
        """,
        (paper_key,),
    ).fetchone()
    return int(row["id"]) if row is not None else None


def _layout_structured_table_text(conn: Any, paper_key: str, *, max_chars: int) -> str:
    run_id = _latest_completed_layout_run_id(conn, paper_key)
    if run_id is None or max_chars <= 0:
        return ""
    rows = conn.execute(
        """
        select page_index, block_index, text, metadata_json
        from paper_layout_blocks
        where paper_key = ? and run_id = ? and block_type = 'table'
        order by page_index, block_index
        """,
        (paper_key, run_id),
    ).fetchall()
    sections: list[str] = []
    for row in rows:
        metadata = parse_json(row["metadata_json"], {})
        if not isinstance(metadata, dict):
            continue
        quality_score = _quality_score(metadata.get("quality_score"))
        if quality_score < HIGH_QUALITY_EVIDENCE_THRESHOLD:
            continue
        table_markdown = str(metadata.get("table_markdown") or "").strip()
        if not table_markdown:
            continue
        caption = str(metadata.get("caption") or row["text"] or "Structured table").strip()
        source_reference = str(
            metadata.get("source_reference")
            or f"page={int(row['page_index']) + 1} block={int(row['block_index'])}"
        )
        reasons = metadata.get("quality_reasons") if isinstance(metadata.get("quality_reasons"), list) else []
        sections.append(
            "\n".join(
                [
                    f"### {caption}",
                    f"Source: {source_reference}",
                    f"Quality: {quality_score:.2f} ({', '.join(str(reason) for reason in reasons[:4])})",
                    table_markdown,
                ]
            )
        )
    return "\n\n".join(sections)[:max_chars]


def _blog_facts(conn: Any, paper_key: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select
            f.id, f.fact_type, f.name, f.statement, f.confidence, f.metadata_json,
            p.evidence_quote, p.evidence_artifact_type, p.evidence_source_path
        from research_facts f
        left join research_fact_provenance p on p.fact_id = f.id
        where f.paper_key = ?
        order by case f.fact_type
            when 'method' then 1
            when 'claim' then 2
            when 'benchmark' then 3
            when 'dataset' then 4
            when 'limitation' then 5
            else 6
        end, f.confidence desc, f.id
        """,
        (paper_key,),
    ).fetchall()
    return [
        {
            "fact_id": int(row["id"]),
            "fact_type": str(row["fact_type"] or ""),
            "name": str(row["name"] or ""),
            "statement": str(row["statement"] or ""),
            "confidence": float(row["confidence"] or 0.0),
            "metadata": parse_json(row["metadata_json"], {}),
            "evidence_quote": str(row["evidence_quote"] or ""),
            "evidence_artifact_type": str(row["evidence_artifact_type"] or ""),
            "evidence_source_path": str(row["evidence_source_path"] or ""),
        }
        for row in rows
    ]


def _code_links(conn: Any, paper_key: str) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        select url, host, owner, repo, source_type, source_path
        from paper_code_links
        where paper_key = ?
        order by url
        """,
        (paper_key,),
    ).fetchall()
    return [
        {
            "url": str(row["url"] or ""),
            "host": str(row["host"] or ""),
            "owner": str(row["owner"] or ""),
            "repo": str(row["repo"] or ""),
            "source_type": str(row["source_type"] or ""),
            "source_path": str(row["source_path"] or ""),
        }
        for row in rows
    ]


def _citations(conn: Any, paper_key: str) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        select source_path, citation_key, raw_text, context
        from paper_citations
        where paper_key = ?
        order by citation_index
        limit 40
        """,
        (paper_key,),
    ).fetchall()
    return [
        {
            "source_path": str(row["source_path"] or ""),
            "citation_key": str(row["citation_key"] or ""),
            "raw_text": str(row["raw_text"] or ""),
            "context": str(row["context"] or ""),
        }
        for row in rows
    ]


def _image_asset_path(path: Path, source_dir: Path) -> str:
    try:
        return str(path.relative_to(source_dir))
    except ValueError:
        return path.name


def _image_fingerprint(path: Path) -> dict[str, Any]:
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "size_bytes": stat.st_size,
        "sha256": digest.hexdigest(),
    }


def _strip_latex_commands(value: str) -> str:
    text = re.sub(r"%.*", "", value)
    text = re.sub(r"\\(?:textbf|emph|textit|textsc)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", "", text)
    text = text.replace("{", "").replace("}", "")
    return " ".join(text.split())


def _path_candidates(value: str) -> tuple[Path, ...]:
    raw = Path(value)
    candidates = [raw]
    if not raw.is_absolute():
        module_path = Path(__file__).resolve()
        candidates.append(module_path.parents[3] / raw)
        candidates.append(module_path.parents[2] / raw)
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return tuple(unique)


def _existing_file(value: str) -> Path | None:
    if not value:
        return None
    for candidate in _path_candidates(value):
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    return None


def _existing_dir(value: str) -> Path | None:
    if not value:
        return None
    for candidate in _path_candidates(value):
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return None


def _default_paper_dir(paper_key: str) -> Path | None:
    candidate = Path(__file__).resolve().parents[3] / "airesearch" / "data" / "paperpipe" / "papers" / paper_key
    return candidate.resolve() if candidate.exists() and candidate.is_dir() else None


def _artifact_path(conn: Any, paper_key: str, artifact_type: str) -> Path | None:
    rows = conn.execute(
        """
        select path from paper_artifacts
        where paper_key = ? and artifact_type = ?
        order by length(path), path
        """,
        (paper_key, artifact_type),
    ).fetchall()
    for row in rows:
        path = _existing_file(str(row["path"] or ""))
        if path is not None:
            return path
    return None


def _source_tex_path(conn: Any, paper_key: str) -> Path | None:
    return _artifact_path(conn, paper_key, "source_tex")


def _paper_pdf_path(conn: Any, paper_key: str) -> Path | None:
    return _artifact_path(conn, paper_key, "paper_pdf")


def _figure_role(value: str) -> str:
    lowered = value.lower()
    if any(term in lowered for term in ("illustration", "paradigm", "motivation", "inference")):
        return "motivation"
    if any(term in lowered for term in ("overview", "framework", "architecture", "pipeline")):
        return "framework"
    if any(term in lowered for term in ("visualization", "qualitative", "trajectory", "closed-loop")):
        return "qualitative"
    if any(term in lowered for term in ("result", "benchmark", "experiment", "ablation", "comparison")):
        return "experiments"
    if any(term in lowered for term in ("mask", "router", "latent", "planner", "method")):
        return "method"
    return "figure"


def _figure_number(value: str) -> int | None:
    lowered = value.lower()
    match = re.search(r"\b(?:fig(?:ure)?\.?)\s*([0-9]{1,2})(?:\b|[.:])", lowered)
    if match:
        return int(match.group(1))
    match = re.search(r"(?:^|[^\w])图\s*([0-9]{1,2})(?:\b|[.:：])", value)
    if match:
        return int(match.group(1))
    return None


def _figure_section_key(role: str, caption: str = "") -> str:
    lowered = f"{role} {caption}".lower()
    if any(term in lowered for term in ("motivation", "paradigm", "illustration")):
        return "background"
    if any(term in lowered for term in ("framework", "overview", "architecture")):
        return "architecture"
    if any(term in lowered for term in ("experiment", "result", "qualitative", "trajectory", "comparison")):
        return "experiments"
    if any(term in lowered for term in ("mask", "router", "latent", "planner", "method")):
        return "method"
    return "architecture"


def _has_disallowed_equation_characters(value: str) -> bool:
    return "\ufffd" in value or any(
        (ord(char) < 32 or 127 <= ord(char) <= 159)
        and char not in "\n\r\t"
        for char in value
    )


def _clean_equation_latex(value: str) -> str:
    if _has_disallowed_equation_characters(value):
        return ""
    lines = []
    for raw_line in value.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        stripped = LABEL_COMMAND_RE.sub("", stripped).strip()
        if stripped:
            lines.append(stripped)
    latex = "\n".join(lines).strip()
    return latex if _sized_delimiters_valid(latex) else ""


SIZED_DELIMITER_RE = re.compile(
    r"\\(?P<side>left|right)\s*(?P<delimiter>"
    r"\\(?:[{}|.]|langle|rangle|lvert|rvert|vert|Vert)"
    r"|[()\[\]{}|.<>])"
)


def _sized_delimiters_valid(value: str) -> bool:
    commands = list(re.finditer(r"\\(?:left|right)\b", value))
    if not commands:
        return True
    tokens = list(SIZED_DELIMITER_RE.finditer(value))
    if len(tokens) != len(commands) or any(
        token.start() != command.start()
        for token, command in zip(tokens, commands, strict=True)
    ):
        return False
    depth = 0
    for token in tokens:
        if token.group("side") == "left":
            depth += 1
        else:
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _equation_label(value: str) -> str:
    match = LABEL_COMMAND_RE.search(value)
    return match.group(1).strip() if match else ""


def _equation_role(value: str) -> str:
    lowered = value.lower()
    if "topk" in lowered or "mathcal h" in lowered:
        return "router_selection"
    if "mathcal{m}" in lowered or "mathcal m" in lowered or "cases" in lowered:
        return "hybrid_mask"
    if "mathcal d" in lowered and "vlm" in lowered:
        return "latent_reasoning"
    if "mathbf{x}" in lowered or "sum_" in lowered or "mathcal i" in lowered:
        return "trajectory_querying"
    if "loss" in lowered or "lambda" in lowered:
        return "training_objective"
    return "formula"


def _candidate_equations_from_text(text: str, *, source_path: str) -> list[dict[str, str]]:
    equations: list[dict[str, str]] = []
    for match in EQUATION_ENV_RE.finditer(text):
        raw = match.group(2)
        latex = _clean_equation_latex(raw)
        if len(latex) < 20 or latex.startswith("%") or OUTER_EQUATION_END_RE.search(latex) or latex.startswith(("4pt]", "[4pt]")):
            continue
        equations.append(
            {
                "equation_id": f"eq-{len(equations) + 1}",
                "label": _equation_label(raw),
                "latex": latex,
                "role": _equation_role(latex),
                "source_path": source_path,
            }
        )
    for match in FENCED_LATEX_RE.finditer(text):
        latex = _clean_equation_latex(match.group(1))
        if (
            len(latex) < 20
            or OUTER_EQUATION_END_RE.search(latex)
            or latex.startswith(("4pt]", "[4pt]"))
            or any(existing["latex"] == latex for existing in equations)
        ):
            continue
        equations.append(
            {
                "equation_id": f"eq-{len(equations) + 1}",
                "label": _equation_label(latex),
                "latex": latex,
                "role": _equation_role(latex),
                "source_path": source_path,
            }
        )
    if not equations and not _has_disallowed_equation_characters(text):
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("```"):
                continue
            if "\\" not in stripped and not any(token in stripped.lower() for token in ("softmax", "attention", "loss")):
                continue
            latex = _clean_equation_latex(stripped)
            if len(latex) < 20 or OUTER_EQUATION_END_RE.search(latex) or latex.startswith(("4pt]", "[4pt]")):
                continue
            equations.append(
                {
                    "equation_id": f"eq-{len(equations) + 1}",
                    "label": _equation_label(latex),
                    "latex": latex,
                    "role": _equation_role(latex),
                    "source_path": source_path,
                }
            )
    return equations


def _score_equation(equation: dict[str, Any]) -> int:
    role = equation.get("role", "")
    role_score = {
        "latent_reasoning": 80,
        "router_selection": 75,
        "hybrid_mask": 70,
        "trajectory_querying": 65,
        "training_objective": 50,
    }.get(role, 20)
    latex = equation.get("latex", "")
    label_bonus = 10 if equation.get("label") else 0
    quality_bonus = 60 if _quality_score(equation.get("quality_score")) >= HIGH_QUALITY_EVIDENCE_THRESHOLD else 0
    return role_score + label_bonus + quality_bonus + min(20, len(latex) // 80)


def _layout_equation_candidates(conn: Any, paper_key: str) -> list[dict[str, Any]]:
    run_id = _latest_completed_layout_run_id(conn, paper_key)
    if run_id is None:
        return []
    rows = conn.execute(
        """
        select id, page_index, block_index, text, metadata_json
        from paper_layout_blocks
        where paper_key = ? and run_id = ? and block_type = 'interline_equation'
        order by page_index, block_index
        """,
        (paper_key, run_id),
    ).fetchall()
    candidates: list[dict[str, Any]] = []
    for row in rows:
        metadata = parse_json(row["metadata_json"], {})
        if not isinstance(metadata, dict):
            continue
        quality_score = _quality_score(metadata.get("quality_score"))
        if quality_score < HIGH_QUALITY_EVIDENCE_THRESHOLD:
            continue
        latex = _clean_equation_latex(str(row["text"] or ""))
        if len(latex) < 8 or not is_likely_formula(latex):
            continue
        reasons = metadata.get("quality_reasons") if isinstance(metadata.get("quality_reasons"), list) else []
        candidates.append(
            {
                "equation_id": str(metadata.get("equation_id") or f"layout-eq-{row['id']}"),
                "label": "",
                "latex": latex,
                "role": str(metadata.get("equation_role") or _equation_role(latex)),
                "source_path": f"paper_layout_blocks:{int(row['id'])}",
                "source_reference": str(
                    metadata.get("source_reference")
                    or f"page={int(row['page_index']) + 1} block={int(row['block_index'])}"
                ),
                "extraction_method": "airesearch_layout",
                "quality_score": quality_score,
                "quality_reasons": [str(reason) for reason in reasons if str(reason)],
            }
        )
    return candidates


def _publishable_blog_equations(
    equations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    publishable: list[dict[str, Any]] = []
    for equation in equations:
        raw_latex = str(equation.get("latex") or "")
        if not raw_latex or _has_disallowed_equation_characters(raw_latex):
            continue
        latex = raw_latex.strip()
        if latex:
            publishable.append({**equation, "latex": latex})
    return publishable


def _blog_equations(conn: Any, paper_key: str, *, max_equations: int = MAX_EQUATIONS) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    candidates.extend(_layout_equation_candidates(conn, paper_key))
    source_tex = _source_tex_path(conn, paper_key)
    if source_tex is not None:
        candidates.extend(_candidate_equations_from_text(source_tex.read_text(encoding="utf-8", errors="replace"), source_path=str(source_tex)))
    rows = conn.execute(
        """
        select path from paper_artifacts
        where paper_key = ? and artifact_type = 'equations'
        order by length(path), path
        """,
        (paper_key,),
    ).fetchall()
    for row in rows:
        path = _existing_file(str(row["path"] or ""))
        if path is None:
            continue
        candidates.extend(_candidate_equations_from_text(path.read_text(encoding="utf-8", errors="replace"), source_path=str(path)))

    unique: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        latex = candidate.get("latex", "").strip()
        if not latex or latex in unique:
            continue
        unique[latex] = candidate
    ranked = sorted(
        _publishable_blog_equations(list(unique.values())),
        key=_score_equation,
        reverse=True,
    )
    selected = ranked[: max(0, max_equations)]
    return [
        {**equation, "equation_id": f"eq-{index}"}
        for index, equation in enumerate(selected, start=1)
    ]


@dataclass(frozen=True)
class PaperFigureContext:
    paper_dir: Path
    source_tex: Path | None
    pdf_path: Path | None
    arxiv_id: str
    cache_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class PaperTableContext:
    paper_dir: Path
    source_tex: Path | None
    pdf_path: Path | None
    output_dir: Path


def _paper_db_root(paper_dir: Path) -> Path:
    try:
        return paper_dir.parent.parent
    except IndexError:
        return paper_dir.parent


def _paper_arxiv_id(conn: Any, paper_key: str, paper: Any) -> str:
    ids = parse_json(paper["ids_json"], {})
    meta = parse_json(paper["meta_json"], {})
    candidates = [
        str(ids.get("arxiv_id") or ""),
        str(meta.get("arxiv_id") or ""),
        str(ids.get("url") or ""),
        str(meta.get("url") or ""),
    ]
    rows = conn.execute(
        "select source_type, source_value from paper_sources where paper_key = ? order by id",
        (paper_key,),
    ).fetchall()
    candidates.extend(str(row["source_value"] or "") for row in rows if str(row["source_type"] or "").lower() == "arxiv_id")
    candidates.extend(str(row["source_value"] or "") for row in rows)
    return extract_arxiv_id(*candidates)


def _paper_figure_context(conn: Any, paper_key: str) -> PaperFigureContext | None:
    paper = conn.execute("select * from papers where paper_key = ?", (paper_key,)).fetchone()
    if paper is None:
        return None
    source_tex = _source_tex_path(conn, paper_key)
    paper_dir = _existing_dir(str(paper["paper_dir"] or ""))
    if paper_dir is None and source_tex is not None:
        paper_dir = source_tex.parent
    if paper_dir is None:
        paper_dir = _default_paper_dir(paper_key)
    if paper_dir is None:
        return None
    if source_tex is None and (paper_dir / "source.tex").is_file():
        source_tex = (paper_dir / "source.tex").resolve()
    pdf_path = _paper_pdf_path(conn, paper_key) or (paper_dir / "paper.pdf")
    return PaperFigureContext(
        paper_dir=paper_dir,
        source_tex=source_tex,
        pdf_path=pdf_path if pdf_path.exists() and pdf_path.is_file() else None,
        arxiv_id=_paper_arxiv_id(conn, paper_key, paper),
        cache_dir=_paper_db_root(paper_dir) / ".cache" / "arxiv-sources",
        output_dir=paper_dir / "blog-assets" / "figures",
    )


def _paper_table_context(conn: Any, paper_key: str) -> PaperTableContext | None:
    figure_context = _paper_figure_context(conn, paper_key)
    if figure_context is None:
        return None
    return PaperTableContext(
        paper_dir=figure_context.paper_dir,
        source_tex=figure_context.source_tex,
        pdf_path=figure_context.pdf_path,
        output_dir=figure_context.paper_dir / "blog-assets" / "tables",
    )


def _resolved_figure_candidates(conn: Any, paper_key: str) -> list[dict[str, Any]]:
    context = _paper_figure_context(conn, paper_key)
    if context is None or context.source_tex is None:
        return []
    resolved = resolve_paper_figures(
        source_tex=context.source_tex,
        paper_dir=context.paper_dir,
        pdf_path=context.pdf_path,
        arxiv_id=context.arxiv_id or None,
        cache_dir=context.cache_dir,
        output_dir=context.output_dir,
    )
    candidates: list[dict[str, Any]] = []
    for figure in resolved:
        path = figure.path
        if not path.exists() or not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        try:
            asset_path = str(path.relative_to(context.paper_dir))
        except ValueError:
            asset_path = _image_asset_path(path, context.paper_dir)
        candidates.append(
            {
                "asset_path": asset_path,
                "source_path": str(path),
                "caption_seed": figure.record.caption,
                "artifact_type": "resolved_figure",
                "asset_kind": "figure",
                "figure_role": figure.record.role,
                "figure_number": figure.record.number,
                "figure_label": figure.record.label,
                "source_reference": figure.source_reference,
                "extraction_method": figure.extraction_method,
                "confidence": figure.confidence,
                "diagnostics": list(figure.diagnostics),
                "evidence": [asdict(item) for item in figure.record.evidence],
                "content_fingerprint": {
                    "sha256": figure.content_sha256,
                    "size_bytes": path.stat().st_size,
                },
            }
        )
    return candidates


def _resolved_table_candidates(conn: Any, paper_key: str) -> list[dict[str, Any]]:
    context = _paper_table_context(conn, paper_key)
    if context is None or context.pdf_path is None:
        return []
    resolved = resolve_paper_tables(
        source_tex=context.source_tex,
        pdf_path=context.pdf_path,
        output_dir=context.output_dir,
    )
    candidates: list[dict[str, Any]] = []
    for table in resolved:
        path = table.path
        if not path.exists() or not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        try:
            asset_path = str(path.relative_to(context.paper_dir))
        except ValueError:
            asset_path = _image_asset_path(path, context.paper_dir)
        candidates.append(
            {
                "asset_path": asset_path,
                "source_path": str(path),
                "caption_seed": table.record.caption,
                "artifact_type": "resolved_table",
                "asset_kind": "table",
                "figure_role": table.record.role,
                "table_number": table.record.number,
                "table_label": table.record.label,
                "table_score": table.record.score,
                "source_reference": table.source_reference,
                "extraction_method": table.extraction_method,
                "confidence": table.confidence,
                "diagnostics": list(table.diagnostics),
                "evidence": [asdict(item) for item in table.record.evidence],
                "content_fingerprint": {
                    "sha256": table.content_sha256,
                    "size_bytes": path.stat().st_size,
                },
            }
        )
    return candidates


def _resolve_layout_asset_path(asset_path: str, metadata: dict[str, Any]) -> Path | None:
    if not asset_path:
        return None
    candidate = Path(asset_path)
    if candidate.is_absolute() and candidate.exists():
        return candidate.resolve()
    source_path = Path(str(metadata.get("source_path") or ""))
    if source_path.exists():
        relative_candidate = source_path.parent / asset_path
        if relative_candidate.exists():
            return relative_candidate.resolve()
    if candidate.exists():
        return candidate.resolve()
    return None


def _layout_visual_candidates(conn: Any, paper_key: str) -> list[dict[str, Any]]:
    run_id = _latest_completed_layout_run_id(conn, paper_key)
    if run_id is None:
        return []
    paper = conn.execute("select paper_dir from papers where paper_key = ?", (paper_key,)).fetchone()
    paper_dir = _existing_dir(str(paper["paper_dir"] or "")) if paper is not None else None
    if paper_dir is None:
        return []
    output_dir = paper_dir / "blog-assets" / "layout"
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = conn.execute(
        """
        select id, page_index, block_index, block_type, bbox_json, text, asset_path, metadata_json
        from paper_layout_blocks
        where paper_key = ? and run_id = ?
          and asset_path <> ''
          and block_type in ('image', 'table', 'chart')
        order by page_index, block_index, id
        """,
        (paper_key, run_id),
    ).fetchall()
    candidates: list[dict[str, Any]] = []
    for row in rows:
        metadata = parse_json(row["metadata_json"], {})
        original_path = _resolve_layout_asset_path(str(row["asset_path"] or ""), metadata if isinstance(metadata, dict) else {})
        if original_path is None or original_path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        copied_name = f"page-{int(row['page_index']) + 1}-block-{row['block_index']}{original_path.suffix.lower()}"
        source_path = output_dir / copied_name
        if not source_path.exists() or hashlib.sha256(source_path.read_bytes()).hexdigest() != hashlib.sha256(original_path.read_bytes()).hexdigest():
            shutil.copy2(original_path, source_path)
        try:
            asset_path = str(source_path.relative_to(paper_dir))
        except ValueError:
            asset_path = str(source_path)
        caption = (
            str(metadata.get("caption") or "").strip()
            if isinstance(metadata, dict)
            else ""
        ) or str(row["text"] or "").strip() or f"Layout {row['block_type']} page {int(row['page_index']) + 1}"
        asset_kind = "table" if str(row["block_type"]) == "table" else "figure"
        figure_number = _figure_number(caption) if asset_kind == "figure" else None
        bbox = parse_json(row["bbox_json"], [])
        dimensions = image_dimensions(source_path)
        confidence = 0.72
        quality_score = 0.0
        quality_reasons: list[str] = []
        if isinstance(metadata, dict):
            try:
                confidence = float(metadata.get("evidence_confidence") or confidence)
            except (TypeError, ValueError):
                confidence = 0.72
            try:
                quality_score = float(metadata.get("quality_score") or 0)
            except (TypeError, ValueError):
                quality_score = 0.0
            if isinstance(metadata.get("quality_reasons"), list):
                quality_reasons = [str(reason) for reason in metadata.get("quality_reasons") or [] if str(reason)]
        candidates.append(
            {
                "asset_path": asset_path,
                "source_path": str(source_path),
                "caption_seed": caption,
                "artifact_type": "layout_block",
                "asset_kind": asset_kind,
                "figure_role": "table" if asset_kind == "table" else "figure",
                "figure_number": figure_number,
                "figure_label": f"Figure {figure_number}" if figure_number is not None else "",
                "page_index": int(row["page_index"]),
                "block_index": int(row["block_index"]),
                "bbox": bbox if isinstance(bbox, list) else [],
                "dimensions": (
                    {"width": dimensions.width, "height": dimensions.height, "area": dimensions.area}
                    if dimensions is not None
                    else {}
                ),
                "source_reference": (
                    str(metadata.get("source_reference") or "")
                    if isinstance(metadata, dict)
                    else ""
                )
                or f"layout_structure_json page={int(row['page_index']) + 1} block={row['block_index']}",
                "extraction_method": "airesearch_layout",
                "confidence": confidence,
                "quality_score": quality_score,
                "quality_reasons": quality_reasons,
                "evidence": [
                    {
                        "source": "paper_layout_blocks",
                        "row_id": int(row["id"]),
                        "page_index": int(row["page_index"]),
                        "block_index": int(row["block_index"]),
                        "block_type": str(row["block_type"] or ""),
                        "original_asset_path": str(original_path),
                    }
                ],
                "content_fingerprint": {
                    "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                    "size_bytes": source_path.stat().st_size,
                },
            }
        )
    return candidates


def _connection_db_path(conn: Any) -> Path | None:
    try:
        rows = conn.execute("pragma database_list").fetchall()
    except Exception:
        return None
    for row in rows:
        name = row["name"] if hasattr(row, "keys") else row[1]
        if str(name) != "main":
            continue
        value = row["file"] if hasattr(row, "keys") else row[2]
        path = Path(str(value or ""))
        return path if path.exists() else None
    return None


def _layout_pdf_crop_candidates(conn: Any, paper_key: str) -> list[dict[str, Any]]:
    db_path = _connection_db_path(conn)
    if db_path is None:
        return []
    paper = conn.execute("select paper_dir from papers where paper_key = ?", (paper_key,)).fetchone()
    paper_dir = _existing_dir(str(paper["paper_dir"] or "")) if paper is not None else None
    if paper_dir is None:
        return []
    candidates: list[dict[str, Any]] = []
    for candidate in layout_service_visual_candidates(db_path, paper_key, source_dir=paper_dir):
        if candidate.source_kind != "pdf_figure_crop":
            continue
        source_path = candidate.source_path
        if not source_path.exists() or not source_path.is_file() or source_path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        try:
            asset_path = str(source_path.relative_to(paper_dir))
        except ValueError:
            asset_path = _image_asset_path(source_path, paper_dir)
        caption = candidate.caption or source_path.stem
        figure_number = _figure_number(caption)
        candidates.append(
            {
                "asset_path": asset_path,
                "source_path": str(source_path),
                "caption_seed": caption,
                "artifact_type": "layout_pdf_crop",
                "asset_kind": candidate.asset_kind,
                "figure_role": _figure_role(caption),
                "figure_number": figure_number,
                "figure_label": f"Figure {figure_number}" if figure_number is not None else "",
                "page_index": candidate.page_index,
                "block_index": candidate.block_index,
                "dimensions": (
                    {
                        "width": candidate.dimensions.width,
                        "height": candidate.dimensions.height,
                        "area": candidate.dimensions.area,
                    }
                    if candidate.dimensions is not None
                    else {}
                ),
                "source_reference": candidate.source_reference,
                "extraction_method": "airesearch_pdf_figure_crop",
                "confidence": candidate.confidence,
                "quality_score": max(0.86, min(1.0, candidate.confidence)),
                "quality_reasons": ["pdf-figure-crop", candidate.source_kind],
                "diagnostics": [candidate.reason],
                "evidence": [
                    {
                        "source": "layout_service.visual_candidates",
                        "source_kind": candidate.source_kind,
                        "page_index": candidate.page_index,
                        "block_index": candidate.block_index,
                    }
                ],
                "content_fingerprint": {
                    "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                    "size_bytes": source_path.stat().st_size,
                },
            }
        )
    return candidates


def _publishable_layout_coverage(candidates: list[dict[str, Any]]) -> tuple[int, int]:
    publishable = _ordered_visual_candidates(candidates, max_images=MAX_IMAGES)
    figure_count = sum(str(candidate.get("asset_kind") or "") != "table" for candidate in publishable)
    table_count = sum(str(candidate.get("asset_kind") or "") == "table" for candidate in publishable)
    return figure_count, table_count


def _image_candidates(conn: Any, paper_key: str) -> list[dict[str, Any]]:
    layout_pdf_candidates = _layout_pdf_crop_candidates(conn, paper_key)
    layout_visual_candidates = _layout_visual_candidates(conn, paper_key)
    figure_count, table_count = _publishable_layout_coverage(
        [*layout_pdf_candidates, *layout_visual_candidates]
    )
    resolved_figures = (
        []
        if figure_count >= 2
        else _resolved_figure_candidates(conn, paper_key)
    )
    resolved_tables = (
        []
        if table_count >= 1
        else _resolved_table_candidates(conn, paper_key)
    )
    return [
        *layout_pdf_candidates,
        *layout_visual_candidates,
        *resolved_figures,
        *resolved_tables,
    ]


def build_blog_evidence_pack(db_path: Path, paper_key: str, *, max_source_chars: int = 24000) -> BlogEvidencePack:
    ensure_blog_schema(db_path)
    with connect(db_path) as conn:
        paper = conn.execute("select * from papers where paper_key = ?", (paper_key,)).fetchone()
        if paper is None:
            raise KeyError(paper_key)
        authors = parse_json(paper["authors_json"], [])
        ids = parse_json(paper["ids_json"], {})
        layout_table_reserve = min(4000, max(0, max_source_chars // 4))
        artifact_texts = _artifact_texts(conn, paper_key, max(0, max_source_chars - layout_table_reserve))
        remaining_source_chars = max(0, max_source_chars - sum(len(text) for text in artifact_texts.values()))
        layout_tables = _layout_structured_table_text(conn, paper_key, max_chars=remaining_source_chars)
        if layout_tables:
            artifact_texts["layout_structured_tables"] = layout_tables
        facts = _blog_facts(conn, paper_key)
        code_links = _code_links(conn, paper_key)
        citations = _citations(conn, paper_key)
        images = _image_candidates(conn, paper_key)
        equations = _blog_equations(conn, paper_key)
        card_row = conn.execute("select * from paper_cards where paper_key = ?", (paper_key,)).fetchone()

    normalized_authors = [str(author) for author in authors] if isinstance(authors, list) else []
    normalized_ids = ids if isinstance(ids, dict) else {}
    paper_card = dict(card_row) if card_row is not None else {}
    payload_for_hash = {
        "paper_key": paper_key,
        "title": paper["title"] or "",
        "authors": normalized_authors,
        "year": paper["year"],
        "venue": paper["venue"] or "",
        "ids": normalized_ids,
        "paper_card": paper_card,
        "facts": facts,
        "artifact_texts": artifact_texts,
        "code_links": code_links,
        "citations": citations,
        "image_candidates": images,
        "equations": equations,
    }
    source_hash = hashlib.sha256(stable_json(payload_for_hash).encode("utf-8")).hexdigest()
    return BlogEvidencePack(
        paper_key=paper_key,
        title=str(paper["title"] or paper_key),
        authors=normalized_authors,
        year=paper["year"],
        venue=str(paper["venue"] or ""),
        ids=normalized_ids,
        paper_card=paper_card,
        facts=facts,
        artifact_texts=artifact_texts,
        code_links=code_links,
        citations=citations,
        image_candidates=images,
        equations=equations,
        source_hash=source_hash,
    )


def _image_section_key(path_text: str) -> str:
    lowered = path_text.lower()
    if "cover" in lowered or "overview" in lowered or "abstract" in lowered:
        return "intro"
    if "method" in lowered or "model" in lowered:
        return "method"
    if "experiment" in lowered or "result" in lowered or "table" in lowered or "benchmark" in lowered:
        return "experiments"
    return "architecture"


def _candidate_quality_score(candidate: dict[str, Any]) -> float:
    try:
        return float(candidate.get("quality_score") or 0)
    except (TypeError, ValueError):
        return 0.0


def _image_candidate_score(candidate: dict[str, Any]) -> tuple[int, int, int, str]:
    role = str(candidate.get("figure_role") or "")
    role_score = {
        "framework": 100,
        "motivation": 95,
        "method": 90,
        "experiments": 85,
        "qualitative": 80,
        "efficiency": 72,
        "ablation": 68,
        "figure": 40,
        "table": 35,
        "implementation": 5,
    }.get(role, 20)
    if str(candidate.get("asset_kind") or "") == "table":
        role_score += min(24, int(candidate.get("table_score") or 0) // 4)
    caption = str(candidate.get("caption_seed") or "").lower()
    if any(term in caption for term in ("overview", "framework", "architecture", "pipeline", "roadmap")):
        role_score += 12
    if any(term in caption for term in ("example", "qualitative", "case study")):
        role_score += 10
    quality_score = _candidate_quality_score(candidate)
    if quality_score >= 0.72:
        role_score += 70
    elif quality_score > 0:
        role_score += int(quality_score * 28)
    if str(candidate.get("artifact_type") or "") == "cover":
        role_score -= 60
    visual_number = int(candidate.get("figure_number") or candidate.get("table_number") or 999)
    quality_rank = -int(quality_score * 1000)
    return (-role_score, quality_rank, visual_number, str(candidate.get("asset_path") or ""))


def _valid_visual_candidate(candidate: dict[str, Any]) -> bool:
    source_path = Path(candidate["source_path"])
    if not source_path.exists() or not source_path.is_file() or source_path.suffix.lower() not in IMAGE_SUFFIXES:
        return False
    asset_path = str(candidate.get("asset_path") or "")
    return bool(asset_path) and not asset_path.startswith(("http://", "https://", "//"))


def _normalized_visual_caption(candidate: dict[str, Any]) -> str:
    caption = str(candidate.get("caption_seed") or candidate.get("caption") or "").casefold()
    return " ".join(re.findall(r"[\w\u4e00-\u9fff]+", caption, flags=re.UNICODE))


def _candidate_page_index(candidate: dict[str, Any]) -> int | None:
    value = candidate.get("page_index")
    try:
        if value is not None:
            return int(value)
    except (TypeError, ValueError):
        pass
    evidence = candidate.get("evidence")
    if isinstance(evidence, list):
        for item in evidence:
            if not isinstance(item, dict) or item.get("page_index") is None:
                continue
            try:
                return int(item["page_index"])
            except (TypeError, ValueError):
                continue
    return None


def _candidate_figure_number(candidate: dict[str, Any]) -> int | None:
    value = candidate.get("figure_number")
    try:
        return int(value) if value is not None else _figure_number(
            str(candidate.get("caption_seed") or candidate.get("caption") or "")
        )
    except (TypeError, ValueError):
        return _figure_number(str(candidate.get("caption_seed") or candidate.get("caption") or ""))


def _caption_has_explicit_subfigure(candidate: dict[str, Any]) -> bool:
    caption = str(candidate.get("caption_seed") or candidate.get("caption") or "")
    return bool(
        re.search(r"\bfig(?:ure)?\.?\s*\d+\s*(?:\([a-z]\)|[a-z]\b)", caption, re.I)
        or re.search(r"图\s*\d+\s*(?:\([a-z]\)|[a-z]\b)", caption, re.I)
    )


def _candidate_bbox(candidate: dict[str, Any]) -> tuple[float, float, float, float] | None:
    bbox = candidate.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        return None
    try:
        x0, y0, x1, y1 = (float(value) for value in bbox)
    except (TypeError, ValueError):
        return None
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def _bbox_contains(parent: tuple[float, float, float, float], child: tuple[float, float, float, float]) -> bool:
    px0, py0, px1, py1 = parent
    cx0, cy0, cx1, cy1 = child
    tolerance = 2.0
    parent_area = (px1 - px0) * (py1 - py0)
    child_area = (cx1 - cx0) * (cy1 - cy0)
    return (
        px0 - tolerance <= cx0
        and py0 - tolerance <= cy0
        and px1 + tolerance >= cx1
        and py1 + tolerance >= cy1
        and parent_area >= child_area * 1.25
    )


def _is_complete_figure_candidate(candidate: dict[str, Any]) -> bool:
    return (
        str(candidate.get("asset_kind") or "") != "table"
        and str(candidate.get("artifact_type") or "") == "layout_pdf_crop"
        and _candidate_figure_number(candidate) is not None
    )


def _is_fragment_of_complete_figure(candidate: dict[str, Any], complete: dict[str, Any]) -> bool:
    if candidate is complete or str(candidate.get("asset_kind") or "") == "table":
        return False
    if _caption_has_explicit_subfigure(candidate):
        return False
    number = _candidate_figure_number(candidate)
    if number is None or number != _candidate_figure_number(complete):
        return False
    page = _candidate_page_index(candidate)
    complete_page = _candidate_page_index(complete)
    if page is not None and complete_page is not None and page != complete_page:
        return False
    same_caption = bool(
        _normalized_visual_caption(candidate)
        and _normalized_visual_caption(candidate) == _normalized_visual_caption(complete)
    )
    candidate_bbox = _candidate_bbox(candidate)
    complete_bbox = _candidate_bbox(complete)
    spatially_contained = bool(
        candidate_bbox is not None
        and complete_bbox is not None
        and _bbox_contains(complete_bbox, candidate_bbox)
    )
    return same_caption or spatially_contained


def _suppress_fragmented_visual_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    complete_figures = [
        candidate for candidate in candidates if _is_complete_figure_candidate(candidate)
    ]
    if not complete_figures:
        return candidates
    return [
        candidate
        for candidate in candidates
        if _is_complete_figure_candidate(candidate)
        or not any(
            _is_fragment_of_complete_figure(candidate, complete)
            for complete in complete_figures
        )
    ]


def _ordered_visual_candidates(candidates: list[dict[str, Any]], *, max_images: int) -> list[dict[str, Any]]:
    limit = max(0, max_images)
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    ranked = sorted(_suppress_fragmented_visual_candidates(candidates), key=_image_candidate_score)
    for candidate in ranked:
        if not _valid_visual_candidate(candidate):
            continue
        fingerprint = candidate.get("content_fingerprint") if isinstance(candidate.get("content_fingerprint"), dict) else {}
        key = str(fingerprint.get("sha256") or candidate.get("source_path") or candidate.get("asset_path") or "")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        ordered.append(candidate)
    if limit <= 0:
        return []
    figures = [candidate for candidate in ordered if str(candidate.get("asset_kind") or "") != "table"]
    tables = [candidate for candidate in ordered if str(candidate.get("asset_kind") or "") == "table"]
    if not figures:
        return tables[:limit]

    selected = figures[:limit]
    if not tables or any(str(candidate.get("asset_kind") or "") == "table" for candidate in selected):
        return selected
    table = tables[0]
    if len(selected) < limit:
        return [*selected, table]
    selected[-1] = table
    return selected


def _select_blog_images_from_candidates(
    candidates: list[dict[str, Any]],
    *,
    max_images: int = MAX_IMAGES,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for candidate in _ordered_visual_candidates(candidates, max_images=max_images):
        if len(selected) >= max(0, max_images):
            break
        source_path = Path(candidate["source_path"])
        asset_path = str(candidate["asset_path"] or "")
        caption_seed = candidate.get("caption_seed") or source_path.name
        role = str(candidate.get("figure_role") or _figure_role(asset_path))
        image = {
            "image_id": f"img-{len(selected) + 1}",
            "asset_path": asset_path,
            "source_path": str(source_path),
            "caption": str(caption_seed),
            "section_key": _figure_section_key(role, str(caption_seed)) or _image_section_key(asset_path),
            "selection_reason": f"semantic-{role}",
            "figure_role": role,
            "asset_kind": str(candidate.get("asset_kind") or "figure"),
            "artifact_type": str(candidate.get("artifact_type") or ""),
        }
        for key in (
            "figure_number",
            "figure_label",
            "table_number",
            "table_label",
            "table_score",
            "source_reference",
            "extraction_method",
            "confidence",
            "quality_score",
            "quality_reasons",
            "diagnostics",
            "evidence",
            "page_index",
            "block_index",
            "bbox",
            "dimensions",
            "content_fingerprint",
        ):
            if key in candidate:
                image[key] = candidate[key]
        selected.append(image)
    return selected


def select_blog_images(db_path: Path, paper_key: str, *, max_images: int = MAX_IMAGES) -> list[dict[str, Any]]:
    pack = build_blog_evidence_pack(db_path, paper_key, max_source_chars=2000)
    return _select_blog_images_from_candidates(pack.image_candidates, max_images=max_images)


def refresh_published_blog_images(db_path: Path, paper_key: str, *, max_images: int = MAX_IMAGES) -> PublishedBlogVersion:
    """Refresh published image evidence without regenerating the blog text."""
    ensure_blog_schema(db_path)
    pack = build_blog_evidence_pack(db_path, paper_key)
    images = _select_blog_images_from_candidates(pack.image_candidates, max_images=max_images)
    with connect(db_path) as conn:
        post = conn.execute("select * from paper_blog_posts where paper_key = ?", (paper_key,)).fetchone()
        if post is None or str(post["status"] or "") != "published":
            raise KeyError(paper_key)
        current_version_id = int(post["current_version_id"] or 0)
        version = conn.execute(
            "select * from paper_blog_versions where id = ? and paper_key = ?",
            (current_version_id, paper_key),
        ).fetchone()
        if version is None:
            raise KeyError(f"{paper_key}:{current_version_id}")
        old_images = parse_json(post["image_refs_json"], [])
        old_images = [item for item in old_images if isinstance(item, dict)] if isinstance(old_images, list) else []

        def identity(item: dict[str, Any]) -> tuple[Any, ...]:
            return (
                item.get("artifact_type"),
                item.get("asset_kind"),
                item.get("figure_number"),
                item.get("table_number"),
                item.get("page_index"),
                item.get("block_index"),
            )

        old_by_identity = {identity(item): item for item in old_images}
        replacement_by_path: dict[str, str] = {}
        for index, new in enumerate(images, start=1):
            old = old_by_identity.get(identity(new))
            if old is not None:
                new["image_id"] = str(old.get("image_id") or f"img-{index}")
            old_path = _normalize_declared_asset_path(old.get("asset_path")) if old is not None else ""
            new_path = _normalize_declared_asset_path(new.get("asset_path"))
            if old_path and new_path and old_path != new_path:
                replacement_by_path[old_path] = new_path
        markdown = _rewrite_markdown_image_destinations(
            str(post["markdown"] or ""),
            replacement_by_path,
        )
        outline = parse_json(version["outline_json"], {})
        generation_meta = parse_json(version["generation_meta_json"], {})
        if not isinstance(generation_meta, dict):
            generation_meta = {}
        generation_meta = {
            **generation_meta,
            "image_refresh": {
                "without_text_regeneration": True,
                "previous_version_id": current_version_id,
                "image_count": len(images),
            },
        }
        html = str(version["html"] or "")
        for old_path, new_path in replacement_by_path.items():
            html = html.replace(old_path, new_path)

    return publish_blog_version(
        db_path,
        paper_key=paper_key,
        title=str(version["title"] or pack.title),
        slug=str(post["slug"] or slugify(paper_key)),
        markdown=markdown,
        html=html,
        outline=outline if isinstance(outline, dict) else {},
        image_refs=images,
        generation_meta=generation_meta,
        model=str(version["model"] or DEFAULT_BLOG_MODEL),
        prompt_version=str(version["prompt_version"] or BLOG_PROMPT_VERSION),
        source_hash=pack.source_hash,
        expected_source_version_id=current_version_id,
    )


def ensure_blog_schema(db_path: Path) -> None:
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            create table if not exists paper_blog_posts (
                paper_key text primary key references papers(paper_key) on delete cascade,
                current_version_id integer,
                title text not null default '',
                slug text not null default '',
                status text not null default 'published' check (status in ('published', 'hidden', 'failed')),
                target_audience text not null default 'ai_engineer',
                language text not null default 'zh',
                word_count integer not null default 0,
                markdown text not null default '',
                html text not null default '',
                outline_json text not null default '{}',
                image_refs_json text not null default '[]',
                model text not null default '',
                prompt_version text not null default '',
                source_hash text not null default '',
                created_at text not null,
                updated_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists paper_blog_versions (
                id integer primary key autoincrement,
                paper_key text not null references papers(paper_key) on delete cascade,
                version_number integer not null,
                status text not null default 'published' check (status in ('published', 'superseded', 'hidden', 'failed')),
                title text not null default '',
                word_count integer not null default 0,
                markdown text not null default '',
                html text not null default '',
                outline_json text not null default '{}',
                image_refs_json text not null default '[]',
                generation_meta_json text not null default '{}',
                model text not null default '',
                prompt_version text not null default '',
                source_hash text not null default '',
                created_at text not null,
                unique(paper_key, version_number)
            )
            """
        )
        conn.execute(
            """
            create table if not exists paper_blog_generation_cache (
                id integer primary key autoincrement,
                paper_key text not null references papers(paper_key) on delete cascade,
                section_key text not null,
                source_hash text not null,
                prompt_version text not null,
                model text not null,
                request_hash text not null,
                response_json text not null default '{}',
                markdown text not null default '',
                token_estimate integer not null default 0,
                created_at text not null,
                updated_at text not null,
                unique(paper_key, section_key, source_hash, prompt_version, model, request_hash)
            )
            """
        )
        conn.execute("create index if not exists idx_paper_blog_posts_status on paper_blog_posts(status)")
        conn.execute(
            "create index if not exists idx_paper_blog_versions_paper_key "
            "on paper_blog_versions(paper_key, version_number desc)"
        )
        conn.execute(
            """
            create index if not exists idx_paper_blog_cache_lookup
            on paper_blog_generation_cache(paper_key, section_key, source_hash, prompt_version, model, request_hash)
            """
        )
        conn.commit()


def _require_paper_row(conn: Any, paper_key: str) -> None:
    row = conn.execute("select 1 from papers where paper_key = ?", (paper_key,)).fetchone()
    if row is None:
        raise KeyError(paper_key)


def publish_blog_version(
    db_path: Path,
    *,
    paper_key: str,
    title: str,
    slug: str,
    markdown: str,
    html: str,
    outline: dict[str, Any],
    image_refs: list[dict[str, Any]],
    generation_meta: dict[str, Any],
    model: str,
    prompt_version: str,
    source_hash: str,
    expected_source_version_id: int | None = None,
) -> PublishedBlogVersion:
    ensure_blog_schema(db_path)
    now = utc_now()
    word_count = chinese_char_count(markdown)
    with connect(db_path) as conn:
        conn.execute("begin immediate")
        _require_paper_row(conn, paper_key)
        if expected_source_version_id is not None:
            current = conn.execute(
                "select current_version_id from paper_blog_posts where paper_key = ?",
                (paper_key,),
            ).fetchone()
            if current is None or int(current["current_version_id"]) != expected_source_version_id:
                raise BlogVersionConflictError(
                    f"blog version changed before publish: expected {expected_source_version_id}"
                )
        row = conn.execute(
            "select coalesce(max(version_number), 0) as version_number from paper_blog_versions where paper_key = ?",
            (paper_key,),
        ).fetchone()
        version_number = int(row["version_number"] or 0) + 1
        conn.execute(
            "update paper_blog_versions set status = 'superseded' where paper_key = ? and status = 'published'",
            (paper_key,),
        )
        cursor = conn.execute(
            """
            insert into paper_blog_versions (
                paper_key, version_number, status, title, word_count, markdown, html,
                outline_json, image_refs_json, generation_meta_json, model, prompt_version,
                source_hash, created_at
            ) values (?, ?, 'published', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper_key,
                version_number,
                title,
                word_count,
                markdown,
                html,
                stable_json(outline),
                stable_json(image_refs),
                stable_json(generation_meta),
                model,
                prompt_version,
                source_hash,
                now,
            ),
        )
        version_id = int(cursor.lastrowid)
        conn.execute(
            """
            insert into paper_blog_posts (
                paper_key, current_version_id, title, slug, status, target_audience,
                language, word_count, markdown, html, outline_json, image_refs_json,
                model, prompt_version, source_hash, created_at, updated_at
            ) values (?, ?, ?, ?, 'published', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(paper_key) do update set
                current_version_id = excluded.current_version_id,
                title = excluded.title,
                slug = excluded.slug,
                status = 'published',
                target_audience = excluded.target_audience,
                language = excluded.language,
                word_count = excluded.word_count,
                markdown = excluded.markdown,
                html = excluded.html,
                outline_json = excluded.outline_json,
                image_refs_json = excluded.image_refs_json,
                model = excluded.model,
                prompt_version = excluded.prompt_version,
                source_hash = excluded.source_hash,
                updated_at = excluded.updated_at
            """,
            (
                paper_key,
                version_id,
                title,
                slug,
                BLOG_TARGET_AUDIENCE,
                BLOG_LANGUAGE,
                word_count,
                markdown,
                html,
                stable_json(outline),
                stable_json(image_refs),
                model,
                prompt_version,
                source_hash,
                now,
                now,
            ),
        )
        conn.commit()
    return PublishedBlogVersion(paper_key, version_id, version_number, word_count, "published")


def blog_detail(db_path: Path, paper_key: str) -> dict[str, Any]:
    ensure_blog_schema(db_path)
    with connect(db_path) as conn:
        post = conn.execute("select * from paper_blog_posts where paper_key = ?", (paper_key,)).fetchone()
        versions = conn.execute(
            "select * from paper_blog_versions where paper_key = ? order by version_number desc",
            (paper_key,),
        ).fetchall()
    return {
        "post": dict(post) if post else None,
        "versions": [dict(version) for version in versions],
    }


def rollback_blog_post(db_path: Path, paper_key: str, version_id: int) -> dict[str, Any]:
    ensure_blog_schema(db_path)
    now = utc_now()
    with connect(db_path) as conn:
        _require_paper_row(conn, paper_key)
        version = conn.execute(
            "select * from paper_blog_versions where id = ? and paper_key = ?",
            (version_id, paper_key),
        ).fetchone()
        if version is None:
            raise KeyError(str(version_id))
        conn.execute(
            "update paper_blog_versions set status = 'superseded' where paper_key = ? and status = 'published'",
            (paper_key,),
        )
        conn.execute("update paper_blog_versions set status = 'published' where id = ?", (version_id,))
        conn.execute(
            """
            insert into paper_blog_posts (
                paper_key, current_version_id, title, slug, status, target_audience,
                language, word_count, markdown, html, outline_json, image_refs_json,
                model, prompt_version, source_hash, created_at, updated_at
            ) values (?, ?, ?, ?, 'published', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(paper_key) do update set
                current_version_id = excluded.current_version_id,
                title = excluded.title,
                slug = excluded.slug,
                status = 'published',
                word_count = excluded.word_count,
                markdown = excluded.markdown,
                html = excluded.html,
                outline_json = excluded.outline_json,
                image_refs_json = excluded.image_refs_json,
                model = excluded.model,
                prompt_version = excluded.prompt_version,
                source_hash = excluded.source_hash,
                updated_at = excluded.updated_at
            """,
            (
                paper_key,
                version_id,
                version["title"],
                slugify(paper_key),
                BLOG_TARGET_AUDIENCE,
                BLOG_LANGUAGE,
                version["word_count"],
                version["markdown"],
                version["html"],
                version["outline_json"],
                version["image_refs_json"],
                version["model"],
                version["prompt_version"],
                version["source_hash"],
                now,
                now,
            ),
        )
        conn.commit()
    return {"paper_key": paper_key, "current_version_id": version_id, "status": "published"}


def hide_blog_post(db_path: Path, paper_key: str) -> dict[str, Any]:
    ensure_blog_schema(db_path)
    with connect(db_path) as conn:
        cursor = conn.execute(
            "update paper_blog_posts set status = 'hidden', updated_at = ? where paper_key = ?",
            (utc_now(), paper_key),
        )
        if cursor.rowcount == 0:
            raise KeyError(paper_key)
        conn.commit()
    return {"paper_key": paper_key, "status": "hidden"}


class BlogValidationError(ValueError):
    pass


class BlogProvider:
    name = "base"

    def generate_outline(
        self,
        pack: BlogEvidencePack,
        images: list[dict[str, Any]],
        *,
        target_chars: int,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def generate_section(
        self,
        pack: BlogEvidencePack,
        section: dict[str, Any],
        images: list[dict[str, Any]],
        *,
        target_chars: int,
    ) -> dict[str, Any]:
        raise NotImplementedError


DEFAULT_SECTIONS = [
    ("intro", "导读"),
    ("background", "背景"),
    ("method", "核心方法"),
    ("architecture", "架构拆解"),
    ("experiments", "实验与指标"),
    ("engineering", "工程启发"),
    ("limitations", "局限性"),
    ("further_reading", "延伸阅读"),
]


class FixtureBlogProvider(BlogProvider):
    name = "fixture-blog"

    def __init__(self, *, chars_per_section: int = 520) -> None:
        self.chars_per_section = chars_per_section
        self.call_count = 0

    def generate_outline(
        self,
        pack: BlogEvidencePack,
        images: list[dict[str, Any]],
        *,
        target_chars: int,
    ) -> dict[str, Any]:
        self.call_count += 1
        per_section = max(350, target_chars // len(DEFAULT_SECTIONS))
        return {
            "title": f"{pack.title} 深度解读",
            "sections": [
                {
                    "section_key": key,
                    "title": title,
                    "purpose": f"面向工程读者解释{title}",
                    "fact_ids": [fact["fact_id"] for fact in pack.facts[:4]],
                    "image_ids": [image["image_id"] for image in images if image["section_key"] == key],
                    "target_chars": per_section,
                }
                for key, title in DEFAULT_SECTIONS
            ],
        }

    def generate_section(
        self,
        pack: BlogEvidencePack,
        section: dict[str, Any],
        images: list[dict[str, Any]],
        *,
        target_chars: int,
    ) -> dict[str, Any]:
        self.call_count += 1
        section_image_ids = [str(image_id) for image_id in section.get("image_ids", [])]
        image_by_id = {str(image["image_id"]): image for image in images}
        fact_text = "；".join(fact["statement"] for fact in pack.facts[:3])
        image_lines = []
        for image_id in section_image_ids:
            image = image_by_id.get(image_id)
            if image is not None:
                image_lines.append(
                    f"![{image['caption']}]({_markdown_image_destination(image['asset_path'])})"
                    f"\n\n图注：{image['caption']}"
                )
        repeated = (
            f"{section['title']}部分围绕论文展开，重点解释它对工程实践的影响。"
            "这一段会先说明问题背景，再拆解方法假设、数据流向、模块职责、训练条件、"
            "评估边界和部署约束。对于实现者来说，关键不是复述结论，而是判断哪些设计"
            "可以迁移到自己的系统，哪些设计依赖论文中的实验设置。"
        )
        body = (repeated * max(1, (self.chars_per_section // max(1, len(repeated))) + 1))[
            : self.chars_per_section
        ]
        if fact_text:
            body = f"{body}\n\n证据摘要：{fact_text[:240]}"
        markdown = f"## {section['title']}\n\n{body}\n\n" + "\n\n".join(image_lines)
        if pack.equations and section.get("section_key") in {"method", "architecture"}:
            equation_blocks = []
            for equation in pack.equations[:2]:
                equation_blocks.append(
                    "$$\n{latex}\n$$\n\n{explanation}".format(
                        latex=equation["latex"],
                        explanation=OpenAICompatibleBlogProvider._equation_explanation(equation),
                    )
                )
            markdown = markdown.rstrip() + "\n\n### 关键公式\n\n" + "\n\n".join(equation_blocks)
        return {
            "section_key": section["section_key"],
            "markdown": markdown.strip() + "\n",
            "fact_ids": section.get("fact_ids", []),
            "image_ids": section.get("image_ids", []),
            "notes": "fixture section generated from deterministic evidence.",
        }


def _strip_json_fence(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    return re.sub(r"\s*```$", "", text).strip()


def _responses_output_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return str(payload["output_text"])
    output = payload.get("output")
    if not isinstance(output, list):
        return ""
    chunks: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content_items = item.get("content")
        if not isinstance(content_items, list):
            continue
        for content in content_items:
            if not isinstance(content, dict) or content.get("type") not in {"output_text", "text"}:
                continue
            chunks.append(str(content.get("text") or ""))
    return "".join(chunks)


def _redact_provider_detail(value: str, api_key: str) -> str:
    detail = str(value or "")
    if api_key:
        detail = detail.replace(api_key, "[REDACTED]")
    return detail[:800]


class OpenAICompatibleBlogTransport:
    @staticmethod
    def _normalize_base_url(base_url: str | None) -> str:
        normalized = api_root(base_url or "https://api.openai.com/v1")
        if normalized == "https://api.deepseek.com":
            return normalized + "/v1"
        return normalized

    @classmethod
    def _uses_deepseek(cls, *, model: str, base_url: str | None) -> bool:
        endpoint = cls._normalize_base_url(base_url).lower()
        return "deepseek" in model.lower() or endpoint.startswith("https://api.deepseek.com/")

    @classmethod
    def _request_payload(
        cls,
        *,
        model: str,
        base_url: str | None,
        messages: list[dict[str, Any]],
        max_output_tokens: int,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        if cls._uses_deepseek(model=model, base_url=base_url):
            payload["thinking"] = {"type": "disabled"}
        return payload

    def complete_json(
        self,
        *,
        model: str,
        base_url: str | None,
        api_key: str,
        messages: list[dict[str, Any]],
        max_output_tokens: int,
    ) -> dict[str, Any]:
        import urllib.error
        import urllib.request

        endpoint = self._normalize_base_url(base_url) + "/chat/completions"
        body = stable_json(
            self._request_payload(
                model=model,
                base_url=base_url,
                messages=messages,
                max_output_tokens=max_output_tokens,
            )
        ).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "authorization": f"Bearer {api_key}",
                "content-type": "application/json",
                "User-Agent": "OpenClaw/1.0",
                "Accept": "application/json",
            },
            method="POST",
        )
        failure = ""
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = _redact_provider_detail(exc.read().decode("utf-8", errors="replace"), api_key)
            failure = f"provider HTTP {exc.code}: {detail}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            failure = f"provider request failed: {_redact_provider_detail(str(exc), api_key)}"
        if failure:
            raise BlogValidationError(failure)
        invalid_detail = ""
        try:
            choice = payload["choices"][0]
            content = choice["message"]["content"]
            result = json.loads(_strip_json_fence(str(content)))
            if not isinstance(result, dict):
                raise TypeError("response JSON must be an object")
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            finish_reason = ""
            content_chars = 0
            try:
                choice = payload["choices"][0]
                finish_reason = str(choice.get("finish_reason") or "")
                content_chars = len(str(choice.get("message", {}).get("content") or ""))
            except (KeyError, IndexError, TypeError, AttributeError):
                pass
            detail = f"provider returned invalid JSON: {exc}"
            if finish_reason or content_chars:
                detail += f" (finish_reason={finish_reason or 'unknown'}, content_chars={content_chars})"
            invalid_detail = detail
        if invalid_detail:
            raise BlogValidationError(invalid_detail)
        return result


ResponsesHTTPTransport = Callable[
    [str, dict[str, str], dict[str, object], float, str],
    dict[str, object],
]


class OpenAIResponsesBlogTransport:
    def __init__(
        self,
        *,
        proxy_url: str = "",
        timeout_seconds: float = 120,
        http_transport: ResponsesHTTPTransport | None = None,
    ) -> None:
        self.proxy_url = str(proxy_url or "").strip()
        self.timeout_seconds = float(timeout_seconds)
        self.http_transport = http_transport or self._request_json

    @staticmethod
    def _normalize_endpoint(base_url: str | None) -> str:
        return responses_url(base_url or "https://api.openai.com/v1")

    @staticmethod
    def _request_json(
        endpoint: str,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout: float,
        proxy_url: str,
    ) -> dict[str, object]:
        import urllib.error
        import urllib.request

        request = urllib.request.Request(
            endpoint,
            data=stable_json(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            if proxy_url:
                opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
                )
                response_context = opener.open(request, timeout=timeout)
            else:
                response_context = urllib.request.urlopen(request, timeout=timeout)
            with response_context as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"provider HTTP {exc.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"provider request failed: {exc}") from None
        if not isinstance(decoded, dict):
            raise RuntimeError("provider response must be a JSON object")
        return decoded

    def complete_json(
        self,
        *,
        model: str,
        base_url: str | None,
        api_key: str,
        messages: list[dict[str, Any]],
        max_output_tokens: int,
    ) -> dict[str, Any]:
        endpoint = self._normalize_endpoint(base_url)
        headers = {
            "authorization": f"Bearer {api_key}",
            "content-type": "application/json",
            "User-Agent": "OpenClaw/1.0",
            "Accept": "application/json",
        }
        payload: dict[str, object] = {
            "model": model,
            "input": [
                {
                    "role": str(message.get("role") or "user"),
                    "content": [
                        {
                            "type": "input_text",
                            "text": str(message.get("content") or ""),
                        }
                    ],
                }
                for message in messages
            ],
            "max_output_tokens": max_output_tokens,
        }
        failure = ""
        try:
            response = self.http_transport(
                endpoint,
                headers,
                payload,
                self.timeout_seconds,
                self.proxy_url,
            )
        except Exception as exc:
            failure = _redact_provider_detail(str(exc), api_key) or "unknown provider failure"
        if failure:
            raise BlogValidationError(f"provider request failed: {failure}")
        if not isinstance(response, dict):
            raise BlogValidationError("provider returned an invalid Responses payload")
        output_text = _strip_json_fence(_responses_output_text(response))
        if not output_text:
            raise BlogValidationError("provider returned empty output")
        invalid_detail = ""
        try:
            result = json.loads(output_text)
        except json.JSONDecodeError as exc:
            invalid_detail = f"provider returned invalid JSON: {exc}"
        if invalid_detail:
            raise BlogValidationError(invalid_detail)
        if not isinstance(result, dict):
            raise BlogValidationError("provider response must be a JSON object")
        return result


class OpenAICompatibleBlogProvider(BlogProvider):
    name = "openai-compatible"

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str | None = None,
        transport: OpenAICompatibleBlogTransport | OpenAIResponsesBlogTransport | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.transport = transport or OpenAICompatibleBlogTransport()

    @classmethod
    def from_env(
        cls,
        *,
        model: str | None = None,
        base_url: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        transport: OpenAICompatibleBlogTransport | OpenAIResponsesBlogTransport | None = None,
        api_style: str | None = None,
        proxy_url: str | None = None,
    ) -> "OpenAICompatibleBlogProvider":
        key_env_names = [
            "AIRESEARCH_BLOG_API_KEY",
            api_key_env,
            "OPENCODE_GO_API_KEY",
            "OPENAI_API_KEY",
            "TRANSLATE_API_KEY",
            "NIU_ASSISTANT_API_KEY",
        ]
        api_key = next(
            (
                os.environ.get(env_name, "").strip()
                for env_name in dict.fromkeys(key_env_names)
                if env_name and os.environ.get(env_name, "").strip()
            ),
            "",
        )
        if not api_key:
            raise BlogValidationError(
                "a configured blog API key is required for openai-compatible provider"
            )
        resolved_model = (
            model
            or os.environ.get("AIRESEARCH_BLOG_MODEL")
            or os.environ.get("NIU_ASSISTANT_MODEL")
            or DEFAULT_BLOG_MODEL
        )
        resolved_base_url = (
            base_url
            or os.environ.get("AIRESEARCH_BLOG_BASE_URL")
            or os.environ.get("OPENCODE_GO_BASE_URL")
            or os.environ.get("TRANSLATE_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("NIU_ASSISTANT_API_BASE")
            or DEFAULT_BLOG_BASE_URL
        )
        resolved_transport = transport
        if resolved_transport is None:
            resolved_api_style = (
                api_style
                if api_style is not None
                else os.environ.get("AIRESEARCH_BLOG_API_STYLE", "")
            ).strip().lower().replace("-", "_")
            if not resolved_api_style:
                resolved_api_style = (
                    "responses"
                    if str(resolved_base_url).rstrip("/").lower().endswith("/responses")
                    else "chat_completions"
                )
            if resolved_api_style == "responses":
                resolved_proxy_url = (
                    proxy_url
                    if proxy_url is not None
                    else os.environ.get("AIRESEARCH_BLOG_PROXY", "")
                    or os.environ.get("OPENCODE_GO_PROXY", "")
                )
                resolved_transport = OpenAIResponsesBlogTransport(proxy_url=resolved_proxy_url)
            elif resolved_api_style in {"chat", "chat_completion", "chat_completions"}:
                resolved_transport = OpenAICompatibleBlogTransport()
            else:
                raise BlogValidationError(
                    f"unsupported blog API style: {resolved_api_style}"
                )
        return cls(
            model=resolved_model,
            api_key=api_key,
            base_url=resolved_base_url,
            transport=resolved_transport,
        )

    def _messages(self, task: str, payload: dict[str, Any]) -> list[dict[str, str]]:
        task_instruction = (
            "Return a JSON object with section_key, markdown, fact_ids, and image_ids. "
            "The markdown field must be long-form Chinese technical writing, no fewer than target_chars "
            "Chinese characters, with 5-8 substantial paragraphs and concrete method, evidence, and "
            "engineering interpretation. If equations are supplied, include and explain the relevant "
            "LaTeX formulas using display math blocks."
            if task == "section"
            else "Return a JSON object with title and sections. sections must use the required section_key values."
        )
        return [
            {
                "role": "system",
                "content": (
                    "Return JSON only. Write Chinese technical analysis for AI and software engineers. "
                    "Use only supplied evidence. Introduce English terms in parentheses on first use. "
                    "Do not invent citations, metrics, or image descriptions. "
                    "Prefer image/table/equation evidence with quality_score >= 0.72 when quality_score is supplied. "
                    "For outline return one object with title and sections. "
                    "For section return one object with section_key, markdown, fact_ids, and image_ids. "
                    "Section markdown must be detailed and meet the requested target_chars. "
                    "When equations are supplied, explain at least two key equations in the method or architecture sections."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{task_instruction}\n"
                    f"Generate paper blog {task} from this payload:\n{stable_json(payload)}"
                ),
            },
        ]

    @staticmethod
    def _bounded_artifact_texts(artifact_texts: dict[str, str], max_chars: int) -> dict[str, str]:
        table_text = str(artifact_texts.get("layout_structured_tables") or "")
        table_reserve = min(len(table_text), 2000, max(0, max_chars // 4))
        remaining = max(0, max_chars - table_reserve)
        bounded: dict[str, str] = {}
        for artifact_type, text in artifact_texts.items():
            if artifact_type == "layout_structured_tables":
                continue
            if remaining <= 0:
                break
            excerpt = text[:remaining]
            if excerpt:
                bounded[artifact_type] = excerpt
                remaining -= len(excerpt)
        if table_reserve:
            bounded["layout_structured_tables"] = table_text[:table_reserve]
        return bounded

    @staticmethod
    def _prompt_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {key: value for key, value in fact.items() if key != "evidence_source_path"}
            for fact in facts
        ]

    @staticmethod
    def _prompt_images(images: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                key: value
                for key, value in image.items()
                if key not in {"source_path", "content_fingerprint"}
            }
            for image in images
        ]

    def _paper_prompt_payload(self, pack: BlogEvidencePack, *, max_source_chars: int) -> dict[str, Any]:
        return {
            "paper_key": pack.paper_key,
            "title": pack.title,
            "authors": pack.authors,
            "year": pack.year,
            "venue": pack.venue,
            "ids": pack.ids,
            "facts": self._prompt_facts(pack.facts),
            "artifact_texts": self._bounded_artifact_texts(pack.artifact_texts, max_source_chars),
            "code_links": [
                {key: value for key, value in link.items() if key != "source_path"}
                for link in pack.code_links
            ],
            "citations": [
                {key: value for key, value in citation.items() if key != "source_path"}
                for citation in pack.citations
            ],
            "equations": [
                {key: value for key, value in equation.items() if key != "source_path"}
                for equation in self._publishable_equations(pack.equations)
            ],
            "evidence_quality_policy": {
                "high_quality_threshold": 0.72,
                "use_high_quality_first": True,
            },
            "source_hash": pack.source_hash,
        }

    @staticmethod
    def _equation_explanation(equation: dict[str, str]) -> str:
        role = equation.get("role", "")
        if role == "latent_reasoning":
            return "这个公式描述 VLM 如何把文本、视觉和自车状态编码为统一潜在令牌，是后续潜在推理的输入基础。"
        if role == "router_selection":
            return "这个公式描述轻量路由器如何给视觉令牌打分并选择 Top-K 安全关键令牌，减少冗余感知信息。"
        if role == "hybrid_mask":
            return "这个公式定义混合注意力掩码，使轨迹 token 只能访问当前尺度和前一尺度，从而保持粗到细规划的因果一致性。"
        if role == "trajectory_querying":
            return "这个公式把剪枝后的上下文和多尺度轨迹查询拼接为统一序列，供并行规划器解码。"
        if role == "training_objective":
            return "这个公式描述训练目标如何联合约束轨迹回归和置信度估计。"
        return "这个公式是论文方法推导中的关键定义，帮助把文字描述落到可实现的张量关系上。"

    @classmethod
    def _publishable_equations(
        cls,
        equations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return _publishable_blog_equations(equations)

    @classmethod
    def _append_equation_notes(cls, markdown: str, equations: list[dict[str, str]], *, limit: int = 2) -> str:
        if not equations or "$$" in markdown:
            return markdown
        blocks = ["\n\n### 关键公式\n"]
        for equation in equations[:limit]:
            latex = str(equation.get("latex") or "").strip()
            if not latex:
                continue
            blocks.append(f"$$\n{latex}\n$$\n\n{cls._equation_explanation(equation)}")
        return markdown.rstrip() + "\n\n" + "\n\n".join(blocks).strip()

    @staticmethod
    def _list_or_empty(value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    @classmethod
    def _normalize_outline_result(cls, result: dict[str, Any], pack: BlogEvidencePack) -> dict[str, Any]:
        if not isinstance(result, dict):
            return result
        raw_sections = result.get("sections")
        if not isinstance(raw_sections, list) and isinstance(result.get("outline"), list):
            raw_sections = result.get("outline")
        if not isinstance(raw_sections, list):
            return result

        sections_by_key: dict[str, dict[str, Any]] = {}
        sections_by_title: dict[str, dict[str, Any]] = {}
        for raw in raw_sections:
            if not isinstance(raw, dict):
                continue
            key = str(raw.get("section_key") or raw.get("key") or "").strip()
            title = str(raw.get("title") or "").strip()
            if key:
                sections_by_key[key] = raw
            if title:
                sections_by_title[title] = raw

        normalized_sections: list[dict[str, Any]] = []
        default_target = max(MIN_SECTION_CHARS, min(MAX_SECTION_CHARS, DEFAULT_TARGET_CHARS // len(DEFAULT_SECTIONS)))
        for key, title in DEFAULT_SECTIONS:
            raw = sections_by_key.get(key) or sections_by_title.get(title) or {}
            section = {
                "section_key": key,
                "title": str(raw.get("title") or title),
                "fact_ids": cls._list_or_empty(raw.get("fact_ids")),
                "image_ids": cls._list_or_empty(raw.get("image_ids")),
                "target_chars": int(raw.get("target_chars") or default_target),
            }
            summary = str(raw.get("summary") or raw.get("content") or "").strip()
            if summary:
                section["summary"] = summary
            normalized_sections.append(section)

        normalized = dict(result)
        normalized["title"] = str(result.get("title") or f"{pack.title} 深度解读")
        normalized["sections"] = normalized_sections
        return normalized

    def generate_outline(
        self,
        pack: BlogEvidencePack,
        images: list[dict[str, Any]],
        *,
        target_chars: int,
    ) -> dict[str, Any]:
        payload = {
            "task": "outline",
            "paper": self._paper_prompt_payload(pack, max_source_chars=OUTLINE_SOURCE_CHAR_LIMIT),
            "images": self._prompt_images(images),
            "required_sections": [
                {"section_key": key, "title": title}
                for key, title in DEFAULT_SECTIONS
            ],
            "target_chars": target_chars,
        }
        result = self.transport.complete_json(
            model=self.model,
            base_url=self.base_url,
            api_key=self.api_key,
            messages=self._messages("outline", payload),
            max_output_tokens=OUTLINE_MAX_OUTPUT_TOKENS,
        )
        result = self._normalize_outline_result(result, pack)
        if not isinstance(result.get("sections"), list):
            raise BlogValidationError("outline response missing sections")
        if not isinstance(result.get("title"), str) or not str(result["title"]).strip():
            raise BlogValidationError("outline response missing title")
        return result

    def generate_section(
        self,
        pack: BlogEvidencePack,
        section: dict[str, Any],
        images: list[dict[str, Any]],
        *,
        target_chars: int,
    ) -> dict[str, Any]:
        fact_ids: list[int] = []
        seen_fact_ids: set[int] = set()
        for raw_fact_id in section.get("fact_ids", []):
            try:
                fact_id = int(raw_fact_id)
            except (TypeError, ValueError):
                continue
            if fact_id not in seen_fact_ids:
                seen_fact_ids.add(fact_id)
                fact_ids.append(fact_id)
        fact_by_id = {int(fact["fact_id"]): fact for fact in pack.facts}
        image_ids = [str(image_id) for image_id in section.get("image_ids", [])]
        available_image_ids = {str(image["image_id"]) for image in images}
        image_by_id = {str(image["image_id"]): image for image in images}
        valid_image_ids = [image_id for image_id in image_ids if image_id in available_image_ids]
        section_text = f"{section.get('section_key', '')} {section.get('title', '')} {section.get('summary', '')}".lower()
        if any(term in section_text for term in ("method", "architecture", "核心", "架构", "方法")):
            equations = self._publishable_equations(pack.equations)[:MAX_EQUATIONS]
        elif "experiment" in section_text or "实验" in section_text:
            equations = self._publishable_equations(
                [
                    equation
                    for equation in pack.equations
                    if equation.get("role") in {"training_objective"}
                ]
            )[:2]
        else:
            equations = []
        payload = {
            "task": "section",
            "paper_key": pack.paper_key,
            "title": pack.title,
            "section": section,
            "response_schema": {
                "section_key": "same as section.section_key",
                "markdown": "Chinese markdown, at least target_chars Chinese characters",
                "fact_ids": "array containing every supplied fact id, with no other ids",
                "image_ids": "array of used image ids from supplied images",
            },
            "equations": [
                {key: value for key, value in equation.items() if key != "source_path"}
                for equation in equations
            ],
            "facts": self._prompt_facts(
                [
                    fact_by_id[fact_id]
                    for fact_id in fact_ids
                    if fact_id in fact_by_id
                ]
            ),
            "artifact_texts": self._bounded_artifact_texts(
                pack.artifact_texts,
                SECTION_SOURCE_CHAR_LIMIT,
            ),
            "images": self._prompt_images(
                [image_by_id[image_id] for image_id in valid_image_ids]
            ),
            "target_chars": target_chars,
        }
        result = self.transport.complete_json(
            model=self.model,
            base_url=self.base_url,
            api_key=self.api_key,
            messages=self._messages("section", payload),
            max_output_tokens=max(1200, min(SECTION_MAX_OUTPUT_TOKENS, target_chars * 3)),
        )
        markdown = str(result.get("markdown") or "").strip()
        if not markdown:
            content = str(result.get("content") or result.get("section") or "").strip()
            if content:
                markdown = f"## {section.get('title') or section.get('section_key')}\n\n{content}"
        if not markdown:
            raise BlogValidationError("section response missing markdown")
        raw_result_fact_ids = result.get("fact_ids", [])
        if not isinstance(raw_result_fact_ids, list):
            raise BlogValidationError("section response contains invalid fact_ids")
        try:
            returned_fact_ids = [int(fact_id) for fact_id in raw_result_fact_ids]
        except (TypeError, ValueError) as exc:
            raise BlogValidationError("section response contains invalid fact_ids") from exc
        if set(returned_fact_ids) != set(fact_ids):
            if fact_ids and "fact_ids" not in result:
                raise BlogValidationError("section response missing required fact_ids")
            raise BlogValidationError("section response fact_ids do not match supplied facts")
        result["fact_ids"] = returned_fact_ids
        markdown = self._append_equation_notes(markdown, equations)
        result["markdown"] = markdown + "\n"
        result.setdefault("image_ids", image_ids)
        return result


def _request_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def _cache_get(
    db_path: Path,
    *,
    paper_key: str,
    section_key: str,
    source_hash: str,
    prompt_version: str,
    model: str,
    request_hash: str,
) -> dict[str, Any] | None:
    ensure_blog_schema(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            select response_json, markdown from paper_blog_generation_cache
            where paper_key = ? and section_key = ? and source_hash = ?
              and prompt_version = ? and model = ? and request_hash = ?
            """,
            (paper_key, section_key, source_hash, prompt_version, model, request_hash),
        ).fetchone()
    if row is None:
        return None
    payload = parse_json(row["response_json"], {})
    if not isinstance(payload, dict):
        payload = {}
    if row["markdown"]:
        payload["markdown"] = row["markdown"]
    return payload


def _cache_put(
    db_path: Path,
    *,
    paper_key: str,
    section_key: str,
    source_hash: str,
    prompt_version: str,
    model: str,
    request_hash: str,
    response: dict[str, Any],
) -> None:
    ensure_blog_schema(db_path)
    now = utc_now()
    markdown = str(response.get("markdown") or "")
    response_json = stable_json(response)
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into paper_blog_generation_cache (
                paper_key, section_key, source_hash, prompt_version, model, request_hash,
                response_json, markdown, token_estimate, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(paper_key, section_key, source_hash, prompt_version, model, request_hash)
            do update set response_json = excluded.response_json,
                          markdown = excluded.markdown,
                          token_estimate = excluded.token_estimate,
                          updated_at = excluded.updated_at
            """,
            (
                paper_key,
                section_key,
                source_hash,
                prompt_version,
                model,
                request_hash,
                response_json,
                markdown,
                max(1, len(response_json) // 4),
                now,
                now,
            ),
        )
        conn.commit()


def _normalize_declared_asset_path(value: Any) -> str:
    asset_path = str(value or "").strip()
    return posixpath.normpath(asset_path) if asset_path else ""


def _markdown_unescape(value: str) -> str:
    unescaped: list[str] = []
    index = 0
    while index < len(value):
        if (
            value[index] == "\\"
            and index + 1 < len(value)
            and value[index + 1] in MARKDOWN_ESCAPABLE
        ):
            unescaped.append(value[index + 1])
            index += 2
            continue
        unescaped.append(value[index])
        index += 1
    return "".join(unescaped)


def _normalize_markdown_asset_path(value: str) -> str:
    decoded = urllib.parse.unquote(html.unescape(_markdown_unescape(value.strip())))
    return posixpath.normpath(decoded) if decoded else ""


def _is_local_normalized_path(asset_path: str) -> bool:
    if not asset_path or asset_path.startswith(("/", "\\", "//")):
        return False
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", asset_path):
        return False
    parts = [part for part in re.split(r"[/\\]+", asset_path) if part]
    return ".." not in parts and asset_path not in {"", "."}


def _is_local_asset_path(value: Any) -> bool:
    return _is_local_normalized_path(_normalize_declared_asset_path(value))


def _markdown_image_destination(value: Any) -> str:
    return urllib.parse.quote(_normalize_declared_asset_path(value), safe="/-._~")


def _markdown_container_parts(line: str) -> tuple[tuple[str, ...], int, int, str]:
    cursor = 0
    contexts: list[str] = []
    list_continuation_indent = 0
    while cursor < len(line):
        blockquote = re.match(r" {0,3}>[ \t]?", line[cursor:])
        if blockquote is not None:
            contexts.append("blockquote")
            cursor += blockquote.end()
            continue
        list_item = re.match(r" {0,3}(?:[-+*]|[0-9]{1,9}[.)])[ \t]+", line[cursor:])
        if list_item is not None:
            contexts.append("list")
            list_continuation_indent = list_item.end()
            cursor += list_item.end()
            continue
        break
    content = line[cursor:]
    indentation = len(content) - len(content.lstrip(" "))
    return tuple(contexts), indentation, list_continuation_indent, content


def _markdown_container_content(line: str) -> str:
    return _markdown_container_parts(line)[3]


def _mask_markdown_code(markdown: str) -> str:
    masked = list(markdown)
    fence_char = ""
    fence_length = 0
    fence_context: tuple[str, ...] = ()
    fence_list_indent = 0
    offset = 0

    def mask_range(start: int, end: int) -> None:
        for index in range(start, end):
            if masked[index] not in {"\r", "\n"}:
                masked[index] = " "

    for line in markdown.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        body_end = offset + len(body)
        (
            container_context,
            container_indentation,
            container_list_indent,
            container_content,
        ) = _markdown_container_parts(body)
        process_as_outside = not fence_char
        if fence_char:
            same_context = container_context == fence_context
            list_continuation = (
                bool(fence_context)
                and fence_context[-1] == "list"
                and container_context == fence_context[:-1]
                and fence_list_indent <= container_indentation <= fence_list_indent + 3
            )
            if fence_context and not (same_context or list_continuation):
                fence_char = ""
                fence_length = 0
                fence_context = ()
                fence_list_indent = 0
                process_as_outside = True
            else:
                mask_range(offset, body_end)
                closing_content = (
                    container_content[fence_list_indent:]
                    if list_continuation
                    else container_content
                )
                closing = re.match(r" {0,3}([`~]+)[ \t]*$", closing_content)
                if (
                    closing is not None
                    and closing.group(1)[0] == fence_char
                    and len(closing.group(1)) >= fence_length
                    and (same_context or list_continuation)
                ):
                    fence_char = ""
                    fence_length = 0
                    fence_context = ()
                    fence_list_indent = 0
        if process_as_outside:
            opening = re.match(r" {0,3}(`{3,}|~{3,})", container_content)
            if opening is not None:
                fence = opening.group(1)
                fence_char = fence[0]
                fence_length = len(fence)
                fence_context = container_context
                fence_list_indent = container_list_indent
                mask_range(offset, body_end)
        offset += len(line)

    fenced_masked = "".join(masked)

    def is_escaped(index: int) -> bool:
        slash_count = 0
        cursor = index - 1
        while cursor >= 0 and fenced_masked[cursor] == "\\":
            slash_count += 1
            cursor -= 1
        return slash_count % 2 == 1

    index = 0
    while index < len(fenced_masked):
        if fenced_masked[index] != "`" or is_escaped(index):
            index += 1
            continue
        opening_end = index + 1
        while opening_end < len(fenced_masked) and fenced_masked[opening_end] == "`":
            opening_end += 1
        run_length = opening_end - index
        cursor = opening_end
        closing_end = -1
        while cursor < len(fenced_masked):
            closing_start = fenced_masked.find("`", cursor)
            if closing_start < 0:
                break
            candidate_end = closing_start + 1
            while candidate_end < len(fenced_masked) and fenced_masked[candidate_end] == "`":
                candidate_end += 1
            if candidate_end - closing_start == run_length:
                closing_end = candidate_end
                break
            cursor = candidate_end
        if closing_end < 0:
            index = opening_end
            continue
        mask_range(index, closing_end)
        index = closing_end
    return "".join(masked)


def _is_markdown_escaped(value: str, index: int) -> bool:
    slash_count = 0
    cursor = index - 1
    while cursor >= 0 and value[cursor] == "\\":
        slash_count += 1
        cursor -= 1
    return slash_count % 2 == 1


def _markdown_label_end(value: str, opening_index: int) -> int | None:
    depth = 1
    index = opening_index + 1
    while index < len(value):
        if (
            value[index] == "\\"
            and index + 1 < len(value)
            and value[index + 1] in MARKDOWN_ESCAPABLE
        ):
            index += 2
            continue
        if value[index] == "[":
            depth += 1
        elif value[index] == "]":
            depth -= 1
            if depth == 0:
                return index
        elif value[index] in "\r\n":
            return None
        index += 1
    return None


def _markdown_title_end(value: str, opening_index: int, closing_char: str) -> int | None:
    index = opening_index + 1
    while index < len(value):
        if (
            value[index] == "\\"
            and index + 1 < len(value)
            and value[index + 1] in MARKDOWN_ESCAPABLE
        ):
            index += 2
            continue
        if value[index] == closing_char:
            return index
        index += 1
    return None


def _parse_markdown_image_destination(
    value: str,
    opening_parenthesis: int,
) -> tuple[int, int, int, str] | None:
    cursor = opening_parenthesis + 1
    while cursor < len(value) and value[cursor] in " \t\r\n":
        cursor += 1
    if cursor >= len(value):
        return None

    if value[cursor] == "<":
        destination_start = cursor
        raw_start = cursor + 1
        cursor = raw_start
        while cursor < len(value):
            if (
                value[cursor] == "\\"
                and cursor + 1 < len(value)
                and value[cursor + 1] in MARKDOWN_ESCAPABLE
            ):
                cursor += 2
                continue
            if value[cursor] == ">":
                raw_destination = value[raw_start:cursor]
                destination_end = cursor + 1
                cursor += 1
                break
            if value[cursor] in "\r\n<":
                return None
            cursor += 1
        else:
            return None
    else:
        destination_start = cursor
        depth = 0
        while cursor < len(value):
            char = value[cursor]
            if (
                char == "\\"
                and cursor + 1 < len(value)
                and value[cursor + 1] in MARKDOWN_ESCAPABLE
            ):
                cursor += 2
                continue
            if char == "(":
                depth += 1
                if depth > MAX_MARKDOWN_DESTINATION_NESTING:
                    return None
            elif char == ")":
                if depth == 0:
                    raw_destination = value[destination_start:cursor]
                    return destination_start, cursor, cursor + 1, raw_destination
                depth -= 1
            elif char in " \t\r\n":
                if depth == 0:
                    raw_destination = value[destination_start:cursor]
                    break
            elif char in "\r\n":
                return None
            cursor += 1
        else:
            return None
        destination_end = cursor

    title_separator_start = cursor
    while cursor < len(value) and value[cursor] in " \t\r\n":
        cursor += 1
    if cursor < len(value) and value[cursor] == ")":
        return destination_start, destination_end, cursor + 1, raw_destination
    if (
        cursor == title_separator_start
        or cursor >= len(value)
        or value[cursor] not in {'"', "'", "("}
    ):
        return None
    title_closing = ")" if value[cursor] == "(" else value[cursor]
    title_end = _markdown_title_end(value, cursor, title_closing)
    if title_end is None:
        return None
    cursor = title_end + 1
    while cursor < len(value) and value[cursor] in " \t\r\n":
        cursor += 1
    if cursor >= len(value) or value[cursor] != ")":
        return None
    return destination_start, destination_end, cursor + 1, raw_destination


def _markdown_image_matches(markdown: str) -> list[MarkdownImageMatch]:
    masked = _mask_markdown_code(markdown)
    matches: list[MarkdownImageMatch] = []
    cursor = 0
    while cursor < len(masked) - 1:
        image_start = masked.find("![", cursor)
        if image_start < 0:
            break
        if _is_markdown_escaped(masked, image_start):
            cursor = image_start + 2
            continue
        label_end = _markdown_label_end(masked, image_start + 1)
        if label_end is None or label_end + 1 >= len(masked) or masked[label_end + 1] != "(":
            cursor = image_start + 2
            continue
        parsed = _parse_markdown_image_destination(masked, label_end + 1)
        if parsed is None:
            cursor = image_start + 2
            continue
        destination_start, destination_end, image_end, raw_destination = parsed
        matches.append(
            MarkdownImageMatch(
                start=image_start,
                end=image_end,
                destination_start=destination_start,
                destination_end=destination_end,
                path=_normalize_markdown_asset_path(raw_destination),
            )
        )
        cursor = image_end
    return matches


def _markdown_image_path(match: MarkdownImageMatch) -> str:
    return match.path


def _embedded_image_paths(markdown: str) -> list[str]:
    return [_markdown_image_path(match) for match in _markdown_image_matches(markdown)]


def _markdown_math_delimiters_valid(markdown: str) -> bool:
    visible = _mask_markdown_code(markdown)
    math_chunks: list[str] = []
    patterns = (
        re.compile(r"\$\$(.*?)\$\$", re.S),
        re.compile(r"\\\[(.*?)\\\]", re.S),
        re.compile(r"\\\((.*?)\\\)", re.S),
        re.compile(r"(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)", re.S),
    )
    for pattern in patterns:
        math_chunks.extend(match.group(1) for match in pattern.finditer(visible))
    return all(_sized_delimiters_valid(chunk) for chunk in math_chunks)


def _replace_image_destination(
    markdown: str,
    match: MarkdownImageMatch,
    destination: str,
) -> str:
    return (
        markdown[match.start : match.destination_start]
        + destination
        + markdown[match.destination_end : match.end]
    )


def _rewrite_markdown_image_destinations(
    markdown: str,
    path_replacements: dict[str, str],
    *,
    removed_paths: set[str] | None = None,
) -> str:
    removed_paths = removed_paths or set()
    parts: list[str] = []
    cursor = 0
    for match in _markdown_image_matches(markdown):
        parts.append(markdown[cursor : match.start])
        replacement = path_replacements.get(_markdown_image_path(match))
        if replacement is not None:
            parts.append(
                _replace_image_destination(
                    markdown,
                    match,
                    _markdown_image_destination(replacement),
                )
            )
        elif _markdown_image_path(match) not in removed_paths:
            parts.append(markdown[match.start : match.end])
        cursor = match.end
    parts.append(markdown[cursor:])
    return "".join(parts)


def _clean_markdown_label(value: Any, *, fallback: str) -> str:
    label = html.unescape(str(value or ""))
    label = re.sub(r"[\x00-\x1f\x7f]+", " ", label)
    label = re.sub(r"\s+", " ", label).strip() or fallback
    label = label[:240]
    return label.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _ensure_section_h2(markdown: Any, title: Any) -> str:
    text = str(markdown or "").strip()
    if SECTION_H2_RE.match(text):
        return text
    heading = _clean_markdown_label(title, fallback="章节")
    return f"## {heading}\n\n{text}".rstrip()


def _escape_model_control_tokens(markdown: str) -> str:
    visible_markdown = _mask_markdown_code(markdown)
    parts: list[str] = []
    cursor = 0
    for match in MODEL_CONTROL_TOKEN_RE.finditer(visible_markdown):
        if _is_markdown_escaped(visible_markdown, match.start()):
            continue
        parts.append(markdown[cursor : match.start()])
        closing = "/" if match.group("closing") else ""
        parts.append(f"&lt;{closing}{match.group('name')}&gt;")
        cursor = match.end()
    parts.append(markdown[cursor:])
    return "".join(parts)


def _assemble_section_response(
    response: dict[str, Any],
    section: dict[str, Any],
    *,
    image_by_id: dict[str, dict[str, Any]],
    image_by_path: dict[str, dict[str, Any]],
    used_asset_paths: set[str],
) -> dict[str, Any]:
    markdown = _escape_model_control_tokens(
        _ensure_section_h2(response.get("markdown"), section.get("title"))
    )
    normalized_image_by_path: dict[str, dict[str, Any]] = {}
    for asset_path, image in image_by_path.items():
        normalized_image_by_path.setdefault(_normalize_declared_asset_path(asset_path), image)
    image_by_path = normalized_image_by_path
    embedded_image_ids: list[str] = []
    markdown_parts: list[str] = []
    cursor = 0
    for match in _markdown_image_matches(markdown):
        markdown_parts.append(markdown[cursor : match.start])
        asset_path = _markdown_image_path(match)
        image = image_by_path.get(asset_path)
        if image is None:
            markdown_parts.append(markdown[match.start : match.end])
        elif asset_path not in used_asset_paths:
            used_asset_paths.add(asset_path)
            image_id = str(image["image_id"])
            if image_id not in embedded_image_ids:
                embedded_image_ids.append(image_id)
            markdown_parts.append(
                _replace_image_destination(
                    markdown,
                    match,
                    _markdown_image_destination(asset_path),
                )
            )
        cursor = match.end
    markdown_parts.append(markdown[cursor:])
    markdown = "".join(markdown_parts).strip()
    response_image_ids = response.get("image_ids", [])
    requested_image_ids = response_image_ids if response_image_ids else section.get("image_ids", [])
    if not isinstance(requested_image_ids, list):
        requested_image_ids = []

    appended_images: list[str] = []
    for raw_image_id in requested_image_ids:
        image = image_by_id.get(str(raw_image_id))
        if image is None:
            continue
        asset_path = _normalize_declared_asset_path(image.get("asset_path"))
        if not _is_local_asset_path(asset_path) or asset_path in used_asset_paths:
            continue
        used_asset_paths.add(asset_path)
        image_id = str(image["image_id"])
        if image_id not in embedded_image_ids:
            embedded_image_ids.append(image_id)
        caption = _clean_markdown_label(image.get("caption"), fallback="论文图示")
        appended_images.append(f"![{caption}]({_markdown_image_destination(asset_path)})")

    if appended_images:
        markdown = markdown.rstrip() + "\n\n" + "\n\n".join(appended_images)
    response["markdown"] = markdown.strip() + "\n"
    response["image_ids"] = embedded_image_ids
    return response


def _final_outline_with_provenance(
    outline: dict[str, Any],
    section_responses: list[dict[str, Any]],
    *,
    facts: list[dict[str, Any]],
    images: list[dict[str, Any]],
) -> dict[str, Any]:
    response_by_key = {
        str(response.get("section_key") or ""): response
        for response in section_responses
        if isinstance(response, dict)
    }
    valid_fact_ids = {int(fact["fact_id"]) for fact in facts}
    valid_image_ids = {str(image["image_id"]) for image in images}
    final_sections: list[Any] = []

    for raw_section in outline.get("sections", []):
        if not isinstance(raw_section, dict):
            final_sections.append(raw_section)
            continue
        section = dict(raw_section)
        response = response_by_key.get(str(section.get("section_key") or ""))
        if response is not None:
            fact_ids: list[int] = []
            seen_fact_ids: set[int] = set()
            for raw_fact_id in response.get("fact_ids", []):
                try:
                    fact_id = int(raw_fact_id)
                except (TypeError, ValueError):
                    continue
                if fact_id in valid_fact_ids and fact_id not in seen_fact_ids:
                    seen_fact_ids.add(fact_id)
                    fact_ids.append(fact_id)

            image_ids: list[str] = []
            seen_image_ids: set[str] = set()
            for raw_image_id in response.get("image_ids", []):
                image_id = str(raw_image_id)
                if image_id in valid_image_ids and image_id not in seen_image_ids:
                    seen_image_ids.add(image_id)
                    image_ids.append(image_id)

            section["fact_ids"] = fact_ids
            section["image_ids"] = image_ids
        final_sections.append(section)

    final_outline = dict(outline)
    final_outline["sections"] = final_sections
    return final_outline


def _outline_with_minimum_fact_coverage(
    outline: dict[str, Any],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    valid_facts: list[tuple[int, str]] = []
    seen_valid_ids: set[int] = set()
    for fact in facts:
        try:
            fact_id = int(fact["fact_id"])
        except (KeyError, TypeError, ValueError):
            continue
        if fact_id in seen_valid_ids:
            continue
        seen_valid_ids.add(fact_id)
        valid_facts.append((fact_id, str(fact.get("fact_type") or "").lower()))
    required_count = int(len(valid_facts) * MIN_OUTLINE_FACT_COVERAGE + 0.999999)
    if required_count <= 0:
        return outline

    raw_sections = outline.get("sections")
    if not isinstance(raw_sections, list):
        return outline
    sections = [dict(section) if isinstance(section, dict) else section for section in raw_sections]
    sections_by_key = {
        str(section.get("section_key") or ""): section
        for section in sections
        if isinstance(section, dict)
    }
    fallback_keys = [key for key, _title in DEFAULT_SECTIONS if key in sections_by_key]
    per_section_limit = max(
        DEFAULT_OUTLINE_FACTS_PER_SECTION,
        (required_count + max(1, len(fallback_keys)) - 1) // max(1, len(fallback_keys)),
    )
    referenced_ids: set[int] = set()
    for section in sections_by_key.values():
        raw_fact_ids = section.get("fact_ids", [])
        if not isinstance(raw_fact_ids, list):
            continue
        normalized_fact_ids: list[Any] = []
        for raw_fact_id in raw_fact_ids:
            try:
                fact_id = int(raw_fact_id)
            except (TypeError, ValueError):
                if len(normalized_fact_ids) < per_section_limit:
                    normalized_fact_ids.append(raw_fact_id)
                continue
            if fact_id in seen_valid_ids:
                if (
                    fact_id in referenced_ids
                    or len(normalized_fact_ids) >= per_section_limit
                ):
                    continue
                referenced_ids.add(fact_id)
                normalized_fact_ids.append(fact_id)
            elif len(normalized_fact_ids) < per_section_limit:
                normalized_fact_ids.append(raw_fact_id)
        section["fact_ids"] = normalized_fact_ids
    if len(referenced_ids) >= required_count:
        enriched = dict(outline)
        enriched["sections"] = sections
        return enriched

    preferences = {
        "method": ("method", "architecture", "engineering"),
        "benchmark": ("experiments", "engineering", "further_reading"),
        "dataset": ("experiments", "background", "engineering"),
        "limitation": ("limitations", "engineering"),
        "claim": ("intro", "background", "engineering"),
    }
    for fact_id, fact_type in valid_facts:
        if fact_id in referenced_ids:
            continue
        preferred_keys = [
            key for key in preferences.get(fact_type, ()) if key in sections_by_key
        ]
        preferred_with_capacity = [
            key
            for key in preferred_keys
            if len(sections_by_key[key].get("fact_ids", [])) < per_section_limit
        ]
        fallback_with_capacity = [
            key
            for key in fallback_keys
            if len(sections_by_key[key].get("fact_ids", [])) < per_section_limit
        ]
        candidate_keys = preferred_with_capacity or fallback_with_capacity
        if not candidate_keys:
            break
        target_key = min(
            candidate_keys,
            key=lambda key: (
                len(sections_by_key[key].get("fact_ids", [])),
                candidate_keys.index(key),
            ),
        )
        target_ids = sections_by_key[target_key].get("fact_ids", [])
        if not isinstance(target_ids, list):
            target_ids = []
        else:
            target_ids = list(target_ids)
        target_ids.append(fact_id)
        sections_by_key[target_key]["fact_ids"] = target_ids
        referenced_ids.add(fact_id)
        if len(referenced_ids) >= required_count:
            break

    enriched = dict(outline)
    enriched["sections"] = sections
    return enriched


def validate_blog(
    *,
    markdown: str,
    outline: dict[str, Any],
    image_refs: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    section_responses: list[dict[str, Any]] | None = None,
    min_chars: int = MIN_BLOG_CHARS,
    enforce_rendered_content: bool = True,
) -> None:
    if "\ufffd" in markdown:
        raise BlogValidationError("generated blog contains replacement character")
    if not _markdown_math_delimiters_valid(markdown):
        raise BlogValidationError("generated blog contains invalid LaTeX delimiter")
    word_count = chinese_char_count(markdown)
    if word_count < min_chars:
        raise BlogValidationError(f"word count below minimum: {word_count} < {min_chars}")

    sections = outline.get("sections")
    if not isinstance(sections, list):
        raise BlogValidationError("outline sections must be a list")
    section_keys = {str(section.get("section_key") or "") for section in sections if isinstance(section, dict)}
    required = {key for key, _title in DEFAULT_SECTIONS}
    if not required.issubset(section_keys):
        raise BlogValidationError(f"missing required sections: {sorted(required - section_keys)}")

    fact_ids = {int(fact["fact_id"]) for fact in facts}
    for section in sections:
        if not isinstance(section, dict):
            raise BlogValidationError("outline section must be an object")
        section_fact_ids = section.get("fact_ids", [])
        if not isinstance(section_fact_ids, list):
            raise BlogValidationError("outline fact_ids must be a list")
        for fact_id in section_fact_ids:
            try:
                normalized_fact_id = int(fact_id)
            except (TypeError, ValueError) as exc:
                raise BlogValidationError(f"invalid fact reference: {fact_id}") from exc
            if normalized_fact_id not in fact_ids:
                raise BlogValidationError(f"invalid fact reference: {fact_id}")

    image_by_id: dict[str, dict[str, Any]] = {}
    image_by_path: dict[str, dict[str, Any]] = {}
    for image in image_refs:
        image_id = str(image["image_id"])
        raw_asset_path = image.get("asset_path")
        if not _is_local_asset_path(raw_asset_path):
            raise BlogValidationError(f"external image path not allowed: {image_id}")
        asset_path = _normalize_declared_asset_path(raw_asset_path)
        image_by_id[image_id] = image
        image_by_path.setdefault(asset_path, image)
    for section in sections:
        section_image_ids = section.get("image_ids", [])
        if not isinstance(section_image_ids, list):
            raise BlogValidationError("outline image_ids must be a list")
        for image_id in section_image_ids:
            image = image_by_id.get(str(image_id))
            if image is None:
                raise BlogValidationError(f"invalid image reference: {image_id}")
            if not _is_local_asset_path(image.get("asset_path")):
                raise BlogValidationError(f"external image path not allowed: {image_id}")

    def validate_embedded_paths(value: str) -> list[str]:
        embedded_paths = _embedded_image_paths(value)
        for asset_path in embedded_paths:
            if not _is_local_normalized_path(asset_path):
                raise BlogValidationError(f"external image path not allowed: {asset_path}")
            if asset_path not in image_by_path:
                raise BlogValidationError(f"undeclared image path: {asset_path}")
        return embedded_paths

    final_embedded_paths = validate_embedded_paths(markdown)
    if enforce_rendered_content and image_refs and not final_embedded_paths:
        raise BlogValidationError("generated blog missing declared local image")

    response_keys: set[str] = set()
    for response in section_responses or []:
        if not isinstance(response, dict):
            raise BlogValidationError("section response must be an object")
        section_key = str(response.get("section_key") or "")
        if section_key not in section_keys:
            raise BlogValidationError(f"invalid section response key: {section_key}")
        if section_key in response_keys:
            raise BlogValidationError(f"duplicate section response key: {section_key}")
        response_keys.add(section_key)
        response_markdown = str(response.get("markdown") or "").strip()
        if "\ufffd" in response_markdown:
            raise BlogValidationError(
                f"section response contains replacement character: {section_key}"
            )
        if not response_markdown:
            raise BlogValidationError(f"section response missing markdown: {section_key}")
        if enforce_rendered_content and not SECTION_H2_RE.match(response_markdown):
            raise BlogValidationError(f"section response must begin with H2: {section_key}")
        response_embedded_paths = validate_embedded_paths(response_markdown)
        response_fact_ids = response.get("fact_ids", [])
        if not isinstance(response_fact_ids, list):
            raise BlogValidationError("section fact_ids must be a list")
        for fact_id in response_fact_ids:
            try:
                normalized_fact_id = int(fact_id)
            except (TypeError, ValueError) as exc:
                raise BlogValidationError(f"invalid section fact reference: {fact_id}") from exc
            if normalized_fact_id not in fact_ids:
                raise BlogValidationError(f"invalid section fact reference: {fact_id}")
        response_image_ids = response.get("image_ids", [])
        if not isinstance(response_image_ids, list):
            raise BlogValidationError("section image_ids must be a list")
        normalized_response_image_ids = [str(image_id) for image_id in response_image_ids]
        for image_id in normalized_response_image_ids:
            if image_id not in image_by_id:
                raise BlogValidationError(f"invalid section image reference: {image_id}")
        embedded_image_ids: list[str] = []
        for asset_path in response_embedded_paths:
            image_id = str(image_by_path[asset_path]["image_id"])
            if image_id not in embedded_image_ids:
                embedded_image_ids.append(image_id)
        if enforce_rendered_content and normalized_response_image_ids != embedded_image_ids:
            raise BlogValidationError(
                f"section image_ids do not match embedded images: {section_key}"
            )


def _validated_outline(
    outline: dict[str, Any],
    *,
    images: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    def contains_replacement_character(value: Any) -> bool:
        if isinstance(value, str):
            return "\ufffd" in value
        if isinstance(value, dict):
            return any(
                contains_replacement_character(key) or contains_replacement_character(item)
                for key, item in value.items()
            )
        if isinstance(value, (list, tuple)):
            return any(contains_replacement_character(item) for item in value)
        return False

    if contains_replacement_character(outline):
        raise BlogValidationError("outline response contains replacement character")
    if not isinstance(outline, dict) or not str(outline.get("title") or "").strip():
        raise BlogValidationError("outline response missing title")
    raw_sections = outline.get("sections")
    if not isinstance(raw_sections, list):
        raise BlogValidationError("outline sections must be a list")
    sections = raw_sections[:MAX_SECTIONS]
    normalized = dict(outline)
    normalized["sections"] = sections
    validate_blog(
        markdown="中" * MIN_BLOG_CHARS,
        outline=normalized,
        image_refs=images,
        facts=facts,
        min_chars=MIN_BLOG_CHARS,
        enforce_rendered_content=False,
    )
    return normalized


def _validated_section_response(
    response: dict[str, Any],
    *,
    section: dict[str, Any],
    images: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    min_chars: int = MIN_SECTION_CHARS,
) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise BlogValidationError("section response must be an object")
    normalized = dict(response)
    normalized.setdefault("section_key", str(section.get("section_key") or ""))
    validation_sections = [
        section if key == normalized["section_key"] else {"section_key": key, "fact_ids": [], "image_ids": []}
        for key, _title in DEFAULT_SECTIONS
    ]
    validate_blog(
        markdown="中" * MIN_BLOG_CHARS,
        outline={"sections": validation_sections},
        image_refs=images,
        facts=facts,
        section_responses=[normalized],
        min_chars=MIN_BLOG_CHARS,
        enforce_rendered_content=False,
    )
    section_chars = chinese_char_count(str(normalized.get("markdown") or ""))
    if section_chars < min_chars:
        raise BlogValidationError(f"section below target length: {section_chars} < {min_chars}")
    return normalized


def _generate_validated_section_with_retries(
    provider: BlogProvider,
    pack: BlogEvidencePack,
    section: dict[str, Any],
    images: list[dict[str, Any]],
    *,
    target_chars: int,
    min_chars: int | None = None,
) -> tuple[dict[str, Any], int]:
    last_error: Exception | None = None
    calls = 0
    required_chars = min_chars if min_chars is not None else max(MIN_SECTION_CHARS, int(target_chars * 0.7))
    for _attempt in range(SECTION_PROVIDER_RETRIES + 1):
        try:
            calls += 1
            response = provider.generate_section(pack, section, images, target_chars=target_chars)
            return (
                _validated_section_response(
                    response,
                    section=section,
                    images=images,
                    facts=pack.facts,
                    min_chars=required_chars,
                ),
                calls,
            )
        except Exception as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def _generate_validated_outline_with_retries(
    provider: BlogProvider,
    pack: BlogEvidencePack,
    images: list[dict[str, Any]],
    *,
    target_chars: int,
) -> tuple[dict[str, Any], int]:
    last_error: Exception | None = None
    calls = 0
    for _attempt in range(SECTION_PROVIDER_RETRIES + 1):
        try:
            calls += 1
            outline = provider.generate_outline(pack, images, target_chars=target_chars)
            return _validated_outline(outline, images=images, facts=pack.facts), calls
        except Exception as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def generate_and_publish_blog(
    db_path: Path,
    paper_key: str,
    *,
    provider: BlogProvider,
    model: str,
    target_chars: int = DEFAULT_TARGET_CHARS,
    force: bool = False,
    prompt_version: str = BLOG_PROMPT_VERSION,
) -> PublishedBlogVersion:
    target_chars = max(MIN_BLOG_CHARS, min(MAX_BLOG_CHARS, int(target_chars)))
    pack = build_blog_evidence_pack(db_path, paper_key)
    if not any(pack.artifact_texts.get(kind, "").strip() for kind in ("summary", "tldr")):
        raise BlogValidationError("missing required summary/tldr grounding artifact")
    if not pack.facts and len(" ".join(pack.artifact_texts.values())) < 2000:
        raise BlogValidationError("missing facts and source text is too short")

    images = _select_blog_images_from_candidates(pack.image_candidates, max_images=MAX_IMAGES)
    cache_hits = 0
    llm_calls = 0

    outline_request = {
        "type": "outline",
        "source_hash": pack.source_hash,
        "target_chars": target_chars,
        "source_char_limit": OUTLINE_SOURCE_CHAR_LIMIT,
        "max_output_tokens": OUTLINE_MAX_OUTPUT_TOKENS,
        "images": images,
    }
    outline_hash = _request_hash(outline_request)
    outline = (
        None
        if force
        else _cache_get(
            db_path,
            paper_key=paper_key,
            section_key="outline",
            source_hash=pack.source_hash,
            prompt_version=prompt_version,
            model=model,
            request_hash=outline_hash,
        )
    )
    if outline is None:
        outline, calls = _generate_validated_outline_with_retries(
            provider,
            pack,
            images,
            target_chars=target_chars,
        )
        llm_calls += calls
        _cache_put(
            db_path,
            paper_key=pack.paper_key,
            section_key="outline",
            source_hash=pack.source_hash,
            prompt_version=prompt_version,
            model=model,
            request_hash=outline_hash,
            response=outline,
        )
    else:
        try:
            outline = _validated_outline(outline, images=images, facts=pack.facts)
        except (BlogValidationError, TypeError, ValueError):
            outline, calls = _generate_validated_outline_with_retries(
                provider,
                pack,
                images,
                target_chars=target_chars,
            )
            llm_calls += calls
            _cache_put(
                db_path,
                paper_key=pack.paper_key,
                section_key="outline",
                source_hash=pack.source_hash,
                prompt_version=prompt_version,
                model=model,
                request_hash=outline_hash,
                response=outline,
            )
        else:
            cache_hits += 1

    outline = _outline_with_minimum_fact_coverage(outline, pack.facts)
    sections = outline.get("sections") if isinstance(outline.get("sections"), list) else []
    image_by_id = {str(image["image_id"]): image for image in images}
    image_by_path: dict[str, dict[str, Any]] = {}
    for image in images:
        image_by_path.setdefault(_normalize_declared_asset_path(image["asset_path"]), image)
    used_asset_paths: set[str] = set()
    section_responses: list[dict[str, Any]] = []
    response_sections: list[dict[str, Any]] = []
    section_request_hashes: dict[str, str] = {}
    baseline_section_target = target_chars // max(1, min(len(sections), MAX_SECTIONS))
    for section in sections[:MAX_SECTIONS]:
        if not isinstance(section, dict):
            continue
        section_key = str(section.get("section_key") or "")
        raw_section_target = int(section.get("target_chars") or target_chars // max(1, len(sections)))
        section_target_chars = max(
            MIN_SECTION_CHARS,
            min(MAX_SECTION_CHARS, max(raw_section_target, baseline_section_target)),
        )
        section_min_chars = max(MIN_SECTION_CHARS, int(section_target_chars * 0.7))
        provider_section_target = min(
            MAX_SECTION_CHARS,
            max(section_target_chars, int(section_target_chars * 1.6)),
        )
        section_request = {
            "type": "section",
            "section": section,
            "source_hash": pack.source_hash,
            "target_chars": provider_section_target,
            "min_chars": section_min_chars,
            "source_char_limit": SECTION_SOURCE_CHAR_LIMIT,
            "max_output_tokens": max(1200, min(SECTION_MAX_OUTPUT_TOKENS, provider_section_target * 3)),
        }
        section_hash = _request_hash(section_request)
        section_request_hashes[section_key] = section_hash
        should_cache_response = False
        response = (
            None
            if force
            else _cache_get(
                db_path,
                paper_key=paper_key,
                section_key=section_key,
                source_hash=pack.source_hash,
                prompt_version=prompt_version,
                model=model,
                request_hash=section_hash,
            )
        )
        if response is None:
            response, calls = _generate_validated_section_with_retries(
                provider,
                pack,
                section,
                images,
                target_chars=provider_section_target,
                min_chars=section_min_chars,
            )
            llm_calls += calls
            should_cache_response = True
        else:
            try:
                response = _validated_section_response(
                    response,
                    section=section,
                    images=images,
                    facts=pack.facts,
                )
            except (BlogValidationError, TypeError, ValueError):
                response, calls = _generate_validated_section_with_retries(
                    provider,
                    pack,
                    section,
                    images,
                    target_chars=section_target_chars,
                )
                llm_calls += calls
                should_cache_response = True
            else:
                cache_hits += 1
        response = _assemble_section_response(
            response,
            section,
            image_by_id=image_by_id,
            image_by_path=image_by_path,
            used_asset_paths=used_asset_paths,
        )
        if should_cache_response:
            _cache_put(
                db_path,
                paper_key=pack.paper_key,
                section_key=section_key,
                source_hash=pack.source_hash,
                prompt_version=prompt_version,
                model=model,
                request_hash=section_hash,
                response=response,
            )
        section_responses.append(response)
        response_sections.append(section)

    if images and not used_asset_paths:
        intro_index = next(
            (
                index
                for index, response in enumerate(section_responses)
                if str(response.get("section_key") or "") == "intro"
            ),
            None,
        )
        if intro_index is not None:
            first_image_id = str(images[0]["image_id"])
            section_responses[intro_index]["image_ids"] = [first_image_id]
            _assemble_section_response(
                section_responses[intro_index],
                response_sections[intro_index],
                image_by_id=image_by_id,
                image_by_path=image_by_path,
                used_asset_paths=used_asset_paths,
            )
            _cache_put(
                db_path,
                paper_key=pack.paper_key,
                section_key="intro",
                source_hash=pack.source_hash,
                prompt_version=prompt_version,
                model=model,
                request_hash=section_request_hashes["intro"],
                response=section_responses[intro_index],
            )

    final_outline = _final_outline_with_provenance(
        outline,
        section_responses,
        facts=pack.facts,
        images=images,
    )
    markdown_parts = [f"# {outline.get('title') or pack.title + ' 深度解读'}\n"]
    markdown_parts.extend(
        str(response.get("markdown") or "").strip() + "\n" for response in section_responses
    )
    markdown = _escape_model_control_tokens("\n".join(markdown_parts).strip()) + "\n"
    validate_blog(
        markdown=markdown,
        outline=final_outline,
        image_refs=images,
        facts=pack.facts,
        section_responses=section_responses,
    )
    publishable_equation_count = len(_publishable_blog_equations(pack.equations))
    required_equation_blocks = min(2, publishable_equation_count)
    if display_math_block_count(markdown) < required_equation_blocks:
        raise BlogValidationError("generated blog missing required equation blocks")
    html_text = render_markdown_fallback(markdown)
    return publish_blog_version(
        db_path,
        paper_key=paper_key,
        title=str(final_outline.get("title") or f"{pack.title} 深度解读"),
        slug=slugify(paper_key),
        markdown=markdown,
        html=html_text,
        outline=final_outline,
        image_refs=images,
        generation_meta={
            "cache_hits": cache_hits,
            "llm_calls": llm_calls,
            "target_chars": target_chars,
            "section_count": len(section_responses),
        },
        model=model,
        prompt_version=prompt_version,
        source_hash=pack.source_hash,
    )


def export_paper_blogs(db_path: Path, out_path: Path) -> dict[str, Any]:
    ensure_blog_schema(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            select paper_key, title, slug, status, word_count, markdown, html,
                   outline_json, image_refs_json, model, prompt_version,
                   source_hash, updated_at
            from paper_blog_posts
            where status = 'published'
            order by updated_at desc, paper_key
            """
        ).fetchall()

    blogs = []
    for row in rows:
        exported_images: list[dict[str, Any]] = []
        exported_path_by_original: dict[str, str] = {}
        unavailable_asset_paths: set[str] = set()
        image_refs = parse_json(row["image_refs_json"], [])
        raw_images = [image for image in image_refs if isinstance(image, dict)] if isinstance(image_refs, list) else []
        publishable_images = _suppress_fragmented_visual_candidates(raw_images)
        publishable_ids = {id(image) for image in publishable_images}
        for image in raw_images:
            if id(image) in publishable_ids:
                continue
            suppressed_path = _normalize_declared_asset_path(image.get("asset_path"))
            if suppressed_path:
                unavailable_asset_paths.add(suppressed_path)
        for image in publishable_images:
            if not isinstance(image, dict):
                continue
            original_asset_path = _normalize_declared_asset_path(image.get("asset_path"))
            source_path = Path(str(image.get("source_path") or ""))
            if (
                not source_path.exists()
                or not source_path.is_file()
                or source_path.suffix.lower() not in IMAGE_SUFFIXES
            ):
                if original_asset_path:
                    unavailable_asset_paths.add(original_asset_path)
                continue
            digest = hashlib.sha256(source_path.read_bytes()).hexdigest()[:12]
            target_name = f"{source_path.stem}-{digest}{source_path.suffix.lower()}"
            target_path = out_path.parent / "paper-assets" / "blogs" / slugify(str(row["paper_key"])) / target_name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
            exported = dict(image)
            exported["asset_path"] = str(target_path.relative_to(out_path.parent))
            exported.pop("source_path", None)
            exported_images.append(exported)
            exported_path_by_original[original_asset_path] = str(exported["asset_path"])
        exported_markdown = _rewrite_markdown_image_destinations(
            str(row["markdown"] or ""),
            exported_path_by_original,
            removed_paths=unavailable_asset_paths,
        )
        blogs.append(
            {
                "paper_key": row["paper_key"],
                "title": row["title"],
                "slug": row["slug"],
                "status": row["status"],
                "word_count": int(row["word_count"] or 0),
                "markdown": exported_markdown,
                "html": row["html"],
                "outline": parse_json(row["outline_json"], {}),
                "image_refs": exported_images,
                "model": row["model"],
                "prompt_version": row["prompt_version"],
                "source_hash": row["source_hash"],
                "updated_at": row["updated_at"],
            }
        )

    payload = {"generated_at": utc_now(), "blog_count": len(blogs), "blogs": blogs}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload
