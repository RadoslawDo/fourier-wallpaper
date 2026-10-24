# Layout

The wallpaper is made of modules: `grid`, `drawing` (the epicycles), `theory`, `square` (the
square-wave example), `spectrum`, `reconstruction` and `title` (the title block). Each one has a
table in `[layout]` (in `config.toml`, a wallpaper, a layout file or a recipe):

```toml
[layout]
spectrum       = { enabled = false }                          # not drawn
reconstruction = { x = -60, y = 78, w = 500, h = 1130 }
title          = { x = -60, y = -40, w = 420, h = 96, scale = 1.2 }
```

`--hide MODULE` and `--show MODULE` turn modules off and on from the command line.

## Position and size

- `x`, `y` are the top-left corner and `w`, `h` the size. A number is pixels on a 1440 px high
  screen; on other screens it is scaled with the height. `"N%"` is a percent of the screen width
  (`x`, `w`) or height (`y`, `h`).
- A negative `x` or `y` measures from the right or bottom edge of the screen to the right or
  bottom edge of the module. A negative `w` or `h` is the screen width or height minus that much
  (`w = -120` is the full width less a 60 px margin on each side).
- `scale` makes the text and lines inside the module larger or smaller.
- `grid` only has `enabled`. `theory` has no `h`, because the text sets its height.
- A key a module does not have (e.g. `columns` on `theory`) or a wrong value stops the program
  with a message listing that module's keys.

## Options of single modules

- **Drawing:**
  - `labels = false` leaves out c₀, c₁… and the label at the small shapes.
  - `align = "left"` or `"right"` pushes the graphic to that edge of its box (default `"center"`).
- **Reconstruction:** there is one frame per item of `reconstructions` (in `[general]` or
  `[wallpaper]`), in a grid of cells that fills the box.
  - `columns = 5` sets how many cells a row has. There are as many rows as the frames need, so
    the grid is the same on every screen; only the size of the cells changes.
  - Without `columns` the frames are in one column, or in one row with `direction = "row"`.
  - `empty = [0, 1]` leaves those cells free, e.g. for a desktop widget; the frames take the next
    free cells in order. Cells are numbered row by row from 0, left to right: with `columns = 8`,
    cells 0–7 are the first row and 8–15 the second.

For example, 20 frames with `columns = 8` and `empty = [0, 1, 8, 9]` (from
`layouts/reconstruction-grid.toml`) make 24 cells in 3 rows, with the top-left 2 × 2 left free:

```
 0  1 |  2  3  4  5  6  7          ·    ·   N=1  N=2  N=3  N=4  N=5  N=6
 8  9 | 10 11 12 13 14 15    →     ·    ·   N=7  N=8  N=10 N=12 N=14 N=16
16 17   18 19 20 21 22 23         N=18 N=20 N=24 N=28 N=32 N=40 N=50 N=60
```

An empty cell after the last frame changes nothing. The header starts above the column of the
first frame.

## Ultrawide screens

`[layout_ultrawide]` is used on top of `[layout]` when the screen is more than twice as wide as it
is high. By default the top-left corner then stays empty, for a desktop widget. Each file applies
its `[layout]` and then its `[layout_ultrawide]`, so a layout file that only has `[layout]` still
beats the `[layout_ultrawide]` from `config.toml`.

## Examples

Each of these recipes makes one wallpaper with an unusual layout, written in the recipe itself, with
comments on how it is set (`python3 fourier.py example-split` and so on):

| Recipe | Layout |
|---|---|
| `recipes/example-split.toml` | the large drawing on one half, the reconstructions in a grid on the other |
| `recipes/example-theory.toml` | only the theory and the square-wave example, larger (`scale`) |
| `recipes/example-grid.toml` | only the sheet and its grid – every other module turned off |
| `recipes/example-three.toml` | three reconstructions in a row, filling the whole screen |

The layout goes into the entry (`[wallpapers.layout]`), so it wins over the layouts of
`config.toml` and of the wallpaper file. Modules that are not named keep their place from
`config.toml`, so the ones that should not be drawn are turned off one by one.

## Layout files

| File | Layout |
|---|---|
| `minimal` | only the drawing and the title block |
| `bare`, `bare-left`, `bare-right` | only the drawing, no texts – in the middle, at the left or at the right edge |
| `row` | reconstructions in a row at the bottom |
| `reconstruction-grid` | the whole screen: 20 reconstructions in a grid |
