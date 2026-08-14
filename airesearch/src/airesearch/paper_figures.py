from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable


COMMAND_RE = re.compile(r"\\([A-Za-z]+\*?)")
FIGURE_BEGIN_RE = re.compile(r"\\begin\s*\{(figure\*?)\}(?:\s*\[[^\]]*\])?")
REFERENCE_COMMANDS = {"autoref", "cref", "Cref", "ref", "vref", "Vref"}
FORMATTING_COMMANDS = {
    "emph",
    "mathrm",
    "textrm",
    "textbf",
    "textit",
    "textnormal",
    "textsc",
    "textsf",
    "textsl",
    "texttt",
    "textup",
}
DISCARDED_COMMANDS = {
    "cite",
    "citealp",
    "citeauthor",
    "citep",
    "citet",
    "citeyear",
    "footnote",
    "label",
}
SOURCE_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".webp", ".eps", ".svg")


class FigureSourceError(RuntimeError):
    pass


@dataclass(frozen=True)
class FigureEvidence:
    evidence_id: str
    kind: str
    text: str


@dataclass(frozen=True)
class FigureRecord:
    figure_id: str
    number: int
    label: str
    layout: str
    includes: tuple[str, ...]
    caption: str
    section: str
    subsection: str
    role: str
    evidence: tuple[FigureEvidence, ...]


@dataclass(frozen=True)
class ResolvedFigure:
    record: FigureRecord
    path: Path
    source_reference: str
    extraction_method: str
    confidence: float
    content_sha256: str
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class _FigureEnvironment:
    start: int
    end: int
    name: str
    body: str


@dataclass(frozen=True)
class _Heading:
    offset: int
    level: str
    text: str


@dataclass(frozen=True)
class _Paragraph:
    start: int
    text: str


def _is_escaped(text: str, offset: int) -> bool:
    slash_count = 0
    cursor = offset - 1
    while cursor >= 0 and text[cursor] == "\\":
        slash_count += 1
        cursor -= 1
    return slash_count % 2 == 1


def _remove_latex_comments(text: str) -> str:
    cleaned_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        comment_at = next(
            (index for index, char in enumerate(line) if char == "%" and not _is_escaped(line, index)),
            None,
        )
        if comment_at is None:
            cleaned_lines.append(line)
            continue
        newline = "\n" if line.endswith("\n") else ""
        cleaned_lines.append(line[:comment_at] + newline)
    return "".join(cleaned_lines)


def _balanced_group(text: str, offset: int, opener: str, closer: str) -> tuple[str, int] | None:
    if offset >= len(text) or text[offset] != opener:
        return None
    depth = 0
    cursor = offset
    while cursor < len(text):
        char = text[cursor]
        if char == opener and not _is_escaped(text, cursor):
            depth += 1
        elif char == closer and not _is_escaped(text, cursor):
            depth -= 1
            if depth == 0:
                return text[offset + 1 : cursor], cursor + 1
        cursor += 1
    return None


def _command_argument_at(text: str, command_end: int) -> tuple[str, int] | None:
    cursor = command_end
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor < len(text) and text[cursor] == "[":
        optional = _balanced_group(text, cursor, "[", "]")
        if optional is None:
            return None
        cursor = optional[1]
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
    return _balanced_group(text, cursor, "{", "}")


def _command_values(text: str, name: str) -> list[tuple[int, str]]:
    values: list[tuple[int, str]] = []
    for match in COMMAND_RE.finditer(text):
        if match.group(1) != name:
            continue
        argument = _command_argument_at(text, match.end())
        if argument is not None:
            values.append((match.start(), argument[0]))
    return values


def _balanced_command(text: str, name: str) -> str:
    values = _command_values(text, name)
    return values[0][1] if values else ""


def _figure_environments(text: str) -> list[_FigureEnvironment]:
    environments: list[_FigureEnvironment] = []
    cursor = 0
    while match := FIGURE_BEGIN_RE.search(text, cursor):
        name = match.group(1)
        end_match = re.search(rf"\\end\s*\{{{re.escape(name)}\}}", text[match.end() :])
        if end_match is None:
            cursor = match.end()
            continue
        body_end = match.end() + end_match.start()
        environment_end = match.end() + end_match.end()
        environments.append(
            _FigureEnvironment(
                start=match.start(),
                end=environment_end,
                name=name,
                body=text[match.end() : body_end],
            )
        )
        cursor = environment_end
    return environments


def _heading_commands(text: str) -> list[_Heading]:
    headings: list[_Heading] = []
    for match in COMMAND_RE.finditer(text):
        name = match.group(1)
        if name not in {"section", "section*", "subsection", "subsection*"}:
            continue
        argument = _command_argument_at(text, match.end())
        if argument is None:
            continue
        headings.append(
            _Heading(
                offset=match.start(),
                level="subsection" if name.startswith("subsection") else "section",
                text=_clean_latex_text(argument[0]),
            )
        )
    return headings


def _containing_headings(headings: list[_Heading], offset: int) -> tuple[str, str]:
    section = ""
    subsection = ""
    for heading in headings:
        if heading.offset >= offset:
            break
        if heading.level == "section":
            section = heading.text
            subsection = ""
        else:
            subsection = heading.text
    return section, subsection


def _mask_environments(text: str, environments: list[_FigureEnvironment]) -> str:
    chars = list(text)
    for environment in environments:
        for index in range(environment.start, environment.end):
            if chars[index] != "\n":
                chars[index] = " "
    return "".join(chars)


def _paragraphs_with_offsets(text: str) -> list[_Paragraph]:
    paragraphs: list[_Paragraph] = []
    for match in re.finditer(r"(?:^|\n\s*\n)(.*?)(?=\n\s*\n|\Z)", text, re.S):
        value = match.group(1)
        if value.strip():
            paragraphs.append(_Paragraph(start=match.start(1), text=value.strip()))
    return paragraphs


def _referenced_labels(text: str) -> set[str]:
    labels: set[str] = set()
    for match in COMMAND_RE.finditer(text):
        if match.group(1) not in REFERENCE_COMMANDS:
            continue
        argument = _command_argument_at(text, match.end())
        if argument is None:
            continue
        labels.update(label.strip() for label in argument[0].split(",") if label.strip())
    return labels


def _clean_latex_text(text: str) -> str:
    previous = None
    cleaned = text
    while cleaned != previous:
        previous = cleaned
        pieces: list[str] = []
        cursor = 0
        for match in COMMAND_RE.finditer(cleaned):
            if match.start() < cursor:
                continue
            name = match.group(1)
            argument = _command_argument_at(cleaned, match.end())
            if argument is None:
                continue
            pieces.append(cleaned[cursor : match.start()])
            if name in FORMATTING_COMMANDS or name in {"section", "section*", "subsection", "subsection*"}:
                pieces.append(argument[0])
            elif name not in DISCARDED_COMMANDS and name not in REFERENCE_COMMANDS:
                pieces.append(argument[0])
            cursor = argument[1]
        if cursor:
            pieces.append(cleaned[cursor:])
            cleaned = "".join(pieces)

    cleaned = re.sub(r"\\([%&#_$])", r"\1", cleaned)
    cleaned = re.sub(r"~", " ", cleaned)
    cleaned = re.sub(r"\\ddagger\b", "ddagger", cleaned)
    cleaned = re.sub(r"\\dagger\b", "dagger", cleaned)
    cleaned = re.sub(r"\\[A-Za-z]+\*?", "", cleaned)
    cleaned = cleaned.replace("^", "")
    cleaned = cleaned.replace("$", "")
    cleaned = cleaned.replace("{", "").replace("}", "")
    cleaned = " ".join(cleaned.split())
    return re.sub(r"\s+([.,;:!?])", r"\1", cleaned).strip()


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


def _build_evidence(
    figure_id: str,
    caption: str,
    label: str,
    paragraphs: list[_Paragraph],
) -> tuple[FigureEvidence, ...]:
    evidence: list[FigureEvidence] = []
    if caption:
        evidence.append(FigureEvidence(f"{figure_id}-caption", "caption", caption))
    reference_number = 0
    if label:
        for paragraph in paragraphs:
            if label not in _referenced_labels(paragraph.text):
                continue
            text = _clean_latex_text(paragraph.text)
            if not text:
                continue
            reference_number += 1
            evidence.append(
                FigureEvidence(
                    f"{figure_id}-reference-{reference_number}",
                    "reference",
                    text,
                )
            )
    return tuple(evidence)


def parse_figure_manifest(source_tex: Path) -> list[FigureRecord]:
    text = _remove_latex_comments(source_tex.read_text(encoding="utf-8", errors="replace"))
    environments = _figure_environments(text)
    headings = _heading_commands(text)
    paragraphs = _paragraphs_with_offsets(_mask_environments(text, environments))
    records: list[FigureRecord] = []

    for number, environment in enumerate(environments, start=1):
        figure_id = f"fig-{number}"
        caption = _clean_latex_text(_balanced_command(environment.body, "caption"))
        label = _balanced_command(environment.body, "label").strip()
        includes = tuple(
            value.strip()
            for _, value in _command_values(environment.body, "includegraphics")
            if value.strip()
        )
        section, subsection = _containing_headings(headings, environment.start)
        role_text = " ".join((caption, section, subsection, *includes))
        records.append(
            FigureRecord(
                figure_id=figure_id,
                number=number,
                label=label,
                layout="double-column" if environment.name == "figure*" else "single-column",
                includes=includes,
                caption=caption,
                section=section,
                subsection=subsection,
                role=_figure_role(role_text),
                evidence=_build_evidence(figure_id, caption, label, paragraphs),
            )
        )
    return records


def _normalized_relative_name(value: str) -> str:
    if not value or "\x00" in value or "\\" in value:
        raise FigureSourceError(f"unsafe archive member: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise FigureSourceError(f"unsafe archive member: {value!r}")
    normalized = str(PurePosixPath(*(part for part in path.parts if part not in ("", "."))))
    if normalized in ("", "."):
        return "."
    return normalized


def _reference_names(reference: str) -> tuple[str, ...]:
    normalized = _normalized_relative_name(reference)
    if normalized == ".":
        return ()
    path = PurePosixPath(normalized)
    if path.suffix:
        return (normalized,)
    return tuple(f"{normalized}{extension}" for extension in SOURCE_EXTENSIONS)


def _reference_candidates(paper_dir: Path, reference: str) -> tuple[Path, ...]:
    try:
        names = _reference_names(reference)
    except FigureSourceError:
        return ()
    return tuple(paper_dir.joinpath(*PurePosixPath(name).parts) for name in names)


def resolve_exact_source_assets(record: FigureRecord, paper_dir: Path) -> list[Path]:
    matches: list[Path] = []
    for reference in record.includes:
        reference_candidates = _reference_candidates(paper_dir, reference)
        direct_match = None
        for candidate in reference_candidates:
            if candidate.is_file() and not candidate.is_symlink():
                direct_match = candidate
                break
        if direct_match is not None:
            matches.append(direct_match)
            continue

        basenames = {candidate.name for candidate in reference_candidates}
        basename_matches = [
            candidate
            for candidate in paper_dir.rglob("*")
            if candidate.name in basenames and candidate.is_file() and not candidate.is_symlink()
        ]
        if len(basename_matches) == 1:
            matches.append(basename_matches[0])
    return matches


def _validate_archive_member(member: tarfile.TarInfo) -> str:
    normalized = _normalized_relative_name(member.name)
    if not (member.isfile() or member.isdir()):
        raise FigureSourceError(f"unsafe archive member: {member.name!r}")
    return normalized


def _safe_archive_destination(target: Path, normalized: str) -> Path:
    root = target.resolve()
    destination = target.joinpath(*PurePosixPath(normalized).parts)
    if not destination.resolve(strict=False).is_relative_to(root):
        raise FigureSourceError(f"unsafe archive member: {normalized!r}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink() or not destination.resolve(strict=False).is_relative_to(root):
        raise FigureSourceError(f"unsafe archive destination: {normalized!r}")
    return destination


def extract_referenced_archive_assets(
    archive_path: Path,
    references: set[str],
    target: Path,
) -> dict[str, Path]:
    reference_names = {reference: _reference_names(reference) for reference in references}
    wanted = {name for names in reference_names.values() for name in names}
    resolved_names: dict[str, str] = {}

    try:
        with tarfile.open(archive_path, "r:*") as archive:
            members = archive.getmembers()
            normalized_members = [_validate_archive_member(member) for member in members]

            selected: list[tuple[tarfile.TarInfo, str]] = []
            for member, normalized in zip(members, normalized_members, strict=True):
                if normalized not in wanted or not member.isfile():
                    continue
                selected.append((member, normalized))
                for reference, names in reference_names.items():
                    if reference not in resolved_names and normalized in names:
                        resolved_names[reference] = normalized

            for member, normalized in selected:
                stream = archive.extractfile(member)
                if stream is None:
                    raise FigureSourceError(f"cannot read archive member: {member.name!r}")
                destination = _safe_archive_destination(target, normalized)
                with stream, destination.open("wb") as output:
                    shutil.copyfileobj(stream, output)
    except (EOFError, tarfile.TarError, OSError, ValueError) as exc:
        raise FigureSourceError(f"cannot extract source archive: {exc}") from exc

    return {
        reference: target.joinpath(*PurePosixPath(normalized).parts)
        for reference, normalized in resolved_names.items()
    }


def fetch_arxiv_source(
    arxiv_id: str,
    destination: Path,
    opener=urllib.request.urlopen,
) -> Path:
    if destination.is_file():
        return destination

    url = f"https://export.arxiv.org/e-print/{urllib.parse.quote(arxiv_id, safe='/')}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AIResearch/0.1 (+https://arxiv.org/)"},
    )
    temporary = destination.with_name(f".{destination.name}.part")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with opener(request, timeout=90) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        temporary.replace(destination)
    except Exception as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise FigureSourceError(f"failed to download arXiv source {arxiv_id}: {exc}") from exc
    return destination


def _file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _short_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _read_figure_manifest(path: Path) -> dict[str, dict[str, str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {key: entry for key, entry in value.items() if isinstance(key, str) and isinstance(entry, dict)}


def _write_figure_manifest(path: Path, manifest: dict[str, dict[str, str]]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def normalize_figure_asset(
    source: Path,
    destination: Path,
    run=subprocess.run,
) -> Path:
    suffix = source.suffix.lower()
    if suffix not in SOURCE_EXTENSIONS:
        raise FigureSourceError(f"unsupported figure source: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = destination.parent / "manifest.json"
    manifest = _read_figure_manifest(manifest_path)
    source_path = str(source.resolve())
    fingerprint = _file_fingerprint(source)
    cached = manifest.get(destination.name, {})
    if (
        destination.is_file()
        and cached.get("source") == source_path
        and cached.get("fingerprint") == fingerprint
    ):
        return destination

    temporary_output: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.stem}-",
            suffix=".webp",
            dir=destination.parent,
            delete=False,
        ) as output:
            temporary_output = Path(output.name)

        raster_source = source
        with tempfile.TemporaryDirectory(prefix="paper-figure-", dir=destination.parent) as temporary:
            if suffix in {".pdf", ".eps"}:
                raster_prefix = Path(temporary) / "raster"
                run(
                    [
                        "pdftocairo",
                        "-png",
                        "-singlefile",
                        "-r",
                        "180",
                        str(source),
                        str(raster_prefix),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=90,
                )
                raster_source = raster_prefix.with_suffix(".png")
            run(
                [
                    "convert",
                    str(raster_source),
                    "-auto-orient",
                    "-resize",
                    "2400x2400>",
                    "-strip",
                    "-quality",
                    "88",
                    str(temporary_output),
                ],
                check=True,
                capture_output=True,
                timeout=90,
            )

        if temporary_output.stat().st_size == 0:
            raise FigureSourceError(f"figure conversion produced empty output: {source}")
        temporary_output.replace(destination)
    except FigureSourceError:
        raise
    except Exception as exc:
        raise FigureSourceError(f"failed to normalize figure asset {source}: {exc}") from exc
    finally:
        if temporary_output is not None:
            try:
                temporary_output.unlink(missing_ok=True)
            except OSError:
                pass

    manifest[destination.name] = {"source": source_path, "fingerprint": fingerprint}
    _write_figure_manifest(manifest_path, manifest)
    return destination


def crop_pdf_figure_fallback(
    record: FigureRecord,
    pdf_path: Path,
    destination: Path,
    *,
    run=subprocess.run,
):
    from airesearch.figure_crop import (
        CropResult,
        extract_page_layouts,
        find_figure_caption,
        plan_figure_crop,
        render_figure_crop,
    )

    if not pdf_path.exists() or not pdf_path.is_file():
        return CropResult(
            None,
            0.0,
            False,
            ("pdf-missing",),
            {"stage": "input", "pdf_path": str(pdf_path)},
        )

    with tempfile.TemporaryDirectory(prefix="paper-figure-crop-", dir=destination.parent) as temp_dir:
        work_dir = Path(temp_dir)
        try:
            layouts = extract_page_layouts(pdf_path, work_dir, run=run)
        except Exception as exc:
            return CropResult(
                None,
                0.0,
                False,
                ("layout-failed",),
                {"stage": "layout", "error": type(exc).__name__},
            )

        match = find_figure_caption(layouts, record)
        if match is None:
            return CropResult(
                None,
                0.0,
                False,
                ("caption-not-found",),
                {"stage": "caption", "figure_number": record.number},
            )

        plan = plan_figure_crop(record, match.page, match.block)
        if not plan.accepted:
            return CropResult(
                None,
                min(match.confidence, plan.confidence),
                False,
                plan.reasons,
                {
                    **plan.diagnostics,
                    "stage": "plan",
                    "caption_confidence": match.confidence,
                    "caption_diagnostics": match.diagnostics,
                },
            )

        result = render_figure_crop(pdf_path, destination, plan, work_dir, run=run)
        return CropResult(
            result.path,
            min(match.confidence, result.confidence),
            result.accepted,
            result.reasons,
            {
                **result.diagnostics,
                "caption_confidence": match.confidence,
                "caption_diagnostics": match.diagnostics,
            },
        )


def _normalized_destination(output_dir: Path, record: FigureRecord) -> Path:
    return output_dir / f"figure-{record.number:02d}.webp"


def _resolved_from_source(
    *,
    record: FigureRecord,
    source_reference: str,
    source_path: Path,
    output_dir: Path,
    extraction_method: str,
    diagnostics: tuple[str, ...],
    normalizer: Callable[..., Path],
) -> ResolvedFigure:
    destination = _normalized_destination(output_dir, record)
    normalized = normalizer(source_path, destination)
    return ResolvedFigure(
        record=record,
        path=normalized,
        source_reference=source_reference,
        extraction_method=extraction_method,
        confidence=1.0,
        content_sha256=_file_fingerprint(normalized),
        diagnostics=diagnostics,
    )


def _fallback_crop(
    *,
    record: FigureRecord,
    pdf_path: Path | None,
    output_dir: Path,
    cropper: Callable[..., Any],
    diagnostics: tuple[str, ...],
) -> ResolvedFigure | None:
    if pdf_path is None:
        return None
    destination = _normalized_destination(output_dir, record)
    result = cropper(record, pdf_path, destination)
    if not getattr(result, "accepted", False) or getattr(result, "path", None) is None:
        return None
    path = Path(result.path)
    return ResolvedFigure(
        record=record,
        path=path,
        source_reference="",
        extraction_method="pdf_crop",
        confidence=float(getattr(result, "confidence", 0.0) or 0.0),
        content_sha256=_file_fingerprint(path),
        diagnostics=tuple(diagnostics + tuple(getattr(result, "reasons", ()) or ())),
    )


def resolve_paper_figures(
    *,
    source_tex: Path,
    paper_dir: Path,
    pdf_path: Path | None,
    arxiv_id: str | None,
    cache_dir: Path,
    output_dir: Path,
    normalizer: Callable[..., Path] | None = None,
    source_fetcher: Callable[..., Path] | None = None,
    cropper: Callable[..., Any] | None = None,
) -> list[ResolvedFigure]:
    if not source_tex.exists() or not source_tex.is_file():
        return []

    normalizer = normalizer or normalize_figure_asset
    source_fetcher = source_fetcher or fetch_arxiv_source
    cropper = cropper or crop_pdf_figure_fallback
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    records = parse_figure_manifest(source_tex)
    resolved: list[ResolvedFigure] = []
    unresolved: list[FigureRecord] = []

    for record in records:
        if len(record.includes) != 1:
            unresolved.append(record)
            continue
        matches = resolve_exact_source_assets(record, paper_dir)
        if matches:
            try:
                resolved.append(
                    _resolved_from_source(
                        record=record,
                        source_reference=record.includes[0],
                        source_path=matches[0],
                        output_dir=output_dir,
                        extraction_method="local_source",
                        diagnostics=("local-source",),
                        normalizer=normalizer,
                    )
                )
                continue
            except FigureSourceError:
                pass
        unresolved.append(record)

    archive_assets: dict[str, Path] = {}
    if unresolved and arxiv_id:
        archive_cache = cache_dir / _short_digest(arxiv_id)
        archive_path = archive_cache / "source.tar"
        needed = {record.includes[0] for record in unresolved if len(record.includes) == 1}
        if needed:
            try:
                for attempt in range(2):
                    fetched = source_fetcher(arxiv_id, archive_path)
                    try:
                        with tempfile.TemporaryDirectory(prefix="extract-", dir=archive_cache) as extract_dir:
                            archive_assets = extract_referenced_archive_assets(fetched, needed, Path(extract_dir))
                            still_unresolved: list[FigureRecord] = []
                            for record in unresolved:
                                if len(record.includes) != 1 or record.includes[0] not in archive_assets:
                                    still_unresolved.append(record)
                                    continue
                                try:
                                    resolved.append(
                                        _resolved_from_source(
                                            record=record,
                                            source_reference=record.includes[0],
                                            source_path=archive_assets[record.includes[0]],
                                            output_dir=output_dir,
                                            extraction_method="arxiv_source",
                                            diagnostics=("arxiv-source",),
                                            normalizer=normalizer,
                                        )
                                    )
                                except FigureSourceError:
                                    still_unresolved.append(record)
                            unresolved = still_unresolved
                        break
                    except FigureSourceError as exc:
                        if attempt == 0 and archive_path.exists():
                            try:
                                archive_path.unlink()
                            except OSError:
                                pass
                            continue
                        raise
            except FigureSourceError:
                pass

    for record in unresolved:
        cropped = _fallback_crop(
            record=record,
            pdf_path=pdf_path,
            output_dir=output_dir,
            cropper=cropper,
            diagnostics=("pdf-fallback",),
        )
        if cropped is not None:
            resolved.append(cropped)

    return sorted(resolved, key=lambda figure: figure.record.number)
