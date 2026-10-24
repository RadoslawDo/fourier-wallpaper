# Configuration

## Recipes

A **recipe** (`recipes/*.toml`) is the file that controls a run: which wallpapers to make, in which
layouts, languages and resolutions, and their variants. Each `[[wallpapers]]` entry is one wallpaper:

```toml
# recipes/desk.toml  →  python3 fourier.py recipes/desk.toml
[general]                                   # for the whole recipe
resolutions = ["3440x1440", "1920x1200"]
language = ["pl"]
output = "~/Pictures/Wallpapers/{resolution}"

[[wallpapers]]
config = "tux"                              # configs/tux.toml (or a path relative to the recipe)
layouts = ["default", "bare-left"]          # files in layouts/; "default" = none

[[wallpapers]]                              # a variant of the same wallpaper: it needs its own name
config = "tux"
name = "tux-ice"
circles = 60
colors = { accent = "#7FD4FF" }
layout = { spectrum = { enabled = false } }

[[wallpapers]]                              # a graphic without a file in configs/
graphic = "../graphics/ghost.svg"
name = "ghost"
tag = "GHOST"
language = ["pl", "en"]
```

- An entry takes `config`, `layouts` and any key of a config file, without its section. The key
  goes where it belongs: `name`, `graphic`, `circles`… to `[wallpaper]`; `language`,
  `resolutions`, `output` to `[general]`; `colors`, `layout`, `layout_ultrawide` to their own
  tables.
- Without `layouts`, an entry is made in the layouts from `layouts` in `[general]`.
- The recipe's own sections (`[general]`, `[colors]`, `[layout]`…) apply to all its wallpapers.
- Two entries that would make the same file, or an unknown key, stop the program before anything
  is generated.
- `recipes/default.toml` (used when no recipe is given) describes all the keys.
  `recipes/examples.toml` has examples.
- A wallpaper file from `configs/` can also be given instead of a recipe
  (`python3 fourier.py configs/tux.toml`): it is made on its own, in the layouts from `[general]`.

## The config files

Files override each other key by key, in this order:

```
config.toml → the recipe → configs/<wallpaper>.toml → layouts/<layout>.toml → the entry → command line
```

- **`config.toml`** holds the defaults: resolutions, languages, layouts, colours, title, number of
  circles and the layout of the modules. Its comments describe every key.
- **A wallpaper** (`configs/`) has a `[wallpaper]` table: the graphic, its name and its texts. It
  can also override anything else, e.g. `circles` in `[general]` or a colour in `[colors]`. The
  keys are described in `configs/cachyos.toml`; see also [Adding a graphic](adding-a-graphic.md).
- **A layout** (`layouts/`) usually only has `[layout]` and `[layout_ultrawide]`, but it may also
  override other sections. Any wallpaper can be combined with any layout. See [Layout](layout.md).
- Tables are merged key by key; other values (numbers, strings, lists) are replaced.
- A file can build on another one with `extends = "other.toml"`. A variant of a wallpaper can
  then change only what is different:

```toml
# configs/tux-red.toml
extends = "tux.toml"
[colors]
accent = "#FF5500"
[wallpaper]
name = "tux-red"
```

Paths are relative to the file that sets them. Unknown sections, keys and colours, and values of
the wrong kind, stop the program with a message naming the key.

## Languages

All texts are in `languages/<code>.toml`. To add a language, copy `en.toml` and translate the
values. `plural_rule` picks how the word "circle" is inflected after a number (`en`, `pl`). The
texts that belong to one graphic (its noun, the last paragraph of the theory, the credit) are in
`[wallpaper.texts.<code>]` of its config file.
