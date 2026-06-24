"""Turn a topic brief into a full video script (title + hook + beats).

Backends:
  - "gemini": Google's Gemini API on a **free** key (GEMINI_API_KEY or
        GOOGLE_API_KEY from https://aistudio.google.com/apikey). Free tier as of
        2026: gemini-2.5-flash ~10 req/min, 250 req/day — plenty for a couple of
        videos a day. Default when a Gemini key is present.
  - "claude_code": run the Claude Code CLI headless, authenticated by a Claude
        Pro/Max **subscription** token (CLAUDE_CODE_OAUTH_TOKEN from
        `claude setup-token`). No metered API charges.
  - "claude": the Anthropic **API** (needs ANTHROPIC_API_KEY — pay per token).
  - "offline": a templated fallback so the pipeline still runs with no LLM at
        all (lower quality — fine for a private review queue, not auto-public).
"auto" prefers gemini (free key), then claude_code, then the Anthropic API key,
then offline.
"""
from __future__ import annotations

import json
import os

from autopilot import gemini_pool

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
        "thumbnail_text": {"type": "string"},
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
                    "image_prompt": {"type": "string"},
                    "negative_prompt": {"type": "string"},
                    "visual_style": {"type": "string"},
                    "visual_effect": {"type": "string"},
                    "scene_type": {"type": "string"},
                    "duration_hint": {"type": "number"},
                    "caption_emphasis": {"type": "string"},
                },
                "required": ["template", "narration"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "hook", "beats"],
    "additionalProperties": False,
}

DEFAULT_PERSONA = (
    "Inklings — hand-drawn, black-background stick-figure videos about the mind, meaning, "
    "time, and the quietly mind-bending. The voice is calm, warm, and emotionally resonant; "
    "second person; plain language; short sentences that each land on their own."
)

# Retention craft distilled from how top faceless/stick-figure channels open and hold
# viewers (front-loaded hooks, open loops, pattern interrupts, mid-roll engagement).
RETENTION_BLOCK = """RETENTION — write for the first 30 seconds and for watch-time:
- The `hook` beat must create instant tension or curiosity in the first 1-3 seconds: a bold \
claim, a vivid question, a stake, or a result. Never open with "Hey", a greeting, channel \
branding, or slow setup. Lead with the most interesting idea, not the context.
- Use a proven hook shape: forbidden truth ("No one tells you this..."), personal stake \
("This is why you keep..."), impossible contrast ("The laziest habit that..."), or visible \
object mystery ("Your phone is training you to..."). The first line must feel like a secret \
the viewer cannot skip.
- Beat 2-3 must pay a tiny bit of that curiosity off AND open a bigger loop (promise what's \
coming) so they stay: e.g. "But the strange part comes later."
- Include 3-5 DISTINCT curiosity hooks across the whole video (a fresh loop roughly every \
20-30 seconds, or for shorts every 2-3 beats): re-hook lines like "Here's where it gets \
weird", "But there's a catch", "Now watch what happens". Never let curiosity flatline.
- Keep an open loop running at all times — answer one question while raising the next.
- Keep each beat SHORT so a new visual lands roughly every 2-3 seconds: one short sentence \
per beat is ideal; avoid long paragraphs in a single beat.
- Use pattern interrupts every 1-2 beats: switch template (solo -> two -> crowd -> stars), \
change scale, set a different `face`/`pose`, or drop a `text`/`icon` to make the visuals pop.
- DYNAMIC PROPS: Use `icon` AND `text` heavily! Whenever a beat makes a point, set `text` to \
the 1-2 most important words of that line so they pop up on screen. Or set `icon` to illustrate \
the concept. The screen should feel busy and animated.
- MOTIVATED COLOR/LIGHT: When an object emits or implies energy, set `visual_effect` to \
`glow`, `rays`, or `burst`. Example: phone -> `icon: phone`, `visual_effect: rays` so the \
screen light can reflect toward the face; realization -> bulb + glow; emotional warmth -> \
heart + glow; important keyword -> text + burst. Use `rays` sparingly — only for phones, \
bulbs, sun, or stars. Most beats should have NO visual_effect.
- Vary sentence rhythm: short, short, longer, short. Each beat should make the next feel \
inevitable. Cut filler words ruthlessly.
- Around the emotional turn (roughly 60-75% through), plant ONE soft engagement nudge inside \
the narration — invite a comment or reflection ("Tell me if you've felt this") — woven in, \
not an ad break.
- The final `cta` beat: land the emotional payoff, ask the viewer a warm specific question \
(drives comments), then explicitly ask them to like, share, and subscribe. Example ending: \
"If this helped, like, share it with someone who needs it, and subscribe for more." \
Set `text` to the last punchy keyword (e.g. SUBSCRIBE) and `caption_emphasis` to include \
that word so it pops when spoken. Keep it human, never salesy."""


def build_system(persona: str | None = None, cta_style: str = "warm") -> str:
    persona = (persona or DEFAULT_PERSONA).strip()
    tone = {
        "energetic": "Punchy and motivating; keep momentum high.",
        "calm": "Slow, soothing, lots of breathing room.",
        "warm": "Warm, intimate, emotionally resonant.",
    }.get(cta_style, "Warm, intimate, emotionally resonant.")
    return _SYSTEM_TEMPLATE.format(persona=persona, tone=tone, retention=RETENTION_BLOCK) + _SYSTEM_BODY


# Back-compat default used by older callers/tests.
SYSTEM = None  # set after _SYSTEM_BODY is defined


_SYSTEM_TEMPLATE = """You write scripts for this YouTube channel:
{persona}

Channel tone: {tone}
Always: second person; plain language; no emojis, no hashtags, no stage directions inside \
the narration.

{retention}

You output a single JSON object: {{title, hook, beats}}.
- title: one clickable line (curiosity or emotion), ideally under 60 characters.
- hook: a 3-6 word on-screen teaser (it will be shown in capitals at the very start).
- thumbnail_text: 2-5 words MAX for the YouTube thumbnail — ALL CAPS curiosity gap \
(e.g. "AI OWNS YOUR DREAMS", "STOP DOOMSCROLLING"). Must be different from the title; \
punchy, mobile-readable, no punctuation clutter.
- beats: an ordered list of beats — YOU pick the length that best fits the topic and what's \
trending: a tight, punchy piece (~26-38 beats, ~3-5 min) for high-curiosity hooks, or a fuller \
piece (~46-58 beats, ~6-8 min) for rich, emotional, or how-to topics. Each beat is ONE or TWO spoken sentences \
(the `narration`) plus a `template` that controls stick visuals."""

_SYSTEM_BODY = """

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

Optional per-beat fields:
- `pose` (stand, think, look_up, point_up, reach, wave, shrug, celebrate).
- `face` (neutral, happy, sad, surprised).
- `icon` (heart, speech, thought, cloud, rain, door, phone, sun, moon, star, clock, gift, spiral, bulb, eye).
- `text` (a 1-3 word keyword to float on screen).
- `visual_effect` (glow, rays, burst) to make the icon/keyword visually attractive.

Hybrid AI-image fields are REQUIRED on every beat:
- `image_prompt`: a cinematic image prompt that illustrates the narration without on-image text.
- `negative_prompt`: what to avoid, especially text, logos, celebrity likenesses, gore, nudity, UI screenshots, watermarks.
- `visual_style`: a short shared style phrase that keeps the whole video visually consistent.
- `scene_type`: one of symbolic, environment, object, character, abstract, transition, cta.
- `duration_hint`: estimated spoken duration in seconds for the beat.
- `caption_emphasis`: 1-4 words from the narration that should feel important in captions.

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
- Every 2-3 beats, include one cinematic visual moment where color is motivated by the story: \
screen glow, light rays, heat/warmth, pressure lines, thought cloud, or bright keyword burst.
- Always give the figure a pose + face that matches the emotion. A neutral figure with no \
icon and no second person should be rare."""

SYSTEM = build_system()


def _user_prompt(topic: dict, trends: list | None = None,
                 desired_length: str | None = None) -> str:
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
    trend_block = ""
    if trends:
        joined = "\n".join(f"- {t}" for t in trends[:12])
        trend_block = ("\n\nWhat's getting views in this niche right now — use ONLY as "
                       "inspiration for angle, curiosity, and title energy; do NOT copy a "
                       f"title and do NOT drift off-brand:\n{joined}")
    length = desired_length or topic.get("desired_length") or "auto"
    length_block = (
        "\nDesired length: "
        f"{length}. Beats are SHORT now — each beat is ~3-4 seconds spoken (one short "
        "sentence), so a new visual lands constantly. If this is `shorts`, use 7-10 beats "
        "total (hook + body + cta), target under 55 seconds. If this is `3-5`, use 40-60 "
        "beats. If this is `6-8`, use 70-100 beats. If it is a custom minute target, "
        "estimate ~16-18 beats per minute and pick a beat count to match."
    )
    return (f"Write the script.\nTopic / brief: {topic['brief']}\n"
            f"Playlist: {topic['playlist']}.{extra}{trend_block}\n"
            f"{length_block}\n"
            "Make image prompts concrete, coherent across scenes, and safe for YouTube. "
            "Return ONLY the JSON object.")


def _gemini_key() -> str | None:
    ks = gemini_pool.keys()
    return ks[0].value if ks else None


def _via_gemini(topic: dict, model: str | None = None, trends: list | None = None,
                desired_length: str | None = None, job_id: str | None = None,
                system: str | None = None) -> dict:
    """Generate the script with the Gemini API on a free key.

    Uses the unified `google-genai` SDK (`pip install google-genai`). Falls back
    to the legacy `google-generativeai` SDK if that's what's installed.
    """
    if not gemini_pool.has_key():
        raise RuntimeError("GEMINI_API_KEY not set (get a free key at "
                           "https://aistudio.google.com/apikey)")
    gemini_model = model if (model and str(model).startswith("gemini")) else None
    if not gemini_model:
        gemini_model = os.environ.get("GEMINI_MODEL") or None
    if gemini_model == "gemini-auto":
        gemini_model = None
    prompt = _user_prompt(topic, trends, desired_length)
    return gemini_pool.generate_json(
        prompt,
        system_instruction=system or SYSTEM,
        model=gemini_model,
        temperature=0.72,
        # Rich beat JSON (image prompts + visual effects) can exceed 16k tokens for
        # long videos. Truncation is the main cause of "unbalanced JSON" failures.
        max_output_tokens=32768,
        job_id=job_id or topic.get("brief"),
    )


def _via_claude(topic: dict, model: str, trends: list | None = None,
                desired_length: str | None = None, system: str | None = None) -> dict:
    import anthropic  # lazy import
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    resp = client.messages.create(
        model=model,
        max_tokens=16000,
        system=system or SYSTEM,
        messages=[{"role": "user", "content": _user_prompt(topic, trends, desired_length)}],
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


def _via_claude_code(topic: dict, trends: list | None = None,
                     desired_length: str | None = None, system: str | None = None) -> dict:
    """Generate the script by running the Claude Code CLI headless, billed to a
    Claude Pro/Max subscription (CLAUDE_CODE_OAUTH_TOKEN). No metered API."""
    import shutil
    import subprocess
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("claude CLI not found (npm install -g @anthropic-ai/claude-code)")
    prompt = ((system or SYSTEM) + "\n\n" + _user_prompt(topic, trends, desired_length) +
              "\n\nOutput ONLY the raw JSON object described above — no markdown "
              "fences, no commentary, no tool use.")
    proc = subprocess.run([exe, "-p", prompt], capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI exited {proc.returncode}: {proc.stderr.strip()[-400:]}")
    return json.loads(_extract_json(proc.stdout))


# --------------------------------------------------------------------------- #
# Offline fallback — coherent but generic; recommend a Claude backend.
# --------------------------------------------------------------------------- #
def _offline(topic: dict) -> dict:
    brief = topic["brief"].rstrip("?.")
    short = " ".join(brief.split()[:9])
    title = short if len(short) < 64 else short[:61] + "..."
    beats = [{"template": "hook", "narration": f"What if {short.lower()} was already controlling you?",
              "face": "surprised", "icon": "eye", "text": "LOOK CLOSER", "visual_effect": "burst"}]
    body = [
        ("solo", f"Your brain filters reality before you even notice it.", "think", "eye", "FILTER", None),
        ("solo", "That sounds small, until one hidden bias changes your whole day.", "stand", "spiral", "HIDDEN BIAS", "burst"),
        ("crowd", "Everyone around you is walking through their own invisible filter.", None, "thought", "INVISIBLE", None),
        ("solo", "Here is where it gets strange.", "surprised", "bulb", "STRANGE", "glow"),
        ("two", "Two people can see the same moment and feel opposite truths.", "stand", "speech", "SAME MOMENT", "burst"),
        ("solo", "Your phone does this too, by rewarding only the loudest signals.", "sad", "phone", "LOUD SIGNALS", "rays"),
        ("walk", "So attention becomes a path you keep walking without choosing.", "neutral", "door", "ATTENTION", None),
        ("stars", "But when you see the filter, you get a little space from it.", None, "star", "SPACE", None),
        ("split", "One version of you reacts instantly.", None, "spiral", "REACT", "burst"),
        ("solo", "Another version pauses long enough to ask one better question.", "think", "bulb", "PAUSE", "glow"),
        ("celebrate", "That tiny pause is where better choices begin.", None, "gift", "CHOICE", None),
        ("solo", "You do not need a perfect mind.", "stand", "heart", "GENTLE", None),
        ("solo", "You just need to catch the pattern one second earlier.", "stand", "eye", "ONE SECOND", None),
        ("stars", "Because seeing clearly is not magic. It is practice.", None, "star", "PRACTICE", None),
    ]
    for tmpl, line, face, icon, text, effect in body * 2:  # repeat to reach a few minutes
        beat = {"template": tmpl, "narration": line}
        if face:
            beat["face"] = face
        beat["icon"] = icon
        beat["text"] = text
        if effect:
            beat["visual_effect"] = effect
        beats.append(beat)
    beats.append({"template": "cta",
                  "narration": "What did this stir up for you? Tell me below. "
                               "If this helped, like, share, and subscribe for more.",
                  "face": "happy", "icon": "heart", "text": "SUBSCRIBE",
                  "caption_emphasis": "subscribe, share, like", "visual_effect": "burst"})
    return {"title": title, "hook": brief[:34], "beats": beats}


def _default_image_prompt(narration: str, title: str) -> str:
    line = narration.strip().rstrip(".")
    return (
        "Cinematic symbolic scene for a faceless reflective YouTube video, "
        f"illustrating: {line}. Recurring lonely stick-figure silhouette, dark "
        f"minimal world, topic mood from title: {title}. No text in image."
    )


def _min_beats(desired_length: str | None) -> int:
    length = (desired_length or "auto").lower()
    if length == "shorts":
        return 7
    if length == "3-5":
        return 28
    if length == "6-8":
        return 50
    if length.startswith("about"):
        try:
            mins = float(length.split()[1])
            return max(7, int(mins * 14))
        except (ValueError, IndexError):
            pass
    return 20


def _validate_script_length(script: dict, desired_length: str | None) -> None:
    n = len(script.get("beats", []))
    need = _min_beats(desired_length)
    if n < need:
        raise ValueError(f"script too short ({n} beats, need ~{need} for {desired_length or 'auto'})")


def _enforce_cta(beat: dict) -> dict:
    if beat.get("template") != "cta":
        return beat
    narr = beat.get("narration", "")
    lower = narr.lower()
    if "like" not in lower or "subscribe" not in lower:
        narr = narr.rstrip(".")
        narr += ". If this helped you, hit like, share it with someone who needs it, and subscribe for more."
        beat["narration"] = narr
    if "share" not in narr.lower():
        beat["narration"] = beat["narration"].replace("like,", "like, share,")
    beat.setdefault("text", "SUBSCRIBE")
    beat.setdefault("icon", "heart")
    beat.setdefault("caption_emphasis", "subscribe, share, like")
    if beat.get("visual_effect") == "rays":
        beat["visual_effect"] = "burst"
    return beat


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
                  "icon", "poseA", "poseB", "faceA", "faceB", "colorB",
                  "image_prompt", "negative_prompt", "visual_style",
                  "visual_effect", "scene_type", "duration_hint", "caption_emphasis"):
            if b.get(k):
                clean[k] = b[k]
        if not clean.get("image_prompt"):
            clean["image_prompt"] = _default_image_prompt(
                clean["narration"], script.get("title", script.get("hook", ""))
            )
        clean.setdefault(
            "negative_prompt",
            "text, subtitles, words, logos, watermark, celebrity likeness, gore, nudity",
        )
        clean.setdefault(
            "visual_style",
            "cinematic dark minimal faceless storytelling, muted teal and warm amber",
        )
        clean.setdefault("scene_type", "symbolic")
        clean.setdefault("caption_emphasis", "")
        clean = _enforce_cta(clean)
        beats.append(clean)
    if not beats:
        raise ValueError("script had no usable beats")
    if beats[0]["template"] != "hook":
        beats.insert(0, {"template": "hook", "narration": beats[0]["narration"]})
    if beats[-1]["template"] != "cta":
        beats.append({"template": "cta",
                      "narration": "What did this stir up for you? Tell me below. "
                                   "If this helped, like, share, and subscribe for more.",
                      "face": "happy", "text": "SUBSCRIBE", "icon": "heart",
                      "caption_emphasis": "subscribe, share, like", "visual_effect": "burst"})
    else:
        beats[-1] = _enforce_cta(beats[-1])
    out = {"title": script.get("title", "").strip() or script.get("hook", "Untitled"),
           "hook": (script.get("hook") or script["title"])[:40],
           "beats": beats}
    if script.get("thumbnail_text"):
        out["thumbnail_text"] = str(script["thumbnail_text"]).strip().upper()[:42]
    return out


def write_script(topic: dict, backend: str = "auto", model: str = "claude-opus-4-8",
                 trends: list | None = None, desired_length: str | None = None,
                 job_id: str | None = None, persona: str | None = None,
                 cta_style: str = "warm", gemini_model: str | None = None) -> dict:
    """Return {title, hook, beats}. Tries backends in order, ending at offline."""
    import shutil
    has_gemini = bool(_gemini_key())
    has_cc = bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")) and bool(shutil.which("claude"))
    has_api = bool(os.environ.get("ANTHROPIC_API_KEY"))
    system = build_system(persona, cta_style)

    if backend == "gemini":
        order = ["gemini"]
    elif backend == "claude_code":
        order = ["cc"]
    elif backend == "claude":
        order = ["api"]
    elif backend == "offline":
        order = ["offline"]
    else:  # auto — free Gemini key first, then Claude options, then offline
        order = (["gemini"] if has_gemini else []) + (["cc"] if has_cc else []) \
            + (["api"] if has_api else []) + ["offline"]

    last_exc = None
    for b in order:
        try:
            if b == "gemini":
                script = _sanitize(_via_gemini(
                    topic, gemini_model, trends, desired_length, job_id, system,
                ))
                _validate_script_length(script, desired_length)
                return script
            if b == "cc":
                script = _sanitize(_via_claude_code(topic, trends, desired_length, system))
                _validate_script_length(script, desired_length)
                return script
            if b == "api":
                script = _sanitize(_via_claude(topic, model, trends, desired_length, system))
                _validate_script_length(script, desired_length)
                return script
            return _sanitize(_offline(topic))
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            print(f"  [scriptwriter] backend '{b}' failed ({exc}); trying next")
    raise last_exc  # only reached if an explicit non-offline backend failed
