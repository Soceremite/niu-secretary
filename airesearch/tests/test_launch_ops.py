import json
import sqlite3
from pathlib import Path

from airesearch.db import init_db
from airesearch.launch_ops import backup_sqlite_db, run_health_check, write_scheduled_refresh_wrapper


def make_site(site_dir: Path) -> None:
    site_dir.mkdir()
    (site_dir / "index.html").write_text("<!doctype html><title>AIResearch</title>\n", encoding="utf-8")
    (site_dir / "manifest.json").write_text('{"artifact_count": 1}\n', encoding="utf-8")
    (site_dir / "publish.json").write_text('{"file_count": 3}\n', encoding="utf-8")


def test_run_health_check_ok(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    site_dir = tmp_path / "site-current"
    init_db(db_path)
    make_site(site_dir)
    monkeypatch.setenv("AIRESEARCH_DB_PATH", str(db_path))
    monkeypatch.setenv("PAPER_DB_PATH", str(paper_db))

    result = run_health_check(db_path=db_path, paper_db_path=paper_db, site_dir=site_dir)

    assert result.ok is True
    assert result.failed_count == 0
    assert {check.name for check in result.checks} >= {
        "db_exists",
        "table.papers",
        "paper_db_index",
        "site_index",
        "publish_manifest",
        "env.PAPER_DB_PATH",
    }


def test_run_health_check_fails_for_missing_site(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    init_db(db_path)
    monkeypatch.setenv("AIRESEARCH_DB_PATH", str(db_path))
    monkeypatch.setenv("PAPER_DB_PATH", str(paper_db))

    result = run_health_check(db_path=db_path, paper_db_path=paper_db, site_dir=tmp_path / "missing-site")

    assert result.ok is False
    assert any(check.name == "site_index" and not check.ok for check in result.checks)


def test_backup_sqlite_db_writes_backup_and_manifest(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    out_dir = tmp_path / "backups"
    init_db(db_path)

    result = backup_sqlite_db(db_path=db_path, out_dir=out_dir, label="launch")

    assert result.backup_path.exists()
    assert result.manifest_path.exists()
    assert result.size_bytes == result.backup_path.stat().st_size
    assert len(result.sha256) == 64
    with sqlite3.connect(result.backup_path) as conn:
        row = conn.execute("select count(*) from papers").fetchone()
    assert row[0] == 0
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert payload["backup_path"] == str(result.backup_path)
    assert payload["sha256"] == result.sha256


def test_write_scheduled_refresh_wrapper_writes_executable_script(tmp_path: Path):
    wrapper = tmp_path / "scripts" / "refresh.sh"

    result = write_scheduled_refresh_wrapper(
        wrapper_path=wrapper,
        project_dir=tmp_path,
        schedule="daily",
        refresh_command="python -m airesearch.cli run-launch-refresh --limit-per-profile 5 --progress",
    )

    script = wrapper.read_text(encoding="utf-8")
    assert result.wrapper_path == wrapper
    assert result.schedule == "daily"
    assert wrapper.stat().st_mode & 0o111
    assert "backup-db --out-dir backups" in script
    assert "health-check --site-dir exports/site-current" in script
    assert "preflight_health_check_failed_continue=true" in script
    assert "run-launch-refresh --limit-per-profile 5 --progress --run-manifest" in script
    assert 'LOG_PATH="$LOG_DIR/launch-refresh-$STAMP.log"' in script
