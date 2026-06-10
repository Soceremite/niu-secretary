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
