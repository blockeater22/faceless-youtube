#!/usr/bin/env python3
"""Generate a kinetic-typography + scenery demo on the Zeigarnik Effect
(why unfinished tasks won't leave your head) - a currently-trending psych
topic - structured against two retention rulesets:

  - 1of10.com "first 30 seconds" hook framework:
      0-5s   shock/question grab
      5-15s  promise (what you'll get)
      15-30s stakes / open loop ("once you see it you can't unsee it")
  - uppbeat.io audience-retention rules:
      pattern interrupt every ~25-35s -> here, the scene cut from clean
      icons into the richer desk/scenery composition (scene 04) plays that
      role, plus every scene already swaps visuals (icon/object + colour).

Run:    python scripts/generate_zeigarnik_demo.py
Render: python -m faceless build stories/zeigarnik_effect.json --formats 9:16
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
    "caption": {"mode": "kinetic", "size": 0.1, "y": 0.46, "max_chars": 16},
}
VOICE = {"backend": "kokoro", "voice": "am_liam", "polish": True, "gap": 0.3}


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
    # 0-5s: shock/question grab - no setup, straight to the open loop.
    scene("01_hook", "Why can't you stop thinking about that one unfinished task?",
          [icon_prop("warning", [0.5, 0.22], 0.16, "#ff5d5d")], min_dur=3.4),
    # 5-15s: promise - what you'll get, framed as a relief/payoff.
    scene("02_promise", "It's not laziness. Your brain is doing it on purpose.",
          [icon_prop("brain", [0.5, 0.22], 0.16, "#1f9bff")], min_dur=3.6),
    # 15-30s: stakes/name-drop - the open loop gets a name, which IS the hook.
    scene("03_name", "Psychologists call it the Zeigarnik Effect.",
          [icon_prop("lightbulb", [0.5, 0.22], 0.16, "#ffb454")], min_dur=3.6),
    # Pattern interrupt: switch from flat icons to a richer scenery composition.
    scene("04_explain", "Open loops create tension your mind won't drop.",
          [obj_prop("table", [0.5, 0.28], 0.44), obj_prop("books", [0.32, 0.18], 0.28, t0=0.1),
           obj_prop("laptop", [0.66, 0.18], 0.28, t0=0.15)], min_dur=3.8),
    # Payoff: closing the loop is the actionable takeaway.
    scene("05_cta", "Close the loop. Write it down. Tell your brain it's handled.",
          [icon_prop("check", [0.5, 0.22], 0.16, "#23b26d")], min_dur=3.8),
]

SCRIPT = {
    "title": "Why Unfinished Tasks Won't Leave You Alone (Zeigarnik Effect)",
    "handle": "@Inklings1",
    "style": STYLE,
    "voice": VOICE,
    "scenes": SCENES,
    "meta": {"format": "kinetic-typography+scenery", "topic": "zeigarnik-effect"},
}

if __name__ == "__main__":
    out = OUT / "zeigarnik_effect.json"
    out.write_text(json.dumps(SCRIPT, indent=2))
    print(f"wrote {out}")
