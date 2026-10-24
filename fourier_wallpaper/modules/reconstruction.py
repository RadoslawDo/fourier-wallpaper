"""Reconstructions: the outline drawn again with a growing N – one frame per item of "reconstructions".

The frames fill the module's box as a grid of cells:
  - "columns" sets how many cells a row has (default: 1, or all frames in one row with direction = "row");
  - the number of rows follows from it: as many as the frames need (with the empty cells before them),
    so it does not depend on the screen – only the size of the cells does;
  - cells are numbered row by row from 0, left to right (cell c: column c % columns, row c // columns);
  - "empty" cells are skipped and the frames take the next free ones, in the order of "reconstructions".
E.g. 20 frames, columns = 8, empty = [0, 1, 8, 9] – 24 cells in 3 rows, the top-left 2 × 2 left free:
     0  1 |  2  3  4  5  6  7          ·   ·  N₁  N₂  …  N₆
     8  9 | 10 11 12 13 14 15    →     ·   ·  N₇  …      N₁₂
    16 17   18 19 20 21 22 23         N₁₃  …             N₂₀
"""
from typing import ClassVar

import numpy as np

from ..canvas import col
from ..tables import is_list
from ..texts import plural
from .base import Box, Module, Option, RenderContext


class Reconstruction(Module):
    name = "reconstruction"
    options: ClassVar[dict[str, Option]] = {
        # without "columns": all frames in one column, or in one row
        "direction": Option("column", lambda v: v in ("column", "row"), '"column" or "row"'),
        # cells in a row; None: 1, or all frames in one row for "row"
        "columns": Option(None, lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 1,
                          "a whole number ≥ 1"),
        # cells left free (numbered row by row from 0); cells after the last frame change nothing
        "empty": Option([], lambda v: is_list(v) and all(isinstance(c, int) and not isinstance(c, bool) and c >= 0
                                                         for c in v),
                        "a list of cell numbers, e.g. [0, 1]"),
    }

    def draw(self, ctx: RenderContext, box: Box) -> None:
        sh, S, k, lang, f = ctx.sheet, ctx.sheet.S, ctx.palette, ctx.lang, ctx.series
        Ns, gap = ctx.settings.reconstructions, 22 * S
        # the cell of each frame: the first free ones, skipping "empty" (e.g. the place of a widget)
        cols = box.opts["columns"] or (len(Ns) if box.opts["direction"] == "row" else 1)
        empty = set(box.opts["empty"])
        cells = [c for c in range(len(Ns) + len(empty)) if c not in empty][:len(Ns)]
        rows = cells[-1] // cols + 1                                 # down to the row of the last frame
        # the cells share the box: their size follows from the box, the gaps and the numbers of rows and columns
        y0 = box.y + 12 * S
        top, bottom = y0 + 30 * S, box.y + box.h
        fw, fh = (box.w + gap) / cols - gap, (bottom - top + gap) / rows - gap
        hx = box.x + (fw + gap) * (cells[0] % cols)                  # the header starts above the first frame
        sh.header(lang["reconstruction_header"], hx, y0, box.x + box.w - hx)
        for c, Kr in zip(cells, Ns):
            fx, fy = box.x + (fw + gap) * (c % cols), top + (fh + gap) * (c // cols)
            sh.frame(fx, fy, fw, fh)
            sh.formula(f"N = {Kr}", fx + 14 * S, fy + 28 * S, 16, col(k.accent, 0.85))
            count = len(ctx.shape.outlines) * (2 * Kr + 1)          # every outline has its own chain
            sh.text(f"{count} {plural(count, lang)}", fx + 14 * S, fy + 50 * S, 13)
            _, Zr, Pr = f.placer(fx + fw * 0.58, fy + fh * 0.5, fw * 0.66, fh * 0.76)
            for o in ctx.shape.outlines:
                sh.poly([Pr(*p) for p in o], col(k.lines), 1.2 * S, close=True, dash=[6 * S, 5 * S])
            tr = np.linspace(0, 1, 1500 if Kr <= 40 else 6000)
            for part in range(len(ctx.shape.outlines)):
                sh.poly([Zr(v) for v in f.recon(Kr, tr, part)], col(k.accent), 2.2 * S, glow=True, close=True)
