"""Example: square wave."""
import math

import numpy as np

from ..canvas import col
from ..graphic import Point
from .base import Box, Module, RenderContext


class Square(Module):
    name = "square"

    def draw(self, ctx: RenderContext, box: Box) -> None:
        sh, S, k, lang = ctx.sheet, ctx.sheet.S, ctx.palette, ctx.lang
        ACCENT, ACCENT2 = k.accent, k.accent2
        x, y0, w = box.x, box.y + 12 * S, box.w
        sh.header(lang["square_header"], x, y0, w)
        sh.formula("f(t) = 4/π · Σ_{k} sin((2k+1)t) / (2k+1)", x, y0 + 40 * S, 18)
        px, py, pw = x, y0 + 70 * S, w
        ph = box.y + box.h - py
        sh.frame(px, py, pw, ph)
        mid, amp = py + ph * 0.54, ph * 0.31
        sh.poly([(px, mid), (px + pw, mid)], (1, 1, 1, 0.08), 1 * S)
        sq: list[Point] = []
        for i in range(4):
            lvl = mid - amp * (1 if i % 2 == 0 else -1)
            sq += [(px + pw * i / 4, lvl), (px + pw * (i + 1) / 4, lvl)]
        sh.poly(sq, col(k.lines), 1.5 * S, dash=[8 * S, 6 * S])
        tt = np.linspace(0, 4 * math.pi, 1400)
        for N, c, lw in ((1, col(ACCENT2, 0.35), 1.4), (3, col(ACCENT2, 0.55), 1.4), (9, col(ACCENT2, 0.85), 1.6), (49, col(ACCENT), 2.2)):
            fN = sum((np.sin((2 * i + 1) * tt) / (2 * i + 1) for i in range(N)), np.zeros_like(tt)) * 4 / math.pi
            sh.poly([(px + pw * t / (4 * math.pi), mid - amp * f) for t, f in zip(tt, fN)], c, lw * S, glow=N == 49)
            sh.text(f"{N}", px + pw + 10 * S, mid - amp * 0.45 + (-28, -8, 12, 32)[[1, 3, 9, 49].index(N)] * S, 12, c)
        gy = mid - amp * 1.1790                                         # Gibbs overshoot ≈ 8.95% of the jump
        sh.poly([(px + 8 * S, gy), (px + pw * 0.5, gy)], col(ACCENT, 0.6), 1 * S, dash=[4 * S, 4 * S])
        sh.text(lang["gibbs"], px + 12 * S, py + 24 * S, 13, col(ACCENT, 0.75))
        sh.text(lang["terms"], px + pw + 10 * S, mid - amp * 0.45 - 52 * S, 12)
