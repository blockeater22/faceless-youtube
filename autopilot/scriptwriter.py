"""Turn a topic brief into a full video script (title + hook + beats).

Two backends:
  - "claude": Anthropic API writes a fresh, high-quality script each run
             (recommended; needs ANTHROPIC_API_KEY).
  - "offline": a templated fallback so the pipeline still runs with no API key
             (lower quality — fine for a private review queue, not for auto-public).
"auto" uses claude when a key + the SDK are available, else offline.
"""
from __future__ import annotations

import json
import os

ALLOWED_TEMPLATES = [
    "hook", "solo", "two", "crowd", "walk", "stars",
    "celebrate", "split", "label_above", "point", "compare", "chapter", "cta",
]
ALLOWED_POSES = ["stand", "think", "look_up", "point_up", "reach", "wave", "shrug", "celebrate"]
ALLOWED_FACES = ["neutral", "happy", "sad", "surprised"]

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "hook": {"type": "string"},
        "beats": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "template": {"type": "string", "enum": ALLOWED_TEMPLATES},
                    "narration": {"type": "string"},
                    "pose": {"type": "string"},
                    "face": {"type": "string"},
                    "text": {"type": "string"},
                    "num": {"type": "string"},
                    "ctitle": {"type": "string"},
                    "dir": {"type": "string"},
                },
                "required": ["template", "narration"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "hook", "beats"],
    "additionalProperties": False,
}

SYSTEM = """You write scripts for "Inklings" — a YouTube channel of hand-drawn, \
black-background stick-figure videos about the mind, meaning, time, and the quietly \
mind-bending. The voice is calm, warm, and emotionally resonant; second person; plain \
language; short sentences that each land on their own. No emojis, no hashtags, no stage \
directions inside the narration.

You output a single JSON object: {title, hook, beats}.
- title: one clickable line (curiosity or emotion), ideally under 60 characters.
- hook: a 3-6 word on-screen teaser (it will be shown in capitals at the very start).
- beats: an ordered list of 46-56 beats. Each beat is ONE or TWO spoken sentences \
(the `narration`) plus a `template` that controls the visuals.

Templates (use a varied rhythm; most beats are "solo"):
- hook: the very FIRST beat — a punchy opening line.
- solo: one figure, the default.
- two: two figures (a comparison, a conversation, two people).
- crowd: many small figures (a street, a group, humanity).
- walk: the figure walks across (movement, time passing, leaving).
- stars: the figure looks up at a starfield (awe, cosmos, the big zoom-out).
- celebrate: the figure celebrates (a win, relief, a hopeful turn).
- split: the figure splits into two (parallel selves, an inner divide).
- point: the figure points (calling something out).
- label_above: floats a SHORT symbol/word above the figure — set `text` to it \
(e.g. "?", a number like "10?", an "∞", or a single word).
- compare: a smaller/older self beside the main figure.
- chapter: a clean title card — set `num` ("1".."6") and `ctitle` (2-3 WORDS, uppercase). \
Use chapter cards ONLY for how-to / list videos to mark each step.
- cta: the very LAST beat — ask the viewer a warm question, then a soft nudge to subscribe.

Optional per-beat fields: `pose` (one of: stand, think, look_up, point_up, reach, wave, \
shrug, celebrate) and `face` (one of: neutral, happy, sad, surprised) — choose them to \
match the emotion of the line. For `point` you may set `dir` to "l" or "r".

Rules: start with exactly one `hook` beat and end with exactly one `cta` beat. Keep \
narration tight and specific; avoid clichés and filler. Do not number sentences except \
inside chapter cards. Make it feel like one flowing piece with a real beginning, middle, \
and a turn near the end."""


def _user_prompt(topic: dict) -> str:
    kind = topic["kind"]
    extra = ""
    if kind == "howto":
        extra = ("\nThis is a how-to video: open by naming the feeling, then give "
                 "4-6 clear, psychology-backed shifts. Mark each shift with a `chapter` "
                 "beat (num + a 2-3 word uppercase ctitle), then 2-4 solo/two beats "
                 "explaining it. End on an empowering line, then the cta.")
    elif kind == "whatif":
        extra = ("\nThis is a 'what if' video: open on the premise, build the world, "
                 "then turn it into something the viewer feels about their own life. "
                 "No chapter cards — keep it a flowing narrative.")
    elif kind == "otheryou":
        extra = ("\nThis is a 'parallel self' video: make the other version vivid and "
                 "specific, then make it a direction the viewer can move toward. "
                 "No chapter cards.")
    else:
        extra = "\nThis is a reflective piece. No chapter cards — flowing narrative."
    return (f"Write the script.\nTopic / brief: {topic['brief']}\n"
            f"Playlist: {topic['playlist']}\nTarget length: 5-7 minutes (46-56 beats)."
            f"{extra}\nReturn ONLY the JSON object.")


def _via_claude(topic: dict, model: str) -> dict:
    import anthropic  # lazy import
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    resp = client.messages.create(
        model=model,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": _user_prompt(topic)}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(text)


# --------------------------------------------------------------------------- #
# Offline fallback — coherent but generic; recommend the Claude backend.
# --------------------------------------------------------------------------- #
def _offline(topic: dict) -> dict:
    brief = topic["brief"].rstrip("?.")
    title = topic["brief"] if topic["brief"].endswith("?") else topic["brief"]
    beats = [{"template": "hook", "narration": f"{brief}?", "face": "neutral"}]
    body = [
        ("solo", f"Sit with that for a second. {brief}.", "think"),
        ("solo", "It sounds small. But follow it, and it changes how today feels.", "stand"),
        ("crowd", "We move through our days mostly on autopilot, barely noticing.", None),
        ("solo", "And the quiet truths are the ones we skip right past.", "stand"),
        ("two", "Think of someone close to you. Picture them clearly.", "stand"),
        ("solo", "Now think of how rarely you really stop and look.", "sad"),
        ("walk", "Time keeps moving whether or not you're paying attention.", "neutral"),
        ("stars", "Zoom out far enough and the small worries go quiet.", None),
        ("solo", "Zoom back in, and what's left is what actually matters.", "stand"),
        ("split", "There's a version of you that already lives this way.", None),
        ("solo", "Calmer. Kinder to themselves. More awake to the moment.", "neutral"),
        ("celebrate", "And the gap between you and them is just a handful of choices.", None),
        ("solo", "You don't have to fix everything tonight.", "stand"),
        ("solo", "You just have to notice a little more than you did yesterday.", "stand"),
        ("stars", "Because you only get so many ordinary days. And they're not ordinary at all.", None),
    ]
    for tmpl, line, face in body * 2:  # repeat to reach a few minutes
        beat = {"template": tmpl, "narration": line}
        if face:
            beat["face"] = face
        beats.append(beat)
    beats.append({"template": "cta",
                  "narration": "What did this stir up for you? Tell me below — "
                               "and subscribe for more quiet thoughts like this.",
                  "face": "happy"})
    return {"title": title, "hook": brief[:34], "beats": beats}


def _sanitize(script: dict) -> dict:
    beats = []
    for b in script.get("beats", []):
        if not isinstance(b, dict) or not b.get("narration"):
            continue
        t = b.get("template", "solo")
        if t not in ALLOWED_TEMPLATES:
            t = "solo"
        clean = {"template": t, "narration": b["narration"].strip()}
        for k in ("pose", "face", "text", "num", "ctitle", "dir"):
            if b.get(k):
                clean[k] = b[k]
        beats.append(clean)
    if not beats:
        raise ValueError("script had no usable beats")
    if beats[0]["template"] != "hook":
        beats.insert(0, {"template": "hook", "narration": beats[0]["narration"]})
    if beats[-1]["template"] != "cta":
        beats.append({"template": "cta",
                      "narration": "What did this stir up for you? Tell me below, "
                                   "and subscribe for more.", "face": "happy"})
    return {"title": script.get("title", "").strip() or script.get("hook", "Untitled"),
            "hook": (script.get("hook") or script["title"])[:40],
            "beats": beats}


def write_script(topic: dict, backend: str = "auto", model: str = "claude-opus-4-8") -> dict:
    """Return {title, hook, beats}. Tries Claude, falls back to offline."""
    use_claude = backend == "claude" or (
        backend == "auto" and os.environ.get("ANTHROPIC_API_KEY"))
    if use_claude:
        try:
            return _sanitize(_via_claude(topic, model))
        except Exception as exc:  # noqa: BLE001
            if backend == "claude":
                raise
            print(f"  [scriptwriter] claude unavailable ({exc}); using offline fallback")
    return _sanitize(_offline(topic))
