import io
import hashlib
import json
import shutil
import subprocess
import tarfile
import urllib.request
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from airesearch.paper_figures import (
    FigureRecord,
    FigureSourceError,
    crop_pdf_figure_fallback,
    extract_referenced_archive_assets,
    fetch_arxiv_source,
    normalize_figure_asset,
    parse_figure_manifest,
    resolve_paper_figures,
    resolve_exact_source_assets,
)
from airesearch.figure_crop import (
    PageLayout,
    TextBlock,
    TextLine,
    WordBox,
    find_figure_caption,
    parse_bbox_layout,
    plan_figure_crop,
)


def figure_record(
    *,
    includes: tuple[str, ...] = (),
    number: int = 1,
    layout: str = "single-column",
    caption: str = "Test figure.",
) -> FigureRecord:
    return FigureRecord(
        figure_id=f"fig-{number}",
        number=number,
        label="fig:test",
        layout=layout,
        includes=includes,
        caption=caption,
        section="",
        subsection="",
        role="figure",
        evidence=(),
    )


def text_block(
    left: float,
    top: float,
    right: float,
    bottom: float,
    text: str,
    *,
    line_count: int = 1,
) -> TextBlock:
    line_height = (bottom - top) / line_count
    lines = tuple(
        TextLine(
            left=left,
            top=top + index * line_height,
            right=right,
            bottom=top + (index + 1) * line_height,
            words=(WordBox(left, top, right, bottom, word),),
            text=word,
        )
        for index, word in enumerate([text] * line_count)
    )
    return TextBlock(left, top, right, bottom, lines, " ".join(line.text for line in lines))


def write_source_archive(tmp_path: Path, members: list[tuple[tarfile.TarInfo, bytes]]) -> Path:
    archive_path = tmp_path / "source.tar"
    with tarfile.open(archive_path, "w") as archive:
        for member, content in members:
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
    return archive_path


def regular_member(name: str, content: bytes = b"asset") -> tuple[tarfile.TarInfo, bytes]:
    return tarfile.TarInfo(name), content


def test_parse_figure_manifest_keeps_layout_caption_and_reference_evidence(tmp_path: Path):
    source = tmp_path / "source.tex"
    source.write_text(
        r"""
\section{Motivation}
Figure~\ref{fig:motivation} compares text and latent reasoning.
% \begin{figure}\includegraphics{img/ignored}\caption{Ignored}\end{figure}
\begin{figure}[t]
  \includegraphics[width=.48\textwidth]{img/motivation}
  \caption{\textbf{Inference paradigms.} Latent reasoning removes \emph{text decoding}.}
  \label{fig:motivation}
\end{figure}
\section{Method}
\subsection{Planner Architecture}
As shown in Fig.~\ref{fig:framework}, visual tokens enter the planner.
\begin{figure*}[t]
  \includegraphics[width=.48\linewidth]{img/encoder}
  \includegraphics[width=.48\linewidth]{img/framework.pdf}
  \caption[Framework]{Overview of the \textbf{complete {ColaVLA} framework}.}
  \label{fig:framework}
\end{figure*}
""",
        encoding="utf-8",
    )

    records = parse_figure_manifest(source)

    assert [record.figure_id for record in records] == ["fig-1", "fig-2"]
    assert [record.layout for record in records] == ["single-column", "double-column"]
    assert records[0].includes == ("img/motivation",)
    assert records[1].includes == ("img/encoder", "img/framework.pdf")
    assert records[0].label == "fig:motivation"
    assert records[0].caption == "Inference paradigms. Latent reasoning removes text decoding."
    assert records[0].section == "Motivation"
    assert records[0].subsection == ""
    assert records[0].role == "motivation"
    assert records[1].section == "Method"
    assert records[1].subsection == "Planner Architecture"
    assert records[1].role == "framework"
    assert records[0].evidence[0].evidence_id == "fig-1-caption"
    assert records[0].evidence[0].kind == "caption"
    assert records[0].evidence[1].evidence_id == "fig-1-reference-1"
    assert records[0].evidence[1].kind == "reference"
    assert "compares text and latent reasoning" in records[0].evidence[1].text


def test_parser_handles_comments_nested_commands_and_reference_variants(tmp_path: Path):
    source = tmp_path / "source.tex"
    source.write_text(
        r"""
\section{Experiments \& Results} % a heading comment
\subsection{Closed-loop Evaluation}
The 10\% route subset is summarized by \autoref{fig:results}.

\cref{fig:results} compares the \textit{closed-loop {driving} score} against baselines.
% The disabled version cites \ref{fig:results} and must not become evidence.
\begin{figure}
  \includegraphics{plots/closed_loop}
  \caption{Closed-loop \textbf{comparison} on \textsc{NeuroNCAP} \cite{smith2025}.}
  \label{fig:results}
\end{figure}

\subsection{Ablations}
\begin{figure}
  \includegraphics{plots/mask}
  \caption{Ablation of the \textbf{hybrid {attention} mask}.}
  \label{fig:mask}
\end{figure}
""",
        encoding="utf-8",
    )

    records = parse_figure_manifest(source)

    assert len(records) == 2
    assert records[0].section == "Experiments & Results"
    assert records[0].subsection == "Closed-loop Evaluation"
    assert records[0].caption == "Closed-loop comparison on NeuroNCAP."
    assert records[0].role == "qualitative"
    assert [item.evidence_id for item in records[0].evidence] == [
        "fig-1-caption",
        "fig-1-reference-1",
        "fig-1-reference-2",
    ]
    assert "10% route subset" in records[0].evidence[1].text
    assert "disabled version" not in " ".join(item.text for item in records[0].evidence)
    assert records[1].subsection == "Ablations"
    assert records[1].role == "experiments"
    assert [item.kind for item in records[1].evidence] == ["caption"]


def test_figure_records_and_nested_evidence_are_immutable(tmp_path: Path):
    source = tmp_path / "source.tex"
    source.write_text(
        r"""
\begin{figure}
  \includegraphics{method}
  \caption{Method overview.}
  \label{fig:method}
\end{figure}
""",
        encoding="utf-8",
    )

    record = parse_figure_manifest(source)[0]

    with pytest.raises(FrozenInstanceError):
        record.caption = "Changed"
    with pytest.raises(FrozenInstanceError):
        record.evidence[0].text = "Changed"


def test_resolve_source_assets_uses_exact_references_and_omitted_extensions(tmp_path: Path):
    paper = tmp_path / "paper"
    (paper / "img").mkdir(parents=True)
    framework = paper / "img" / "framework.pdf"
    framework.write_bytes(b"author")
    explicit = paper / "img" / "results.png"
    explicit.write_bytes(b"results")
    (paper / "figures").mkdir()
    generic = paper / "figures" / "figure_01.png"
    generic.write_bytes(b"icon")
    wrong_basename = paper / "framework.pdf"
    wrong_basename.write_bytes(b"wrong")

    matches = resolve_exact_source_assets(
        figure_record(includes=("img/framework", "img/results.png", "img/missing")),
        paper,
    )

    assert matches == [framework, explicit]
    assert generic not in matches
    assert wrong_basename not in matches


def test_resolve_source_assets_rejects_symlinks(tmp_path: Path):
    paper = tmp_path / "paper"
    (paper / "img").mkdir(parents=True)
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"outside")
    (paper / "img" / "framework.pdf").symlink_to(outside)

    assert resolve_exact_source_assets(figure_record(includes=("img/framework",)), paper) == []


def test_resolve_source_assets_falls_back_to_unique_exact_basename(tmp_path: Path):
    paper = tmp_path / "paper"
    (paper / "author-assets").mkdir(parents=True)
    framework = paper / "author-assets" / "framework.pdf"
    framework.write_bytes(b"author")
    (paper / "author-assets" / "framework-detail.pdf").write_bytes(b"other")
    (paper / "figures").mkdir()
    (paper / "figures" / "figure_01.png").write_bytes(b"generic")

    matches = resolve_exact_source_assets(figure_record(includes=("img/framework",)), paper)

    assert matches == [framework]


def test_resolve_source_assets_supports_svg_references(tmp_path: Path):
    paper = tmp_path / "paper"
    (paper / "figures").mkdir(parents=True)
    svg = paper / "figures" / "figure1.svg"
    svg.write_text("<svg></svg>", encoding="utf-8")

    matches = resolve_exact_source_assets(figure_record(includes=("figures/figure1",)), paper)

    assert matches == [svg]


def test_resolve_source_assets_rejects_ambiguous_exact_basename(tmp_path: Path):
    paper = tmp_path / "paper"
    (paper / "first").mkdir(parents=True)
    (paper / "second").mkdir()
    (paper / "first" / "framework.pdf").write_bytes(b"first")
    (paper / "second" / "framework.png").write_bytes(b"second")

    matches = resolve_exact_source_assets(figure_record(includes=("missing/framework",)), paper)

    assert matches == []


def test_archive_rejects_late_traversal_before_extracting(tmp_path: Path):
    archive = write_source_archive(
        tmp_path,
        [regular_member("img/framework.pdf", b"pdf"), regular_member("../escape", b"bad")],
    )
    target = tmp_path / "cache"

    with pytest.raises(FigureSourceError, match="unsafe archive member"):
        extract_referenced_archive_assets(archive, {"img/framework.pdf"}, target)

    assert not (target / "img" / "framework.pdf").exists()


@pytest.mark.parametrize("member_name", ["/tmp/absolute.pdf", "../../escape.pdf"])
def test_archive_rejects_absolute_and_parent_paths(tmp_path: Path, member_name: str):
    archive = write_source_archive(tmp_path, [regular_member(member_name)])

    with pytest.raises(FigureSourceError, match="unsafe archive member"):
        extract_referenced_archive_assets(archive, set(), tmp_path / "cache")


@pytest.mark.parametrize(
    "member_type",
    [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE],
)
def test_archive_rejects_links_and_devices(tmp_path: Path, member_type: bytes):
    member = tarfile.TarInfo("img/unsafe")
    member.type = member_type
    member.linkname = "img/framework.pdf"
    archive = write_source_archive(tmp_path, [(member, b"")])

    with pytest.raises(FigureSourceError, match="unsafe archive member"):
        extract_referenced_archive_assets(archive, set(), tmp_path / "cache")


def test_archive_extracts_only_exact_referenced_regular_files(tmp_path: Path):
    archive = write_source_archive(
        tmp_path,
        [
            regular_member("img/framework.pdf", b"pdf"),
            regular_member("img/unused.png", b"unused"),
            regular_member("figure_01.png", b"generic"),
        ],
    )
    target = tmp_path / "cache"

    resolved = extract_referenced_archive_assets(archive, {"img/framework"}, target)

    assert resolved == {"img/framework": target / "img" / "framework.pdf"}
    assert (target / "img" / "framework.pdf").read_bytes() == b"pdf"
    assert not (target / "img" / "unused.png").exists()
    assert not (target / "figure_01.png").exists()


def test_archive_wraps_truncated_tar_as_source_error(tmp_path: Path):
    archive = tmp_path / "source.tar"
    archive.write_bytes(b"not a complete tar archive")

    with pytest.raises(FigureSourceError, match="cannot extract source archive"):
        extract_referenced_archive_assets(archive, {"img/framework"}, tmp_path / "cache")


def test_fetch_arxiv_source_uses_injected_opener_and_reuses_cache(tmp_path: Path):
    destination = tmp_path / "cache" / "source.tar"
    opened: list[tuple[urllib.request.Request, int]] = []

    def opener(request: urllib.request.Request, *, timeout: int):
        opened.append((request, timeout))
        return io.BytesIO(b"source archive")

    assert fetch_arxiv_source("2503.04496v2", destination, opener=opener) == destination
    assert destination.read_bytes() == b"source archive"
    assert opened[0][0].full_url == "https://export.arxiv.org/e-print/2503.04496v2"
    assert opened[0][0].get_header("User-agent") == "AIResearch/0.1 (+https://arxiv.org/)"
    assert opened[0][1] == 90

    def offline_opener(request: urllib.request.Request, *, timeout: int):
        raise AssertionError(f"network access attempted: {request.full_url}")

    assert fetch_arxiv_source("2503.04496v2", destination, opener=offline_opener) == destination


def test_fetch_arxiv_source_wraps_network_errors_with_cause(tmp_path: Path):
    failure = OSError("offline")

    def opener(request: urllib.request.Request, *, timeout: int):
        raise failure

    with pytest.raises(FigureSourceError, match="download arXiv source") as caught:
        fetch_arxiv_source("2503.04496v2", tmp_path / "source.tar", opener=opener)

    assert caught.value.__cause__ is failure


@pytest.mark.parametrize("suffix", [".pdf", ".eps", ".png", ".jpg", ".webp"])
def test_normalize_figure_asset_creates_webp_with_injected_run(tmp_path: Path, suffix: str):
    source = tmp_path / f"source{suffix}"
    source.write_bytes(b"figure")
    destination = tmp_path / "figures" / "blog" / "figure-2.webp"
    commands: list[list[str]] = []

    def run(command: list[str], **kwargs):
        commands.append(command)
        if command[0] == "pdftocairo":
            Path(f"{command[-1]}.png").write_bytes(b"raster")
        else:
            Path(command[-1]).write_bytes(b"webp")

    assert normalize_figure_asset(source, destination, run=run) == destination
    assert destination.read_bytes() == b"webp"
    assert commands[-1][0] == "convert"
    assert commands[-1][commands[-1].index("-resize") + 1] == "2400x2400>"
    assert Path(commands[-1][-1]).parent == destination.parent
    assert Path(commands[-1][-1]).suffix == ".webp"
    assert Path(commands[-1][-1]) != destination
    if suffix in {".pdf", ".eps"}:
        assert commands[0][:2] == ["pdftocairo", "-png"]
    else:
        assert len(commands) == 1


def test_normalize_figure_asset_reuses_matching_manifest_fingerprint(tmp_path: Path):
    source = tmp_path / "framework.png"
    source.write_bytes(b"same source")
    destination = tmp_path / "figures" / "blog" / "figure-1.webp"
    calls = 0

    def run(command: list[str], **kwargs):
        nonlocal calls
        calls += 1
        Path(command[-1]).write_bytes(b"webp")

    normalize_figure_asset(source, destination, run=run)
    manifest = json.loads((destination.parent / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["figure-1.webp"]["source"] == str(source.resolve())
    assert len(manifest["figure-1.webp"]["fingerprint"]) == 64

    def fail_run(command: list[str], **kwargs):
        raise AssertionError("cached figure was converted again")

    assert normalize_figure_asset(source, destination, run=fail_run) == destination
    assert calls == 1


def test_normalize_figure_asset_refreshes_changed_source(tmp_path: Path):
    source = tmp_path / "framework.png"
    source.write_bytes(b"first")
    destination = tmp_path / "figures" / "blog" / "figure-1.webp"
    calls = 0

    def run(command: list[str], **kwargs):
        nonlocal calls
        calls += 1
        Path(command[-1]).write_bytes(f"webp-{calls}".encode())

    normalize_figure_asset(source, destination, run=run)
    source.write_bytes(b"second")
    normalize_figure_asset(source, destination, run=run)

    assert calls == 2
    assert destination.read_bytes() == b"webp-2"


def test_normalize_figure_asset_failure_leaves_no_output_or_manifest(tmp_path: Path):
    source = tmp_path / "framework.png"
    source.write_bytes(b"source")
    destination = tmp_path / "figures" / "blog" / "figure-1.webp"
    failure = subprocess.CalledProcessError(1, ["convert"], stderr=b"bad image")

    def run(command: list[str], **kwargs):
        Path(command[-1]).write_bytes(b"partial")
        raise failure

    with pytest.raises(FigureSourceError, match="normalize figure asset") as caught:
        normalize_figure_asset(source, destination, run=run)

    assert caught.value.__cause__ is failure
    assert not destination.exists()
    assert not (destination.parent / "manifest.json").exists()


def test_normalize_figure_asset_failure_preserves_existing_output_and_manifest(tmp_path: Path):
    source = tmp_path / "framework.png"
    source.write_bytes(b"changed source")
    destination = tmp_path / "figures" / "blog" / "figure-1.webp"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"old webp")
    manifest_path = destination.parent / "manifest.json"
    old_manifest = '{"figure-1.webp": {"fingerprint": "old", "source": "old"}}\n'
    manifest_path.write_text(old_manifest, encoding="utf-8")

    def run(command: list[str], **kwargs):
        Path(command[-1]).write_bytes(b"partial")
        raise OSError("converter unavailable")

    with pytest.raises(FigureSourceError, match="normalize figure asset"):
        normalize_figure_asset(source, destination, run=run)

    assert destination.read_bytes() == b"old webp"
    assert manifest_path.read_text(encoding="utf-8") == old_manifest


def test_normalize_figure_asset_rejects_empty_converter_output(tmp_path: Path):
    source = tmp_path / "framework.png"
    source.write_bytes(b"source")
    destination = tmp_path / "figures" / "blog" / "figure-1.webp"

    def run(command: list[str], **kwargs):
        Path(command[-1]).touch()

    with pytest.raises(FigureSourceError, match="empty output"):
        normalize_figure_asset(source, destination, run=run)

    assert not destination.exists()
    assert not (destination.parent / "manifest.json").exists()


BBOX_LAYOUT = """\
<html><body><doc>
  <page width="612.000000" height="792.000000">
    <flow><block xMin="318" yMin="60" xMax="570" yMax="90">
      <line xMin="318" yMin="60" xMax="570" yMax="70">
        <word xMin="318" yMin="60" xMax="340" yMax="70">Body</word>
        <word xMin="344" yMin="60" xMax="370" yMax="70">text</word>
      </line>
    </block></flow>
    <flow><block xMin="318" yMin="430" xMax="568" yMax="466">
      <line xMin="318" yMin="430" xMax="568" yMax="442">
        <word xMin="318" yMin="430" xMax="345" yMax="442">Figure</word>
        <word xMin="349" yMin="430" xMax="356" yMax="442">4.</word>
        <word xMin="360" yMin="430" xMax="405" yMax="442">Hybrid</word>
      </line>
      <line xMin="318" yMin="448" xMax="430" yMax="466">
        <word xMin="318" yMin="448" xMax="350" yMax="466">mask</word>
        <word xMin="354" yMin="448" xMax="390" yMax="466">overview.</word>
      </line>
    </block></flow>
  </page>
</doc></body></html>
"""


def test_parse_bbox_layout_preserves_page_block_line_and_word_coordinates():
    layouts = parse_bbox_layout(BBOX_LAYOUT)

    assert len(layouts) == 1
    assert (layouts[0].width, layouts[0].height) == (612.0, 792.0)
    caption = layouts[0].blocks[1]
    assert (caption.left, caption.top, caption.right, caption.bottom) == (318.0, 430.0, 568.0, 466.0)
    assert len(caption.lines) == 2
    assert caption.lines[0].words[0] == WordBox(318.0, 430.0, 345.0, 442.0, "Figure")
    assert caption.text == "Figure 4. Hybrid mask overview."


def test_find_caption_uses_manifest_similarity_when_body_reference_appears_first():
    page = PageLayout(
        number=1,
        width=612,
        height=792,
        blocks=(
            text_block(30, 80, 290, 100, "Fig. 4 shows the result of our baseline."),
            text_block(318, 430, 568, 470, "Figure 4. Hybrid mask overview."),
        ),
    )

    match = find_figure_caption([page], figure_record(number=4, caption="Hybrid mask overview."))

    assert match is not None
    assert match.block is page.blocks[1]
    assert match.candidate_count == 2
    assert match.confidence >= 0.7


def test_find_caption_rejects_ambiguity_without_manifest_caption():
    page = PageLayout(
        number=1,
        width=612,
        height=792,
        blocks=(
            text_block(30, 80, 290, 100, "Fig. 4 first candidate"),
            text_block(318, 430, 568, 470, "Figure 4 second candidate"),
        ),
    )

    assert find_figure_caption([page], figure_record(number=4, caption="")) is None


def test_find_caption_without_manifest_caption_requires_strict_figure_prefix():
    page = PageLayout(
        number=1,
        width=612,
        height=792,
        blocks=(text_block(30, 80, 290, 100, "Fig. 4 shows the result of our baseline."),),
    )

    assert find_figure_caption([page], figure_record(number=4, caption="")) is None


def test_find_caption_handles_tied_similarity_without_comparing_page_objects():
    page = PageLayout(
        number=1,
        width=612,
        height=792,
        blocks=(
            text_block(30, 80, 290, 100, "Figure 4. Hybrid mask overview."),
            text_block(318, 430, 568, 470, "Figure 4. Hybrid mask overview."),
        ),
    )

    match = find_figure_caption([page], figure_record(number=4, caption="Hybrid mask overview."))

    assert match is None


@pytest.mark.parametrize(
    ("caption_left", "caption_right", "expected_side"),
    [(35, 285, "left"), (320, 570, "right")],
)
def test_crop_plan_uses_caption_column_for_single_column_figure(
    caption_left: float,
    caption_right: float,
    expected_side: str,
):
    caption = text_block(caption_left, 430, caption_right, 470, "Figure 3. Hybrid mask.")
    page = PageLayout(
        number=2,
        width=612,
        height=792,
        blocks=(text_block(caption_left, 72, caption_right, 110, "body text"), caption),
    )

    crop = plan_figure_crop(figure_record(number=3), page, caption)

    assert crop.accepted is True
    assert crop.bottom <= caption.top
    assert crop.confidence >= 0.7
    if expected_side == "left":
        assert crop.right < page.width / 2
    else:
        assert crop.left > page.width / 2


def test_crop_plan_uses_full_width_for_figure_star():
    caption = text_block(40, 440, 572, 475, "Figure 2. Wide architecture.")
    page = PageLayout(number=1, width=612, height=792, blocks=(caption,))

    crop = plan_figure_crop(
        figure_record(number=2, layout="double-column", caption="Wide architecture."),
        page,
        caption,
    )

    assert crop.accepted is True
    assert crop.left < 50
    assert crop.right > 562
    assert crop.right - crop.left > 500


def test_crop_plan_uses_table_caption_as_upper_boundary():
    table_caption = text_block(40, 330, 572, 355, "Table 9. Main implementation and training hyperparameters.")
    caption = text_block(40, 680, 572, 720, "Figure 5. Qualitative closed-loop comparisons.")
    page = PageLayout(number=12, width=612, height=792, blocks=(table_caption, caption))

    crop = plan_figure_crop(
        figure_record(number=5, layout="double-column", caption="Qualitative closed-loop comparisons."),
        page,
        caption,
    )

    assert crop.accepted is True
    assert crop.top > table_caption.bottom
    assert "preceding-caption-boundary" in crop.reasons
    assert crop.diagnostics["preceding_caption_count"] == 1


def test_crop_plan_rejects_only_continuous_body_text_not_sparse_vector_labels():
    caption = text_block(318, 500, 570, 530, "Figure 5. Planner diagram.")
    sparse_labels = tuple(
        text_block(330 + (index % 2) * 90, 180 + index * 35, 390 + (index % 2) * 90, 195 + index * 35, "Encoder")
        for index in range(7)
    )
    sparse_page = PageLayout(1, 612, 792, (*sparse_labels, caption))

    assert plan_figure_crop(figure_record(number=5), sparse_page, caption).accepted is True

    body = text_block(
        318,
        150,
        570,
        430,
        "This is a continuous paragraph with many words across the column",
        line_count=14,
    )
    heavy_page = PageLayout(1, 612, 792, (body, caption))
    rejected = plan_figure_crop(figure_record(number=5), heavy_page, caption)

    assert rejected.accepted is False
    assert "text-heavy" in rejected.reasons
    assert rejected.diagnostics["body_text_coverage"] > 0.35


def test_pdf_fallback_failure_has_diagnostics_and_never_uses_embedded_image_order(
    tmp_path: Path,
):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"pdf")
    destination = tmp_path / "figure-4.webp"
    commands: list[list[str]] = []

    def run(command: list[str], **kwargs):
        commands.append(command)
        if command[0] == "pdftotext":
            Path(command[-1]).write_text(BBOX_LAYOUT, encoding="utf-8")
            return
        raise subprocess.CalledProcessError(1, command)

    result = crop_pdf_figure_fallback(
        figure_record(number=4, caption="Hybrid mask overview."),
        pdf,
        destination,
        run=run,
    )

    assert result.accepted is False
    assert result.path is None
    assert result.confidence > 0
    assert result.reasons
    assert result.diagnostics["stage"] == "render"
    assert all(command[0] != "pdfimages" for command in commands)
    assert all("figure_01" not in " ".join(command) for command in commands)


def test_resolve_paper_figures_prefers_local_single_source_without_network_or_crop(tmp_path: Path):
    paper = tmp_path / "paper"
    (paper / "img").mkdir(parents=True)
    (paper / "img" / "framework.pdf").write_bytes(b"framework")
    source = paper / "source.tex"
    source.write_text(
        r"""
\begin{figure}
\includegraphics{img/framework.pdf}
\caption{Overview of the framework.}
\label{fig:framework}
\end{figure}
""",
        encoding="utf-8",
    )
    calls: list[str] = []

    def normalizer(src: Path, dst: Path) -> Path:
        calls.append(f"normalize:{src.name}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"webp")
        return dst

    def fetcher(*args, **kwargs):
        raise AssertionError("network should not be used")

    def cropper(*args, **kwargs):
        raise AssertionError("crop should not be used")

    resolved = resolve_paper_figures(
        source_tex=source,
        paper_dir=paper,
        pdf_path=paper / "paper.pdf",
        arxiv_id="2601.00001",
        cache_dir=tmp_path / "cache",
        output_dir=paper / "blog-assets" / "figures",
        normalizer=normalizer,
        source_fetcher=fetcher,
        cropper=cropper,
    )

    assert calls == ["normalize:framework.pdf"]
    assert len(resolved) == 1
    assert resolved[0].source_reference == "img/framework.pdf"
    assert resolved[0].extraction_method == "local_source"
    assert resolved[0].path == paper / "blog-assets" / "figures" / "figure-01.webp"
    assert resolved[0].content_sha256


def test_resolve_paper_figures_downloads_arxiv_once_for_missing_local_asset(tmp_path: Path):
    paper = tmp_path / "paper"
    paper.mkdir()
    source = paper / "source.tex"
    source.write_text(
        r"""
\begin{figure}
\includegraphics{img/framework.pdf}
\caption{Overview of the framework.}
\label{fig:framework}
\end{figure}
""",
        encoding="utf-8",
    )
    archive = write_source_archive(tmp_path, [regular_member("img/framework.pdf", b"pdf")])
    fetch_calls: list[str] = []

    def fetcher(arxiv_id: str, destination: Path) -> Path:
        fetch_calls.append(arxiv_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archive, destination)
        return destination

    def normalizer(src: Path, dst: Path) -> Path:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes() + b"-webp")
        return dst

    resolved = resolve_paper_figures(
        source_tex=source,
        paper_dir=paper,
        pdf_path=None,
        arxiv_id="2601.00001",
        cache_dir=tmp_path / "cache",
        output_dir=paper / "blog-assets" / "figures",
        normalizer=normalizer,
        source_fetcher=fetcher,
    )

    assert fetch_calls == ["2601.00001"]
    assert resolved[0].extraction_method == "arxiv_source"
    assert resolved[0].path.is_file()
    assert "extract-" not in str(resolved[0].path)


def test_resolve_paper_figures_refetches_corrupt_cached_archive(tmp_path: Path):
    paper = tmp_path / "paper"
    paper.mkdir()
    source = paper / "source.tex"
    source.write_text(
        r"""
\begin{figure}
\includegraphics{img/framework.pdf}
\caption{Overview of the framework.}
\label{fig:framework}
\end{figure}
""",
        encoding="utf-8",
    )
    archive = write_source_archive(tmp_path, [regular_member("img/framework.pdf", b"pdf")])
    fetch_calls: list[bool] = []

    def fetcher(_arxiv_id: str, destination: Path) -> Path:
        fetch_calls.append(destination.exists())
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(archive, destination)
        return destination

    def normalizer(src: Path, dst: Path) -> Path:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes() + b"-webp")
        return dst

    cache_dir = tmp_path / "cache"
    archive_cache = hashlib.sha256("2601.00001".encode("utf-8")).hexdigest()[:16]
    corrupt = cache_dir / archive_cache / "source.tar"
    corrupt.parent.mkdir(parents=True)
    corrupt.write_bytes(b"truncated")

    resolved = resolve_paper_figures(
        source_tex=source,
        paper_dir=paper,
        pdf_path=None,
        arxiv_id="2601.00001",
        cache_dir=cache_dir,
        output_dir=paper / "blog-assets" / "figures",
        normalizer=normalizer,
        source_fetcher=fetcher,
    )

    assert fetch_calls == [True, False]
    assert len(resolved) == 1
    assert resolved[0].extraction_method == "arxiv_source"
    assert resolved[0].path.read_bytes() == b"pdf-webp"


def test_resolve_paper_figures_uses_pdf_crop_for_multi_include_composite(tmp_path: Path):
    paper = tmp_path / "paper"
    (paper / "img").mkdir(parents=True)
    (paper / "img" / "left.png").write_bytes(b"left")
    (paper / "img" / "right.png").write_bytes(b"right")
    pdf = paper / "paper.pdf"
    pdf.write_bytes(b"pdf")
    source = paper / "source.tex"
    source.write_text(
        r"""
\begin{figure*}
\includegraphics{img/left.png}
\includegraphics{img/right.png}
\caption{Composite qualitative comparison.}
\label{fig:comparison}
\end{figure*}
""",
        encoding="utf-8",
    )
    normalized_calls: list[Path] = []

    class Result:
        path: Path
        confidence = 0.81
        accepted = True
        reasons = ("double-column",)
        diagnostics = {"stage": "complete"}

        def __init__(self, path: Path) -> None:
            self.path = path

    def normalizer(src: Path, dst: Path) -> Path:
        normalized_calls.append(src)
        dst.write_bytes(b"bad")
        return dst

    def cropper(record: FigureRecord, pdf_path: Path, destination: Path):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"cropped")
        return Result(destination)

    resolved = resolve_paper_figures(
        source_tex=source,
        paper_dir=paper,
        pdf_path=pdf,
        arxiv_id=None,
        cache_dir=tmp_path / "cache",
        output_dir=paper / "blog-assets" / "figures",
        normalizer=normalizer,
        cropper=cropper,
    )

    assert normalized_calls == []
    assert resolved[0].extraction_method == "pdf_crop"
    assert resolved[0].source_reference == ""
    assert resolved[0].path.read_bytes() == b"cropped"
