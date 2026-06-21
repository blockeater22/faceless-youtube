#!/usr/bin/env python3
"""Generate a 'kinetic typography' demo story: white background, big
colourful phrase-by-phrase centre-screen text + flat icon accents - the
Apex-Psychology / Psych2Go explainer look, as an alternative to the
paper/stick-figure stories elsewhere in this repo.

Run:    python scripts/generate_kinetic_demo.py
Render: python -m faceless build stories/kinetic_dopamine_loop.json --formats 9:16
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
    "caption": {"mode": "kinetic", "size": 0.105, "y": 0.46, "max_chars": 16},
}
VOICE = {"backend": "espeak", "voice": "en-us+f3", "rate": 158, "polish": True, "gap": 0.35}


def K(t, pos=None, scale=None, alpha=None, ease=None):
    d = {"t": round(t, 3)}
    for k, v in (("pos", pos), ("scale", scale), ("alpha", alpha), ("ease", ease)):
        if v is not None:
            d[k] = v
    return d


def icon_prop(name, pos, r, color):
    return {
        "type": "icon", "id": name, "name": name, "color": color, "r": r,
        "keys": [
            K(0, pos, 0.6, 0),
            K(0.16, pos, 1.08, 1, ease="pop"),
            K(0.55, pos, 1.0, 1),
            K(1, pos, 1.04, 1),
        ],
    }


def scene(sid, narration, icon=None, min_dur=3.4):
    return {"id": sid, "narration": narration, "min_dur": min_dur, "props": [icon] if icon else []}


SCENES = [
    scene("01_hook", "Your brain is lying to you.",
          icon_prop("brain", [0.5, 0.22], 0.16, "#ff5d5d")),
    scene("02_loop", "Every scroll spikes dopamine, then crashes it.",
          icon_prop("chat", [0.5, 0.22], 0.15, "#1f9bff")),
    scene("03_cost", "That crash is why you feel drained after.",
          icon_prop("warning", [0.5, 0.22], 0.15, "#ffb454")),
    scene("04_cta", "Notice it. Name it. Take back control.",
          icon_prop("check", [0.5, 0.22], 0.16, "#23b26d"), min_dur=3.8),
]

SCRIPT = {
    "title": "Why Scrolling Drains You (Dopamine Loop)",
    "handle": "@Inklings1",
    "style": STYLE,
    "voice": VOICE,
    "scenes": SCENES,
    "meta": {"format": "kinetic-typography"},
}

if __name__ == "__main__":
    out = OUT / "kinetic_dopamine_loop.json"
    out.write_text(json.dumps(SCRIPT, indent=2))
    print(f"wrote {out}")
