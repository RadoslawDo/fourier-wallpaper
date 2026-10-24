"""Spectrum of the outline."""
import math

from ..canvas import col
from .base import Box, Module, RenderContext


class Spectrum(Module):
    name = "spectrum"

    def draw(self, ctx: RenderContext, box: Box) -> None:
        sh, S, k, lang, texts, cn = ctx.sheet, ctx.sheet.S, ctx.palette, ctx.lang, ctx.texts, ctx.series.cn
        x, y0, w = box.x, box.y + 12 * S, box.w
        sh.header(lang["spectrum_header"], x, y0, w)
        sh.formula(lang["spectrum_caption"] + (": " + texts.spectrum if texts.spectrum is not None else ""), x, y0 + 36 * S, 13, sh.TEXT)
        px, py, pw = x, y0 + 64 * S, w
        ph = box.y + box.h - py
        sh.frame(px, py, pw, ph)
        base_y = py + ph - 26 * S
        top = max(abs(cn[n]) for n in range(-30, 31) if n)
        for n in range(-30, 31):
            xx = px + pw * (n + 31) / 62
            if n == 0:
                sh.poly([(xx, base_y), (xx, py + 14 * S)], col(k.lines), 2 * S, dash=[4 * S, 4 * S])
                sh.formula("c_{0}", xx + 6 * S, py + 30 * S, 13, sh.TEXT)
                continue
            v = max(0.0, (math.log10(abs(cn[n]) / top) + 3.2) / 3.2)
            c = col(k.accent) if n > 0 else col(k.accent2)
            yy = base_y - v * (ph - 50 * S)
            sh.poly([(xx, base_y), (xx, yy)], c, 2.4 * S, glow=abs(n) <= 2)
            sh.disc(xx, yy, 3.4 * S, c)
            if n % 10 == 0 or abs(n) == 1:
                sh.text(f"{n}", xx, base_y + 18 * S, 11, center=True)
        sh.poly([(px, base_y), (px + pw, base_y)], (1, 1, 1, 0.15), 1 * S)
