import struct
from pathlib import Path

from airesearch.image_selection import first_figure_references, representative_image


def write_png_header(path: Path, width: int, height: int) -> None:
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height))


def test_representative_image_prefers_large_complete_figure(tmp_path: Path):
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir()
    write_png_header(figures_dir / "figure_01.png", 224, 224)
    write_png_header(figures_dir / "figure_02.png", 2000, 120)
    write_png_header(figures_dir / "figure_03.png", 1600, 900)

    assert representative_image(figures_dir) == figures_dir / "figure_03.png"


def test_representative_image_uses_first_source_figure_reference(tmp_path: Path):
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir()
    write_png_header(figures_dir / "appendix.png", 1800, 900)
    write_png_header(figures_dir / "method.png", 640, 360)
    source_tex = tmp_path / "source.tex"
    source_tex.write_text(
        r"""
        \begin{figure*}
          \includegraphics[width=0.93\textwidth]{Figures/method.png}
          \caption{Overview.}
        \end{figure*}
        """,
        encoding="utf-8",
    )

    assert first_figure_references(source_tex) == ["method.png", "method"]
    assert representative_image(figures_dir, source_tex=source_tex) == figures_dir / "method.png"
