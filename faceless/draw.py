"""Low-level sketch primitives.

A :class:`Sketcher` draws onto an RGBA layer with a deliberately imperfect,
hand-drawn line: every stroke is subdivided and its interior points are nudged
by a little noise. Re-seeding the noise a few times per second produces the
classic "boiling line" doodle wobble.
"""
from __future__ import annotations

import math
import random
from typing import Sequence

from PIL import Image, ImageDraw

Point = tuple[float, float]


class Sketcher:
    def __init__(
        self,
        size: tuple[int, int],
        ink: tuple[int, int, int],
        width: float,
        wobble: float,
        seed: int,
    ) -> None:
        self.size = size
        self.img = Image.new("RGBA", size, (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.img)
        self.ink = ink
        self.width = max(1, int(round(width)))
        self.wobble = wobble
        self._seed = seed
        self._stroke = 0
        # tip of the most recently part-revealed stroke (for a marker cursor);
        # None when the last stroke was drawn whole.
        self.last_tip: Point | None = None

    # -- internal -------------------------------------------------------- #
    def _rng(self) -> random.Random:
        """A fresh RNG per stroke, stable within a 'boil' group (the seed)."""
        self._stroke += 1
        return random.Random((self._seed * 1_000_003) ^ (self._stroke * 2_654_435_761))

    def _wobbly(self, pts: Sequence[Point], rng: random.Random, amp: float | None = None) -> list[Point]:
        """Subdivide a polyline and offset interior vertices perpendicular to
        the local direction, giving an inked, slightly shaky stroke."""
        amp = self.wobble if amp is None else amp
        if amp <= 0 or len(pts) < 2:
            return [(float(x), float(y)) for x, y in pts]
        out: list[Point] = [pts[0]]
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            dx, dy = x1 - x0, y1 - y0
            length = math.hypot(dx, dy) or 1e-6
            nx, ny = -dy / length, dx / length  # unit normal
            steps = max(2, int(length / 22))    # ~1 wobble point per 22px
            for s in range(1, steps + 1):
                f = s / steps
                px, py = x0 + dx * f, y0 + dy * f
                # taper the wobble toward the endpoints so joints stay tight
                taper = math.sin(f * math.pi) if i == 0 or i == len(pts) - 2 else 1.0
                off = rng.uniform(-amp, amp) * (0.6 + 0.4 * taper)
                out.append((px + nx * off, py + ny * off))
        return out

    @staticmethod
    def _truncate(pts: list[Point], reveal: float) -> tuple[list[Point], Point]:
        """First ``reveal`` (0..1) fraction of a polyline by arc length, plus
        the tip point where the drawing currently stops."""
        if reveal >= 1.0 or len(pts) < 2:
            return pts, pts[-1]
        if reveal <= 0.0:
            return [], pts[0]
        seg = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1)]
        total = sum(seg) or 1e-9
        target = total * reveal
        out: list[Point] = [pts[0]]
        acc = 0.0
        for i, sl in enumerate(seg):
            if acc + sl >= target:
                f = (target - acc) / (sl or 1e-9)
                tip = (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f,
                       pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f)
                out.append(tip)
                return out, tip
            acc += sl
            out.append(pts[i + 1])
        return out, pts[-1]

    # -- public primitives ---------------------------------------------- #
    def stroke(self, pts: Sequence[Point], color=None, width: float | None = None,
               amp: float | None = None, reveal: float = 1.0) -> None:
        rng = self._rng()
        w = self.width if width is None else max(1, int(round(width)))
        wob = self._wobbly(pts, rng, amp)
        if reveal < 1.0:
            wob, tip = self._truncate(wob, reveal)
            self.last_tip = tip
        else:
            self.last_tip = None
        if len(wob) < 2:
            return
        self.draw.line(wob, fill=color or self.ink, width=w, joint="curve")
        # round the caps so segments meet cleanly
        for p in (wob[0], wob[-1]):
            r = w / 2.0
            self.draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color or self.ink)

    def line(self, p0: Point, p1: Point, color=None, width: float | None = None) -> None:
        self.stroke([p0, p1], color=color, width=width)

    def circle(self, center: Point, r: float, color=None, width: float | None = None,
               fill=None, segments: int = 26, amp: float | None = None, reveal: float = 1.0) -> None:
        cx, cy = center
        start = self._rng().uniform(0, math.tau)  # vary the seam each boil
        pts = [
            (cx + r * math.cos(start + i / segments * math.tau),
             cy + r * math.sin(start + i / segments * math.tau))
            for i in range(segments + 1)
        ]
        if fill is not None and reveal >= 1.0:
            self.draw.polygon(pts, fill=fill)
        self.stroke(pts, color=color, width=width, amp=amp, reveal=reveal)

    def arc(self, center: Point, r: float, a0: float, a1: float, color=None,
            width: float | None = None, segments: int = 16, amp: float | None = None,
            reveal: float = 1.0) -> None:
        cx, cy = center
        a0, a1 = math.radians(a0), math.radians(a1)
        pts = [
            (cx + r * math.cos(a0 + (a1 - a0) * i / segments),
             cy + r * math.sin(a0 + (a1 - a0) * i / segments))
            for i in range(segments + 1)
        ]
        self.stroke(pts, color=color, width=width, amp=amp, reveal=reveal)

    def dot(self, center: Point, r: float, color=None) -> None:
        cx, cy = center
        self.draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color or self.ink)

    def composite_onto(self, base: Image.Image, alpha: float = 1.0) -> None:
        """Alpha-composite this layer onto ``base`` (RGBA), scaling opacity."""
        layer = self.img
        if alpha < 1.0:
            a = layer.getchannel("A").point(lambda v: int(v * max(0.0, min(1.0, alpha))))
            layer = layer.copy()
            layer.putalpha(a)
        base.alpha_composite(layer)
