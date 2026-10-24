"""Fourier wallpaper generator: epicycles (a Fourier series) draw the outline of an SVG graphic on
a technical-drawing sheet. Around it: theory, a square-wave example with the Gibbs phenomenon,
the |cₙ| spectrum of the outline and reconstructions with a growing number of circles.

From the graphic the program takes:
  - the outline – the outer contour of the whole graphic (drawn by a chain of 2K+1 circles),
  - inner lines – boundaries between regions of different colour (k-means on colours, graphic_colors),
  - small shapes – separate ones next to the outline (e.g. logo dots) and small round holes in it are
    found automatically,
    ones inside (e.g. pupils) are pointed to in the config; a circle is drawn by 1 term,
    an ellipse by 2 (n = 1 and n = −1).

Parameters: config.toml (the defaults), overridden by a recipe (recipes/<name>.toml – which wallpapers to
make, in which layouts, languages and resolutions), configs/<name>.toml (one per wallpaper) and
layouts/<name>.toml (where the modules go: theory, square wave, spectrum, reconstructions… – each can be
turned off, moved and resized); texts: languages/<code>.toml. On an ultrawide screen (width > 2 × height)
the top-left corner stays empty by default – a desktop widget sits there.

Usage:
  python3 fourier.py                          the wallpapers of recipes/default.toml
  python3 fourier.py examples                 the wallpapers of recipes/examples.toml
  python3 fourier.py configs/tux.toml -l pl   one wallpaper, in Polish
  python3 fourier.py -g drawing.svg -r 2560x1440 -t "MY // WALLPAPER" --color accent=#FF5500
"""

# MAJOR.MINOR.PATCH (https://semver.org): MAJOR when a config file or recipe that worked before stops working,
# MINOR for new features, PATCH for fixes; every version is listed in CHANGELOG.md and tagged v<version> in git
__version__ = "1.0.0"
