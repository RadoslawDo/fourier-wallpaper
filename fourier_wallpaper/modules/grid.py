"""Grid of the sheet (the box is not used)."""
from .base import Module, RenderContext


class Grid(Module):
    name = "grid"

    def draw(self, ctx: RenderContext, box):
        b, S, W, H = ctx.sheet.b, ctx.sheet.S, ctx.sheet.W, ctx.sheet.H
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
