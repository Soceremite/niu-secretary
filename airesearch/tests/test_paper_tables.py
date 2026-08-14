from pathlib import Path

from airesearch.figure_crop import PageLayout, TextBlock, TextLine, WordBox
from airesearch.paper_tables import (
    TableRecord,
    find_table_caption,
    parse_pdf_table_manifest,
    parse_table_manifest,
    plan_table_crop,
    resolve_paper_tables,
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


def table_record(
    *,
    number: int = 1,
    caption: str = "Open-loop planning results on the nuScenes benchmark.",
    layout: str = "double-column",
    caption_position: str = "below",
) -> TableRecord:
    return TableRecord(
        table_id=f"tab-{number}",
        number=number,
        label=f"tab:{number}",
        layout=layout,
        caption=caption,
        raw_latex="Method & Score \\\\ ColaVLA & 3.48 \\\\",
        section="Experiments",
        subsection="",
        role="experiments",
        score=90,
        caption_position=caption_position,
        evidence=(),
    )


def test_parse_table_manifest_ranks_main_results_and_collects_reference_evidence(tmp_path: Path):
    source = tmp_path / "source.tex"
    source.write_text(
        r"""
\section{Experiments}
\subsection{State-of-the-art Comparison}
\cref{tab:sota} reports the main open-loop planning benchmark comparison.
\begin{table*}[t]
\centering
\begin{tabular}{lcc}
Method & Score & Collision \\
Baseline & 1.00 & 88.6 \\
ColaVLA & \textbf{3.48} & \textbf{36.8} \\
\end{tabular}
\caption{\textbf{Open-loop planning results} on the nuScenes benchmark.}
\label{tab:sota}
\end{table*}

\begin{table}[t]
\caption{Main implementation and training hyperparameters for ColaVLA.}
\begin{tabular}{ll}
Backbone & LLaVA \\
\end{tabular}
\label{tab:hparams}
\end{table}
""",
        encoding="utf-8",
    )

    records = parse_table_manifest(source)

    assert [record.number for record in records] == [1, 2]
    assert records[0].label == "tab:sota"
    assert records[0].layout == "double-column"
    assert records[0].caption.startswith("Open-loop planning results")
    assert records[0].section == "Experiments"
    assert records[0].subsection == "State-of-the-art Comparison"
    assert records[0].role == "experiments"
    assert records[0].score > records[1].score
    assert records[0].caption_position == "below"
    assert [item.kind for item in records[0].evidence] == ["caption", "reference"]
    assert "main open-loop planning benchmark comparison" in records[0].evidence[1].text
    assert records[1].role == "implementation"
    assert records[1].caption_position == "above"


def test_find_caption_and_plan_crop_uses_preceding_caption_boundary():
    page = PageLayout(
        3,
        612,
        792,
        (
            text_block(58, 70, 554, 120, "Table 1. Previous benchmark table."),
            text_block(90, 150, 520, 320, "Method Score Collision ColaVLA 3.48 36.8", line_count=8),
            text_block(58, 350, 554, 380, "Table 2. Open-loop planning results on the nuScenes benchmark."),
        ),
    )
    record = table_record(number=2)

    match = find_table_caption([page], record)
    assert match is not None
    plan = plan_table_crop(record, match.page, match.block)

    assert plan.accepted
    assert plan.page == 3
    assert plan.top >= 120
    assert plan.bottom <= 330
    assert "preceding" not in " ".join(plan.reasons)


def test_resolve_paper_tables_uses_cropper_and_preserves_sorted_records(tmp_path: Path):
    source = tmp_path / "source.tex"
    pdf = tmp_path / "paper.pdf"
    output_dir = tmp_path / "tables"
    pdf.write_bytes(b"%PDF-1.4\n")
    source.write_text(
        r"""
\begin{table}
\caption{Main implementation and training hyperparameters for ColaVLA.}
\begin{tabular}{ll}Backbone & LLaVA \\\end{tabular}
\label{tab:hparams}
\end{table}
\begin{table*}
\begin{tabular}{lc}Method & Score \\ ColaVLA & 3.48 \\\end{tabular}
\caption{Closed-loop simulation results on NeuroNCAP.}
\label{tab:closed}
\end{table*}
""",
        encoding="utf-8",
    )

    def fake_cropper(record: TableRecord, _pdf_path: Path, destination: Path):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(f"table-{record.number}".encode())

        class Result:
            path = destination
            accepted = True
            confidence = 0.91
            reasons = ("fake-crop",)

        return Result()

    resolved = resolve_paper_tables(source_tex=source, pdf_path=pdf, output_dir=output_dir, cropper=fake_cropper)

    assert [table.record.number for table in resolved] == [2, 1]
    assert resolved[0].record.role == "experiments"
    assert resolved[0].path.name == "table-02.webp"
    assert resolved[0].extraction_method == "pdf_table_crop"
    assert resolved[0].content_sha256


def test_resolve_paper_tables_can_fall_back_to_pdf_caption_manifest(tmp_path: Path, monkeypatch):
    pdf = tmp_path / "paper.pdf"
    output_dir = tmp_path / "tables"
    pdf.write_bytes(b"%PDF-1.4\n")
    pdf_record = TableRecord(
        table_id="tab-1",
        number=1,
        label="",
        layout="double-column",
        caption="Open-loop planning results on the nuScenes benchmark.",
        raw_latex="",
        section="",
        subsection="",
        role="experiments",
        score=80,
        caption_position="below",
        evidence=(),
    )

    def fake_manifest(_pdf_path: Path, _work_dir: Path, **_kwargs):
        return [pdf_record]

    def fake_cropper(record: TableRecord, _pdf_path: Path, destination: Path):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(f"table-{record.number}".encode())

        class Result:
            path = destination
            accepted = True
            confidence = 0.88
            reasons = ("pdf-caption",)

        return Result()

    monkeypatch.setattr("airesearch.paper_tables.parse_pdf_table_manifest", fake_manifest)

    resolved = resolve_paper_tables(source_tex=None, pdf_path=pdf, output_dir=output_dir, cropper=fake_cropper)

    assert len(resolved) == 1
    assert resolved[0].record.caption.startswith("Open-loop planning results")
    assert resolved[0].path.name == "table-01.webp"
    assert resolved[0].diagnostics == ("pdf-caption",)
