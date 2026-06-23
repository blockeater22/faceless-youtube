"""Turn a topic brief into a full video script (title + hook + beats).

Three backends:
  - "claude_code": run the Claude Code CLI headless, authenticated by a Claude
        Pro/Max **subscription** token (CLAUDE_CODE_OAUTH_TOKEN from
        `claude setup-token`). No metered API charges. Recommended.
  - "claude": the Anthropic **API** (needs ANTHROPIC_API_KEY — pay per token).
  - "offline": a templated fallback so the pipeline still runs with no Claude at
        all (lower quality — fine for a private review queue, not auto-public).
"auto" prefers claude_code (if the CLI + token are present), then the API key,
then offline.
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
                    "icon": {"type": "string"},
                    "poseA": {"type": "string"},
                    "poseB": {"type": "string"},
                    "faceA": {"type": "string"},
                    "faceB": {"type": "string"},
                    "colorB": {"type": "string"},
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
- beats: an ordered list of beats — YOU pick the length that best fits the topic and what's \
trending: a tight, punchy piece (~26-38 beats, ~3-5 min) for high-curiosity hooks, or a fuller \
piece (~46-58 beats, ~6-8 min) for rich, emotional, or how-to topics. Each beat is ONE or TWO spoken sentences \
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
and a turn near the end.

ILLUSTRATE every line — never just narrate over a standing figure:
- For anything between people (someone hurt, grateful, ignored, comforted) use template \
"two" with poseA/poseB + faceA/faceB and set colorB to "muted" for the other person \
(hurt friend: poseB "stand", faceB "sad"; grateful: poseB "wave", faceB "happy").
- When a line is about an object, feeling, or concept, set `icon` to ONE of: heart, speech, \
thought, cloud, rain, door, phone, sun, moon, star, clock, gift, spiral, bulb, eye \
(heart=love/warmth, spiral=overthinking, door=a choice, phone=connection, bulb=a realization, \
rain=sadness, star=wonder, clock=time, gift=giving, eye=noticing/being seen).
- Always give the figure a pose + face that matches the emotion. A neutral figure with no \
icon and no second person should be rare."""


def _user_prompt(topic: dict, trends: list | None = None, mode: str = "long") -> str:
    kind = topic["kind"]
    trend_block = ""
    if trends:
        joined = "\n".join(f"- {t}" for t in trends[:12])
        trend_block = ("\n\nWhat's getting views in this niche right now — use ONLY as "
                       "inspiration for angle, curiosity, and title energy; do NOT copy a "
                       f"title and do NOT drift off-brand:\n{joined}")

    if mode == "short":
        directive = (
            "\nFORMAT: a vertical YouTube SHORT — the channel's growth engine. Write 12-18 "
            "beats, about 35-55 seconds total. The FIRST beat must be an instant, "
            "scroll-stopping hook (a bold claim or a sharp question) with NO warm-up. Keep "
            "ONE tight idea, fast and punchy; one short sentence per beat; no chapter cards. "
            "End on a line that makes them rewatch or comment. Still illustrate every line "
            "(icons / two-figure interactions).")
    else:
        longx = {
            "howto": ("\nThis is a how-to video: name the feeling, then 4-6 psychology-backed "
                      "shifts, each marked with a `chapter` beat (num + 2-3 word uppercase "
                      "ctitle) then 2-4 explaining beats. End empowering, then the cta."),
            "whatif": ("\nThis is a 'what if' video: open on the premise, build the world, then "
                       "turn it into something the viewer feels. No chapter cards."),
            "otheryou": ("\nThis is a 'parallel self' video: make the other version vivid and "
                         "specific, then a direction the viewer can move toward. No chapter cards."),
        }.get(kind, "\nThis is a reflective piece. No chapter cards — flowing narrative.")
        directive = longx + ("\nChoose the ideal length yourself (tight 3-5 min or fuller "
                             "6-8 min — see the system instructions).")

    return (f"Write the script.\nTopic / brief: {topic['brief']}\n"
            f"Playlist: {topic['playlist']}.{trend_block}{directive}\n"
            "Return ONLY the JSON object.")


def _via_claude(topic: dict, model: str, trends: list | None = None, mode: str = "long") -> dict:
    import anthropic  # lazy import
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    resp = client.messages.create(
        model=model,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": _user_prompt(topic, trends, mode)}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(text)


def _extract_json(text: str) -> str:
    """Pull the first balanced {...} object out of CLI output (tolerates fences/prose)."""
    t = text.strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) >= 2:
            t = parts[1]
            if t.lstrip().lower().startswith("json"):
                t = t.lstrip()[4:]
    start = t.find("{")
    if start == -1:
        raise ValueError("no JSON object in Claude Code output")
    depth = 0
    for i in range(start, len(t)):
        if t[i] == "{":
            depth += 1
        elif t[i] == "}":
            depth -= 1
            if depth == 0:
                return t[start:i + 1]
    raise ValueError("unbalanced JSON in Claude Code output")


def _via_claude_code(topic: dict, trends: list | None = None, mode: str = "long") -> dict:
    """Generate the script by running the Claude Code CLI headless, billed to a
    Claude Pro/Max subscription (CLAUDE_CODE_OAUTH_TOKEN). No metered API."""
    import shutil
    import subprocess
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("claude CLI not found (npm install -g @anthropic-ai/claude-code)")
    prompt = (SYSTEM + "\n\n" + _user_prompt(topic, trends, mode) +
              "\n\nOutput ONLY the raw JSON object described above — no markdown "
              "fences, no commentary, no tool use.")
    proc = subprocess.run([exe, "-p", prompt], capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI exited {proc.returncode}: {proc.stderr.strip()[-400:]}")
    return json.loads(_extract_json(proc.stdout))


# --------------------------------------------------------------------------- #
# Offline fallback — coherent but generic; recommend a Claude backend.
# --------------------------------------------------------------------------- #
def _offline(topic: dict, mode: str = "long") -> dict:
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
    for tmpl, line, face in (body[:10] if mode == "short" else body * 2):
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
        for k in ("pose", "face", "text", "num", "ctitle", "dir",
                  "icon", "poseA", "poseB", "faceA", "faceB", "colorB"):
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


def write_script(topic: dict, backend: str = "auto", model: str = "claude-opus-4-8",
                 trends: list | None = None, mode: str = "long") -> dict:
    """Return {title, hook, beats}. Tries backends in order, ending at offline."""
    import shutil
    has_cc = bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")) and bool(shutil.which("claude"))
    has_api = bool(os.environ.get("ANTHROPIC_API_KEY"))

    if backend == "claude_code":
        order = ["cc"]
    elif backend == "claude":
        order = ["api"]
    elif backend == "offline":
        order = ["offline"]
    else:  # auto
        order = ([("cc")] if has_cc else []) + (["api"] if has_api else []) + ["offline"]

    last_exc = None
    for b in order:
        try:
            if b == "cc":
                return _sanitize(_via_claude_code(topic, trends, mode))
            if b == "api":
                return _sanitize(_via_claude(topic, model, trends, mode))
            return _sanitize(_offline(topic, mode))
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            print(f"  [scriptwriter] backend '{b}' failed ({exc}); trying next")
    raise last_exc  # only reached if an explicit non-offline backend failed
