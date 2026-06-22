#!/usr/bin/env python3
"""Long-form (5-7 min) search-driven how-to:
'How to Stop Caring What People Think'

Chaptered (6 shifts) with LARGER stick figures. Run:
    python scripts/generate_stop_caring.py
Then render 16:9:
    python -m faceless build stories/longform_stop_caring.json --formats 16:9
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_stories import BASE_STYLE, BASE_VOICE, OUT, TEMPLATES, label  # noqa: E402

TITLE = "How to Stop Caring What People Think"
SLUG = "longform_stop_caring"
HOOK = "Stop caring what they think."
MIN_DUR = 5.6
CH_DUR = 3.4
EMBIGGEN = 1.42


def t_chapter(p):
    props = [
        label("cnum", p.get("num", "1"), "accent", 0.20, [0.5, 0.37], t0=0.0),
        label("ctitle", p.get("title", ""), "ink", 0.072, [0.5, 0.56], t0=0.12),
    ]
    return ([], props)


TMPL = dict(TEMPLATES)
TMPL["chapter"] = t_chapter


def embiggen(actors, f=EMBIGGEN):
    for a in actors:
        for k in a.get("keys", []):
            if "scale" in k:
                k["scale"] = round(k["scale"] * f, 4)
    return actors


# (template, narration, params?)
BEATS = [
    # ---- INTRO ----
    ("hook", "It's two a.m., and you're replaying it again. That thing you said. The way they looked at you.", {"face": "sad"}),
    ("solo", "You've been living your whole life inside a courtroom that doesn't even exist.", {"pose": "think", "face": "sad"}),
    ("solo", "An invisible jury, judging your every move. You built it. Which means you can take it apart.", {"pose": "stand"}),
    ("solo", "So here is how to actually stop caring what people think. Real psychology, not feel-good lines.", {"poses": ["stand", "point_up"]}),
    ("solo", "One quick warning. You can't switch this off completely. And you really shouldn't want to.", {"pose": "stand"}),
    ("solo", "The goal isn't to feel nothing. It's to stop letting other people's opinions run your life.", {"pose": "stand"}),

    # ---- 1. WIRING ----
    ("chapter", "One. It's wiring, not weakness.", {"num": "1", "title": "IT'S ANCIENT WIRING"}),
    ("crowd", "For two hundred thousand years, you lived or died by the group.", {}),
    ("solo", "Back then, being cast out of the tribe wasn't embarrassing. It was a death sentence.", {"pose": "stand", "face": "sad"}),
    ("solo", "So your brain learned to treat disapproval as if it were mortal danger.", {"pose": "think"}),
    ("two", "That is why one cold look from a stranger can quietly ruin your whole afternoon.", {"poseA": "stand", "poseB": "stand", "colorB": "muted", "faceA": "sad"}),
    ("solo", "It's a hundred-thousand-year-old alarm, going off in a world that will not actually exile you.", {"pose": "stand"}),
    ("solo", "So stop being ashamed that you care. Your brain is just doing its oldest job.", {"pose": "stand", "face": "happy"}),

    # ---- 2. SPOTLIGHT ----
    ("chapter", "Two. Nobody is really watching.", {"num": "2", "title": "THE SPOTLIGHT IS OFF"}),
    ("solo", "You walk into a room, certain that everyone is studying you.", {"pose": "stand", "face": "sad"}),
    ("crowd", "They're not. Every person in that room is starring in their own anxious movie.", {}),
    ("solo", "Worried about their hair, their words, their own imaginary jury.", {"pose": "think"}),
    ("label_above", "Psychologists call it the spotlight effect. We wildly overestimate how much we're noticed.", {"text": "you?", "size": 0.08, "color": "accent"}),
    ("solo", "That thing you cringe about for years? Most people forgot it by dinner.", {"pose": "stand", "face": "happy"}),
    ("solo", "You're the main character in your story, and a background extra in everyone else's. That's freedom.", {"pose": "stand"}),

    # ---- 3. VOTES ----
    ("chapter", "Three. Not every opinion gets a vote.", {"num": "3", "title": "GIVE FEWER VOTES"}),
    ("solo", "Right now, you are handing out votes on your life to total strangers.", {"pose": "stand"}),
    ("two", "The commenter. The relative who never chased anything. The person you'll never see again.", {"poseA": "shrug", "poseB": "shrug", "colorB": "muted"}),
    ("solo", "So draw a small circle. Inside it, the few people who truly love you and want you to grow.", {"pose": "think"}),
    ("two", "Their honest feedback is gold. Protect it. Actually listen to it.", {"poseA": "stand", "poseB": "wave", "colorB": "muted", "faceA": "happy", "faceB": "happy"}),
    ("solo", "Everyone outside that circle is just weather. You don't rebuild your house for every passing cloud.", {"pose": "stand"}),
    ("solo", "Would you really take directions from someone going nowhere you'd ever want to be?", {"pose": "think"}),

    # ---- 4. THE MATH ----
    ("chapter", "Four. You can't win everyone.", {"num": "4", "title": "THE PEACH RULE"}),
    ("solo", "You could be the ripest, juiciest peach in the entire world.", {"pose": "stand"}),
    ("two", "And someone out there still just doesn't like peaches. That was never about you.", {"poseA": "stand", "poseB": "shrug", "colorB": "muted"}),
    ("label_above", "Some will like you, some won't, and most won't think about you at all.", {"text": "30%", "size": 0.07, "color": "accent"}),
    ("solo", "Here's the trap. Shrinking yourself doesn't change those numbers. It just makes you smaller.", {"pose": "stand", "face": "sad"}),
    ("solo", "So you may as well be fully yourself, and get disliked for who you actually are.", {"pose": "celebrate", "face": "happy"}),
    ("two", "Because being real is exactly what filters the world down to your actual people.", {"poseA": "wave", "poseB": "wave", "faceA": "happy", "faceB": "happy"}),

    # ---- 5. CRINGE ----
    ("chapter", "Five. Survive it on purpose.", {"num": "5", "title": "COLLECT THE EVIDENCE"}),
    ("solo", "Caring less isn't a single thought. It's a skill you build with evidence.", {"pose": "stand"}),
    ("solo", "And you gather that evidence by doing small things that risk looking a little silly.", {"pose": "stand"}),
    ("two", "Ask the question everyone's afraid to ask. Raise your hand. Wear the bold thing.", {"poseA": "point_up", "poseB": "stand", "colorB": "muted"}),
    ("walk", "Send the message. Speak up in the meeting. Let yourself be a visible beginner.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
    ("celebrate", "Each time, you feel the cringe, and then you notice something. You survived it.", {}),
    ("solo", "Do that enough, and the fear goes quiet, because you've proven the threat was never real.", {"pose": "stand", "face": "happy"}),

    # ---- 6. PERSPECTIVE ----
    ("chapter", "Six. You'll be forgotten. It's freeing.", {"num": "6", "title": "ZOOM ALL THE WAY OUT"}),
    ("solo", "Here's the one that truly sets you free. One day, all of this is forgotten.", {"pose": "stand"}),
    ("crowd", "In a hundred years, almost no one alive will even know your name.", {}),
    ("solo", "Every person whose opinion you fear will be gone. And so will their opinions.", {"pose": "stand", "face": "neutral"}),
    ("solo", "I know that sounds bleak. It's the opposite. It is permission.", {"pose": "think"}),
    ("stars", "The audience you're so afraid of is temporary. The universe is not keeping a highlight reel of your flaws.", {}),
    ("solo", "So spend your one short life on the people who matter, not the crowd that won't remember.", {"pose": "look_up", "face": "happy"}),

    # ---- OUTRO ----
    ("solo", "You won't stop caring overnight. That was never the goal.", {"pose": "stand"}),
    ("solo", "You'll just slowly stop handing your power to people who never earned it.", {"pose": "stand"}),
    ("two", "Keep the small circle of voices that love you. Let all the rest fade into background noise.", {"poseA": "stand", "poseB": "wave", "colorB": "muted", "faceB": "happy"}),
    ("solo", "Because the only opinion you are stuck living inside, every second, is your own.", {"pose": "think"}),
    ("solo", "So make that one kind. Start there, and the whole world gets a little quieter.", {"pose": "stand", "face": "happy"}),
    ("cta", "Tell me below. Whose opinion are you finally ready to stop carrying? Then set it down.", {}),
]


def build():
    scenes = []
    for i, beat in enumerate(BEATS):
        tmpl, text = beat[0], beat[1]
        params = beat[2] if len(beat) > 2 else {}
        actors, props = TMPL[tmpl](params or {})
        embiggen(actors)
        min_dur = CH_DUR if tmpl == "chapter" else MIN_DUR
        scenes.append({"id": f"{i:02d}_{tmpl}", "narration": text, "min_dur": min_dur,
                       "actors": actors, "props": props})
    story = {"title": TITLE, "handle": "@Inklings1", "hook": HOOK, "hook_dur": 2.0,
             "meta": {"playlist": "3 AM Thoughts", "format": "long-form",
                      "topic": "how to stop caring what people think"},
             "style": BASE_STYLE, "voice": BASE_VOICE, "scenes": scenes}
    path = OUT / f"{SLUG}.json"
    path.write_text(json.dumps(story, indent=2))
    chapters = [(b[2]["num"], b[2]["title"]) for b in BEATS if b[0] == "chapter"]
    print(f"wrote {path}  ({len(scenes)} scenes, {len(chapters)} chapters)")
    return path


if __name__ == "__main__":
    build()
