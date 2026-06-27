#!/usr/bin/env python3
"""Auto-direction: turn a line of narration into screen *acting*.

Storytelling channels don't just show a stick figure read a sentence — the
character *reacts* (a worried brow, a surprised gasp, a proud grin) and a small,
relatable, colourful prop pops in to anchor the idea (a phone, a clock, a heart,
a laptop...). This module derives both from the narration text so every scene
across the long-form and Shorts pipelines feels acted and illustrated, not flat.

Two public helpers:
  * ``infer_face(text)``  -> an emotion name understood by figures._draw_face
  * ``infer_prop(text, idx)`` -> a ready-to-render colourful prop dict, or None

Both are pure and keyword-driven, so they're deterministic and easy to test.
"""
from __future__ import annotations

# Bright, saturated, high-contrast prop palette (cycled for variety so the set
# feels "infinitely colourful" rather than one accent colour everywhere).
BRIGHT = ["#ff5d5d", "#1f9bff", "#ffb454", "#23b26d", "#a463f2",
          "#ff7ac0", "#ffd23f", "#2dd4bf", "#fb7185", "#60a5fa"]


def pick_color(i: int) -> str:
    return BRIGHT[i % len(BRIGHT)]


# --------------------------------------------------------------------------- #
# Emotion inference  (checked in priority order; first category that hits wins)
# --------------------------------------------------------------------------- #
_FACE_RULES: list[tuple[str, tuple[str, ...]]] = [
    # The wider mouth library - placed first so explicit cues win
    ("laughing", ("laugh", "laughing", "hilarious", "burst out", "lol",
                  "couldn't stop laughing")),
    ("crying",   ("cry", "crying", "tears", "sobbing", "broke down")),
    ("shocked",  ("can't believe", "no way", "what?!", "gasp", "stunned",
                  "speechless")),
    ("smug",     ("told you so", "knew it", "called it", "smug", "i was right",
                  "as predicted")),
    ("grit",     ("clench", "grit", "force yourself", "push through", "white-knuckle",
                  "determined")),
    ("surprised", (
        "shock", "suddenly", "realize", "realise", "secret", "secretly", "truth",
        "plot twist", "surprising", "crazy", "wild", "what if", "wait", "turns out",
        "imagine", "didn't know", "without you", "without asking", "never noticed",
        "you won't believe", "here's the catch", "but actually", "watch this",
    )),
    ("angry", (
        "angry", "anger", "rage", "unfair", "hate", "furious", "frustrat",
        "resent", "betray", "sick of", "fed up", "enough is enough",
    )),
    ("sad", (
        "alone", "lonely", "lost", "lose", "losing", "fail", "failure", "pain",
        "painful", "hurt", "cry", "behind", "stuck", "regret", "afraid", "fear",
        "scared", "nobody", "empty", "tired", "exhausted", "burnout", "burned out",
        "died", "death", " die", "rock bottom", "worst", "broke", "broken", "grief",
        "miss", "missing", "disappear", "forgotten", "forget", "numb", "anxiety",
        "anxious", "depress", "struggle", "suffer", "trapped", "drain", "give up",
        "can't", "never enough", "not enough", "falling apart",
    )),
    ("happy", (
        "love", "loved", "happy", "joy", "win", "won", "celebrate", "smile",
        "free", "freedom", "grow", "growth", "better", "proud", "hope", "hopeful",
        "grateful", "gratitude", "success", "succeed", "achieve", "peace", "calm",
        "worth", "enough", "heal", "healed", "bright", "thrive", "confident",
        "finally", "you've got this", "celebrate you",
    )),
    ("think", (
        "why", "question", "wonder", "consider", "think", "thinking", "decision",
        "decide", "choice", "choose", "ask", "notice", "maybe", "how", "reason",
        "because", "what makes", "ever wonder", "the trick", "the answer",
    )),
]


def infer_face(text: str, default: str = "neutral") -> str:
    t = " " + (text or "").lower() + " "
    for face, words in _FACE_RULES:
        if any(w in t for w in words):
            return face
    return default


# --------------------------------------------------------------------------- #
# Body-language / pose inference  (so the character ACTS the specific sentence
# instead of holding a generic pose - first category that hits wins)
# --------------------------------------------------------------------------- #
_POSE_RULES: list[tuple[str, tuple[str, ...]]] = [
    # specific ref-image gestures first (most expressive wins on a match)
    ("hold_box",   ("holding", "carrying", "load", "weight", "baggage", "burden")),
    ("crossed",    ("defensive", "guarded", "stubborn", "not buying", "skeptical",
                    "arms crossed", "shut down")),
    ("hips",       ("confident", "ready", "stand your ground", "fed up",
                    "had enough", "drawing a line")),
    ("facepalm",   ("regret", "embarrass", "embarrassed", "cringe", "oh no",
                    "can't believe", "facepalm")),
    ("look_around",("searching", "looking for", "where is", "scanning",
                    "watching out", "on alert")),
    ("cheer",      ("celebrate", "winning", "amazing", "yes!", "did it",
                    "we did it", "best news")),
    ("celebrate", ("win", "won", "free", "freedom", "finally", "proud", "relief",
                   "relieved", "let it go", "go home", "lighter")),
    ("walk_a", ("busy", "rushing", "rush", "walk", "running", "run ", "moving",
                "leave", "leaving", "walked away", "passes", "passing", "go about")),
    ("look_up", ("audience", "watching", "watch", "stage", "spotlight", "crowd",
                 "stares", "everyone is looking", "the whole room", "courtroom")),
    ("arms_up", ("bigger", "huge", "whole room", "entire", "grows", "grow",
                 "expands", "everything", "the world", "blown up", "all of it")),
    ("point_r", ("they", "them", "others", "other people", "grade", "grading",
                 "judge", "judging", "blame", "point", "everyone else")),
    ("reach", ("send", "give", "offer", "reach", "hand", "drop", "share", "hold",
               "care", "reaching", "let the")),
    ("sit", ("rest", "relax", "calm down", "sit", "settle", "finally rest",
             "breathe", "at peace", "wind down")),
    ("think", ("think", "thinking", "wonder", "replay", "rehears", "analyz",
               "process", "figure out", "in your head", "your mind", "your brain")),
    ("shrug", ("not weakness", "isn't weakness", "not fake", "pretend", "pretending",
               "you're fine", "don't know", "not sure", "unsure", "shrug", "nothing")),
]


def infer_pose(text: str, default: str = "stand") -> str:
    """Pick a body pose that matches the sentence's meaning."""
    t = " " + (text or "").lower() + " "
    for pose, words in _POSE_RULES:
        if any(w in t for w in words):
            return pose
    return default


# --------------------------------------------------------------------------- #
# Relatable prop inference
# --------------------------------------------------------------------------- #
# (keywords, kind, name, semantic_color_or_None).  First match wins, so order
# the more specific / evocative triggers first.
_PROP_RULES: list[tuple[tuple[str, ...], str, str, str | None]] = [
    (("phone", "texting", "text message", "scroll", "scrolling", "app", "feed",
      "social media", "dm", "online", "notification", "screen time", "instagram",
      "doomscroll", "message", "wording", "sending", "reputation", "comma",
      "reply", "conversation"), "icon", "chat", "#1f9bff"),
    (("trial", "court", "courtroom", "judge", "judging", "judged", "grade",
      "grading", "jury", "verdict", "on trial", "criticize", "criticise"),
     "icon", "warning", "#ff5d5d"),
    (("audience", "watching", "watched", "stares", "staring", "spotlight",
      "everyone is looking", "on display", "being seen", "all eyes"),
     "icon", "eye", "#1f9bff"),
    (("drain", "drains", "draining", "energy", "exhaust", "exhausted", "battery",
      "running low", "depleted", "worn out", "costs energy"),
     "icon", "battery", "#23b26d"),
    (("mask", "pretend", "pretending", "perform", "performs", "performing",
      "fake smile", "putting on", "put on a face", "painted smile", "faking"),
     "icon", "mask", "#a463f2"),
    (("love", "relationship", "heart", "romance", "connection", "connect",
      "lonely", "alone", "friend", "friendship", "intimacy", "belong"),
     "icon", "heart", "#ff5d5d"),
    (("idea", "realize", "realise", "insight", "lesson", "learned", "clarity",
      "epiphany", "aha", "understand", "figure out", "solution", "honest",
      "truth", "the truth", "real answer", "honestly"),
     "icon", "lightbulb", "#ffd23f"),
    (("brain", "mind", "mental", "psychology", "psycholog", "thought", "thoughts",
      "overthink", "subconscious", "cognitive", "rehears", "replay", "rumination",
      "in your head", "your head"), "icon", "brain", "#a463f2"),
    (("warning", "danger", "mistake", "trap", "wrong", "risk", "toxic", "avoid",
      "red flag", "careful", "beware"), "icon", "warning", "#ffb454"),
    (("win", "success", "succeed", "achieve", "goal", "best", "proud", "reward",
      "trophy", "champion", "shine"), "icon", "star", "#ffd23f"),
    (("rise", "rising", "growth", "increase", "improve", "higher", "level up",
      "more energy", "go up", "soar"), "icon", "arrow_up", "#23b26d"),
    (("fall", "falling", "drop", "decline", "lower", "sink", "spiral down",
      "go down", "crash", "plummet"), "icon", "arrow_down", "#ff5d5d"),
    (("time", "clock", "hour", "minute", "late", "someday", "today", "tomorrow",
      "deadline", "running out", "too late", "years pass"), "icon", "clock", "#2dd4bf"),
    (("done", "correct", "agree", "checklist", "accomplish", "finished",
      "got it right", "yes"), "icon", "check", "#23b26d"),
    # multi-colour scenery objects (kept at their own designed palettes -> color None)
    (("work", "job", "career", "laptop", "productive", "productivity", "office",
      "email", "hustle"), "object", "laptop", None),
    (("sleep", "bed", "tired", "exhausted", "couch", "comfort", "comfortable",
      "relax", "cozy", "rest", "lazy"), "object", "armchair", None),
    (("book", "read", "study", "knowledge", "learn"), "object", "books", None),
    (("coffee", "morning", "mug", "tea", "cafe"), "object", "mug", None),
    (("door", "leave", "exit", "opportunity", "escape", "walk away", "new chapter",
      "fresh start"), "object", "door", None),
    (("warm", "blanket", "cold", "winter", "safe", "secure", "soothe"),
     "object", "blanket", None),
]


def _popkeys(pos: list[float]) -> list[dict]:
    """Lively pop-in -> settle -> tiny drift, for a storytelling feel."""
    return [
        {"t": 0.0, "pos": pos, "scale": 0.5, "alpha": 0.0},
        {"t": 0.16, "pos": pos, "scale": 1.08, "alpha": 1.0, "ease": "pop"},
        {"t": 0.6, "pos": pos, "scale": 1.0, "alpha": 1.0},
        {"t": 1.0, "pos": pos, "scale": 1.03, "alpha": 1.0},
    ]


def make_prop(kind: str, name: str, color: str | None, idx: int,
              side: str | None = None) -> dict:
    """Build a ready-to-render prop dict (pop-in, upper-corner, colour-cycled)."""
    if side is None:
        side = "r" if idx % 2 == 0 else "l"
    x = 0.81 if side == "r" else 0.19
    pos = [x, 0.27]
    if kind == "object":
        prop = {"type": "object", "id": f"dp{idx}", "name": name,
                "size": 0.26, "front": True, "keys": _popkeys(pos)}
        if color:
            prop["color"] = color
    else:
        prop = {"type": "icon", "id": f"dp{idx}", "name": name,
                "color": color or pick_color(idx), "r": 0.094,
                "front": True, "keys": _popkeys(pos)}
    return prop


def infer_prop(text: str, idx: int, side: str | None = None) -> dict | None:
    """Pick a relatable colourful prop for this line, or None if nothing fits."""
    t = " " + (text or "").lower() + " "
    for words, kind, name, color in _PROP_RULES:
        if any(w in t for w in words):
            # icons cycle the bright palette for variety unless a semantic
            # colour reads stronger; objects keep their own designed palette.
            col = color if (kind == "icon") else color
            return make_prop(kind, name, col, idx, side)
    return None


if __name__ == "__main__":  # quick self-check
    samples = [
        "Your brain makes thousands of decisions without asking you.",
        "You feel completely alone even in a crowd.",
        "Texting quietly replaced actually visiting people.",
        "Finally, you win back your own time.",
        "Why do smart people procrastinate so much?",
        "Comfort is secretly the enemy of growth.",
    ]
    for i, s in enumerate(samples):
        p = infer_prop(s, i)
        pn = f"{p['type']}:{p['name']}" if p else "-"
        print(f"{infer_face(s):10s} {pn:16s} | {s}")
