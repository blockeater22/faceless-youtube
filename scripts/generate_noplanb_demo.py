#!/usr/bin/env python3
"""Generate a kinetic-typography + scenery demo in the raw-motivation /
no-backup-plan niche (the format @MrNoPlanA and similar faceless mindset
channels run: blunt declarative lines, dark intense palette, no fluff).
Structured against the same retention rulesets as the Zeigarnik demo:

  - 1of10.com "first 30 seconds" hook framework:
      0-5s   shock/blunt statement
      5-15s  promise/reframe
      15-30s stakes / the raw truth
  - uppbeat.io pattern-interrupt rule: switch from flat icons into the
      richer door/desk scenery composition partway through (scene 04).

Run:    python scripts/generate_noplanb_demo.py
Render: python -m faceless build stories/no_plan_b.json --formats 9:16
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "stories"

PALETTE = ["#ff5d5d", "#ffb454", "#f2ede1", "#23b26d", "#a463f2"]

STYLE = {
    "background": "#0e1320",
    "ink": "#f2ede1",
    "accent": "#ff5d5d",
    "muted": "#6f7791",
    "palette": PALETTE,
    "fps": 30,
    "grain": 0.05,
    "vignette": 0.55,
    "caption": {"mode": "kinetic", "size": 0.1, "y": 0.46, "max_chars": 16},
}
VOICE = {"backend": "kokoro", "voice": "am_liam", "polish": True, "gap": 0.28}


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
    # 0-5s: blunt statement grab - no warmup, straight to the claim.
    scene("01_hook", "You don't have a Plan B. Good.",
          [icon_prop("warning", [0.5, 0.22], 0.16, "#ff5d5d")], min_dur=3.2),
    # 5-15s: promise/reframe - turn the scary fact into the point.
    scene("02_reframe", "That's not reckless. That's the only way anything real gets built.",
          [icon_prop("brain", [0.5, 0.22], 0.16, "#ffb454")], min_dur=3.8),
    # 15-30s: the raw truth - name what a backup plan actually costs you.
    scene("03_truth", "A backup plan is just a pre-approved excuse to quit early.",
          [icon_prop("arrow_down", [0.5, 0.22], 0.16, "#a463f2")], min_dur=3.8),
    # Pattern interrupt: flat icons -> a desk/door scene staging the "burn it" beat.
    scene("04_burn", "Burn the exit. Leave yourself one door, and walk through it.",
          [obj_prop("table", [0.5, 0.28], 0.44), obj_prop("books", [0.3, 0.18], 0.26, t0=0.1),
           obj_prop("door", [0.7, 0.16], 0.32, t0=0.15)], min_dur=4.0),
    # Payoff: the bet-on-yourself CTA.
    scene("05_cta", "No Plan A. No Plan B. Just you, betting on you.",
          [icon_prop("check", [0.5, 0.22], 0.16, "#23b26d")], min_dur=3.8),
]

SCRIPT = {
    "title": "No Plan B - Bet On Yourself",
    "handle": "@Inklings1",
    "style": STYLE,
    "voice": VOICE,
    "scenes": SCENES,
    "meta": {"format": "kinetic-typography+scenery", "topic": "no-backup-plan-motivation"},
}

if __name__ == "__main__":
    out = OUT / "no_plan_b.json"
    out.write_text(json.dumps(SCRIPT, indent=2))
    print(f"wrote {out}")
