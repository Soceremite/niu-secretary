from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from airesearch.db import connect, init_db


GITHUB_RE = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)
TRAILING_RE = re.compile(r"[),.;:}>\\]+$")


@dataclass(frozen=True)
class CodeLink:
    url: str
    host: str
    owner: str
    repo: str
    source_type: str
    source_path: str
    context: str


@dataclass(frozen=True)
class CodeLinkResult:
    papers_seen: int
    links_written: int


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def parse_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def normalize_repo(repo: str) -> str:
    repo = TRAILING_RE.sub("", repo.strip())
    if repo.endswith(".git"):
        repo = repo[:-4]
    return repo


def context_window(text: str, start: int, end: int, width: int = 100) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    return " ".join(text[left:right].split())


def extract_github_links_from_text(text: str, *, source_type: str, source_path: str = "") -> list[CodeLink]:
    links: list[CodeLink] = []
    seen: set[str] = set()
    for match in GITHUB_RE.finditer(text):
        owner = match.group(1).strip()
        repo = normalize_repo(match.group(2))
        if not owner or not repo:
            continue
        url = f"https://github.com/{owner}/{repo}"
        key = url.lower()
        if key in seen:
            continue
        seen.add(key)
        links.append(
            CodeLink(
                url=url,
                host="github.com",
                owner=owner,
                repo=repo,
                source_type=source_type,
                source_path=source_path,
                context=context_window(text, match.start(), match.end()),
            )
        )
    return links


def load_papers(conn, *, limit: int | None, paper_key: str | None):
    sql = "select * from papers"
    params: list[Any] = []
    if paper_key:
        sql += " where paper_key = ?"
        params.append(paper_key)
    sql += " order by updated_at desc, paper_key"
    if limit is not None:
        sql += " limit ?"
        params.append(limit)
    return conn.execute(sql, params).fetchall()


def source_tex_artifacts(conn, paper_key: str):
    return conn.execute(
        """
        select path from paper_artifacts
        where paper_key = ? and artifact_type = 'source_tex'
        order by path
        """,
        (paper_key,),
    ).fetchall()


def links_for_paper(conn, paper) -> list[CodeLink]:
    links: list[CodeLink] = []
    meta = parse_json(paper["meta_json"], {})
    meta_text = "\n".join(iter_strings(meta))
    if meta_text:
        links.extend(extract_github_links_from_text(meta_text, source_type="meta_json"))
    for artifact in source_tex_artifacts(conn, paper["paper_key"]):
        path = Path(artifact["path"])
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        links.extend(extract_github_links_from_text(text, source_type="source_tex", source_path=str(path)))
    deduped: dict[str, CodeLink] = {}
    for link in links:
        deduped.setdefault(link.url.lower(), link)
    return list(deduped.values())


def extract_code_links(db_path: Path, *, limit: int | None = None, paper_key: str | None = None) -> CodeLinkResult:
    init_db(db_path)
    now = utc_now()
    with connect(db_path) as conn:
        papers = load_papers(conn, limit=limit, paper_key=paper_key)
        written = 0
        for paper in papers:
            conn.execute("delete from paper_code_links where paper_key = ?", (paper["paper_key"],))
            for link in links_for_paper(conn, paper):
                conn.execute(
                    """
                    insert into paper_code_links (
                        paper_key, url, host, owner, repo, source_type,
                        source_path, context, created_at, updated_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    on conflict(paper_key, url, source_type, source_path) do update set
                        host = excluded.host,
                        owner = excluded.owner,
                        repo = excluded.repo,
                        context = excluded.context,
                        updated_at = excluded.updated_at
                    """,
                    (
                        paper["paper_key"],
                        link.url,
                        link.host,
                        link.owner,
                        link.repo,
                        link.source_type,
                        link.source_path,
                        link.context,
                        now,
                        now,
                    ),
                )
                written += 1
        conn.commit()
    return CodeLinkResult(papers_seen=len(papers), links_written=written)


def list_code_links(db_path: Path, *, paper_key: str | None = None, limit: int = 20):
    init_db(db_path)
    sql = "select * from paper_code_links"
    params: list[Any] = []
    if paper_key:
        sql += " where paper_key = ?"
        params.append(paper_key)
    sql += " order by paper_key, url limit ?"
    params.append(limit)
    with connect(db_path) as conn:
        return conn.execute(sql, params).fetchall()


def export_code_links(db_path: Path, out_path: Path) -> int:
    rows = list_code_links(db_path, limit=1_000_000)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = {
                "paper_key": row["paper_key"],
                "url": row["url"],
                "host": row["host"],
                "owner": row["owner"],
                "repo": row["repo"],
                "source_type": row["source_type"],
                "source_path": row["source_path"],
                "context": row["context"],
            }
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)
