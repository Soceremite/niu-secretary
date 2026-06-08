import json
from pathlib import Path

from airesearch.code_links import (
    export_code_links,
    extract_code_links,
    extract_github_links_from_text,
    list_code_links,
)
from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import sync_paperpipe


def synced_fixture_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    init_db(db_path)
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    return db_path


def test_extract_github_links_normalizes_project_url():
    text = "Code: https://github.com/openai/whisper/blob/main/README.md and github.com/openai/whisper.git."

    links = extract_github_links_from_text(text, source_type="abstract")

    assert len(links) == 1
    assert links[0].url == "https://github.com/openai/whisper"
    assert links[0].owner == "openai"
    assert links[0].repo == "whisper"


def test_extract_code_links_from_source_tex_is_idempotent(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)

    first = extract_code_links(db_path)
    second = extract_code_links(db_path)

    assert first.papers_seen == 1
    assert first.links_written == 1
    assert second.links_written == 1
    with connect(db_path) as conn:
        count = conn.execute("select count(*) as count from paper_code_links").fetchone()["count"]
        row = conn.execute("select * from paper_code_links").fetchone()

    assert count == 1
    assert row["url"] == "https://github.com/attention/transformer"
    assert row["source_type"] == "source_tex"


def test_list_and_export_code_links(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)
    out_path = tmp_path / "code_links.jsonl"
    extract_code_links(db_path)

    rows = list_code_links(db_path, paper_key="1706_03762", limit=10)
    exported = export_code_links(db_path, out_path)

    assert len(rows) == 1
    assert exported == 1
    payload = json.loads(out_path.read_text(encoding="utf-8").strip())
    assert payload["paper_key"] == "1706_03762"
    assert payload["url"] == "https://github.com/attention/transformer"
