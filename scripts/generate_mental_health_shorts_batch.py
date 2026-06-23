#!/usr/bin/env python3
"""Generate 10 listicle-format Shorts on trending mental-health / self-improvement
topics (mental energy, loneliness, depression, anxiety, burnout) - the niche that
overperforms because "5 signs that's literally me" drives comments + shares.

Each follows the same retention structure as scripts/generate_psych_shorts_batch.py,
plus two upgrades requested for this batch:
  - a `hook` overlay (big punch-in title text) so the literal first rendered frame
    reads like a bold thumbnail/cover card, not blank narration text
  - a numbered "1/5 .. 5/5" label above each item's icon so the 5-hook listicle
    structure is visually explicit, not just spoken

Retention rules (house style, same as prior batches):
  - 1of10.com hook framework: 0-5s shock/question, 5-15s promise, 15-30s stakes.
  - uppbeat.io pattern-interrupt rule: one beat per video swaps a flat icon for a
    richer scenery composition.
  - Every video ends with an explicit comment/like/subscribe CTA.

Run:    python scripts/generate_mental_health_shorts_batch.py
Render: python -m faceless build stories/<name>.json --formats 9:16
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "stories"

PALETTE = ["#ff5d5d", "#1f9bff", "#ffb454", "#23b26d", "#a463f2"]

LIGHT_STYLE = {
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
DARK_STYLE = {
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


def thumb_icon(name, pos, r, color):
    """Non-fading icon: fully visible from frame 0, for the cover/thumbnail scene."""
    return {
        "type": "icon", "id": name, "name": name, "color": color, "r": r,
        "keys": [K(0, pos, 1.0, 1)],
    }


def num_label(n, pos, color):
    return {
        "type": "label", "id": f"num{n}", "text": f"{n}/5", "size": 0.07, "color": color,
        "keys": [
            K(0, pos, 0.6, 0),
            K(0.16, pos, 1.08, 1, ease="pop"),
            K(0.55, pos, 1.0, 1),
            K(1, pos, 1.0, 1),
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


ICON_POS = [0.5, 0.24]
NUM_POS = [0.5, 0.12]
SCENERY_SLOT = 4  # which numbered item (1-indexed) gets the pattern-interrupt scenery beat


def item_scene(n, icon_name, narration, color, scenery_names=None):
    if scenery_names:
        props = [
            obj_prop(scenery_names[0], [0.5, 0.3], 0.44),
            obj_prop(scenery_names[1], [0.3, 0.18], 0.27, t0=0.1),
            obj_prop(scenery_names[2], [0.7, 0.18], 0.27, t0=0.15),
            num_label(n, NUM_POS, color),
        ]
    else:
        props = [icon_prop(icon_name, ICON_POS, 0.16, color), num_label(n, NUM_POS, color)]
    return scene(f"{n+1:02d}_item{n}", narration, props, min_dur=3.6)


def build(slug, title, style, hook, intro_icon, items, cta_icon, cta_line, topic):
    intro_color = items[0][1]
    scenes = [
        scene("01_intro", title_intro(title), [thumb_icon(intro_icon, ICON_POS, 0.16, intro_color)],
              min_dur=3.4),
    ]
    for i, (icon_name, color, line, *rest) in enumerate(items, start=1):
        scenery_names = rest[0] if rest else None
        scenes.append(item_scene(i, icon_name, line, color, scenery_names))
    scenes.append(scene("07_cta", cta_line, [icon_prop(cta_icon, ICON_POS, 0.16, "#23b26d")], min_dur=3.8))
    return {
        "title": title,
        "handle": "@Inklings1",
        "hook": hook,
        "hook_dur": 1.8,
        "style": style,
        "voice": VOICE,
        "scenes": scenes,
        "meta": {"format": "kinetic-typography+listicle", "topic": topic},
    }, slug


def title_intro(title):
    return INTROS[title]


INTROS = {}


def add_intro(title, text):
    INTROS[title] = text


VIDEOS = []

# 1 -------------------------------------------------------------------------
t = "5 Habits Secretly Draining Your Mental Energy Every Day"
add_intro(t, "Here are 5 everyday habits secretly draining your mental energy without you even noticing.")
VIDEOS.append(build(
    "habits_draining_mental_energy", t, DARK_STYLE, "5 HABITS DRAINING YOUR MENTAL ENERGY", "brain",
    [
        ("chat", "#1f9bff", "Replying to every notification the second it pops up keeps your brain in constant alert mode."),
        ("clock", "#ffb454", "Running on caffeine instead of sleep borrows energy you don't actually have."),
        ("warning", "#ff5d5d", "Saying yes when you mean no quietly taxes you all day long."),
        ("arrow_down", "#a463f2", "Doomscrolling before bed loads your brain with stress it can't process while you sleep.",
         ["table", "laptop", "books"]),
        ("brain", "#23b26d", "Multitasking doesn't save time, it just splits your one battery five different ways."),
    ],
    "check", "Which one hit closest to home? Comment the number, like this if it helped, and subscribe for more daily psychology shorts.",
    "mental-energy-habits",
))

# 2 -------------------------------------------------------------------------
t = "5 Silent Signs You're More Lonely Than You Realize"
add_intro(t, "Loneliness doesn't always look empty. Here are 5 silent signs you're more lonely than you realize.")
VIDEOS.append(build(
    "silent_signs_of_loneliness", t, DARK_STYLE, "5 SILENT SIGNS YOU'RE LONELY", "heart",
    [
        ("chat", "#1f9bff", "You scroll through old messages just to feel like someone's still there."),
        ("clock", "#ffb454", "You stay busy on purpose, because stillness is when it gets loud."),
        ("heart", "#ff5d5d", "You crave connection but cancel plans the moment they're offered."),
        ("warning", "#a463f2", "You feel lonely in a room full of people who actually like you.",
         ["armchair", "mug", "blanket"]),
        ("brain", "#23b26d", "You've started talking to yourself just to hear a voice that isn't a screen."),
    ],
    "check", "If even one of these felt familiar, comment below, you're not as alone as it feels. Like this and subscribe for more.",
    "loneliness-signs",
))

# 3 -------------------------------------------------------------------------
t = "5 Signs of High-Functioning Depression Most People Miss"
add_intro(t, "High-functioning depression hides behind a smile. Here are 5 signs most people completely miss.")
VIDEOS.append(build(
    "high_functioning_depression_signs", t, DARK_STYLE, "5 SIGNS OF HIDDEN DEPRESSION", "warning",
    [
        ("check", "#23b26d", "You're getting everything done, but nothing feels like it matters."),
        ("chat", "#1f9bff", "You're the funniest person in the room and the emptiest one too."),
        ("clock", "#ffb454", "You sleep eight hours and still wake up exhausted."),
        ("warning", "#ff5d5d", "You've stopped wanting things you used to love, and just call it being busy.",
         ["armchair", "blanket", "mug"]),
        ("brain", "#a463f2", "You can talk anyone else through a hard day, but never your own."),
    ],
    "heart", "If this sounds like you, you're not broken, you're tired. Comment below, like this, and subscribe so you don't feel alone in it.",
    "high-functioning-depression",
))

# 4 -------------------------------------------------------------------------
t = "5 Habits Quietly Feeding Your Anxiety Without You Knowing"
add_intro(t, "These 5 everyday habits are quietly feeding your anxiety without you ever clocking it.")
VIDEOS.append(build(
    "habits_feeding_anxiety", t, DARK_STYLE, "5 HABITS FEEDING YOUR ANXIETY", "warning",
    [
        ("chat", "#1f9bff", "Checking the news first thing in the morning loads your brain with dread before breakfast."),
        ("warning", "#ff5d5d", "Replaying old conversations keeps your nervous system stuck in a fight that already ended."),
        ("clock", "#ffb454", "Skipping meals tells your body it's in danger, so it panics to match.",
         ["table", "books", "laptop"]),
        ("arrow_down", "#a463f2", "Avoiding the hard conversation doesn't remove the anxiety, it just rents it out longer."),
        ("brain", "#23b26d", "Comparing your behind-the-scenes to everyone else's highlight reel quietly convinces you you're behind."),
    ],
    "check", "Which habit do you need to drop first? Comment the number, like this video, and subscribe for more.",
    "anxiety-habits",
))

# 5 -------------------------------------------------------------------------
t = "5 Things Mentally Strong People Never Do"
add_intro(t, "Mentally strong people aren't fearless. Here are 5 things they simply never do.")
VIDEOS.append(build(
    "mentally_strong_people_never_do", t, LIGHT_STYLE, "5 THINGS MENTALLY STRONG PEOPLE NEVER DO", "star",
    [
        ("warning", "#ff5d5d", "They never let one bad day write the story of the whole week."),
        ("heart", "#1f9bff", "They never confuse being kind with being a doormat."),
        ("clock", "#ffb454", "They never wait to feel ready before they start.",
         ["table", "laptop", "books"]),
        ("chat", "#a463f2", "They never explain themselves to people who were never going to understand."),
        ("star", "#23b26d", "They never compare a chapter one to someone else's chapter twenty."),
    ],
    "check", "Which one are you working on? Comment below, like this if it resonated, and subscribe for more.",
    "mental-strength",
))

# 6 -------------------------------------------------------------------------
t = "5 Reasons You're Tired After a Full Night's Sleep"
add_intro(t, "Slept eight hours and still exhausted? Here are 5 sneaky reasons why.")
VIDEOS.append(build(
    "tired_after_sleeping_reasons", t, LIGHT_STYLE, "5 REASONS YOU'RE STILL TIRED", "clock",
    [
        ("clock", "#1f9bff", "Your sleep schedule changes every day, so your body never locks into a rhythm."),
        ("warning", "#ff5d5d", "Your phone's blue light tricks your brain into staying half-awake all night."),
        ("brain", "#a463f2", "Stress hormones don't clock out just because your eyes are closed.",
         ["armchair", "blanket", "mug"]),
        ("chat", "#ffb454", "Snoring or shallow breathing can quietly cut your oxygen all night long."),
        ("arrow_down", "#23b26d", "Skipping water during the day leaves your brain running on empty by morning."),
    ],
    "check", "Which one's been sabotaging your sleep? Comment below, like this, and subscribe for more.",
    "tired-after-sleep",
))

# 7 -------------------------------------------------------------------------
t = "5 Habits of People Who Never Burn Out"
add_intro(t, "Some people just don't burn out. Here are 5 habits they all quietly share.")
VIDEOS.append(build(
    "habits_people_never_burn_out", t, LIGHT_STYLE, "5 HABITS OF PEOPLE WHO NEVER BURN OUT", "check",
    [
        ("clock", "#1f9bff", "They protect their mornings like it's the most important meeting of the day."),
        ("heart", "#ff5d5d", "They say no early, instead of saying yes and resenting it later."),
        ("star", "#ffb454", "They celebrate small wins instead of waiting for the finish line.",
         ["table", "books", "laptop"]),
        ("chat", "#a463f2", "They ask for help before they're drowning, not after."),
        ("check", "#23b26d", "They end the day on purpose, instead of just running out of hours."),
    ],
    "star", "Which habit are you missing? Comment the number, like this, and subscribe for more.",
    "burnout-prevention",
))

# 8 -------------------------------------------------------------------------
t = "5 Signs You're Emotionally Exhausted, Not Just Tired"
add_intro(t, "Tired sleep can fix. Emotional exhaustion is different. Here are 5 signs you're dealing with the second one.")
VIDEOS.append(build(
    "emotionally_exhausted_signs", t, DARK_STYLE, "5 SIGNS YOU'RE EMOTIONALLY EXHAUSTED", "warning",
    [
        ("warning", "#ff5d5d", "Small inconveniences suddenly feel unbearable."),
        ("heart", "#1f9bff", "You've stopped reacting to things that used to make you happy."),
        ("chat", "#ffb454", "You're irritated by people you actually love, for no real reason.",
         ["armchair", "mug", "blanket"]),
        ("clock", "#a463f2", "Rest doesn't reset you anymore, you wake up just as drained."),
        ("brain", "#23b26d", "You feel like you're performing your own life instead of living it."),
    ],
    "heart", "If this is you, please be gentle with yourself. Comment below, like this, and subscribe for more.",
    "emotional-exhaustion",
))

# 9 -------------------------------------------------------------------------
t = "5 Small Habits That Instantly Boost Your Mental Energy"
add_intro(t, "Want your mental energy back today? Start with these 5 small habits.")
VIDEOS.append(build(
    "habits_boost_mental_energy", t, LIGHT_STYLE, "5 HABITS THAT BOOST MENTAL ENERGY", "lightbulb",
    [
        ("star", "#ffb454", "Step outside for two minutes before you touch your phone."),
        ("heart", "#ff5d5d", "Text one person who actually makes you feel good."),
        ("check", "#23b26d", "Finish one small task you've been avoiding, it frees more energy than it costs.",
         ["table", "books", "laptop"]),
        ("clock", "#1f9bff", "Take a real break, not a scrolling break."),
        ("lightbulb", "#a463f2", "Write down one thing that's going right, even on a hard day."),
    ],
    "check", "Try one of these today. Comment which one you'll start with, like this, and subscribe for more.",
    "boost-mental-energy",
))

# 10 ------------------------------------------------------------------------
t = "5 Signs You're Lonely Even Around People You Love"
add_intro(t, "You can be surrounded by people and still feel completely alone. Here are 5 signs it's happening to you.")
VIDEOS.append(build(
    "lonely_around_people_you_love", t, DARK_STYLE, "5 SIGNS YOU'RE LONELY AROUND PEOPLE", "heart",
    [
        ("chat", "#1f9bff", "You're in the room, but you've stopped really saying anything real."),
        ("heart", "#ff5d5d", "You laugh at the joke, but nobody there actually knows what you're carrying."),
        ("warning", "#ffb454", "You feel like a guest in your own life, even at your own table.",
         ["armchair", "table", "mug"]),
        ("clock", "#a463f2", "You leave gatherings more drained than connected."),
        ("brain", "#23b26d", "You've started performing 'fine' so well that nobody thinks to check."),
    ],
    "heart", "If this is you, let someone in today. Comment below, like this, and subscribe for more.",
    "lonely-around-people",
))

if __name__ == "__main__":
    for script, slug in VIDEOS:
        out = OUT / f"{slug}.json"
        out.write_text(json.dumps(script, indent=2))
        print(f"wrote {out}")
