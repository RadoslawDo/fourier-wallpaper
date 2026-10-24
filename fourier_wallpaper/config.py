"""Config files: config.toml (the defaults), configs/<wallpaper>.toml, layouts/<layout>.toml, "extends";
what they say about one wallpaper, as a Job."""
import os
import re
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field, fields
from typing import Any, Literal, Self

from .canvas import FORMATS
from .layout import LAYOUT, LAYOUT_ULTRAWIDE, check_layout
from .tables import Table, is_list, is_table

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the project folder
CONFIGS = os.path.join(ROOT, "configs")          # one file per wallpaper (config = "<name>" in a recipe)
LAYOUTS = os.path.join(ROOT, "layouts")          # layouts of the modules (layouts = ["<name>"] in a recipe)

Chain = list[tuple[str, Table]]                  # the files of a config, base first: (path, contents)


def merge(base: Table, over: Table) -> Table:
    """Config over base: tables merged key by key, other values (also arrays) replaced."""
    out = dict(base)
    for k, v in over.items():
        out[k] = merge(out[k], v) if is_table(v) and is_table(out.get(k)) else v
    return out


def config_chain(path: str) -> Chain:
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


def find_config(name: str, folder: str, relative_to: str = ".") -> str:
    """A path (relative to relative_to), or a bare name of a file in the folder (e.g. "tux" → configs/tux.toml)."""
    name = os.path.expanduser(name)
    for path in (os.path.join(relative_to, name), os.path.join(folder, name), os.path.join(folder, name + ".toml")):
        if os.path.isfile(path):
            return path
    sys.exit(f"not found: {name!r} (neither a file nor {os.path.relpath(folder, ROOT)}/{name}.toml)")


def merge_chain(chain: Chain) -> Table:
    """One config from its files (each file listed once, where it first comes)."""
    seen: set[str] = set()
    cfg: Table = {}
    for path, c in chain:
        if path not in seen:
            seen.add(path); cfg = merge(cfg, c)
    return cfg


# ============================== what the files say about one wallpaper ==============================
SETTINGS = {"circles", "reconstructions", "title", "revision", "font", "graphic_colors"}   # [general] or [wallpaper]
SECTIONS: dict[str, set[str] | None] = {
    "general": SETTINGS | {"language", "resolutions", "layouts", "output", "format", "quality"},
    "wallpaper": SETTINGS | {"name", "graphic", "tag", "outlines", "extras", "texts", "colors"},
    "colors": None, "layout": None, "layout_ultrawide": None,        # checked by Palette / check_layout
}


@dataclass(frozen=True)
class Palette:
    background: str
    accent: str                  # trace, headers, formulas, n > 0
    accent2: str                 # chain of circles, n < 0
    text: str
    lines: str                   # target outline, header rules
    details: str                 # inner lines of the graphic

    @classmethod
    def from_table(cls, table: Table, where: str) -> Self:
        names = [f.name for f in fields(cls)]
        if set(table) - set(names):
            sys.exit(f"{where}: unknown colours {sorted(set(table) - set(names))} (colours: {', '.join(names)})")
        if set(names) - set(table):
            sys.exit(f"{where}: missing colours {sorted(set(names) - set(table))}")
        for k, v in table.items():
            if not (isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v)):
                sys.exit(f"{where}.{k} = {v!r}: a colour as #RRGGBB")
        return cls(**table)


@dataclass(frozen=True)
class Screen:
    width: int
    height: int

    @classmethod
    def parse(cls, text: str) -> Self:
        m = re.fullmatch(r"(\d+)[xX](\d+)", str(text))
        if not m or 0 in (int(m[1]), int(m[2])):
            sys.exit(f"resolution {text!r}: WIDTHxHEIGHT, e.g. 3440x1440")
        return cls(int(m[1]), int(m[2]))

    @property
    def ultrawide(self) -> bool:         # the top-left corner stays empty there – a desktop widget sits there
        return self.width / self.height > 2

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"


@dataclass(frozen=True)
class ExtraHint:
    """A small shape inside the outline, pointed to in "extras" (position as a fraction of the SVG canvas)."""
    x: float
    y: float
    type: Literal["shape", "circle"] = "shape"


@dataclass(frozen=True)
class WallpaperTexts:
    """[wallpaper.texts.<language>] – all optional."""
    noun: str | None = None      # "The outline of the <noun> is a closed curve"
    closing: str | None = None   # last paragraph of the theory
    spectrum: str | None = None  # note under the spectrum header
    author: str | None = None    # credit above the title block


@dataclass(frozen=True)
class WallpaperSpec:
    """[wallpaper]: the graphic and how to read it."""
    name: str
    graphic: str
    tag: str
    graphic_colors: int = 3
    outlines: int = 1           # separate parts drawn as outlines, the largest first
    extras: tuple[ExtraHint, ...] = ()
    texts: dict[str, WallpaperTexts] = field(default_factory=dict[str, WallpaperTexts])

    def texts_in(self, language: str) -> WallpaperTexts:
        return self.texts.get(language, WallpaperTexts())


@dataclass(frozen=True)
class RenderSettings:
    circles: int = 40                                 # K: the chain has 2K+1 circles
    reconstructions: tuple[int, ...] = (1, 3, 8, 30)  # N of each reconstruction frame
    title: str = "FOURIER"
    revision: str = "A"
    font: str = "Hack"


@dataclass(frozen=True)
class Overrides:
    """What the command line sets over the files."""
    colors: dict[str, str] = field(default_factory=dict[str, str])
    circles: int | None = None
    title: str | None = None
    languages: list[str] | None = None
    resolutions: list[str] | None = None
    output: str | None = None
    formats: list[str] | None = None
    modules: dict[str, Table] = field(default_factory=dict[str, Table])     # --hide / --show


@dataclass(frozen=True)
class Job:
    """One wallpaper in one layout: everything needed to generate its files."""
    spec: WallpaperSpec
    settings: RenderSettings
    palette: Palette
    layers: list[tuple[Table, bool]]  # layout tables in order, (table, ultrawide only)
    languages: tuple[str, ...]
    screens: tuple[Screen, ...]
    output: str                       # folder; "{resolution}" is replaced, e.g. ../3440x1440
    suffix: str = ""                  # after the wallpaper name in the file name (the layout)
    formats: tuple[str, ...] = ("png",)
    quality: int | None = None        # of WebP files: 1–100, None = lossless

    def file_name(self, language: str, screen: Screen, fmt: str = "png") -> str:
        return f"fourier-{self.spec.name}{self.suffix}-{language}_{screen}.{fmt}"

    def folder(self, screen: Screen) -> str:
        return os.path.normpath(self.output.format(resolution=str(screen)))

    def path(self, language: str, screen: Screen, fmt: str = "png") -> str:
        return os.path.join(self.folder(screen), self.file_name(language, screen, fmt))

    def paths(self, language: str, screen: Screen) -> list[str]:
        """Its files in one language and resolution: one per format."""
        return [self.path(language, screen, fmt) for fmt in self.formats]


def _check(value: Any, ok: Callable[[Any], object], where: str, what: str) -> Any:
    if not ok(value):
        sys.exit(f"{where} = {value!r}: {what}")
    return value


def _whole(n: object) -> bool:
    return isinstance(n, int) and not isinstance(n, bool)


def _strings(v: object) -> bool:
    return is_list(v) and all(isinstance(s, str) for s in v)


def check_file(path: str, cfg: Table) -> None:
    """Unknown sections and keys of one config file."""
    for section, table in cfg.items():
        if section not in SECTIONS:
            sys.exit(f"{path}: unknown section [{section}] (sections: {', '.join(SECTIONS)})")
        if not is_table(table):
            sys.exit(f"{path}: {section} must be a table ([{section}])")
        allowed = SECTIONS[section]
        if allowed is not None and set(table) - allowed:
            sys.exit(f"{path}: [{section}] unknown keys {sorted(set(table) - allowed)} (keys: {', '.join(sorted(allowed))})")


def load_job(chain: Chain, suffix: str, overrides: Overrides) -> Job:
    """A Job from the files of one wallpaper (defaults, the wallpaper, the layout) and the command line.
    A setting in [wallpaper] wins over the same one in [general]."""
    for path, c in chain:
        check_file(path, c)
    cfg = merge_chain(chain)
    where = chain[-1][0]
    if "wallpaper" not in cfg:
        sys.exit(f"{where}: no [wallpaper] table")
    general, t = cfg.get("general", {}), cfg["wallpaper"]

    def get(key: str, default: Any) -> Any:
        return t.get(key, general.get(key, default))

    for key in ("name", "graphic", "tag"):
        if key not in t:
            sys.exit(f"{where}: [wallpaper] {key} is missing (name, graphic and tag are required)")
        _check(t[key], lambda v: isinstance(v, str) and v, f"[wallpaper] {key}", "a text")
    extras: list[ExtraHint] = []
    for i, e in enumerate(_check(get("extras", []), is_list, "extras", "a list of { x, y, type }")):
        at = f"extras[{i}]"
        if not is_table(e) or set(e) - {"x", "y", "type"} or not {"x", "y"} <= set(e):
            sys.exit(f"{at} = {e!r}: {{ x = …, y = …, type = \"shape\" | \"circle\" }}")
        for k in ("x", "y"):
            _check(e[k], lambda v: isinstance(v, (int, float)) and 0 <= v <= 1, f"{at}.{k}", "a fraction of the canvas, 0…1")
        _check(e.get("type", "shape"), lambda v: v in ("shape", "circle"), f"{at}.type", '"shape" or "circle"')
        extras.append(ExtraHint(float(e["x"]), float(e["y"]), e.get("type", "shape")))
    texts: dict[str, WallpaperTexts] = {}
    for language, tx in _check(get("texts", {}), is_table, "texts", "a table per language").items():
        at = f"[wallpaper.texts.{language}]"
        allowed = {f.name for f in fields(WallpaperTexts)}
        if not is_table(tx) or set(tx) - allowed:
            sys.exit(f"{at}: keys {', '.join(sorted(allowed))}")
        for k, v in tx.items():
            _check(v, lambda s: isinstance(s, str), f"{at} {k}", "a text")
        texts[language] = WallpaperTexts(**tx)
    spec = WallpaperSpec(name=t["name"], graphic=t["graphic"], tag=t["tag"],
                         graphic_colors=_check(get("graphic_colors", 3), lambda n: _whole(n) and n >= 1,
                                               "graphic_colors", "a whole number ≥ 1"),
                         outlines=_check(t.get("outlines", 1), lambda n: _whole(n) and n >= 1,
                                         "[wallpaper] outlines", "a whole number ≥ 1"),
                         extras=tuple(extras), texts=texts)

    d = RenderSettings()
    reconstructions = _check(get("reconstructions", list(d.reconstructions)),
                             lambda v: is_list(v) and v and all(_whole(n) and n >= 0 for n in v),
                             "reconstructions", "a non-empty list of whole numbers ≥ 0")
    settings = RenderSettings(
        circles=_check(overrides.circles if overrides.circles is not None else get("circles", d.circles),
                       lambda n: _whole(n) and n >= 1, "circles", "a whole number ≥ 1"),
        reconstructions=tuple(reconstructions),
        **{k: _check(v, lambda s: isinstance(s, str), k, "a text")
           for k, v in (("title", overrides.title or get("title", d.title)), ("revision", get("revision", d.revision)),
                        ("font", get("font", d.font)))})

    # colours given on the command line win over the wallpaper's own ones (which are then not used at all)
    colors = dict(cfg.get("colors", {}), **overrides.colors)
    if not overrides.colors:
        colors.update(_check(t.get("colors", {}), lambda v: isinstance(v, dict), "[wallpaper] colors", "a table"))
    palette = Palette.from_table(colors, "[colors]")

    # module layout: built-in, then every file in turn, then the command line; the [layout_ultrawide] of a file
    # is used only on ultrawide screens and wins over the [layout] of the same file (not over later files)
    check_layout(LAYOUT, "built-in layout"); check_layout(LAYOUT_ULTRAWIDE, "built-in layout_ultrawide")
    layers = [(LAYOUT, False), (LAYOUT_ULTRAWIDE, True)]
    for path, c in chain:
        for key, wide in (("layout", False), ("layout_ultrawide", True)):
            check_layout(c.get(key, {}), f"{path}: {key}")
            layers.append((c.get(key, {}), wide))
    layers.append((overrides.modules, False))

    languages = overrides.languages or general.get("language", "en")
    languages = [languages] if isinstance(languages, str) else languages
    _check(languages, lambda v: _strings(v) and v, "language", 'a language code or a list, e.g. ["pl", "en"]')
    resolutions = overrides.resolutions or general.get("resolutions", ["3440x1440"])
    _check(resolutions, lambda v: _strings(v) and v, "resolutions", 'a list, e.g. ["3440x1440"]')
    output = _check(overrides.output or general.get("output", "."), lambda s: isinstance(s, str), "output", "a folder")
    formats = _check(overrides.formats or general.get("format", "png"),
                     lambda v: v in FORMATS or (_strings(v) and v and set(v) <= set(FORMATS)), "format",
                     f'a format or a list of them: {", ".join(FORMATS)}, e.g. ["png", "svg"]')
    formats = [formats] if isinstance(formats, str) else formats
    quality = _check(general.get("quality", "lossless"), lambda v: v == "lossless" or (_whole(v) and 1 <= v <= 100),
                     "quality", '"lossless" or a whole number 1–100 (WebP)')
    return Job(spec, settings, palette, layers, tuple(languages), tuple(Screen.parse(r) for r in resolutions),
               output, suffix, tuple(dict.fromkeys(formats)), None if quality == "lossless" else quality)
