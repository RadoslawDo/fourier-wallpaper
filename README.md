# fourier-wallpaper

This program makes wallpapers. In each one, epicycles (a Fourier series) draw the outline of an
SVG graphic on a technical-drawing sheet. Around the drawing are:

- the theory,
- a square-wave example with the Gibbs phenomenon,
- the |cₙ| spectrum of the outline,
- reconstructions with a growing number of circles.

Texts come from language files. English and Polish are included.

## Installation

Requirements: Python 3.11+ (tomllib), pycairo, opencv-python, numpy, Pillow and `rsvg-convert`
(librsvg). To install the Python packages in a virtual environment:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # or: uv venv && uv pip install -r requirements.txt
.venv/bin/python fourier.py
```

Building pycairo needs the cairo headers (on Arch they come with the `cairo` package).

With [direnv](https://direnv.net), `.envrc` turns the virtual environment on in the project folder
(once: `direnv allow`), so `python3 fourier.py` uses it.

## Usage

```sh
python3 fourier.py                        # the wallpapers of recipes/default.toml
python3 fourier.py examples               # recipes/examples.toml (a name in recipes/ or any path)
python3 fourier.py example-split          # one of the layout examples, recipes/example-*.toml
python3 fourier.py ~/my-desk.toml -w tux  # only the wallpaper named tux from that recipe
python3 fourier.py configs/tux.toml -l en # one wallpaper file on its own, in English
python3 fourier.py -r 2560x1440           # another resolution (-r can be repeated)
python3 fourier.py -f webp -f svg         # other file formats: png (default), webp, svg, pdf
python3 fourier.py -g drawing.svg -t "MY // WALLPAPER" --color accent=#FF5500
python3 fourier.py --hide spectrum --hide square    # without some modules
python3 fourier.py --help
```

The options override what the recipe says, for every wallpaper in it. They are meant for quick tries,
e.g. `-r 1280x800 -o /tmp/test` to see a recipe at a small size.

Output files are named `fourier-<name>[-<layout>]-<language>_<width>x<height>.png` (or `.webp`, `.svg`,
`.pdf`). The layout is left out of the name for `default`. They go to the directory set by `output`:
`output/<resolution>/` in the project folder (ignored by git), set in `recipes/default.toml` and, for
the other recipes, in `config.toml`. `{resolution}` in that path is replaced by e.g. `3440x1440`, so
each resolution gets its own folder. A slideshow can then use one folder per monitor.

## Your own wallpaper

`recipes/template.toml` is a template for your own wallpaper: every option is in it, explained and
switched off with `#` – remove the `#` to use one. As it is, it makes the ghost from `graphics/ghost.svg`:

```sh
python3 fourier.py template               # → output/1920x1080/fourier-my-wallpaper-en_1920x1080.png
```

To make your own, copy it in `recipes/` (the paths in it are relative to the file), change `graphic`,
`name` and `tag`, and uncomment what you want to change:

```sh
cp recipes/template.toml recipes/my-wallpaper.toml
python3 fourier.py my-wallpaper
```

How to prepare the graphic: [Adding a graphic](docs/adding-a-graphic.md).

## Documentation

- [Configuration](docs/configuration.md) – recipes, the config files and the order in which they
  override each other.
- [Layout](docs/layout.md) – the modules of the wallpaper: where they go, their options, the grid of
  reconstructions, ultrawide screens.
- [Adding a graphic](docs/adding-a-graphic.md) – step by step, with the ghost example, and how the
  program reads a graphic.
- [How to…](docs/how-to.md) – run the examples, change the resolution or the file format, add a language.
- [Development](docs/development.md) – the files of the project, the tests, type checking.

## Versions

`python3 fourier.py --version` shows the version; [CHANGELOG.md](CHANGELOG.md) lists what each one
changed. A new major version (2.0.0…) means that config files or recipes need changing – the
changelog then says how.

## Licence

The code and the configuration and language files are under the [MIT licence](LICENSE).

The graphics in `graphics/` keep their own licences. See [graphics/LICENSES.md](graphics/LICENSES.md):

| Graphic | Licence |
|---|---|
| `heckert_gnu.svg` | GNU head by Etienne Suvasa, vector version by Aurelio A. Heckert. Free Art License (also CC BY-SA 2.0 / GPLv3+) |
| `tux.svg` | Tux by Larry Ewing and The GIMP, from the Inkscape package. Free to use with credit to the authors |
| `cachyos.svg` | CachyOS logo from `cachyos-settings` (GPL-1.0-only). Also a CachyOS trademark |
| `archlinux.svg` | Arch Linux logo from Arch's `filesystem` package (0BSD), without the "TM". A trademark: non-commercial use under the Arch Linux trademark policy |
| `debian.svg` | Debian Open Use Logo © Software in the Public Interest. LGPL-3+ or CC BY-SA 3.0 |
| `gentoo.svg` | Gentoo signet © Gentoo Foundation, Lennart Andre Rolland. CC BY-SA 2.5; also a Gentoo trademark |
| `nixos.svg` | NixOS snowflake by Simon Frankau and Tim Cuthbertson. CC BY 4.0 |
| `ghost.svg` | drawn for this project as the example graphic. CC0 1.0 (public domain) |
