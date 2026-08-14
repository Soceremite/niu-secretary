from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from airesearch.db import connect, init_db
from airesearch.layout_parser import PARSER_NAME, PARSER_VERSION
from airesearch.layout_service import (
    _expand_figure_bbox_with_supporting_text,
    _nearby_visual_bbox,
    pdf_figure_crop_candidates,
    select_representative_visual,
    visual_candidates,
)
from airesearch.paperpipe_sync import sha256_file, utc_now


def write_png_header(path: Path, width: int, height: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height))


def insert_paper(conn, paper_key: str, paper_dir: Path) -> None:
    now = utc_now()
    conn.execute(
        """
        insert into papers (
            paper_key, title, authors_json, year, venue, ids_json,
            paper_dir, meta_json, created_at, updated_at
        ) values (?, ?, '[]', 2026, '', '{}', ?, '{}', ?, ?)
        """,
        (paper_key, "Layout Service Paper", str(paper_dir), now, now),
    )
    conn.execute(
        """
        insert into paper_cards (
            paper_key, title, source_dir, extractor_version, created_at, updated_at
        ) values (?, ?, ?, 'test', ?, ?)
        """,
        (paper_key, "Layout Service Paper", str(paper_dir), now, now),
    )


def insert_layout_block(
    conn,
    *,
    paper_key: str,
    run_id: int,
    page_index: int,
    block_index: int,
    caption: str,
    asset_path: str,
    structure_path: Path,
) -> None:
    conn.execute(
        """
        insert into paper_layout_blocks (
            paper_key, run_id, page_index, block_index, block_type,
            bbox_json, text, asset_path, metadata_json, created_at
        ) values (?, ?, ?, ?, 'image', '[]', '', ?, ?, ?)
        """,
        (
            paper_key,
            run_id,
            page_index,
            block_index,
            asset_path,
            json.dumps(
                {
                    "caption": caption,
                    "source_path": str(structure_path),
                    "source_reference": f"page={page_index + 1} block={block_index}",
                    "evidence_confidence": 0.83,
                }
            ),
            utc_now(),
        ),
    )


def test_select_representative_visual_prefers_layout_figure_over_stale_cover(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_key = "paper-a"
    paper_dir = tmp_path / "papers" / paper_key
    paper_dir.mkdir(parents=True)
    write_png_header(paper_dir / "cover.webp", 800, 90)

    layout_dir = tmp_path / "layout" / paper_key / "run"
    structure_path = layout_dir / "paper_layout.json"
    structure_path.parent.mkdir(parents=True)
    structure_path.write_text("{}", encoding="utf-8")
    write_png_header(layout_dir / "assets" / "figure-1.png", 2400, 520)
    write_png_header(layout_dir / "assets" / "figure-2.png", 2400, 760)

    init_db(db_path)
    with connect(db_path) as conn:
        insert_paper(conn, paper_key, paper_dir)
        cursor = conn.execute(
            """
            insert into paper_layout_runs (
                paper_key, provider, provider_version, backend, method, status,
                input_pdf_path, output_dir, artifact_json, stats_json, started_at, finished_at
            ) values (?, ?, ?, 'pymupdf', 'native', 'completed', '', ?, '{}', '{}', ?, ?)
            """,
            (paper_key, PARSER_NAME, PARSER_VERSION, str(layout_dir), utc_now(), utc_now()),
        )
        run_id = int(cursor.lastrowid)
        insert_layout_block(
            conn,
            paper_key=paper_key,
            run_id=run_id,
            page_index=0,
            block_index=2,
            caption="Figure 1. Text-heavy teaser.",
            asset_path="assets/figure-1.png",
            structure_path=structure_path,
        )
        insert_layout_block(
            conn,
            paper_key=paper_key,
            run_id=run_id,
            page_index=2,
            block_index=4,
            caption="Figure 2. System overview.",
            asset_path="assets/figure-2.png",
            structure_path=structure_path,
        )
        conn.commit()

    selected = select_representative_visual(
        db_path,
        paper_key,
        source_dir=paper_dir,
        cover_names=("cover.webp",),
    )

    assert selected is not None
    assert selected.source_kind == "layout_block"
    assert selected.source_path.name == "figure-2.png"
    assert "Figure 2" in selected.caption


def test_visual_candidates_rank_source_figures_before_cover_fallback(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    source_dir = tmp_path / "papers" / "paper-b"
    write_png_header(source_dir / "cover.webp", 640, 120)
    write_png_header(source_dir / "figures" / "figure_01.png", 2400, 552)
    write_png_header(source_dir / "figures" / "figure_02.png", 2400, 754)
    write_png_header(source_dir / "figures" / "figure_04.png", 2400, 1617)
    init_db(db_path)

    candidates = visual_candidates(
        db_path,
        "paper-b",
        source_dir=source_dir,
        cover_names=("cover.webp",),
    )

    assert candidates[0].source_kind == "source_figure"
    assert candidates[0].source_path.name == "figure_02.png"
    assert all(candidate.source_kind != "cover_fallback" for candidate in candidates[:2])


def test_nearby_visual_bbox_expands_caption_linked_composite_layers():
    visuals = [
        {"bbox": [80, 64, 249, 203], "figure_number": 1},
        {"bbox": [178, 64, 246, 110], "figure_number": 1},
        {"bbox": [151, 82, 206, 110], "figure_number": 1},
        {"bbox": [124, 105, 165, 126], "figure_number": 1},
        {"bbox": [93, 145, 135, 165], "figure_number": 1},
        {"bbox": [268, 64, 541, 177], "figure_number": 1},
    ]
    for row in range(2):
        for column in range(5):
            left = 73 + column * 93
            top = 189 + row * 53
            visuals.append(
                {
                    "bbox": [left, top, left + 92, top + 52],
                    "figure_number": 1,
                }
            )

    crop_bbox, fragment_count = _nearby_visual_bbox(
        visuals,
        [70, 335, 542, 410],
        figure_number=1,
    )

    assert crop_bbox == [73, 64, 541, 294]
    assert fragment_count == 16


def test_nearby_visual_bbox_includes_overlapping_uncaptioned_panel():
    visuals = [
        {"bbox": [70, 80, 240, 180], "figure_number": 2},
        {"bbox": [250, 90, 430, 170], "figure_number": 2},
        {"bbox": [420, 72, 560, 150], "figure_number": None},
    ]

    crop_bbox, fragment_count = _nearby_visual_bbox(
        visuals,
        [70, 205, 560, 232],
        figure_number=2,
    )

    assert crop_bbox == [70, 72, 560, 180]
    assert fragment_count == 3


def test_figure_crop_includes_short_labels_before_caption_boundary():
    expanded = _expand_figure_bbox_with_supporting_text(
        [70, 80, 240, 180],
        [
            {"bbox": [72, 181, 236, 192], "text": "Input Video Sequence"},
            {"bbox": [72, 196, 236, 215], "text": "(a) Overview of the proposed method."},
            {"bbox": [72, 218, 236, 240], "text": "Figure 1: Actual caption."},
        ],
        caption_top=218,
    )

    assert expanded == [70, 80, 240, 215]


def test_fragmented_layout_layers_use_pdf_figure_crop_candidate(tmp_path: Path):
    fitz = pytest.importorskip("fitz")
    db_path = tmp_path / "airesearch.sqlite3"
    paper_key = "paper-c"
    paper_dir = tmp_path / "papers" / paper_key
    paper_dir.mkdir(parents=True)
    pdf_path = paper_dir / "paper.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.draw_rect(fitz.Rect(90, 95, 520, 380), color=(0.15, 0.45, 0.95), fill=(0.85, 0.92, 1.0))
    page.insert_text((120, 210), "Complete composite figure", fontsize=24)
    page.insert_text((70, 430), "Figure 1. Composite architecture with many vector layers.", fontsize=10)
    doc.save(pdf_path)
    doc.close()
    write_png_header(paper_dir / "figures" / "figure_01.png", 2400, 1900)

    init_db(db_path)
    with connect(db_path) as conn:
        insert_paper(conn, paper_key, paper_dir)
        now = utc_now()
        conn.execute(
            """
            insert into paper_artifacts (
                paper_key, artifact_type, path, sha256, size_bytes, updated_at
            ) values (?, 'paper_pdf', ?, ?, ?, ?)
            """,
            (paper_key, str(pdf_path), sha256_file(pdf_path), pdf_path.stat().st_size, now),
        )
        cursor = conn.execute(
            """
            insert into paper_layout_runs (
                paper_key, provider, provider_version, backend, method, status,
                input_pdf_path, output_dir, artifact_json, stats_json, started_at, finished_at
            ) values (?, ?, ?, 'pymupdf', 'native', 'completed', ?, ?, '{}', '{}', ?, ?)
            """,
            (paper_key, PARSER_NAME, PARSER_VERSION, str(pdf_path), str(tmp_path / "layout"), now, now),
        )
        run_id = int(cursor.lastrowid)
        for index in range(9):
            left = 95 + index * 8
            conn.execute(
                """
                insert into paper_layout_blocks (
                    paper_key, run_id, page_index, block_index, block_type,
                    bbox_json, text, asset_path, metadata_json, created_at
                ) values (?, ?, 0, ?, 'image', ?, '', ?, ?, ?)
                """,
                (
                    paper_key,
                    run_id,
                    index,
                    json.dumps([left, 100, left + 36, 360]),
                    f"assets/layer-{index}.png",
                    json.dumps(
                        {
                            "caption": "Figure 1. Composite architecture with many vector layers.",
                            "source_reference": f"page=1 block={index}",
                            "evidence_confidence": 0.82,
                        }
                    ),
                    now,
                ),
            )
        conn.execute(
            """
            insert into paper_layout_blocks (
                paper_key, run_id, page_index, block_index, block_type,
                bbox_json, text, asset_path, metadata_json, created_at
            ) values (?, ?, 0, 20, 'text', ?, ?, '', ?, ?)
            """,
            (
                paper_key,
                run_id,
                json.dumps([70, 420, 540, 455]),
                "Figure 1. Composite architecture with many vector layers.",
                json.dumps({"caption_kind": "figure", "evidence_kind": "caption"}),
                now,
            ),
        )
        conn.commit()

    crop_candidates = pdf_figure_crop_candidates(db_path, paper_key, source_dir=paper_dir)
    selected = select_representative_visual(db_path, paper_key, source_dir=paper_dir, cover_names=("cover.webp",))

    assert len(crop_candidates) == 1
    assert crop_candidates[0].source_path.exists()
    assert selected is not None
    assert selected.source_kind == "pdf_figure_crop"
    assert selected.source_path == crop_candidates[0].source_path
    assert crop_candidates[0].dimensions is not None
    assert crop_candidates[0].dimensions.width > 1000


def test_pdf_caption_window_recovers_vector_figure_without_image_blocks(tmp_path: Path):
    fitz = pytest.importorskip("fitz")
    db_path = tmp_path / "airesearch.sqlite3"
    paper_key = "paper-d"
    paper_dir = tmp_path / "papers" / paper_key
    paper_dir.mkdir(parents=True)
    pdf_path = paper_dir / "paper.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.draw_rect(fitz.Rect(82, 115, 532, 360), color=(0.1, 0.35, 0.9), fill=(0.86, 0.92, 1.0))
    page.draw_line(fitz.Point(150, 240), fitz.Point(464, 240), color=(0.9, 0.2, 0.15), width=4)
    page.insert_text((210, 235), "Vector-only Figure 1", fontsize=22)
    page.insert_text((75, 408), "Figure 1. Vector architecture rendered directly by PDF.", fontsize=10)
    doc.save(pdf_path)
    doc.close()

    init_db(db_path)
    with connect(db_path) as conn:
        insert_paper(conn, paper_key, paper_dir)
        now = utc_now()
        conn.execute(
            """
            insert into paper_artifacts (
                paper_key, artifact_type, path, sha256, size_bytes, updated_at
            ) values (?, 'paper_pdf', ?, ?, ?, ?)
            """,
            (paper_key, str(pdf_path), sha256_file(pdf_path), pdf_path.stat().st_size, now),
        )
        cursor = conn.execute(
            """
            insert into paper_layout_runs (
                paper_key, provider, provider_version, backend, method, status,
                input_pdf_path, output_dir, artifact_json, stats_json, started_at, finished_at
            ) values (?, ?, ?, 'pymupdf', 'native', 'completed', ?, ?, '{}', '{}', ?, ?)
            """,
            (paper_key, PARSER_NAME, PARSER_VERSION, str(pdf_path), str(tmp_path / "layout"), now, now),
        )
        run_id = int(cursor.lastrowid)
        conn.execute(
            """
            insert into paper_layout_blocks (
                paper_key, run_id, page_index, block_index, block_type,
                bbox_json, text, asset_path, metadata_json, created_at
            ) values (?, ?, 0, 3, 'text', ?, ?, '', ?, ?)
            """,
            (
                paper_key,
                run_id,
                json.dumps([75, 398, 545, 425]),
                "Figure 1. Vector architecture rendered directly by PDF.",
                json.dumps({"caption_kind": "figure", "evidence_kind": "caption"}),
                now,
            ),
        )
        conn.commit()

    crop_candidates = pdf_figure_crop_candidates(db_path, paper_key, source_dir=paper_dir)
    selected = select_representative_visual(db_path, paper_key, source_dir=paper_dir, cover_names=("cover.webp",))

    assert len(crop_candidates) == 1
    assert crop_candidates[0].source_path.exists()
    assert crop_candidates[0].source_reference == "pdf page=1 figure=1 caption_window"
    assert selected is not None
    assert selected.source_kind == "pdf_figure_crop"


def test_pdf_caption_window_beats_partial_layout_asset(tmp_path: Path):
    fitz = pytest.importorskip("fitz")
    db_path = tmp_path / "airesearch.sqlite3"
    paper_key = "paper-e"
    paper_dir = tmp_path / "papers" / paper_key
    paper_dir.mkdir(parents=True)
    pdf_path = paper_dir / "paper.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.draw_rect(fitz.Rect(82, 116, 532, 358), color=(0.05, 0.25, 0.7), fill=(0.86, 0.93, 1.0))
    page.draw_line(fitz.Point(130, 235), fitz.Point(470, 235), color=(0.85, 0.15, 0.15), width=5)
    page.insert_text((210, 226), "Full system diagram", fontsize=22)
    page.insert_text((75, 405), "Figure 1. Full system diagram with arrows and modules.", fontsize=10)
    doc.save(pdf_path)
    doc.close()

    layout_dir = tmp_path / "layout" / paper_key / "run"
    structure_path = layout_dir / "paper_layout.json"
    structure_path.parent.mkdir(parents=True)
    structure_path.write_text("{}", encoding="utf-8")
    write_png_header(layout_dir / "assets" / "arrow-only.png", 260, 70)

    init_db(db_path)
    with connect(db_path) as conn:
        insert_paper(conn, paper_key, paper_dir)
        now = utc_now()
        conn.execute(
            """
            insert into paper_artifacts (
                paper_key, artifact_type, path, sha256, size_bytes, updated_at
            ) values (?, 'paper_pdf', ?, ?, ?, ?)
            """,
            (paper_key, str(pdf_path), sha256_file(pdf_path), pdf_path.stat().st_size, now),
        )
        cursor = conn.execute(
            """
            insert into paper_layout_runs (
                paper_key, provider, provider_version, backend, method, status,
                input_pdf_path, output_dir, artifact_json, stats_json, started_at, finished_at
            ) values (?, ?, ?, 'pymupdf', 'native', 'completed', ?, ?, '{}', '{}', ?, ?)
            """,
            (paper_key, PARSER_NAME, PARSER_VERSION, str(pdf_path), str(layout_dir), now, now),
        )
        run_id = int(cursor.lastrowid)
        conn.execute(
            """
            insert into paper_layout_blocks (
                paper_key, run_id, page_index, block_index, block_type,
                bbox_json, text, asset_path, metadata_json, created_at
            ) values (?, ?, 0, 1, 'image', ?, '', ?, ?, ?)
            """,
            (
                paper_key,
                run_id,
                json.dumps([315, 224, 368, 247]),
                "assets/arrow-only.png",
                json.dumps(
                    {
                        "caption": "Figure 1. Full system diagram with arrows and modules.",
                        "source_path": str(structure_path),
                        "source_reference": "page=1 block=1",
                        "evidence_confidence": 0.86,
                    }
                ),
                now,
            ),
        )
        conn.execute(
            """
            insert into paper_layout_blocks (
                paper_key, run_id, page_index, block_index, block_type,
                bbox_json, text, asset_path, metadata_json, created_at
            ) values (?, ?, 0, 4, 'text', ?, ?, '', ?, ?)
            """,
            (
                paper_key,
                run_id,
                json.dumps([75, 395, 545, 422]),
                "Figure 1. Full system diagram with arrows and modules.",
                json.dumps({"caption_kind": "figure", "evidence_kind": "caption"}),
                now,
            ),
        )
        conn.commit()

    candidates = visual_candidates(db_path, paper_key, source_dir=paper_dir, cover_names=("cover.webp",))

    assert candidates[0].source_kind == "pdf_figure_crop"
    assert candidates[0].source_reference == "pdf page=1 figure=1 caption_window"
    assert any(candidate.source_path.name == "arrow-only.png" for candidate in candidates)


def test_pdf_figure_crop_keeps_same_page_figures_separate(tmp_path: Path):
    fitz = pytest.importorskip("fitz")
    db_path = tmp_path / "airesearch.sqlite3"
    paper_key = "paper-same-page"
    paper_dir = tmp_path / "papers" / paper_key
    paper_dir.mkdir(parents=True)
    pdf_path = paper_dir / "paper.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.draw_rect(fitz.Rect(70, 80, 542, 170), color=(0.1, 0.3, 0.8), fill=(0.86, 0.92, 1.0))
    page.insert_text((238, 128), "Figure 1 chart", fontsize=18)
    page.insert_text((70, 195), "Figure 1. Metric trends over time.", fontsize=10)
    page.draw_rect(fitz.Rect(70, 255, 542, 385), color=(0.1, 0.55, 0.25), fill=(0.88, 0.96, 0.9))
    page.insert_text((220, 320), "Figure 2 visual example", fontsize=18)
    page.insert_text((70, 415), "Figure 2. Qualitative visual example.", fontsize=10)
    doc.save(pdf_path)
    doc.close()

    init_db(db_path)
    with connect(db_path) as conn:
        insert_paper(conn, paper_key, paper_dir)
        now = utc_now()
        conn.execute(
            """
            insert into paper_artifacts (
                paper_key, artifact_type, path, sha256, size_bytes, updated_at
            ) values (?, 'paper_pdf', ?, ?, ?, ?)
            """,
            (paper_key, str(pdf_path), sha256_file(pdf_path), pdf_path.stat().st_size, now),
        )
        cursor = conn.execute(
            """
            insert into paper_layout_runs (
                paper_key, provider, provider_version, backend, method, status,
                input_pdf_path, output_dir, artifact_json, stats_json, started_at, finished_at
            ) values (?, ?, ?, 'pymupdf', 'native', 'completed', ?, ?, '{}', '{}', ?, ?)
            """,
            (paper_key, PARSER_NAME, PARSER_VERSION, str(pdf_path), str(tmp_path / "layout"), now, now),
        )
        run_id = int(cursor.lastrowid)
        for figure_number, block_index, image_bbox, caption_bbox, caption in [
            (1, 0, [70, 80, 542, 170], [70, 185, 542, 218], "Figure 1. Metric trends over time."),
            (2, 2, [70, 255, 542, 385], [70, 405, 542, 438], "Figure 2. Qualitative visual example."),
        ]:
            conn.execute(
                """
                insert into paper_layout_blocks (
                    paper_key, run_id, page_index, block_index, block_type,
                    bbox_json, text, asset_path, metadata_json, created_at
                ) values (?, ?, 0, ?, 'image', ?, ?, ?, ?, ?)
                """,
                (
                    paper_key,
                    run_id,
                    block_index,
                    json.dumps(image_bbox),
                    caption,
                    f"assets/figure-{figure_number}.png",
                    json.dumps({"caption": caption, "caption_kind": "figure", "evidence_confidence": 0.86}),
                    now,
                ),
            )
            conn.execute(
                """
                insert into paper_layout_blocks (
                    paper_key, run_id, page_index, block_index, block_type,
                    bbox_json, text, asset_path, metadata_json, created_at
                ) values (?, ?, 0, ?, 'text', ?, ?, '', ?, ?)
                """,
                (
                    paper_key,
                    run_id,
                    block_index + 1,
                    json.dumps(caption_bbox),
                    caption,
                    json.dumps({"caption_kind": "figure", "evidence_kind": "caption"}),
                    now,
                ),
            )
        conn.commit()

    crop_candidates = pdf_figure_crop_candidates(db_path, paper_key, source_dir=paper_dir)
    by_figure = {candidate.source_reference: candidate for candidate in crop_candidates}

    assert len(crop_candidates) == 2
    assert "pdf page=1 figure=1 figure_bbox" in by_figure
    assert "pdf page=1 figure=2 figure_bbox" in by_figure
    figure_1 = by_figure["pdf page=1 figure=1 figure_bbox"]
    figure_2 = by_figure["pdf page=1 figure=2 figure_bbox"]
    assert figure_1.source_path != figure_2.source_path
    assert figure_1.dimensions is not None
    assert figure_2.dimensions is not None
    assert figure_2.dimensions.height > figure_1.dimensions.height
