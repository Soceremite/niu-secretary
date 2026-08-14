from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from airesearch.figure_crop import write_pdf_window_trim_cover
from airesearch.image_selection import representative_image


def first_figure(figures_dir: Path, *, source_tex: Path | None = None) -> Path | None:
    return representative_image(figures_dir, source_tex=source_tex)


def write_webp_cover(source_path: Path, cover_path: Path, *, target_width: int) -> None:
    try:
        from PIL import Image
    except ImportError:
        if shutil.which("convert") is None:
            raise SystemExit("Pillow or ImageMagick convert is required for create_covers.py")
        cover_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "convert",
                str(source_path),
                "-auto-orient",
                "-resize",
                f"{target_width}x>",
                "-quality",
                "88",
                str(cover_path),
            ],
            check=True,
        )
        return

    with Image.open(source_path) as image:
        image = image.convert("RGB")
        width = min(target_width, image.width)
        height = max(1, round(image.height * (width / image.width)))
        image = image.resize((width, height))
        image.save(cover_path, format="WEBP", quality=88, method=6)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-db", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    generated = 0
    for paper_dir in sorted((args.paper_db / "papers").iterdir()):
        if not paper_dir.is_dir():
            continue
        cover_path = paper_dir / "cover.webp"
        if cover_path.exists() and not args.overwrite:
            continue
        if write_pdf_window_trim_cover(paper_dir / "paper.pdf", cover_path, target_width=args.width):
            generated += 1
            print(f"cover generated from pdf for {paper_dir.name}")
            continue
        source_path = first_figure(paper_dir / "figures", source_tex=paper_dir / "source.tex")
        if source_path is None:
            continue
        if source_path.suffix.lower() == ".svg":
            continue
        write_webp_cover(source_path, cover_path, target_width=args.width)
        generated += 1
        print(f"cover generated for {paper_dir.name}")
    print(f"covers_generated={generated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
