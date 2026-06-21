#!/usr/bin/env python3
"""Generate the launch batch of story JSONs from compact narration beats.

Each story is a list of (template, narration, params) beats. Templates expand
into the figures/props/keyframes the engine needs, so you only write the words.
Re-run after editing to regenerate:  python scripts/generate_stories.py

Render them (Piper on your machine, Festival fallback in-sandbox):
  for f in stories/1*_*.json stories/0*_*.json; do python -m faceless build "$f"; done
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "stories"

BASE_STYLE = {
    "background": "#0e1320", "ink": "#f2ede1", "accent": "#ffb454", "muted": "#6f7791",
    "fps": 24, "wobble": 1.7, "grain": 0.05, "vignette": 0.55,
    "caption": {"size": 0.05, "color": "#ffffff"},
    "logo": "branding/watermark.png", "logo_pos": "tl", "logo_scale": 0.1, "logo_opacity": 0.72,
}
BASE_VOICE = {
    "backend": "piper", "piper_model": "voices/en_US-ryan-high.onnx", "piper_length": 1.1,
    "voice": "cmu_us_slt_arctic_hts", "rate": 135, "polish": True, "gap": 0.5,
}
MIN_DUR = 4.8   # per-scene floor -> deliberate holds; keeps videos in the 1-2 min range

GROUND = 0.62          # default hip height
SCALE = 0.30


# --------------------------------------------------------------------------- #
# keyframe / element helpers
# --------------------------------------------------------------------------- #
def K(t, pos=None, pose=None, scale=None, alpha=None, ease=None, p1=None, p2=None):
    d = {"t": round(t, 3)}
    for k, v in (("pos", pos), ("pose", pose), ("scale", scale),
                 ("alpha", alpha), ("ease", ease), ("p1", p1), ("p2", p2)):
        if v is not None:
            d[k] = v
    return d


def figure(fid, keys, color="ink", face="neutral"):
    return {"type": "figure", "id": fid, "color": color, "face": face, "keys": keys}


def fkeys(pos, poses, scale=SCALE):
    """Fade in, then move through a list of poses across the scene."""
    poses = poses if isinstance(poses, list) else [poses]
    keys = [K(0, pos, poses[0], scale, 0), K(0.16, pos, poses[0], scale, 1)]
    for i, ps in enumerate(poses[1:], 1):
        keys.append(K(min(0.97, 0.16 + 0.8 * i / len(poses)), pos, ps, scale, 1))
    keys.append(K(1, pos, poses[-1], scale, 1))
    return keys


def label(lid, text, color, size, pos, t0=0.35, hold=True, follow=None, offset=None, front=True):
    keys = [K(t0, pos, alpha=0, scale=0.4),
            K(t0 + 0.2, [pos[0], pos[1] - 0.02], alpha=1, scale=1.0, ease="pop"),
            K(1, [pos[0], pos[1] - 0.02], alpha=1, scale=1.0)]
    d = {"type": "label", "id": lid, "text": text, "color": color, "size": size,
         "keys": keys, "front": front}
    if follow:
        d["follow"] = follow
        d["offset"] = offset or [0, -0.24]
    return d


def path(pid, points, color, anchor, unit=0.4, t0=0.1, alpha=0.9, front=False):
    return {"type": "path", "id": pid, "points": points, "color": color,
            "anchor": anchor, "unit": unit, "front": front,
            "keys": [K(t0, alpha=0), K(t0 + 0.25, alpha=alpha, ease="ease_out"), K(1, alpha=alpha)]}


def circle(cid, pos, r, color, t0=0.1, alpha=1.0):
    return {"type": "circle", "id": cid, "color": color, "r": r,
            "keys": [K(t0, pos, alpha=0), K(t0 + 0.3, [pos[0], pos[1] - 0.03], alpha=alpha, ease="ease_out"),
                     K(1, [pos[0], pos[1] - 0.03], alpha=alpha)]}


def line(lid, p1, p2, color, t0=0.1, alpha=0.9, front=False):
    return {"type": "line", "id": lid, "color": color, "front": front,
            "keys": [K(t0, p1=p1, p2=p2, alpha=0),
                     K(t0 + 0.25, p1=p1, p2=p2, alpha=alpha, ease="ease_out"),
                     K(1, p1=p1, p2=p2, alpha=alpha)]}


# --------------------------------------------------------------------------- #
# scene templates  ->  (actors, props)
# --------------------------------------------------------------------------- #
def t_hook(p):
    return ([figure("hero", [K(0, [0.5, GROUND], "stand", SCALE, 0), K(0.16, [0.5, GROUND], "stand", SCALE, 1),
                             K(0.55, [0.5, GROUND], "think", SCALE, 1), K(1, [0.5, GROUND], "think", SCALE, 1)],
                    face=p.get("face", "neutral"))],
            [label("q", p.get("mark", "?"), "accent", 0.16, [0.66, 0.31])])


def t_solo(p):
    poses = p.get("poses", p.get("pose", "stand"))
    return ([figure("hero", fkeys([0.5, GROUND], poses), color=p.get("color", "ink"),
                    face=p.get("face", "neutral"))], [])


def t_point(p):
    pose = "point_r" if p.get("dir", "r") == "r" else "point_l"
    return ([figure("hero", fkeys([0.5, GROUND], ["stand", pose]), face=p.get("face", "neutral"))], [])


def t_walk(p):
    x0, x1 = p.get("x0", 0.30), p.get("x1", 0.70)
    keys = [K(0, [x0, GROUND], "stand", SCALE, 0), K(0.12, [x0, GROUND], "walk_a", SCALE, 1)]
    for i in range(1, 5):
        keys.append(K(0.12 + 0.78 * i / 5, [x0 + (x1 - x0) * i / 5, GROUND],
                      "walk_a" if i % 2 else "walk_b", SCALE, 1))
    keys.append(K(1, [x1, GROUND], "stand", SCALE, 1))
    return ([figure("hero", keys, color=p.get("color", "ink"), face=p.get("face", "happy"))], [])


def t_two(p):
    a = figure("a", fkeys([0.33, GROUND], p.get("poseA", "stand"), 0.27),
               color=p.get("colorA", "ink"), face=p.get("faceA", "neutral"))
    b = figure("b", fkeys([0.67, GROUND], p.get("poseB", "stand"), 0.27),
               color=p.get("colorB", "ink"), face=p.get("faceB", "neutral"))
    return ([a, b], [])


def t_compare(p):
    # younger/smaller vs older self
    a = figure("a", fkeys([0.34, GROUND + 0.03], p.get("poseA", "stand"), 0.22),
               color="muted", face=p.get("faceA", "surprised"))
    b = figure("b", fkeys([0.66, GROUND], p.get("poseB", "stand"), 0.31),
               color="ink", face=p.get("faceB", "neutral"))
    return ([a, b], [])


def t_split(p):
    hero = figure("hero", [K(0, [0.5, GROUND], "stand", 0.28, 1), K(0.45, [0.4, GROUND], "stand", 0.28, 1),
                           K(1, [0.4, GROUND], "stand", 0.28, 1)], face=p.get("face", "neutral"))
    ghost = figure("ghost", [K(0, [0.5, GROUND], "stand", 0.28, 0), K(0.45, [0.5, GROUND], "stand", 0.28, 0.2),
                             K(0.8, [0.62, GROUND], "stand", 0.28, 0.85), K(1, [0.62, GROUND], "stand", 0.28, 0.85)],
                   color="muted", face="neutral")
    return ([hero, ghost], [])


def t_crowd(p):
    specs = [(0.15, 0.50, "wave", "ink"), (0.33, 0.42, "celebrate", "muted"),
             (0.50, 0.56, "point_up", "ink"), (0.67, 0.42, "shrug", "muted"),
             (0.85, 0.50, "wave", "ink"), (0.50, 0.36, "stand", "muted")]
    actors = []
    for i, (x, y, pose, col) in enumerate(specs[:p.get("n", 6)]):
        t0 = 0.05 + i * 0.07
        actors.append(figure(f"m{i}", [K(0, [x, y], pose, 0.13, 0), K(t0, [x, y], "stand", 0.13, 0),
                                       K(t0 + 0.12, [x, y], pose, 0.13, 1), K(1, [x, y], pose, 0.13, 1)],
                             color=col, face="dots"))
    return (actors, [])


def t_label_above(p):
    col = p.get("color", "accent")
    hero = figure("hero", fkeys([0.5, GROUND], p.get("poses", ["stand"])), face=p.get("face", "neutral"))
    lab = label("num", p.get("text", "?"), col, p.get("size", 0.07), [0.5, GROUND - 0.26],
                t0=0.25, follow="hero", offset=[0, -0.26])
    return ([hero], [lab])


def t_stars(p):
    hero = figure("hero", fkeys([0.5, GROUND + 0.05], ["stand", "look_up"]), face=p.get("face", "neutral"))
    stars = [label(f"s{i}", "*", "accent" if i % 2 else "ink", 0.045 + 0.01 * (i % 2),
                   pos, t0=0.3 + i * 0.08)
             for i, pos in enumerate([[0.26, 0.24], [0.44, 0.18], [0.6, 0.22], [0.76, 0.28], [0.36, 0.32]])]
    return ([hero], stars)


def t_celebrate(p):
    hero = figure("hero", [K(0, [0.5, GROUND + 0.04], "stand", SCALE, 1),
                           K(0.4, [0.5, GROUND], "celebrate", SCALE, 1, ease="pop"),
                           K(1, [0.5, GROUND], "celebrate", SCALE, 1)], face="happy")
    sparks = [label("e1", "!", "accent", 0.07, [0.31, 0.36], t0=0.4),
              label("e2", "!", "accent", 0.07, [0.7, 0.38], t0=0.5)]
    return ([hero], sparks)


def t_bench(p):
    # seat line + 2 legs; figures sit with hips ON the seat (legs hang = seated).
    # single figure sits left, leaving the right half empty (the "empty half").
    seat_y, gy = 0.61, 0.76
    props = [line("seat", [0.32, seat_y], [0.68, seat_y], "muted"),
             line("legL", [0.38, seat_y], [0.38, gy], "muted"),
             line("legR", [0.62, seat_y], [0.62, gy], "muted")]
    if p.get("birds"):
        for i, (x, y) in enumerate([(0.28, 0.34), (0.40, 0.28), (0.72, 0.31), (0.82, 0.38)]):
            props.append(path(f"bird{i}", [[-1, 0.6], [0, 0], [1, 0.6]], "ink",
                              anchor=[x, y], unit=0.045, t0=0.2 + i * 0.12, front=True))
    if p.get("two"):
        actors = [figure("a", fkeys([0.41, seat_y], "stand", 0.23), face=p.get("faceA", "neutral")),
                  figure("b", fkeys([0.59, seat_y], "stand", 0.23), color="muted", face=p.get("faceB", "neutral"))]
    else:
        actors = [figure("a", fkeys([0.42, seat_y], "stand", 0.23), face=p.get("face", "neutral"))]
    return (actors, props)


def t_bus(p):
    # window strip (implies a bus interior) + a long seat; figures sit on it.
    seat_y = 0.61
    props = [
        {"type": "rect", "id": "win", "color": "muted", "w": 0.52, "h": 0.2,
         "keys": [K(0.05, [0.5, 0.4], alpha=0), K(0.3, [0.5, 0.4], alpha=0.65, ease="ease_out"),
                  K(1, [0.5, 0.4], alpha=0.65)]},
        line("seat", [0.30, seat_y], [0.70, seat_y], "muted"),
    ]
    if p.get("two"):
        actors = [figure("a", fkeys([0.41, seat_y], "stand", 0.22), face=p.get("faceA", "neutral")),
                  figure("b", fkeys([0.59, seat_y], "stand", 0.22), color="muted", face=p.get("faceB", "neutral"))]
    else:  # one figure + an empty seat beside her (divider hint)
        actors = [figure("a", fkeys([0.40, seat_y], "stand", 0.22), face=p.get("face", "sad"))]
        props.append(line("divider", [0.55, seat_y], [0.55, seat_y - 0.13], "muted", t0=0.2, alpha=0.45))
    return (actors, props)


def t_cta(p):
    hero = figure("hero", fkeys([0.5, GROUND], ["stand", "wave"]), face="happy")
    return ([hero], [label("m", p.get("mark", "+"), "accent", 0.08, [0.68, 0.38], t0=0.45)])


TEMPLATES = {
    "hook": t_hook, "solo": t_solo, "point": t_point, "walk": t_walk, "two": t_two,
    "compare": t_compare, "split": t_split, "crowd": t_crowd, "label_above": t_label_above,
    "stars": t_stars, "celebrate": t_celebrate, "bench": t_bench, "bus": t_bus, "cta": t_cta,
}


def make_story(slug, title, playlist, beats):
    scenes = []
    for i, beat in enumerate(beats):
        tmpl, text = beat[0], beat[1]
        params = beat[2] if len(beat) > 2 else {}
        actors, props = TEMPLATES[tmpl](params or {})
        scenes.append({"id": f"{i:02d}_{tmpl}", "narration": text, "min_dur": MIN_DUR,
                       "actors": actors, "props": props})
    story = {"title": title, "handle": "@Inklings1", "meta": {"playlist": playlist},
             "style": BASE_STYLE, "voice": BASE_VOICE, "scenes": scenes}
    (OUT / f"{slug}.json").write_text(json.dumps(story, indent=2))
    return slug, len(scenes)


# --------------------------------------------------------------------------- #
# the 13 stories (narration beats)
# --------------------------------------------------------------------------- #
STORIES = [
 ("02_sonder", "Everyone You Walk Past Has a Life as Deep as Yours", "3 AM Thoughts", [
   ("hook", "You're walking through a crowded street.", {"face": "neutral"}),
   ("crowd", "Hundreds of strangers blur past you.", {}),
   ("point", "And your mind quietly files them all under one word. Extras.", {"dir": "r"}),
   ("solo", "But look a little closer.", {"pose": "think"}),
   ("label_above", "That woman on her phone is rehearsing how to say goodbye.", {"text": "...", "face": "sad"}),
   ("solo", "That man staring at nothing just lost the job he held for twenty years.", {"pose": "stand", "face": "sad"}),
   ("solo", "That kid has a nickname only his grandmother is allowed to use.", {"pose": "wave", "face": "happy"}),
   ("solo", "Every stranger you pass is the main character of a story as deep as yours.", {"pose": "stand"}),
   ("solo", "Full of people they love. Fears they hide. Nights they can't forget.", {"pose": "think", "face": "sad"}),
   ("label_above", "There's a word for this feeling. Sonder.", {"text": "SONDER", "size": 0.06, "face": "neutral"}),
   ("solo", "The quiet shock of realizing everyone is exactly as real as you are.", {"pose": "look_up"}),
   ("crowd", "Hundreds of universes, brushing past each other, every single day.", {}),
   ("stars", "You'll forget their faces by tonight. And they'll forget yours.", {}),
   ("cta", "So who did you walk past today, without ever really seeing them?", {}),
 ]),
 ("03_days_left", "What If You Could See How Many Days People Had Left?", "What If…", [
   ("hook", "What if you could see a number floating above everyone's head?", {}),
   ("label_above", "The exact number of days they have left to live.", {"text": "9,540", "face": "neutral"}),
   ("solo", "You'd stop scrolling your phone. You'd start watching the numbers.", {"pose": "stand"}),
   ("label_above", "Your best friend glows with a comfortable forty thousand.", {"text": "41,028", "face": "happy"}),
   ("label_above", "The old man feeding pigeons has just two hundred.", {"text": "204", "color": "muted", "face": "neutral"}),
   ("solo", "And then, one ordinary morning, you'd see it.", {"pose": "think"}),
   ("label_above", "A stranger on the train. The number above her is one.", {"text": "1", "color": "accent", "face": "neutral"}),
   ("solo", "She's laughing at something on her screen. She has no idea.", {"pose": "stand"}),
   ("solo", "Do you tell her? Could you even find the words?", {"pose": "think", "face": "sad"}),
   ("two", "You freeze. The doors slide open. And just like that, she's gone.", {"poseA": "stand", "poseB": "walk_a", "colorB": "muted"}),
   ("solo", "That night, you can't sleep. So you finally walk to a mirror.", {"pose": "stand", "face": "sad"}),
   ("label_above", "But your own number is the one you were never meant to see.", {"text": "?", "color": "accent"}),
   ("stars", "Maybe not seeing it is the only thing that lets us truly live.", {}),
   ("cta", "If you could see your number… would you even want to? Tell me below.", {}),
 ]),
 ("04_stranger_wave", "He Waved at the Same Stranger Every Day", "The Twist", [
   ("hook", "Every morning at 8:15, two trains stopped side by side.", {}),
   ("two", "A man in one window. A woman in the other. Total strangers.", {"poseA": "stand", "poseB": "stand"}),
   ("two", "One day, he waved. And to his surprise, she waved back.", {"poseA": "wave", "poseB": "wave", "faceA": "happy", "faceB": "happy"}),
   ("two", "It became their ritual. A wave, a smile, then gone in opposite directions.", {"poseA": "wave", "poseB": "wave"}),
   ("solo", "He never learned her name. But she made his grey mornings lighter.", {"pose": "stand", "face": "happy"}),
   ("solo", "Then one Tuesday, her window was empty.", {"pose": "stand", "face": "sad"}),
   ("solo", "The next day, empty again. And the next.", {"pose": "stand", "face": "sad"}),
   ("solo", "He told himself she'd changed jobs. Moved. Anything.", {"pose": "think"}),
   ("walk", "But he kept choosing the 8:15 train. Just in case.", {"x0": 0.35, "x1": 0.6, "face": "sad"}),
   ("solo", "Years later, an old woman stopped him on that very platform.", {"pose": "stand"}),
   ("two", "'You're him,' she said. 'My mother waved at you every morning.'", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
   ("two", "'She said you were the only stranger who ever really saw her.'", {"poseA": "stand", "poseB": "stand", "faceA": "sad", "colorB": "muted"}),
   ("stars", "He finally understood. A small kindness can be someone's whole world.", {}),
   ("cta", "Who's the stranger that quietly made your day better? Tell me below.", {}),
 ]),
 ("05_never_gave_up", "Somewhere, There's a You Who Never Gave Up", "The Other You", [
   ("hook", "Somewhere, there's a version of you who never gave up.", {}),
   ("split", "You split apart on one completely ordinary night.", {}),
   ("two", "You closed the laptop. He kept going for one more hour.", {"poseA": "stand", "poseB": "reach", "colorB": "muted"}),
   ("walk", "While you slept, he kept walking forward.", {"x0": 0.3, "x1": 0.7, "face": "neutral"}),
   ("solo", "He failed more than you did. He just refused to call it the end.", {"pose": "stand"}),
   ("compare", "Today, you and he look almost the same. Almost.", {"poseA": "stand", "poseB": "stand"}),
   ("solo", "But his eyes hold something yours lost somewhere along the way.", {"pose": "look_up"}),
   ("solo", "He's not smarter than you. Not braver. Not luckier.", {"pose": "stand"}),
   ("solo", "He just didn't stop on the night you decided it was over.", {"pose": "think", "face": "sad"}),
   ("solo", "And here's the part that should keep you up tonight.", {"pose": "think"}),
   ("split", "That version of you isn't gone. He begins again every morning.", {}),
   ("solo", "The door he walked through is still standing right in front of you.", {"pose": "reach"}),
   ("stars", "You can become him. Not someday. Tonight.", {}),
   ("cta", "What did you quit that you're not ready to let go of? Say it below.", {}),
 ]),
 ("06_last_time", "One Day You'll Do Everything for the Last Time", "3 AM Thoughts", [
   ("hook", "There was a last time your mother ever carried you to bed.", {}),
   ("solo", "And neither of you knew it was the last time.", {"pose": "stand", "face": "sad"}),
   ("solo", "A last time your father lifted you onto his shoulders.", {"pose": "stand"}),
   ("crowd", "A final game of tag, before everyone just stopped playing.", {}),
   ("solo", "Most of life's endings don't announce themselves.", {"pose": "think"}),
   ("solo", "No music. No warning. They just quietly happen.", {"pose": "stand"}),
   ("two", "One day you saw a childhood friend for the very last time.", {"poseA": "wave", "poseB": "wave"}),
   ("solo", "You said, see you around. You didn't.", {"pose": "stand", "face": "sad"}),
   ("walk", "People don't always leave with goodbyes. Sometimes just slow, silent fades.", {"x0": 0.5, "x1": 0.85, "face": "sad"}),
   ("solo", "One day you'll hug someone for the last time, and only one of you will know.", {"pose": "think", "face": "sad"}),
   ("solo", "It sounds unbearable. But it's also the secret.", {"pose": "stand"}),
   ("celebrate", "Because if everything gets a last time, then nothing is ordinary.", {}),
   ("stars", "Not the boring Tuesday. Not the traffic with someone you love.", {}),
   ("cta", "Call the person you keep meaning to call. Before it becomes a last time.", {}),
 ]),
 ("07_lies_cost_days", "What If Every Lie Took One Day Off Your Life?", "What If…", [
   ("hook", "What if every lie took one full day off your life?", {}),
   ("label_above", "Not a metaphor. A real number, ticking down in front of you.", {"text": "-1", "color": "accent"}),
   ("solo", "I'm fine. Minus one day.", {"pose": "stand", "face": "sad"}),
   ("solo", "I'm five minutes away. Minus another.", {"pose": "stand"}),
   ("two", "No really, it looks great on you. Minus three, somehow.", {"poseA": "shrug", "poseB": "stand"}),
   ("crowd", "Suddenly, the whole world would go very, very quiet.", {}),
   ("solo", "We tell around two hundred lies a day. Most of them to ourselves.", {"pose": "think"}),
   ("label_above", "Your counter would bleed out before lunch.", {"text": "-37", "color": "accent", "face": "sad"}),
   ("solo", "But here's the strange part.", {"pose": "think"}),
   ("solo", "The truth would cost you nothing. And buy you everything.", {"pose": "stand", "face": "happy"}),
   ("two", "Real conversations. Real people. A life with no exits to maintain.", {"poseA": "wave", "poseB": "wave", "faceA": "happy", "faceB": "happy"}),
   ("solo", "We think our lies protect us. Mostly, they just cost us time.", {"pose": "stand"}),
   ("stars", "Time we will never, ever get a refund on.", {}),
   ("cta", "What's one lie you'd stop telling, if you could see the price? Comment it.", {}),
 ]),
 ("08_old_man_birds", "The Old Man Fed the Birds Every Morning", "The Twist", [
   ("hook", "Every morning, an old man sat on the same bench and fed the birds.", {}),
   ("bench", "Rain or shine. Always the same crumbs. Always the same seat.", {"birds": True, "face": "neutral"}),
   ("solo", "The whole neighborhood assumed he was just lonely.", {"pose": "stand"}),
   ("bench", "Children laughed, joggers passed. He only smiled and scattered the bread.", {"birds": True}),
   ("two", "One day, a young woman asked why he never missed a single morning.", {"poseA": "stand", "poseB": "stand"}),
   ("bench", "He gently patted the empty half of the bench.", {"face": "sad"}),
   ("solo", "My wife fed them here for forty years, he said.", {"pose": "stand", "face": "sad"}),
   ("bench", "She knew every one of them. Named them. They came to her like old friends.", {"birds": True}),
   ("solo", "When she passed, the birds still came. Looking for her.", {"pose": "stand", "face": "sad"}),
   ("bench", "So I come. So they're not waiting for someone who'll never return.", {"birds": True}),
   ("bench", "The woman sat with him in silence. The birds gathered around them both.", {"two": True, "birds": True}),
   ("solo", "He wasn't feeding birds. He was keeping a promise.", {"pose": "stand"}),
   ("stars", "Some love doesn't end. It just changes who it takes care of.", {}),
   ("cta", "Who do you show up for, even when no one is watching? Tell me below.", {}),
 ]),
 ("09_younger_self", "You Met the You From Ten Years Ago. He's Watching.", "The Other You", [
   ("hook", "Imagine the you from ten years ago is standing right in front of you.", {}),
   ("compare", "Younger. Softer. Terrified of things you've long since forgotten.", {"poseA": "stand", "poseB": "stand"}),
   ("solo", "He's looking at your life. The one he used to dream about.", {"pose": "look_up"}),
   ("solo", "And the first thing he asks is… did we make it?", {"pose": "think"}),
   ("solo", "You open your mouth, and you're not quite sure what to say.", {"pose": "stand", "face": "sad"}),
   ("compare", "He notices you stopped drawing. That you let that friendship quietly die.", {"poseA": "stand", "poseB": "stand", "faceA": "sad"}),
   ("solo", "He's heartbroken that you call the dream unrealistic now.", {"pose": "stand", "face": "sad"}),
   ("solo", "But then he sees the things you survived. The things that should have broken you.", {"pose": "stand"}),
   ("compare", "And his eyes go wide. We got through THAT?", {"poseA": "celebrate", "poseB": "stand", "faceA": "surprised"}),
   ("solo", "He's not disappointed in you. He's amazed by you.", {"pose": "stand", "face": "happy"}),
   ("compare", "He would trade everything to be standing where you are right now.", {"poseA": "stand", "poseB": "stand"}),
   ("stars", "The life you have is the life he prayed for.", {}),
   ("solo", "Don't make him watch you waste it.", {"pose": "stand"}),
   ("cta", "What would the you from ten years ago thank you for? Say it below.", {}),
 ]),
 ("10_afraid_dark", "You're Not Afraid of the Dark", "3 AM Thoughts", [
   ("hook", "You're not actually afraid of the dark.", {}),
   ("solo", "Think about it. A dark, empty room doesn't really scare you.", {"pose": "stand"}),
   ("two", "Put one other person in it, and the fear simply vanishes.", {"poseA": "stand", "poseB": "stand"}),
   ("solo", "It was never the darkness. It was being alone in it.", {"pose": "think"}),
   ("solo", "Humans aren't scared of the absence of light.", {"pose": "stand"}),
   ("crowd", "We're scared of the absence of each other.", {}),
   ("solo", "For a hundred thousand years, alone in the dark meant one thing. Danger.", {"pose": "stand", "face": "sad"}),
   ("solo", "The ones who feared it survived. So now, so do we.", {"pose": "stand"}),
   ("solo", "That's why the empty apartment feels louder than any noise.", {"pose": "think", "face": "sad"}),
   ("two", "And why one familiar voice can make an entire night feel safe.", {"poseA": "stand", "poseB": "wave", "faceB": "happy"}),
   ("solo", "Your fear of the dark was never weakness.", {"pose": "stand"}),
   ("solo", "It's a million years of ancestors whispering, don't drift too far from the others.", {"pose": "look_up"}),
   ("stars", "So if tonight feels heavy, it isn't the dark. It's the alone.", {}),
   ("cta", "Text someone you trust. You don't have to sit in it by yourself.", {}),
 ]),
 ("11_you_who_won", "What If You Woke Up as the Version of You Who Won?", "What If…", [
   ("hook", "What if you woke up tomorrow as the version of you who won?", {}),
   ("split", "Same face. Same past. But every choice went right.", {}),
   ("celebrate", "He took the risk you talked yourself out of.", {}),
   ("two", "He sent the message. Started the thing. Said the hard truth.", {"poseA": "point_up", "poseB": "stand"}),
   ("solo", "You get to live his day, just to feel what it's like.", {"pose": "stand"}),
   ("walk", "You wake up early, and somehow you actually want to.", {"x0": 0.3, "x1": 0.65, "face": "happy"}),
   ("solo", "His body is strong, because he kept the promises you keep breaking.", {"pose": "celebrate", "face": "happy"}),
   ("two", "His people respect him, because he stopped abandoning himself.", {"poseA": "stand", "poseB": "wave", "faceB": "happy"}),
   ("solo", "And slowly, the terrifying truth sinks in.", {"pose": "think"}),
   ("solo", "He's not more talented than you. He didn't get luckier.", {"pose": "stand"}),
   ("two", "He just did the small, boring, scary things you keep putting off.", {"poseA": "stand", "poseB": "reach"}),
   ("solo", "Here's the secret. You don't have to wake up as him.", {"pose": "reach"}),
   ("stars", "You just have to do one thing today that he would do.", {}),
   ("cta", "What's the one thing the winning you would do today? Commit to it below.", {}),
 ]),
 ("12_empty_seat", "She Left One Seat Empty on Every Bus", "The Twist", [
   ("hook", "Every day, on a packed bus, she kept the seat beside her empty.", {}),
   ("bus", "No bag on it. No excuse. She'd just rest her hand on the cushion.", {"face": "neutral"}),
   ("bus", "Strangers stood, crammed together. Still, she guarded that one seat.", {"face": "neutral"}),
   ("solo", "People assumed she was rude. Or strange. Or waiting for someone.", {"pose": "stand"}),
   ("two", "One evening, a tired old man asked if he could finally sit.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
   ("bus", "She smiled, and quietly said, of course.", {"face": "sad"}),
   ("solo", "As he sat down, he noticed her eyes were wet.", {"pose": "stand", "face": "sad"}),
   ("two", "My husband and I rode this bus for thirty years, she said.", {"poseA": "stand", "poseB": "sit", "colorB": "muted"}),
   ("bus", "That was his seat. For a year, I couldn't let anyone take it.", {"face": "sad"}),
   ("solo", "But he'd hate that I ride alone. He always said, make room for people.", {"pose": "stand"}),
   ("bus", "From then on, she offered the seat to whoever needed it most.", {"two": True, "faceA": "happy", "faceB": "neutral"}),
   ("solo", "And every time someone sat down, it felt a little like he was still there.", {"pose": "stand", "face": "happy"}),
   ("stars", "Grief is just love with nowhere to go. So she gave it somewhere.", {}),
   ("cta", "Who would you keep a seat for? Tell me about them below.", {}),
 ]),
 ("13_stayed_home", "There's a You That Stayed Home. Is He Happier?", "The Other You", [
   ("hook", "Somewhere, there's a version of you who never left home.", {}),
   ("split", "Who didn't take the leap. Who stayed where it was safe.", {}),
   ("two", "No big move. No risky dream. Just the same familiar street.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
   ("solo", "And some nights, you wonder if he's happier than you.", {"pose": "think"}),
   ("two", "He sees his family every Sunday. He knows the cashier by name.", {"poseA": "wave", "poseB": "wave", "faceA": "happy"}),
   ("walk", "While you chased something out there, he built something deep, right here.", {"x0": 0.3, "x1": 0.7}),
   ("solo", "But here's what the daydream conveniently leaves out.", {"pose": "think"}),
   ("two", "He lies awake too. Wondering about the you that actually left.", {"poseA": "stand", "poseB": "stand", "colorB": "muted", "faceA": "sad"}),
   ("solo", "About the cities you've seen. The person you became out there.", {"pose": "look_up"}),
   ("two", "Neither of you is the wrong answer. You just paid different prices.", {"poseA": "stand", "poseB": "stand"}),
   ("solo", "He traded adventure for roots. You traded roots for the unknown.", {"pose": "stand"}),
   ("stars", "The grass isn't greener on the other side. It's greener where you water it.", {}),
   ("solo", "So stop envying the life you didn't pick. Start living the one you did.", {"pose": "reach", "face": "happy"}),
   ("cta", "Stayed, or left? Tell me which 'you' you became below.", {}),
 ]),
 ("14_unlived_futures", "What If You Remembered Every Future You'll Never Live?", "What If…", [
   ("hook", "What if, for one second, you remembered every future you'll never live?", {}),
   ("split", "The you who moved abroad. Who said yes. Who picked up the phone.", {}),
   ("crowd", "Thousands of yous, fanning out from every choice you ever made.", {}),
   ("two", "The you who stayed in that city. The you who became an artist.", {"poseA": "stand", "poseB": "celebrate", "faceB": "happy"}),
   ("label_above", "Each one a whole life. Vivid. Real. Just… not chosen.", {"text": "∞", "color": "accent"}),
   ("solo", "For one breath, you feel all of them at once.", {"pose": "look_up"}),
   ("solo", "The love you walked away from. The dream you let go of quietly.", {"pose": "stand", "face": "sad"}),
   ("solo", "It's almost too heavy to hold.", {"pose": "think", "face": "sad"}),
   ("solo", "But then, finally, you understand why you can only live one.", {"pose": "think"}),
   ("solo", "If every path stayed open forever, none of them would mean anything.", {"pose": "stand"}),
   ("two", "Choosing is what makes a life yours, instead of everyone's.", {"poseA": "stand", "poseB": "stand"}),
   ("solo", "Every no is the price of a real, solid yes.", {"pose": "reach"}),
   ("stars", "The futures you'll never live aren't losses. They're the cost of being here.", {}),
   ("cta", "Which 'almost' life do you think about most? I'm reading every reply.", {}),
 ]),
]


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    print("Generating launch batch ->", OUT)
    total = 0
    for slug, title, playlist, beats in STORIES:
        s, n = make_story(slug, title, playlist, beats)
        total += n
        print(f"  {s}.json  ({n} scenes)  [{playlist}]  {title}")
    print(f"\n{len(STORIES)} stories, {total} scenes. Render with:")
    print("  for f in stories/0*_*.json stories/1*_*.json; do python -m faceless build \"$f\"; done")
