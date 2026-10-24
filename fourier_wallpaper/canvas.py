"""The sheet: a cairo surface with a glow layer, and the drawing helpers (lines, text, formulas)."""
from __future__ import annotations

import contextlib
import math
from collections.abc import Generator, Sequence
from typing import TYPE_CHECKING

import cairo
from PIL import Image, ImageFilter

if TYPE_CHECKING:                    # config imports the modules, which import this file
    from .config import Palette
    from .graphic import Point

RGBA = tuple[float, float, float, float]


def col(h: str, a: float = 1.0) -> RGBA:
    return int(h[1:3], 16) / 255, int(h[3:5], 16) / 255, int(h[5:7], 16) / 255, a


class Sheet:
    """Wallpaper canvas: a sharp layer and a glow layer (blurred later), plus drawing helpers."""

    def __init__(self, W: int, H: int, colors: Palette, font: str):
        self.W, self.H, self.S = W, H, H / 1440          # scale relative to 1440 px height
        self.k, self.fontname = colors, font
        self.base, self.b = self._surface()
        self.glow, self.gl = self._surface()
        self.TEXT = col(colors.text, 0.62)

    def _surface(self) -> tuple[cairo.ImageSurface, cairo.Context[cairo.ImageSurface]]:
        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.W, self.H)
        c = cairo.Context(s)
        c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_line_join(cairo.LINE_JOIN_ROUND)
        return s, c

    def poly(self, pts: Sequence[Point], c: RGBA, w: float, glow: bool = False, close: bool = False,
             dash: list[float] | None = None) -> None:
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

    def disc(self, x: float, y: float, r: float, c: RGBA, glow: bool = False) -> None:
        for ctx in (self.b, self.gl) if glow else (self.b,):
            ctx.new_path(); ctx.set_source_rgba(*c); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()

    def circle(self, x: float, y: float, r: float, c: RGBA, w: float) -> None:
        b = self.b
        b.new_path(); b.set_source_rgba(*c); b.set_line_width(w); b.arc(x, y, r, 0, 2 * math.pi); b.stroke()

    def font(self, size: float, bold: bool = False) -> None:
        self.b.select_font_face(self.fontname, cairo.FONT_SLANT_NORMAL,
                                cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
        self.b.set_font_size(size * self.S)

    def width(self, t: str, size: float = 15, bold: bool = False) -> float:
        self.font(size, bold)
        return self.b.text_extents(t).x_advance

    def text(self, t: str, x: float, y: float, size: float = 15, c: RGBA | None = None, bold: bool = False,
             center: bool = False) -> float:
        self.font(size, bold); self.b.set_source_rgba(*(c or self.TEXT))
        if center:
            x -= self.b.text_extents(t).x_advance / 2
        self.b.move_to(x, y); self.b.show_text(t)
        return self.b.text_extents(t).x_advance

    def formula(self, t: str, x: float, y: float, size: float = 20, c: RGBA | None = None) -> float:
        """Formula with _{subscripts} and ^{superscripts} (Hack has no sub/superscript glyphs – smaller, shifted text)."""
        c = c or col(self.k.accent, 0.9)
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

    def para(self, t: str, x: float, y: float, width: float, size: float = 15, lead: float = 1.45) -> float:
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

    def header(self, t: str, x: float, y: float, width: float) -> None:
        """Section header: capitals in the accent colour and a rule to the end of the column."""
        S = self.S
        w = self.text(t, x, y, 16, col(self.k.accent, 0.95), bold=True)
        self.poly([(x + w + 12 * S, y - 6 * S), (x + width, y - 6 * S)], col(self.k.lines), 1.5 * S)

    def frame(self, x: float, y: float, w: float, h: float) -> None:
        b = self.b
        b.new_path(); b.set_source_rgba(1, 1, 1, 0.10); b.set_line_width(1.2 * self.S)
        b.rectangle(x, y, w, h); b.stroke()

    @contextlib.contextmanager
    def scaled(self, factor: float) -> Generator[None, None, None]:
        """Text and line sizes × factor (a module's "scale")."""
        S = self.S
        self.S = S * factor
        try:
            yield
        finally:
            self.S = S

    def save(self, path: str) -> None:
        def pil(s: cairo.ImageSurface) -> Image.Image:
            s.flush()
            return Image.frombuffer("RGBA", (self.W, self.H), bytes(s.get_data()), "raw", "BGRa", 0, 1)
        img = pil(self.base)
        g = pil(self.glow).filter(ImageFilter.GaussianBlur(9 * self.S))
        g.putalpha(g.getchannel("A").point(lambda v: int(v * 0.5)))
        Image.alpha_composite(img, g).convert("RGB").save(path, optimize=True)
