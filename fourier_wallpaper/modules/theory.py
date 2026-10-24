"""Theory (h is not used – the text sets the height)."""
from ..graphic import Circle, Curve
from ..texts import plural
from .base import Box, Module, RenderContext


class Theory(Module):
    name = "theory"
    box = "xyw"                      # the text sets the height

    def draw(self, ctx: RenderContext, box: Box) -> None:
        sh, S, lang, texts = ctx.sheet, ctx.sheet.S, ctx.lang, ctx.texts
        K = ctx.settings.circles
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
        parts = len(ctx.shape.outlines)
        if parts > 1:
            y += 10 * S
            y = sh.para(lang["theory_parts"].format(parts=parts, total=parts * (2 * K + 1),
                                                    circles=plural(parts * (2 * K + 1), lang)), TX, y, TW)
        y += 10 * S
        y = sh.para(lang["theory_5"], TX, y, TW)
        y += 10 * S
        if texts.closing is not None:
            last = texts.closing
        else:
            kinds = {type(e) for e in ctx.shape.extras}
            last = " ".join([lang["closing_circle"]] * (Circle in kinds) + [lang["closing_ellipse"]] * (Curve in kinds)
                            + [lang["closing_rest"]])
        sh.para(last, TX, y, TW)
