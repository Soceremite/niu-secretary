from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Sequence

from airesearch.db import connect, init_db


class ArchiveStatus(str, Enum):
    PLANNED = "planned"
    UPLOADED = "uploaded"
    VERIFIED = "verified"
    EVICTED = "evicted"
    RESTORING = "restoring"
    AVAILABLE = "available"
    FAILED = "failed"


ALLOWED_TRANSITIONS = {
    ArchiveStatus.PLANNED: {ArchiveStatus.UPLOADED, ArchiveStatus.FAILED},
    ArchiveStatus.UPLOADED: {ArchiveStatus.VERIFIED, ArchiveStatus.FAILED},
    ArchiveStatus.VERIFIED: {ArchiveStatus.EVICTED, ArchiveStatus.FAILED},
    ArchiveStatus.EVICTED: {ArchiveStatus.RESTORING, ArchiveStatus.FAILED},
    ArchiveStatus.RESTORING: {
        ArchiveStatus.AVAILABLE,
        ArchiveStatus.EVICTED,
        ArchiveStatus.FAILED,
    },
    ArchiveStatus.AVAILABLE: {
        ArchiveStatus.VERIFIED,
        ArchiveStatus.EVICTED,
        ArchiveStatus.FAILED,
    },
    ArchiveStatus.FAILED: {
        ArchiveStatus.PLANNED,
        ArchiveStatus.UPLOADED,
        ArchiveStatus.VERIFIED,
        ArchiveStatus.EVICTED,
        ArchiveStatus.RESTORING,
    },
}


class InvalidArchiveTransition(ValueError):
    pass


class ArchiveRecordNotFound(LookupError):
    pass


@dataclass(frozen=True)
class ArchiveRecord:
    paper_key: str
    provider: str
    remote_name: str
    remote_path: str
    archive_sha256: str
    archive_size_bytes: int
    source_manifest_json: str
    status: ArchiveStatus
    verified_at: str | None
    evicted_at: str | None
    restored_at: str | None
    last_error: str | None
    pinned: bool
    updated_at: str


@dataclass(frozen=True)
class EligiblePaper:
    paper_key: str
    paper_dir: Path


@dataclass(frozen=True)
class ExcludedPaper:
    paper_key: str
    reason: str


@dataclass(frozen=True)
class EligibilityReport:
    eligible: tuple[EligiblePaper, ...]
    excluded: tuple[ExcludedPaper, ...]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _record_from_row(row) -> ArchiveRecord:
    return ArchiveRecord(
        paper_key=str(row["paper_key"]),
        provider=str(row["provider"]),
        remote_name=str(row["remote_name"]),
        remote_path=str(row["remote_path"]),
        archive_sha256=str(row["archive_sha256"]),
        archive_size_bytes=int(row["archive_size_bytes"]),
        source_manifest_json=str(row["source_manifest_json"]),
        status=ArchiveStatus(row["status"]),
        verified_at=row["verified_at"],
        evicted_at=row["evicted_at"],
        restored_at=row["restored_at"],
        last_error=row["last_error"],
        pinned=bool(row["pinned"]),
        updated_at=str(row["updated_at"]),
    )


class ArchiveStore:
    def __init__(self, *, db_path: Path, paper_db_path: Path) -> None:
        self.db_path = db_path
        self.paper_db_path = paper_db_path
        init_db(db_path)

    def get(self, paper_key: str) -> ArchiveRecord | None:
        with connect(self.db_path) as conn:
            row = conn.execute(
                "select * from paper_archives where paper_key = ?",
                (paper_key,),
            ).fetchone()
        return _record_from_row(row) if row is not None else None

    def paper_directory(self, paper_key: str) -> Path:
        with connect(self.db_path) as conn:
            row = conn.execute(
                "select paper_dir from papers where paper_key = ?",
                (paper_key,),
            ).fetchone()
        if row is None:
            raise ArchiveRecordNotFound(paper_key)
        paper_dir = Path(row["paper_dir"]).resolve(strict=True)
        papers_root = (self.paper_db_path / "papers").resolve(strict=True)
        try:
            paper_dir.relative_to(papers_root)
        except ValueError as exc:
            raise ValueError("paper directory is outside paper database") from exc
        return paper_dir

    def list_records(
        self,
        paper_keys: Sequence[str] | None = None,
    ) -> tuple[ArchiveRecord, ...]:
        with connect(self.db_path) as conn:
            if paper_keys is None:
                rows = conn.execute(
                    "select * from paper_archives order by paper_key"
                ).fetchall()
            elif not paper_keys:
                rows = []
            else:
                placeholders = ",".join("?" for _ in paper_keys)
                rows = conn.execute(
                    f"select * from paper_archives where paper_key in ({placeholders}) order by paper_key",
                    tuple(paper_keys),
                ).fetchall()
        return tuple(_record_from_row(row) for row in rows)

    def upsert_planned(
        self,
        *,
        paper_key: str,
        remote_name: str,
        remote_path: str,
        archive_sha256: str,
        archive_size_bytes: int,
        source_manifest_json: str,
    ) -> ArchiveRecord:
        existing = self.get(paper_key)
        if existing is not None and existing.archive_sha256 == archive_sha256:
            return existing
        protected = {
            ArchiveStatus.VERIFIED,
            ArchiveStatus.EVICTED,
            ArchiveStatus.RESTORING,
            ArchiveStatus.AVAILABLE,
        }
        if existing is not None and existing.status in protected:
            raise InvalidArchiveTransition(
                f"cannot replace verified archive for {paper_key}"
            )
        now = utc_now()
        with connect(self.db_path) as conn:
            conn.execute(
                """
                insert into paper_archives (
                    paper_key, provider, remote_name, remote_path,
                    archive_sha256, archive_size_bytes, source_manifest_json,
                    status, last_error, updated_at
                ) values (?, 'rclone', ?, ?, ?, ?, ?, 'planned', null, ?)
                on conflict(paper_key) do update set
                    provider = excluded.provider,
                    remote_name = excluded.remote_name,
                    remote_path = excluded.remote_path,
                    archive_sha256 = excluded.archive_sha256,
                    archive_size_bytes = excluded.archive_size_bytes,
                    source_manifest_json = excluded.source_manifest_json,
                    status = excluded.status,
                    verified_at = null,
                    evicted_at = null,
                    restored_at = null,
                    last_error = null,
                    updated_at = excluded.updated_at
                """,
                (
                    paper_key,
                    remote_name,
                    remote_path,
                    archive_sha256,
                    archive_size_bytes,
                    source_manifest_json,
                    now,
                ),
            )
            conn.commit()
        record = self.get(paper_key)
        if record is None:
            raise ArchiveRecordNotFound(paper_key)
        return record

    def transition(
        self,
        paper_key: str,
        status: ArchiveStatus,
        *,
        verified_at: str | None = None,
        evicted_at: str | None = None,
        restored_at: str | None = None,
        last_error: str | None = None,
    ) -> ArchiveRecord:
        existing = self.get(paper_key)
        if existing is None:
            raise ArchiveRecordNotFound(paper_key)
        if existing.status == status:
            return existing
        if status not in ALLOWED_TRANSITIONS[existing.status]:
            raise InvalidArchiveTransition(
                f"invalid archive transition: {existing.status.value} -> {status.value}"
            )
        now = utc_now()
        if status == ArchiveStatus.VERIFIED:
            verified_at = verified_at or now
        if status == ArchiveStatus.EVICTED:
            evicted_at = evicted_at or now
        if status == ArchiveStatus.AVAILABLE:
            restored_at = restored_at or now
        with connect(self.db_path) as conn:
            conn.execute(
                """
                update paper_archives set
                    status = ?,
                    verified_at = coalesce(?, verified_at),
                    evicted_at = coalesce(?, evicted_at),
                    restored_at = coalesce(?, restored_at),
                    last_error = ?,
                    updated_at = ?
                where paper_key = ?
                """,
                (
                    status.value,
                    verified_at,
                    evicted_at,
                    restored_at,
                    last_error,
                    now,
                    paper_key,
                ),
            )
            conn.commit()
        record = self.get(paper_key)
        if record is None:
            raise ArchiveRecordNotFound(paper_key)
        return record

    def set_pinned(self, paper_key: str, pinned: bool) -> ArchiveRecord:
        with connect(self.db_path) as conn:
            cursor = conn.execute(
                "update paper_archives set pinned = ?, updated_at = ? where paper_key = ?",
                (int(pinned), utc_now(), paper_key),
            )
            if cursor.rowcount != 1:
                raise ArchiveRecordNotFound(paper_key)
            conn.commit()
        record = self.get(paper_key)
        if record is None:
            raise ArchiveRecordNotFound(paper_key)
        return record

    def has_active_work(self, paper_key: str) -> bool:
        queries = (
            (
                """
                select 1 from ingest_items
                where status = 'running' and resolved_paper_key = ? limit 1
                """,
                (paper_key,),
            ),
            (
                """
                select 1 from extraction_runs
                where status = 'running' and (paper_key = ? or paper_key is null) limit 1
                """,
                (paper_key,),
            ),
            (
                """
                select 1 from fact_extraction_runs
                where status = 'running' and (paper_key = ? or paper_key is null) limit 1
                """,
                (paper_key,),
            ),
            (
                """
                select 1 from admin_jobs
                where status = 'running'
                  and job_type in (
                      'search_ingest', 'refresh', 'rebuild_deploy',
                      'rebuild', 'publish'
                  )
                limit 1
                """,
                (),
            ),
        )
        with connect(self.db_path) as conn:
            return any(
                conn.execute(sql, params).fetchone() is not None
                for sql, params in queries
            )

    def eligible_papers(
        self,
        paper_keys: Sequence[str] | None = None,
    ) -> EligibilityReport:
        with connect(self.db_path) as conn:
            if paper_keys is None:
                rows = conn.execute(
                    "select paper_key, paper_dir from papers order by paper_key"
                ).fetchall()
                requested = [str(row["paper_key"]) for row in rows]
            else:
                requested = list(dict.fromkeys(paper_keys))
                if requested:
                    placeholders = ",".join("?" for _ in requested)
                    rows = conn.execute(
                        f"select paper_key, paper_dir from papers where paper_key in ({placeholders})",
                        tuple(requested),
                    ).fetchall()
                else:
                    rows = []
        by_key = {str(row["paper_key"]): row for row in rows}
        eligible: list[EligiblePaper] = []
        excluded: list[ExcludedPaper] = []
        papers_root = (self.paper_db_path / "papers").resolve()
        for paper_key in requested:
            row = by_key.get(paper_key)
            if row is None:
                excluded.append(ExcludedPaper(paper_key, "missing_database_record"))
                continue
            paper_dir = Path(row["paper_dir"])
            try:
                resolved = paper_dir.resolve(strict=True)
            except FileNotFoundError:
                excluded.append(ExcludedPaper(paper_key, "paper_dir_missing"))
                continue
            try:
                resolved.relative_to(papers_root)
            except ValueError:
                excluded.append(ExcludedPaper(paper_key, "paper_dir_outside_database"))
                continue
            record = self.get(paper_key)
            if record is not None and record.status in {
                ArchiveStatus.EVICTED,
                ArchiveStatus.RESTORING,
            }:
                excluded.append(ExcludedPaper(paper_key, "local_sources_unavailable"))
                continue
            if self.has_active_work(paper_key):
                excluded.append(ExcludedPaper(paper_key, "active_paper_work"))
                continue
            eligible.append(EligiblePaper(paper_key, resolved))
        return EligibilityReport(tuple(eligible), tuple(excluded))

    def unreferenced_directories(self) -> tuple[str, ...]:
        papers_root = self.paper_db_path / "papers"
        if not papers_root.is_dir():
            return ()
        with connect(self.db_path) as conn:
            known = {
                str(row["paper_key"])
                for row in conn.execute("select paper_key from papers").fetchall()
            }
        return tuple(
            sorted(
                child.name
                for child in papers_root.iterdir()
                if child.is_dir() and child.name not in known
            )
        )
