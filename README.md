# fourier-wallpaper

This program makes wallpapers. In each one, epicycles (a Fourier series) draw the outline of an
SVG graphic on a technical-drawing sheet. Around the drawing are:

- the theory,
- a square-wave example with the Gibbs phenomenon,
- the |cₙ| spectrum of the outline,
- reconstructions with a growing number of circles.

Texts come from language files. English and Polish are included.

## Usage

```sh
python3 fourier.py                        # every wallpaper in configs/, in the layouts from config.toml
python3 fourier.py -c tux -l en           # one wallpaper (configs/tux.toml), in English
python3 fourier.py -L minimal -L row      # every wallpaper in two layouts (layouts/*.toml)
python3 fourier.py -c tux -L default -L minimal     # "default" = no layout file
python3 fourier.py -c ~/my.toml           # any file (-c and -L take paths too)
python3 fourier.py -r 2560x1440           # another resolution (-r can be repeated)
python3 fourier.py -g drawing.svg -t "MY // WALLPAPER" --color accent=#FF5500
python3 fourier.py --hide spectrum --hide square    # without some modules
python3 fourier.py --help
```

Output files are named `fourier-<name>[-<layout>]-<language>_<width>x<height>.png`. The layout is left
out of the name for `default`. They go to the directory set by `output`. `{resolution}` in that path is
replaced by e.g. `3440x1440`, so each resolution gets its own folder. A slideshow can then use one
folder per monitor.

## Configuration

`config.toml` holds the defaults. Other files override them key by key, in this order:

```
config.toml  →  configs/<wallpaper>.toml (-c)  →  layouts/<layout>.toml (-L)  →  command line
```

- **A wallpaper** (`configs/`) has a `[wallpaper]` table: the graphic, its name and its texts. It
  can also override anything else, e.g. `circles` in `[general]` or a colour in `[colors]`.
- **A layout** (`layouts/`) usually only has `[layout]` and `[layout_ultrawide]`, but it may also
  override other sections. Any wallpaper can be combined with any layout.
- Which layouts are made without `-L`: `layouts = ["default", "minimal"]` in `[general]`.
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

Paths are relative to the file that sets them.

Requirements: Python 3.11+ (tomllib), pycairo, opencv-python, numpy, Pillow and `rsvg-convert`
(librsvg). To install the Python packages in a virtual environment:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # or: uv venv && uv pip install -r requirements.txt
.venv/bin/python fourier.py
```

Building pycairo needs the cairo headers (on Arch they come with the `cairo` package).

## Files

| File | Contents |
|---|---|
| `fourier.py` | the program |
| `config.toml` | the defaults: resolutions, languages, layouts to make, colours, title, number of circles, layout of the modules |
| `configs/<name>.toml` | one wallpaper each: the graphic, its texts and anything it overrides (keys described in `cachyos.toml`) |
| `layouts/<name>.toml` | layouts of the modules: `minimal` (only the drawing and the title block), `bare`, `bare-left`, `bare-right` (only the drawing, no texts – in the middle, at the left or right edge), `row` (reconstructions in a row at the bottom), `reconstruction-grid` (the whole screen: 20 reconstructions in a grid) |
| `languages/<code>.toml` | all texts. To add a language, copy `en.toml` and translate the values. `plural_rule` picks how the word "circle" is inflected after a number (`en`, `pl`) |
| `graphics/*.svg` | source graphics |

## Layout

The wallpaper is made of modules: `grid`, `drawing` (the epicycles), `theory`, `square` (the
square-wave example), `spectrum`, `reconstruction` and `title` (the title block). Each one has a
table in `[layout]` (in `config.toml`, a wallpaper or a layout file):

```toml
[layout]
spectrum       = { enabled = false }                          # not drawn
reconstruction = { x = -60, y = 78, w = 500, h = 1130 }
title          = { x = -60, y = -40, w = 420, h = 96, scale = 1.2 }
```

- `x`, `y` are the top-left corner and `w`, `h` the size. A number is pixels on a 1440 px high
  screen; on other screens it is scaled with the height. `"N%"` is a percent of the screen width
  (`x`, `w`) or height (`y`, `h`).
- A negative `x` or `y` measures from the right or bottom edge of the screen to the right or
  bottom edge of the module. A negative `w` or `h` is the screen width or height minus that much
  (`w = -120` is the full width less a 60 px margin on each side).
- `scale` makes the text and lines inside the module larger or smaller.
- Drawing only:
  - `labels = false` leaves out c₀, c₁… and the label at the small shapes.
  - `align = "left"` or `"right"` pushes the graphic to that edge of its box (default `"center"`).
- Reconstruction only:
  - `direction = "row"` puts the frames side by side.
  - `columns = 5` puts them in a grid with that many columns.
  - `empty = [0, 1]` leaves those grid cells empty, e.g. for a desktop widget. Cells are numbered
    row by row from 0.
- `grid` only has `enabled`. `theory` has no `h`, because the text sets its height.

`[layout_ultrawide]` is used on top of `[layout]` when the screen is more than twice as wide as it
is high. Each file applies its `[layout]` and then its `[layout_ultrawide]`, so a layout file that
only has `[layout]` still beats the `[layout_ultrawide]` from `config.toml`.
`--hide MODULE` and `--show MODULE` turn modules off and on from the command line.

## Adding a graphic

1. **Prepare the SVG** and put it in `graphics/`.
   - The background must be **transparent**. The outline is found from the opaque pixels, so a
     background rectangle would make the outline a rectangle.
   - The outline is the outer contour of everything opaque, so the graphic should be one main
     shape. Separate small parts next to it (like the dots of a logo) are fine: each is drawn as a
     circle or an ellipse. Other separate parts, such as text, would also become ellipses, so
     remove them.
   - Colours matter only for the inner lines: they are the boundaries between regions of
     different colour.

2. **Try it quickly** with the default settings, without writing any config:

   ```sh
   python3 fourier.py -g graphics/ghost.svg -r 1920x1200 -l en -o /tmp/fourier-test
   ```

3. **Create `configs/<name>.toml`**. `name`, `graphic` and `tag` are required, everything else is
   optional:

   ```toml
   # configs/ghost.toml
   [wallpaper]
   name = "ghost"                       # in the file name: fourier-ghost-en_1920x1200.png
   graphic = "../graphics/ghost.svg"    # relative to this file
   tag = "GHOST"                        # on the title block
   graphic_colors = 2
   extras = [{ x = 0.35, y = 0.4167, type = "shape" }, { x = 0.65, y = 0.4167, type = "shape" }]

   [wallpaper.texts.en]
   noun = "ghost"                       # "The outline of the ghost is a closed curve…"
   closing = "…"                        # last paragraph of the theory
   spectrum = "…"                       # note under the spectrum header
   author = "Ghost: Jane Doe, CC BY 4.0"   # credit above the title block

   [wallpaper.texts.pl]
   noun = "ducha"                       # in Polish in the genitive case

   [general]                            # anything from config.toml can be overridden, e.g.
   circles = 80
   reconstructions = [1, 4, 12, 40]
   ```

   The keys are described in `configs/cachyos.toml`, and `configs/tux.toml` and
   `configs/gnu.toml` are complete examples.

4. **Tune it** while checking the result with `python3 fourier.py -c ghost -r 1920x1200 -l en -o /tmp/fourier-test`:
   - **Inner lines:** too many or noisy → lower `graphic_colors`. Some missing → raise it.
   - **Jagged shapes** (horns, beards, sharp corners) need more circles, e.g. `circles = 150`
     and larger N in `reconstructions` (see `gnu.toml`).
   - **Small shapes inside the outline** (eyes, pupils) are not found by themselves. Point to
     each one in `extras`, otherwise it shows up only as a faint inner line. `x`, `y` are the
     position of the shape's centre as a fraction of the **whole SVG canvas** (its `viewBox`),
     not of the shape. For a circle at (70, 100) on a 200 × 240 canvas: `x = 0.35`,
     `y = 0.4167`. To read positions from pixels, render the SVG with
     `rsvg-convert -h 1000 graphics/ghost.svg > /tmp/ghost.png` and divide the pixel
     coordinates by the image width and height.
   - `type = "shape"` takes the whole single-colour shape at that point. Use `type = "circle"`
     when the shape merges with other lines; it takes the largest disc of that colour near the
     point.

5. **Generate it.** A file in `configs/` is included when you run `python3 fourier.py` with no
   `-c`. It can be combined with any layout: `python3 fourier.py -c ghost -L bare`.

6. **Record the licence.** Add the source and licence of the graphic to
   [graphics/LICENSES.md](graphics/LICENSES.md) and to the table at the end of this file. If the
   licence asks for credit, put it in `author`.

## How the graphic is read

- **Outline:** the outer contour of the whole graphic. A chain of 2K+1 circles draws it (`circles` = K).
- **Inner lines:** the boundaries between regions of different colour. Colours are found by
  k-means; `graphic_colors` is how many colours to split the graphic into.
- **Small shapes next to the outline** (e.g. the dots of a logo) are found automatically.
- **Small shapes inside** (e.g. pupils) must be pointed to in `extras`. Give each position as a
  fraction of the width and height of the whole SVG canvas.
  - A circle is drawn by 1 term, an ellipse by 2 (n = 1 and n = −1).
  - `type = "circle"` finds the largest disc of that colour near the point. Use it when the shape
    merges with other lines.

## Tests

```sh
.venv/bin/pip install -r requirements-dev.txt     # pytest
.venv/bin/python -m pytest -q
```

`tests/test_golden.py` generates every wallpaper in `configs/` in every layout in `layouts/` (and
the default one) at 640×400 (16:10), 640×360 (16:9) and 860×360 (21:9). It compares each image pixel
for pixel with the reference in `tests/golden/`. The program is run through its command line, so the
test keeps working when the code is reorganised.

After a change that is meant to alter the wallpapers, or after adding a wallpaper or a layout, look
at the new images and accept them:

```sh
.venv/bin/python -m pytest -q --update-golden
```

The references also depend on the fonts and on the cairo, librsvg and OpenCV builds, so they may
need updating after a system update. At this small size, changes below about a tenth of a pixel
can go unnoticed.

## Licence

The code and the configuration and language files are under the [MIT licence](LICENSE).

The graphics in `graphics/` keep their own licences. See [graphics/LICENSES.md](graphics/LICENSES.md):

| Graphic | Licence |
|---|---|
| `heckert_gnu.svg` | GNU head by Etienne Suvasa, vector version by Aurelio A. Heckert. Free Art License (also CC BY-SA 2.0 / GPLv3+) |
| `tux.svg` | Tux by Larry Ewing and The GIMP, from the Inkscape package. Free to use with credit to the authors |
| `cachyos.svg` | CachyOS logo from `cachyos-settings` (GPL-1.0-only). Also a CachyOS trademark |
