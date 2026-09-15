#!/usr/bin/env python3
"""Fetch leisure candidates from public charts (douban movies, netease music,
douban new books). No LLM: pure HTTP + regex. Output: leisure/dist/data/candidates.json.

Posters came straight from the chart pages (doubanio CDN), so coverUrl is real
and image_review has something meaningful to check.
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "dist" / "data" / "candidates.json"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 NiuLeisure/1.0"


def fetch(url: str, timeout: float = 15.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def douban_new_movies(limit: int = 8) -> list[dict]:
    try:
        html = fetch("https://movie.douban.com/chart")
    except Exception as exc:
        print(f"  ! douban movies: {exc}")
        return []
    rows = re.findall(r'<div class="pl2">\s*<a[^>]*href="([^"]+)"[^>]*>\s*(.*?)</a>', html, re.S)
    posters = re.findall(r'src="(https://img\d\.doubanio\.com/[^"]+)"', html)
    posters = [p for p in posters if "/view/photo/" in p]
    out = []
    for i, (url, inner) in enumerate(rows[:limit]):
        raw_title = re.sub(r"<[^>]+>", "", inner).strip()
        # Titles look like "求救信号\n / 求救暗号 / 碍的迫降": keep only the Chinese main title cell
        title = raw_title.split("\n")[0].strip() or raw_title[:40]
        out.append({
            "title": title[:60],
            "doubanUrl": url,
            "coverUrl": posters[i] if i < len(posters) else "",
            "source": "豆瓣新片榜",
        })
    return out


def netease_hot_songs(limit: int = 8) -> list[dict]:
    try:
        data = json.loads(fetch("https://music.163.com/api/playlist/detail?id=3778678"))
        tracks = (data.get("result") or {}).get("tracks") or []
        out = []
        for t in tracks[:limit]:
            artists = " / ".join(a.get("name", "") for a in (t.get("artists") or [])[:2])
            out.append({
                "title": t.get("name", "")[:60],
                "artist": artists,
                "album": (t.get("album") or {}).get("name", "")[:60],
                "platformUrl": f"https://music.163.com/#/song?id={t.get('id','')}",
                "source": "网易云音乐热歌榜",
            })
        return out
    except Exception as exc:
        print(f"  ! netease music: {exc}")
        return []


def douban_new_books(limit: int = 6) -> list[dict]:
    try:
        html = fetch("https://book.douban.com/latest?subcat=%E5%85%A8%E9%83%A8")
        entries = []
        for li in re.findall(r'<li[^>]*class="media[^"]*"[^>]*>(.*?)</li>', html, re.S):
            link = re.search(r'href="(https://book\.douban\.com/subject/\d+/)"', li)
            title = re.search(r'<h2[^>]*>\s*<a[^>]*>(.*?)</a>', li, re.S)
            img = re.search(r'<img[^>]*src="(https://img\d\.doubanio\.com/[^"]+)"', li)
            author = re.search(r'class="subject-abstract[^"]*">\s*(\[[^\]]+\]|[^\s/][^/]*)', li)
            if link and title:
                entries.append((
                    link.group(1),
                    (img.group(1) if img else ""),
                    re.sub(r"<[^>]+>", "", title.group(1)).strip(),
                    (re.sub(r"<[^>]+>", "", author.group(1)).strip() if author else ""),
                ))
        out = []
        for i, (url, cover, title, author) in enumerate(entries[:limit]):
            out.append({
                "title": title[:60],
                "author": author[:30],
                "doubanUrl": url,
                "coverUrl": cover,
                "source": "豆瓣新书速递",
            })
        return out
    except Exception as exc:
        print(f"  ! douban books: {exc}")
        return []


def main() -> int:
    print("fetching leisure candidates...")
    movies = douban_new_movies()
    music = netease_hot_songs()
    novels = douban_new_books()
    # Podcasts have no free chart API the platforms agree on: carry last-known items onward (LLM refreshes descriptions)
    podcasts: list[dict] = []
    try:
        current = json.loads((HERE / "dist" / "data" / "podcasts.json").read_text(encoding="utf-8"))
        podcasts = (current if isinstance(current, list) else current.get("items", []))[:5]
    except Exception:
        pass

    payload = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "movies": movies,
        "music": music,
        "podcasts": podcasts,
        "novels": novels,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = {k: len(v) for k, v in payload.items() if k != "generated"}
    print("counts:", counts)
    if movies or music or novels:
        return 0
    print("ERROR: all leisure chart fetches failed", file=__import__("sys").stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
