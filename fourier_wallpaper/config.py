"""Config files: config.toml (the defaults), configs/<wallpaper>.toml, layouts/<layout>.toml, "extends"."""
import os
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the project folder
CONFIGS = os.path.join(ROOT, "configs")          # one file per wallpaper (-c <name>)
LAYOUTS = os.path.join(ROOT, "layouts")          # layouts of the modules (-L <name>)


def merge(base, over):
    """Config over base: tables merged key by key, other values (also arrays) replaced."""
    out = dict(base)
    for k, v in over.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def config_chain(path):
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


def find_config(name, folder):
    """-c / -L: a path, or a bare name of a file in the folder (e.g. "tux" → configs/tux.toml)."""
    for path in (name, os.path.join(folder, name), os.path.join(folder, name + ".toml")):
        if os.path.isfile(path):
            return path
    sys.exit(f"not found: {name!r} (neither a file nor {os.path.relpath(folder, ROOT)}/{name}.toml)")


def merge_chain(chain):
    """One config from its files (each file listed once, where it first comes)."""
    seen, cfg = set(), {}
    for path, c in chain:
        if path not in seen:
            seen.add(path); cfg = merge(cfg, c)
    return cfg
