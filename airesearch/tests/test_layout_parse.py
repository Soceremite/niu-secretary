from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

import pytest

from airesearch.cli import build_parser
from airesearch.config import Settings
from airesearch.db import connect, init_db
from airesearch.formula_ocr import FormulaOCRResult
from airesearch.layout_parse import layout_detail, parse_paper_layout
from airesearch.layout_parser import (
    LayoutParserOptions,
    _apply_reading_order,
    _caption_kind,
    _enrich_page_blocks,
    _looks_like_equation,
    _reconstruct_table_from_words,
    _table_geometry_is_coherent,
    _table_to_html,
    _table_to_markdown,
    parse_pdf_layout,
)
from airesearch.paperpipe_sync import sha256_file, utc_now


def write_sample_pdf(path: Path) -> None:
    import fitz

    tiny_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "Native Layout Parser Smoke Paper", fontsize=18)
    page.insert_text((72, 120), "This paragraph is extracted in reading order.", fontsize=11)
    page.insert_text((72, 170), "accuracy    latency    memory\n91.2        12ms       4GB\n90.1        10ms       3GB", fontsize=10)
    page.insert_text((72, 260), "loss = - log softmax(x) + lambda * ||w||_2", fontsize=11)
    page.insert_image(fitz.Rect(72, 310, 172, 370), stream=tiny_png)
    page.insert_text((72, 390), "Figure 1. Native parser architecture.", fontsize=9)
    doc.save(path)
    doc.close()


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Figure 2 presents an overview of the method.", ""),
        ("Fig. 1: Failure cases.", "figure"),
        ("Fig. 1: Failure cases of the state-of-the-art VTS model Go-\nMatching++.", "figure"),
        ("Figure 2 Overview of the method.", "figure"),
        ("TABLE III: Ablation results.", "table"),
    ],
)
def test_caption_kind_distinguishes_captions_from_inline_figure_references(text: str, expected: str):
    assert _caption_kind(text) == expected


def write_margin_noise_pdf(path: Path) -> None:
    import fitz

    doc = fitz.open()
    for index in range(2):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 26), "Proceedings Header Should Disappear", fontsize=8)
        page.insert_text((72, 760), "Footer Copyright Should Disappear", fontsize=8)
        page.insert_text((300, 776), str(index + 1), fontsize=8)
        page.insert_text((72, 96), f"Section {index + 1}. Important Body Text", fontsize=15)
        page.insert_text((72, 132), f"Body paragraph {index + 1} should stay in markdown output.", fontsize=11)
    doc.save(path)
    doc.close()


def write_scanned_pdf(path: Path, *, include_digital_page: bool = False) -> None:
    import fitz

    source = fitz.open()
    source_page = source.new_page(width=612, height=792)
    source_page.insert_text((72, 120), "Scanned page visual text", fontsize=24)
    image_bytes = source_page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).tobytes("png")
    source.close()

    doc = fitz.open()
    if include_digital_page:
        digital = doc.new_page(width=612, height=792)
        digital.insert_text((72, 100), "Digital page with a complete selectable text layer for classification.", fontsize=12)
        digital.insert_text((72, 130), "This page must not be sent to OCR in automatic mode.", fontsize=12)
    scanned = doc.new_page(width=612, height=792)
    scanned.insert_image(scanned.rect, stream=image_bytes)
    doc.save(path)
    doc.close()


def write_ruled_table_pdf(path: Path) -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    x_positions = [70, 250, 370, 500]
    y_positions = [100, 130, 160, 190]
    for x in x_positions:
        page.draw_line((x, y_positions[0]), (x, y_positions[-1]))
    for y in y_positions:
        page.draw_line((x_positions[0], y), (x_positions[-1], y))
    rows = [
        ["Method", "Accuracy", "Latency"],
        ["Baseline", "71.2", "18 ms"],
        ["Ours", "", "9 ms"],
    ]
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            if value:
                page.insert_text(
                    (x_positions[column_index] + 5, y_positions[row_index] + 20),
                    value,
                    fontsize=9,
                )
    doc.save(path)
    doc.close()


def write_booktabs_table_pdf(path: Path) -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    x_positions = [72, 230, 276, 322, 368, 414, 460]
    y_positions = [120, 145, 170, 195, 220]
    page.insert_text((72, 103), "Table 1: Dense benchmark results.", fontsize=9)
    page.draw_rect(fitz.Rect(226, 190, 506, 218), color=None, fill=(0.9, 0.95, 0.95), overlay=False)
    page.draw_line((70, 112), (506, 112), width=0.8)
    page.draw_line((70, 137), (506, 137), width=0.5)
    page.draw_line((70, 187), (506, 187), width=0.5)
    page.draw_line((70, 222), (506, 222), width=0.8)
    rows = [
        ["Model", "A", "B", "C", "D", "E", "Score"],
        ["Baseline", "10.0", "20.0", "30.0", "40.0", "50.0", "25.0"],
        ["Adapter", "11.0", "21.0", "31.0", "41.0", "51.0", "26.0"],
        ["Ours", "12.0", "22.0", "32.0", "42.0", "52.0", "27.0"],
    ]
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            page.insert_text((x_positions[column_index], y_positions[row_index]), value, fontsize=8)
    doc.save(path)
    doc.close()


def write_stacked_booktabs_tables_pdf(path: Path) -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    left, right = 330, 510
    for y, width in [(100, 0.8), (128, 0.5), (170, 0.5), (198, 0.5), (240, 0.8)]:
        page.draw_line((left, y), (right, y), width=width)
    top_rows = [
        [(390, "(a) Warm-up")],
        [(336, "Setting"), (420, "Score"), (466, "Profile"), (500, "Env.")],
        [(336, "Baseline"), (420, "91.2"), (466, "67.1"), (500, "40.4")],
        [(336, "Ours"), (420, "96.0"), (466, "72.9"), (500, "52.2")],
    ]
    bottom_rows = [
        [(390, "(b) Trajectory")],
        [(336, "Setting"), (440, "SV"), (490, "SV-R")],
        [(336, "Baseline"), (440, "91.7"), (490, "92.1")],
        [(336, "Ours"), (440, "96.8"), (490, "97.1")],
    ]
    for baseline, row in zip((116, 140, 153, 166), top_rows):
        for x, value in row:
            page.insert_text((x, baseline), value, fontsize=7)
    for baseline, row in zip((186, 210, 223, 236), bottom_rows):
        for x, value in row:
            page.insert_text((x, baseline), value, fontsize=7)
    page.insert_textbox(
        fitz.Rect(72, 100, 310, 240),
        "This prose remains outside the two compact tables. It must never be merged into their cells. " * 3,
        fontsize=9,
    )
    doc.save(path)
    doc.close()


def table_word(x0: float, y0: float, x1: float, y1: float, text: str, line_no: int) -> tuple:
    return (x0, y0, x1, y1, text, 0, line_no, 0)


def layout_block(text: str, bbox: list[float], *, block_type: str = "text", block_index: int = 0) -> dict:
    return {
        "type": block_type,
        "page_index": 0,
        "block_index": block_index,
        "bbox": bbox,
        "text": text,
        "asset_path": "",
        "metadata": {"parser": "airesearch_layout"},
    }


def test_reading_order_uses_cross_column_blocks_as_segment_anchors():
    blocks = [
        layout_block("left before figure", [72, 100, 260, 135], block_index=0),
        layout_block("left after figure", [72, 330, 260, 365], block_index=1),
        layout_block("right before figure", [330, 110, 520, 145], block_index=2),
        layout_block("wide figure", [80, 240, 540, 300], block_type="image", block_index=3),
        layout_block("right after figure", [330, 340, 520, 375], block_index=4),
    ]

    ordered, stats = _apply_reading_order(blocks, page_width=612, page_height=792)

    assert [block["text"] for block in ordered] == [
        "left before figure",
        "right before figure",
        "wide figure",
        "left after figure",
        "right after figure",
    ]
    assert stats["method"] == "geometry_columns_v2"
    assert stats["multi_column"] is True
    assert stats["cross_column_blocks"] == 1
    assert all(block["metadata"]["reading_order_method"] == "geometry_columns_v2" for block in ordered)
    assert [block["metadata"]["reading_order_index"] for block in ordered] == [0, 1, 2, 3, 4]
    assert ordered[2]["metadata"]["reading_order_region"] == "full_width"


def test_reading_order_keeps_caption_adjacent_to_visual_block():
    image = layout_block("", [330, 160, 510, 250], block_type="image", block_index=0)
    caption = layout_block("Figure 1. Right column system.", [330, 258, 510, 282], block_index=1)
    image["metadata"]["caption_block_index"] = 1
    blocks = [
        layout_block("left paragraph", [72, 120, 260, 150], block_index=2),
        caption,
        layout_block("right paragraph", [330, 110, 510, 138], block_index=3),
        image,
    ]

    ordered, stats = _apply_reading_order(blocks, page_width=612, page_height=792)

    texts = [block["text"] for block in ordered]
    assert texts.index("") + 1 == texts.index("Figure 1. Right column system.")
    assert stats["caption_paired_blocks"] == 1
    assert "caption-paired" in ordered[texts.index("")]["metadata"]["reading_order_reasons"]


def test_geometry_table_reconstruction_preserves_sparse_cells_and_uneven_spacing():
    words = [
        table_word(72, 100, 112, 112, "Method", 0),
        table_word(248, 100, 302, 112, "Accuracy", 0),
        table_word(430, 100, 474, 112, "Latency", 0),
        table_word(72, 126, 124, 138, "Baseline", 1),
        table_word(265, 126, 290, 138, "71.2", 1),
        table_word(426, 126, 463, 138, "18 ms", 1),
        table_word(72, 152, 101, 164, "Ours", 2),
        table_word(432, 152, 463, 164, "9 ms", 2),
    ]

    result = _reconstruct_table_from_words(words, [60, 90, 500, 176])

    assert result["table_rows"] == [
        ["Method", "Accuracy", "Latency"],
        ["Baseline", "71.2", "18 ms"],
        ["Ours", "", "9 ms"],
    ]
    assert result["column_count"] == 3
    assert result["row_count"] == 3
    assert result["header_row_count"] == 1
    assert result["reconstruction_method"] == "word_geometry_v2"
    assert result["reconstruction_confidence"] >= 0.8
    assert not any(cell["row"] == 2 and cell["column"] == 1 for cell in result["table_cells"])


def test_geometry_table_reconstruction_separates_dense_numeric_columns():
    words = []
    for row_index, values in enumerate(
        [
            ["Model", "A", "B", "C", "D", "E", "F", "G", "H", "Score"],
            ["Baseline", "11.0", "22.0", "33.0", "44.0", "55.0", "66.0", "77.0", "88.0", "49.5"],
            ["Ours", "12.0", "23.0", "34.0", "45.0", "56.0", "67.0", "78.0", "89.0", "50.5"],
        ]
    ):
        x = 72.0
        for column_index, value in enumerate(values):
            width = 36.0 if column_index == 0 else 15.0
            words.append(table_word(x, 100 + row_index * 20, x + width, 110 + row_index * 20, value, row_index))
            x += 42.0 if column_index == 0 else 20.7

    result = _reconstruct_table_from_words(words, [68, 94, 310, 154])

    assert result["column_count"] == 10
    assert result["table_rows"][1] == ["Baseline", "11.0", "22.0", "33.0", "44.0", "55.0", "66.0", "77.0", "88.0", "49.5"]


def test_geometry_table_reconstruction_marks_multirow_header_and_spanning_cell():
    words = [
        table_word(220, 90, 470, 102, "Evaluation Results", 0),
        table_word(72, 112, 112, 124, "Method", 1),
        table_word(248, 112, 302, 124, "Accuracy", 1),
        table_word(430, 112, 474, 124, "Latency", 1),
        table_word(72, 138, 124, 150, "Baseline", 2),
        table_word(265, 138, 290, 150, "71.2", 2),
        table_word(426, 138, 463, 150, "18 ms", 2),
        table_word(72, 164, 101, 176, "Ours", 3),
        table_word(263, 164, 290, 176, "78.4", 3),
        table_word(432, 164, 463, 176, "9 ms", 3),
    ]

    result = _reconstruct_table_from_words(words, [60, 80, 500, 188])

    assert result["table_rows"][0] == ["", "Evaluation Results", ""]
    assert result["table_rows"][1] == ["Method", "Accuracy", "Latency"]
    assert result["header_row_count"] == 2
    spanning = next(cell for cell in result["table_cells"] if cell["text"] == "Evaluation Results")
    assert spanning["column"] == 1
    assert spanning["column_span"] == 2
    assert result["has_spanning_cells"] is True
    markdown = _table_to_markdown(
        result["table_rows"],
        header_row_count=result["header_row_count"],
        cells=result["table_cells"],
    )
    html = _table_to_html(
        result["table_rows"],
        header_row_count=result["header_row_count"],
        cells=result["table_cells"],
    )
    assert "Evaluation Results / Accuracy" in markdown
    assert '<th colspan="2">Evaluation Results</th>' in html


def test_table_enrichment_keeps_text_spacing_fallback_when_geometry_is_unavailable():
    block = {
        "type": "table",
        "page_index": 0,
        "block_index": 2,
        "bbox": [72.0, 100.0, 300.0, 150.0],
        "text": "Method\tScore\nBaseline\t71.2\nOurs\t78.4",
        "asset_path": "",
        "metadata": {"parser": "airesearch_layout"},
    }

    enriched = _enrich_page_blocks([block], page_height=792.0)[0]

    metadata = enriched["metadata"]
    assert metadata["table_reconstruction_method"] == "text_spacing_v1"
    assert metadata["table_reconstruction_confidence"] == 0.62
    assert metadata["table_rows"] == [["Method", "Score"], ["Baseline", "71.2"], ["Ours", "78.4"]]
    assert all(cell["bbox"] == [] for cell in metadata["table_cells"])
    assert "text-spacing-fallback" in metadata["quality_reasons"]


def test_layout_parser_reconstructs_ruled_table_region_with_sparse_cell(tmp_path: Path):
    pdf_path = tmp_path / "ruled-table.pdf"
    write_ruled_table_pdf(pdf_path)

    result = parse_pdf_layout(pdf_path, LayoutParserOptions(output_dir=tmp_path / "layout"))

    structure = json.loads(result.structure_json_files[0].read_text(encoding="utf-8"))
    summary = json.loads(result.summary_files[0].read_text(encoding="utf-8"))
    tables = [block for page in structure["pages"] for block in page["blocks"] if block["type"] == "table"]
    assert len(tables) == 1
    metadata = tables[0]["metadata"]
    assert metadata["table_rows"] == [
        ["Method", "Accuracy", "Latency"],
        ["Baseline", "71.2", "18 ms"],
        ["Ours", "", "9 ms"],
    ]
    assert metadata["table_reconstruction_method"] == "pymupdf_table_lines"
    assert metadata["table_reconstruction_confidence"] >= 0.9
    assert metadata["table_cells"]
    assert summary["geometry_table_blocks"] == 1
    assert summary["text_fallback_table_blocks"] == 0


def test_layout_parser_reconstructs_complete_booktabs_table_instead_of_colored_fragment(tmp_path: Path):
    pdf_path = tmp_path / "booktabs-table.pdf"
    write_booktabs_table_pdf(pdf_path)

    result = parse_pdf_layout(pdf_path, LayoutParserOptions(output_dir=tmp_path / "layout"))

    structure = json.loads(result.structure_json_files[0].read_text(encoding="utf-8"))
    tables = [block for page in structure["pages"] for block in page["blocks"] if block["type"] == "table"]
    structured = [table for table in tables if table["metadata"].get("table_rows")]
    assert len(structured) == 1
    metadata = structured[0]["metadata"]
    assert metadata["table_reconstruction_method"] == "booktabs_geometry_v1"
    assert metadata["table_rows"] == [
        ["Model", "A", "B", "C", "D", "E", "Score"],
        ["Baseline", "10.0", "20.0", "30.0", "40.0", "50.0", "25.0"],
        ["Adapter", "11.0", "21.0", "31.0", "41.0", "51.0", "26.0"],
        ["Ours", "12.0", "22.0", "32.0", "42.0", "52.0", "27.0"],
    ]


def test_layout_parser_splits_stacked_booktabs_subtables(tmp_path: Path):
    pdf_path = tmp_path / "stacked-booktabs.pdf"
    write_stacked_booktabs_tables_pdf(pdf_path)

    result = parse_pdf_layout(pdf_path, LayoutParserOptions(output_dir=tmp_path / "layout"))

    structure = json.loads(result.structure_json_files[0].read_text(encoding="utf-8"))
    tables = [
        block
        for page in structure["pages"]
        for block in page["blocks"]
        if block["type"] == "table" and block["metadata"].get("table_rows")
    ]
    assert len(tables) == 2
    assert [table["metadata"]["column_count"] for table in tables] == [4, 3]
    assert all(table["metadata"]["table_reconstruction_method"] == "booktabs_geometry_v1" for table in tables)


def test_table_geometry_rejects_collapsed_prose_rows():
    geometry = {
        "column_count": 6,
        "table_rows": [
            ["A long prose sentence was incorrectly captured as a table row", "", "", "", "", ""],
            ["Another explanatory paragraph continues in the first column", "", "", "", "", ""],
            ["A third prose line still does not belong to this table", "", "", "", "", ""],
            ["Setting", "", "", "", "SV", "SV-R"],
            ["Baseline", "", "", "", "91.7", "92.1"],
            ["Ours", "", "", "", "96.8", "97.1"],
        ],
    }

    assert _table_geometry_is_coherent(geometry) is False


def test_equation_classifier_rejects_non_math_layout_labels():
    assert _looks_like_equation("x_t = f(x_{t-1})") is True
    assert _looks_like_equation("Initial frame X0\nT = 1s\nT = 3s\nT = 5s") is False
    assert _looks_like_equation("Table 4: Dataset composition. AD = Autonomous Driving.") is False
    assert _looks_like_equation("in psychology, 3(2):77-101, 2006.") is False


def insert_paper(conn, tmp_path: Path, paper_key: str = "paper-1") -> Path:
    paper_dir = tmp_path / "paperpipe" / "papers" / paper_key
    paper_dir.mkdir(parents=True)
    pdf_path = paper_dir / "paper.pdf"
    write_sample_pdf(pdf_path)
    now = utc_now()
    conn.execute(
        """
        insert into papers (
            paper_key, title, authors_json, year, venue, ids_json,
            paper_dir, meta_json, created_at, updated_at
        ) values (?, ?, '[]', 2026, '', '{}', ?, '{}', ?, ?)
        """,
        (paper_key, "Layout Paper", str(paper_dir), now, now),
    )
    conn.execute(
        """
        insert into paper_artifacts (
            paper_key, artifact_type, path, sha256, size_bytes, updated_at
        ) values (?, 'paper_pdf', ?, ?, ?, ?)
        """,
        (paper_key, str(pdf_path), sha256_file(pdf_path), pdf_path.stat().st_size, now),
    )
    return pdf_path


def test_layout_schema_tables_exist(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    with connect(db_path) as conn:
        tables = {row["name"] for row in conn.execute("select name from sqlite_master where type = 'table'")}
    assert "paper_layout_runs" in tables
    assert "paper_layout_blocks" in tables


def test_settings_reads_layout_environment(tmp_path: Path):
    settings = Settings.from_env(
        {
            "PAPER_DB_PATH": str(tmp_path / "paperpipe"),
            "AIRESEARCH_DB_PATH": str(tmp_path / "db.sqlite3"),
            "AIRESEARCH_LAYOUT_OUTPUT_DIR": str(tmp_path / "layout-out"),
            "AIRESEARCH_LAYOUT_MAX_PAGES": "3",
            "AIRESEARCH_LAYOUT_OCR_MODE": "force",
            "AIRESEARCH_LAYOUT_OCR_LANGUAGES": "eng",
            "AIRESEARCH_LAYOUT_OCR_DPI": "240",
            "AIRESEARCH_LAYOUT_OCR_EXECUTABLE": "/usr/bin/tesseract",
            "AIRESEARCH_FORMULA_OCR_MODE": "auto",
            "AIRESEARCH_FORMULA_OCR_DPI": "280",
            "AIRESEARCH_FORMULA_OCR_MIN_CONFIDENCE": "0.82",
        },
        project_root=tmp_path,
    )
    assert settings.layout_output_dir == tmp_path / "layout-out"
    assert settings.layout_max_pages == 3
    assert settings.layout_ocr_mode == "force"
    assert settings.layout_ocr_languages == "eng"
    assert settings.layout_ocr_dpi == 240
    assert settings.layout_ocr_executable == "/usr/bin/tesseract"
    assert settings.layout_formula_ocr_mode == "auto"
    assert settings.layout_formula_ocr_dpi == 280
    assert settings.layout_formula_ocr_min_confidence == 0.82


def test_native_pdf_layout_parser_writes_structured_outputs(tmp_path: Path):
    pdf_path = tmp_path / "paper.pdf"
    write_sample_pdf(pdf_path)

    result = parse_pdf_layout(pdf_path, LayoutParserOptions(output_dir=tmp_path / "layout"))

    assert len(result.markdown_files) == 1
    assert len(result.content_list_files) == 1
    assert len(result.structure_json_files) == 1
    assert len(result.debug_json_files) == 1
    assert len(result.summary_files) == 1
    structure = json.loads(result.structure_json_files[0].read_text(encoding="utf-8"))
    assert structure["parser"] == "airesearch_layout"
    blocks = [block for page in structure["pages"] for block in page["blocks"]]
    block_types = {block["type"] for block in blocks}
    assert "title" in block_types
    assert "text" in block_types
    assert "table" in block_types or "interline_equation" in block_types
    summary = json.loads(result.summary_files[0].read_text(encoding="utf-8"))
    assert summary["parser_version"] == "v2"
    assert summary["evidence_ready_blocks"] >= 2
    assert summary["equation_blocks"] >= 1
    assert any(block["type"] == "image" and block["metadata"].get("caption") for block in blocks)
    assert any(block["type"] == "interline_equation" and block["metadata"].get("equation_id") for block in blocks)
    assert any(block["type"] == "table" and block["metadata"].get("table_rows") for block in blocks)
    evidence_blocks = [block for block in blocks if block["metadata"].get("evidence_kind")]
    assert evidence_blocks
    assert all(isinstance(block["metadata"].get("quality_score"), float) for block in evidence_blocks)
    assert all(block["metadata"].get("quality_reasons") for block in evidence_blocks)
    assert any(block["metadata"].get("quality_score", 0) >= 0.72 for block in evidence_blocks)
    table_blocks = [block for block in blocks if block["type"] == "table" and block["metadata"].get("table_rows")]
    assert table_blocks
    assert table_blocks[0]["metadata"]["quality_score"] >= 0.82
    assert table_blocks[0]["metadata"]["table_markdown"].startswith("|")
    assert table_blocks[0]["metadata"]["table_html"].startswith("<table>")
    assert table_blocks[0]["metadata"]["table_cells"]
    assert table_blocks[0]["metadata"]["table_reconstruction_method"] == "word_geometry_v2"
    assert table_blocks[0]["metadata"]["table_reconstruction_confidence"] >= 0.8
    equation_blocks = [block for block in blocks if block["type"] == "interline_equation"]
    assert equation_blocks[0]["metadata"]["quality_score"] >= 0.72
    assert "math-signal" in equation_blocks[0]["metadata"]["quality_reasons"]
    assert summary["high_quality_evidence_blocks"] >= 2
    assert summary["geometry_table_blocks"] >= 1
    assert summary["text_fallback_table_blocks"] == 0
    assert summary["reading_order"]["method"] == "geometry_columns_v2"
    assert summary["reading_order"]["pages_completed"] == 1
    assert summary["reading_order"]["average_confidence"] >= 0.72
    assert all("reading_order_index" in block["metadata"] for block in blocks)
    markdown = result.markdown_files[0].read_text(encoding="utf-8")
    assert "| accuracy | latency | memory |" in markdown


def test_layout_parser_detects_digital_pdf_without_running_ocr(tmp_path: Path, monkeypatch):
    pdf_path = tmp_path / "digital.pdf"
    write_sample_pdf(pdf_path)

    def fail_ocr(*_args, **_kwargs):
        raise AssertionError("digital PDF should not invoke OCR in auto mode")

    monkeypatch.setattr("airesearch.layout_parser._ocr_page_with_tesseract", fail_ocr)
    result = parse_pdf_layout(
        pdf_path,
        LayoutParserOptions(output_dir=tmp_path / "layout", ocr_mode="auto"),
    )

    summary = json.loads(result.summary_files[0].read_text(encoding="utf-8"))
    assert summary["document_type"] == "digital"
    assert summary["ocr"]["pages_attempted"] == 0
    assert summary["ocr"]["block_count"] == 0


def test_layout_parser_runs_ocr_for_scanned_page(tmp_path: Path, monkeypatch):
    pdf_path = tmp_path / "scanned.pdf"
    write_scanned_pdf(pdf_path)
    calls: list[int] = []

    def fake_ocr(_page, *, page_index, languages, dpi, executable):
        calls.append(page_index)
        assert languages == "eng+chi_sim"
        assert dpi == 220
        assert executable == "tesseract"
        return (
            [{"bbox": [70, 90, 430, 132], "text": "OCR recovered scanned paper text", "confidence": 0.94}],
            {"status": "completed", "engine": "fixture-ocr", "error": ""},
        )

    monkeypatch.setattr("airesearch.layout_parser._ocr_page_with_tesseract", fake_ocr)
    result = parse_pdf_layout(
        pdf_path,
        LayoutParserOptions(output_dir=tmp_path / "layout", ocr_mode="auto"),
    )

    summary = json.loads(result.summary_files[0].read_text(encoding="utf-8"))
    structure = json.loads(result.structure_json_files[0].read_text(encoding="utf-8"))
    blocks = structure["pages"][0]["blocks"]
    markdown = result.markdown_files[0].read_text(encoding="utf-8")
    assert calls == [0]
    assert summary["document_type"] == "scanned"
    assert summary["page_types"] == {"scanned": 1}
    assert summary["ocr"]["pages_attempted"] == 1
    assert summary["ocr"]["pages_succeeded"] == 1
    assert summary["ocr"]["block_count"] == 1
    assert "OCR recovered scanned paper text" in markdown
    assert any(block["metadata"].get("ocr") is True for block in blocks)
    assert any(block["metadata"].get("ocr_engine") == "fixture-ocr" for block in blocks)


def test_layout_parser_marks_mixed_document_and_only_ocrs_scanned_page(tmp_path: Path, monkeypatch):
    pdf_path = tmp_path / "mixed.pdf"
    write_scanned_pdf(pdf_path, include_digital_page=True)
    calls: list[int] = []

    def fake_ocr(_page, *, page_index, languages, dpi, executable):
        calls.append(page_index)
        return ([{"bbox": [50, 80, 450, 120], "text": "Recovered second page", "confidence": 0.9}], {"status": "completed", "engine": "fixture-ocr", "error": ""})

    monkeypatch.setattr("airesearch.layout_parser._ocr_page_with_tesseract", fake_ocr)
    result = parse_pdf_layout(
        pdf_path,
        LayoutParserOptions(output_dir=tmp_path / "layout", ocr_mode="auto"),
    )

    summary = json.loads(result.summary_files[0].read_text(encoding="utf-8"))
    assert calls == [1]
    assert summary["document_type"] == "mixed"
    assert summary["page_types"] == {"digital": 1, "scanned": 1}


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")
def test_layout_parser_real_tesseract_smoke(tmp_path: Path):
    pdf_path = tmp_path / "real-ocr.pdf"
    write_scanned_pdf(pdf_path)

    result = parse_pdf_layout(
        pdf_path,
        LayoutParserOptions(
            output_dir=tmp_path / "layout",
            ocr_mode="auto",
            ocr_languages="eng",
            ocr_dpi=220,
        ),
    )

    summary = json.loads(result.summary_files[0].read_text(encoding="utf-8"))
    markdown = result.markdown_files[0].read_text(encoding="utf-8")
    assert summary["document_type"] == "scanned"
    assert summary["ocr"]["pages_succeeded"] == 1
    assert summary["ocr"]["block_count"] >= 1
    assert "Scanned page visual text" in markdown


def test_layout_parser_formula_ocr_reconstructs_scanned_equation(tmp_path: Path, monkeypatch):
    pdf_path = tmp_path / "scanned-formula.pdf"
    write_scanned_pdf(pdf_path)

    def fake_page_ocr(_page, *, page_index, languages, dpi, executable):
        return (
            [{"bbox": [90, 180, 500, 230], "text": "loss = - log softmax x", "confidence": 0.71}],
            {"status": "completed", "engine": "fixture-ocr", "error": ""},
        )

    class FakeFormulaProvider:
        def recognize(self, image_bytes, *, mime_type, context):
            assert image_bytes.startswith(b"\x89PNG")
            assert mime_type == "image/png"
            assert "softmax" in context
            return FormulaOCRResult(
                latex=r"\mathcal{L}=-\log \operatorname{softmax}(x)",
                confidence=0.94,
                model="fixture-formula-model",
            )

    monkeypatch.setattr("airesearch.layout_parser._ocr_page_with_tesseract", fake_page_ocr)
    monkeypatch.setattr("airesearch.layout_parser._build_formula_ocr_provider", lambda: FakeFormulaProvider())
    result = parse_pdf_layout(
        pdf_path,
        LayoutParserOptions(
            output_dir=tmp_path / "layout",
            ocr_mode="auto",
            formula_ocr_mode="auto",
        ),
    )

    summary = json.loads(result.summary_files[0].read_text(encoding="utf-8"))
    structure = json.loads(result.structure_json_files[0].read_text(encoding="utf-8"))
    equation = next(block for block in structure["pages"][0]["blocks"] if block["type"] == "interline_equation")
    assert equation["text"] == r"\mathcal{L}=-\log \operatorname{softmax}(x)"
    assert equation["metadata"]["formula_ocr"] is True
    assert equation["metadata"]["formula_ocr_source_text"] == "loss = - log softmax x"
    assert equation["metadata"]["formula_ocr_confidence"] == 0.94
    assert equation["metadata"]["formula_ocr_model"] == "fixture-formula-model"
    assert equation["asset_path"].endswith(".png")
    assert (result.output_dir / equation["asset_path"]).exists()
    assert summary["formula_ocr"]["blocks_attempted"] == 1
    assert summary["formula_ocr"]["blocks_succeeded"] == 1


def test_layout_parser_removes_headers_footers_and_page_numbers(tmp_path: Path):
    pdf_path = tmp_path / "margin-noise.pdf"
    write_margin_noise_pdf(pdf_path)

    result = parse_pdf_layout(pdf_path, LayoutParserOptions(output_dir=tmp_path / "layout"))

    markdown = result.markdown_files[0].read_text(encoding="utf-8")
    summary = json.loads(result.summary_files[0].read_text(encoding="utf-8"))
    structure = json.loads(result.structure_json_files[0].read_text(encoding="utf-8"))
    all_text = "\n".join(block.get("text", "") for page in structure["pages"] for block in page["blocks"])
    assert "Important Body Text" in markdown
    assert "Body paragraph 1 should stay" in markdown
    assert "Proceedings Header Should Disappear" not in all_text
    assert "Footer Copyright Should Disappear" not in all_text
    assert summary["removed_margin_blocks"]["header"] >= 2
    assert summary["removed_margin_blocks"]["footer"] >= 2
    assert summary["removed_margin_blocks"]["page_number"] >= 2


def test_parse_paper_layout_records_run_artifacts_and_blocks(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    with connect(db_path) as conn:
        insert_paper(conn, tmp_path)
        conn.commit()
    options = LayoutParserOptions(output_dir=tmp_path / "layout")

    result = parse_paper_layout(db_path=db_path, paper_key="paper-1", options=options, force=True)

    assert result.status == "completed"
    assert result.artifact_count >= 5
    assert result.block_count >= 3
    detail = layout_detail(db_path, "paper-1")
    assert detail["latest_run"]["status"] == "completed"
    assert detail["latest_run"]["provider"] == "airesearch_layout"
    assert detail["api_version"] == "layout-v2"
    assert detail["paper_key"] == "paper-1"
    assert detail["summary"]["parser_version"] == "v2"
    assert detail["capabilities"]["has_markdown"] is True
    assert detail["capabilities"]["has_structure_json"] is True
    assert detail["capabilities"]["has_equations"] is True
    assert detail["capabilities"]["has_geometry_tables"] is True
    assert detail["capabilities"]["has_reading_order"] is True
    artifact_types = {row["artifact_type"] for row in detail["artifacts"]}
    assert "layout_markdown" in artifact_types
    assert "layout_structure_json" in artifact_types
    assert "layout_debug_json" in artifact_types
    assert "layout_summary_json" in artifact_types
    assert "layout_markdown" in detail["artifacts_by_type"]
    assert detail["sample_blocks"][0]["bbox"]
    assert detail["sample_blocks"][0]["source_reference"]
    assert detail["evidence_blocks"]
    assert any(block["metadata"].get("quality_score", 0) >= 0.72 for block in detail["evidence_blocks"])
    assert any(block["block_type"] == "interline_equation" for block in detail["evidence_blocks"])


def test_parse_paper_layout_reuses_completed_run_without_force(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    with connect(db_path) as conn:
        insert_paper(conn, tmp_path)
        conn.commit()
    options = LayoutParserOptions(output_dir=tmp_path / "layout")
    first = parse_paper_layout(db_path=db_path, paper_key="paper-1", options=options, force=True)
    second = parse_paper_layout(db_path=db_path, paper_key="paper-1", options=options, force=False)

    assert second.status == "skipped"
    assert second.run_id == first.run_id


def test_parse_paper_layout_records_failed_run(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    with connect(db_path) as conn:
        insert_paper(conn, tmp_path)
        conn.commit()
    options = LayoutParserOptions(output_dir=tmp_path / "not" / "used")
    pdf_path = tmp_path / "paperpipe" / "papers" / "paper-1" / "paper.pdf"
    pdf_path.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(Exception):
        parse_paper_layout(db_path=db_path, paper_key="paper-1", options=options, force=True)

    detail = layout_detail(db_path, "paper-1")
    assert detail["latest_run"]["status"] == "failed"
    assert detail["latest_run"]["error"]


def test_parse_pdf_layout_raises_for_missing_input(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        parse_pdf_layout(tmp_path / "missing.pdf", LayoutParserOptions(output_dir=tmp_path / "layout"))


def test_cli_layout_commands_parse(tmp_path: Path):
    parser = build_parser()
    args = parser.parse_args(
        [
            "--db",
            str(tmp_path / "db.sqlite3"),
            "parse-layout",
            "--paper-key",
            "paper-1",
            "--force",
            "--layout-output-dir",
            str(tmp_path / "layout"),
            "--max-pages",
            "2",
            "--ocr-mode",
            "force",
            "--ocr-languages",
            "eng",
            "--ocr-dpi",
            "240",
            "--ocr-executable",
            "/usr/bin/tesseract",
            "--formula-ocr-mode",
            "auto",
            "--formula-ocr-dpi",
            "280",
            "--formula-ocr-min-confidence",
            "0.82",
        ]
    )
    assert args.command == "parse-layout"
    assert args.paper_key == "paper-1"
    assert args.force is True
    assert args.layout_output_dir == tmp_path / "layout"
    assert args.max_pages == 2
    assert args.ocr_mode == "force"
    assert args.ocr_languages == "eng"
    assert args.ocr_dpi == 240
    assert args.ocr_executable == "/usr/bin/tesseract"
    assert args.formula_ocr_mode == "auto"
    assert args.formula_ocr_dpi == 280
    assert args.formula_ocr_min_confidence == 0.82

    status_args = parser.parse_args(["layout-status", "--paper-key", "paper-1"])
    assert status_args.command == "layout-status"
    assert status_args.paper_key == "paper-1"
