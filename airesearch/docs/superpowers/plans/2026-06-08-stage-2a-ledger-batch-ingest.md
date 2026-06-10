# Stage 2A Ledger And Batch Ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build AIResearch's SQLite ledger, paperpipe sync adapter, and batch ingest CLI so roughly 100 papers can be imported and audited locally.

**Architecture:** Paperpipe remains the L0 content substrate under `data/paperpipe`. AIResearch adds a Python package that owns SQLite operational state under `data/airesearch.sqlite3`, syncs paperpipe artifacts into ledger tables, and runs batch ingestion by invoking `papi add` item by item. No KG extraction or automatic discovery is implemented in this stage.

**Tech Stack:** Python 3.12, SQLite, pytest, paperpipe / `papi`, local `.env` / `activate.sh` runtime.

---

## File Structure

- Create `pyproject.toml`: package metadata, pytest config, console script.
- Create `src/airesearch/__init__.py`: package version.
- Create `src/airesearch/config.py`: runtime path resolution.
- Create `src/airesearch/schema.sql`: SQLite DDL.
- Create `src/airesearch/db.py`: connection and migration helpers.
- Create `src/airesearch/paperpipe_sync.py`: sync paperpipe `index.json` and artifacts.
- Create `src/airesearch/batch.py`: manifest parser and batch ingest workflow.
- Create `src/airesearch/cli.py`: command-line interface.
- Create `tests/fixtures/paperpipe_db/`: minimal fake paperpipe DB.
- Create `tests/test_db.py`: schema tests.
- Create `tests/test_paperpipe_sync.py`: sync tests.
- Create `tests/test_batch.py`: manifest and batch tests.
- Create `tests/test_cli.py`: CLI smoke tests.
- Modify `PLAN.md`: mark Stage 2A as in progress and add execution checklist.

## Task 1: Package Skeleton And Config

**Files:**
- Create: `pyproject.toml`
- Create: `src/airesearch/__init__.py`
- Create: `src/airesearch/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write config tests**

```python
from pathlib import Path

from airesearch.config import Settings


def test_settings_defaults_to_project_data(tmp_path: Path):
    project = tmp_path / "airesearch"
    project.mkdir()

    settings = Settings.from_env({}, project_root=project)

    assert settings.project_root == project
    assert settings.paper_db_path == project / "data" / "paperpipe"
    assert settings.sqlite_path == project / "data" / "airesearch.sqlite3"
    assert settings.papi_executable == "papi"


def test_settings_reads_environment_overrides(tmp_path: Path):
    env = {
        "PAPER_DB_PATH": str(tmp_path / "papers"),
        "AIRESEARCH_DB_PATH": str(tmp_path / "custom.sqlite3"),
        "AIRESEARCH_PAPI": "/x/papi",
    }

    settings = Settings.from_env(env, project_root=tmp_path)

    assert settings.paper_db_path == tmp_path / "papers"
    assert settings.sqlite_path == tmp_path / "custom.sqlite3"
    assert settings.papi_executable == "/x/papi"
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `.venv/bin/python -m pytest tests/test_config.py -v`

Expected: import failure because `airesearch.config` does not exist.

- [ ] **Step 3: Add package skeleton**

Create `pyproject.toml` with setuptools package discovery, pytest path config, and console script `airesearch=airesearch.cli:main`.

Create `src/airesearch/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/airesearch/config.py`:

```python
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
        return cls(
            project_root=root,
            paper_db_path=paper_db_path,
            sqlite_path=sqlite_path,
            papi_executable=papi_executable,
        )
```

- [ ] **Step 4: Run config tests**

Run: `.venv/bin/python -m pytest tests/test_config.py -v`

Expected: 2 tests pass.

## Task 2: SQLite Schema And DB Helpers

**Files:**
- Create: `src/airesearch/schema.sql`
- Create: `src/airesearch/db.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Write schema tests**

```python
import sqlite3
from pathlib import Path

from airesearch.db import connect, init_db


def test_init_db_creates_expected_tables(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        names = {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }

    assert {
        "papers",
        "paper_sources",
        "paper_artifacts",
        "ingest_runs",
        "ingest_items",
        "sync_events",
    }.issubset(names)


def test_connect_returns_row_mapping(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)

    with connect(db_path) as conn:
        row = conn.execute("select count(*) as count from papers").fetchone()

    assert row["count"] == 0
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `.venv/bin/python -m pytest tests/test_db.py -v`

Expected: import failure because `airesearch.db` does not exist.

- [ ] **Step 3: Add schema and DB helpers**

Create `src/airesearch/schema.sql` with tables and indexes for the six Stage 2A tables. Use `paper_key` as the stable paperpipe key and foreign keys where possible.

Create `src/airesearch/db.py` with:

```python
from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys = on")
    return conn


def init_db(path: Path) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
```

- [ ] **Step 4: Run DB tests**

Run: `.venv/bin/python -m pytest tests/test_db.py -v`

Expected: 2 tests pass.

## Task 3: Paperpipe Sync Adapter

**Files:**
- Create: `src/airesearch/paperpipe_sync.py`
- Create: `tests/fixtures/paperpipe_db/index.json`
- Create: `tests/fixtures/paperpipe_db/papers/1706_03762/meta.json`
- Create: fixture artifact files under `tests/fixtures/paperpipe_db/papers/1706_03762/`
- Test: `tests/test_paperpipe_sync.py`

- [ ] **Step 1: Write sync tests**

```python
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
        paper = conn.execute("select * from papers where paper_key = ?", ("1706_03762",)).fetchone()
        artifacts = conn.execute("select artifact_type from paper_artifacts where paper_key = ?", ("1706_03762",)).fetchall()

    assert paper["title"] == "Attention Is All You Need"
    assert {"paper_pdf", "summary", "equations"}.issubset({row["artifact_type"] for row in artifacts})
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `.venv/bin/python -m pytest tests/test_paperpipe_sync.py -v`

Expected: import or fixture failure.

- [ ] **Step 3: Add fixture data**

Use a minimal `index.json` containing one `1706_03762` record, a `meta.json` with title/authors/year if available, and short text files for `summary.md`, `equations.md`, `tldr.md`, `notes.md`, plus a dummy `paper.pdf` text fixture.

- [ ] **Step 4: Implement sync adapter**

Implement:

- `SyncResult(papers_seen: int, artifacts_seen: int)`
- `sync_paperpipe(db_path: Path, paper_db_path: Path) -> SyncResult`
- SHA-256 hashing for artifact files.
- Upsert logic for `papers` and `paper_artifacts`.
- Insert one `sync_events` row per run.

- [ ] **Step 5: Run sync tests**

Run: `.venv/bin/python -m pytest tests/test_paperpipe_sync.py -v`

Expected: sync test passes.

## Task 4: Batch Manifest And Ingest Workflow

**Files:**
- Create: `src/airesearch/batch.py`
- Test: `tests/test_batch.py`

- [ ] **Step 1: Write manifest and batch tests**

```python
from pathlib import Path

from airesearch.batch import parse_manifest, run_batch_ingest
from airesearch.db import connect, init_db


def test_parse_manifest_ignores_blank_and_comment_lines(tmp_path: Path):
    manifest = tmp_path / "papers.txt"
    manifest.write_text("\\n# seed papers\\n1706.03762\\nhttps://arxiv.org/abs/2103.00020\\n", encoding="utf-8")

    items = parse_manifest(manifest)

    assert [item.raw_input for item in items] == ["1706.03762", "https://arxiv.org/abs/2103.00020"]


def test_batch_ingest_records_failed_item(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = tmp_path / "paperpipe"
    fake_papi = tmp_path / "papi"
    manifest = tmp_path / "papers.txt"
    fake_papi.write_text("#!/bin/sh\\necho papi failed >&2\\nexit 2\\n", encoding="utf-8")
    fake_papi.chmod(0o755)
    manifest.write_text("bad-paper\\n", encoding="utf-8")
    init_db(db_path)

    result = run_batch_ingest(db_path=db_path, paper_db_path=paper_db, manifest_path=manifest, papi_executable=str(fake_papi))

    assert result.failed == 1
    with connect(db_path) as conn:
        item = conn.execute("select status, error from ingest_items").fetchone()
    assert item["status"] == "failed"
    assert "papi failed" in item["error"]
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `.venv/bin/python -m pytest tests/test_batch.py -v`

Expected: import failure because `airesearch.batch` does not exist.

- [ ] **Step 3: Implement manifest parser and batch workflow**

Implement:

- `ManifestItem(raw_input: str, line_number: int)`
- `BatchResult(total: int, success: int, failed: int, duplicate: int, skipped: int)`
- `parse_manifest(path: Path) -> list[ManifestItem]`
- `run_batch_ingest(...) -> BatchResult`

For each manifest item, insert `ingest_items` as `running`, run `papi add <raw_input>` with `PAPER_DB_PATH` in the environment, sync paperpipe after success, then update item status.

- [ ] **Step 4: Run batch tests**

Run: `.venv/bin/python -m pytest tests/test_batch.py -v`

Expected: manifest and failure tests pass.

## Task 5: CLI Commands

**Files:**
- Create: `src/airesearch/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write CLI tests**

```python
from pathlib import Path

from airesearch.cli import main


def test_cli_init_db(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main(["--db", str(db_path), "init-db"])

    assert code == 0
    assert db_path.exists()


def test_cli_status_empty_db(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"
    main(["--db", str(db_path), "init-db"])

    code = main(["--db", str(db_path), "status"])

    assert code == 0
    assert "papers: 0" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `.venv/bin/python -m pytest tests/test_cli.py -v`

Expected: import failure because `airesearch.cli` does not exist.

- [ ] **Step 3: Implement CLI**

Use `argparse` with global options:

- `--db`
- `--paper-db`
- `--papi`

Commands:

- `init-db`
- `sync-paperpipe`
- `batch-ingest <manifest>`
- `status`

Return integer exit codes from `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 4: Run CLI tests**

Run: `.venv/bin/python -m pytest tests/test_cli.py -v`

Expected: CLI tests pass.

## Task 6: Real Local Verification And PLAN Update

**Files:**
- Modify: `PLAN.md`

- [ ] **Step 1: Install package in editable mode**

Run: `.venv/bin/python -m pip install -e .`

Expected: package installs and console script is available in `.venv/bin/airesearch`.

- [ ] **Step 2: Initialize local DB**

Run: `.venv/bin/python -m airesearch.cli init-db`

Expected: `data/airesearch.sqlite3` exists.

- [ ] **Step 3: Sync current paperpipe DB**

Run: `.venv/bin/python -m airesearch.cli sync-paperpipe`

Expected: output includes `papers_seen=1` or greater and artifact count greater than zero.

- [ ] **Step 4: Print status**

Run: `.venv/bin/python -m airesearch.cli status`

Expected: output includes paper count, artifact count, latest sync, and latest ingest run.

- [ ] **Step 5: Run full test suite**

Run: `.venv/bin/python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 6: Update `PLAN.md`**

Mark Stage 2A as in progress or done according to verification results. Add the commands that passed and the current SQLite ledger path.

## Self-Review

- Spec coverage: The plan covers schema, sync, batch ingest, status, and local verification.
- Scope control: The plan intentionally excludes OpenAlex/S2 discovery, KG extraction, and reports.
- Type consistency: Public names are fixed as `Settings`, `init_db`, `connect`, `sync_paperpipe`, `parse_manifest`, `run_batch_ingest`, and `main`.
