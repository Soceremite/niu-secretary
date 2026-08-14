from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path
from urllib import request


OG_IMAGE_RE = re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I)


def arxiv_og_image(arxiv_id: str) -> str:
    with request.urlopen(f"https://arxiv.org/abs/{arxiv_id}", timeout=60) as response:
        html = response.read().decode("utf-8", errors="ignore")
    match = OG_IMAGE_RE.search(html)
    return match.group(1).strip() if match else ""


def download(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with request.urlopen(url, timeout=120) as response:
        out_path.write_bytes(response.read())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-db", type=Path, required=True)
    parser.add_argument("--papi", default=os.environ.get("PAPI", "papi"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    extracted = 0
    for paper_dir in sorted((args.paper_db / "papers").iterdir()):
        if not paper_dir.is_dir():
            continue
        figures_dir = paper_dir / "figures"
        figures_dir.mkdir(exist_ok=True)
        existing = any(figures_dir.iterdir())
        if existing and not args.overwrite:
            continue
        subprocess.run([args.papi, "regenerate", str(paper_dir), "--overwrite", "figures"], check=False)
        if any(figures_dir.iterdir()):
            extracted += 1
            print(f"figures regenerated for {paper_dir.name}")
            continue
        arxiv_id = paper_dir.name.replace("_", ".")
        og_image = arxiv_og_image(arxiv_id)
        if og_image:
            target = figures_dir / "fallback-og-image.jpg"
            download(og_image, target)
            extracted += 1
            print(f"fallback image downloaded for {paper_dir.name}")
    print(f"figure_sets={extracted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
