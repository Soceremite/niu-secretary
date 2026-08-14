from __future__ import annotations

import hashlib
import shutil
import tarfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from urllib.parse import quote

from airesearch.archive_lock import paper_lock
from airesearch.archive_manifest import (
    ArchiveSafetyError,
    SourceManifest,
    build_source_manifest,
    create_archive,
    sha256_file,
    validate_archive,
)
from airesearch.archive_remote import RcloneRemote, RemoteCommandError
from airesearch.archive_store import (
    ArchiveRecord,
    ArchiveStatus,
    ArchiveStore,
    ExcludedPaper,
)


class ArchiveWorkflowError(RuntimeError):
    def __init__(self, paper_key: str, category: str) -> None:
        self.paper_key = paper_key
        self.category = category
        super().__init__(f"{paper_key}: {category}")


@dataclass(frozen=True)
class ArchivePlanItem:
    paper_key: str
    source_bytes: int
    status: str
    reason: str


@dataclass(frozen=True)
class ArchivePlan:
    eligible_count: int
    excluded_count: int
    reclaimable_bytes: int
    items: tuple[ArchivePlanItem, ...]
    unreferenced_directories: tuple[str, ...]


@dataclass(frozen=True)
class ArchiveOperation:
    paper_key: str
    operation: str
    prior_status: ArchiveStatus | None
    status: ArchiveStatus
    changed: bool
    archive_sha256: str
    remote_path: str
    source_bytes: int
    remote_bytes: int
    duration_ms: int
    verified_at: str | None


class ArchiveService:
    def __init__(
        self,
        *,
        db_path: Path,
        paper_db_path: Path,
        staging_path: Path,
        remote: RcloneRemote,
        lock_root: Path,
    ) -> None:
        self.db_path = db_path
        self.paper_db_path = paper_db_path
        self.staging_path = staging_path
        self.remote = remote
        self.lock_root = lock_root
        self.store = ArchiveStore(db_path=db_path, paper_db_path=paper_db_path)

    def _staging_file(self, paper_key: str, purpose: str) -> Path:
        key_digest = hashlib.sha256(paper_key.encode("utf-8")).hexdigest()[:16]
        return self.staging_path / f"{key_digest}.{purpose}.{uuid.uuid4().hex}.tar"

    @staticmethod
    def _paper_component(paper_key: str) -> str:
        return quote(paper_key, safe="._-")

    @staticmethod
    def _category(error: Exception, default: str) -> str:
        if isinstance(error, ArchiveWorkflowError):
            return error.category
        if isinstance(error, RemoteCommandError):
            return error.category
        if isinstance(error, ArchiveSafetyError):
            return default
        return default

    def _mark_failure(self, paper_key: str, category: str) -> None:
        record = self.store.get(paper_key)
        if record is None or record.status in {
            ArchiveStatus.VERIFIED,
            ArchiveStatus.EVICTED,
            ArchiveStatus.AVAILABLE,
        }:
            return
        self.store.transition(
            paper_key,
            ArchiveStatus.FAILED,
            last_error=category,
        )

    def _require_eligible(self, paper_key: str) -> Path:
        report = self.store.eligible_papers([paper_key])
        if not report.eligible:
            reason = report.excluded[0].reason if report.excluded else "paper_not_eligible"
            raise ArchiveWorkflowError(paper_key, reason)
        return report.eligible[0].paper_dir

    def _operation(
        self,
        *,
        operation: str,
        prior_status: ArchiveStatus | None,
        record: ArchiveRecord,
        changed: bool,
        source_bytes: int,
        started: float,
    ) -> ArchiveOperation:
        return ArchiveOperation(
            paper_key=record.paper_key,
            operation=operation,
            prior_status=prior_status,
            status=record.status,
            changed=changed,
            archive_sha256=record.archive_sha256,
            remote_path=record.remote_path,
            source_bytes=source_bytes,
            remote_bytes=record.archive_size_bytes,
            duration_ms=round((time.monotonic() - started) * 1000),
            verified_at=record.verified_at,
        )

    def plan(
        self,
        paper_keys: Sequence[str] | None = None,
        *,
        record: bool = False,
    ) -> ArchivePlan:
        report = self.store.eligible_papers(paper_keys)
        items: list[ArchivePlanItem] = []
        excluded = list(report.excluded)
        for paper in report.eligible:
            try:
                manifest = build_source_manifest(paper.paper_key, paper.paper_dir)
                if record:
                    with paper_lock(self.lock_root, paper.paper_key):
                        staged = self._staging_file(paper.paper_key, "plan")
                        try:
                            archive = create_archive(manifest, paper.paper_dir, staged)
                            component = self._paper_component(paper.paper_key)
                            self.store.upsert_planned(
                                paper_key=paper.paper_key,
                                remote_name=self.remote.remote_name,
                                remote_path=(
                                    f"papers/{component}/{archive.sha256}.tar"
                                ),
                                archive_sha256=archive.sha256,
                                archive_size_bytes=archive.size_bytes,
                                source_manifest_json=manifest.to_json(),
                            )
                        finally:
                            staged.unlink(missing_ok=True)
                items.append(
                    ArchivePlanItem(
                        paper_key=paper.paper_key,
                        source_bytes=manifest.total_size,
                        status="eligible",
                        reason="",
                    )
                )
            except ArchiveSafetyError:
                excluded.append(ExcludedPaper(paper.paper_key, "archive_sources_invalid"))
        items.extend(
            ArchivePlanItem(
                paper_key=item.paper_key,
                source_bytes=0,
                status="excluded",
                reason=item.reason,
            )
            for item in excluded
        )
        return ArchivePlan(
            eligible_count=sum(item.status == "eligible" for item in items),
            excluded_count=sum(item.status == "excluded" for item in items),
            reclaimable_bytes=sum(
                item.source_bytes for item in items if item.status == "eligible"
            ),
            items=tuple(items),
            unreferenced_directories=self.store.unreferenced_directories(),
        )

    def upload(self, paper_key: str) -> ArchiveOperation:
        started = time.monotonic()
        staged: Path | None = None
        prior = self.store.get(paper_key)
        prior_status = prior.status if prior is not None else None
        try:
            with paper_lock(self.lock_root, paper_key):
                current = self.store.get(paper_key)
                if current is not None:
                    self._recover_quarantine(
                        paper_key,
                        self.store.paper_directory(paper_key),
                        current,
                    )
                paper_dir = self._require_eligible(paper_key)
                manifest = build_source_manifest(paper_key, paper_dir)
                staged = self._staging_file(paper_key, "upload")
                archive = create_archive(manifest, paper_dir, staged)
                component = self._paper_component(paper_key)
                final_path = f"papers/{component}/{archive.sha256}.tar"
                record = self.store.upsert_planned(
                    paper_key=paper_key,
                    remote_name=self.remote.remote_name,
                    remote_path=final_path,
                    archive_sha256=archive.sha256,
                    archive_size_bytes=archive.size_bytes,
                    source_manifest_json=manifest.to_json(),
                )
                final_stat = self.remote.stat(final_path)
                if final_stat.exists:
                    if final_stat.size_bytes != archive.size_bytes:
                        raise ArchiveWorkflowError(paper_key, "remote_size_mismatch")
                else:
                    if record.status in {
                        ArchiveStatus.VERIFIED,
                        ArchiveStatus.EVICTED,
                        ArchiveStatus.AVAILABLE,
                    }:
                        raise ArchiveWorkflowError(paper_key, "verified_remote_missing")
                    temporary_path = f"tmp/{component}/{uuid.uuid4().hex}.tar"
                    self.remote.upload(staged, temporary_path)
                    temporary_stat = self.remote.stat(temporary_path)
                    if (
                        not temporary_stat.exists
                        or temporary_stat.size_bytes != archive.size_bytes
                    ):
                        raise ArchiveWorkflowError(
                            paper_key,
                            "temporary_remote_size_mismatch",
                        )
                    self.remote.promote(temporary_path, final_path)
                    promoted_stat = self.remote.stat(final_path)
                    if (
                        not promoted_stat.exists
                        or promoted_stat.size_bytes != archive.size_bytes
                    ):
                        raise ArchiveWorkflowError(
                            paper_key,
                            "promoted_remote_size_mismatch",
                        )
                if record.status not in {
                    ArchiveStatus.VERIFIED,
                    ArchiveStatus.EVICTED,
                    ArchiveStatus.AVAILABLE,
                }:
                    record = self.store.transition(
                        paper_key,
                        ArchiveStatus.UPLOADED,
                    )
                return self._operation(
                    operation="upload",
                    prior_status=prior_status,
                    record=record,
                    changed=record.status != prior_status,
                    source_bytes=manifest.total_size,
                    started=started,
                )
        except Exception as exc:
            category = self._category(exc, "archive_upload_failed")
            self._mark_failure(paper_key, category)
            if isinstance(exc, ArchiveWorkflowError):
                raise
            raise ArchiveWorkflowError(paper_key, category) from exc
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)

    def verify(self, paper_key: str) -> ArchiveOperation:
        started = time.monotonic()
        downloaded: Path | None = None
        prior = self.store.get(paper_key)
        prior_status = prior.status if prior is not None else None
        try:
            with paper_lock(self.lock_root, paper_key):
                record = self.store.get(paper_key)
                if record is None or record.status not in {
                    ArchiveStatus.UPLOADED,
                    ArchiveStatus.VERIFIED,
                }:
                    raise ArchiveWorkflowError(paper_key, "archive_not_uploaded")
                self._recover_quarantine(
                    paper_key,
                    self.store.paper_directory(paper_key),
                    record,
                )
                stat = self.remote.stat(record.remote_path)
                if not stat.exists:
                    raise ArchiveWorkflowError(paper_key, "remote_archive_missing")
                if stat.size_bytes != record.archive_size_bytes:
                    raise ArchiveWorkflowError(paper_key, "remote_size_mismatch")
                downloaded = self._staging_file(paper_key, "verify")
                self.remote.download(record.remote_path, downloaded)
                if sha256_file(downloaded) != record.archive_sha256:
                    raise ArchiveWorkflowError(paper_key, "archive_digest_mismatch")
                try:
                    manifest = SourceManifest.from_json(record.source_manifest_json)
                    validate_archive(downloaded, manifest)
                except (ArchiveSafetyError, KeyError, TypeError, ValueError) as exc:
                    raise ArchiveWorkflowError(
                        paper_key,
                        "archive_validation_failed",
                    ) from exc
                verified = self.store.transition(
                    paper_key,
                    ArchiveStatus.VERIFIED,
                )
                return self._operation(
                    operation="verify",
                    prior_status=prior_status,
                    record=verified,
                    changed=prior_status != ArchiveStatus.VERIFIED,
                    source_bytes=manifest.total_size,
                    started=started,
                )
        except Exception as exc:
            category = self._category(exc, "archive_verification_failed")
            self._mark_failure(paper_key, category)
            if isinstance(exc, ArchiveWorkflowError):
                raise
            raise ArchiveWorkflowError(paper_key, category) from exc
        finally:
            if downloaded is not None:
                downloaded.unlink(missing_ok=True)

    def _download_validated(
        self,
        record: ArchiveRecord,
        purpose: str,
    ) -> tuple[Path, SourceManifest]:
        stat = self.remote.stat(record.remote_path)
        if not stat.exists:
            raise ArchiveWorkflowError(record.paper_key, "remote_archive_missing")
        if stat.size_bytes != record.archive_size_bytes:
            raise ArchiveWorkflowError(record.paper_key, "remote_size_mismatch")
        downloaded = self._staging_file(record.paper_key, purpose)
        try:
            self.remote.download(record.remote_path, downloaded)
            if sha256_file(downloaded) != record.archive_sha256:
                raise ArchiveWorkflowError(
                    record.paper_key,
                    "archive_digest_mismatch",
                )
            manifest = SourceManifest.from_json(record.source_manifest_json)
            validate_archive(downloaded, manifest)
            return downloaded, manifest
        except Exception:
            downloaded.unlink(missing_ok=True)
            raise

    def _recover_quarantine(
        self,
        paper_key: str,
        paper_dir: Path,
        record: ArchiveRecord,
    ) -> None:
        quarantine_root = paper_dir / ".archive-quarantine"
        operations = sorted(path for path in quarantine_root.glob("*") if path.is_dir())
        if not operations:
            return
        if len(operations) != 1:
            raise ArchiveWorkflowError(paper_key, "ambiguous_quarantine")
        operation = operations[0]
        if record.status == ArchiveStatus.EVICTED:
            shutil.rmtree(operation)
        elif record.status in {ArchiveStatus.VERIFIED, ArchiveStatus.AVAILABLE}:
            for name in ("paper.pdf", "figures"):
                source = operation / name
                target = paper_dir / name
                if not source.exists():
                    continue
                if target.exists():
                    raise ArchiveWorkflowError(paper_key, "quarantine_target_conflict")
                source.rename(target)
            operation.rmdir()
        else:
            raise ArchiveWorkflowError(paper_key, "quarantine_state_conflict")
        if quarantine_root.exists() and not any(quarantine_root.iterdir()):
            quarantine_root.rmdir()

    def evict(self, paper_key: str, *, apply: bool = False) -> ArchiveOperation:
        started = time.monotonic()
        downloaded: Path | None = None
        prior = self.store.get(paper_key)
        prior_status = prior.status if prior is not None else None
        try:
            with paper_lock(self.lock_root, paper_key):
                record = self.store.get(paper_key)
                if record is None or record.status not in {
                    ArchiveStatus.VERIFIED,
                    ArchiveStatus.AVAILABLE,
                }:
                    raise ArchiveWorkflowError(paper_key, "archive_not_verified")
                paper_dir = self.store.paper_directory(paper_key)
                self._recover_quarantine(paper_key, paper_dir, record)
                if record.pinned:
                    raise ArchiveWorkflowError(paper_key, "archive_pinned")
                if self.store.has_active_work(paper_key):
                    raise ArchiveWorkflowError(paper_key, "active_paper_work")
                expected = SourceManifest.from_json(record.source_manifest_json)
                current = build_source_manifest(paper_key, paper_dir)
                if current != expected:
                    raise ArchiveWorkflowError(paper_key, "local_manifest_drift")
                downloaded, remote_manifest = self._download_validated(record, "evict")
                if remote_manifest != expected:
                    raise ArchiveWorkflowError(paper_key, "archive_validation_failed")
                if not apply:
                    return self._operation(
                        operation="evict",
                        prior_status=prior_status,
                        record=record,
                        changed=False,
                        source_bytes=expected.total_size,
                        started=started,
                    )

                operation_dir = (
                    paper_dir / ".archive-quarantine" / uuid.uuid4().hex
                )
                operation_dir.mkdir(parents=True)
                moved: list[tuple[Path, Path]] = []
                try:
                    for name in ("paper.pdf", "figures"):
                        source = paper_dir / name
                        if source.exists():
                            destination = operation_dir / name
                            source.rename(destination)
                            moved.append((source, destination))
                    evicted = self.store.transition(
                        paper_key,
                        ArchiveStatus.EVICTED,
                    )
                except Exception:
                    for source, destination in reversed(moved):
                        if destination.exists() and not source.exists():
                            destination.rename(source)
                    if operation_dir.exists():
                        shutil.rmtree(operation_dir)
                    quarantine_root = paper_dir / ".archive-quarantine"
                    if quarantine_root.exists() and not any(quarantine_root.iterdir()):
                        quarantine_root.rmdir()
                    raise
                shutil.rmtree(operation_dir)
                quarantine_root = paper_dir / ".archive-quarantine"
                if quarantine_root.exists() and not any(quarantine_root.iterdir()):
                    quarantine_root.rmdir()
                return self._operation(
                    operation="evict",
                    prior_status=prior_status,
                    record=evicted,
                    changed=True,
                    source_bytes=expected.total_size,
                    started=started,
                )
        except Exception as exc:
            category = self._category(exc, "archive_eviction_failed")
            if isinstance(exc, ArchiveWorkflowError):
                raise
            raise ArchiveWorkflowError(paper_key, category) from exc
        finally:
            if downloaded is not None:
                downloaded.unlink(missing_ok=True)

    def restore(self, paper_key: str) -> ArchiveOperation:
        started = time.monotonic()
        downloaded: Path | None = None
        extraction_root: Path | None = None
        prior = self.store.get(paper_key)
        prior_status = prior.status if prior is not None else None
        try:
            with paper_lock(self.lock_root, paper_key):
                record = self.store.get(paper_key)
                if record is None:
                    raise ArchiveWorkflowError(paper_key, "archive_not_found")
                paper_dir = self.store.paper_directory(paper_key)
                self._recover_quarantine(paper_key, paper_dir, record)
                if record.status == ArchiveStatus.AVAILABLE:
                    manifest = SourceManifest.from_json(record.source_manifest_json)
                    return self._operation(
                        operation="restore",
                        prior_status=prior_status,
                        record=record,
                        changed=False,
                        source_bytes=manifest.total_size,
                        started=started,
                    )
                if record.status != ArchiveStatus.EVICTED:
                    raise ArchiveWorkflowError(paper_key, "archive_not_evicted")
                manifest = SourceManifest.from_json(record.source_manifest_json)
                required = record.archive_size_bytes + manifest.total_size
                if shutil.disk_usage(self.staging_path.parent).free < required:
                    raise ArchiveWorkflowError(paper_key, "insufficient_free_space")
                self.store.transition(paper_key, ArchiveStatus.RESTORING)
                downloaded, validated_manifest = self._download_validated(
                    record,
                    "restore",
                )
                if validated_manifest != manifest:
                    raise ArchiveWorkflowError(paper_key, "archive_validation_failed")
                extraction_root = self.staging_path / f"restore.{uuid.uuid4().hex}"
                extraction_root.mkdir(parents=True)
                with tarfile.open(downloaded, mode="r:") as archive:
                    for member in archive:
                        target = extraction_root / member.name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        source = archive.extractfile(member)
                        if source is None:
                            raise ArchiveWorkflowError(paper_key, "archive_extract_failed")
                        with target.open("wb") as handle:
                            shutil.copyfileobj(source, handle)
                extracted_manifest = build_source_manifest(paper_key, extraction_root)
                if extracted_manifest != manifest:
                    raise ArchiveWorkflowError(paper_key, "restored_manifest_mismatch")
                installed: list[tuple[Path, Path]] = []
                try:
                    for name in ("paper.pdf", "figures"):
                        source = extraction_root / name
                        target = paper_dir / name
                        if not source.exists():
                            continue
                        if target.exists():
                            raise ArchiveWorkflowError(
                                paper_key,
                                "restore_target_conflict",
                            )
                        source.rename(target)
                        installed.append((source, target))
                    available = self.store.transition(
                        paper_key,
                        ArchiveStatus.AVAILABLE,
                    )
                except Exception:
                    for source, target in reversed(installed):
                        if target.exists() and not source.exists():
                            target.rename(source)
                    raise
                return self._operation(
                    operation="restore",
                    prior_status=prior_status,
                    record=available,
                    changed=True,
                    source_bytes=manifest.total_size,
                    started=started,
                )
        except Exception as exc:
            current = self.store.get(paper_key)
            if current is not None and current.status == ArchiveStatus.RESTORING:
                self.store.transition(paper_key, ArchiveStatus.EVICTED)
            category = self._category(exc, "archive_restore_failed")
            if isinstance(exc, ArchiveWorkflowError):
                raise
            raise ArchiveWorkflowError(paper_key, category) from exc
        finally:
            if downloaded is not None:
                downloaded.unlink(missing_ok=True)
            if extraction_root is not None and extraction_root.exists():
                shutil.rmtree(extraction_root)
