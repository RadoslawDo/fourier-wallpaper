"""Golden-image test: every wallpaper in configs/ × every layout in layouts/ (and the default one), at small
16:10, 16:9 and 21:9 resolutions, must come out pixel for pixel the same as the reference PNGs in tests/golden.

The program is run through its command line, so the test does not depend on how the code is organised.
The references depend on the fonts and on the cairo / librsvg / OpenCV builds: after updating them, or after
a change that is meant to alter the wallpapers, look at the new images and accept them with
    pytest --update-golden
"""
import glob
import os
import shutil
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "tests", "golden")
RESOLUTIONS = ["640x400", "640x360", "860x360"]   # 16:10, 16:9, 21:9 (ultrawide: width > 2 × height)


def names(folder):
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(ROOT, folder, "*.toml")))


WALLPAPERS = names("configs")
LAYOUTS = ["default"] + names("layouts")
# every layout in Polish; the default layout also in English (the texts differ, the drawing does not)
RUNS = [(w, layout, "pl") for w in WALLPAPERS for layout in LAYOUTS] + [(w, "default", "en") for w in WALLPAPERS]
CASES = [f"{res}/fourier-{w}{'' if layout == 'default' else '-' + layout}-{lang}_{res}.png"
         for w, layout, lang in RUNS for res in RESOLUTIONS]


@pytest.fixture(scope="session")
def generated(tmp_path_factory, request):
    """All the wallpapers, generated once; returns the folder they are in (or tests/golden with --update-golden)."""
    out = tmp_path_factory.mktemp("wallpapers")
    for w in WALLPAPERS:
        for lang in ("pl", "en"):
            layouts = sorted({layout for w_, layout, l_ in RUNS if w_ == w and l_ == lang})
            cmd = [sys.executable, os.path.join(ROOT, "fourier.py"), "-c", w, "-l", lang,
                   "-o", os.path.join(out, "{resolution}")]
            cmd += [a for layout in layouts for a in ("-L", layout)] + [a for r in RESOLUTIONS for a in ("-r", r)]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
    if request.config.getoption("--update-golden"):
        shutil.rmtree(GOLDEN, ignore_errors=True)
        shutil.copytree(out, GOLDEN)
    return out


@pytest.mark.parametrize("case", CASES)
def test_golden(generated, case):
    reference = os.path.join(GOLDEN, case)
    assert os.path.exists(reference), f"no reference image {reference} – run: pytest --update-golden"
    expected = np.asarray(Image.open(reference).convert("RGB")).astype(int)
    actual = np.asarray(Image.open(os.path.join(generated, case)).convert("RGB")).astype(int)
    assert actual.shape == expected.shape, f"size {actual.shape[1::-1]} instead of {expected.shape[1::-1]}"
    diff = np.abs(actual - expected).max(-1)
    assert diff.max() == 0, (f"{(diff > 0).sum()} pixels differ (by up to {diff.max()}); "
                             f"generated image: {os.path.join(generated, case)}")


def test_no_stale_references():
    """Every reference image belongs to a current wallpaper × layout (removed ones must not linger)."""
    found = {os.path.relpath(p, GOLDEN) for p in glob.glob(os.path.join(GOLDEN, "*", "*.png"))}
    assert found == set(CASES), f"extra: {sorted(found - set(CASES))}, missing: {sorted(set(CASES) - found)}"
