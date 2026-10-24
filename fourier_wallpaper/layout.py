"""Where the modules go: boxes from the [layout] / [layout_ultrawide] tables."""
import sys
from dataclasses import dataclass
from typing import Any

from .modules import BY_NAME

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

@dataclass(frozen=True)
class Box:
    """Where a module goes, in px of the screen, and the values of all its options (defaults filled in)."""
    x: float
    y: float
    w: float
    h: float
    scale: float
    opts: dict[str, Any]


def check_layout(table, where):
    for m, opts in table.items():
        if m not in BY_NAME:
            sys.exit(f"{where}: unknown module {m!r} (modules: {', '.join(BY_NAME)})")
        if not isinstance(opts, dict):
            sys.exit(f"{where}.{m} = {opts!r}: a table, e.g. {{ enabled = false }}")
        keys = BY_NAME[m].keys()
        if set(opts) - set(keys):
            sys.exit(f"{where}.{m}: unknown keys {sorted(set(opts) - set(keys))} (keys of {m}: {', '.join(keys)})")
        for k, v in opts.items():
            if not keys[k].ok(v):
                sys.exit(f"{where}.{m}.{k} = {v!r}: {keys[k].what}")


def layout(layers, W, H, S):
    """Boxes of the enabled modules. layers: (table, ultrawide only) pairs, later ones win key by key."""
    uw = W / H > 2
    mods = {m: {k: o.default for k, o in cls.keys().items()} for m, cls in BY_NAME.items()}
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
            boxes[m] = Box(position(o.get("x", 0), w, W), position(o.get("y", 0), h, H), w, h, o.get("scale", 1.0),
                           {k: v for k, v in o.items() if k in BY_NAME[m].options})
    return boxes
