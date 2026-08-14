from __future__ import annotations

import hashlib
import json
import tarfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath


CHUNK_SIZE = 1024 * 1024


class ArchiveSafetyError(ValueError):
    pass


@dataclass(frozen=True)
class ArchiveEntry:
    path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class SourceManifest:
    paper_key: str
    entries: tuple[ArchiveEntry, ...]
    total_size: int

    def to_json(self) -> str:
        return json.dumps(
            {
                "paper_key": self.paper_key,
                "entries": [asdict(entry) for entry in self.entries],
                "total_size": self.total_size,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, value: str) -> SourceManifest:
        payload = json.loads(value)
        entries = tuple(ArchiveEntry(**entry) for entry in payload["entries"])
        manifest = cls(
            paper_key=str(payload["paper_key"]),
            entries=entries,
            total_size=int(payload["total_size"]),
        )
        _validate_manifest(manifest)
        return manifest


@dataclass(frozen=True)
class ArchiveFile:
    path: Path
    sha256: str
    size_bytes: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ArchiveSafetyError(f"unsafe archive path: {value}")
    return path


def _validate_manifest(manifest: SourceManifest) -> None:
    seen: set[str] = set()
    calculated_size = 0
    for entry in manifest.entries:
        path = _safe_relative_path(entry.path)
        if path.parts[0] != "paper.pdf" and path.parts[0] != "figures":
            raise ArchiveSafetyError(f"unexpected archive source: {entry.path}")
        if entry.path in seen:
            raise ArchiveSafetyError(f"duplicate archive path: {entry.path}")
        if entry.size_bytes < 0 or len(entry.sha256) != 64:
            raise ArchiveSafetyError(f"invalid archive entry metadata: {entry.path}")
        seen.add(entry.path)
        calculated_size += entry.size_bytes
    if calculated_size != manifest.total_size:
        raise ArchiveSafetyError("manifest total size mismatch")


def build_source_manifest(paper_key: str, paper_dir: Path) -> SourceManifest:
    paper_root = paper_dir.resolve(strict=True)
    candidates: list[Path] = []
    pdf_path = paper_dir / "paper.pdf"
    if pdf_path.is_symlink():
        raise ArchiveSafetyError("archive source is a symlink: paper.pdf")
    if pdf_path.is_file():
        candidates.append(pdf_path)

    figures_dir = paper_dir / "figures"
    if figures_dir.is_symlink():
        raise ArchiveSafetyError("archive source is a symlink: figures")
    if figures_dir.is_dir():
        for path in figures_dir.rglob("*"):
            if path.is_symlink():
                relative = path.relative_to(paper_dir).as_posix()
                raise ArchiveSafetyError(f"archive source is a symlink: {relative}")
            if path.is_file():
                candidates.append(path)

    entries: list[ArchiveEntry] = []
    for path in sorted(candidates, key=lambda item: item.relative_to(paper_dir).as_posix()):
        resolved = path.resolve(strict=True)
        try:
            resolved.relative_to(paper_root)
        except ValueError as exc:
            raise ArchiveSafetyError(f"archive source escapes paper directory: {path}") from exc
        relative = path.relative_to(paper_dir).as_posix()
        _safe_relative_path(relative)
        entries.append(
            ArchiveEntry(
                path=relative,
                size_bytes=path.stat().st_size,
                sha256=sha256_file(path),
            )
        )

    if not entries:
        raise ArchiveSafetyError("paper has no archive sources")
    return SourceManifest(
        paper_key=paper_key,
        entries=tuple(entries),
        total_size=sum(entry.size_bytes for entry in entries),
    )


def create_archive(
    manifest: SourceManifest,
    paper_dir: Path,
    destination: Path,
) -> ArchiveFile:
    _validate_manifest(manifest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for entry in manifest.entries:
            source = paper_dir / Path(entry.path)
            if source.is_symlink() or not source.is_file():
                raise ArchiveSafetyError(f"archive source is not a regular file: {entry.path}")
            if source.stat().st_size != entry.size_bytes or sha256_file(source) != entry.sha256:
                raise ArchiveSafetyError(f"archive source changed after inventory: {entry.path}")
            info = archive.gettarinfo(str(source), arcname=entry.path)
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            info.mode = 0o644
            info.pax_headers = {}
            with source.open("rb") as handle:
                archive.addfile(info, handle)
    return ArchiveFile(
        path=destination,
        sha256=sha256_file(destination),
        size_bytes=destination.stat().st_size,
    )


def validate_archive(path: Path, manifest: SourceManifest) -> ArchiveFile:
    _validate_manifest(manifest)
    expected = {entry.path: entry for entry in manifest.entries}
    seen: set[str] = set()
    try:
        with tarfile.open(path, mode="r:") as archive:
            for member in archive:
                member_path = _safe_relative_path(member.name).as_posix()
                if not member.isreg():
                    raise ArchiveSafetyError(f"archive member is not a regular file: {member_path}")
                if member_path in seen:
                    raise ArchiveSafetyError(f"duplicate archive member: {member_path}")
                entry = expected.get(member_path)
                if entry is None:
                    raise ArchiveSafetyError(f"unexpected archive member: {member_path}")
                if member.size != entry.size_bytes:
                    raise ArchiveSafetyError(f"archive member size mismatch: {member_path}")
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise ArchiveSafetyError(f"cannot read archive member: {member_path}")
                digest = hashlib.sha256()
                for chunk in iter(lambda: extracted.read(CHUNK_SIZE), b""):
                    digest.update(chunk)
                if digest.hexdigest() != entry.sha256:
                    raise ArchiveSafetyError(f"archive member digest mismatch: {member_path}")
                seen.add(member_path)
    except tarfile.TarError as exc:
        raise ArchiveSafetyError(f"invalid tar archive: {path}") from exc

    missing = sorted(set(expected) - seen)
    if missing:
        raise ArchiveSafetyError(f"archive members missing: {', '.join(missing)}")
    return ArchiveFile(path=path, sha256=sha256_file(path), size_bytes=path.stat().st_size)
