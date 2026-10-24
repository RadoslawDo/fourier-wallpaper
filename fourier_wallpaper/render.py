"""Drawing one wallpaper: every enabled module in its box; generating it in every language and resolution."""
import math
import os
import sys
import tomllib

import cairo
import numpy as np

from .canvas import Sheet, col
from .config import ROOT
from .graphic import Circle, Curve, analyze
from .layout import MODULES, layout
from .series import Series
from .texts import plural


class Wallpaper:
    """One wallpaper at one resolution; each enabled module draws itself into its box."""

    def __init__(self, job, series, screen, language, lang):
        self.job, self.f, self.lang, self.k = job, series, lang, job.palette
        self.settings, self.shape = job.settings, series.shape
        self.sh = Sheet(screen.width, screen.height, self.k, job.settings.font)
        self.UW = screen.ultrawide   # ultrawide screen (with a widget in the top-left corner)
        self.texts = job.spec.texts_in(language)
        self.boxes = layout(job.layers, screen.width, screen.height, self.sh.S)

    def render(self, path):
        sh, b, W, H = self.sh, self.sh.b, self.sh.W, self.sh.H
        # background: the sheet
        b.set_source_rgba(*col(self.k.background)); b.paint()
        g = cairo.RadialGradient(W * 0.62, H * 0.5, 0, W * 0.62, H * 0.5, max(W, H) * 0.75)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.025); g.add_color_stop_rgba(1, 0, 0, 0, 0.18)
        b.set_source(g); b.paint()
        for m in MODULES:
            if m in self.boxes:
                with sh.scaled(self.boxes[m].scale):
                    getattr(self, m)(self.boxes[m])
        sh.save(path)

    # ------------------------------ grid of the sheet (the box is not used) ------------------------------
    def grid(self, box):
        b, S, W, H = self.sh.b, self.sh.S, self.sh.W, self.sh.H
        minor, major = 24 * S, 120 * S
        b.set_line_width(1)
        for step, a in ((minor, 0.018), (major, 0.035)):
            b.set_source_rgba(1, 1, 1, a)
            x = 0.5
            while x < W:
                b.move_to(x, 0); b.line_to(x, H); x += step
            y = 0.5
            while y < H:
                b.move_to(0, y); b.line_to(W, y); y += step
            b.stroke()
        b.set_source_rgba(1, 1, 1, 0.07); b.set_line_width(1.2 * S)
        for i in range(int(W / major) + 1):
            for j in range(int(H / major) + 1):
                x, y = i * major, j * major
                b.move_to(x - 5 * S, y); b.line_to(x + 5 * S, y); b.move_to(x, y - 5 * S); b.line_to(x, y + 5 * S)
        b.stroke()

    # ------------------------------ main drawing: epicycles draw the outline ------------------------------
    def drawing(self, box):
        sh, b, S, k, f, lang = self.sh, self.sh.b, self.sh.S, self.k, self.f, self.lang
        ACCENT, ACCENT2, BG, LINES = k.accent, k.accent2, k.background, k.lines
        OUTLINE, extras, cn = self.shape.outline, self.shape.extras, f.cn
        K = self.settings.circles    # terms n = -K..K
        T0 = 0.90                    # the moment the drawing is "frozen"
        labels_on = box.opts.get("labels", True)
        # the graphic fills the box height (or width); "align" pushes it to the left / right edge of the box
        BX0, BX1, BY0, BY1 = f.bbox
        gw = min(box.w, box.h * (BX1 - BX0) / (BY1 - BY0))
        cx = {"left": box.x + gw / 2, "center": box.x + box.w / 2, "right": box.x + box.w - gw / 2}[box.opts.get("align", "center")]
        sc, Z, Pt = f.placer(cx, box.y + box.h / 2, box.w, box.h)
        # inner lines of the graphic and the target outline – thin, like a drawing underneath
        b.new_path(); b.set_source_rgba(1, 1, 1, 0.025)
        b.move_to(*Pt(*OUTLINE[0]))
        for p in OUTLINE[1:]:
            b.line_to(*Pt(*p))
        b.close_path(); b.fill()
        for d in self.shape.details:
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
                for ctx, lw in ((b, 3.2 * S), (sh.gl, 8 * S)):
                    ctx.new_path(); ctx.set_source_rgba(*col(ACCENT)); ctx.set_line_width(lw)
                    ctx.arc_negative(x0, y0, r, ph, ph - 2 * math.pi * done); ctx.stroke()
                sh.circle(x0, y0, r, col(LINES), 1.2 * S)
                ex, ey = x0 + r * math.cos(ph - 2 * math.pi * done), y0 + r * math.sin(ph - 2 * math.pi * done)
                sh.poly([(x0, y0), (ex, ey)], col(ACCENT2, 0.9), 2 * S)
                sh.disc(x0, y0, 2.6 * S, col(ACCENT2)); sh.disc(ex, ey, 5 * S, col(ACCENT), glow=True)
            else:
                ce = f.fourier(e.points, 512)
                ell = lambda t: ce[0] + ce[1] * np.exp(2j * np.pi * t) + ce[-1] * np.exp(-2j * np.pi * t)
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
            if self.shape.inside[int(oy), int(ox)]:
                lx, ly = Pt(f.bbox[1], 0)[0] + 50 * S, y0 - 60 * S
                if not self.UW:      # narrower screen: above the drawing, before the modules on the right at that height
                    ly = Pt(0, f.bbox[2])[1] - 30 * S
                    rx = min([m.x for m in (self.boxes.get(n) for n in ("reconstruction", "title"))
                              if m and m.x > box.x + box.w / 2 and m.y - 40 * S < ly < m.y + m.h + 20 * S], default=sh.W)
                    lw_ = sh.width(label.replace("_{", "").replace("^{", "").replace("}", ""), 16)
                    lx = min(lx, rx - 40 * S - lw_)
                sh.poly([(x0, y0), (lx - 10 * S, ly), (lx - 4 * S, ly)], col(ACCENT2, 0.5), 1.2 * S)
                lx += 4 * S; ly += 6 * S
            else:
                lx, ly = (x0 + er + 18 * S, y0 + 6 * S) if self.UW else (x0 - er, y0 + er + 34 * S)
            sh.formula(label, lx, ly, 16, col(ACCENT2, 0.85))

    # ------------------------------ theory (h is not used – the text sets the height) ------------------------------
    def theory(self, box):
        sh, S, lang, texts = self.sh, self.sh.S, self.lang, self.texts
        K = self.settings.circles
        TX, TW = box.x, box.w
        y = box.y + 12 * S
        sh.header(lang["theory_header"], TX, y, TW); y += 44 * S
        y = sh.para(lang["theory_1"].format(noun=texts.noun if texts.noun is not None else lang["default_noun"]), TX, y, TW)
        y += 8 * S; sh.formula("z(t) = x(t) + i·y(t),   0 ≤ t < 1", TX + 14 * S, y + 6 * S); y += 50 * S
        y = sh.para(lang["theory_2"], TX, y, TW)
        y += 8 * S; sh.formula("z(t) ≈ Σ_{|n|≤N} c_{n} e^{2πint}", TX + 14 * S, y + 6 * S, 22); y += 54 * S
        y = sh.para(lang["theory_3"], TX, y, TW)
        y += 8 * S; sh.formula("c_{n} = ∫_{0}^{1} z(t) e^{-2πint} dt", TX + 14 * S, y + 6 * S, 22); y += 54 * S
        y = sh.para(lang["theory_4"].format(count=2 * K + 1, circles=plural(2 * K + 1, lang), K=K), TX, y, TW)
        y += 10 * S
        y = sh.para(lang["theory_5"], TX, y, TW)
        y += 10 * S
        if texts.closing is not None:
            last = texts.closing
        else:
            kinds = {type(e) for e in self.shape.extras}
            last = " ".join([lang["closing_circle"]] * (Circle in kinds) + [lang["closing_ellipse"]] * (Curve in kinds)
                            + [lang["closing_rest"]])
        sh.para(last, TX, y, TW)

    # ------------------------------ example: square wave ------------------------------
    def square(self, box):
        sh, S, k, lang = self.sh, self.sh.S, self.k, self.lang
        ACCENT, ACCENT2 = k.accent, k.accent2
        x, y0, w = box.x, box.y + 12 * S, box.w
        sh.header(lang["square_header"], x, y0, w)
        sh.formula("f(t) = 4/π · Σ_{k} sin((2k+1)t) / (2k+1)", x, y0 + 40 * S, 18)
        px, py, pw = x, y0 + 70 * S, w
        ph = box.y + box.h - py
        sh.frame(px, py, pw, ph)
        mid, amp = py + ph * 0.54, ph * 0.31
        sh.poly([(px, mid), (px + pw, mid)], (1, 1, 1, 0.08), 1 * S)
        sq = []
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

    # ------------------------------ spectrum of the outline ------------------------------
    def spectrum(self, box):
        sh, S, k, lang, texts, cn = self.sh, self.sh.S, self.k, self.lang, self.texts, self.f.cn
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

    # ------------------------------ reconstructions: a column (or a row) of frames ------------------------------
    def reconstruction(self, box):
        sh, S, k, lang, f = self.sh, self.sh.S, self.k, self.lang, self.f
        Ns, gap = self.settings.reconstructions, 22 * S
        # cells of a grid, numbered row by row from 0; "empty" ones are skipped (e.g. the place of a widget)
        cols = box.opts.get("columns", len(Ns) if box.opts.get("direction") == "row" else 1)
        empty = set(box.opts.get("empty", []))
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
            sh.poly([Pr(*p) for p in self.shape.outline], col(k.lines), 1.2 * S, close=True, dash=[6 * S, 5 * S])
            tr = np.linspace(0, 1, 1500 if Kr <= 40 else 6000)
            sh.poly([Zr(v) for v in f.recon(Kr, tr)], col(k.accent), 2.2 * S, glow=True, close=True)

    # ------------------------------ title block (the author credit goes above it) ------------------------------
    def title(self, box):
        sh, b, S, k, lang, st = self.sh, self.sh.b, self.sh.S, self.k, self.lang, self.settings
        tx, ty, tw_, th_ = box[:4]
        b.new_path(); b.set_source_rgba(0, 0, 0, 0.2); b.rectangle(tx, ty, tw_, th_); b.fill()
        b.set_source_rgba(*col(k.lines)); b.set_line_width(1.5 * S); b.rectangle(tx, ty, tw_, th_)
        b.move_to(tx, ty + th_ * 0.5); b.line_to(tx + tw_, ty + th_ * 0.5)
        b.move_to(tx + tw_ * 0.62, ty + th_ * 0.5); b.line_to(tx + tw_ * 0.62, ty + th_); b.stroke()
        title, size = st.title, 20
        while sh.width(title, size, True) > tw_ - 28 * S and size > 10:   # long title – smaller font
            size -= 1
        sh.text(title, tx + 14 * S, ty + th_ * 0.5 - 15 * S, size, col(k.accent, 0.85), bold=True)
        sh.text(f"{lang['sheet']}   {self.job.spec.tag}", tx + 14 * S, ty + th_ - 17 * S, 13, col(k.text, 0.5))
        sh.text(f"{lang['revision']} {st.revision}", tx + tw_ * 0.62 + 14 * S, ty + th_ - 17 * S, 13, col(k.text, 0.5))
        if self.texts.author:
            a_ = self.texts.author
            sh.text(a_, tx + tw_ - sh.width(a_, 12), ty - 14 * S, 12, col(k.text, 0.4))


def generate(job):
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
            Wallpaper(job, series, screen, language, lang).render(path)
            print(path)
