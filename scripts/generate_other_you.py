#!/usr/bin/env python3
"""Long-form (5-7 min) 'The Other You' video:
'What If You Met the Person You Could Have Been?'

Flowing narrative with LARGER stick figures (embiggen pass). Run:
    python scripts/generate_other_you.py
Then render 16:9:
    python -m faceless build stories/longform_other_you.json --formats 16:9
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_stories import BASE_STYLE, BASE_VOICE, OUT, TEMPLATES  # noqa: E402

TITLE = "What If You Met the Person You Could Have Been?"
SLUG = "longform_other_you"
HOOK = "Meet who you could've been."
MIN_DUR = 5.6
EMBIGGEN = 1.42  # scale figures up ~42% so the stickman fills more of the frame


def embiggen(actors, f=EMBIGGEN):
    for a in actors:
        for k in a.get("keys", []):
            if "scale" in k:
                k["scale"] = round(k["scale"] * f, 4)
    return actors


# (template, narration, params?)
BEATS = [
    # ---- INTRO ----
    ("hook", "What if you met the person you could have been?", {"face": "neutral"}),
    ("solo", "Not a stranger. You. Same face, same start, but every chance you talked yourself out of, taken.", {"pose": "think"}),
    ("solo", "You would know him in an instant.", {"pose": "stand"}),
    ("solo", "And honestly, it would break your heart a little.", {"pose": "stand", "face": "sad"}),
    ("walk", "So picture this. One completely ordinary night, there is a knock at your door.", {"x0": 0.34, "x1": 0.62}),
    ("split", "You open it. And you are standing face to face with yourself.", {}),

    # ---- THE MEETING ----
    ("compare", "But he looks lighter. Like he sleeps well. Like he isn't carrying the weight you carry.", {"poseA": "stand", "poseB": "stand", "faceA": "sad", "faceB": "happy"}),
    ("two", "Hey, he says, in your own voice. I'm the version that didn't wait.", {"poseA": "stand", "poseB": "wave", "colorB": "muted", "faceB": "happy"}),
    ("solo", "He doesn't gloat. He just steps inside, like he has been here before.", {"pose": "stand"}),
    ("solo", "And he offers to show you the life you almost lived.", {"pose": "reach"}),
    ("walk", "So you follow yourself, down a long hallway of every choice you ever postponed.", {"x0": 0.3, "x1": 0.7}),

    # ---- WHAT HE DID ----
    ("label_above", "He sent the message you left sitting in your drafts for three whole years.", {"text": "SENT", "size": 0.06, "color": "accent"}),
    ("solo", "He started the thing before he felt ready. You are still waiting to feel ready.", {"pose": "stand"}),
    ("two", "He let people watch him be a beginner. So he actually got to become something.", {"poseA": "shrug", "poseB": "celebrate", "colorB": "muted", "faceB": "happy"}),
    ("solo", "On the hard mornings, he kept the promise to himself. That was the entire secret.", {"pose": "stand"}),
    ("solo", "Not talent. Not luck. Just a refusal to quietly break his own word.", {"pose": "think"}),
    ("celebrate", "And those tiny kept promises stacked up into a life that actually feels like his.", {}),

    # ---- THE TOUR / COMPARISON ----
    ("compare", "You walk through his days. It isn't glamorous. It's just, lived. On purpose.", {"poseA": "stand", "poseB": "stand", "faceB": "happy"}),
    ("two", "His body is strong, because he moved on the days he most wanted to quit.", {"poseA": "stand", "poseB": "celebrate", "colorB": "muted", "faceB": "happy"}),
    ("two", "His work is good, because he was willing to be bad at it first, in public.", {"poseA": "think", "poseB": "point_up", "colorB": "muted"}),
    ("two", "His friendships run deep, because he said the honest, terrifying thing out loud.", {"poseA": "stand", "poseB": "wave", "colorB": "muted", "faceA": "happy", "faceB": "happy"}),
    ("solo", "He isn't richer in money. He's richer in time he simply refused to waste.", {"pose": "stand"}),
    ("compare", "And everything he has, you can see the exact door he walked through to get it.", {"poseA": "stand", "poseB": "reach", "faceB": "happy"}),
    ("solo", "Because you stood in front of those same doors. You remember every single one.", {"pose": "think"}),
    ("solo", "You just told yourself, not yet. Maybe tomorrow. Maybe once it feels safe.", {"pose": "stand", "face": "sad"}),

    # ---- THE PAINFUL TRUTH ----
    ("two", "You wait for him to look down on you. He never does.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
    ("solo", "He is not smarter than you. Not braver. Not born any luckier.", {"pose": "stand"}),
    ("split", "He just flinched a little less, a thousand quiet times, at a thousand small forks.", {}),
    ("solo", "That is the whole distance between you and him. A pile of tiny moments.", {"pose": "think"}),
    ("solo", "Each one so small it felt like it couldn't matter. Together, they built a different person.", {"pose": "stand"}),

    # ---- THE TURN ----
    ("solo", "Then he tells you the thing you weren't ready to hear.", {"pose": "stand"}),
    ("label_above", "I'm not actually real yet, he says.", {"text": "?", "size": 0.13, "color": "accent"}),
    ("solo", "I am just the sum of the choices you haven't made.", {"pose": "stand"}),
    ("split", "Every day you wait, I drift a little further out of reach.", {}),
    ("solo", "But every time you choose forward, even badly, I take one step closer to you.", {"pose": "reach", "face": "happy"}),
    ("stars", "He isn't a ghost haunting your past. He is a direction, waiting in your future.", {}),

    # ---- THE THIRD YOU ----
    ("split", "And then he says, quietly, there's a third one of us, you know.", {}),
    ("compare", "The version who stopped completely. Who stayed exactly here, and called it being safe.", {"poseA": "stand", "poseB": "stand", "faceA": "sad", "faceB": "sad"}),
    ("solo", "He isn't lazy. He's just frightened, and he's gotten very good at hiding it.", {"pose": "stand", "face": "sad"}),
    ("two", "Every single morning, you wake up standing between the two of them.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
    ("solo", "And you decide, with one small choice, which one you take a step toward.", {"pose": "stand"}),

    # ---- HOW ----
    ("solo", "So how do you actually close the gap? Not in one heroic leap.", {"pose": "think"}),
    ("solo", "You don't become him in a day. You become him in a single decision.", {"pose": "stand"}),
    ("label_above", "Pick the one thing he would do today. Only one.", {"text": "1", "size": 0.16, "color": "accent"}),
    ("solo", "Do it badly. Do it scared. Do it anyway.", {"pose": "point_up", "face": "happy"}),
    ("walk", "Not the whole staircase. You only ever have to see the very next step.", {"x0": 0.3, "x1": 0.68, "face": "happy"}),
    ("solo", "And stop waiting for motivation. It never leads. It follows you, after you begin.", {"pose": "stand"}),
    ("celebrate", "Do the brave small thing first, and the feeling you wanted shows up right behind it.", {}),

    # ---- OUTRO ----
    ("solo", "You will never meet the person you could have been in a doorway.", {"pose": "stand"}),
    ("stars", "You meet him in your calendar. In the boring Tuesday. In the choice nobody claps for.", {}),
    ("two", "He is always standing exactly one brave decision away from where you are now.", {"poseA": "stand", "poseB": "wave", "colorB": "muted", "faceB": "happy"}),
    ("solo", "And the beautiful part? You still have time to become him.", {"pose": "look_up", "face": "happy"}),
    ("solo", "Not someday. Not once it's perfect. With the very next thing you choose to do.", {"pose": "stand"}),
    ("cta", "So tell me below. What is the one choice the other you would make today? Then go make it.", {}),
]


def build():
    scenes = []
    for i, beat in enumerate(BEATS):
        tmpl, text = beat[0], beat[1]
        params = beat[2] if len(beat) > 2 else {}
        actors, props = TEMPLATES[tmpl](params or {})
        embiggen(actors)
        scenes.append({"id": f"{i:02d}_{tmpl}", "narration": text, "min_dur": MIN_DUR,
                       "actors": actors, "props": props})
    story = {"title": TITLE, "handle": "@Inklings1", "hook": HOOK, "hook_dur": 2.0,
             "meta": {"playlist": "The Other You", "format": "long-form",
                      "topic": "the person you could have been"},
             "style": BASE_STYLE, "voice": BASE_VOICE, "scenes": scenes}
    path = OUT / f"{SLUG}.json"
    path.write_text(json.dumps(story, indent=2))
    print(f"wrote {path}  ({len(scenes)} scenes)")
    return path


if __name__ == "__main__":
    build()
