#!/usr/bin/env python3
"""Generate a long-form (7-8 min) chaptered video essay for Inklings.

Reuses the scene templates from generate_stories.py and adds a chapter-card
template. Run:  python scripts/generate_longform.py
Then render 16:9:  python -m faceless build stories/longform_seven_thoughts.json --formats 16:9
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_stories import BASE_STYLE, BASE_VOICE, OUT, TEMPLATES, label  # noqa: E402

TITLE = "7 Thoughts That Will Quietly Change How You See Your Life"
SLUG = "longform_seven_thoughts"
HOOK = "You are sleepwalking."


def t_chapter(p):
    """A clean chapter card: big accent number + title."""
    props = [
        label("cnum", p.get("num", "1"), "accent", 0.20, [0.5, 0.37], t0=0.0),
        label("ctitle", p.get("title", ""), "ink", 0.072, [0.5, 0.56], t0=0.12),
    ]
    return ([], props)


TMPL = dict(TEMPLATES)
TMPL["chapter"] = t_chapter

# (template, narration, params?)  — chapter cards get a short spoken line.
BEATS = [
    # ---- INTRO ----
    ("solo", "Right now, you are sitting on a rock, hurtling through space at sixty-seven thousand miles an hour.", {"pose": "look_up", "face": "surprised"}),
    ("stars", "You're breathing air made by trees, on a planet somehow placed at the exact right distance from a star.", {}),
    ("solo", "And most days, you don't notice any of it. You move through a miracle on autopilot.", {"pose": "stand", "face": "sad"}),
    ("solo", "You scroll past sunsets. You eat meals you don't taste. You keep waiting for life to start, while it's quietly happening all around you.", {"pose": "stand", "face": "sad"}),
    ("solo", "So tonight, let's wake up. Here are seven thoughts that quietly change how you see your whole life.", {"poses": ["stand", "reach"]}),

    # ---- 1. SONDER ----
    ("chapter", "One. Sonder.", {"num": "1", "title": "SONDER"}),
    ("crowd", "Picture a crowded street. Hundreds of strangers, blurring past you.", {}),
    ("point", "Your brain quietly files them all as background. Extras in your story.", {"dir": "r"}),
    ("solo", "But every one of them is the main character of a life as deep and detailed as yours.", {"pose": "stand"}),
    ("solo", "That man has a childhood bedroom he still dreams about.", {"pose": "think"}),
    ("label_above", "That woman is carrying news she hasn't found the words to tell anyone yet.", {"text": "...", "face": "sad"}),
    ("two", "Each of them has people they would die for, and fears they've never said out loud.", {"poseA": "stand", "poseB": "stand"}),
    ("solo", "The barista. The driver who cut you off. The old man on the bench. Every single face is a doorway into an entire world.", {"pose": "think"}),
    ("label_above", "There's a word for the moment you truly realize this. Sonder.", {"text": "SONDER", "size": 0.06}),
    ("crowd", "And after that, a crowd is never just a backdrop again. It's a thousand universes, walking.", {}),

    # ---- 2. THE LAST TIME ----
    ("chapter", "Two. The Last Time.", {"num": "2", "title": "THE LAST TIME"}),
    ("solo", "There was a last time your mother ever picked you up and carried you.", {"pose": "stand", "face": "sad"}),
    ("crowd", "A final evening you played outside until the streetlights flickered on.", {}),
    ("solo", "And nobody marked the moment. No music, no warning. It just quietly happened.", {"pose": "stand"}),
    ("solo", "Most of life's endings arrive in disguise, dressed as an ordinary afternoon.", {"pose": "think"}),
    ("two", "One day, you'll have a last conversation with someone you love.", {"poseA": "stand", "poseB": "stand"}),
    ("solo", "You probably won't know it's the last. That's the quiet ache of being human.", {"pose": "stand", "face": "sad"}),
    ("solo", "But hidden inside that is a gift. Because if everything gets a last time...", {"pose": "think"}),
    ("celebrate", "then nothing is ordinary. Not the boring dinner, not the traffic, not the goodbye at the door.", {}),

    # ---- 3. THE OTHER YOU ----
    ("chapter", "Three. The Other You.", {"num": "3", "title": "THE OTHER YOU"}),
    ("solo", "Every day, you make a thousand tiny choices. Left or right. Speak, or stay silent.", {"pose": "shrug"}),
    ("split", "And somewhere in the branching of all those decisions are other versions of you.", {}),
    ("two", "The you who took the other job. Who said the brave thing. Who never let that person go.", {"poseA": "stand", "poseB": "celebrate", "colorB": "muted"}),
    ("solo", "They aren't better than you. They just chose differently at one fork in the road.", {"pose": "stand"}),
    ("walk", "Somewhere, a version of you is living your backup dream at this very moment.", {"x0": 0.3, "x1": 0.7}),
    ("two", "And another you would trade everything for the ordinary life you forget to appreciate.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
    ("solo", "You can't visit them. But you can become more like the one you admire, starting with your next choice.", {"poses": ["stand", "reach"], "face": "happy"}),

    # ---- 4. FOUR THOUSAND WEEKS ----
    ("chapter", "Four. Four Thousand Weeks.", {"num": "4", "title": "4000 WEEKS"}),
    ("label_above", "If you live to eighty, you get about four thousand weeks. That's the whole thing.", {"text": "4000", "face": "neutral"}),
    ("solo", "It sounds small because it is. And you've already spent a good chunk of them.", {"pose": "stand"}),
    ("label_above", "Now picture a jar with a single marble for every weekend left with your parents.", {"text": "...", "face": "sad"}),
    ("solo", "For most adults, that jar is far emptier than they ever let themselves think.", {"pose": "think", "face": "sad"}),
    ("solo", "You'll see your parents maybe a few dozen more times. The people who raised you, countable on your fingers.", {"pose": "stand", "face": "sad"}),
    ("solo", "This isn't here to scare you. It's here to wake you up.", {"pose": "stand"}),
    ("solo", "Time isn't running out someday. It's running out right now, quietly, in the background.", {"pose": "look_up"}),
    ("solo", "So the question was never whether you have enough time. It's whether you're awake for the time you have.", {"poses": ["stand", "reach"]}),

    # ---- 5. YOU ARE STARDUST ----
    ("chapter", "Five. You Are the Universe.", {"num": "5", "title": "YOU ARE STARDUST"}),
    ("stars", "Every atom in your body was forged inside a dying star, billions of years ago.", {}),
    ("label_above", "The iron in your blood. The calcium in your bones. All of it, ancient stardust.", {"text": "*", "face": "neutral"}),
    ("solo", "Which means you are not separate from the universe. You are the universe.", {"pose": "look_up"}),
    ("stars", "You are the cosmos that somehow woke up and started asking questions about itself.", {}),
    ("solo", "The same force that lit the stars is the one reading these words, right now.", {"pose": "look_up"}),
    ("solo", "So when you look up at the night sky and feel impossibly small...", {"pose": "look_up", "face": "sad"}),
    ("stars", "remember: that sky is looking back, through your eyes.", {}),
    ("solo", "You are how the universe gets to experience a sunrise, a song, a person it loves.", {"poses": ["look_up", "reach"], "face": "happy"}),

    # ---- 6. THE DARK ----
    ("chapter", "Six. The Dark.", {"num": "6", "title": "THE DARK"}),
    ("solo", "You're not actually afraid of the dark. A dark, empty room doesn't scare you at all.", {"pose": "stand"}),
    ("two", "Put one person you trust in it, and the fear simply disappears.", {"poseA": "stand", "poseB": "wave", "faceB": "happy"}),
    ("solo", "It was never the darkness. It was being alone in it.", {"pose": "think"}),
    ("solo", "For a hundred thousand years, alone in the dark meant one thing. Danger.", {"pose": "stand", "face": "sad"}),
    ("crowd", "The ones who stayed close to the others survived. So now, so do we.", {}),
    ("two", "One familiar voice on the phone can turn the loneliest night into something survivable.", {"poseA": "stand", "poseB": "wave", "faceB": "happy"}),
    ("solo", "That loneliness you feel at three a.m. isn't a weakness in you.", {"pose": "stand", "face": "sad"}),
    ("two", "It's a million years of ancestors whispering, don't drift too far from the others.", {"poseA": "stand", "poseB": "stand"}),
    ("solo", "So when the dark feels heavy, the answer was never to be stronger alone. It was to reach for someone.", {"poses": ["stand", "reach"], "face": "happy"}),

    # ---- 7. EVERY UNLIVED LIFE ----
    ("chapter", "Seven. Every Unlived Life.", {"num": "7", "title": "THE UNLIVED"}),
    ("split", "For one moment, imagine feeling every future you will never live.", {}),
    ("crowd", "The cities you didn't move to. The person you didn't quite become.", {}),
    ("solo", "It's almost too heavy to hold. So many beautiful lives, just out of reach.", {"pose": "think", "face": "sad"}),
    ("solo", "But here is the secret hidden inside that grief.", {"pose": "stand"}),
    ("two", "If every path stayed open forever, not one of them would mean anything.", {"poseA": "stand", "poseB": "stand"}),
    ("solo", "Choosing is what turns a possibility into a life. Your life.", {"poses": ["stand", "reach"]}),
    ("stars", "Every no is the price of a real, solid yes. The unlived futures aren't losses. They're the cost of being here.", {}),

    # ---- OUTRO ----
    ("solo", "So there they are. Seven thoughts.", {"pose": "stand"}),
    ("crowd", "Everyone is real. Nothing is ordinary. You are stardust, briefly awake.", {}),
    ("solo", "Built for each other. Living one precious branch out of a billion that could have been.", {"pose": "look_up", "face": "happy"}),
    ("solo", "You can't quite unsee these now. And honestly, that's the whole point.", {"pose": "stand"}),
    ("solo", "Tomorrow, the autopilot switches back on. The trick is just to wake up a little more often than you did before.", {"pose": "stand"}),
    ("stars", "The miracle was never going to announce itself. You just have to start noticing it.", {}),
    ("cta", "If even one of these stayed with you, tell me which one in the comments. I'll see you in the next one.", {}),
]


def build():
    scenes = []
    for i, beat in enumerate(BEATS):
        tmpl, text = beat[0], beat[1]
        params = beat[2] if len(beat) > 2 else {}
        actors, props = TMPL[tmpl](params or {})
        min_dur = 3.4 if tmpl == "chapter" else 5.8
        scenes.append({"id": f"{i:02d}_{tmpl}", "narration": text, "min_dur": min_dur,
                       "actors": actors, "props": props})
    story = {"title": TITLE, "handle": "@Inklings1", "hook": HOOK, "hook_dur": 2.0,
             "meta": {"playlist": "3 AM Thoughts", "format": "long-form"},
             "style": BASE_STYLE, "voice": BASE_VOICE, "scenes": scenes}
    path = OUT / f"{SLUG}.json"
    path.write_text(json.dumps(story, indent=2))
    chapters = [(i, b[2]["num"], b[2]["title"]) for i, b in enumerate(BEATS) if b[0] == "chapter"]
    print(f"wrote {path}  ({len(scenes)} scenes, {len(chapters)} chapters)")
    return path


if __name__ == "__main__":
    build()
