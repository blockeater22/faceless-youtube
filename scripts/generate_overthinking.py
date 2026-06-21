#!/usr/bin/env python3
"""Generate a short long-form (2-5 min) SEO video: "How to Stop Overthinking".

Reuses the scene templates + chapter card. Run:
  python scripts/generate_overthinking.py
Render: python -m faceless build stories/longform_stop_overthinking.json --formats 16:9
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_stories import BASE_STYLE, BASE_VOICE, OUT, TEMPLATES  # noqa: E402
from generate_longform import t_chapter  # noqa: E402

TITLE = "How to Stop Overthinking (5 Tricks That Actually Work)"
SLUG = "longform_stop_overthinking"
HOOK = "Can't stop overthinking?"
MIN_DUR = 5.5

TMPL = dict(TEMPLATES)
TMPL["chapter"] = t_chapter

BEATS = [
    # ---- INTRO ----
    ("hook", "It's late, and your brain is replaying that one moment for the fiftieth time.", {"face": "sad"}),
    ("solo", "Overthinking feels productive. Like if you just think hard enough, you'll finally solve it.", {"pose": "think"}),
    ("solo", "But you're not solving anything. You're spinning. Same thought, new lap.", {"pose": "think", "face": "sad"}),
    ("solo", "Here are five ways to actually break the loop, backed by psychology, not motivation fluff.", {"poses": ["stand", "point_up"]}),

    # ---- 1 ----
    ("chapter", "One. Catch it in the act.", {"num": "1", "title": "NAME THE SPIRAL"}),
    ("solo", "Your brain can't spiral and observe itself at the same time.", {"pose": "think"}),
    ("solo", "So the moment you notice it, just say: I'm overthinking again.", {"pose": "stand"}),
    ("solo", "Don't judge yourself for it. Label it like a weather report. Ah, overthinking.", {"pose": "stand", "face": "happy"}),
    ("solo", "That tiny act hands control from your panicked brain back to your calm one.", {"poses": ["stand", "point_up"], "face": "happy"}),

    # ---- 2 ----
    ("chapter", "Two. The ten-ten-ten rule.", {"num": "2", "title": "ZOOM OUT"}),
    ("solo", "Ask yourself: will this matter in ten days? Ten months? Ten years?", {"pose": "think"}),
    ("label_above", "Almost everything we agonize over fails the ten-month test.", {"text": "10?", "face": "neutral"}),
    ("solo", "Overthinking shrinks your whole world down to one moment. This zooms the camera back out.", {"pose": "look_up"}),
    ("solo", "And if it truly does matter, good. That's your signal to act, not to spiral.", {"pose": "point_up", "face": "happy"}),

    # ---- 3 ----
    ("chapter", "Three. Move to break the loop.", {"num": "3", "title": "TAKE ONE STEP"}),
    ("solo", "Overthinking lives in your head. The fastest way out is through your body.", {"pose": "stand"}),
    ("walk", "Stand up. Walk. Do one tiny piece of the thing you're avoiding.", {"x0": 0.3, "x1": 0.7}),
    ("solo", "Wash one dish. Write one sentence. It tells your brain: we're moving now.", {"pose": "reach", "face": "happy"}),
    ("solo", "Anxiety is just energy with nowhere to go. Action finally gives it somewhere.", {"pose": "stand"}),

    # ---- 4 ----
    ("chapter", "Four. You are not your thoughts.", {"num": "4", "title": "WATCH THE CLOUDS"}),
    ("split", "A thought is not a fact. It's just a thought, passing through.", {}),
    ("solo", "Picture each worry as a cloud drifting across the sky. You are the sky, not the cloud.", {"pose": "look_up"}),
    ("solo", "Thoughts feel urgent, and they feel true. They are very often neither.", {"pose": "think", "face": "sad"}),
    ("solo", "You don't have to grab every single one. Just let it drift past.", {"pose": "stand", "face": "happy"}),

    # ---- 5 ----
    ("chapter", "Five. Set a decision deadline.", {"num": "5", "title": "DECIDE, THEN GO"}),
    ("solo", "Most overthinking is really just the fear of choosing wrong.", {"pose": "think", "face": "sad"}),
    ("two", "So give the decision a timer. Five minutes. Then commit, and move.", {"poseA": "stand", "poseB": "stand"}),
    ("solo", "You can almost always adjust later. You can't adjust a choice you never made.", {"pose": "stand"}),
    ("celebrate", "A good decision today beats a perfect one that never comes.", {}),

    # ---- OUTRO ----
    ("solo", "You can't stop thoughts from showing up. That was never the goal.", {"pose": "stand"}),
    ("solo", "The goal is to stop feeding them. Notice. Zoom out. Move. Let go. Decide.", {"poses": ["stand", "point_up"]}),
    ("stars", "Your mind is a tool. And tonight, you're the one holding it.", {}),
    ("cta", "Which trick are you trying first? Tell me below, and subscribe for more.", {}),
]


def build():
    scenes = []
    for i, beat in enumerate(BEATS):
        tmpl, text = beat[0], beat[1]
        params = beat[2] if len(beat) > 2 else {}
        actors, props = TMPL[tmpl](params or {})
        min_dur = 3.4 if tmpl == "chapter" else MIN_DUR
        scenes.append({"id": f"{i:02d}_{tmpl}", "narration": text, "min_dur": min_dur,
                       "actors": actors, "props": props})
    story = {"title": TITLE, "handle": "@Inklings1", "hook": HOOK, "hook_dur": 1.8,
             "meta": {"playlist": "3 AM Thoughts", "format": "long-form", "topic": "how to stop overthinking"},
             "style": BASE_STYLE, "voice": BASE_VOICE, "scenes": scenes}
    path = OUT / f"{SLUG}.json"
    path.write_text(json.dumps(story, indent=2))
    print(f"wrote {path}  ({len(scenes)} scenes)")
    return path


if __name__ == "__main__":
    build()
