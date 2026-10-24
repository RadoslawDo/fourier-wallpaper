"""Where the modules go: boxes from the [layout] / [layout_ultrawide] tables."""
import sys
from collections import namedtuple


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
