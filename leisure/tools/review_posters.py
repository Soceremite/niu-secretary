#!/usr/bin/env python3
"""Vision-review leisure posters via the unified gateway.

Reads dist/data/{movies,novels}.json entries with coverUrl, asks the "vision"
logic model whether each poster is a real movie poster/cover (pass) or a
logo/ad/placeholder (fail). Writes dist/data/image_review.json:
{"results": [{"id": ..., "verdict": "pass"|"fail", "reason": ...}]}
"""
from __future__ import annotations

import base64
import json
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from niu_core.llm_client import NiuLLM  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "dist" / "data"
OUT = DATA / "image_review.json"


def fetch_image_b64(url: str) -> tuple[str, str] | None:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Referer": "https://movie.douban.com/",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
        ctype = (r.headers.get("Content-Type") or "image/jpeg").split(";")[0]
        if len(raw) < 2048:
            return None  # too small to be a real poster
        return base64.b64encode(raw).decode(), ctype
    except Exception:
        return None


def review(llm: NiuLLM, title: str, img_b64: str, ctype: str) -> tuple[str, str]:
    prompt = (
        f"这是影视/图书《{title}》的网络图片。判断它是否是真正的海报/封面："
        "真正的海报或封面图 → PASS；logo、广告、占位图、色块、无关照片 → FAIL。\n只回复 PASS 或 FAIL。"
    )
    try:
        rsp = llm.vision("vision", f"data:{ctype};base64,{img_b64}", prompt)
        answer = rsp.text.strip().upper()
        return ("pass" if "PASS" in answer else "fail"), answer[:60]
    except Exception as exc:
        return "pass", f"error:{exc}"[:60]  # fail-open: don't nuke covers on API hiccups


def main() -> int:
    llm = NiuLLM.load()
    results = []
    for fname in ("movies.json", "novels.json"):
        path = DATA / fname
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("items", [])
        for it in items:
            url = it.get("coverUrl") or ""
            if not url:
                results.append({"id": it["id"], "verdict": "pass", "reason": "no cover"})
                continue
            img = fetch_image_b64(url)
            if img is None:
                results.append({"id": it["id"], "verdict": "fail", "reason": "cover unreachable"})
                continue
            verdict, reason = review(llm, it.get("title", ""), img[0], img[1])
            results.append({"id": it["id"], "verdict": verdict, "reason": reason})
            print(f"  {it['id']} {it.get('title','')[:24]}: {verdict} ({reason[:30]})")

    out = {"results": results, "generated": __import__("datetime").datetime.now().isoformat(timespec="seconds")}
    (DATA / "image_review.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    passed = sum(1 for r in results if r["verdict"] == "pass")
    print(f"=== poster review: pass {passed} / fail {len(results)-passed} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
