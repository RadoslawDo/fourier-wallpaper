#!/usr/bin/env python3
"""Fourier wallpaper generator: epicycles (a Fourier series) draw the outline of an SVG graphic on
a technical-drawing sheet. Around it: theory, a square-wave example with the Gibbs phenomenon,
the |cₙ| spectrum of the outline and reconstructions with a growing number of circles.

From the graphic the program takes:
  - the outline – the outer contour of the whole graphic (drawn by a chain of 2K+1 circles),
  - inner lines – boundaries between regions of different colour (k-means on colours, graphic_colors),
  - small shapes – separate ones next to the outline (e.g. logo dots) are found automatically,
    ones inside (e.g. pupils) are pointed to in the config; a circle is drawn by 1 term,
    an ellipse by 2 (n = 1 and n = −1).

Parameters: config.toml (next to this file), texts: languages/<code>.toml. On an ultrawide screen
(width > 2 × height) the top-left corner stays empty – a desktop widget sits there.

Usage:
  python3 fourier.py                          all wallpapers from the config
  python3 fourier.py -w tux -l pl             one wallpaper, in Polish
  python3 fourier.py -g drawing.svg -r 2560x1440 -t "MY // WALLPAPER" --color accent=#FF5500
"""
import argparse
import copy
import math
import os
import subprocess
import sys
import tomllib

import cairo
import cv2
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))


# ============================== graphic → outline, inner lines, small shapes ==============================
def raster(svg, height=1600):
    """SVG → BGRA (numpy) via rsvg-convert; contour coordinates are pixels of this raster."""
    png = subprocess.run(["rsvg-convert", "-h", str(height), svg], capture_output=True, check=True).stdout
    return cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)


def contours(mask, mode, min_area=150):
    cs, _ = cv2.findContours(mask.astype(np.uint8), mode, cv2.CHAIN_APPROX_NONE)
    return [c for c in cs if cv2.contourArea(c) > min_area]


def as_pts(c, eps=0.8):
    return [tuple(map(float, p[0])) for p in cv2.approxPolyDP(c, eps, True)]


def classify(c):
    """Small shape: a circle (1 term) or a curve drawn as an ellipse (2 terms)."""
    area = cv2.contourArea(c)
    _, r = cv2.minEnclosingCircle(c)
    if area / (math.pi * r * r) > 0.9:
        m = cv2.moments(c)
        return ("circle", (m["m10"] / m["m00"], m["m01"] / m["m00"], math.sqrt(area / math.pi)))
    return ("curve", as_pts(c, 0.5))


def analyze(svg, colors, extras_cfg):
    im = raster(svg)
    h, w = im.shape[:2]
    a = im[..., 3] > 128
    outer = sorted(contours(a, cv2.RETR_EXTERNAL), key=cv2.contourArea, reverse=True)
    main = outer[0]
    inside = np.zeros((h, w), np.uint8)
    cv2.drawContours(inside, [main], -1, 1, -1)
    # colours: k-means in Lab space on the pixels inside the outline, then the boundaries of each colour region
    lab = cv2.cvtColor(np.ascontiguousarray(im[..., :3]), cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    sel = np.flatnonzero((a & (inside > 0)).ravel())
    sample = lab[sel[np.random.default_rng(0).permutation(len(sel))[:200000]]]
    _, _, centers = cv2.kmeans(sample, colors, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5),
                               3, cv2.KMEANS_PP_CENTERS)
    labels = np.argmin(((lab[:, None, :] - centers[None]) ** 2).sum(-1), 1).reshape(h, w)
    # boundaries of every colour except the most common one – otherwise both sides would draw each boundary
    details = []
    common = np.argmax(np.bincount(labels[a & (inside > 0)], minlength=colors))
    for k in range(colors):
        if k == common:
            continue
        m = ((labels == k) & a & (inside > 0)).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        details += [(as_pts(c), True) for c in contours(m, cv2.RETR_CCOMP)]
    # small shapes: separate ones next to the outline and the ones pointed to in the config
    extras = [classify(c) for c in outer[1:] if cv2.contourArea(c) > 3e-4 * cv2.contourArea(main)]
    for e in extras_cfg:
        x, y = int(e["x"] * w), int(e["y"] * h)
        m = (labels == labels[y, x]) & a
        if e.get("type", "shape") == "circle":
            # the largest disc of this colour near the given point (the shape merges with other lines)
            r0 = int(0.04 * h)
            dist = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
            win = dist[y - r0:y + r0, x - r0:x + r0]
            yy, xx = np.unravel_index(np.argmax(win), win.shape)
            extras.append(("circle", (x - r0 + xx, y - r0 + yy, float(win[yy, xx]))))
        else:
            _, comp = cv2.connectedComponents(m.astype(np.uint8))
            extras.append(classify(contours(comp == comp[y, x], cv2.RETR_EXTERNAL)[0]))
    extras.sort(key=lambda e: -(e[1][2] if e[0] == "circle" else cv2.contourArea(np.array(e[1], np.float32))))
    return dict(outline=as_pts(main), details=details, extras=extras, inside=inside)


# ============================== drawing ==============================
def col(h, a=1.0):
    return int(h[1:3], 16) / 255, int(h[3:5], 16) / 255, int(h[5:7], 16) / 255, a


def plural(n, lang):
    """The word "circle" after a number, by the language's plural rule."""
    forms = lang["circle"]
    if lang["plural_rule"] == "pl":
        return forms[0] if n == 1 else forms[1] if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else forms[2]
    return forms[0] if n == 1 else forms[1]


class Sheet:
    """Wallpaper canvas: a sharp layer and a glow layer (blurred later), plus drawing helpers."""

    def __init__(self, W, H, colors, font):
        self.W, self.H, self.S = W, H, H / 1440          # scale relative to 1440 px height
        self.k, self.fontname = colors, font
        self.base, self.b = self._surface()
        self.glow, self.gl = self._surface()
        self.TEXT = col(colors["text"], 0.62)

    def _surface(self):
        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.W, self.H)
        c = cairo.Context(s)
        c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_line_join(cairo.LINE_JOIN_ROUND)
        return s, c

    def poly(self, pts, c, w, glow=False, close=False, dash=None):
        for ctx, lw in ((self.b, w),) + (((self.gl, w * 2.6),) if glow else ()):
            ctx.new_path(); ctx.set_source_rgba(*c); ctx.set_line_width(lw)
            if dash and ctx is self.b:
                ctx.set_dash(dash)
            ctx.move_to(*pts[0])
            for p in pts[1:]:
                ctx.line_to(*p)
            if close:
                ctx.close_path()
            ctx.stroke(); ctx.set_dash([])

    def disc(self, x, y, r, c, glow=False):
        for ctx in (self.b, self.gl) if glow else (self.b,):
            ctx.new_path(); ctx.set_source_rgba(*c); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()

    def circle(self, x, y, r, c, w):
        b = self.b
        b.new_path(); b.set_source_rgba(*c); b.set_line_width(w); b.arc(x, y, r, 0, 2 * math.pi); b.stroke()

    def font(self, size, bold=False):
        self.b.select_font_face(self.fontname, cairo.FONT_SLANT_NORMAL,
                                cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
        self.b.set_font_size(size * self.S)

    def width(self, t, size=15, bold=False):
        self.font(size, bold)
        return self.b.text_extents(t).x_advance

    def text(self, t, x, y, size=15, c=None, bold=False, center=False):
        self.font(size, bold); self.b.set_source_rgba(*(c or self.TEXT))
        if center:
            x -= self.b.text_extents(t).x_advance / 2
        self.b.move_to(x, y); self.b.show_text(t)
        return self.b.text_extents(t).x_advance

    def formula(self, t, x, y, size=20, c=None):
        """Formula with _{subscripts} and ^{superscripts} (Hack has no sub/superscript glyphs – smaller, shifted text)."""
        c = c or col(self.k["accent"], 0.9)
        b, i = self.b, 0
        while i < len(t):
            if t[i] in "_^" and i + 1 < len(t) and t[i + 1] == "{":
                j = t.index("}", i)
                self.font(size * 0.62); b.set_source_rgba(*c)
                b.move_to(x, y + (0.28 if t[i] == "_" else -0.42) * size * self.S); b.show_text(t[i + 2:j])
                x += b.text_extents(t[i + 2:j]).x_advance; i = j + 1
            else:
                j = i
                while j < len(t) and t[j] not in "_^":
                    j += 1
                self.font(size); b.set_source_rgba(*c); b.move_to(x, y); b.show_text(t[i:j])
                x += b.text_extents(t[i:j]).x_advance; i = j
        return x

    def para(self, t, x, y, width, size=15, lead=1.45):
        """Paragraph wrapped to a width; returns the y below it."""
        self.font(size); line = ""
        for word in t.split():
            test = (line + " " + word).strip()
            if self.b.text_extents(test).x_advance > width and line:
                self.text(line, x, y, size); y += size * self.S * lead; line = word
            else:
                line = test
        if line:
            self.text(line, x, y, size); y += size * self.S * lead
        return y

    def header(self, t, x, y, width):
        """Section header: capitals in the accent colour and a rule to the end of the column."""
        S = self.S
        w = self.text(t, x, y, 16, col(self.k["accent"], 0.95), bold=True)
        self.poly([(x + w + 12 * S, y - 6 * S), (x + width, y - 6 * S)], col(self.k["lines"]), 1.5 * S)

    def frame(self, x, y, w, h):
        b = self.b
        b.new_path(); b.set_source_rgba(1, 1, 1, 0.10); b.set_line_width(1.2 * self.S)
        b.rectangle(x, y, w, h); b.stroke()

    def save(self, path):
        def pil(s):
            s.flush()
            return Image.frombuffer("RGBA", (self.W, self.H), bytes(s.get_data()), "raw", "BGRa", 0, 1)
        img = pil(self.base)
        g = pil(self.glow).filter(ImageFilter.GaussianBlur(9 * self.S))
        g.putalpha(g.getchannel("A").point(lambda v: int(v * 0.5)))
        Image.alpha_composite(img, g).convert("RGB").save(path, optimize=True)


def render(job, shape, W, H, lang, path):
    k = job["colors"]
    ACCENT, ACCENT2, BG, LINES = k["accent"], k["accent2"], k["background"], k["lines"]
    sh = Sheet(W, H, k, job["font"])
    b, S = sh.b, sh.S
    UW = W / H > 2               # ultrawide screen (with a widget in the top-left corner)
    texts = job.get("texts", {}).get(job["language"], {})

    # --- background: sheet with a grid ---
    b.set_source_rgba(*col(BG)); b.paint()
    g = cairo.RadialGradient(W * 0.62, H * 0.5, 0, W * 0.62, H * 0.5, max(W, H) * 0.75)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.025); g.add_color_stop_rgba(1, 0, 0, 0, 0.18)
    b.set_source(g); b.paint()
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

    # --- Fourier series of the outline ---
    OUTLINE, extras = shape["outline"], shape["extras"]
    xs = [p[0] for p in OUTLINE]; ys = [p[1] for p in OUTLINE]
    for kind, e in extras:
        ep = [(e[0] - e[2], e[1] - e[2]), (e[0] + e[2], e[1] + e[2])] if kind == "circle" else e
        xs += [p[0] for p in ep]; ys += [p[1] for p in ep]
    BX0, BX1, BY0, BY1 = min(xs), max(xs), min(ys), max(ys)
    mx0, my0 = (BX0 + BX1) / 2, (BY0 + BY1) / 2

    def fourier(poly_, M=2048):
        """Coefficients cₙ of a closed curve (a polygon sampled at equal arc lengths)."""
        ring = poly_ + [poly_[0]]
        seg = [math.dist(ring[i], ring[i + 1]) for i in range(len(poly_))]
        cum = np.concatenate([[0], np.cumsum(seg)])
        pts = []
        for s_ in np.linspace(0, cum[-1], M, endpoint=False):
            i = np.searchsorted(cum, s_, side="right") - 1
            f = (s_ - cum[i]) / seg[i]
            pts.append((ring[i][0] + (ring[i + 1][0] - ring[i][0]) * f, ring[i][1] + (ring[i + 1][1] - ring[i][1]) * f))
        # complex plane with the imaginary axis pointing up (SVG y flipped) – n > 0 turns counter-clockwise
        z = np.array([(x - mx0) - 1j * (y - my0) for x, y in pts])
        return dict(zip(np.fft.fftfreq(M, 1 / M).astype(int), np.fft.fft(z) / M))

    cn = fourier(OUTLINE)

    def recon(K, ts):
        return sum(cn[n] * np.exp(2j * np.pi * n * ts) for n in range(-K, K + 1))

    def placer(cx, cy, height):
        sc = height / (BY1 - BY0)
        return sc, (lambda zz: (cx + sc * zz.real, cy - sc * zz.imag)), (lambda x, y: (cx + sc * (x - mx0), cy + sc * (y - my0)))

    # --- page layout ---
    if UW:
        TX, TY, TW = 960.0, 90 * S, 520 * S                       # theory, next to the widget
        SQ = (60 * S, 960 * S, 660 * S, 390 * S)                  # square wave
        SP = (790 * S, 960 * S, 690 * S, 390 * S)                 # spectrum
        LC, LH = (W * 0.635, H * 0.47), H * 0.60                  # main drawing
    else:
        TX, TY, TW = 50 * S, 70 * S, 560 * S
        SQ = (50 * S, 820 * S, 560 * S, 250 * S)
        SP = (50 * S, 1110 * S, 560 * S, 250 * S)
        LC, LH = (W * 0.545, H * 0.46), H * 0.52
    RX, RW = W - 560 * S, 500 * S                                  # reconstruction column

    # ============================== centre: epicycles draw the outline ==============================
    K = job["circles"]           # terms n = -K..K
    T0 = 0.90                    # the moment the drawing is "frozen"
    sc, Z, Pt = placer(LC[0], LC[1], LH)
    # inner lines of the graphic and the target outline – thin, like a drawing underneath
    b.new_path(); b.set_source_rgba(1, 1, 1, 0.025)
    b.move_to(*Pt(*OUTLINE[0]))
    for p in OUTLINE[1:]:
        b.line_to(*Pt(*p))
    b.close_path(); b.fill()
    for d, closed in shape["details"]:
        sh.poly([Pt(*p) for p in d], col(k["details"]), 1.5 * S, close=closed)
    sh.poly([Pt(*p) for p in OUTLINE], col(LINES), 1.5 * S, close=True, dash=[10 * S, 7 * S])
    # trace: reconstruction from 2K+1 circles for t = 0..T0 (slight ripples show at the corners)
    ts = np.linspace(0, T0, 3000 if K <= 40 else 10000)
    sh.poly([Z(v) for v in recon(K, ts)], col(ACCENT), 3.2 * S, glow=True)
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
        if labels < 5 and r > 30 * S:                              # labels of the largest terms
            mx_, my_ = Z(pos + v / 2)
            sh.formula(f"c_{{{n}}}", mx_ + 8 * S, my_ - 8 * S, 15, col(ACCENT2, 0.8)); labels += 1
        pos = nxt
    tx_, ty_ = Z(pos)
    sh.disc(tx_, ty_, 7 * S, col(ACCENT), glow=True); sh.disc(tx_, ty_, 3 * S, col(BG))
    cx_, cy_ = Z(cn[0])
    sh.disc(cx_, cy_, 5 * S, col(k["text"], 0.8))
    sh.formula("c_{0}", cx_ - 34 * S, cy_ + 24 * S, 15, sh.TEXT)

    # --- small shapes: circle = one term, ellipse = two (n = 1 and n = −1) ---
    nx = len(extras)
    for i, (kind, e) in enumerate(extras):
        done = 1.0 - 0.38 * (nx - 1 - i) / max(1, nx - 1)       # different drawing phases, the last one complete
        if kind == "circle":
            dx, dy, dr = e
            x0, y0 = Pt(dx, dy); r = dr * sc
            ph = -math.pi / 2
            for ctx, lw in ((b, 3.2 * S), (sh.gl, 8 * S)):
                ctx.new_path(); ctx.set_source_rgba(*col(ACCENT)); ctx.set_line_width(lw)
                ctx.arc_negative(x0, y0, r, ph, ph - 2 * math.pi * done); ctx.stroke()
            sh.circle(x0, y0, r, col(LINES), 1.2 * S)
            ex, ey = x0 + r * math.cos(ph - 2 * math.pi * done), y0 + r * math.sin(ph - 2 * math.pi * done)
            sh.poly([(x0, y0), (ex, ey)], col(ACCENT2, 0.9), 2 * S)
            sh.disc(x0, y0, 2.6 * S, col(ACCENT2)); sh.disc(ex, ey, 5 * S, col(ACCENT), glow=True)
        else:
            ce = fourier(e, 512)
            ell = lambda t: ce[0] + ce[1] * np.exp(2j * np.pi * t) + ce[-1] * np.exp(-2j * np.pi * t)
            tt = np.linspace(0, 1, 400)
            sh.poly([Z(v) for v in ell(tt)], col(LINES), 1.2 * S, close=True)
            sh.poly([Z(v) for v in ell(tt * done)], col(ACCENT), 3.2 * S, glow=True)
            p0 = ce[0]; p1 = p0 + ce[1] * np.exp(2j * np.pi * done); p2 = p1 + ce[-1] * np.exp(-2j * np.pi * done)
            for c_, n_ in ((p0, 1), (p1, -1)):
                sh.circle(*Z(c_), abs(ce[n_]) * sc, col(ACCENT2, 0.3), 1 * S)
            sh.poly([Z(p0), Z(p1), Z(p2)], col(ACCENT2, 0.9), 2 * S)
            sh.disc(*Z(p0), 2.6 * S, col(ACCENT2)); sh.disc(*Z(p1), 2.2 * S, col(ACCENT2))
            sh.disc(*Z(p2), 5 * S, col(ACCENT), glow=True)
    # label at the largest shape: beside it when it lies outside the outline, otherwise via a leader to the right
    if extras:
        kind, e = extras[0]
        label = lang["label_circle"] if kind == "circle" else lang["label_ellipse"]
        if kind == "circle":
            ox, oy, er = e
        else:
            ox, oy, er = np.mean([p[0] for p in e]), np.mean([p[1] for p in e]), 0
        x0, y0 = Pt(ox, oy); er *= sc
        if shape["inside"][int(oy), int(ox)]:
            lx, ly = Pt(BX1, 0)[0] + 50 * S, y0 - 60 * S
            if not UW:           # narrower screen: above the drawing, before the reconstruction column
                lw_ = sh.width(label.replace("_{", "").replace("^{", "").replace("}", ""), 16)
                lx, ly = min(lx, RX - 40 * S - lw_), Pt(0, BY0)[1] - 30 * S
            sh.poly([(x0, y0), (lx - 10 * S, ly), (lx - 4 * S, ly)], col(ACCENT2, 0.5), 1.2 * S)
            lx += 4 * S; ly += 6 * S
        else:
            lx, ly = (x0 + er + 18 * S, y0 + 6 * S) if UW else (x0 - er, y0 + er + 34 * S)
        sh.formula(label, lx, ly, 16, col(ACCENT2, 0.85))

    # ============================== column: theory ==============================
    y = TY
    sh.header(lang["theory_header"], TX, y, TW); y += 44 * S
    y = sh.para(lang["theory_1"].format(noun=texts.get("noun", lang["default_noun"])), TX, y, TW)
    y += 8 * S; sh.formula("z(t) = x(t) + i·y(t),   0 ≤ t < 1", TX + 14 * S, y + 6 * S); y += 50 * S
    y = sh.para(lang["theory_2"], TX, y, TW)
    y += 8 * S; sh.formula("z(t) ≈ Σ_{|n|≤N} c_{n} e^{2πint}", TX + 14 * S, y + 6 * S, 22); y += 54 * S
    y = sh.para(lang["theory_3"], TX, y, TW)
    y += 8 * S; sh.formula("c_{n} = ∫_{0}^{1} z(t) e^{-2πint} dt", TX + 14 * S, y + 6 * S, 22); y += 54 * S
    y = sh.para(lang["theory_4"].format(count=2 * K + 1, circles=plural(2 * K + 1, lang), K=K), TX, y, TW)
    y += 10 * S
    y = sh.para(lang["theory_5"], TX, y, TW)
    y += 10 * S
    if "closing" in texts:
        last = texts["closing"]
    else:
        kinds = {kd for kd, _ in extras}
        last = " ".join([lang["closing_circle"]] * ("circle" in kinds) + [lang["closing_ellipse"]] * ("curve" in kinds)
                        + [lang["closing_rest"]])
    sh.para(last, TX, y, TW)

    # ============================== example: square wave ==============================
    x, y0, w, h = SQ
    sh.header(lang["square_header"], x, y0, w)
    sh.formula("f(t) = 4/π · Σ_{k} sin((2k+1)t) / (2k+1)", x, y0 + 40 * S, 18)
    px, py, pw, ph = x, y0 + 70 * S, w, h - 80 * S
    sh.frame(px, py, pw, ph)
    mid, amp = py + ph * 0.54, ph * 0.31
    sh.poly([(px, mid), (px + pw, mid)], (1, 1, 1, 0.08), 1 * S)
    sq = []
    for i in range(4):
        lvl = mid - amp * (1 if i % 2 == 0 else -1)
        sq += [(px + pw * i / 4, lvl), (px + pw * (i + 1) / 4, lvl)]
    sh.poly(sq, col(LINES), 1.5 * S, dash=[8 * S, 6 * S])
    tt = np.linspace(0, 4 * math.pi, 1400)
    for N, c, lw in ((1, col(ACCENT2, 0.35), 1.4), (3, col(ACCENT2, 0.55), 1.4), (9, col(ACCENT2, 0.85), 1.6), (49, col(ACCENT), 2.2)):
        fN = sum(np.sin((2 * i + 1) * tt) / (2 * i + 1) for i in range(N)) * 4 / math.pi
        sh.poly([(px + pw * t / (4 * math.pi), mid - amp * f) for t, f in zip(tt, fN)], c, lw * S, glow=N == 49)
        sh.text(f"{N}", px + pw + 10 * S, mid - amp * 0.45 + (-28, -8, 12, 32)[[1, 3, 9, 49].index(N)] * S, 12, c)
    gy = mid - amp * 1.1790                                         # Gibbs overshoot ≈ 8.95% of the jump
    sh.poly([(px + 8 * S, gy), (px + pw * 0.5, gy)], col(ACCENT, 0.6), 1 * S, dash=[4 * S, 4 * S])
    sh.text(lang["gibbs"], px + 12 * S, py + 24 * S, 13, col(ACCENT, 0.75))
    sh.text(lang["terms"], px + pw + 10 * S, mid - amp * 0.45 - 52 * S, 12)

    # ============================== spectrum of the outline ==============================
    x, y0, w, h = SP
    sh.header(lang["spectrum_header"], x, y0, w)
    sh.formula(lang["spectrum_caption"] + (": " + texts["spectrum"] if "spectrum" in texts else ""), x, y0 + 36 * S, 13, sh.TEXT)
    px, py, pw, ph = x, y0 + 64 * S, w, h - 74 * S
    sh.frame(px, py, pw, ph)
    base_y = py + ph - 26 * S
    top = max(abs(cn[n]) for n in range(-30, 31) if n)
    for n in range(-30, 31):
        xx = px + pw * (n + 31) / 62
        if n == 0:
            sh.poly([(xx, base_y), (xx, py + 14 * S)], col(LINES), 2 * S, dash=[4 * S, 4 * S])
            sh.formula("c_{0}", xx + 6 * S, py + 30 * S, 13, sh.TEXT)
            continue
        v = max(0.0, (math.log10(abs(cn[n]) / top) + 3.2) / 3.2)
        c = col(ACCENT) if n > 0 else col(ACCENT2)
        yy = base_y - v * (ph - 50 * S)
        sh.poly([(xx, base_y), (xx, yy)], c, 2.4 * S, glow=abs(n) <= 2)
        sh.disc(xx, yy, 3.4 * S, c)
        if n % 10 == 0 or abs(n) == 1:
            sh.text(f"{n}", xx, base_y + 18 * S, 11, center=True)
    sh.poly([(px, base_y), (px + pw, base_y)], (1, 1, 1, 0.15), 1 * S)

    # ============================== column: reconstructions ==============================
    sh.header(lang["reconstruction_header"], RX, 90 * S, RW)
    rh = (H - 330 * S) / 4
    for i, Kr in enumerate(job["reconstructions"][:4]):
        ry = 120 * S + rh * i
        sh.frame(RX, ry, RW, rh - 22 * S)
        sh.formula(f"N = {Kr}", RX + 14 * S, ry + 28 * S, 16, col(ACCENT, 0.85))
        sh.text(f"{2 * Kr + 1} {plural(2 * Kr + 1, lang)}", RX + 14 * S, ry + 50 * S, 13)
        _, Zr, Pr = placer(RX + RW * 0.58, ry + (rh - 22 * S) * 0.5, (rh - 22 * S) * 0.76)
        sh.poly([Pr(*p) for p in OUTLINE], col(LINES), 1.2 * S, close=True, dash=[6 * S, 5 * S])
        tr = np.linspace(0, 1, 1500 if Kr <= 40 else 6000)
        sh.poly([Zr(v) for v in recon(Kr, tr)], col(ACCENT), 2.2 * S, glow=True, close=True)

    # ============================== title block ==============================
    tw_, th_ = 420 * S, 96 * S
    tx, ty = W - tw_ - 60 * S, H - th_ - 40 * S
    b.new_path(); b.set_source_rgba(0, 0, 0, 0.2); b.rectangle(tx, ty, tw_, th_); b.fill()
    b.set_source_rgba(*col(LINES)); b.set_line_width(1.5 * S); b.rectangle(tx, ty, tw_, th_)
    b.move_to(tx, ty + th_ * 0.5); b.line_to(tx + tw_, ty + th_ * 0.5)
    b.move_to(tx + tw_ * 0.62, ty + th_ * 0.5); b.line_to(tx + tw_ * 0.62, ty + th_); b.stroke()
    title, size = job["title"], 20
    while sh.width(title, size, True) > tw_ - 28 * S and size > 10:   # long title – smaller font
        size -= 1
    sh.text(title, tx + 14 * S, ty + th_ * 0.5 - 15 * S, size, col(ACCENT, 0.85), bold=True)
    sh.text(f"{lang['sheet']}   {job['tag']}", tx + 14 * S, ty + th_ - 17 * S, 13, col(k["text"], 0.5))
    sh.text(f"{lang['revision']} {job['revision']}", tx + tw_ * 0.62 + 14 * S, ty + th_ - 17 * S, 13, col(k["text"], 0.5))
    if texts.get("author"):
        a_ = texts["author"]
        sh.text(a_, tx + tw_ - sh.width(a_, 12), ty - 14 * S, 12, col(k["text"], 0.4))

    sh.save(path)


# ============================== config and command line ==============================
def main():
    ap = argparse.ArgumentParser(description="Fourier wallpaper generator: epicycles draw the outline of an SVG graphic.",
                                 epilog="Without -w and -g: all wallpapers from the config.")
    ap.add_argument("-c", "--config", default=os.path.join(HERE, "config.toml"), help="TOML file with parameters")
    ap.add_argument("-w", "--wallpaper", action="append", help="only the wallpaper with this name (repeatable)")
    ap.add_argument("-g", "--graphic", help="any SVG file instead of the wallpapers from the config")
    ap.add_argument("-l", "--language", help="language code, e.g. en, pl (file languages/<code>.toml)")
    ap.add_argument("-r", "--resolution", action="append", help="e.g. 3440x1440 (repeatable)")
    ap.add_argument("-t", "--title", help='text on the title block, e.g. "AMBERFROST // FOURIER"')
    ap.add_argument("-n", "--circles", type=int, help="K: the chain has 2K+1 circles")
    ap.add_argument("--color", action="append", default=[], metavar="KEY=#RRGGBB",
                    help="colour from [colors]: background, accent, accent2, text, lines, details")
    ap.add_argument("-o", "--output", help="directory for the PNG files")
    args = ap.parse_args()

    with open(args.config, "rb") as f:
        cfg = tomllib.load(f)
    cdir = os.path.dirname(os.path.abspath(args.config))
    general, colors = cfg.get("general", {}), cfg.get("colors", {})
    if args.graphic:
        name = os.path.splitext(os.path.basename(args.graphic))[0]
        jobs = [{"name": name, "graphic": os.path.abspath(args.graphic), "tag": name.upper()}]
    else:
        jobs = [dict(t, graphic=os.path.join(cdir, t["graphic"])) for t in cfg.get("wallpaper", [])
                if not args.wallpaper or t["name"] in args.wallpaper]
        if not jobs:
            sys.exit(f"no wallpapers {args.wallpaper} in {args.config}")
    for kv in args.color:
        key, _, val = kv.partition("=")
        colors[key] = val
    language = args.language or general.get("language", "en")
    with open(os.path.join(HERE, "languages", f"{language}.toml"), "rb") as f:
        lang = tomllib.load(f)
    sizes = args.resolution or general.get("resolutions", ["3440x1440"])
    out = os.path.normpath(args.output or os.path.join(cdir, general.get("output", ".")))
    os.makedirs(out, exist_ok=True)

    for t in jobs:
        job = copy.deepcopy(general)
        job.update({k: v for k, v in t.items() if k != "colors"})
        # colours given on the command line win over per-wallpaper ones
        job["colors"] = dict(colors, **({} if args.color else t.get("colors", {})))
        job["language"] = language
        job.setdefault("circles", 40); job.setdefault("reconstructions", [1, 3, 8, 30])
        job.setdefault("title", "FOURIER"); job.setdefault("revision", "A"); job.setdefault("font", "Hack")
        if args.circles:
            job["circles"] = args.circles
        if args.title:
            job["title"] = args.title
        shape = analyze(job["graphic"], job.get("graphic_colors", 3), job.get("extras", []))
        for size in sizes:
            W, H = map(int, size.lower().split("x"))
            path = os.path.join(out, f"fourier-{job['name']}-{language}_{W}x{H}.png")
            render(job, shape, W, H, lang, path)
            print(path)


if __name__ == "__main__":
    main()
