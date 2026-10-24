"""Output formats: the WebP file is the PNG one, the SVG and PDF files look like it."""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "fourier-tux-en_640x400"


@pytest.fixture(scope="module")
def out(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("formats")
    subprocess.run([sys.executable, os.path.join(ROOT, "fourier.py"), os.path.join(ROOT, "configs", "tux.toml"),
                    "-l", "en", "-r", "640x400", "-o", str(out)] + [a for f in ("png", "webp", "svg", "pdf")
                                                                     for a in ("-f", f)],
                   check=True, capture_output=True, text=True)
    return out


def pixels(path: Path) -> np.ndarray[tuple[int, int, int], np.dtype[np.int16]]:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)


def test_webp_is_lossless(out: Path) -> None:
    assert np.array_equal(pixels(out / f"{NAME}.webp"), pixels(out / f"{NAME}.png"))


def test_svg_looks_like_png(out: Path, tmp_path: Path) -> None:
    png = tmp_path / "svg.png"
    subprocess.run(["rsvg-convert", str(out / f"{NAME}.svg"), "-o", str(png)], check=True)
    diff = np.abs(pixels(png) - pixels(out / f"{NAME}.png"))
    assert diff.shape == (400, 640, 3) and diff.mean() < 1.5, diff.mean()     # only the antialiasing differs


def test_pdf(out: Path) -> None:
    assert (out / f"{NAME}.pdf").read_bytes().startswith(b"%PDF")
