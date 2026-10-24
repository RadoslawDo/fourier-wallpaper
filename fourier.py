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

Parameters: config.toml (the defaults), overridden by configs/<name>.toml (one per wallpaper) and
layouts/<name>.toml (where the modules go: theory, square wave, spectrum, reconstructions… – each can be
turned off, moved and resized); texts: languages/<code>.toml. On an ultrawide screen (width > 2 × height)
the top-left corner stays empty by default – a desktop widget sits there.

Usage:
  python3 fourier.py                          all wallpapers (every config in configs/)
  python3 fourier.py -c tux -l pl             one wallpaper (configs/tux.toml), in Polish
  python3 fourier.py -c tux -L minimal        in another layout (layouts/minimal.toml)
  python3 fourier.py -g drawing.svg -r 2560x1440 -t "MY // WALLPAPER" --color accent=#FF5500
"""
import argparse
import contextlib
import copy
import glob
import math
import os
import subprocess
import sys
import tomllib
from collections import namedtuple

import cairo
import cv2
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIGS = os.path.join(HERE, "configs")          # one file per wallpaper (-c <name>)
LAYOUTS = os.path.join(HERE, "layouts")          # layouts of the modules (-L <name>)


# ============================== graphic → outline, inner lines, small shapes ==============================
def raster(svg, height=1600):
    """SVG → BGRA (numpy) via rsvg-convert; contour coordinates are pixels of this raster."""
    png = subprocess.run(["rsvg-convert", "-h", str(height), svg], capture_output=True, check=True).stdout
    im = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)
    if im is None:
        sys.exit(f"{svg}: rsvg-convert did not give a readable image")
    return im


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
    cv2.setRNGSeed(0)            # the same colours whichever wallpapers were generated before
    _, _, centers = cv2.kmeans(sample, colors, None,  # pyright: ignore[reportCallIssue, reportArgumentType] – None is fine
                               (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5), 3, cv2.KMEANS_PP_CENTERS)
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
            extras.append(("circle", (float(x - r0 + xx), float(y - r0 + yy), float(win[yy, xx]))))
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

    @contextlib.contextmanager
    def scaled(self, factor):
        """Text and line sizes × factor (a module's "scale")."""
        S = self.S
        self.S = S * factor
        try:
            yield
        finally:
            self.S = S

    def save(self, path):
        def pil(s):
            s.flush()
            return Image.frombuffer("RGBA", (self.W, self.H), bytes(s.get_data()), "raw", "BGRa", 0, 1)
        img = pil(self.base)
        g = pil(self.glow).filter(ImageFilter.GaussianBlur(9 * self.S))
        g.putalpha(g.getchannel("A").point(lambda v: int(v * 0.5)))
        Image.alpha_composite(img, g).convert("RGB").save(path, optimize=True)


class Series:
    """Fourier series of the outline, plus placing the graphic (outline and small shapes) on the sheet."""

    def __init__(self, shape):
        self.outline, self.details, self.extras, self.inside = (shape[k] for k in ("outline", "details", "extras", "inside"))
        xs = [p[0] for p in self.outline]; ys = [p[1] for p in self.outline]
        for kind, e in self.extras:
            ep = [(e[0] - e[2], e[1] - e[2]), (e[0] + e[2], e[1] + e[2])] if kind == "circle" else e
            xs += [p[0] for p in ep]; ys += [p[1] for p in ep]
        self.bbox = min(xs), max(xs), min(ys), max(ys)
        self.mid = (self.bbox[0] + self.bbox[1]) / 2, (self.bbox[2] + self.bbox[3]) / 2
        self.cn = self.fourier(self.outline)

    def fourier(self, poly_, M=2048):
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
        mx0, my0 = self.mid
        z = np.array([(x - mx0) - 1j * (y - my0) for x, y in pts])
        return dict(zip(np.fft.fftfreq(M, 1 / M).astype(int), np.fft.fft(z) / M))

    def recon(self, K, ts):
        return sum(self.cn[n] * np.exp(2j * np.pi * n * ts) for n in range(-K, K + 1))

    def placer(self, cx, cy, w, h):
        """The graphic fitted into a w × h box centred at (cx, cy): scale, complex → sheet, graphic px → sheet."""
        BX0, BX1, BY0, BY1 = self.bbox
        mx0, my0 = self.mid
        sc = min(w / (BX1 - BX0), h / (BY1 - BY0))
        return sc, (lambda zz: (cx + sc * zz.real, cy - sc * zz.imag)), (lambda x, y: (cx + sc * (x - mx0), cy + sc * (y - my0)))


# ============================== layout ==============================
MODULES = ("grid", "drawing", "theory", "square", "spectrum", "reconstruction", "title")   # in drawing order
# Box of each module: x, y – top-left corner, w, h – size. A number is px on a 1440 px high screen (scaled with the
# height), "N%" – percent of the screen width (x, w) or height (y, h). A negative x / y is the distance of the
# module's right / bottom edge from the right / bottom edge of the screen; a negative w / h – the screen
# width / height minus that much.
LAYOUT = {
    "grid": {},
    "drawing": {"x": "34.5%", "y": "20%", "w": "40%", "h": "52%"},
    "theory": {"x": 50, "y": 58, "w": 560},
    "square": {"x": 50, "y": 808, "w": 560, "h": 252},
    "spectrum": {"x": 50, "y": 1098, "w": 560, "h": 252},
    "reconstruction": {"x": -60, "y": 78, "w": 500, "h": 1130},
    "title": {"x": -60, "y": -40, "w": 420, "h": 96},
}
# ultrawide screen (width > 2 × height): the top-left corner stays empty – a desktop widget sits there
LAYOUT_ULTRAWIDE = {
    "drawing": {"x": "41.5%", "y": "17%", "w": "44%", "h": "60%"},
    "theory": {"x": 960, "y": 78, "w": 520},
    "square": {"x": 60, "y": 948, "w": 660, "h": 392},
    "spectrum": {"x": 790, "y": 948, "w": 690, "h": 392},
}
KEYS = {"enabled", "x", "y", "w", "h", "scale", "direction", "columns", "empty", "labels", "align"}
Box = namedtuple("Box", "x y w h scale opts")


def check_layout(table, where):
    for m, opts in table.items():
        if m not in MODULES:
            sys.exit(f"{where}: unknown module {m!r} (modules: {', '.join(MODULES)})")
        if set(opts) - KEYS:
            sys.exit(f"{where}.{m}: unknown keys {sorted(set(opts) - KEYS)} (keys: {', '.join(sorted(KEYS))})")
        for k, v in opts.items():
            if k in "xywh" and not (isinstance(v, (int, float)) or isinstance(v, str) and v.endswith("%")):
                sys.exit(f'{where}.{m}.{k} = {v!r}: a number or "N%"')
        if opts.get("align", "center") not in ("left", "center", "right"):
            sys.exit(f'{where}.{m}.align: "left", "center" or "right"')
        if opts.get("direction", "column") not in ("column", "row"):
            sys.exit(f'{where}.{m}.direction: "column" or "row"')
        if not (isinstance(opts.get("columns", 1), int) and opts.get("columns", 1) >= 1):
            sys.exit(f"{where}.{m}.columns: a whole number ≥ 1")
        if not (isinstance(opts.get("empty", []), list) and all(isinstance(c, int) for c in opts.get("empty", []))):
            sys.exit(f"{where}.{m}.empty: a list of cell numbers, e.g. [0, 1]")


def layout(layers, W, H, S):
    """Boxes of the enabled modules. layers: (table, ultrawide only) pairs, later ones win key by key."""
    uw = W / H > 2
    mods = {m: {"enabled": True} for m in MODULES}
    for table, wide in layers:
        if uw or not wide:
            for m, opts in table.items():
                mods[m].update(opts)

    def length(v, total):
        return float(v[:-1]) / 100 * total if isinstance(v, str) else v * S

    def size(v, total):
        n = length(v, total)
        return total + n if str(v).startswith("-") else n

    def position(v, size, total):
        p = length(v, total)
        return total + p - size if str(v).startswith("-") else p

    boxes = {}
    for m, o in mods.items():
        if o["enabled"]:
            w, h = size(o.get("w", 0), W), size(o.get("h", 0), H)
            boxes[m] = Box(position(o.get("x", 0), w, W), position(o.get("y", 0), h, H), w, h, o.get("scale", 1.0), o)
    return boxes


# ============================== modules ==============================
class Wallpaper:
    """One wallpaper at one resolution; each enabled module draws itself into its box."""

    def __init__(self, job, series, W, H, lang):
        self.job, self.f, self.lang, self.k = job, series, lang, job["colors"]
        self.sh = Sheet(W, H, self.k, job["font"])
        self.UW = W / H > 2      # ultrawide screen (with a widget in the top-left corner)
        self.texts = job.get("texts", {}).get(job["language"], {})
        self.boxes = layout(job["layout"], W, H, self.sh.S)

    def render(self, path):
        sh, b, W, H = self.sh, self.sh.b, self.sh.W, self.sh.H
        # background: the sheet
        b.set_source_rgba(*col(self.k["background"])); b.paint()
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
        ACCENT, ACCENT2, BG, LINES = k["accent"], k["accent2"], k["background"], k["lines"]
        OUTLINE, extras, cn = f.outline, f.extras, f.cn
        K = self.job["circles"]      # terms n = -K..K
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
        for d, closed in f.details:
            sh.poly([Pt(*p) for p in d], col(k["details"]), 1.5 * S, close=closed)
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
        sh.disc(cx_, cy_, 5 * S, col(k["text"], 0.8))
        if labels_on:
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
                ce = f.fourier(e, 512)
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
            kind, e = extras[0]
            label = lang["label_circle"] if kind == "circle" else lang["label_ellipse"]
            if kind == "circle":
                ox, oy, er = e
            else:
                ox, oy, er = np.mean([p[0] for p in e]), np.mean([p[1] for p in e]), 0
            x0, y0 = Pt(ox, oy); er *= sc
            if f.inside[int(oy), int(ox)]:
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
        K = self.job["circles"]
        TX, TW = box.x, box.w
        y = box.y + 12 * S
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
            kinds = {kd for kd, _ in self.f.extras}
            last = " ".join([lang["closing_circle"]] * ("circle" in kinds) + [lang["closing_ellipse"]] * ("curve" in kinds)
                            + [lang["closing_rest"]])
        sh.para(last, TX, y, TW)

    # ------------------------------ example: square wave ------------------------------
    def square(self, box):
        sh, S, k, lang = self.sh, self.sh.S, self.k, self.lang
        ACCENT, ACCENT2 = k["accent"], k["accent2"]
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
        sh.poly(sq, col(k["lines"]), 1.5 * S, dash=[8 * S, 6 * S])
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
        sh.formula(lang["spectrum_caption"] + (": " + texts["spectrum"] if "spectrum" in texts else ""), x, y0 + 36 * S, 13, sh.TEXT)
        px, py, pw = x, y0 + 64 * S, w
        ph = box.y + box.h - py
        sh.frame(px, py, pw, ph)
        base_y = py + ph - 26 * S
        top = max(abs(cn[n]) for n in range(-30, 31) if n)
        for n in range(-30, 31):
            xx = px + pw * (n + 31) / 62
            if n == 0:
                sh.poly([(xx, base_y), (xx, py + 14 * S)], col(k["lines"]), 2 * S, dash=[4 * S, 4 * S])
                sh.formula("c_{0}", xx + 6 * S, py + 30 * S, 13, sh.TEXT)
                continue
            v = max(0.0, (math.log10(abs(cn[n]) / top) + 3.2) / 3.2)
            c = col(k["accent"]) if n > 0 else col(k["accent2"])
            yy = base_y - v * (ph - 50 * S)
            sh.poly([(xx, base_y), (xx, yy)], c, 2.4 * S, glow=abs(n) <= 2)
            sh.disc(xx, yy, 3.4 * S, c)
            if n % 10 == 0 or abs(n) == 1:
                sh.text(f"{n}", xx, base_y + 18 * S, 11, center=True)
        sh.poly([(px, base_y), (px + pw, base_y)], (1, 1, 1, 0.15), 1 * S)

    # ------------------------------ reconstructions: a column (or a row) of frames ------------------------------
    def reconstruction(self, box):
        sh, S, k, lang, f = self.sh, self.sh.S, self.k, self.lang, self.f
        Ns, gap = self.job["reconstructions"], 22 * S
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
            sh.formula(f"N = {Kr}", fx + 14 * S, fy + 28 * S, 16, col(k["accent"], 0.85))
            sh.text(f"{2 * Kr + 1} {plural(2 * Kr + 1, lang)}", fx + 14 * S, fy + 50 * S, 13)
            _, Zr, Pr = f.placer(fx + fw * 0.58, fy + fh * 0.5, fw * 0.66, fh * 0.76)
            sh.poly([Pr(*p) for p in f.outline], col(k["lines"]), 1.2 * S, close=True, dash=[6 * S, 5 * S])
            tr = np.linspace(0, 1, 1500 if Kr <= 40 else 6000)
            sh.poly([Zr(v) for v in f.recon(Kr, tr)], col(k["accent"]), 2.2 * S, glow=True, close=True)

    # ------------------------------ title block (the author credit goes above it) ------------------------------
    def title(self, box):
        sh, b, S, k, lang, job = self.sh, self.sh.b, self.sh.S, self.k, self.lang, self.job
        tx, ty, tw_, th_ = box[:4]
        b.new_path(); b.set_source_rgba(0, 0, 0, 0.2); b.rectangle(tx, ty, tw_, th_); b.fill()
        b.set_source_rgba(*col(k["lines"])); b.set_line_width(1.5 * S); b.rectangle(tx, ty, tw_, th_)
        b.move_to(tx, ty + th_ * 0.5); b.line_to(tx + tw_, ty + th_ * 0.5)
        b.move_to(tx + tw_ * 0.62, ty + th_ * 0.5); b.line_to(tx + tw_ * 0.62, ty + th_); b.stroke()
        title, size = job["title"], 20
        while sh.width(title, size, True) > tw_ - 28 * S and size > 10:   # long title – smaller font
            size -= 1
        sh.text(title, tx + 14 * S, ty + th_ * 0.5 - 15 * S, size, col(k["accent"], 0.85), bold=True)
        sh.text(f"{lang['sheet']}   {job['tag']}", tx + 14 * S, ty + th_ - 17 * S, 13, col(k["text"], 0.5))
        sh.text(f"{lang['revision']} {job['revision']}", tx + tw_ * 0.62 + 14 * S, ty + th_ - 17 * S, 13, col(k["text"], 0.5))
        if self.texts.get("author"):
            a_ = self.texts["author"]
            sh.text(a_, tx + tw_ - sh.width(a_, 12), ty - 14 * S, 12, col(k["text"], 0.4))


# ============================== config and command line ==============================
def merge(base, over):
    """Config over base: tables merged key by key, other values (also arrays) replaced."""
    out = dict(base)
    for k, v in over.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def config_chain(path):
    """The files a config is made of, base first: what it "extends" (if anything), then the file itself.
    Paths in a file are relative to that file."""
    with open(path, "rb") as f:
        cfg = tomllib.load(f)
    cdir = os.path.dirname(os.path.abspath(path))
    if "output" in cfg.get("general", {}):
        cfg["general"]["output"] = os.path.join(cdir, cfg["general"]["output"])
    if "graphic" in cfg.get("wallpaper", {}):
        cfg["wallpaper"]["graphic"] = os.path.join(cdir, cfg["wallpaper"]["graphic"])
    base = cfg.pop("extends", None)
    return (config_chain(os.path.join(cdir, base)) if base else []) + [(os.path.abspath(path), cfg)]


def find_config(name, folder):
    """-c / -L: a path, or a bare name of a file in the folder (e.g. "tux" → configs/tux.toml)."""
    for path in (name, os.path.join(folder, name), os.path.join(folder, name + ".toml")):
        if os.path.isfile(path):
            return path
    sys.exit(f"not found: {name!r} (neither a file nor {os.path.relpath(folder, HERE)}/{name}.toml)")


def main():
    ap = argparse.ArgumentParser(description="Fourier wallpaper generator: epicycles draw the outline of an SVG graphic.",
                                 epilog="config.toml holds the defaults; a wallpaper (-c) and a layout (-L) override them. "
                                        "Without -c: every wallpaper in configs/ (with -g: none). "
                                        "Without -L: the layouts listed in \"layouts\" of [general].")
    ap.add_argument("-c", "--config", action="append", default=[],
                    help="wallpaper: a TOML file or the name of one in configs/, e.g. tux (repeatable)")
    ap.add_argument("-L", "--layout", action="append", default=[],
                    help="layout: a TOML file or the name of one in layouts/, e.g. minimal; "
                         "\"default\" = config.toml alone (repeatable)")
    ap.add_argument("-w", "--wallpaper", action="append", help="only the wallpaper with this name (repeatable)")
    ap.add_argument("-g", "--graphic", help="any SVG file instead of the wallpapers from configs/")
    ap.add_argument("-l", "--language", action="append",
                    help="language code, e.g. en, pl (file languages/<code>.toml; repeatable)")
    ap.add_argument("-r", "--resolution", action="append", help="e.g. 3440x1440 (repeatable)")
    ap.add_argument("-t", "--title", help='text on the title block, e.g. "AMBERFROST // FOURIER"')
    ap.add_argument("-n", "--circles", type=int, help="K: the chain has 2K+1 circles")
    ap.add_argument("--color", action="append", default=[], metavar="KEY=#RRGGBB",
                    help="colour from [colors]: background, accent, accent2, text, lines, details")
    ap.add_argument("--hide", action="append", default=[], metavar="MODULE",
                    help=f"do not draw this module (repeatable): {', '.join(MODULES)}")
    ap.add_argument("--show", action="append", default=[], metavar="MODULE", help="draw a module turned off in the config")
    ap.add_argument("-o", "--output", help="directory for the PNG files; {resolution} is replaced, e.g. out/{resolution}")
    args = ap.parse_args()

    cli = {m: {"enabled": False} for m in args.hide} | {m: {"enabled": True} for m in args.show}
    check_layout(cli, "--hide/--show")
    defaults = config_chain(os.path.join(HERE, "config.toml"))
    if args.graphic:
        name = os.path.splitext(os.path.basename(args.graphic))[0]
        graphic = {"wallpaper": {"name": name, "graphic": os.path.abspath(args.graphic), "tag": name.upper()}}
        wallpapers = [[("-g", graphic)]]
    else:
        paths = [find_config(c, CONFIGS) for c in args.config] or sorted(glob.glob(os.path.join(CONFIGS, "*.toml")))
        wallpapers = [config_chain(p) for p in paths]
    done = 0
    for wallpaper in wallpapers:
        chain = defaults + wallpaper
        layouts = args.layout or merge_chain(chain).get("general", {}).get("layouts", ["default"])
        for name in layouts:
            if name == "default":
                done += generate(chain, "", args, cli)
            else:
                path = find_config(name, LAYOUTS)
                done += generate(chain + config_chain(path), "-" + os.path.splitext(os.path.basename(path))[0], args, cli)
    if not done:
        sys.exit(f"no wallpapers {args.wallpaper or ''} in {', '.join(c[-1][0] for c in wallpapers) or CONFIGS}")


def merge_chain(chain):
    """One config from its files (each file listed once, where it first comes)."""
    seen, cfg = set(), {}
    for path, c in chain:
        if path not in seen:
            seen.add(path); cfg = merge(cfg, c)
    return cfg


def generate(chain, suffix, args, cli):
    """One wallpaper (config files: defaults, the wallpaper, the layout) in every language and resolution.
    suffix – added to the file name after the wallpaper name (the layout, empty for the default one)."""
    cfg = merge_chain(chain)
    if "wallpaper" not in cfg:
        sys.exit(f"{chain[-1][0]}: no [wallpaper] table")
    t = cfg["wallpaper"]
    if args.wallpaper and t["name"] not in args.wallpaper:
        return False
    general, colors = cfg.get("general", {}), dict(cfg.get("colors", {}))
    for kv in args.color:
        key, _, val = kv.partition("=")
        colors[key] = val
    languages = args.language or general.get("language", "en")
    languages = [languages] if isinstance(languages, str) else languages
    sizes = args.resolution or general.get("resolutions", ["3440x1440"])
    # "{resolution}" in the output path gives a folder per resolution (e.g. one per monitor for a slideshow)
    out = args.output or general.get("output", ".")

    job = copy.deepcopy(general)
    job.update({k: v for k, v in t.items() if k != "colors"})
    # colours given on the command line win over the wallpaper's own ones
    job["colors"] = dict(colors, **({} if args.color else t.get("colors", {})))
    job.setdefault("circles", 40); job.setdefault("reconstructions", [1, 3, 8, 30])
    job.setdefault("title", "FOURIER"); job.setdefault("revision", "A"); job.setdefault("font", "Hack")
    if args.circles:
        job["circles"] = args.circles
    if args.title:
        job["title"] = args.title
    # module layout: built-in, then every file in turn, then the command line; the [layout_ultrawide] of a file
    # is used only on ultrawide screens and wins over the [layout] of the same file (not over later files)
    job["layout"] = [(LAYOUT, False), (LAYOUT_ULTRAWIDE, True)]
    for path, c in chain:
        for key, wide in (("layout", False), ("layout_ultrawide", True)):
            check_layout(c.get(key, {}), f"{path}: {key}")
            job["layout"].append((c.get(key, {}), wide))
    job["layout"].append((cli, False))
    series = Series(analyze(job["graphic"], job.get("graphic_colors", 3), job.get("extras", [])))
    for language in languages:
        with open(os.path.join(HERE, "languages", f"{language}.toml"), "rb") as f:
            lang = tomllib.load(f)
        job["language"] = language
        for size in sizes:
            W, H = map(int, size.lower().split("x"))
            folder = os.path.normpath(out.format(resolution=f"{W}x{H}"))
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, f"fourier-{job['name']}{suffix}-{language}_{W}x{H}.png")
            Wallpaper(job, series, W, H, lang).render(path)
            print(path)
    return True


if __name__ == "__main__":
    main()
