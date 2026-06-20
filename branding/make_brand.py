"""Generate channel branding (profile picture + banner) with the faceless engine.

    python branding/make_brand.py
Outputs branding/profile.png (1024x1024) and branding/banner.png (2560x1440).
Edit NAME / TAGLINE / colours below and re-run to rebrand.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

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


def _mark(n: int, ring: bool, q: bool, pose: str) -> Image.Image:
    """A bold, transparent logo mark (figure [+ring] [+?]) for watermarks."""
    layer = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    sk = Sketcher((n, n), INK, int(n * 0.026), 2.6, 9)
    if ring:
        sk.circle((n / 2, n / 2), n * 0.43, color=ACCENT, width=int(n * 0.022), amp=2.6)
    draw_figure(sk, (n * 0.5, n * 0.60), n * 0.42, get_pose(pose), color=INK, face="neutral")
    sk.composite_onto(layer)
    if q:
        d = ImageDraw.Draw(layer)
        d.text((n * 0.67, n * 0.30), "?", font=_font(int(n * 0.21)),
               fill=ACCENT + (255,), anchor="mm")
    return layer


def _glow(mark: Image.Image, radius: int = 8) -> Image.Image:
    """Composite a soft dark halo behind a mark so it reads on any background."""
    n = mark.size[0]
    halo = Image.new("RGBA", (n, n), (6, 8, 14, 0))
    halo.putalpha(mark.getchannel("A").filter(ImageFilter.GaussianBlur(radius)))
    out = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    out = Image.alpha_composite(out, halo)
    out = Image.alpha_composite(out, halo)   # double the halo for contrast
    return Image.alpha_composite(out, mark)


def watermark() -> None:
    """YouTube branding/subscribe watermark - transparent PNG, square."""
    n = 800
    # badge (figure + accent ring): most legible at tiny corner size, matches pfp
    final = _glow(_mark(n, ring=True, q=False, pose="think"))
    final.save(OUT / "watermark.png")
    print("wrote", OUT / "watermark.png")


def watermark_candidates() -> None:
    n = 800
    wm = OUT / "_wm"
    wm.mkdir(exist_ok=True)
    opts = {
        "plain": dict(ring=False, q=False, pose="think"),
        "q": dict(ring=False, q=True, pose="think"),
        "badge": dict(ring=True, q=False, pose="think"),
        "badge_q": dict(ring=True, q=True, pose="think"),
        "wave": dict(ring=False, q=False, pose="wave"),
    }
    # contact sheet on a checkerboard so transparency is visible
    cell = 300
    sheet = Image.new("RGB", (cell * len(opts), cell + 30), (40, 40, 46))
    dd = ImageDraw.Draw(sheet)
    for i, (name, kw) in enumerate(opts.items()):
        m = _glow(_mark(n, **kw)).resize((cell, cell))
        # checkerboard backdrop
        for yy in range(0, cell, 30):
            for xx in range(0, cell, 30):
                if (xx // 30 + yy // 30) % 2:
                    dd.rectangle([i * cell + xx, yy, i * cell + xx + 30, yy + 30], fill=(60, 60, 68))
        sheet.paste(m, (i * cell, 0), m)
        _glow(_mark(n, **kw)).save(wm / f"{name}.png")
        dd.text((i * cell + cell // 2, cell + 14), name, font=_font(22), anchor="mm", fill=(255, 255, 255))
    sheet.save(wm / "_contact_sheet.png")
    print("wrote", wm / "_contact_sheet.png")


if __name__ == "__main__":
    profile()
    banner()
    watermark()
    watermark_candidates()
