# Adding a graphic

The steps below use `graphics/ghost.svg` and `configs/ghost.toml`, which are in the repository, so
each command can be tried as it is.

1. **Prepare the SVG** and put it in `graphics/`.
   - The background must be **transparent**. The outline is found from the opaque pixels, so a
     background rectangle would make the outline a rectangle.
   - The outline is the outer contour of everything opaque, so the graphic should be one main
     shape. Separate small parts next to it (like the dots of a logo) are fine: each is drawn as a
     circle or an ellipse. Other separate parts, such as text, would also become ellipses, so
     remove them.
   - A graphic made of several large separate parts (like the six lambdas of the NixOS snowflake)
     needs `outlines = 6`: then each part has its own outline and its own chain of circles.
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
   # author = "Ghost: …, CC BY 4.0"    # credit above the title block, if the licence asks for it

   [wallpaper.texts.pl]
   noun = "ducha"                       # in Polish in the genitive case

   [general]                            # anything from config.toml can be overridden, e.g.
   circles = 80
   reconstructions = [1, 4, 12, 40]
   ```

   The keys are described in `configs/cachyos.toml`. `configs/ghost.toml` is this example in
   full, and `configs/tux.toml` and `configs/gnu.toml` are larger ones.

4. **Tune it** while checking the result with
   `python3 fourier.py configs/ghost.toml -r 1920x1200 -l en -o /tmp/fourier-test`:
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

5. **Add it to a recipe**, e.g. `recipes/default.toml`, in any layouts (see
   [Configuration](configuration.md)):

   ```toml
   [[wallpapers]]
   config = "ghost"
   layouts = ["default", "bare"]
   ```

6. **Record the licence.** Add the source and licence of the graphic to
   [graphics/LICENSES.md](../graphics/LICENSES.md) and to the table at the end of the
   [README](../README.md#licence). If the licence asks for credit, put it in `author`.

7. **Accept its golden images** (see [Development](development.md#tests)): the tests make every
   wallpaper in `configs/`, so a new one needs reference images.

## How the graphic is read

- **Outline:** the outer contour of the whole graphic. A chain of 2K+1 circles draws it (`circles` = K).
  With `outlines = N`, the N largest separate parts each have their own outline and chain. The
  spectrum shows the largest one.
- **Inner lines:** the boundaries between regions of different colour. Colours are found by
  k-means; `graphic_colors` is how many colours to split the graphic into.
- **Small shapes next to the outline** (e.g. the dots of a logo) are found automatically.
- **Small shapes inside** (e.g. pupils) must be pointed to in `extras`. Give each position as a
  fraction of the width and height of the whole SVG canvas.
  - A circle is drawn by 1 term, an ellipse by 2 (n = 1 and n = −1).
  - `type = "circle"` finds the largest disc of that colour near the point. Use it when the shape
    merges with other lines.
