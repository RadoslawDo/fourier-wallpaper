"""The modules of the wallpaper. A new module: a Module subclass in its own file, added to MODULES."""
from .base import Module, RenderContext
from .drawing import Drawing
from .grid import Grid
from .reconstruction import Reconstruction
from .spectrum import Spectrum
from .square import Square
from .theory import Theory
from .title import Title

MODULES: tuple[type[Module], ...] = (Grid, Drawing, Theory, Square, Spectrum, Reconstruction, Title)   # drawing order
MODULE_NAMES = tuple(m.name for m in MODULES)

__all__ = ["MODULES", "MODULE_NAMES", "Module", "RenderContext"]
