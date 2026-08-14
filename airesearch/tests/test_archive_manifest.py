import io
import tarfile
from pathlib import Path

import pytest

from airesearch.archive_manifest import (
    ArchiveEntry,
    ArchiveSafetyError,
    SourceManifest,
    build_source_manifest,
    create_archive,
    validate_archive,
)


def make_paper(tmp_path: Path) -> Path:
    paper_dir = tmp_path / "papers" / "paper_a"
    figures_dir = paper_dir / "figures"
    figures_dir.mkdir(parents=True)
    (paper_dir / "paper.pdf").write_bytes(b"pdf")
    (figures_dir / "chart.webp").write_bytes(b"figure")
    (paper_dir / "cover.webp").write_bytes(b"cover")
    (paper_dir / "source.tex").write_text("source", encoding="utf-8")
    return paper_dir


def test_manifest_contains_only_archive_sources_and_round_trips(tmp_path: Path):
    paper_dir = make_paper(tmp_path)

    manifest = build_source_manifest("paper_a", paper_dir)
    restored = SourceManifest.from_json(manifest.to_json())

    assert [entry.path for entry in manifest.entries] == [
        "figures/chart.webp",
        "paper.pdf",
    ]
    assert manifest.total_size == len(b"figure") + len(b"pdf")
    assert restored == manifest


def test_archive_is_deterministic_and_validates_content(tmp_path: Path):
    paper_dir = make_paper(tmp_path)
    manifest = build_source_manifest("paper_a", paper_dir)

    first = create_archive(manifest, paper_dir, tmp_path / "first.tar")
    second = create_archive(manifest, paper_dir, tmp_path / "second.tar")

    assert first.sha256 == second.sha256
    assert first.size_bytes == second.size_bytes
    assert first.path.read_bytes() == second.path.read_bytes()
    assert validate_archive(first.path, manifest) == first


def test_manifest_rejects_symlinked_archive_source(tmp_path: Path):
    paper_dir = make_paper(tmp_path)
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")
    (paper_dir / "figures" / "linked.png").symlink_to(outside)

    with pytest.raises(ArchiveSafetyError, match="symlink"):
        build_source_manifest("paper_a", paper_dir)


def test_validate_archive_rejects_manifest_traversal(tmp_path: Path):
    archive_path = tmp_path / "empty.tar"
    with tarfile.open(archive_path, "w"):
        pass
    manifest = SourceManifest(
        paper_key="paper_a",
        entries=(ArchiveEntry(path="../escape", size_bytes=1, sha256="0" * 64),),
        total_size=1,
    )

    with pytest.raises(ArchiveSafetyError, match="unsafe archive path"):
        validate_archive(archive_path, manifest)


def test_validate_archive_rejects_absolute_member(tmp_path: Path):
    archive_path = tmp_path / "malicious.tar"
    with tarfile.open(archive_path, "w") as archive:
        info = tarfile.TarInfo("/tmp/escape")
        info.size = 1
        archive.addfile(info, io.BytesIO(b"x"))
    manifest = SourceManifest(paper_key="paper_a", entries=(), total_size=0)

    with pytest.raises(ArchiveSafetyError, match="unsafe archive path"):
        validate_archive(archive_path, manifest)


def test_validate_archive_rejects_digest_drift(tmp_path: Path):
    paper_dir = make_paper(tmp_path)
    manifest = build_source_manifest("paper_a", paper_dir)
    archive = create_archive(manifest, paper_dir, tmp_path / "paper.tar")
    drifted = SourceManifest(
        paper_key=manifest.paper_key,
        entries=tuple(
            ArchiveEntry(entry.path, entry.size_bytes, "0" * 64)
            if entry.path == "paper.pdf"
            else entry
            for entry in manifest.entries
        ),
        total_size=manifest.total_size,
    )

    with pytest.raises(ArchiveSafetyError, match="digest mismatch"):
        validate_archive(archive.path, drifted)


def test_manifest_rejects_paper_without_archive_sources(tmp_path: Path):
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "cover.webp").write_bytes(b"cover")

    with pytest.raises(ArchiveSafetyError, match="no archive sources"):
        build_source_manifest("paper_a", paper_dir)
