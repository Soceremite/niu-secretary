from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    project_root: Path
    paper_db_path: Path
    sqlite_path: Path
    papi_executable: str
    layout_output_dir: Path
    layout_max_pages: int | None
    layout_ocr_mode: str
    layout_ocr_languages: str
    layout_ocr_dpi: int
    layout_ocr_executable: str
    layout_formula_ocr_mode: str
    layout_formula_ocr_dpi: int
    layout_formula_ocr_min_confidence: float
    archive_remote: str
    archive_staging_path: Path
    rclone_executable: str
    archive_workers: int
    archive_cache_gb: int

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        project_root: Path | None = None,
    ) -> "Settings":
        values = os.environ if env is None else env
        root = project_root or Path(__file__).resolve().parents[2]
        paper_db_path = Path(values.get("PAPER_DB_PATH", root / "data" / "paperpipe"))
        sqlite_path = Path(values.get("AIRESEARCH_DB_PATH", root / "data" / "airesearch.sqlite3"))
        papi_executable = values.get("AIRESEARCH_PAPI", "papi")
        layout_output_dir = Path(values.get("AIRESEARCH_LAYOUT_OUTPUT_DIR", root / "data" / "layout"))
        layout_max_pages_raw = values.get("AIRESEARCH_LAYOUT_MAX_PAGES", "")
        layout_max_pages = int(layout_max_pages_raw) if layout_max_pages_raw.strip().isdigit() else None
        layout_ocr_mode = values.get("AIRESEARCH_LAYOUT_OCR_MODE", "auto").strip().lower() or "auto"
        if layout_ocr_mode not in {"off", "auto", "force"}:
            raise ValueError("AIRESEARCH_LAYOUT_OCR_MODE must be off, auto, or force")
        layout_ocr_dpi_raw = values.get("AIRESEARCH_LAYOUT_OCR_DPI", "220")
        layout_ocr_dpi = int(layout_ocr_dpi_raw) if layout_ocr_dpi_raw.isdigit() else 220
        if layout_ocr_dpi < 72:
            raise ValueError("AIRESEARCH_LAYOUT_OCR_DPI must be at least 72")
        formula_ocr_mode = values.get("AIRESEARCH_FORMULA_OCR_MODE", "off").strip().lower() or "off"
        if formula_ocr_mode not in {"off", "auto", "force"}:
            raise ValueError("AIRESEARCH_FORMULA_OCR_MODE must be off, auto, or force")
        formula_ocr_dpi_raw = values.get("AIRESEARCH_FORMULA_OCR_DPI", "260")
        formula_ocr_dpi = int(formula_ocr_dpi_raw) if formula_ocr_dpi_raw.isdigit() else 260
        formula_confidence_raw = values.get("AIRESEARCH_FORMULA_OCR_MIN_CONFIDENCE", "0.7")
        try:
            formula_ocr_min_confidence = float(formula_confidence_raw)
        except ValueError:
            formula_ocr_min_confidence = 0.7
        if not 0 <= formula_ocr_min_confidence <= 1:
            raise ValueError("AIRESEARCH_FORMULA_OCR_MIN_CONFIDENCE must be between 0 and 1")
        archive_workers = int(values.get("AIRESEARCH_ARCHIVE_WORKERS", "2"))
        archive_cache_gb = int(values.get("AIRESEARCH_ARCHIVE_CACHE_GB", "1"))
        if archive_workers < 1:
            raise ValueError("AIRESEARCH_ARCHIVE_WORKERS must be at least 1")
        if archive_cache_gb < 0:
            raise ValueError("AIRESEARCH_ARCHIVE_CACHE_GB must be non-negative")
        return cls(
            project_root=root,
            paper_db_path=paper_db_path,
            sqlite_path=sqlite_path,
            papi_executable=papi_executable,
            layout_output_dir=layout_output_dir,
            layout_max_pages=layout_max_pages,
            layout_ocr_mode=layout_ocr_mode,
            layout_ocr_languages=values.get("AIRESEARCH_LAYOUT_OCR_LANGUAGES", "eng+chi_sim").strip() or "eng+chi_sim",
            layout_ocr_dpi=layout_ocr_dpi,
            layout_ocr_executable=values.get("AIRESEARCH_LAYOUT_OCR_EXECUTABLE", "tesseract").strip() or "tesseract",
            layout_formula_ocr_mode=formula_ocr_mode,
            layout_formula_ocr_dpi=formula_ocr_dpi,
            layout_formula_ocr_min_confidence=formula_ocr_min_confidence,
            archive_remote=values.get("AIRESEARCH_ARCHIVE_REMOTE", "").rstrip("/"),
            archive_staging_path=Path(
                values.get(
                    "AIRESEARCH_ARCHIVE_STAGING",
                    root / "data" / "archive-staging",
                )
            ),
            rclone_executable=values.get("AIRESEARCH_RCLONE", "rclone"),
            archive_workers=archive_workers,
            archive_cache_gb=archive_cache_gb,
        )
