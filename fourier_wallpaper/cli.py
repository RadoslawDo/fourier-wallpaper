"""Command line: which wallpapers, layouts, languages and resolutions to generate."""
import argparse
import os
import sys

from . import __version__
from .canvas import FORMATS
from .config import ROOT, Overrides, config_chain, find_config
from .layout import check_layout
from .modules import MODULE_NAMES
from .recipe import RECIPES, check_outputs, load_recipe, recipe_jobs
from .render import generate


def main() -> None:
    ap = argparse.ArgumentParser(description="Fourier wallpaper generator: epicycles draw the outline of an SVG graphic.",
                                 epilog="config.toml holds the defaults; a recipe says which wallpapers to make, in which "
                                        "layouts, languages and resolutions. The options below override the recipe.")
    ap.add_argument("--version", action="version", version=f"fourier-wallpaper {__version__}")
    ap.add_argument("recipe", nargs="?", default="default",
                    help="a TOML file or the name of one in recipes/ (default: recipes/default.toml); "
                         "a wallpaper file (configs/…) makes just that wallpaper")
    ap.add_argument("-w", "--wallpaper", action="append", help="only the wallpaper with this name (repeatable)")
    ap.add_argument("-g", "--graphic", help="any SVG file instead of the wallpapers of the recipe")
    ap.add_argument("-l", "--language", action="append",
                    help="language code, e.g. en, pl (file languages/<code>.toml; repeatable)")
    ap.add_argument("-r", "--resolution", action="append", help="e.g. 3440x1440 (repeatable)")
    ap.add_argument("-t", "--title", help='text on the title block, e.g. "MY // WALLPAPER"')
    ap.add_argument("-n", "--circles", type=int, help="K: the chain has 2K+1 circles")
    ap.add_argument("--color", action="append", default=[], metavar="KEY=#RRGGBB",
                    help="colour from [colors]: background, accent, accent2, text, lines, details")
    ap.add_argument("--hide", action="append", default=[], metavar="MODULE",
                    help=f"do not draw this module (repeatable): {', '.join(MODULE_NAMES)}")
    ap.add_argument("--show", action="append", default=[], metavar="MODULE", help="draw a module turned off in the config")
    ap.add_argument("-o", "--output", help="directory for the files; {resolution} is replaced, e.g. out/{resolution}")
    ap.add_argument("-f", "--format", action="append", choices=FORMATS, help="file format (repeatable; default: png)")
    args = ap.parse_args()

    modules = {m: {"enabled": False} for m in args.hide} | {m: {"enabled": True} for m in args.show}
    check_layout(modules, "--hide/--show")
    colors: dict[str, str] = {}
    for kv in args.color:
        key, sep, val = kv.partition("=")
        if not sep:
            sys.exit(f"--color {kv!r}: KEY=#RRGGBB, e.g. accent=#FF5500")
        colors[key] = val
    overrides = Overrides(colors=colors, circles=args.circles, title=args.title, languages=args.language,
                          resolutions=args.resolution, output=args.output,
                          formats=args.format, modules=modules)
    recipe = find_config(args.recipe, RECIPES)
    settings, entries = load_recipe(recipe)
    if args.graphic:
        name = os.path.splitext(os.path.basename(args.graphic))[0]
        entries = [("-g", ROOT, {"graphic": os.path.abspath(args.graphic), "name": name, "tag": name.upper()})]
    if not entries:
        sys.exit(f"{recipe}: no wallpapers – add [[wallpapers]] entries (see recipes/default.toml)")
    jobs = recipe_jobs(config_chain(os.path.join(ROOT, "config.toml")) + settings, entries, overrides)
    jobs = [(where, job) for where, job in jobs if not args.wallpaper or job.spec.name in args.wallpaper]
    if not jobs:
        sys.exit(f"no wallpapers {args.wallpaper} in {recipe}")
    check_outputs(jobs)
    for _, job in jobs:
        generate(job)
