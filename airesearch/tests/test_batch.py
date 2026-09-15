from pathlib import Path

from airesearch.batch import parse_manifest, run_batch_ingest
from airesearch.db import connect, init_db


def test_parse_manifest_ignores_blank_and_comment_lines(tmp_path: Path):
    manifest = tmp_path / "papers.txt"
    manifest.write_text(
        "\n# seed papers\n1706.03762\nhttps://arxiv.org/abs/2103.00020\n",
        encoding="utf-8",
    )

    items = parse_manifest(manifest)

    assert [item.raw_input for item in items] == [
        "1706.03762",
        "https://arxiv.org/abs/2103.00020",
    ]


def test_batch_ingest_records_failed_item(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = tmp_path / "paperpipe"
    fake_papi = tmp_path / "papi"
    manifest = tmp_path / "papers.txt"
    fake_papi.write_text("#!/bin/sh\necho papi failed >&2\nexit 2\n", encoding="utf-8")
    fake_papi.chmod(0o755)
    manifest.write_text("bad-paper\n", encoding="utf-8")
    init_db(db_path)

    result = run_batch_ingest(
        db_path=db_path,
        paper_db_path=paper_db,
        manifest_path=manifest,
        papi_executable=str(fake_papi),
    )

    assert result.failed == 1
    with connect(db_path) as conn:
        item = conn.execute("select status, error from ingest_items").fetchone()
    assert item["status"] == "failed"
    assert "papi failed" in item["error"]


ARXIV_ABS_PAGE_HTML = """
<html><head>
<meta name="citation_title" content="DA-DLM: Explicitly Modeling Token Dependencies in Diffusion Language Models" />
<meta name="citation_author" content="Ji, Pengyu" />
<meta name="citation_author" content="Zhang, Zichen" />
<meta name="citation_date" content="2026/09/14" />
<meta name="citation_pdf_url" content="https://arxiv.org/pdf/2609.15070" />
</head><body>
<blockquote class="abstract mathjax">
  <span class="descriptor">Abstract:</span>Diffusion Language Models generate text by denoising.
</blockquote>
</body></html>
"""


def test_batch_ingest_falls_back_to_pdf_when_export_api_rate_limited(tmp_path: Path, monkeypatch):
    from airesearch import providers

    monkeypatch.setattr(providers, "fetch_text", lambda *args, **kwargs: ARXIV_ABS_PAGE_HTML)

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = tmp_path / "paperpipe"
    fake_papi = tmp_path / "papi"
    manifest = tmp_path / "papers.txt"
    fake_papi.write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        "  *--pdf*) echo 'Added: da-dlm'; exit 0 ;;\n"
        "  *) echo 'Error fetching metadata: Page request resulted in HTTP 429' >&2; exit 2 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    fake_papi.chmod(0o755)
    manifest.write_text("https://arxiv.org/abs/2609.15070\n", encoding="utf-8")
    init_db(db_path)

    result = run_batch_ingest(
        db_path=db_path,
        paper_db_path=paper_db,
        manifest_path=manifest,
        papi_executable=str(fake_papi),
        normalize_urls=False,
    )

    assert result.success == 1
    with connect(db_path) as conn:
        item = conn.execute("select status, stdout from ingest_items").fetchone()
    assert item["status"] == "success"
    assert "[arxiv-pdf-fallback]" in item["stdout"]
    assert "Added: da-dlm" in item["stdout"]


def test_batch_ingest_dedupes_arxiv_items_already_in_library(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = tmp_path / "paperpipe"
    fake_papi = tmp_path / "papi"
    manifest = tmp_path / "papers.txt"
    fake_papi.write_text("#!/bin/sh\necho should-not-run\nexit 0\n", encoding="utf-8")
    fake_papi.chmod(0o755)
    manifest.write_text("https://arxiv.org/abs/2609.15070\n", encoding="utf-8")
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into papers
            (paper_key, title, authors_json, year, venue, ids_json, paper_dir, meta_json, created_at, updated_at)
            values (?, ?, '[]', 2026, 'arXiv', ?, ?, '{}', ?, ?)
            """,
            (
                "2609_15070",
                "DA-DLM",
                '{"arxiv_id": "2609.15070", "doi": null, "s2_id": null, "url": null}',
                "papers/2609_15070",
                "2026-09-15T00:00:00+00:00",
                "2026-09-15T00:00:00+00:00",
            ),
        )
        conn.commit()

    result = run_batch_ingest(
        db_path=db_path,
        paper_db_path=paper_db,
        manifest_path=manifest,
        papi_executable=str(fake_papi),
        normalize_urls=False,
    )

    assert result.duplicate == 1
    assert result.success == 0
    with connect(db_path) as conn:
        item = conn.execute("select status, stdout from ingest_items").fetchone()
    assert item["status"] == "duplicate"
    assert not (item["stdout"] or "").strip()


def test_batch_ingest_marks_item_failed_when_papi_hangs(tmp_path: Path, monkeypatch):
    from airesearch import batch as batch_module

    monkeypatch.setattr(batch_module, "PAPI_PRIMARY_TIMEOUT_S", 1)

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = tmp_path / "paperpipe"
    fake_papi = tmp_path / "papi"
    manifest = tmp_path / "papers.txt"
    fake_papi.write_text("#!/bin/sh\nsleep 15\necho late\n", encoding="utf-8")
    fake_papi.chmod(0o755)
    manifest.write_text("some-unknown-paper\n", encoding="utf-8")
    init_db(db_path)

    result = run_batch_ingest(
        db_path=db_path,
        paper_db_path=paper_db,
        manifest_path=manifest,
        papi_executable=str(fake_papi),
        normalize_urls=False,
    )

    assert result.failed == 1
    with connect(db_path) as conn:
        item = conn.execute("select status, error from ingest_items").fetchone()
    assert item["status"] == "failed"
    assert "timed out" in item["error"]
