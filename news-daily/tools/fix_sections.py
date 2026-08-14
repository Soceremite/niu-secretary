#!/usr/bin/env python3
"""Fix template IDs and add h2 tags to news section HTML files."""
import re
from pathlib import Path

SECTIONS_DIR = Path(__file__).resolve().parent.parent / "dist" / "sections"

for section_file in sorted(SECTIONS_DIR.glob("*.html")):
    content = section_file.read_text(encoding="utf-8")

    # Find card titles by openDetail id
    title_map = {}
    for card in re.finditer(
        r"<a\b[^>]*class=\"[^\"]*card-link[^\"]*\"[^>]*openDetail\('([^']+)'\)[^>]*>.*?<h3[^>]*>(.*?)</h3>.*?</a>",
        content,
        re.DOTALL,
    ):
        title_map[card.group(1)] = card.group(2)

    # Fix each template: add h2 after detail-meta if missing
    def fix_template(m):
        tid = m.group(1)
        body = m.group(2)
        if "<h2" not in body:
            title = title_map.get(tid, "新闻详情")
            body = re.sub(
                r'(<div[^>]*class="[^"]*detail-meta[^"]*"[^>]*>.*?</div>)',
                r'\1\n  <h2>' + title + r'</h2>',
                body,
                count=1,
                flags=re.DOTALL,
            )
        return f'<template id="detail-{tid}">{body}</template>'

    content = re.sub(
        r'<template[^>]*id="detail-([^"]+)"[^>]*>(.*?)</template>',
        fix_template,
        content,
        flags=re.DOTALL,
    )

    section_file.write_text(content, encoding="utf-8")
    print(f"Fixed: {section_file.name}")

print("All sections fixed.")
