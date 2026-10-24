"""What every module of the wallpaper is, and what it gets to draw with."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:                    # only for the type checker – config imports the module list at run time
    from ..canvas import Sheet
    from ..config import Palette, RenderSettings, WallpaperSpec, WallpaperTexts
    from ..graphic import Shape
    from ..layout import Box
    from ..series import Series


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


class Module(ABC):
    """One part of the wallpaper, drawn into its box from the layout."""
    name: ClassVar[str]              # the name in [layout], --hide, --show

    @abstractmethod
    def draw(self, ctx: RenderContext, box: Box) -> None: ...
