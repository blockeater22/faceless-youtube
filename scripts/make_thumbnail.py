#!/usr/bin/env python3
"""Export a strong, colourful thumbnail PNG per story.

The opening hook frame *is* the thumbnail, but in the video the bold hook bars
are at full opacity only while the character is still drawing itself on - so a
plain frame grab catches either a faded card or a half-drawn figure. This
composes the ideal version directly: bold full-opacity hook bars + a complete,
expressive character, with no animation-timing compromise.

Run:    python scripts/make_thumbnail.py [slug ...]
Out:    output/<slug>_thumb.png
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from faceless import render                       # noqa: E402
from faceless.model import RESOLUTIONS, load_script  # noqa: E402

OUT = ROOT / "output"


def make_thumb(slug: str) -> Path:
    script = load_script(ROOT / "stories" / f"{slug}.json")
    script.style.draw_on = 0.0          # draw the character complete, not mid-stroke
    script.handle = ""                  # no watermark behind the title on a thumbnail
    size = RESOLUTIONS["9:16"]
    mindim = min(size)
    scene = script.scenes[0]            # the hook scene
    scene.duration = 3.0
    # Fill the frame: enlarge + raise the character so it isn't a small figure
    # marooned in white space under the title.
    for actor in scene.actors:
        for k in actor.get("keys", []):
            k["scale"] = 0.62
            k["pos"] = [0.5, 0.66]
    fps = max(1, script.style.fps)
    # a moment inside the hook card's full-opacity "hold" (past the 0.12s snap,
    # before the fade) so the bars are at full saturation.
    t = max(0.4, script.hook_dur * 0.45)
    img = render.render_frame(script, scene, t, size, mindim, int(t * fps))
    out = OUT / f"{slug}_thumb.png"
    img.convert("RGB").save(out)
    return out


if __name__ == "__main__":
    slugs = sys.argv[1:] or ["imaginary_audience", "post_event_processing", "surface_acting"]
    for s in slugs:
        print(f"thumbnail -> {make_thumb(s)}")
