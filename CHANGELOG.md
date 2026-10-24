# Changelog

Versions are numbered MAJOR.MINOR.PATCH ([semantic versioning](https://semver.org)):

- **MAJOR** – a config file or recipe that worked before has to be changed;
- **MINOR** – new features, old files keep working;
- **PATCH** – fixes.

Each version is tagged `v<version>` in git. `python3 fourier.py --version` shows the installed one.

## 1.0.0 – 2026-10-24

The first public version.

- Epicycles (a Fourier series) draw the outline of any SVG graphic on a technical-drawing sheet,
  with the theory, a square-wave example (the Gibbs phenomenon), the |cₙ| spectrum and
  reconstructions with a growing number of circles.
- Inner lines from the colours of the graphic; small shapes (dots, pupils) drawn as circles and
  ellipses; graphics of several separate parts (`outlines`).
- Recipes (`recipes/`): which wallpapers to make, in which layouts, languages, resolutions and
  formats; `template.toml` as a start for your own wallpaper, `example-*.toml` with unusual layouts.
- Modules that can be moved, resized, scaled and turned off; layout files (`layouts/`); a separate
  layout for ultrawide screens.
- Output as PNG, WebP (lossless or lossy), SVG and PDF.
- Texts in English and Polish (`languages/`).
- Graphics: Arch Linux, CachyOS, Debian, Gentoo, GNU, NixOS, Tux and the example ghost.
