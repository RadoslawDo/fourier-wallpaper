"""Fourier series of the outline, and fitting the graphic into a box on the sheet."""
import math

import numpy as np


class Series:
    """Fourier series of the outline, plus placing the graphic (outline and small shapes) on the sheet."""

    def __init__(self, shape):
        self.shape = shape
        pts = shape.outline + [p for e in shape.extras for p in e.extent]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        self.bbox = min(xs), max(xs), min(ys), max(ys)
        self.mid = (self.bbox[0] + self.bbox[1]) / 2, (self.bbox[2] + self.bbox[3]) / 2
        self.cn = self.fourier(shape.outline)

    def fourier(self, poly_, M=2048):
        """Coefficients cₙ of a closed curve (a polygon sampled at equal arc lengths)."""
        ring = poly_ + [poly_[0]]
        seg = [math.dist(ring[i], ring[i + 1]) for i in range(len(poly_))]
        cum = np.concatenate([[0], np.cumsum(seg)])
        pts = []
        for s_ in np.linspace(0, cum[-1], M, endpoint=False):
            i = np.searchsorted(cum, s_, side="right") - 1
            f = (s_ - cum[i]) / seg[i]
            pts.append((ring[i][0] + (ring[i + 1][0] - ring[i][0]) * f, ring[i][1] + (ring[i + 1][1] - ring[i][1]) * f))
        # complex plane with the imaginary axis pointing up (SVG y flipped) – n > 0 turns counter-clockwise
        mx0, my0 = self.mid
        z = np.array([(x - mx0) - 1j * (y - my0) for x, y in pts])
        return dict(zip(np.fft.fftfreq(M, 1 / M).astype(int), np.fft.fft(z) / M))

    def recon(self, K, ts):
        return sum((self.cn[n] * np.exp(2j * np.pi * n * ts) for n in range(-K, K + 1)), np.zeros_like(ts, complex))

    def placer(self, cx, cy, w, h):
        """The graphic fitted into a w × h box centred at (cx, cy): scale, complex → sheet, graphic px → sheet."""
        BX0, BX1, BY0, BY1 = self.bbox
        mx0, my0 = self.mid
        sc = min(w / (BX1 - BX0), h / (BY1 - BY0))
        return sc, (lambda zz: (cx + sc * zz.real, cy - sc * zz.imag)), (lambda x, y: (cx + sc * (x - mx0), cy + sc * (y - my0)))
