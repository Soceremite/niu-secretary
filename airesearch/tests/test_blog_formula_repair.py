from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from airesearch.blog_formula_repair import (
    FormulaEvidence,
    FormulaSpan,
    FormulaValidation,
    _match_layout,
    extract_math_spans,
    repair_blog_formulas,
)
from airesearch.db import connect, init_db
from airesearch.formula_ocr import FormulaOCRError, FormulaOCRResult
from airesearch.paper_blog import publish_blog_version


class FakeCompiler:
    def __init__(self, *, repaired_valid: bool = True, unavailable: bool = False):
        self.repaired_valid = repaired_valid
        self.unavailable = unavailable
        self.calls: list[str] = []

    def validate_many(self, formulas: list[str]) -> list[FormulaValidation]:
        return [self.validate(formula) for formula in formulas]

    def validate(self, latex: str) -> FormulaValidation:
        self.calls.append(latex)
        if self.unavailable:
            return FormulaValidation(False, "validator_unavailable", "browser unavailable")
        if r"\right]" in latex and r"\left[" not in latex:
            return FormulaValidation(False, "compile_failed", r"Missing \left or extra \right")
        if latex == r"x=\left[y\right]" and not self.repaired_valid:
            return FormulaValidation(False, "compile_failed", "candidate still invalid")
        return FormulaValidation(True, "compiled")


class FakeProvider:
    def __init__(self, *, fail: bool = False, latex: str = r"x=\left[y\right]"):
        self.config = SimpleNamespace(model="gpt-5.6-luna")
        self.fail = fail
        self.latex = latex
        self.calls: list[dict[str, object]] = []

    def repair(self, image_bytes: bytes, *, failed_latex: str, context: str = "", mime_type: str = "image/png"):
        self.calls.append(
            {"image_bytes": image_bytes, "failed_latex": failed_latex, "context": context, "mime_type": mime_type}
        )
        if self.fail:
            raise FormulaOCRError("provider offline")
        return FormulaOCRResult(self.latex, 0.96, "gpt-5.6-luna")


def _seed_blog(db_path: Path, tmp_path: Path) -> tuple[int, str]:
    init_db(db_path)
    now = "2026-08-12T10:00:00+00:00"
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    with connect(db_path) as conn:
        conn.execute(
            "insert into papers (paper_key, title, paper_dir, created_at, updated_at) values (?, ?, ?, ?, ?)",
            ("paper-a", "Paper A", str(paper_dir), now, now),
        )
        conn.commit()
    markdown = """# Deep reading

Normal formula $a+b=c$ remains unchanged.

Broken formula:

$$x=\\right]$$

![Figure 1](assets/full-figure.png)

| Method | Score |
| --- | ---: |
| Ours | 99 |
"""
    published = publish_blog_version(
        db_path,
        paper_key="paper-a",
        title="Paper A",
        slug="paper-a",
        markdown=markdown,
        html=f"<article>{markdown}</article>",
        outline={"sections": []},
        image_refs=[{"path": "assets/full-figure.png", "caption": "Figure 1"}],
        generation_meta={"generator": "deep-reading"},
        model="deep-reading-model",
        prompt_version="blog-v1",
        source_hash="source-a",
    )
    return published.version_id, markdown


def _evidence(_db_path: Path, _paper_key: str, _markdown: str, _span) -> FormulaEvidence:
    return FormulaEvidence(
        pdf_page=3,
        bbox=[100.0, 220.0, 500.0, 280.0],
        crop_path="/tmp/formula-crop.png",
        crop_bytes=b"png-crop",
        context="The local paragraph defining x and y.",
        selection_method="layout-similarity:0.950:bbox",
    )


def test_repair_is_local_audited_and_idempotent(tmp_path: Path):
    db_path = tmp_path / "research.sqlite3"
    source_version, original = _seed_blog(db_path, tmp_path)
    compiler = FakeCompiler()
    provider = FakeProvider()

    first = repair_blog_formulas(
        db_path, "paper-a", compiler=compiler, provider=provider, evidence_builder=_evidence
    )

    assert first.status == "applied"
    assert first.source_version_id == source_version
    assert first.applied_version_id is not None
    assert first.compile_failures == 1
    assert provider.calls == [
        {
            "image_bytes": b"png-crop",
            "failed_latex": r"x=\right]",
            "context": "The local paragraph defining x and y.",
            "mime_type": "image/png",
        }
    ]
    with connect(db_path) as conn:
        post = dict(conn.execute("select * from paper_blog_posts where paper_key='paper-a'").fetchone())
        audit = dict(conn.execute("select * from paper_blog_formula_repairs").fetchone())
        versions = conn.execute("select count(*) as count from paper_blog_versions").fetchone()["count"]
    expected = original.replace(r"x=\right]", r"x=\left[y\right]", 1)
    assert post["markdown"] == expected
    assert "Normal formula $a+b=c$ remains unchanged." in post["markdown"]
    assert "![Figure 1](assets/full-figure.png)" in post["markdown"]
    assert "| Ours | 99 |" in post["markdown"]
    assert json.loads(post["image_refs_json"]) == [{"caption": "Figure 1", "path": "assets/full-figure.png"}]
    assert audit["paper_key"] == "paper-a"
    assert audit["source_version_id"] == source_version
    assert audit["applied_version_id"] == first.applied_version_id
    assert audit["original_latex"] == r"x=\right]"
    assert audit["repaired_latex"] == r"x=\left[y\right]"
    assert audit["pdf_page"] == 3
    assert json.loads(audit["bbox_json"]) == [100.0, 220.0, 500.0, 280.0]
    assert audit["crop_path"] == "/tmp/formula-crop.png"
    assert audit["context"] == "The local paragraph defining x and y."
    assert audit["model"] == "gpt-5.6-luna"
    assert audit["confidence"] == 0.96
    assert audit["initial_validation_status"] == "compile_failed"
    assert "extra \\right" in audit["initial_validation_error"]
    assert audit["validation_status"] == "compiled"
    assert audit["validation_error"] == ""
    assert audit["repair_status"] == "applied"
    assert audit["created_at"] and audit["updated_at"]

    second = repair_blog_formulas(
        db_path, "paper-a", compiler=compiler, provider=provider, evidence_builder=_evidence
    )
    with connect(db_path) as conn:
        version_count_after = conn.execute("select count(*) as count from paper_blog_versions").fetchone()["count"]
    assert second.status == "clean"
    assert len(provider.calls) == 1
    assert version_count_after == versions


def test_provider_failure_is_audited_without_blog_write_and_retry_is_explicit(tmp_path: Path):
    db_path = tmp_path / "research.sqlite3"
    source_version, original = _seed_blog(db_path, tmp_path)
    provider = FakeProvider(fail=True)

    first = repair_blog_formulas(
        db_path, "paper-a", compiler=FakeCompiler(), provider=provider, evidence_builder=_evidence
    )
    second = repair_blog_formulas(
        db_path, "paper-a", compiler=FakeCompiler(), provider=provider, evidence_builder=_evidence
    )

    assert first.status == second.status == "failed"
    assert len(provider.calls) == 1
    with connect(db_path) as conn:
        post = dict(conn.execute("select * from paper_blog_posts where paper_key='paper-a'").fetchone())
        audit = dict(conn.execute("select * from paper_blog_formula_repairs").fetchone())
        version_count = conn.execute("select count(*) as count from paper_blog_versions").fetchone()["count"]
    assert post["current_version_id"] == source_version
    assert post["markdown"] == original
    assert version_count == 1
    assert audit["repair_status"] == "failed"
    assert audit["initial_validation_status"] == "compile_failed"
    assert audit["validation_status"] == "provider_failed"
    assert audit["validation_error"] == "provider offline"

    retry = repair_blog_formulas(
        db_path,
        "paper-a",
        compiler=FakeCompiler(),
        provider=provider,
        evidence_builder=_evidence,
        force_retry=True,
    )
    assert retry.status == "failed"
    assert len(provider.calls) == 2


def test_invalid_luna_candidate_and_validator_unavailable_never_write(tmp_path: Path):
    db_path = tmp_path / "research.sqlite3"
    source_version, original = _seed_blog(db_path, tmp_path)
    provider = FakeProvider()

    invalid = repair_blog_formulas(
        db_path,
        "paper-a",
        compiler=FakeCompiler(repaired_valid=False),
        provider=provider,
        evidence_builder=_evidence,
    )
    unavailable = repair_blog_formulas(
        db_path,
        "paper-a",
        compiler=FakeCompiler(unavailable=True),
        provider=provider,
        evidence_builder=_evidence,
        force_retry=True,
    )

    assert invalid.status == "failed"
    assert unavailable.status == "validator_unavailable"
    with connect(db_path) as conn:
        post = dict(conn.execute("select * from paper_blog_posts where paper_key='paper-a'").fetchone())
        audit = dict(conn.execute("select * from paper_blog_formula_repairs").fetchone())
        version_count = conn.execute("select count(*) as count from paper_blog_versions").fetchone()["count"]
    assert post["current_version_id"] == source_version
    assert post["markdown"] == original
    assert version_count == 1
    assert audit["validation_status"] == "compile_failed"
    assert audit["validation_error"] == "candidate still invalid"


def test_concurrent_blog_publish_returns_stale_without_overwriting_new_version(tmp_path: Path):
    db_path = tmp_path / "research.sqlite3"
    source_version, _original = _seed_blog(db_path, tmp_path)

    def publish_during_evidence(_db_path: Path, _paper_key: str, _markdown: str, _span) -> FormulaEvidence:
        publish_blog_version(
            db_path,
            paper_key="paper-a",
            title="Concurrent version",
            slug="paper-a",
            markdown="# New content\n\n$concurrent=true$",
            html="<h1>New content</h1>",
            outline={"sections": []},
            image_refs=[],
            generation_meta={"source": "concurrent"},
            model="other-model",
            prompt_version="other-v1",
            source_hash="source-b",
        )
        return _evidence(_db_path, _paper_key, _markdown, _span)

    result = repair_blog_formulas(
        db_path,
        "paper-a",
        compiler=FakeCompiler(),
        provider=FakeProvider(),
        evidence_builder=publish_during_evidence,
    )

    assert result.status == "stale"
    assert result.source_version_id == source_version
    with connect(db_path) as conn:
        post = dict(conn.execute("select * from paper_blog_posts where paper_key='paper-a'").fetchone())
        audit = dict(conn.execute("select * from paper_blog_formula_repairs").fetchone())
        versions = conn.execute("select count(*) as count from paper_blog_versions").fetchone()["count"]
    assert post["title"] == "Concurrent version"
    assert post["markdown"] == "# New content\n\n$concurrent=true$"
    assert versions == 2
    assert audit["repair_status"] == "validated"
    assert audit["applied_version_id"] is None


def test_extract_math_spans_ignores_code_and_preserves_locators():
    markdown = "Inline $a+b$ and `code $not_math$`.\n\n$$x=\\right]$$"

    spans = extract_math_spans(markdown)

    assert [span.latex for span in spans] == ["a+b", r"x=\right]"]
    assert [span.ordinal for span in spans] == [1, 2]
    assert markdown[spans[1].content_start:spans[1].content_end] == r"x=\right]"


def test_low_similarity_layout_match_uses_page_without_unrelated_bbox():
    span = FormulaSpan(2, "display_dollar", 10, 20, 12, 18, r"x=\right]", "digest")
    rows = [
        {"page_index": 2, "bbox": [10, 20, 30, 40], "text": r"a+b=c"},
        {"page_index": 4, "bbox": [50, 60, 70, 80], "text": r"u+v=w"},
    ]

    matched, method = _match_layout(span, rows)

    assert matched is not None
    assert matched["page_index"] == 4
    assert matched["bbox"] == []
    assert method == "layout-ordinal-page-fallback"
