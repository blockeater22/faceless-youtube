#!/usr/bin/env python3
"""Generate 5 kinetic-typography + icon/scenery Shorts on evergreen, highly
shareable psychology effects - the niche that consistently overperforms for
faceless channels because the "aha, that's literally me" reaction drives
comments + shares, and the underlying psychology doesn't go stale.

Each follows the same retention structure as scripts/generate_zeigarnik_demo.py:
  - 1of10.com hook framework: 0-5s shock/question, 5-15s promise, 15-30s
    stakes/name-the-effect (naming it IS the open loop/payoff).
  - uppbeat.io pattern-interrupt rule: one scene switches from a flat icon
    into a richer scenery composition partway through.

Run:    python scripts/generate_psych_shorts_batch.py
Render: python -m faceless build stories/<name>.json --formats 9:16
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "stories"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from direction import infer_face  # noqa: E402

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


# A small expressive "narrator" that reacts to each line, so these kinetic-text
# Shorts feel like someone is telling the story rather than just floating words.
NARR_POS = [0.26, 0.83]
NARR_POSES = ["point_up", "reach", "think", "shrug", "wave"]
_SCENE_K = [0]


def narrator(narration, k, mood="think"):
    pose = NARR_POSES[k % len(NARR_POSES)]
    face = infer_face(narration, default=mood)

    def kf(t, scale, alpha, ease=None):
        d = {"t": round(t, 3), "pos": NARR_POS, "pose": pose, "scale": scale, "alpha": alpha}
        if ease:
            d["ease"] = ease
        return d

    return {"type": "figure", "id": "narrator", "color": "ink", "face": face,
            "keys": [kf(0, 0.0, 0), kf(0.18, 0.22, 1, "pop"), kf(1.0, 0.22, 1)]}


def _mood_for(sid):
    if "hook" in sid:
        return "surprised"
    if "cta" in sid:
        return "happy"
    return "think"


def scene(sid, narration, props=None, min_dur=3.2):
    k = _SCENE_K[0]
    _SCENE_K[0] += 1
    return {"id": sid, "narration": narration, "min_dur": min_dur,
            "props": props or [], "actors": [narrator(narration, k, _mood_for(sid))]}


def build(slug, title, scenes, topic):
    return {
        "title": title,
        "handle": "@Inklings1",
        "style": STYLE,
        "voice": VOICE,
        "scenes": scenes,
        "meta": {"format": "kinetic-typography+scenery", "topic": topic},
    }, slug


VIDEOS = [
    build(
        "baader_meinhof",
        "Why You See It Everywhere Once You Learn About It (Baader-Meinhof Effect)",
        [
            scene("01_hook", "Ever learn a new word, then suddenly hear it everywhere?",
                  [icon_prop("chat", [0.5, 0.22], 0.16, "#1f9bff")], min_dur=3.4),
            scene("02_promise", "That's not a coincidence. Your brain is doing it on purpose.",
                  [icon_prop("brain", [0.5, 0.22], 0.16, "#ff5d5d")], min_dur=3.6),
            scene("03_name", "Psychologists call it the Baader-Meinhof phenomenon.",
                  [icon_prop("lightbulb", [0.5, 0.22], 0.16, "#ffb454")], min_dur=3.8),
            scene("04_explain", "The moment something feels new, your brain starts a silent search for it.",
                  [obj_prop("table", [0.5, 0.28], 0.44), obj_prop("books", [0.32, 0.18], 0.28, t0=0.1),
                   obj_prop("laptop", [0.66, 0.18], 0.28, t0=0.15)], min_dur=4.0),
            scene("05_cta", "Notice one thing right now. Watch it start showing up everywhere.",
                  [icon_prop("check", [0.5, 0.22], 0.16, "#23b26d")], min_dur=3.8),
        ],
        "baader-meinhof-effect",
    ),
    build(
        "ikea_effect",
        "Why You Love the Wobbly Shelf You Built More Than a Perfect One (IKEA Effect)",
        [
            scene("01_hook", "You love that wobbly shelf you built more than a perfect one from the store.",
                  [icon_prop("star", [0.5, 0.22], 0.16, "#ffb454")], min_dur=3.6),
            scene("02_promise", "That's not nostalgia. It's a glitch in how your brain values effort.",
                  [icon_prop("brain", [0.5, 0.22], 0.16, "#1f9bff")], min_dur=3.8),
            scene("03_name", "Psychologists call it the IKEA Effect.",
                  [icon_prop("lightbulb", [0.5, 0.22], 0.16, "#ffb454")], min_dur=3.4),
            scene("04_explain", "The moment your hands build something, your brain quietly inflates its worth.",
                  [obj_prop("table", [0.5, 0.28], 0.44), obj_prop("laptop", [0.32, 0.18], 0.28, t0=0.1),
                   obj_prop("books", [0.66, 0.18], 0.28, t0=0.15)], min_dur=4.0),
            scene("05_cta", "Build one small thing today. Your brain will pay you back in pride.",
                  [icon_prop("check", [0.5, 0.22], 0.16, "#23b26d")], min_dur=3.8),
        ],
        "ikea-effect",
    ),
    build(
        "spotlight_effect",
        "Nobody Noticed What You Think They Noticed (Spotlight Effect)",
        [
            scene("01_hook", "Think everyone noticed that thing you said? They didn't.",
                  [icon_prop("warning", [0.5, 0.22], 0.16, "#ff5d5d")], min_dur=3.4),
            scene("02_promise", "Your brain isn't lying to you on purpose. It's just wired to overestimate your spotlight.",
                  [icon_prop("brain", [0.5, 0.22], 0.16, "#1f9bff")], min_dur=4.0),
            scene("03_name", "Psychologists call it the Spotlight Effect.",
                  [icon_prop("lightbulb", [0.5, 0.22], 0.16, "#ffb454")], min_dur=3.6),
            scene("04_explain", "Most people are too busy starring in their own movie to notice yours.",
                  [obj_prop("armchair", [0.34, 0.28], 0.34), obj_prop("mug", [0.62, 0.24], 0.16, t0=0.1),
                   obj_prop("blanket", [0.5, 0.36], 0.3, t0=0.15)], min_dur=4.0),
            scene("05_cta", "Stop performing for an audience that isn't watching.",
                  [icon_prop("check", [0.5, 0.22], 0.16, "#23b26d")], min_dur=3.6),
        ],
        "spotlight-effect",
    ),
    build(
        "dunning_kruger",
        "Why Confident People Are Often Wrong (Dunning-Kruger Effect)",
        [
            scene("01_hook", "The less someone knows, the more confident they sound. Ever notice that?",
                  [icon_prop("warning", [0.5, 0.22], 0.16, "#ff5d5d")], min_dur=3.8),
            scene("02_promise", "It's not arrogance. It's a blind spot built into how confidence actually works.",
                  [icon_prop("brain", [0.5, 0.22], 0.16, "#1f9bff")], min_dur=4.0),
            scene("03_name", "Psychologists call it the Dunning-Kruger Effect.",
                  [icon_prop("lightbulb", [0.5, 0.22], 0.16, "#ffb454")], min_dur=3.6),
            scene("04_explain", "The more you actually learn, the more clearly you see how much you don't know.",
                  [obj_prop("table", [0.5, 0.28], 0.44), obj_prop("books", [0.32, 0.18], 0.28, t0=0.1),
                   obj_prop("laptop", [0.66, 0.18], 0.28, t0=0.15)], min_dur=4.0),
            scene("05_cta", "Stay humble. That doubt you feel means you're actually growing.",
                  [icon_prop("check", [0.5, 0.22], 0.16, "#23b26d")], min_dur=3.8),
        ],
        "dunning-kruger-effect",
    ),
    build(
        "mere_exposure",
        "Why a Song You Hated Grows On You (Mere-Exposure Effect)",
        [
            scene("01_hook", "Why does that song you hated grow on you after the tenth listen?",
                  [icon_prop("chat", [0.5, 0.22], 0.16, "#a463f2")], min_dur=3.8),
            scene("02_promise", "Your brain isn't changing its taste. It's rewarding familiarity.",
                  [icon_prop("brain", [0.5, 0.22], 0.16, "#1f9bff")], min_dur=3.6),
            scene("03_name", "Psychologists call it the Mere-Exposure Effect.",
                  [icon_prop("lightbulb", [0.5, 0.22], 0.16, "#ffb454")], min_dur=3.8),
            scene("04_explain", "The more your brain sees something, the safer it feels - and safe feels good.",
                  [obj_prop("armchair", [0.34, 0.28], 0.34), obj_prop("mug", [0.62, 0.24], 0.16, t0=0.1),
                   obj_prop("clock", [0.85, 0.16], 0.12, t0=0.2)], min_dur=4.0),
            scene("05_cta", "Show up enough times, and people start to like you too.",
                  [icon_prop("heart", [0.5, 0.22], 0.16, "#ff5d5d")], min_dur=3.8),
        ],
        "mere-exposure-effect",
    ),
]

if __name__ == "__main__":
    for script, slug in VIDEOS:
        out = OUT / f"{slug}.json"
        out.write_text(json.dumps(script, indent=2))
        print(f"wrote {out}")
