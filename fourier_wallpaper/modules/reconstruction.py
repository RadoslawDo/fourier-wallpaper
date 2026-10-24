"""Reconstructions: frames in a column, a row or a grid ("columns"), with a growing N."""
import numpy as np

from ..canvas import col
from ..texts import plural
from .base import Module, Option, RenderContext


class Reconstruction(Module):
    name = "reconstruction"
    options = {
        "direction": Option("column", lambda v: v in ("column", "row"), '"column" or "row"'),
        "columns": Option(None, lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 1,
                          "a whole number ≥ 1"),          # None: 1, or all frames in one row for "row"
        "empty": Option([], lambda v: isinstance(v, list) and all(isinstance(c, int) and not isinstance(c, bool)
                                                                  and c >= 0 for c in v),
                        "a list of cell numbers, e.g. [0, 1]"),
    }

    def draw(self, ctx: RenderContext, box):
        sh, S, k, lang, f = ctx.sheet, ctx.sheet.S, ctx.palette, ctx.lang, ctx.series
        Ns, gap = ctx.settings.reconstructions, 22 * S
        # cells of a grid, numbered row by row from 0; "empty" ones are skipped (e.g. the place of a widget)
        cols = box.opts["columns"] or (len(Ns) if box.opts["direction"] == "row" else 1)
        empty = set(box.opts["empty"])
        cells = [c for c in range(len(Ns) + len(empty)) if c not in empty][:len(Ns)]
        rows = cells[-1] // cols + 1
        y0 = box.y + 12 * S
        top, bottom = y0 + 30 * S, box.y + box.h
        fw, fh = (box.w + gap) / cols - gap, (bottom - top + gap) / rows - gap
        hx = box.x + (fw + gap) * (cells[0] % cols)                  # the header starts above the first frame
        sh.header(lang["reconstruction_header"], hx, y0, box.x + box.w - hx)
        for c, Kr in zip(cells, Ns):
            fx, fy = box.x + (fw + gap) * (c % cols), top + (fh + gap) * (c // cols)
            sh.frame(fx, fy, fw, fh)
            sh.formula(f"N = {Kr}", fx + 14 * S, fy + 28 * S, 16, col(k.accent, 0.85))
            sh.text(f"{2 * Kr + 1} {plural(2 * Kr + 1, lang)}", fx + 14 * S, fy + 50 * S, 13)
            _, Zr, Pr = f.placer(fx + fw * 0.58, fy + fh * 0.5, fw * 0.66, fh * 0.76)
            sh.poly([Pr(*p) for p in ctx.shape.outline], col(k.lines), 1.2 * S, close=True, dash=[6 * S, 5 * S])
            tr = np.linspace(0, 1, 1500 if Kr <= 40 else 6000)
            sh.poly([Zr(v) for v in f.recon(Kr, tr)], col(k.accent), 2.2 * S, glow=True, close=True)
