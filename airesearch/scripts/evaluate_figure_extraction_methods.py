from __future__ import annotations

import html
import json
import random
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from airesearch.image_selection import image_dimensions, representative_image


METHODS = [
    ("image-heuristic", "Image heuristic", "Best extracted image from paperpipe figures."),
    ("pdf-top-to-caption", "PDF top to caption", "Full text width from top margin down to the Figure 1 caption."),
    ("pdf-window", "PDF caption window", "A fixed-height window immediately above the Figure 1 caption."),
    ("pdf-window-trim", "PDF window trim", "The same caption window, then ImageMagick trims white margins."),
]


@dataclass(frozen=True)
class FigureCaption:
    page: int
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    page_width: float
    page_height: float


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def selected_papers(paper_db: Path, *, count: int = 10) -> list[Path]:
    required = [paper_db / "papers" / "world2vlm", paper_db / "papers" / "world-action-models"]
    candidates = [
        path
        for path in sorted((paper_db / "papers").iterdir())
        if path.is_dir() and (path / "paper.pdf").exists() and path not in required
    ]
    random.Random(20260611).shuffle(candidates)
    return required + candidates[: max(0, count - len(required))]


def find_figure_one_caption(pdf_path: Path, tmp_dir: Path) -> FigureCaption | None:
    xml_path = tmp_dir / f"{pdf_path.parent.name}.bbox.html"
    run(["pdftotext", "-bbox-layout", "-f", "1", "-l", "5", str(pdf_path), str(xml_path)])
    text = xml_path.read_text(encoding="utf-8", errors="ignore")
    pages = list(re.finditer(r"<page\b(?P<attrs>[^>]*)>(?P<body>.*?)</page>", text, re.S))
    for page_index, page_match in enumerate(pages, start=1):
        page_attrs = dict(re.findall(r'(\w+)="([^"]*)"', page_match.group("attrs")))
        page_width = float(page_attrs.get("width", "612"))
        page_height = float(page_attrs.get("height", "792"))
        words = []
        for word_match in re.finditer(r"<word\b(?P<attrs>[^>]*)>(?P<text>.*?)</word>", page_match.group("body"), re.S):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', word_match.group("attrs")))
            word_text = re.sub(r"<[^>]+>", "", word_match.group("text"))
            words.append((attrs, html.unescape(word_text)))
        rows: dict[int, list[ET.Element]] = {}
        for attrs, _word_text in words:
            if "yMin" not in attrs:
                continue
            y = round(float(attrs["yMin"]))
            rows.setdefault(y, []).append((attrs, _word_text))
        for _y, row_words in sorted(rows.items()):
            ordered = sorted(row_words, key=lambda item: float(item[0]["xMin"]))
            row_text = " ".join(item[1] for item in ordered)
            if re.search(r"\b(?:Figure|Fig\.?)\s*1\b", row_text, re.I):
                return FigureCaption(
                    page=page_index,
                    x_min=min(float(item[0]["xMin"]) for item in ordered),
                    y_min=min(float(item[0]["yMin"]) for item in ordered),
                    x_max=max(float(item[0]["xMax"]) for item in ordered),
                    y_max=max(float(item[0]["yMax"]) for item in ordered),
                    page_width=page_width,
                    page_height=page_height,
                )
    return None


def render_page(pdf_path: Path, caption: FigureCaption, out_dir: Path) -> Path:
    prefix = out_dir / "page"
    run(["pdftoppm", "-f", str(caption.page), "-l", str(caption.page), "-png", "-r", "180", str(pdf_path), str(prefix)])
    rendered = out_dir / f"page-{caption.page:02d}.png"
    if not rendered.exists():
        matches = sorted(out_dir.glob("page-*.png"))
        if not matches:
            raise RuntimeError(f"pdftoppm did not render {pdf_path}")
        rendered = matches[0]
    return rendered


def identify_size(path: Path) -> tuple[int, int]:
    output = subprocess.check_output(["identify", "-format", "%w %h", str(path)], text=True)
    width, height = output.strip().split()
    return int(width), int(height)


def convert_to_webp(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    run(["convert", str(source), "-auto-orient", "-resize", "900x>", "-quality", "88", str(target)])


def crop_page(rendered: Path, caption: FigureCaption, target: Path, *, mode: str) -> None:
    width, height = identify_size(rendered)
    scale_x = width / caption.page_width
    scale_y = height / caption.page_height
    left = round(caption.page_width * 0.075 * scale_x)
    right = round(caption.page_width * 0.925 * scale_x)
    caption_top = round(max(0, caption.y_min - 6) * scale_y)

    if mode == "top":
        top = round(caption.page_height * 0.08 * scale_y)
    else:
        top = max(round(caption_top - caption.page_height * 0.52 * scale_y), round(caption.page_height * 0.06 * scale_y))
    crop_width = max(1, right - left)
    crop_height = max(1, caption_top - top)
    geometry = f"{crop_width}x{crop_height}+{left}+{top}"
    command = ["convert", str(rendered), "-crop", geometry, "+repage"]
    if mode == "window-trim":
        command.extend(["-trim", "+repage"])
    command.extend(["-resize", "900x>", "-quality", "88", str(target)])
    run(command)


def generate_for_paper(paper_dir: Path, out_dir: Path) -> dict[str, object]:
    paper_out = out_dir / "assets" / paper_dir.name
    paper_out.mkdir(parents=True, exist_ok=True)
    methods: list[dict[str, str]] = []

    image_source = representative_image(paper_dir / "figures", source_tex=paper_dir / "source.tex")
    if image_source is not None and image_source.suffix.lower() != ".svg":
        target = paper_out / "image-heuristic.webp"
        convert_to_webp(image_source, target)
        dimensions = image_dimensions(image_source)
        methods.append(
            {
                "id": "image-heuristic",
                "path": str(target.relative_to(out_dir)),
                "source": image_source.name,
                "size": f"{dimensions.width}x{dimensions.height}" if dimensions else "unknown",
            }
        )

    caption = find_figure_one_caption(paper_dir / "paper.pdf", paper_out)
    if caption is not None:
        rendered = render_page(paper_dir / "paper.pdf", caption, paper_out)
        for method_id, mode in [
            ("pdf-top-to-caption", "top"),
            ("pdf-window", "window"),
            ("pdf-window-trim", "window-trim"),
        ]:
            target = paper_out / f"{method_id}.webp"
            crop_page(rendered, caption, target, mode=mode)
            methods.append(
                {
                    "id": method_id,
                    "path": str(target.relative_to(out_dir)),
                    "source": f"page {caption.page}",
                    "size": "pdf crop",
                }
            )

    return {
        "paper_key": paper_dir.name,
        "title": json.loads((paper_dir / "meta.json").read_text(encoding="utf-8")).get("title", paper_dir.name),
        "methods": methods,
    }


def render_html(results: list[dict[str, object]]) -> str:
    method_lookup = {method_id: (label, note) for method_id, label, note in METHODS}
    cards = []
    for result in results:
        method_cards = []
        by_id = {method["id"]: method for method in result["methods"]}
        for method_id, label, _note in METHODS:
            method = by_id.get(method_id)
            if method is None:
                method_cards.append(f'<article class="method missing"><h3>{html.escape(label)}</h3><p>not available</p></article>')
                continue
            method_cards.append(
                f"""
                <article class="method">
                  <div class="method-head">
                    <h3>{html.escape(label)}</h3>
                    <span>{html.escape(method["source"])} · {html.escape(method["size"])}</span>
                  </div>
                  <img src="{html.escape(method["path"])}" alt="{html.escape(str(result["paper_key"]))} {html.escape(label)}">
                </article>
                """
            )
        cards.append(
            f"""
            <section class="paper">
              <div class="paper-title">
                <p>{html.escape(str(result["paper_key"]))}</p>
                <h2>{html.escape(str(result["title"]))}</h2>
              </div>
              <div class="method-grid">{''.join(method_cards)}</div>
            </section>
            """
        )
    notes = "".join(
        f"<li><strong>{html.escape(label)}</strong><span>{html.escape(note)}</span></li>"
        for _method_id, label, note in METHODS
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Figure 1 Extraction Method Review</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #171717;
      --muted: #6d6a62;
      --paper: #f8f7f3;
      --line: #d7d2c8;
      --panel: #ffffff;
      --accent: #9d3f2c;
      --accent-2: #1f6f69;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background: var(--paper);
    }}
    header {{
      padding: 32px clamp(20px, 5vw, 72px) 24px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(90deg, #fffdf8 0%, #f1eee6 100%);
    }}
    header p {{
      max-width: 980px;
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.55;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(32px, 5vw, 64px);
      line-height: 0.95;
      letter-spacing: 0;
      max-width: 980px;
    }}
    .legend {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
      padding: 18px clamp(20px, 5vw, 72px);
      margin: 0;
      list-style: none;
      border-bottom: 1px solid var(--line);
    }}
    .legend li {{
      display: grid;
      gap: 4px;
      padding: 12px;
      background: rgba(255,255,255,.62);
      border: 1px solid var(--line);
      border-radius: 6px;
    }}
    .legend strong {{ font-size: 14px; }}
    .legend span {{ color: var(--muted); font-size: 13px; line-height: 1.35; }}
    main {{
      padding: 22px clamp(20px, 5vw, 72px) 56px;
    }}
    .paper {{
      padding: 26px 0 34px;
      border-bottom: 1px solid var(--line);
    }}
    .paper-title {{
      display: grid;
      grid-template-columns: minmax(140px, 220px) 1fr;
      gap: 18px;
      align-items: baseline;
      margin-bottom: 16px;
    }}
    .paper-title p {{
      margin: 0;
      color: var(--accent);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 13px;
    }}
    .paper-title h2 {{
      margin: 0;
      font-size: clamp(20px, 2.6vw, 34px);
      line-height: 1.08;
      letter-spacing: 0;
    }}
    .method-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      align-items: start;
    }}
    .method {{
      min-width: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      overflow: hidden;
    }}
    .method-head {{
      min-height: 76px;
      padding: 12px 12px 10px;
      border-bottom: 1px solid var(--line);
    }}
    .method h3 {{
      margin: 0 0 6px;
      font-size: 15px;
      line-height: 1.2;
      letter-spacing: 0;
    }}
    .method span, .method p {{
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 11px;
      line-height: 1.35;
    }}
    .method img {{
      display: block;
      width: 100%;
      max-width: 100%;
      height: 280px;
      object-fit: contain;
      background: #ebe7de;
    }}
    .missing {{
      min-height: 358px;
      display: grid;
      place-content: center;
      text-align: center;
      color: var(--muted);
    }}
    @media (max-width: 1180px) {{
      .method-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 720px) {{
      .paper-title {{ grid-template-columns: 1fr; gap: 6px; }}
      .method-grid {{ grid-template-columns: 1fr; }}
      .method img {{ height: 240px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Figure 1 Extraction Method Review</h1>
    <p>每篇论文同屏展示四种候选方案。重点看是否拿到完整 Figure 1，而不是 PDF/LaTeX 内部嵌入的小子图。</p>
  </header>
  <ul class="legend">{notes}</ul>
  <main>{''.join(cards)}</main>
</body>
</html>
"""


def main() -> int:
    paper_db = Path("airesearch/data/paperpipe")
    out_dir = Path("airesearch/exports/figure-extraction-eval")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    papers = selected_papers(paper_db, count=12)
    results = [generate_for_paper(paper_dir, out_dir) for paper_dir in papers]
    (out_dir / "index.html").write_text(render_html(results), encoding="utf-8")
    (out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out_dir / "index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
