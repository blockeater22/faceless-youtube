#!/usr/bin/env python3
"""Generate a kinetic-typography demo that also uses 'scenery' props (armchair,
mug, books, laptop, door, ...) to ground each line in a relatable, everyday
setting - the way illustrated explainer channels surround their character
with a couch, a laptop, a doorway, instead of a bare icon.

Run:    python scripts/generate_relatable_demo.py
Render: python -m faceless build stories/relatable_new_opportunity.json --formats 9:16
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "stories"

PALETTE = ["#ff5d5d", "#1f9bff", "#ffb454", "#23b26d", "#a463f2"]

STYLE = {
    "background": "#ffffff",
    "ink": "#15161a",
    "accent": "#ff5d5d",
    "muted": "#9aa0ab",
    "palette": PALETTE,
    "fps": 30,
    "grain": 0.0,
    "vignette": 0.0,
    "caption": {"mode": "kinetic", "size": 0.1, "y": 0.5, "max_chars": 16},
}
VOICE = {"backend": "espeak", "voice": "en-us+f3", "rate": 158, "polish": True, "gap": 0.35}


def K(t, pos=None, scale=None, alpha=None, ease=None):
    d = {"t": round(t, 3)}
    for k, v in (("pos", pos), ("scale", scale), ("alpha", alpha), ("ease", ease)):
        if v is not None:
            d[k] = v
    return d


def obj_prop(name, pos, size, color=None, t0=0.0):
    d = {
        "type": "object", "id": name, "name": name, "size": size,
        "keys": [
            K(t0, pos, 0.7, 0),
            K(t0 + 0.18, pos, 1.05, 1, ease="pop"),
            K(t0 + 0.55, pos, 1.0, 1),
            K(1, pos, 1.0, 1),
        ],
    }
    if color:
        d["color"] = color
    return d


def scene(sid, narration, props=None, min_dur=3.2):
    return {"id": sid, "narration": narration, "min_dur": min_dur, "props": props or []}


SCENES = [
    scene("01_couch", "You've been thinking about this for weeks.",
          [obj_prop("armchair", [0.32, 0.30], 0.34), obj_prop("mug", [0.62, 0.26], 0.16, t0=0.1),
           obj_prop("clock", [0.85, 0.18], 0.12, t0=0.2)]),
    scene("02_research", "All the research in the world won't decide it for you.",
          [obj_prop("table", [0.5, 0.26], 0.46), obj_prop("books", [0.32, 0.16], 0.3, t0=0.1),
           obj_prop("laptop", [0.66, 0.16], 0.3, t0=0.15)],
          min_dur=3.8),
    scene("03_door", "At some point, you just have to open the door.",
          [obj_prop("door", [0.5, 0.32], 0.28)],
          min_dur=3.6),
    scene("04_cta", "Stop overthinking it. Take the step.",
          [{
              "type": "icon", "id": "check", "name": "check", "color": "#23b26d", "r": 0.15,
              "keys": [K(0, [0.5, 0.2], 0.6, 0), K(0.16, [0.5, 0.2], 1.08, 1, ease="pop"),
                       K(0.55, [0.5, 0.2], 1.0, 1), K(1, [0.5, 0.2], 1.04, 1)],
          }],
          min_dur=3.4),
]

SCRIPT = {
    "title": "Stop Overthinking the Decision - Open the Door",
    "handle": "@Inklings1",
    "style": STYLE,
    "voice": VOICE,
    "scenes": SCENES,
    "meta": {"format": "kinetic-typography+scenery"},
}

if __name__ == "__main__":
    out = OUT / "relatable_new_opportunity.json"
    out.write_text(json.dumps(SCRIPT, indent=2))
    print(f"wrote {out}")
