from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db


ARTIFACT_TYPES = {
    "paper.pdf": "paper_pdf",
    "source.tex": "source_tex",
    "summary.md": "summary",
    "summary.zh.md": "summary_zh",
    "equations.md": "equations",
    "tldr.md": "tldr",
    "tldr.zh.md": "tldr_zh",
    "notes.md": "notes",
}

FIGURE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".svg")


@dataclass(frozen=True)
class SyncResult:
    papers_seen: int
    artifacts_seen: int


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_year(meta: dict[str, Any]) -> int | None:
    published = str(meta.get("published") or "")
    if len(published) >= 4 and published[:4].isdigit():
        return int(published[:4])
    year = meta.get("year")
    return int(year) if isinstance(year, int) else None


def source_pairs(meta: dict[str, Any], index_entry: dict[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for key in ("arxiv_id", "doi", "s2_id", "url"):
        value = meta.get(key) or index_entry.get(key)
        if value:
            pairs.append((key, str(value)))
    title = meta.get("title") or index_entry.get("title")
    if title:
        pairs.append(("title", str(title)))
    return pairs


def sync_paperpipe(*, db_path: Path, paper_db_path: Path) -> SyncResult:
    init_db(db_path)
    started_at = utc_now()
    index = read_json(paper_db_path / "index.json")
    papers_seen = 0
    artifacts_seen = 0

    with connect(db_path) as conn:
        for paper_key, index_entry in index.items():
            if not isinstance(index_entry, dict):
                index_entry = {}
            paper_dir = paper_db_path / "papers" / paper_key
            meta = read_json(paper_dir / "meta.json")
            merged = {**index_entry, **meta}
            now = utc_now()
            conn.execute(
                """
                insert into papers (
                    paper_key, title, authors_json, year, venue, ids_json,
                    paper_dir, meta_json, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(paper_key) do update set
                    title = excluded.title,
                    authors_json = excluded.authors_json,
                    year = excluded.year,
                    venue = excluded.venue,
                    ids_json = excluded.ids_json,
                    paper_dir = excluded.paper_dir,
                    meta_json = excluded.meta_json,
                    updated_at = excluded.updated_at
                """,
                (
                    paper_key,
                    merged.get("title"),
                    stable_json(merged.get("authors", [])),
                    extract_year(merged),
                    merged.get("venue"),
                    stable_json(
                        {
                            "arxiv_id": merged.get("arxiv_id"),
                            "doi": merged.get("doi"),
                            "s2_id": merged.get("s2_id"),
                            "url": merged.get("url"),
                        }
                    ),
                    str(paper_dir),
                    stable_json(merged),
                    now,
                    now,
                ),
            )
            papers_seen += 1

            for source_type, source_value in source_pairs(meta, index_entry):
                conn.execute(
                    """
                    insert or ignore into paper_sources
                        (paper_key, source_type, source_value, created_at)
                    values (?, ?, ?, ?)
                    """,
                    (paper_key, source_type, source_value, now),
                )

            artifact_pairs: list[tuple[Path, str]] = []
            for filename, artifact_type in ARTIFACT_TYPES.items():
                artifact_path = paper_dir / filename
                if artifact_path.exists():
                    artifact_pairs.append((artifact_path, artifact_type))
            for cover_name in ("cover.webp", "cover.png", "cover.jpg", "cover.jpeg", "cover.svg"):
                cover_path = paper_dir / cover_name
                if cover_path.exists():
                    artifact_pairs.append((cover_path, "cover"))
                    break
            figures_dir = paper_dir / "figures"
            if figures_dir.exists():
                for figure_path in sorted(path for path in figures_dir.iterdir() if path.suffix.lower() in FIGURE_SUFFIXES):
                    if figure_path.is_file():
                        artifact_pairs.append((figure_path, "figure"))

            for artifact_path, artifact_type in artifact_pairs:
                stat = artifact_path.stat()
                conn.execute(
                    """
                    insert into paper_artifacts (
                        paper_key, artifact_type, path, sha256, size_bytes, updated_at
                    )
                    values (?, ?, ?, ?, ?, ?)
                    on conflict(paper_key, artifact_type, path) do update set
                        sha256 = excluded.sha256,
                        size_bytes = excluded.size_bytes,
                        updated_at = excluded.updated_at
                    """,
                    (
                        paper_key,
                        artifact_type,
                        str(artifact_path),
                        sha256_file(artifact_path),
                        stat.st_size,
                        now,
                    ),
                )
                artifacts_seen += 1

        finished_at = utc_now()
        conn.execute(
            """
            insert into sync_events (
                paper_db_path, papers_seen, artifacts_seen,
                started_at, finished_at, status
            )
            values (?, ?, ?, ?, ?, ?)
            """,
            (str(paper_db_path), papers_seen, artifacts_seen, started_at, finished_at, "success"),
        )
        conn.commit()

    return SyncResult(papers_seen=papers_seen, artifacts_seen=artifacts_seen)
