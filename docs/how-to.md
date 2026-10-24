# How to…

## Run the examples

The examples are recipes in `recipes/`. A recipe is given by its name (or a path):

```sh
python3 fourier.py examples          # recipes/examples.toml: variants and other layouts
python3 fourier.py example-split     # the drawing on one half, the reconstructions on the other
python3 fourier.py example-theory    # only the theory and the square wave
python3 fourier.py example-grid      # only the sheet and its grid
python3 fourier.py example-three     # three reconstructions in a row
```

They write their files to the folder from `output` in `config.toml`, next to the other wallpapers.
To look at them first, send them somewhere else and make them smaller, which is also faster:

```sh
python3 fourier.py example-split -o /tmp/fourier/{resolution} -r 1720x720 -l en
```

- `-o` sets the output folder; `{resolution}` becomes e.g. `1720x720`.
- `-r` sets the resolution, `-l` the language (both can be repeated).
- `-w NAME` makes only the wallpaper with that name, e.g.
  `python3 fourier.py examples -w tux-ice`. The names are the `name` keys in the recipe (or in the
  wallpaper files in `configs/`); a file is called `fourier-<name>[-<layout>]-<language>_<resolution>.png`.

## Change the resolution

Every wallpaper is made in every resolution of the list `resolutions`. It can be set at four
levels; the later one wins:

| Where | For |
|---|---|
| `[general]` in `config.toml` | every recipe (now `["3440x1440", "1920x1200"]`) |
| `[general]` in a recipe | every wallpaper of that recipe |
| `resolutions = […]` in a `[[wallpapers]]` entry | one wallpaper |
| `-r 2560x1440` on the command line (repeatable) | this run only |

```toml
# config.toml
[general]
resolutions = ["2560x1440", "1920x1080"]
```

- A resolution is `WIDTHxHEIGHT`, e.g. `3840x2160`.
- The layout follows the height: sizes in the layout are pixels on a 1440 px high screen and are
  scaled for other heights, so a 1080 px high wallpaper looks the same, only smaller.
- A screen more than twice as wide as it is high (e.g. 3440×1440) is "ultrawide": it also uses
  `[layout_ultrawide]` (see [Layout](layout.md#ultrawide-screens)).
- With `{resolution}` in `output` (as in `config.toml`), each resolution gets its own folder.

## Add a language

1. **Copy `languages/en.toml`** as `languages/<code>.toml`, e.g. `languages/de.toml`, and translate
   the values. Keep every key and the `{names}` in braces – the program fills them in. In formulas
   `_{…}` is a subscript and `^{…}` a superscript.
2. **Set the plural of "circle"** (the word after a number, e.g. "3 circles"):
   - `plural_rule = "en"` with `circle = ["singular", "plural"]` – one form for 1, the other for the
     rest (English, German, French…);
   - `plural_rule = "pl"` with three forms, `circle = ["okrąg", "okręgi", "okręgów"]` – for 1, for
     2–4, 22–24… (but not 12–14) and for the rest, as in Polish.

   A language with other rules (e.g. Czech, where 22 takes the third form, or Ukrainian, where 21
   takes the first one) needs one more rule in `plural()` in `fourier_wallpaper/texts.py`.
3. **Use it:** `python3 fourier.py -l de`, or add it to `language` in `[general]` of `config.toml`
   or of a recipe, e.g. `language = ["pl", "en", "de"]`.
4. **Texts of single graphics (optional).** A wallpaper file can have its own texts in each
   language in `[wallpaper.texts.<code>]`: `noun` (what the graphic is), `closing` (the last
   paragraph of the theory), `spectrum` and `author`. Without them the wallpaper uses
   `default_noun` and a closing paragraph made from `closing_*` of the language file – but texts
   in another language (e.g. a Polish `author`) are not used either, so a credit that a licence
   asks for should be translated too:

   ```toml
   # configs/tux.toml
   [wallpaper.texts.de]
   noun = "Pinguins"
   author = "Tux: Larry Ewing und The GIMP"
   ```

A language file that lacks a key stops the program with a message naming the missing keys.
