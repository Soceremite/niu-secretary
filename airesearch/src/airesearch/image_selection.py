from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from pathlib import Path


IMAGE_SUFFIXES = (".webp", ".png", ".jpg", ".jpeg", ".svg")


@dataclass(frozen=True)
class ImageDimensions:
    width: int
    height: int

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def aspect_skew(self) -> float:
        if self.width <= 0 or self.height <= 0:
            return 999.0
        return max(self.width / self.height, self.height / self.width)


def _png_dimensions(data: bytes) -> ImageDimensions | None:
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 24:
        return None
    width, height = struct.unpack(">II", data[16:24])
    return ImageDimensions(width=width, height=height)


def _jpeg_dimensions(data: bytes) -> ImageDimensions | None:
    if not data.startswith(b"\xff\xd8"):
        return None
    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in (0xD8, 0xD9):
            continue
        if offset + 2 > len(data):
            return None
        segment_length = struct.unpack(">H", data[offset : offset + 2])[0]
        if segment_length < 2 or offset + segment_length > len(data):
            return None
        if 0xC0 <= marker <= 0xC3 or 0xC5 <= marker <= 0xC7 or 0xC9 <= marker <= 0xCB or 0xCD <= marker <= 0xCF:
            if offset + 7 > len(data):
                return None
            height = struct.unpack(">H", data[offset + 3 : offset + 5])[0]
            width = struct.unpack(">H", data[offset + 5 : offset + 7])[0]
            return ImageDimensions(width=width, height=height)
        offset += segment_length
    return None


def _webp_dimensions(data: bytes) -> ImageDimensions | None:
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    chunk = data[12:16]
    if chunk == b"VP8X" and len(data) >= 30:
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return ImageDimensions(width=width, height=height)
    if chunk == b"VP8 " and len(data) >= 30:
        width = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        height = struct.unpack("<H", data[28:30])[0] & 0x3FFF
        return ImageDimensions(width=width, height=height)
    if chunk == b"VP8L" and len(data) >= 25:
        bits = int.from_bytes(data[21:25], "little")
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return ImageDimensions(width=width, height=height)
    return None


def _svg_dimensions(path: Path) -> ImageDimensions | None:
    text = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    viewbox = re.search(r"\bviewBox=[\"']\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)", text)
    if viewbox:
        return ImageDimensions(width=round(float(viewbox.group(1))), height=round(float(viewbox.group(2))))
    width = re.search(r"\bwidth=[\"']([\d.]+)", text)
    height = re.search(r"\bheight=[\"']([\d.]+)", text)
    if width and height:
        return ImageDimensions(width=round(float(width.group(1))), height=round(float(height.group(1))))
    return None


def image_dimensions(path: Path) -> ImageDimensions | None:
    suffix = path.suffix.lower()
    if suffix == ".svg":
        return _svg_dimensions(path)
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if suffix == ".png":
        return _png_dimensions(data)
    if suffix in (".jpg", ".jpeg"):
        return _jpeg_dimensions(data)
    if suffix == ".webp":
        return _webp_dimensions(data)
    return None


def first_figure_references(source_tex: Path) -> list[str]:
    if not source_tex.exists() or not source_tex.is_file():
        return []
    text = source_tex.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"(?m)^\s*%.*$", "", text)
    match = re.search(r"\\begin\{figure\*?\}.*?\\end\{figure\*?\}", text, re.S)
    if not match:
        return []
    refs = []
    for ref in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", match.group(0)):
        normalized = Path(ref.strip()).name
        refs.extend([normalized.lower(), Path(normalized).stem.lower()])
    return refs


def _dimension_score(dimensions: ImageDimensions | None) -> float:
    if dimensions is None:
        return 0.0
    score = float(dimensions.area)
    min_side = min(dimensions.width, dimensions.height)
    if dimensions.area < 90_000:
        score *= 0.35
    if min_side < 160:
        score *= 0.2
    elif min_side < 220:
        score *= 0.65
    skew = dimensions.aspect_skew
    if skew > 8:
        score *= 0.18
    elif skew > 5:
        score *= 0.4
    elif skew > 3.6:
        score *= 0.7
    return score


def representative_image(figures_dir: Path, *, source_tex: Path | None = None) -> Path | None:
    if not figures_dir.exists() or not figures_dir.is_dir():
        return None
    candidates = sorted(
        path for path in figures_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not candidates:
        return None

    references = set(first_figure_references(source_tex)) if source_tex is not None else set()
    if references:
        for candidate in candidates:
            names = {candidate.name.lower(), candidate.stem.lower()}
            if names & references:
                return candidate

    scored = []
    for candidate in candidates:
        dimensions = image_dimensions(candidate)
        scored.append((_dimension_score(dimensions), dimensions, candidate))
    scored.sort(key=lambda item: (item[0], item[1].area if item[1] is not None else 0, item[2].name), reverse=True)
    return scored[0][2]
