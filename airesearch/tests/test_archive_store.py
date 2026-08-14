from pathlib import Path

import pytest

from airesearch.archive_lock import ArchiveBusyError, paper_lock
from airesearch.archive_store import (
    ArchiveStatus,
    ArchiveStore,
    InvalidArchiveTransition,
)
from airesearch.db import connect, init_db


def insert_paper(db_path: Path, paper_key: str, paper_dir: Path) -> None:
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into papers (
                paper_key, title, authors_json, ids_json, paper_dir,
                meta_json, created_at, updated_at
            ) values (?, ?, '[]', '{}', ?, '{}', ?, ?)
            """,
            (paper_key, paper_key, str(paper_dir), "2026-06-19", "2026-06-19"),
        )
        conn.commit()


def make_store(tmp_path: Path) -> tuple[ArchiveStore, Path, Path]:
    paper_db = tmp_path / "paperpipe"
    paper_dir = paper_db / "papers" / "paper_a"
    paper_dir.mkdir(parents=True)
    (paper_dir / "paper.pdf").write_bytes(b"pdf")
    db_path = tmp_path / "airesearch.sqlite3"
    insert_paper(db_path, "paper_a", paper_dir)
    return ArchiveStore(db_path=db_path, paper_db_path=paper_db), db_path, paper_dir


def planned(store: ArchiveStore, paper_key: str = "paper_a", digest: str = "a" * 64):
    return store.upsert_planned(
        paper_key=paper_key,
        remote_name="gdrive",
        remote_path=f"papers/{paper_key}/{digest}.tar",
        archive_sha256=digest,
        archive_size_bytes=42,
        source_manifest_json='{"entries":[]}',
    )


def test_archive_store_applies_guarded_state_transitions(tmp_path: Path):
    store, _, _ = make_store(tmp_path)

    record = planned(store)
    assert record.status == ArchiveStatus.PLANNED

    uploaded = store.transition("paper_a", ArchiveStatus.UPLOADED)
    verified = store.transition(
        "paper_a",
        ArchiveStatus.VERIFIED,
        verified_at="2026-06-19T00:00:00+00:00",
    )

    assert uploaded.status == ArchiveStatus.UPLOADED
    assert verified.status == ArchiveStatus.VERIFIED
    assert verified.verified_at == "2026-06-19T00:00:00+00:00"
    with pytest.raises(InvalidArchiveTransition):
        store.transition("paper_a", ArchiveStatus.PLANNED)


def test_planning_preserves_verified_digest_and_rejects_replacement(tmp_path: Path):
    store, _, _ = make_store(tmp_path)
    planned(store)
    store.transition("paper_a", ArchiveStatus.UPLOADED)
    store.transition("paper_a", ArchiveStatus.VERIFIED)

    same = planned(store)
    assert same.status == ArchiveStatus.VERIFIED

    with pytest.raises(InvalidArchiveTransition, match="verified archive"):
        planned(store, digest="b" * 64)


def test_store_pins_archive_and_records_failure_without_secret_text(tmp_path: Path):
    store, _, _ = make_store(tmp_path)
    planned(store)

    pinned = store.set_pinned("paper_a", True)
    failed = store.transition(
        "paper_a",
        ArchiveStatus.FAILED,
        last_error="authentication_failed",
    )

    assert pinned.pinned is True
    assert failed.status == ArchiveStatus.FAILED
    assert failed.last_error == "authentication_failed"


def test_paper_lock_rejects_same_paper_and_allows_different_paper(tmp_path: Path):
    lock_root = tmp_path / "locks"

    with paper_lock(lock_root, "paper_a"):
        with pytest.raises(ArchiveBusyError, match="paper_a"):
            with paper_lock(lock_root, "paper_a"):
                pass
        with paper_lock(lock_root, "paper_b"):
            pass

    assert len(list(lock_root.glob("*.lock"))) == 2


def test_eligibility_uses_database_papers_and_reports_unreferenced_dirs(tmp_path: Path):
    store, _, _ = make_store(tmp_path)
    unreferenced = store.paper_db_path / "papers" / "not_synced"
    unreferenced.mkdir()

    report = store.eligible_papers(["paper_a", "missing"])

    assert [item.paper_key for item in report.eligible] == ["paper_a"]
    assert [(item.paper_key, item.reason) for item in report.excluded] == [
        ("missing", "missing_database_record")
    ]
    assert store.unreferenced_directories() == ("not_synced",)


def test_eligibility_rejects_paper_dir_outside_paper_database(tmp_path: Path):
    store, db_path, _ = make_store(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    with connect(db_path) as conn:
        conn.execute("update papers set paper_dir = ? where paper_key = 'paper_a'", (str(outside),))
        conn.commit()

    report = store.eligible_papers()

    assert report.eligible == ()
    assert report.excluded[0].reason == "paper_dir_outside_database"


@pytest.mark.parametrize(
    "blocker",
    ["ingest", "extraction", "fact_extraction", "admin_job"],
)
def test_eligibility_rejects_active_work(tmp_path: Path, blocker: str):
    store, db_path, _ = make_store(tmp_path)
    with connect(db_path) as conn:
        if blocker == "ingest":
            conn.execute(
                """
                insert into ingest_runs (
                    started_at, status
                ) values ('2026-06-19', 'running')
                """
            )
            run_id = conn.execute("select last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                insert into ingest_items (
                    run_id, line_number, raw_input, status, resolved_paper_key, started_at
                ) values (?, 1, 'paper_a', 'running', 'paper_a', '2026-06-19')
                """,
                (run_id,),
            )
        elif blocker == "extraction":
            conn.execute(
                """
                insert into extraction_runs (
                    extractor_name, extractor_version, paper_key, started_at, status
                ) values ('cards', '1', null, '2026-06-19', 'running')
                """
            )
        elif blocker == "fact_extraction":
            conn.execute(
                """
                insert into fact_extraction_runs (
                    provider_name, extractor_version, paper_key, started_at, status
                ) values ('fixture', '1', 'paper_a', '2026-06-19', 'running')
                """
            )
        else:
            conn.execute(
                """
                insert into admin_jobs (
                    job_type, status, started_at
                ) values ('rebuild_deploy', 'running', '2026-06-19')
                """
            )
        conn.commit()

    report = store.eligible_papers()

    assert report.eligible == ()
    assert report.excluded[0].reason == "active_paper_work"
