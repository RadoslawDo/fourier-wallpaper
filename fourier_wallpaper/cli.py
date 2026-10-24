"""Command line: which wallpapers, layouts, languages and resolutions to generate."""
import argparse
import glob
import os
import sys

from .config import CONFIGS, LAYOUTS, ROOT, Overrides, config_chain, find_config, load_job, merge_chain
from .layout import check_layout
from .modules import MODULE_NAMES
from .render import generate


def main() -> None:
    ap = argparse.ArgumentParser(description="Fourier wallpaper generator: epicycles draw the outline of an SVG graphic.",
                                 epilog="config.toml holds the defaults; a wallpaper (-c) and a layout (-L) override them. "
                                        "Without -c: every wallpaper in configs/ (with -g: none). "
                                        "Without -L: the layouts listed in \"layouts\" of [general].")
    ap.add_argument("-c", "--config", action="append", default=[],
                    help="wallpaper: a TOML file or the name of one in configs/, e.g. tux (repeatable)")
    ap.add_argument("-L", "--layout", action="append", default=[],
                    help="layout: a TOML file or the name of one in layouts/, e.g. minimal; "
                         "\"default\" = config.toml alone (repeatable)")
    ap.add_argument("-w", "--wallpaper", action="append", help="only the wallpaper with this name (repeatable)")
    ap.add_argument("-g", "--graphic", help="any SVG file instead of the wallpapers from configs/")
    ap.add_argument("-l", "--language", action="append",
                    help="language code, e.g. en, pl (file languages/<code>.toml; repeatable)")
    ap.add_argument("-r", "--resolution", action="append", help="e.g. 3440x1440 (repeatable)")
    ap.add_argument("-t", "--title", help='text on the title block, e.g. "AMBERFROST // FOURIER"')
    ap.add_argument("-n", "--circles", type=int, help="K: the chain has 2K+1 circles")
    ap.add_argument("--color", action="append", default=[], metavar="KEY=#RRGGBB",
                    help="colour from [colors]: background, accent, accent2, text, lines, details")
    ap.add_argument("--hide", action="append", default=[], metavar="MODULE",
                    help=f"do not draw this module (repeatable): {', '.join(MODULE_NAMES)}")
    ap.add_argument("--show", action="append", default=[], metavar="MODULE", help="draw a module turned off in the config")
    ap.add_argument("-o", "--output", help="directory for the PNG files; {resolution} is replaced, e.g. out/{resolution}")
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
                          resolutions=args.resolution, output=args.output, modules=modules)
    defaults = config_chain(os.path.join(ROOT, "config.toml"))
    if args.graphic:
        name = os.path.splitext(os.path.basename(args.graphic))[0]
        graphic = {"wallpaper": {"name": name, "graphic": os.path.abspath(args.graphic), "tag": name.upper()}}
        wallpapers = [[("-g", graphic)]]
    else:
        paths = [find_config(c, CONFIGS) for c in args.config] or sorted(glob.glob(os.path.join(CONFIGS, "*.toml")))
        wallpapers = [config_chain(p) for p in paths]
    done = 0
    for wallpaper in wallpapers:
        chain = defaults + wallpaper
        layouts = args.layout or merge_chain(chain).get("general", {}).get("layouts", ["default"])
        for name in layouts:
            if name == "default":
                job = load_job(chain, "", overrides)
            else:
                path = find_config(name, LAYOUTS)
                job = load_job(chain + config_chain(path), "-" + os.path.splitext(os.path.basename(path))[0], overrides)
            if not args.wallpaper or job.spec.name in args.wallpaper:
                generate(job)
                done += 1
    if not done:
        sys.exit(f"no wallpapers {args.wallpaper or ''} in {', '.join(c[-1][0] for c in wallpapers) or CONFIGS}")
