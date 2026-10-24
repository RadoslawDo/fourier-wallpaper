"""Drawing one wallpaper (the sheet, then every enabled module in its box) and generating its files."""
import os
import sys
import tomllib

import cairo

from .canvas import RASTER, Sheet, col
from .config import ROOT, Job, Screen
from .graphic import analyze
from .layout import layout
from .modules import MODULES, RenderContext
from .series import Series
from .texts import Lang


class Renderer:
    """One wallpaper at one resolution."""

    def __init__(self, job: Job, series: Series, screen: Screen, language: str, lang: Lang,
                 vector: str | None = None):
        self.quality = job.quality
        sheet = Sheet(screen.width, screen.height, job.palette, job.settings.font, vector)
        self.ctx = RenderContext(sheet=sheet, palette=job.palette, series=series, shape=series.shape,
                                 settings=job.settings, spec=job.spec, texts=job.spec.texts_in(language), lang=lang,
                                 ultrawide=screen.ultrawide,
                                 boxes=layout(job.layers, screen.width, screen.height, sheet.S))

    def render(self, paths: list[str]) -> None:
        """Draws it; paths: the image files (.png, .webp) to save it as, or [] for the vector file of the sheet."""
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
        if sh.vector:
            sh.finish()
        else:
            sh.save(paths, self.quality)


def generate(job: Job) -> None:
    """The files of one Job: every language × resolution."""
    series = Series(analyze(job.spec))
    for language in job.languages:
        path = os.path.join(ROOT, "languages", f"{language}.toml")
        if not os.path.isfile(path):
            sys.exit(f"language {language!r}: no file languages/{language}.toml")
        with open(path, "rb") as f:
            lang = tomllib.load(f)
        with open(os.path.join(ROOT, "languages", "en.toml"), "rb") as f:
            missing = sorted(set(tomllib.load(f)) - set(lang))      # en.toml has every key
        if missing:
            sys.exit(f"languages/{language}.toml: missing keys {missing} (copy them from en.toml)")
        for screen in job.screens:
            # "{resolution}" in the output path gives a folder per resolution (e.g. one per monitor for a slideshow)
            os.makedirs(job.folder(screen), exist_ok=True)
            # the image formats come from one drawing, each vector format is drawn again into its own file
            raster = [job.path(language, screen, fmt) for fmt in job.formats if fmt in RASTER]
            if raster:
                Renderer(job, series, screen, language, lang).render(raster)
            for fmt in job.formats:
                if fmt not in RASTER:
                    Renderer(job, series, screen, language, lang, job.path(language, screen, fmt)).render([])
            for path in job.paths(language, screen):
                print(path)
