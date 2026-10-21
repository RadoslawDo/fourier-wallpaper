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
python3 fourier.py                        # all wallpapers from config.toml
python3 fourier.py -w tux -l en           # one wallpaper, in English
python3 fourier.py -r 2560x1440           # another resolution (-r can be repeated)
python3 fourier.py -g drawing.svg -t "MY // WALLPAPER" --color accent=#FF5500
python3 fourier.py --help
```

Output files are named `fourier-<name>-<language>_<width>x<height>.png`. They go to the directory set
by `output` in `config.toml`. `{resolution}` in that path is replaced by e.g. `3440x1440`, so each
resolution gets its own folder. A slideshow can then use one folder per monitor.

Requirements: Python 3.11+ (tomllib), pycairo, opencv-python, numpy, Pillow and `rsvg-convert`
(librsvg).

## Files

| File | Contents |
|---|---|
| `fourier.py` | the program |
| `config.toml` | the list of wallpapers, resolutions, language, colours, title, number of circles |
| `languages/<code>.toml` | all texts. To add a language, copy `en.toml` and translate the values. `plural_rule` picks how the word "circle" is inflected after a number (`en`, `pl`) |
| `graphics/*.svg` | source graphics |

## How the graphic is read

- **Outline:** the outer contour of the whole graphic. A chain of 2K+1 circles draws it (`circles` = K).
- **Inner lines:** the boundaries between regions of different colour. Colours are found by
  k-means; `graphic_colors` is how many colours to split the graphic into.
- **Small shapes next to the outline** (e.g. the dots of a logo) are found automatically.
- **Small shapes inside** (e.g. pupils) must be pointed to in `extras`. Give each position as a
  fraction of the graphic's width and height.
  - A circle is drawn by 1 term, an ellipse by 2 (n = 1 and n = −1).
  - `type = "circle"` finds the largest disc of that colour near the point. Use it when the shape
    merges with other lines.

## Licence

The code and the configuration and language files are under the [MIT licence](LICENSE).

The graphics in `graphics/` keep their own licences. See [graphics/LICENSES.md](graphics/LICENSES.md):

| Graphic | Licence |
|---|---|
| `heckert_gnu.svg` | GNU head by Etienne Suvasa, vector version by Aurelio A. Heckert. Free Art License (also CC BY-SA 2.0 / GPLv3+) |
| `tux.svg` | Tux by Larry Ewing and The GIMP, from the Inkscape package. Free to use with credit to the authors |
| `cachyos.svg` | CachyOS logo from `cachyos-settings` (GPL-1.0-only). Also a CachyOS trademark |
