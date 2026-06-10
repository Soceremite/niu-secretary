from pathlib import Path

from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import sync_paperpipe


def test_sync_paperpipe_upserts_papers_and_artifacts(tmp_path: Path):
    fixture = Path(__file__).parent / "fixtures" / "paperpipe_db"
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)

    result = sync_paperpipe(db_path=db_path, paper_db_path=fixture)

    assert result.papers_seen == 1
    assert result.artifacts_seen >= 3
    with connect(db_path) as conn:
        paper = conn.execute(
            "select * from papers where paper_key = ?", ("1706_03762",)
        ).fetchone()
        artifacts = conn.execute(
            "select artifact_type from paper_artifacts where paper_key = ?",
            ("1706_03762",),
        ).fetchall()

    assert paper["title"] == "Attention Is All You Need"
    assert {"paper_pdf", "summary", "equations"}.issubset(
        {row["artifact_type"] for row in artifacts}
    )
