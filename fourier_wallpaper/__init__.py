"""Fourier wallpaper generator: epicycles (a Fourier series) draw the outline of an SVG graphic on
a technical-drawing sheet. Around it: theory, a square-wave example with the Gibbs phenomenon,
the |cₙ| spectrum of the outline and reconstructions with a growing number of circles.

From the graphic the program takes:
  - the outline – the outer contour of the whole graphic (drawn by a chain of 2K+1 circles),
  - inner lines – boundaries between regions of different colour (k-means on colours, graphic_colors),
  - small shapes – separate ones next to the outline (e.g. logo dots) are found automatically,
    ones inside (e.g. pupils) are pointed to in the config; a circle is drawn by 1 term,
    an ellipse by 2 (n = 1 and n = −1).

Parameters: config.toml (the defaults), overridden by configs/<name>.toml (one per wallpaper) and
layouts/<name>.toml (where the modules go: theory, square wave, spectrum, reconstructions… – each can be
turned off, moved and resized); texts: languages/<code>.toml. On an ultrawide screen (width > 2 × height)
the top-left corner stays empty by default – a desktop widget sits there.

Usage:
  python3 fourier.py                          all wallpapers (every config in configs/)
  python3 fourier.py -c tux -l pl             one wallpaper (configs/tux.toml), in Polish
  python3 fourier.py -c tux -L minimal        in another layout (layouts/minimal.toml)
  python3 fourier.py -g drawing.svg -r 2560x1440 -t "MY // WALLPAPER" --color accent=#FF5500
"""
