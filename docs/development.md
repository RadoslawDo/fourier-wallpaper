# Development

## Files

| File | Contents |
|---|---|
| `fourier.py` | starts the program |
| `CHANGELOG.md` | the versions; the number is `__version__` in `fourier_wallpaper/__init__.py` |
| `fourier_wallpaper/` | the program: `cli.py` (command line), `config.py` (loading and merging the TOML files), `recipe.py` (recipes → jobs), `graphic.py` (SVG → outlines and small shapes), `series.py` (Fourier series), `layout.py` (module boxes), `canvas.py` (cairo drawing helpers), `render.py` (drawing one wallpaper and generating the files), `texts.py`, `tables.py` (TOML values for the type checker) |
| `fourier_wallpaper/modules/` | one file per module (`grid.py`, `drawing.py`, `theory.py`…), each a `Module` subclass listed in `modules/__init__.py`, declaring its own layout keys in `options` |
| `tests/` | the golden-image test with its reference images, the recipe tests and the output-format tests |
| `config.toml` | the defaults: resolutions, languages, layouts to make, colours, title, number of circles, layout of the modules |
| `recipes/<name>.toml` | what to make in one run: `default` (used without a recipe; describes the keys), `template` (every option, commented, for a new wallpaper), `examples`, `example-*`, `github-examples` (the README previews) |
| `configs/<name>.toml` | one wallpaper each: the graphic, its texts and anything it overrides (keys described in `cachyos.toml`) |
| `layouts/<name>.toml` | layouts of the modules (see [Layout](layout.md#layout-files)) |
| `languages/<code>.toml` | all texts (see [Configuration](configuration.md#languages)) |
| `graphics/*.svg` | source graphics, with their licences in `graphics/LICENSES.md` |
| `docs/` | this documentation |

A new module is a `Module` subclass in its own file in `modules/`, added to `MODULES` in
`modules/__init__.py` (the list also sets the drawing order).

## Tests

```sh
.venv/bin/pip install -r requirements-dev.txt     # pytest
.venv/bin/python -m pytest -q
```

`tests/test_golden.py` generates every wallpaper in `configs/` in every layout in `layouts/` (and
the default one) at 640×400 (16:10), 640×360 (16:9) and 860×360 (21:9). It compares each image pixel
for pixel with the reference in `tests/golden/`. The program is run through its command line (with a
recipe the test writes), so the test keeps working when the code is reorganised.
The example recipes (`recipes/example-*.toml`) are compared the same way.
`tests/test_recipe.py` checks that mistakes in a recipe stop the program with a message.
`tests/test_formats.py` checks that a lossless WebP has the pixels of the PNG and that the SVG,
drawn by `rsvg-convert`, looks like it.

After a change that is meant to alter the wallpapers, or after adding a wallpaper or a layout, look
at the new images and accept them (and remake the README previews in `docs/images/` with
`python3 fourier.py github-examples`):

```sh
.venv/bin/python -m pytest -q --update-golden
```

The references also depend on the fonts and on the cairo, librsvg and OpenCV builds, so they may
need updating after a system update. At this small size, changes below about a tenth of a pixel
can go unnoticed.

## Type checking and lint

The code is fully type-annotated and checked with basedpyright in strict mode, and with ruff:

```sh
uvx basedpyright
uvx ruff check .
```

`pyrightconfig.json` points basedpyright to the virtual environment in `.venv`, so editors that use
it (e.g. Zed) see the installed packages and report the same errors.
