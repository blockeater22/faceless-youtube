"""Generate channel branding (profile picture + banner) with the faceless engine.

    python branding/make_brand.py
Outputs branding/profile.png (1024x1024) and branding/banner.png (2560x1440).
Edit NAME / TAGLINE / colours below and re-run to rebrand.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from faceless.draw import Sketcher                # noqa: E402
from faceless.figures import draw_figure, get_pose  # noqa: E402
from faceless.render import _background, _font     # noqa: E402

NAME = "Inklings"
TAGLINE = "little drawings · big what-ifs"
BG = (14, 19, 32)        # #0e1320
INK = (242, 237, 225)    # #f2ede1
ACCENT = (255, 180, 84)  # #ffb454
MUTED = (111, 119, 145)  # #6f7791

OUT = Path(__file__).resolve().parent


def profile() -> None:
    """Icon-only avatar (reads at any size; YouTube crops it to a circle)."""
    n = 1024
    img = _background((n, n), BG, 0.5).copy()
    sk = Sketcher((n, n), INK, 12, 2.2, 11)
    # accent ring kept well inside the circular crop
    sk.circle((n / 2, n / 2), n * 0.42, color=ACCENT, width=14, amp=2.4)
    # a couple of idea-sparks
    for (x, y, r) in [(0.34, 0.30, 7), (0.66, 0.27, 5), (0.30, 0.62, 5)]:
        sk.dot((x * n, y * n), r, color=ACCENT)
    # the figure: mid-wonder "think" pose
    draw_figure(sk, (n * 0.5, n * 0.60), n * 0.36, get_pose("think"),
                color=INK, face="neutral")
    sk.composite_onto(img)
    # the brand's signature "?"
    d = ImageDraw.Draw(img)
    f = _font(230)
    d.text((n * 0.66, n * 0.30), "?", font=f, fill=ACCENT + (255,),
           anchor="mm", stroke_width=10, stroke_fill=(0, 0, 0, 220))
    img.convert("RGB").save(OUT / "profile.png")
    print("wrote", OUT / "profile.png")


def banner() -> None:
    """2560x1440 banner; all text lives in the device-safe centre (1546x423)."""
    w, h = 2560, 1440
    img = _background((w, h), BG, 0.6).copy()
    # faint crowd of figures behind the wordmark
    sk = Sketcher((w, h), MUTED, 9, 2.0, 7)
    crowd = [(0.12, "wave"), (0.27, "point_up"), (0.74, "celebrate"),
             (0.88, "shrug"), (0.20, "stand"), (0.82, "look_up")]
    for x, pose in crowd:
        draw_figure(sk, (x * w, h * 0.62), h * 0.26, get_pose(pose), color=MUTED)
    sk.composite_onto(img, alpha=0.5)

    d = ImageDraw.Draw(img)
    # wordmark + accent dot + underline, centred in the safe area
    fw = _font(210)
    d.text((w / 2, h * 0.44), NAME, font=fw, fill=INK + (255,), anchor="mm",
           stroke_width=6, stroke_fill=(0, 0, 0, 180))
    bbox = d.textbbox((w / 2, h * 0.44), NAME, font=fw, anchor="mm")
    d.ellipse([bbox[2] + 18, bbox[1] + 14, bbox[2] + 52, bbox[1] + 48], fill=ACCENT)  # accent dot
    su = Sketcher((w, h), ACCENT, 10, 2.2, 5)
    su.line((bbox[0], bbox[3] + 26), (bbox[2], bbox[3] + 26), color=ACCENT)
    su.composite_onto(img)
    ft = _font(66)
    d.text((w / 2, h * 0.6), TAGLINE, font=ft, fill=MUTED + (255,), anchor="mm")
    img.convert("RGB").save(OUT / "banner.png")
    print("wrote", OUT / "banner.png")


if __name__ == "__main__":
    profile()
    banner()
