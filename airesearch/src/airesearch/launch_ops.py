from __future__ import annotations

import hashlib
import json
import os
import shlex
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


REQUIRED_TABLES = [
    "papers",
    "paper_artifacts",
    "paper_cards",
    "research_facts",
    "sync_events",
]

DEFAULT_REQUIRED_ENV = ["PAPER_DB_PATH"]
FACT_PROVIDER_ENV = ["OPENAI_API_KEY", "OPENAI_BASE_URL", "AIRESEARCH_FACT_MODEL"]
EMBEDDING_ENV = [
    "AIRESEARCH_EMBEDDING_API_KEY",
    "AIRESEARCH_EMBEDDING_BASE_URL",
    "AIRESEARCH_EMBEDDING_MODEL",
]


@dataclass(frozen=True)
class HealthCheckItem:
    name: str
    ok: bool
    detail: str
    required: bool = True


@dataclass(frozen=True)
class HealthCheckResult:
    ok: bool
    checks: list[HealthCheckItem]

    @property
    def failed_count(self) -> int:
        return sum(1 for check in self.checks if check.required and not check.ok)


@dataclass(frozen=True)
class DbBackupResult:
    source_path: Path
    backup_path: Path
    manifest_path: Path
    size_bytes: int
    sha256: str
    generated_at: str


@dataclass(frozen=True)
class ScheduledRefreshWrapperResult:
    wrapper_path: Path
    project_dir: Path
    schedule: str
    log_dir: Path
    history_dir: Path
    command: str


def _count_table(db_path: Path, table: str) -> int:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(f"select count(*) from {table}").fetchone()
    return int(row[0])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_label(label: str | None) -> str:
    if not label:
        return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    clean = "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in label.strip())
    clean = clean.strip("-_")
    if not clean:
        raise ValueError("backup label must contain at least one alphanumeric character")
    return clean


def run_health_check(
    *,
    db_path: Path,
    paper_db_path: Path,
    site_dir: Path,
    require_fact_provider: bool = False,
    require_embedding: bool = False,
    required_env: list[str] | None = None,
) -> HealthCheckResult:
    checks: list[HealthCheckItem] = []
    checks.append(HealthCheckItem("db_exists", db_path.exists(), str(db_path)))

    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                conn.execute("select 1").fetchone()
            checks.append(HealthCheckItem("db_readable", True, "sqlite ok"))
        except sqlite3.Error as exc:
            checks.append(HealthCheckItem("db_readable", False, f"sqlite error: {exc}"))

        for table in REQUIRED_TABLES:
            try:
                count = _count_table(db_path, table)
            except sqlite3.Error as exc:
                checks.append(HealthCheckItem(f"table.{table}", False, f"query failed: {exc}"))
            else:
                checks.append(HealthCheckItem(f"table.{table}", True, f"rows={count}"))
    else:
        checks.append(HealthCheckItem("db_readable", False, "missing database"))
        for table in REQUIRED_TABLES:
            checks.append(HealthCheckItem(f"table.{table}", False, "database missing"))

    paper_index = paper_db_path / "index.json"
    checks.append(HealthCheckItem("paper_db_exists", paper_db_path.exists() and paper_db_path.is_dir(), str(paper_db_path)))
    checks.append(HealthCheckItem("paper_db_index", paper_index.exists() and paper_index.is_file(), str(paper_index)))

    site_index = site_dir / "index.html"
    site_manifest = site_dir / "manifest.json"
    publish_manifest = site_dir / "publish.json"
    checks.append(HealthCheckItem("site_index", site_index.exists() and site_index.stat().st_size > 0 if site_index.exists() else False, str(site_index)))
    checks.append(HealthCheckItem("site_manifest", site_manifest.exists() and site_manifest.is_file(), str(site_manifest)))
    checks.append(HealthCheckItem("publish_manifest", publish_manifest.exists() and publish_manifest.is_file(), str(publish_manifest)))

    env_names = list(DEFAULT_REQUIRED_ENV)
    if required_env:
        env_names.extend(required_env)
    if require_fact_provider:
        env_names.extend(FACT_PROVIDER_ENV)
    if require_embedding:
        env_names.extend(EMBEDDING_ENV)
    for name in dict.fromkeys(env_names):
        checks.append(HealthCheckItem(f"env.{name}", bool(os.environ.get(name)), "present" if os.environ.get(name) else "missing"))

    return HealthCheckResult(
        ok=all(check.ok for check in checks if check.required),
        checks=checks,
    )


def backup_sqlite_db(
    *,
    db_path: Path,
    out_dir: Path = Path("backups"),
    label: str | None = None,
) -> DbBackupResult:
    if not db_path.exists():
        raise ValueError(f"database does not exist: {db_path}")
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_label(label)
    backup_path = out_dir / f"airesearch-{stem}.sqlite3"
    manifest_path = out_dir / f"airesearch-{stem}.json"
    if backup_path.exists() or manifest_path.exists():
        raise ValueError(f"backup output already exists for label: {stem}")

    with sqlite3.connect(db_path) as source:
        with sqlite3.connect(backup_path) as target:
            source.backup(target)

    generated_at = datetime.now(UTC).isoformat()
    size_bytes = backup_path.stat().st_size
    digest = _sha256(backup_path)
    result = DbBackupResult(
        source_path=db_path,
        backup_path=backup_path,
        manifest_path=manifest_path,
        size_bytes=size_bytes,
        sha256=digest,
        generated_at=generated_at,
    )
    payload = asdict(result)
    payload["source_path"] = str(result.source_path)
    payload["backup_path"] = str(result.backup_path)
    payload["manifest_path"] = str(result.manifest_path)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def write_scheduled_refresh_wrapper(
    *,
    wrapper_path: Path,
    project_dir: Path = Path("."),
    schedule: str = "manual",
    log_dir: Path = Path("logs"),
    history_dir: Path = Path("exports/run-history"),
    refresh_command: str | None = None,
) -> ScheduledRefreshWrapperResult:
    if schedule not in {"manual", "daily", "weekly"}:
        raise ValueError("schedule must be one of: manual, daily, weekly")
    project_dir = project_dir.expanduser().resolve(strict=False)
    command = refresh_command or (
        "python -m airesearch.cli run-launch-refresh "
        "--limit-per-profile 50 --select-limit 10 --min-score 0.60 "
        "--out-dir exports/mvp-current --site-dir exports/site-current --progress"
    )
    wrapper_path.parent.mkdir(parents=True, exist_ok=True)
    script = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f"# schedule={schedule}",
            f'ROOT_DIR={shlex.quote(str(project_dir))}',
            f'LOG_DIR={shlex.quote(str(log_dir))}',
            f'HISTORY_DIR={shlex.quote(str(history_dir))}',
            'STAMP="$(date -u +%Y%m%d-%H%M%S)"',
            'mkdir -p "$ROOT_DIR/$LOG_DIR" "$ROOT_DIR/$HISTORY_DIR" "$ROOT_DIR/backups"',
            'cd "$ROOT_DIR"',
            'if [ -f ./activate.sh ]; then source ./activate.sh; fi',
            'LOG_PATH="$LOG_DIR/launch-refresh-$STAMP.log"',
            'RUN_MANIFEST="$HISTORY_DIR/launch-refresh-$STAMP.json"',
            "{",
            '  echo "started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"',
            '  python -m airesearch.cli backup-db --out-dir backups --label "before-launch-refresh-$STAMP"',
            '  python -m airesearch.cli health-check --site-dir exports/site-current || echo "preflight_health_check_failed_continue=true"',
            f"  {command} --run-manifest \"$RUN_MANIFEST\"",
            '  python -m airesearch.cli health-check --site-dir exports/site-current',
            '  echo "finished_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"',
            '} 2>&1 | tee "$LOG_PATH"',
            "",
        ]
    )
    wrapper_path.write_text(script, encoding="utf-8")
    wrapper_path.chmod(0o755)
    return ScheduledRefreshWrapperResult(
        wrapper_path=wrapper_path,
        project_dir=project_dir,
        schedule=schedule,
        log_dir=log_dir,
        history_dir=history_dir,
        command=command,
    )
