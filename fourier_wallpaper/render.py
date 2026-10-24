"""Drawing one wallpaper (the sheet, then every enabled module in its box) and generating its files."""
import os
import sys
import tomllib

import cairo

from .canvas import Sheet, col
from .config import ROOT, Job, Screen
from .graphic import analyze
from .layout import layout
from .modules import MODULES, RenderContext
from .series import Series
from .texts import Lang


class Renderer:
    """One wallpaper at one resolution."""

    def __init__(self, job: Job, series: Series, screen: Screen, language: str, lang: Lang):
        sheet = Sheet(screen.width, screen.height, job.palette, job.settings.font)
        self.ctx = RenderContext(sheet=sheet, palette=job.palette, series=series, shape=series.shape,
                                 settings=job.settings, spec=job.spec, texts=job.spec.texts_in(language), lang=lang,
                                 ultrawide=screen.ultrawide,
                                 boxes=layout(job.layers, screen.width, screen.height, sheet.S))

    def render(self, path: str) -> None:
        sh, W, H = self.ctx.sheet, self.ctx.sheet.W, self.ctx.sheet.H
        b = sh.b
        # background: the sheet
        b.set_source_rgba(*col(self.ctx.palette.background)); b.paint()
        g = cairo.RadialGradient(W * 0.62, H * 0.5, 0, W * 0.62, H * 0.5, max(W, H) * 0.75)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.025); g.add_color_stop_rgba(1, 0, 0, 0, 0.18)
        b.set_source(g); b.paint()
        for module in MODULES:
            box = self.ctx.boxes.get(module.name)
            if box:
                with sh.scaled(box.scale):
                    module().draw(self.ctx, box)
        sh.save(path)


def generate(job: Job) -> None:
    """The files of one Job: every language × resolution."""
    series = Series(analyze(job.spec))
    for language in job.languages:
        path = os.path.join(ROOT, "languages", f"{language}.toml")
        if not os.path.isfile(path):
            sys.exit(f"language {language!r}: no file languages/{language}.toml")
        with open(path, "rb") as f:
            lang = tomllib.load(f)
        for screen in job.screens:
            # "{resolution}" in the output path gives a folder per resolution (e.g. one per monitor for a slideshow)
            folder = os.path.normpath(job.output.format(resolution=str(screen)))
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, job.file_name(language, screen))
            Renderer(job, series, screen, language, lang).render(path)
            print(path)
