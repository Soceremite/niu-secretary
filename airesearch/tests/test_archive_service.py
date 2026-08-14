import json
import shutil
from collections import namedtuple
from pathlib import Path

import pytest

from airesearch.archive_remote import RcloneRemote
from airesearch.archive_service import ArchiveService, ArchiveWorkflowError
from airesearch.archive_store import ArchiveStatus
from airesearch.db import connect
from airesearch.paperpipe_sync import sync_paperpipe
from test_archive_remote import make_fake_rclone


def make_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[ArchiveService, Path, Path, Path]:
    fixture = Path(__file__).parent / "fixtures" / "paperpipe_db"
    paper_db = tmp_path / "paperpipe"
    shutil.copytree(fixture, paper_db)
    db_path = tmp_path / "airesearch.sqlite3"
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    executable = make_fake_rclone(tmp_path, monkeypatch)
    remote = RcloneRemote(
        executable=str(executable),
        remote_root="gdrive:niu-secretary/airesearch/v1",
    )
    service = ArchiveService(
        db_path=db_path,
        paper_db_path=paper_db,
        staging_path=tmp_path / "staging",
        remote=remote,
        lock_root=tmp_path / "locks",
    )
    paper_dir = paper_db / "papers" / "1706_03762"
    return service, db_path, paper_dir, tmp_path / "remote"


def remote_object(remote_root: Path, relative_path: str) -> Path:
    return (
        remote_root
        / "objects"
        / "niu-secretary"
        / "airesearch"
        / "v1"
        / relative_path
    )


def test_plan_is_read_only_until_record_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, _, _, _ = make_service(tmp_path, monkeypatch)

    preview = service.plan(record=False)

    assert preview.eligible_count == 1
    assert preview.excluded_count == 0
    assert preview.reclaimable_bytes > 0
    assert service.store.get("1706_03762") is None

    recorded = service.plan(["1706_03762"], record=True)

    assert recorded.eligible_count == 1
    assert service.store.get("1706_03762").status == ArchiveStatus.PLANNED
    assert list(service.staging_path.glob("*.tar")) == []


def test_upload_then_verify_keeps_local_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, _, paper_dir, _ = make_service(tmp_path, monkeypatch)

    uploaded = service.upload("1706_03762")
    verified = service.verify("1706_03762")

    assert uploaded.status == ArchiveStatus.UPLOADED
    assert verified.status == ArchiveStatus.VERIFIED
    assert verified.verified_at is not None
    assert (paper_dir / "paper.pdf").exists()
    assert (paper_dir / "figures").exists()
    assert list(service.staging_path.glob("*.tar")) == []


def test_upload_reuses_existing_final_digest_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, _, _, remote_root = make_service(tmp_path, monkeypatch)
    first = service.upload("1706_03762")
    command_log = remote_root / "commands.jsonl"
    before = command_log.read_text(encoding="utf-8").splitlines()

    second = service.upload("1706_03762")
    after = command_log.read_text(encoding="utf-8").splitlines()

    assert second.status == ArchiveStatus.UPLOADED
    assert second.archive_sha256 == first.archive_sha256
    assert len(after) == len(before) + 1
    assert json.loads(after[-1])[0] == "lsjson"


def test_upload_rejects_existing_remote_size_mismatch_and_keeps_local_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, _, paper_dir, remote_root = make_service(tmp_path, monkeypatch)
    service.plan(["1706_03762"], record=True)
    record = service.store.get("1706_03762")
    target = remote_object(remote_root, record.remote_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"wrong")

    with pytest.raises(ArchiveWorkflowError, match="remote_size_mismatch"):
        service.upload("1706_03762")

    assert service.store.get("1706_03762").status == ArchiveStatus.FAILED
    assert (paper_dir / "paper.pdf").exists()


def test_verify_rejects_remote_digest_drift_without_downgrading_verified(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, _, paper_dir, remote_root = make_service(tmp_path, monkeypatch)
    service.upload("1706_03762")
    verified = service.verify("1706_03762")
    target = remote_object(remote_root, verified.remote_path)
    payload = bytearray(target.read_bytes())
    payload[-1] ^= 1
    target.write_bytes(payload)

    with pytest.raises(ArchiveWorkflowError, match="archive_digest_mismatch"):
        service.verify("1706_03762")

    assert service.store.get("1706_03762").status == ArchiveStatus.VERIFIED
    assert (paper_dir / "paper.pdf").exists()


def test_verify_rejects_manifest_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, db_path, paper_dir, _ = make_service(tmp_path, monkeypatch)
    service.upload("1706_03762")
    record = service.store.get("1706_03762")
    manifest = json.loads(record.source_manifest_json)
    manifest["entries"][0]["sha256"] = "0" * 64
    with connect(db_path) as conn:
        conn.execute(
            "update paper_archives set source_manifest_json = ? where paper_key = ?",
            (json.dumps(manifest), "1706_03762"),
        )
        conn.commit()

    with pytest.raises(ArchiveWorkflowError, match="archive_validation_failed"):
        service.verify("1706_03762")

    assert service.store.get("1706_03762").status == ArchiveStatus.FAILED
    assert (paper_dir / "paper.pdf").exists()


def test_upload_can_retry_after_remote_authentication_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, _, paper_dir, _ = make_service(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_RCLONE_FAIL", "1")

    with pytest.raises(ArchiveWorkflowError, match="authentication_failed"):
        service.upload("1706_03762")

    assert service.store.get("1706_03762").status == ArchiveStatus.FAILED
    monkeypatch.delenv("FAKE_RCLONE_FAIL")

    retried = service.upload("1706_03762")

    assert retried.status == ArchiveStatus.UPLOADED
    assert (paper_dir / "paper.pdf").exists()


def verified_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    service, db_path, paper_dir, remote_root = make_service(tmp_path, monkeypatch)
    service.upload("1706_03762")
    service.verify("1706_03762")
    return service, db_path, paper_dir, remote_root


def test_evict_defaults_to_dry_run_and_respects_pin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, _, paper_dir, _ = verified_service(tmp_path, monkeypatch)

    preview = service.evict("1706_03762", apply=False)

    assert preview.changed is False
    assert preview.status == ArchiveStatus.VERIFIED
    assert (paper_dir / "paper.pdf").exists()

    service.store.set_pinned("1706_03762", True)
    with pytest.raises(ArchiveWorkflowError, match="archive_pinned"):
        service.evict("1706_03762", apply=True)


def test_evict_and_restore_round_trip_all_manifest_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, _, paper_dir, _ = verified_service(tmp_path, monkeypatch)
    record = service.store.get("1706_03762")
    before = json.loads(record.source_manifest_json)

    evicted = service.evict("1706_03762", apply=True)
    restored = service.restore("1706_03762")

    assert evicted.status == ArchiveStatus.EVICTED
    assert not (paper_dir / ".archive-quarantine").exists()
    assert restored.status == ArchiveStatus.AVAILABLE
    for entry in before["entries"]:
        path = paper_dir / entry["path"]
        assert path.exists()
        from airesearch.archive_manifest import sha256_file
        assert sha256_file(path) == entry["sha256"]


def test_evict_rejects_local_manifest_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, _, paper_dir, _ = verified_service(tmp_path, monkeypatch)
    (paper_dir / "paper.pdf").write_bytes(b"changed")

    with pytest.raises(ArchiveWorkflowError, match="local_manifest_drift"):
        service.evict("1706_03762", apply=True)

    assert (paper_dir / "paper.pdf").read_bytes() == b"changed"
    assert service.store.get("1706_03762").status == ArchiveStatus.VERIFIED


def test_evict_rolls_back_quarantine_when_database_transition_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, _, paper_dir, _ = verified_service(tmp_path, monkeypatch)
    original_transition = service.store.transition

    def fail_eviction(paper_key, status, **kwargs):
        if status == ArchiveStatus.EVICTED:
            raise RuntimeError("database unavailable")
        return original_transition(paper_key, status, **kwargs)

    monkeypatch.setattr(service.store, "transition", fail_eviction)

    with pytest.raises(ArchiveWorkflowError, match="archive_eviction_failed"):
        service.evict("1706_03762", apply=True)

    assert (paper_dir / "paper.pdf").exists()
    assert (paper_dir / "figures").exists()


def test_restore_rejects_insufficient_free_space(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, _, paper_dir, _ = verified_service(tmp_path, monkeypatch)
    service.evict("1706_03762", apply=True)
    Usage = namedtuple("Usage", "total used free")
    monkeypatch.setattr(
        "airesearch.archive_service.shutil.disk_usage",
        lambda _: Usage(100, 100, 0),
    )

    with pytest.raises(ArchiveWorkflowError, match="insufficient_free_space"):
        service.restore("1706_03762")

    assert not (paper_dir / "paper.pdf").exists()
    assert service.store.get("1706_03762").status == ArchiveStatus.EVICTED


def test_evict_recovers_interrupted_quarantine_before_preview(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, _, paper_dir, _ = verified_service(tmp_path, monkeypatch)
    operation = paper_dir / ".archive-quarantine" / "interrupted"
    operation.mkdir(parents=True)
    (paper_dir / "paper.pdf").rename(operation / "paper.pdf")
    (paper_dir / "figures").rename(operation / "figures")

    preview = service.evict("1706_03762", apply=False)

    assert preview.changed is False
    assert (paper_dir / "paper.pdf").exists()
    assert (paper_dir / "figures").exists()
    assert not (paper_dir / ".archive-quarantine").exists()


def test_restore_refuses_to_overwrite_different_local_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    service, _, paper_dir, _ = verified_service(tmp_path, monkeypatch)
    service.evict("1706_03762", apply=True)
    (paper_dir / "paper.pdf").write_bytes(b"operator-file")

    with pytest.raises(ArchiveWorkflowError, match="restore_target_conflict"):
        service.restore("1706_03762")

    assert (paper_dir / "paper.pdf").read_bytes() == b"operator-file"
    assert service.store.get("1706_03762").status == ArchiveStatus.EVICTED
