"""Recipes (recipes/*.toml): one file that says which wallpapers to make – in which layouts, languages,
resolutions and variants. Each entry of [[wallpapers]] becomes one Job per layout."""
import os
import sys
from typing import Any

from .config import (CONFIGS, LAYOUTS, ROOT, SECTIONS, Chain, Job, Overrides, config_chain, find_config, load_job,
                     merge_chain)
from .tables import Table, is_list, is_table

RECIPES = os.path.join(ROOT, "recipes")

# keys of an entry: "config" and "layouts", and the keys of a config file without their sections
GENERAL_KEYS = {"language", "resolutions", "output"}
TABLE_KEYS = {"colors", "layout", "layout_ultrawide"}
WALLPAPER_KEYS = SECTIONS["wallpaper"] or set()
ENTRY_KEYS = {"config", "layouts"} | GENERAL_KEYS | TABLE_KEYS | WALLPAPER_KEYS


def load_recipe(path: str) -> tuple[Chain, list[tuple[str, str, Table]]]:
    """The recipe's own settings (a chain of config files, like any config) and its entries as
    (where, folder their paths are relative to, entry). A wallpaper file (configs/…) is a recipe of itself."""
    chain = config_chain(path)
    entries: list[tuple[str, str, Table]] = []
    for file, cfg in chain:
        if "wallpapers" in cfg:           # a recipe that extends another one replaces its entries
            found = cfg.pop("wallpapers")
            if not (is_list(found) and all(is_table(e) for e in found)):
                sys.exit(f"{file}: wallpapers must be a list of tables ([[wallpapers]])")
            entries = [(f"{file}: wallpapers[{i}]", os.path.dirname(file), e) for i, e in enumerate(found)]
    if not entries and "wallpaper" in chain[-1][1]:
        return [], [(chain[-1][0], ROOT, {"config": path})]
    return chain, entries


def entry_config(entry: Table, where: str, folder: str) -> Table:
    """An entry as a config file: its keys put into the sections where they belong."""
    if set(entry) - ENTRY_KEYS:
        sys.exit(f"{where}: unknown keys {sorted(set(entry) - ENTRY_KEYS)} (keys: {', '.join(sorted(ENTRY_KEYS))})")
    if "config" in entry and "graphic" in entry and "name" not in entry:
        sys.exit(f"{where}: with both config and graphic, give the wallpaper a name (the file names would clash)")
    cfg: dict[str, Any] = {}
    for k, v in entry.items():
        if k in TABLE_KEYS:
            cfg[k] = v
        elif k in GENERAL_KEYS or k in WALLPAPER_KEYS:
            section = "general" if k in GENERAL_KEYS else "wallpaper"
            if k in ("graphic", "output") and isinstance(v, str):
                v = os.path.join(folder, os.path.expanduser(v))      # relative to the recipe
            cfg.setdefault(section, {})[k] = v
    return cfg


def recipe_jobs(base: Chain, entries: list[tuple[str, str, Table]], overrides: Overrides) -> list[tuple[str, Job]]:
    """(where, Job) for every entry × layout. base: config.toml and the recipe's own settings."""
    jobs: list[tuple[str, Job]] = []
    for where, folder, entry in entries:
        inline = (where, entry_config(entry, where, folder))
        config = entry.get("config")
        if config is not None and not isinstance(config, str):
            sys.exit(f"{where}: config = {config!r}: a file in configs/ (e.g. \"tux\") or a path")
        own = config_chain(find_config(config, CONFIGS, folder)) if config else []
        layouts = entry.get("layouts") or merge_chain(base + own + [inline]).get("general", {}).get("layouts", ["default"])
        if not (is_list(layouts) and all(isinstance(n, str) for n in layouts)):
            sys.exit(f'{where}: layouts = {layouts!r}: a list of files in layouts/, e.g. ["default", "minimal"]')
        for name in layouts:
            if name == "default":
                jobs.append((where, load_job(base + own + [inline], "", overrides)))
            else:
                path = find_config(name, LAYOUTS)
                suffix = "-" + os.path.splitext(os.path.basename(path))[0]
                jobs.append((where, load_job(base + own + config_chain(path) + [inline], suffix, overrides)))
    return jobs


def check_outputs(jobs: list[tuple[str, Job]]) -> None:
    """No two entries may make the same file."""
    made: dict[str, str] = {}
    for where, job in jobs:
        for language in job.languages:
            for screen in job.screens:
                path = job.path(language, screen)
                if path in made and made[path] != where:
                    sys.exit(f"{made[path]} and {where} both make {path} – give one of them another name")
                made[path] = where
