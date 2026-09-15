#!/usr/bin/env python3
"""Generate leisure recommendation JSONs from fetched candidates.

Reads dist/data/candidates.json, asks the unified LLM ("content") for
per-item recommendation reasons + matchScore + mood, then writes the live
data files (movies/music/podcasts/novels/context.json). Also writes a
QQ-facing digest to dist/qq_digest.txt.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from niu_core.llm_client import NiuLLM  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "dist" / "data"
CANDIDATES = DATA / "candidates.json"

SCHEMA = {
    "movies": ["id", "title", "titleOriginal", "type", "year", "genres", "region",
               "duration", "doubanRating", "matchScore", "reason", "mood",
               "coverUrl", "doubanUrl", "director", "actors"],
    "music": ["id", "title", "type", "genre", "language", "trackCount",
              "matchScore", "reason", "mood", "scene", "platformUrl", "artist"],
}

SYSTEM = (
    "你是牛秘书的闲趣推荐编辑。为每条候选写 reason(50-90字中文,亲切自然)、matchScore(60-95)、"
    "mood(2-6字情绪标签)。不编造评分、导演、演员、年份——没有的信息写空字符串。"
    "只输出 JSON,外形 {\"movies\":[{\"i\":1,\"reason\":\"..\",\"matchScore\":70,\"mood\":\"..\"}],"
    "\"music\":[...],\"novels\":[...]},i 从 1 开始对应候选序号。不要输出任何其他文字。"
)


def llm_json(llm: NiuLLM, prompt: str) -> dict:
    rsp = llm.chat("content", [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
    ], temperature=0.3, max_tokens=6000)
    text = re.sub(r"^```(?:json)?\s*", "", rsp.text.strip())
    text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return {}


def main() -> int:
    cands = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    schedule_n, fitness_note = 0, "未获取"
    try:
        sched = json.loads(Path("/home/ubuntu/vibe_proj/niu-secretary/exports/niu-secretary/schedule.json").read_text() or "{}")
        schedule_n = len(sched.get("events", []))
    except Exception:
        pass
    busy = "轻松" if schedule_n <= 2 else ("适中" if schedule_n <= 4 else "繁忙")
    strategy = {"轻松": "烧脑沉浸", "适中": "平衡舒缓", "繁忙": "轻量放松"}.get(busy) or "平衡舒缓"

    llm = NiuLLM.load()

    movie_lines = "\n".join(f"{i+1}. {m['title']} ({m.get('source','')})" for i, m in enumerate(cands["movies"][:5]))
    music_lines = "\n".join(f"{i+1}. {m['title']} — {m.get('artist','')} ({m.get('album','')})" for i, m in enumerate(cands["music"][:5]))
    book_lines = "\n".join(f"{i+1}. {n['title']} — {n.get('author','')}" for i, n in enumerate(cands["novels"][:4]))
    podcast_lines = "\n".join(f"{i+1}. {p.get('title','')} ({p.get('podcast','')})" for i, p in enumerate(cands["podcasts"][:4]))

    prompt = f"""今日推荐策略: {strategy}（今日日程 {schedule_n} 项）

为以下候选写推荐理由。候选:
[电影]
{movie_lines}

[音乐]
{music_lines}

[小说]
{book_lines}

"""
    parsed = llm_json(llm, prompt)
    if not parsed:
        print("LLM returned unparseable JSON — aborting without touching live data", file=__import__("sys").stderr)
        return 1

    def attach(items, patch_keys, prefix):
        out = []
        for i, it in enumerate(items, 1):
            llm_row = next((r for r in parsed.get(patch_keys, []) if r.get("i") == i or r.get("n") == i), {})
            row = {
                "id": f"{patch_keys[0][:3]}_{datetime.now().strftime('%m%d')}_{i:02d}",
                **it,
                "matchScore": llm_row.get("matchScore") or 75,
                "reason": llm_row.get("reason") or f"{it['title']}——今日上榜，值得一看。",
                "mood": llm_row.get("mood") or strategy,
            }
            out.append(row)
        return out

    movies_out = []
    for i, m in enumerate(cands["movies"][:5], 1):
        llm_row = next((r for r in parsed.get("movies", []) if r.get("i") == i), {})
        movies_out.append({
            "id": f"mov_{datetime.now().strftime('%m%d')}_{i:02d}",
            "title": m["title"],
            "titleOriginal": "",
            "type": "电影",
            "year": datetime.now().year,
            "genres": [],
            "region": "",
            "duration": "未知",
            "doubanRating": None,
            "matchScore": llm_row.get("matchScore") or 75,
            "reason": llm_row.get("reason") or f"{m['title']}——豆瓣新片上榜。",
            "mood": llm_row.get("mood") or strategy,
            "coverUrl": m.get("coverUrl", ""),
            "doubanUrl": m.get("doubanUrl", ""),
            "director": "",
            "actors": [],
        })

    music_out = []
    for i, m in enumerate(cands["music"][:5], 1):
        llm_row = next((r for r in parsed.get("music", []) if r.get("i") == i), {})
        music_out.append({
            "id": f"mus_{datetime.now().strftime('%m%d')}_{i:02d}",
            "title": m["title"],
            "type": "歌曲",
            "genre": "流行",
            "language": "中文",
            "artist": m.get("artist", ""),
            "matchScore": llm_row.get("matchScore") or 75,
            "reason": llm_row.get("reason") or f"{m['title']}——热歌榜在列。",
            "mood": llm_row.get("mood") or strategy,
            "scene": "通勤/休息",
            "platformUrl": m.get("platformUrl", ""),
        })

    novels_out = []
    for i, n in enumerate(cands["novels"][:4], 1):
        llm_row = next((r for r in parsed.get("novels", []) if r.get("i") == i), {})
        novels_out.append({
            "id": f"nov_{datetime.now().strftime('%m%d')}_{i:02d}",
            "title": n["title"],
            "author": n.get("author") or "",
            "genres": [],
            "matchScore": llm_row.get("matchScore") or 75,
            "reason": llm_row.get("reason") or f"{n['title']}——新书速递上榜。",
            "mood": llm_row.get("mood") or strategy,
            "doubanUrl": n.get("doubanUrl", ""),
            "coverUrl": n.get("coverUrl", ""),
        })
    podcasts_out = cands["podcasts"]

    payload_files = {
        "movies.json": movies_out,
        "music.json": music_out,
        "podcasts.json": podcasts_out if podcasts_out else [],
        "novels.json": {"items": novels_out},
        "context.json": {
            "generated": datetime.now().isoformat(timespec="seconds"),
            "schedule": {"taskCount": schedule_n, "busyLevel": busy, "note": ""},
            "fitness": {"hasWorkout": False, "intensity": "低", "note": "未接入塑形馆数据"},
            "moodProfile": {"primary": strategy[:2], "secondary": strategy[2:4], "label": strategy},
            "dailyNote": f"今天日程{busy}，走「{strategy}」调性。",
            "recommendationStrategy": {k: [strategy] for k in ("movies", "music", "podcasts")},
        },
    }
    for fname, payload in payload_files.items():
        (DATA / fname).write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  wrote {fname}")

    # QQ digest (silent file, deploy job only cats this)
    prompt2 = f"""根据今天以下推荐内容,写一份 QQ 晨间推荐推送,格式严格:

🎬 牛秘书·今日闲趣推荐

🎥 电影
1. 片名 — 一句话推荐理由
    ...

🎵 音乐
1. 歌名 — 歌手 — 一句话理由

🎙️ 播客
1. 节目名 — 一句话理由

📚 小说
1. 书名 — 一句话理由

规则:不出现分数、字段名、JSON、路径;每类最多3条精选;口吻亲和自然。

今日推荐数据:
 movies: {[(m['title'], m.get('reason','')[:30]) for m in movies_out]}
 music: {[(m['title'], m.get('reason','')[:30]) for m in music_out]}
 novels: {[(n['title'], n.get('reason','')[:30]) for n in novels_out]}
 podcasts: {[(p.get('title',''), p.get('reason','')[:30]) for p in podcasts_out]}
"""
    rsp = llm.chat("content", [{"role": "user", "content": prompt2}], temperature=0.4)
    digest = rsp.text.strip()
    digest = re.sub(r"^```[a-z]*\s*", "", digest).strip()
    if not digest.startswith("🎬"):
        digest = "🎬 牛秘书·今日闲趣推荐\n\n" + digest
    (HERE / "dist" / "qq_digest.txt").write_text(digest + "\n", encoding="utf-8")
    print("wrote dist/qq_digest.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
