from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib import request


SYSTEM_PROMPT = (
    "Translate the given research paper summary into concise, natural Simplified Chinese. "
    "Preserve formulas, identifiers, markdown structure, and technical terms when appropriate."
)


def _normalize_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized == "https://api.deepseek.com":
        return normalized + "/v1"
    return normalized


def translate_text(*, base_url: str, api_key: str, model: str, text: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
    }
    req = request.Request(
        _normalize_base_url(base_url) + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"translation API error {exc.code}: {detail}") from exc
    choices = body.get("choices", [])
    if not choices:
        raise ValueError("translation API returned no choices")
    message = choices[0].get("message", {})
    return str(message.get("content") or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-db", type=Path, required=True)
    try:
        from niu_core.llm_client import compat as _niu_compat
        _d_url, _d_key, _d_model = _niu_compat.resolve("translate")
    except Exception:
        _d_url, _d_key, _d_model = "", "", ""
    parser.add_argument(
        "--model",
        default=os.environ.get("TRANSLATE_MODEL") or _d_model or "deepseek/deepseek-v4-pro",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TRANSLATE_BASE_URL") or _d_url
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.deepseek.com/v1",
    )
    parser.add_argument("--api-key-env", default="TRANSLATE_API_KEY")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key and args.api_key_env == "TRANSLATE_API_KEY":
        api_key = _d_key or os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(f"missing API key in {args.api_key_env}")

    translated = 0
    for paper_dir in sorted((args.paper_db / "papers").iterdir()):
        if not paper_dir.is_dir():
            continue
        for source_name, target_name in (("summary.md", "summary.zh.md"), ("tldr.md", "tldr.zh.md")):
            source_path = paper_dir / source_name
            target_path = paper_dir / target_name
            if not source_path.exists():
                continue
            if target_path.exists() and not args.overwrite:
                continue
            text = source_path.read_text(encoding="utf-8").strip()
            if not text:
                continue
            translated_text = translate_text(base_url=args.base_url, api_key=api_key, model=args.model, text=text)
            target_path.write_text(translated_text.rstrip() + "\n", encoding="utf-8")
            translated += 1
            print(f"translated {paper_dir.name}/{target_name}")
    print(f"translated_assets={translated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
