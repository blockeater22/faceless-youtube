#!/usr/bin/env python3
"""Generate the long-form (3-4 min) 'What If...' video:
'What If You Could Hear What People Really Think of You?'

A flowing narrative (no chapter cards) built from compact narration beats,
reusing the scene templates from generate_stories.py. Run:
    python scripts/generate_hear_thoughts.py
Then render 16:9:
    python -m faceless build stories/longform_hear_thoughts.json --formats 16:9
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_stories import BASE_STYLE, BASE_VOICE, OUT, TEMPLATES  # noqa: E402

TITLE = "What If You Could Hear What People Really Think of You?"
SLUG = "longform_hear_thoughts"
HOOK = "What do they really think?"
MIN_DUR = 5.4  # per-scene floor; most scenes run longer on narration alone

# (template, narration, params?)
BEATS = [
    # ---- THE WISH ----
    ("hook", "What if, for one day, you could hear exactly what everyone really thinks of you?", {"face": "neutral"}),
    ("solo", "Every private thought. The ones they would never, ever say to your face.", {"pose": "think"}),
    ("solo", "Be honest. A part of you has always wanted to know. And a part of you is terrified to.", {"pose": "stand"}),
    ("solo", "Because somewhere deep down, you have always quietly assumed the worst.", {"pose": "stand", "face": "sad"}),
    ("walk", "So you step out into the world, and you brace yourself for the noise.", {"x0": 0.32, "x1": 0.66, "face": "sad"}),

    # ---- THE FEAR, AND THE SURPRISE ----
    ("crowd", "And the thoughts come flooding in. A hundred quiet voices, all at once.", {}),
    ("point", "You flinch, waiting for the judgment you are so certain is coming.", {"dir": "r", "face": "sad"}),
    ("two", "The coworker you're sure resents you is quietly wishing he had your calm.", {"poseA": "stand", "poseB": "think", "colorB": "muted"}),
    ("solo", "Wait. That isn't what you expected at all. Not even close.", {"pose": "stand", "face": "surprised"}),
    ("two", "The friend you snapped at last week forgot it by lunch. She's just glad you called.", {"poseA": "stand", "poseB": "wave", "colorB": "muted", "faceB": "happy"}),
    ("solo", "That clumsy thing you said in the meeting, the one you still replay at three a.m.?", {"pose": "think"}),
    ("crowd", "No one is thinking about it. No one else even remembers that it happened.", {}),

    # ---- THE FIRST TRUTH: THE SPOTLIGHT ----
    ("label_above", "People think about you far, far less than you fear that they do.", {"text": "you?", "size": 0.08, "color": "accent"}),
    ("solo", "Everyone is the nervous main character of their own private show.", {"pose": "stand"}),
    ("solo", "That harsh, crowded audience you've been performing for your entire life...", {"pose": "stand", "face": "sad"}),
    ("celebrate", "was never really watching. And something you've carried for years gets lighter.", {}),

    # ---- THE ONES WHO LOVE YOU ----
    ("solo", "Then the volume shifts, and the quieter voices start to come through.", {"pose": "look_up"}),
    ("two", "Your mother, across the city, thinking of you mid-sentence, for no reason at all.", {"poseA": "wave", "poseB": "stand", "colorB": "muted", "faceA": "happy"}),
    ("label_above", "An old friend, miles away. I hope they know I still think about them.", {"text": "♥", "size": 0.09, "color": "accent", "face": "happy"}),
    ("solo", "The people who love you think of you more, and far more gently, than you let yourself believe.", {"pose": "stand", "face": "happy"}),
    ("two", "A stranger you helped once, years ago, who has never forgotten your face.", {"poseA": "stand", "poseB": "wave", "colorB": "muted", "faceB": "happy"}),
    ("solo", "You spent so long bracing for the hate. You never once planned for this.", {"pose": "stand", "face": "happy"}),

    # ---- THE THOUGHTS THAT ACHE ----
    ("solo", "And then come the thoughts that ache.", {"pose": "stand", "face": "sad"}),
    ("two", "Someone who needed you to ask if they were okay. And you never even noticed.", {"poseA": "stand", "poseB": "stand", "colorB": "muted", "faceA": "sad"}),
    ("solo", "A quiet I miss you, from someone you slowly let drift away.", {"pose": "stand", "face": "sad"}),
    ("stars", "And the silence where certain voices used to be. The ones you can't hear anymore.", {}),
    ("solo", "You would give anything for just one more of their thoughts.", {"pose": "look_up", "face": "sad"}),

    # ---- THE TWIST: THE LOUDEST VOICE ----
    ("solo", "But the loudest voice of all isn't a stranger's. It isn't even theirs.", {"pose": "think"}),
    ("split", "It's the one that has been narrating your every flaw from the inside.", {}),
    ("solo", "The cruelest critic you will ever meet has been wearing your face the whole time.", {"pose": "stand", "face": "sad"}),

    # ---- RESOLVE ----
    ("solo", "Then the sun goes down, the voices fade, and the day is finally over.", {"pose": "stand"}),
    ("solo", "You can't really hear their thoughts. You never could. But maybe you don't need to.", {"pose": "stand"}),
    ("two", "Maybe you just stop assuming the worst, ask how they really are, and say the kind thing out loud.", {"poseA": "wave", "poseB": "wave", "faceA": "happy", "faceB": "happy"}),
    ("stars", "Because everyone around you is guessing too. Bracing themselves, exactly like you were.", {}),
    ("cta", "So whose thought would you most want to hear? Tell me below, and I'll see you in the next one.", {}),
]


def build():
    scenes = []
    for i, beat in enumerate(BEATS):
        tmpl, text = beat[0], beat[1]
        params = beat[2] if len(beat) > 2 else {}
        actors, props = TEMPLATES[tmpl](params or {})
        scenes.append({"id": f"{i:02d}_{tmpl}", "narration": text, "min_dur": MIN_DUR,
                       "actors": actors, "props": props})
    story = {"title": TITLE, "handle": "@Inklings1", "hook": HOOK, "hook_dur": 2.0,
             "meta": {"playlist": "What If…", "format": "long-form",
                      "topic": "what people really think of you"},
             "style": BASE_STYLE, "voice": BASE_VOICE, "scenes": scenes}
    path = OUT / f"{SLUG}.json"
    path.write_text(json.dumps(story, indent=2))
    print(f"wrote {path}  ({len(scenes)} scenes)")
    return path


if __name__ == "__main__":
    build()
