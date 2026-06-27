#!/usr/bin/env python3
"""SOP-compliant Shorts generator - the replacement for the templated
hook/promise/name/explain/cta pattern that vidIQ flagged as content-mill.

Every topic is written directly against ``faceless.scripting_sop``'s 4-beat
formula (hook -> explain -> reframe -> cta), carries a verbatim specificity
spike, and ends on a personal question instead of a subscribe ask. Each
story's ``meta.sop`` block is what ``scripts/lint_script.py`` checks before
anything is allowed to render - run that after this, before building.

Run:    python scripts/generate_sop_shorts.py
Lint:   python scripts/lint_script.py "stories/*.json"
Render: python -m faceless build stories/<slug>.json --formats 9:16
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "stories"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from direction import infer_pose, infer_prop, make_prop  # noqa: E402
from faceless.scripting_sop import format_cta, title_why, validate_topic  # noqa: E402

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
    "draw_on": 0.9,   # whiteboard: each figure draws itself on over 0.9s
    "hook_y": 0.18,   # hook card sits near the top, clear of the character below
    "caption": {"mode": "kinetic", "size": 0.095, "y": 0.85, "max_chars": 14},
}
VOICE = {"backend": "kokoro", "voice": "am_liam", "polish": True, "gap": 0.3}

# The character is the hero now: large and centred, not a corner decoration.
# Sized/placed to occupy the central frame so the top isn't dead space.
HERO_POS = [0.5, 0.52]
HERO_SCALE = 0.46
# The hook character sits lower and smaller so it never overlaps the hook card,
# which now lives near the top (style.hook_y).
HOOK_HERO_POS = [0.5, 0.66]
HOOK_HERO_SCALE = 0.42

# Explicit face per beat so the emotional arc (jolt -> curiosity -> relief ->
# warm invite) is intentional, not inferred from narration keywords.
BEAT_FACE = {"hook": "surprised", "explain": "think", "reframe": "happy", "cta": "happy"}

# Several poses per beat so each sentence's sub-scene reads as visually NEW -
# the fix for one frozen sketch sitting on screen for 12s. The reframe poses
# open up progressively (wave -> reach -> celebrate) to build the payoff.
BEAT_POSES = {
    "hook":    ["shrug"],
    "explain": ["think", "point_l", "shrug", "reach"],
    "reframe": ["wave", "reach", "celebrate", "point_up"],
    "cta":     ["point_r"],
}


def sentences(text: str) -> list[str]:
    """Split a beat into its individual sentences (each becomes a sub-scene)."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def K(t, pos=None, scale=None, alpha=None, ease=None):
    d = {"t": round(t, 3)}
    for k, v in (("pos", pos), ("scale", scale), ("alpha", alpha), ("ease", ease)):
        if v is not None:
            d[k] = v
    return d


def icon_prop(name, pos, r, color):
    return {"type": "icon", "id": name, "name": name, "color": color, "r": r,
            "keys": [K(0, pos, 0.6, 0), K(0.16, pos, 1.08, 1, "pop"), K(0.55, pos, 1.0, 1), K(1, pos, 1.04, 1)]}


def hero(beat, pose, pos=None, scale=None):
    """The lead character for a sub-scene: explicit face (per beat) + pose.

    Full scale/alpha from t=0: the whiteboard draw-on (style.draw_on) is the
    entrance, so there's no scale-pop to fight it."""
    pos = pos or HERO_POS
    scale = scale or HERO_SCALE
    face = BEAT_FACE[beat]
    return {"type": "figure", "id": "narrator", "color": "ink", "face": face,
            "keys": [{"t": 0, "pos": pos, "pose": pose, "scale": scale, "alpha": 1},
                     {"t": 1.0, "pos": pos, "pose": pose, "scale": scale, "alpha": 1}]}


def camera(zoom_end=1.0, pan_end=(0.5, 0.5)):
    """Slow push-in over the scene, biggest on the reframe beat (the SOP's
    'pattern interrupt' device) - a no-op when zoom_end is 1.0."""
    return [{"t": 0.0, "zoom": 1.0, "pan": [0.5, 0.5]},
            {"t": 1.0, "zoom": zoom_end, "pan": list(pan_end)}]


def scene(sid, beat, narration, pose, min_dur, prop=None, cam=None, pos=None, scale=None):
    """One sub-scene: a hero character (centre stage) + at most one small
    metaphor prop set off to the upper side, so the figure stays the subject."""
    props = [prop] if prop else []
    return {"id": sid, "beat": beat, "narration": narration, "min_dur": min_dur,
            "camera": cam or [], "props": props, "actors": [hero(beat, pose, pos, scale)]}


def expand(beat, text):
    """Split a beat into one sub-scene per sentence. Each sub-scene's POSE and
    METAPHOR PROP are inferred from that sentence's own words, so the character
    acts out what's being said instead of cycling generic poses - this is what
    keeps the visuals synced to the narration and stops them repeating."""
    out = []
    palette = BEAT_POSES[beat]
    last_pose = None
    for i, sent in enumerate(sentences(text)):
        pose = infer_pose(sent, palette[i % len(palette)])
        if pose == last_pose:                # never hold the same pose twice in a row
            pose = next((p for p in palette if p != last_pose), pose)
        last_pose = pose
        prop = infer_prop(sent, i)           # colourful metaphor matched to the line
        if beat == "reframe":                # build the push-in across the payoff
            cam = camera(min(1.07 + 0.045 * i, 1.18), (0.5, 0.43))
        elif beat == "explain":              # alternate a gentle push with a hold
            cam = camera(1.06, (0.5, 0.47)) if i % 2 == 0 else camera(1.0)
        else:
            cam = camera(1.0)
        out.append(scene(f"{beat}_{i + 1}", beat, sent, pose, 2.6, prop=prop, cam=cam))
    return out


def build(t: dict) -> tuple[dict, str]:
    # No support prop on the hook: the hook card owns the top, the drawing
    # character owns the bottom - a prop up top would collide with the text.
    scenes = [
        scene("01_hook", "hook", t["hook"], "shrug", 3.4, prop=None, cam=camera(1.0),
              pos=HOOK_HERO_POS, scale=HOOK_HERO_SCALE),
    ]
    scenes += expand("explain", t["explain"])
    scenes += expand("reframe", t["reframe"])
    scenes += [
        scene("99_cta", "cta", format_cta(t["cta_question"]), "point_r", 3.6,
              prop=make_prop("icon", "chat", "#1f9bff", 0), cam=camera(1.0)),
    ]
    title = title_why(t["title_behavior"], t["title_outcome"])
    tags = list(t["keywords"]) + ["psychology", "shorts", "Inklings"]
    hashtags = ["#shorts", "#psychology", f"#{t['slug'].replace('_', '')}", "#inklings"]
    topic_sop = {"hook": t["hook"], "explain": t["explain"], "reframe": t["reframe"],
                 "cta_question": t["cta_question"], "specificity": t["specificity"]}
    errors = validate_topic({**topic_sop, "title": title})
    assert not errors, f"{t['slug']} fails SOP lint: {errors}"
    return {
        "title": title, "handle": "@Inklings1",
        # full hook (never truncated mid-word); the card wraps + auto-sizes
        "hook": t["hook"].upper().rstrip("."), "hook_dur": 1.3,
        "style": STYLE, "voice": VOICE, "scenes": scenes,
        "meta": {"format": "kinetic-typography+scenery", "topic": t["slug"],
                 "tags": tags, "hashtags": hashtags, "sop": topic_sop},
    }, t["slug"]


TOPICS = [
    dict(
        slug="imaginary_audience",
        hook="You reread that text three times before sending it.",
        hook_icon="chat", hook_color="#1f9bff",
        explain="Psychologists call it the imaginary audience effect. Your brain stages a courtroom trial for one short message. "
                "It feels like the whole room is grading your wording. Every comma feels like it carries your whole reputation.",
        explain_icon="brain", explain_color="#a463f2",
        reframe="That's not insecurity, it's evidence you care how you land. Most people are too busy rehearsing their own lines to grade yours. "
                "The audience in your head is bigger than the one in real life. Send the message and let the imaginary jury go home.",
        reframe_obj1="table", reframe_obj2="laptop", reframe_obj3="books",
        cta_question="What's the longest you've ever rehearsed a text before sending it?",
        specificity="three times",
        title_behavior="You Reread Every Text", title_outcome="Before You Send It",
        keywords=["imaginary audience effect", "social anxiety", "overthinking texts", "self compassion"],
    ),
    dict(
        slug="post_event_processing",
        hook="You win the argument hours later, doing dishes.",
        hook_icon="clock", hook_color="#2dd4bf",
        explain="Psychologists call it post-event processing. Your brain keeps replaying it to rehearse what it missed. "
                "It's trying to file the moment away so it can finally rest. Each replay is your mind hunting for a cleaner ending.",
        explain_icon="brain", explain_color="#a463f2",
        reframe="That replay isn't weakness, it's your brain finishing unfinished business. No one else is still in that kitchen with you. "
                "The conversation ended for them the second they walked away. You can let the scene close without a perfect comeback.",
        reframe_obj1="armchair", reframe_obj2="mug", reframe_obj3="blanket",
        cta_question="When did you last win an argument hours after it ended?",
        specificity="doing dishes",
        title_behavior="You Replay Arguments", title_outcome="Hours After They're Over",
        keywords=["post-event processing", "rumination", "overthinking", "self compassion"],
    ),
    dict(
        slug="surface_acting",
        hook="You say you're fine for the fourth time today.",
        hook_icon="warning", hook_color="#ffb454",
        explain="Psychologists call it surface acting. Your face performs calm while the rest of you stays in alarm. "
                "It takes real effort to look like nothing is happening. Holding that mask all day quietly drains your battery.",
        explain_icon="brain", explain_color="#a463f2",
        reframe="That's not fake, it's your nervous system protecting the room. Pretending costs energy you don't even notice spending. "
                "You're allowed to put the performance down once in a while. One honest answer feels lighter than an hour of pretending.",
        reframe_obj1="table", reframe_obj2="mug", reframe_obj3="blanket",
        cta_question="What do you really feel when you say you're fine?",
        specificity="fourth time today",
        title_behavior="You Say You're Fine", title_outcome="When You're Not",
        keywords=["surface acting", "emotional labor", "emotional suppression", "self compassion"],
    ),
]

assert len(TOPICS) == 3
assert len({t["slug"] for t in TOPICS}) == 3
VIDEOS = [build(t) for t in TOPICS]

if __name__ == "__main__":
    for script, slug in VIDEOS:
        out = OUT / f"{slug}.json"
        out.write_text(json.dumps(script, indent=2))
        print(f"wrote {out}")
