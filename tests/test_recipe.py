"""Recipes: mistakes in them stop the program with a message, before anything is generated."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(tmp_path: Path, recipe: str) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "recipe.toml"
    path.write_text(recipe)
    return subprocess.run([sys.executable, os.path.join(ROOT, "fourier.py"), str(path), "-r", "64x40",
                           "-o", str(tmp_path / "out")], capture_output=True, text=True)


@pytest.mark.parametrize("recipe, message", [
    ('[[wallpapers]]\nconfig = "tux"\nlayout_typo = {}\n', "unknown keys ['layout_typo']"),
    ('[[wallpapers]]\nconfig = "tux"\n[[wallpapers]]\nconfig = "tux"\ncircles = 10\n', "both make"),
    ('[[wallpapers]]\nconfig = "tux"\ngraphic = "x.svg"\n', "give the wallpaper a name"),
    ('[[wallpapers]]\nconfig = "nothing"\n', "not found: 'nothing'"),
    ('[[wallpapers]]\nconfig = "tux"\nlayouts = ["nothing"]\n', "not found: 'nothing'"),
    ('[[wallpapers]]\ngraphic = "x.svg"\nname = "x"\n', "[wallpaper] tag is missing"),
    ('[[wallpapers]]\nconfig = "tux"\nlayout = { theory = { columns = 2 } }\n', "unknown keys ['columns']"),
    ('wallpapers = 3\n', "wallpapers must be a list of tables"),
    ('[general]\nlanguage = ["en"]\n', "no wallpapers"),
])
def test_mistake(tmp_path: Path, recipe: str, message: str) -> None:
    result = run(tmp_path, recipe)
    assert result.returncode != 0 and message in result.stderr, result.stderr
    assert not (tmp_path / "out").exists()
