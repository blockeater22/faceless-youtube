"""SvgCanvas: minimal SVG primitive emitter with a hand-drawn 'boil' wobble.

Pure string building, no dependencies. The wobble is deterministic given a seed
so frames are reproducible and testable, while still giving the lively
'sketch redrawn every couple of frames' quality.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


def _rng(seed: int) -> float:
    """Deterministic pseudo-random in [-1, 1] from an integer seed."""
    x = math.sin(seed * 12.9898) * 43758.5453
    return (x - math.floor(x)) * 2.0 - 1.0


def _fmt(v: float) -> str:
    return f"{v:.2f}"


@dataclass
class SvgCanvas:
    width: int
    height: int
    elements: list[str] = field(default_factory=list)

    # -- hand-drawn helpers ---------------------------------------------- #
    def _wobble_path(self, points, amp: float, seed: int) -> str:
        """Build a smooth-ish path through points with per-vertex jitter."""
        pts = [(p.x if hasattr(p, "x") else p[0],
                p.y if hasattr(p, "y") else p[1]) for p in points]
        out = []
        k = seed * 131
        for i, (x, y) in enumerate(pts):
            jx = _rng(k + i * 7) * amp
            jy = _rng(k + i * 7 + 3) * amp
            out.append((x + jx, y + jy))
        d = f"M {_fmt(out[0][0])} {_fmt(out[0][1])}"
        for x, y in out[1:]:
            d += f" L {_fmt(x)} {_fmt(y)}"
        return d

    # -- primitives ------------------------------------------------------- #
    def stroke(self, points, color: str, width: float,
               wobble: float = 0.0, seed: int = 0, opacity: float = 1.0) -> None:
        if len(points) < 2:
            return
        # subdivide each segment once so the wobble bends lines, not just ends
        dense = []
        seq = [(p.x, p.y) if hasattr(p, "x") else p for p in points]
        for i in range(len(seq) - 1):
            a, b = seq[i], seq[i + 1]
            dense.append(a)
            dense.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
        dense.append(seq[-1])
        d = self._wobble_path(dense, wobble, seed)
        self.elements.append(
            f'<path d="{d}" fill="none" stroke="{color}" '
            f'stroke-width="{_fmt(width)}" stroke-linecap="round" '
            f'stroke-linejoin="round" opacity="{opacity:.2f}"/>')

    def circle(self, center, r: float, color: str, width: float,
               fill: str = "none", wobble: float = 0.0, seed: int = 0) -> None:
        cx = center.x if hasattr(center, "x") else center[0]
        cy = center.y if hasattr(center, "y") else center[1]
        if wobble <= 0:
            self.elements.append(
                f'<circle cx="{_fmt(cx)}" cy="{_fmt(cy)}" r="{_fmt(r)}" '
                f'fill="{fill}" stroke="{color}" stroke-width="{_fmt(width)}"/>')
            return
        # wobbled circle as a closed path of jittered points
        n = 18
        pts = [(cx + r * math.cos(2 * math.pi * i / n),
                cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        pts.append(pts[0])
        d = self._wobble_path(pts, wobble * 0.6, seed) + " Z"
        self.elements.append(
            f'<path d="{d}" fill="{fill}" stroke="{color}" '
            f'stroke-width="{_fmt(width)}" stroke-linejoin="round"/>')

    def dot(self, center, r: float, color: str) -> None:
        cx = center.x if hasattr(center, "x") else center[0]
        cy = center.y if hasattr(center, "y") else center[1]
        self.elements.append(
            f'<circle cx="{_fmt(cx)}" cy="{_fmt(cy)}" r="{_fmt(r)}" fill="{color}"/>')

    def path(self, d: str, color: str, width: float, fill: str = "none") -> None:
        self.elements.append(
            f'<path d="{d}" fill="{fill}" stroke="{color}" '
            f'stroke-width="{_fmt(width)}" stroke-linecap="round"/>')

    def quad(self, p0, ctrl, p1, color: str, width: float, fill: str = "none") -> None:
        d = (f"M {_fmt(p0[0])} {_fmt(p0[1])} "
             f"Q {_fmt(ctrl[0])} {_fmt(ctrl[1])} {_fmt(p1[0])} {_fmt(p1[1])}")
        self.path(d, color, width, fill)

    def rect(self, x, y, w, h, fill: str, opacity: float = 1.0) -> None:
        self.elements.append(
            f'<rect x="{_fmt(x)}" y="{_fmt(y)}" width="{_fmt(w)}" '
            f'height="{_fmt(h)}" fill="{fill}" opacity="{opacity:.2f}"/>')

    def text(self, x, y, s: str, size: float, color: str,
             anchor: str = "middle", weight: str = "bold") -> None:
        esc = (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        self.elements.append(
            f'<text x="{_fmt(x)}" y="{_fmt(y)}" font-size="{_fmt(size)}" '
            f'font-family="Helvetica, Arial, sans-serif" font-weight="{weight}" '
            f'fill="{color}" text-anchor="{anchor}">{esc}</text>')

    # -- grouping --------------------------------------------------------- #
    def group_open(self, transform: str = "", opacity: float = 1.0) -> None:
        attrs = ""
        if transform:
            attrs += f' transform="{transform}"'
        if opacity < 1.0:
            attrs += f' opacity="{opacity:.2f}"'
        self.elements.append(f"<g{attrs}>")

    def group_close(self) -> None:
        self.elements.append("</g>")

    # -- output ----------------------------------------------------------- #
    def to_svg(self, background: str = "#0e1320") -> str:
        body = "\n".join(self.elements)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">\n'
            f'<rect width="100%" height="100%" fill="{background}"/>\n'
            f"{body}\n</svg>")
