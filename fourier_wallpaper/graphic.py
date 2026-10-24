"""Graphic → outline, inner lines and small shapes (circles, ellipses)."""
import math
import subprocess
import sys
from dataclasses import dataclass

import cv2
import numpy as np

Point = tuple[float, float]          # pixels of the raster (see raster())


@dataclass(frozen=True)
class Circle:
    """A small shape that is a circle: drawn by 1 term."""
    x: float
    y: float
    r: float

    @property
    def extent(self):            # corners of the bounding square
        return [(self.x - self.r, self.y - self.r), (self.x + self.r, self.y + self.r)]

    @property
    def size(self):              # for sorting small shapes – the radius (Curve: the area)
        return self.r


@dataclass(frozen=True)
class Curve:
    """Any other small shape: drawn as an ellipse, by 2 terms (n = 1 and n = −1)."""
    points: list[Point]

    @property
    def extent(self):
        return self.points

    @property
    def size(self):
        return cv2.contourArea(np.array(self.points, np.float32))

    @property
    def centre(self):
        return float(np.mean([p[0] for p in self.points])), float(np.mean([p[1] for p in self.points]))


@dataclass(frozen=True)
class Shape:
    """What is taken from the graphic."""
    outline: list[Point]                 # outer contour of the whole graphic (closed)
    details: list[list[Point]]           # inner lines: boundaries between colour regions (closed)
    extras: list[Circle | Curve]         # small shapes, the largest first
    inside: np.ndarray                   # 1 inside the outline (raster size)


def raster(svg, height=1600):
    """SVG → BGRA (numpy) via rsvg-convert; contour coordinates are pixels of this raster."""
    png = subprocess.run(["rsvg-convert", "-h", str(height), svg], capture_output=True, check=True).stdout
    im = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)
    if im is None:
        sys.exit(f"{svg}: rsvg-convert did not give a readable image")
    return im


def contours(mask, mode, min_area=150):
    cs, _ = cv2.findContours(mask.astype(np.uint8), mode, cv2.CHAIN_APPROX_NONE)
    return [c for c in cs if cv2.contourArea(c) > min_area]


def as_pts(c, eps=0.8):
    return [(float(p[0][0]), float(p[0][1])) for p in cv2.approxPolyDP(c, eps, True)]


def classify(c):
    """Small shape: a circle (1 term) or a curve drawn as an ellipse (2 terms)."""
    area = cv2.contourArea(c)
    _, r = cv2.minEnclosingCircle(c)
    if area / (math.pi * r * r) > 0.9:
        m = cv2.moments(c)
        return Circle(m["m10"] / m["m00"], m["m01"] / m["m00"], math.sqrt(area / math.pi))
    return Curve(as_pts(c, 0.5))


def analyze(spec):
    """The outline, inner lines and small shapes of the wallpaper's graphic (a WallpaperSpec)."""
    colors = spec.graphic_colors
    im = raster(spec.graphic)
    h, w = im.shape[:2]
    a = im[..., 3] > 128
    outer = sorted(contours(a, cv2.RETR_EXTERNAL), key=cv2.contourArea, reverse=True)
    main = outer[0]
    inside = np.zeros((h, w), np.uint8)
    cv2.drawContours(inside, [main], -1, 1, -1)
    # colours: k-means in Lab space on the pixels inside the outline, then the boundaries of each colour region
    lab = cv2.cvtColor(np.ascontiguousarray(im[..., :3]), cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    sel = np.flatnonzero((a & (inside > 0)).ravel())
    sample = lab[sel[np.random.default_rng(0).permutation(len(sel))[:200000]]]
    cv2.setRNGSeed(0)            # the same colours whichever wallpapers were generated before
    _, _, centers = cv2.kmeans(sample, colors, None,  # pyright: ignore[reportCallIssue, reportArgumentType] – None is fine
                               (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5), 3, cv2.KMEANS_PP_CENTERS)
    labels = np.argmin(((lab[:, None, :] - centers[None]) ** 2).sum(-1), 1).reshape(h, w)
    # boundaries of every colour except the most common one – otherwise both sides would draw each boundary
    details = []
    common = np.argmax(np.bincount(labels[a & (inside > 0)], minlength=colors))
    for k in range(colors):
        if k == common:
            continue
        m = ((labels == k) & a & (inside > 0)).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        details += [as_pts(c) for c in contours(m, cv2.RETR_CCOMP)]
    # small shapes: separate ones next to the outline and the ones pointed to in the config
    extras = [classify(c) for c in outer[1:] if cv2.contourArea(c) > 3e-4 * cv2.contourArea(main)]
    for e in spec.extras:
        x, y = int(e.x * w), int(e.y * h)
        m = (labels == labels[y, x]) & a
        if e.type == "circle":
            # the largest disc of this colour near the given point (the shape merges with other lines)
            r0 = int(0.04 * h)
            dist = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
            win = dist[y - r0:y + r0, x - r0:x + r0]
            yy, xx = np.unravel_index(np.argmax(win), win.shape)
            extras.append(Circle(float(x - r0 + xx), float(y - r0 + yy), float(win[yy, xx])))
        else:
            _, comp = cv2.connectedComponents(m.astype(np.uint8))
            extras.append(classify(contours(comp == comp[y, x], cv2.RETR_EXTERNAL)[0]))
    extras.sort(key=lambda e: -e.size)
    return Shape(as_pts(main), details, extras, inside)
