"""Title block (the author credit goes above it)."""
from ..canvas import col
from .base import Box, Module, RenderContext


class Title(Module):
    name = "title"

    def draw(self, ctx: RenderContext, box: Box) -> None:
        sh, b, S, k, lang, st = ctx.sheet, ctx.sheet.b, ctx.sheet.S, ctx.palette, ctx.lang, ctx.settings
        tx, ty, tw_, th_ = box.x, box.y, box.w, box.h
        b.new_path(); b.set_source_rgba(0, 0, 0, 0.2); b.rectangle(tx, ty, tw_, th_); b.fill()
        b.set_source_rgba(*col(k.lines)); b.set_line_width(1.5 * S); b.rectangle(tx, ty, tw_, th_)
        b.move_to(tx, ty + th_ * 0.5); b.line_to(tx + tw_, ty + th_ * 0.5)
        b.move_to(tx + tw_ * 0.62, ty + th_ * 0.5); b.line_to(tx + tw_ * 0.62, ty + th_); b.stroke()
        title, size = st.title, 20
        while sh.width(title, size, True) > tw_ - 28 * S and size > 10:   # long title – smaller font
            size -= 1
        sh.text(title, tx + 14 * S, ty + th_ * 0.5 - 15 * S, size, col(k.accent, 0.85), bold=True)
        sh.text(f"{lang['sheet']}   {ctx.spec.tag}", tx + 14 * S, ty + th_ - 17 * S, 13, col(k.text, 0.5))
        sh.text(f"{lang['revision']} {st.revision}", tx + tw_ * 0.62 + 14 * S, ty + th_ - 17 * S, 13, col(k.text, 0.5))
        if ctx.texts.author:
            a_ = ctx.texts.author
            sh.text(a_, tx + tw_ - sh.width(a_, 12), ty - 14 * S, 12, col(k.text, 0.4))
