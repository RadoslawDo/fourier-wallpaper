"""What every module of the wallpaper is, and what it gets to draw with."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:                    # only for the type checker – config imports the module list at run time
    from ..canvas import Sheet
    from ..config import Palette, RenderSettings, WallpaperSpec, WallpaperTexts
    from ..graphic import Shape
    from ..series import Series


@dataclass(frozen=True)
class Box:
    """Where a module goes, in px of the screen, and the values of all its options (defaults filled in)."""
    x: float
    y: float
    w: float
    h: float
    scale: float
    opts: dict[str, Any]


@dataclass(frozen=True)
class RenderContext:
    """One wallpaper at one resolution, as the modules see it."""
    sheet: Sheet                     # where to draw; sheet.S is the scale (× the module's "scale" while it draws)
    palette: Palette
    series: Series                   # Fourier series of the outline, placing the graphic in a box
    shape: Shape                     # outline, inner lines and small shapes of the graphic
    settings: RenderSettings
    spec: WallpaperSpec
    texts: WallpaperTexts            # the wallpaper's own texts in this language
    lang: dict[str, Any]             # languages/<code>.toml
    ultrawide: bool                  # width > 2 × height (a desktop widget in the top-left corner)
    boxes: dict[str, Box]            # boxes of all enabled modules (e.g. to keep a label clear of them)


@dataclass(frozen=True)
class Option:
    """One key of a module's table in [layout]: its default and what values it takes."""
    default: Any
    ok: Callable[[Any], object]
    what: str                        # the allowed values, for the error message


def _number(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _length(v: object) -> bool:
    if isinstance(v, str) and v.endswith("%"):
        try:
            float(v[:-1])
            return True
        except ValueError:
            return False
    return _number(v)


ENABLED = Option(True, lambda v: isinstance(v, bool), "true or false")
LENGTH = Option(0, _length, 'a number (px on a 1440 px high screen) or "N%"')
SCALE = Option(1.0, lambda v: _number(v) and v > 0, "a number > 0")


class Module(ABC):
    """One part of the wallpaper, drawn into its box from the layout."""
    name: ClassVar[str]              # the name in [layout], --hide, --show
    box: ClassVar[str] = "xywh"      # which of x, y, w, h it has ("" – no box, and no scale either)
    options: ClassVar[dict[str, Option]] = {}    # its own keys, on top of enabled, x, y, w, h, scale

    @classmethod
    def keys(cls) -> dict[str, Option]:
        """All keys of the module's table in [layout]."""
        return {"enabled": ENABLED, **{k: LENGTH for k in cls.box}, **({"scale": SCALE} if cls.box else {}),
                **cls.options}

    @abstractmethod
    def draw(self, ctx: RenderContext, box: Box) -> None: ...
