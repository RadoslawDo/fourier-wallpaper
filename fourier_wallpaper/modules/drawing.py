"""Main drawing: epicycles draw the outline."""
import math

import numpy as np

from ..canvas import col
from ..graphic import Circle
from ..series import Complexes, Floats
from .base import Box, Module, Option, RenderContext


class Drawing(Module):
    name = "drawing"
    options = {
        "labels": Option(True, lambda v: isinstance(v, bool), "true or false"),       # c₀, c₁… and the small shapes
        "align": Option("center", lambda v: v in ("left", "center", "right"), '"left", "center" or "right"'),
    }

    def draw(self, ctx: RenderContext, box: Box) -> None:
        sh, b, S, k, f, lang = ctx.sheet, ctx.sheet.b, ctx.sheet.S, ctx.palette, ctx.series, ctx.lang
        ACCENT, ACCENT2, BG, LINES = k.accent, k.accent2, k.background, k.lines
        OUTLINE, extras, cn = ctx.shape.outline, ctx.shape.extras, f.cn
        K = ctx.settings.circles     # terms n = -K..K
        T0 = 0.90                    # the moment the drawing is "frozen"
        labels_on = box.opts["labels"]
        # the graphic fills the box height (or width); "align" pushes it to the left / right edge of the box
        BX0, BX1, BY0, BY1 = f.bbox
        gw = min(box.w, box.h * (BX1 - BX0) / (BY1 - BY0))
        cx = {"left": box.x + gw / 2, "center": box.x + box.w / 2, "right": box.x + box.w - gw / 2}[box.opts["align"]]
        sc, Z, Pt = f.placer(cx, box.y + box.h / 2, box.w, box.h)
        # inner lines of the graphic and the target outline – thin, like a drawing underneath
        b.new_path(); b.set_source_rgba(1, 1, 1, 0.025)
        b.move_to(*Pt(*OUTLINE[0]))
        for p in OUTLINE[1:]:
            b.line_to(*Pt(*p))
        b.close_path(); b.fill()
        for d in ctx.shape.details:
            sh.poly([Pt(*p) for p in d], col(k.details), 1.5 * S, close=True)
        sh.poly([Pt(*p) for p in OUTLINE], col(LINES), 1.5 * S, close=True, dash=[10 * S, 7 * S])
        # trace: reconstruction from 2K+1 circles for t = 0..T0 (slight ripples show at the corners)
        ts = np.linspace(0, T0, 3000 if K <= 40 else 10000)
        sh.poly([Z(v) for v in f.recon(K, ts)], col(ACCENT), 3.2 * S, glow=True)
        # chain of circles: c₀ (centre), then from the largest
        order = sorted([n for n in range(-K, K + 1) if n], key=lambda n: -abs(cn[n]))
        pos = cn[0]
        labels = 0
        for n in order:
            v = cn[n] * np.exp(2j * np.pi * n * T0)
            r = abs(v) * sc
            x0, y0 = Z(pos)
            if r > 1.2 * S:
                sh.circle(x0, y0, r, col(ACCENT2, 0.10 + 0.35 * min(1, r / (120 * S))), 1.3 * S)
            nxt = pos + v
            sh.poly([Z(pos), Z(nxt)], col(ACCENT2, 0.9), 2 * S if r > 20 * S else 1.4 * S, glow=r > 40 * S)
            if r > 3 * S:
                sh.disc(x0, y0, 2.6 * S, col(ACCENT2))
            if labels_on and labels < 5 and r > 30 * S:                              # labels of the largest terms
                mx_, my_ = Z(pos + v / 2)
                sh.formula(f"c_{{{n}}}", mx_ + 8 * S, my_ - 8 * S, 15, col(ACCENT2, 0.8)); labels += 1
            pos = nxt
        tx_, ty_ = Z(pos)
        sh.disc(tx_, ty_, 7 * S, col(ACCENT), glow=True); sh.disc(tx_, ty_, 3 * S, col(BG))
        cx_, cy_ = Z(cn[0])
        sh.disc(cx_, cy_, 5 * S, col(k.text, 0.8))
        if labels_on:
            sh.formula("c_{0}", cx_ - 34 * S, cy_ + 24 * S, 15, sh.TEXT)

        # --- small shapes: circle = one term, ellipse = two (n = 1 and n = −1) ---
        nx = len(extras)
        for i, e in enumerate(extras):
            done = 1.0 - 0.38 * (nx - 1 - i) / max(1, nx - 1)       # different drawing phases, the last one complete
            if isinstance(e, Circle):
                x0, y0 = Pt(e.x, e.y); r = e.r * sc
                ph = -math.pi / 2
                for cr, lw in ((b, 3.2 * S), (sh.gl, 8 * S)):      # the sharp layer and the glow layer
                    cr.new_path(); cr.set_source_rgba(*col(ACCENT)); cr.set_line_width(lw)
                    cr.arc_negative(x0, y0, r, ph, ph - 2 * math.pi * done); cr.stroke()
                sh.circle(x0, y0, r, col(LINES), 1.2 * S)
                ex, ey = x0 + r * math.cos(ph - 2 * math.pi * done), y0 + r * math.sin(ph - 2 * math.pi * done)
                sh.poly([(x0, y0), (ex, ey)], col(ACCENT2, 0.9), 2 * S)
                sh.disc(x0, y0, 2.6 * S, col(ACCENT2)); sh.disc(ex, ey, 5 * S, col(ACCENT), glow=True)
            else:
                ce = f.fourier(e.points, 512)
                def ell(t: Floats) -> Complexes:
                    return ce[0] + ce[1] * np.exp(2j * np.pi * t) + ce[-1] * np.exp(-2j * np.pi * t)
                tt = np.linspace(0, 1, 400)
                sh.poly([Z(v) for v in ell(tt)], col(LINES), 1.2 * S, close=True)
                sh.poly([Z(v) for v in ell(tt * done)], col(ACCENT), 3.2 * S, glow=True)
                p0 = ce[0]; p1 = p0 + ce[1] * np.exp(2j * np.pi * done); p2 = p1 + ce[-1] * np.exp(-2j * np.pi * done)
                (x0, y0), (x1, y1), (x2, y2) = Z(p0), Z(p1), Z(p2)
                sh.circle(x0, y0, abs(ce[1]) * sc, col(ACCENT2, 0.3), 1 * S)
                sh.circle(x1, y1, abs(ce[-1]) * sc, col(ACCENT2, 0.3), 1 * S)
                sh.poly([(x0, y0), (x1, y1), (x2, y2)], col(ACCENT2, 0.9), 2 * S)
                sh.disc(x0, y0, 2.6 * S, col(ACCENT2)); sh.disc(x1, y1, 2.2 * S, col(ACCENT2))
                sh.disc(x2, y2, 5 * S, col(ACCENT), glow=True)
        # label at the largest shape: beside it when it lies outside the outline, otherwise via a leader to the right
        if extras and labels_on:
            e = extras[0]
            if isinstance(e, Circle):
                label, (ox, oy), er = lang["label_circle"], (e.x, e.y), e.r
            else:
                label, (ox, oy), er = lang["label_ellipse"], e.centre, 0
            x0, y0 = Pt(ox, oy); er *= sc
            if ctx.shape.inside[int(oy), int(ox)]:
                lx, ly = Pt(f.bbox[1], 0)[0] + 50 * S, y0 - 60 * S
                if not ctx.ultrawide:      # narrower screen: above the drawing, before the modules on the right at that height
                    ly = Pt(0, f.bbox[2])[1] - 30 * S
                    rx = min([m.x for m in (ctx.boxes.get(n) for n in ("reconstruction", "title"))
                              if m and m.x > box.x + box.w / 2 and m.y - 40 * S < ly < m.y + m.h + 20 * S], default=sh.W)
                    lw_ = sh.width(label.replace("_{", "").replace("^{", "").replace("}", ""), 16)
                    lx = min(lx, rx - 40 * S - lw_)
                sh.poly([(x0, y0), (lx - 10 * S, ly), (lx - 4 * S, ly)], col(ACCENT2, 0.5), 1.2 * S)
                lx += 4 * S; ly += 6 * S
            else:
                lx, ly = (x0 + er + 18 * S, y0 + 6 * S) if ctx.ultrawide else (x0 - er, y0 + er + 34 * S)
            sh.formula(label, lx, ly, 16, col(ACCENT2, 0.85))
