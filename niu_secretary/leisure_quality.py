from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


BROKEN_DOUBAN_URLS = {
    "https://movie.douban.com/subject/",
    "http://movie.douban.com/subject/",
}


def _load_movies(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [item for item in payload["items"] if isinstance(item, dict)]
    return []


def is_valid_douban_subject_url(value: str) -> bool:
    value = (value or "").strip()
    if value in BROKEN_DOUBAN_URLS:
        return False
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc != "movie.douban.com":
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) >= 2 and parts[0] == "subject" and parts[1].isdigit()


def collect_movie_quality_errors(movies: list[dict], *, require_any_cover: bool = True) -> list[str]:
    errors: list[str] = []
    if not movies:
        return ["movies.json: expected non-empty movie list"]

    cover_count = 0
    for index, movie in enumerate(movies, start=1):
        ident = str(movie.get("id") or f"#{index}")
        title = str(movie.get("title") or "<untitled>")
        douban_url = str(movie.get("doubanUrl") or "").strip()
        cover_url = str(movie.get("coverUrl") or "").strip()
        if cover_url:
            cover_count += 1
        if not is_valid_douban_subject_url(douban_url):
            errors.append(f"{ident} {title}: invalid doubanUrl {douban_url!r}")

    if require_any_cover and cover_count == 0:
        errors.append("movies.json: all movie coverUrl values are empty")
    return errors


def validate_movie_file(path: Path, *, require_any_cover: bool = True) -> list[str]:
    return collect_movie_quality_errors(_load_movies(path), require_any_cover=require_any_cover)
