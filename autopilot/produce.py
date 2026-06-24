"""Produce one finished video from a script: story JSON -> render -> thumbnail
-> metadata. Returns paths + YouTube metadata.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from generate_stories import BASE_STYLE, BASE_VOICE, TEMPLATES, label  # noqa: E402
from autopilot.thumbnail import make_thumbnail  # noqa: E402

STOP = set("a an the to of in on for and or but if is are was were be been being you your "
           "what how why when it its this that these those do does can will with as at".split())

HASHTAGS = {
    "whatif": ["#whatif", "#deepthoughts", "#psychology", "#mindfulness", "#inklings"],
    "howto": ["#selfimprovement", "#psychology", "#mindfulness", "#calm", "#inklings"],
    "otheryou": ["#motivation", "#selfimprovement", "#deepthoughts", "#whatif", "#inklings"],
    "reflection": ["#deepthoughts", "#philosophy", "#mindfulness", "#sonder", "#inklings"],
}
TAG_POOL = {
    "whatif": ["what if", "deep thoughts", "psychology", "mind bending", "philosophy"],
    "howto": ["how to stop overthinking", "self improvement", "anxiety", "mindfulness",
              "mental health", "how to be confident", "psychology"],
    "otheryou": ["the other you", "motivation", "self improvement", "discipline",
                 "your potential", "what if"],
    "reflection": ["deep thoughts", "philosophy", "sonder", "perspective on life",
                   "mindfulness", "meaning of life"],
}


def _chapter(p):
    return ([], [label("cnum", p.get("num", "1"), "accent", 0.20, [0.5, 0.37], t0=0.0),
                 label("ctitle", p.get("title", ""), "ink", 0.072, [0.5, 0.56], t0=0.12)])


def _embiggen(actors, f):
    for a in actors:
        for k in a.get("keys", []):
            if "scale" in k:
                k["scale"] = round(k["scale"] * f, 4)
    return actors


LIGHT_ICONS = {"phone", "bulb", "sun", "star", "heart", "eye", "gift"}


def _pick_sync_word(beat: dict, *, for_text: bool = False) -> str | None:
    """Word in the narration when a prop/label should pop in."""
    narr = beat.get("narration", "")
    if for_text and beat.get("text"):
        return beat["text"]
    emph = (beat.get("caption_emphasis") or "").replace(",", " ").split()
    for w in reversed(emph):
        clean = w.strip(".,!?\"'").lower()
        if clean and clean in narr.lower():
            return clean
    if beat.get("text"):
        return beat["text"]
    return None


def _text_prop(text, sync_word=None, effect: str | None = None):
    """A floating keyword that pops in when that word is spoken."""
    effect = effect if effect in ("glow", "burst") else "glow"
    return {"type": "label", "id": "t", "text": text.upper(), "color": "accent", "size": 0.08, "front": True,
            "sync_word": (sync_word or text).lower(), "effect": effect,
            "glow": effect == "glow", "glow_radius": 0.10,
            "keys": [{"t": 0.0, "pos": [0.32, 0.28], "alpha": 0, "scale": 0.35},
                     {"t": 0.15, "pos": [0.32, 0.25], "alpha": 1, "scale": 1.0, "ease": "pop"},
                     {"t": 1, "pos": [0.32, 0.25], "alpha": 1, "scale": 1.0}]}


def _icon_prop(name, sync_word=None, effect: str | None = None):
    """A scene object that pops in when the synced word is spoken."""
    use = effect if effect in ("glow", "rays", "burst") else None
    return {"type": "icon", "name": name, "color": "accent", "size": 0.12, "front": True,
            "sync_word": sync_word, "effect": use,
            "glow": use in ("glow", "burst"), "rays": use == "rays", "glow_to": "hero",
            "glow_radius": 0.14 if name == "phone" else 0.11,
            "keys": [{"t": 0.0, "pos": [0.72, 0.32], "alpha": 0, "scale": 0.35},
                     {"t": 0.15, "pos": [0.72, 0.30], "alpha": 1, "scale": 1.0, "ease": "pop"},
                     {"t": 1, "pos": [0.72, 0.30], "alpha": 1, "scale": 1.0}]}


# Vivid sketch palette (used to colour props/labels/icons on a per-scene rotation so
# the screen stays lively — a new accent colour every scene).
DEFAULT_COLORS = ["#ff5a5f", "#ffb454", "#22c1a4", "#4d8bff", "#c879ff", "#ff8fab", "#7ed957"]


def _colorize(actors, props, colors, idx):
    """Rotate vivid colours onto figures + accent props so every scene is lively
    (a different bold palette each beat), while keeping 'muted' ghosts muted."""
    if not colors:
        return actors, props
    c = colors[idx % len(colors)]
    c2 = colors[(idx + 2) % len(colors)]
    c3 = colors[(idx + 4) % len(colors)]
    # Colour the figures: the hero/first actor gets the scene's primary colour,
    # a second actor a contrasting one; ghosts/muted stay muted for meaning.
    hero_cols = [c, c3, c2]
    hi = 0
    for a in actors:
        ac = a.get("color")
        if ac in (None, "ink"):
            a["color"] = hero_cols[hi % len(hero_cols)]
            hi += 1
        # 'muted' actors (ghosts, younger self, crowd extras) keep their tone
    for p in props:
        ptype = p.get("type")
        if ptype in ("label", "icon") or p.get("color") == "accent":
            p["color"] = c
        elif ptype in ("circle", "path", "line", "arrow") and p.get("color") in (None, "ink"):
            p["color"] = c2
    return actors, props


def _beats_to_scenes(beats, embiggen, shorts=False, pace=None, colors=None):
    tmpl = dict(TEMPLATES)
    tmpl["chapter"] = _chapter
    scenes = []
    for i, b in enumerate(beats):
        t = b["template"]
        params = {}
        if b.get("pose"):
            params["pose"] = b["pose"]
            params["poses"] = [b["pose"]]
        # generic + two-figure params so interactions actually render distinct poses
        for k_src, k_dst in (("face", "face"), ("dir", "dir"), ("text", "text"),
                             ("num", "num"), ("ctitle", "title"),
                             ("poseA", "poseA"), ("poseB", "poseB"),
                             ("faceA", "faceA"), ("faceB", "faceB"),
                             ("colorA", "colorA"), ("colorB", "colorB")):
            if b.get(k_src):
                params[k_dst] = b[k_src]
        actors, props = tmpl.get(t, tmpl["solo"])(params)
        _embiggen(actors, embiggen)
        effect = b.get("visual_effect") or b.get("effect")
        sync = _pick_sync_word(b)
        if b.get("icon"):
            props = list(props) + [_icon_prop(b["icon"], sync_word=sync, effect=effect)]
        if b.get("text") and t not in ("label_above", "chapter", "compare"):
            props = list(props) + [_text_prop(b["text"], sync_word=_pick_sync_word(b, for_text=True),
                                   effect=effect if effect in ("glow", "burst") else None)]
        actors, props = _colorize(actors, props, colors, i)
        # Pace: a lower floor keeps something changing roughly every `pace` seconds.
        if shorts:
            floor = pace or 2.5
            min_dur = max(2.0, floor - 0.4) if t == "hook" else floor
        else:
            floor = pace or 3.0
            min_dur = max(2.4, floor - 0.4) if t in ("hook", "chapter") else floor
        scenes.append({"id": f"{i:02d}_{t}", "narration": b["narration"],
                       "min_dur": round(min_dur, 2),
                       "caption_emphasis": b.get("caption_emphasis") or "",
                       "actors": actors, "props": props})
    return scenes


def _slugify(text):
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:48] or "video"


def build_metadata(script, topic, config=None):
    config = config or {}
    title = script["title"]
    body = next((b["narration"] for b in script["beats"] if b["template"] != "hook"), title)
    cta = next((b["narration"] for b in reversed(script["beats"]) if b["template"] == "cta"), "")
    q = next((s.strip() + "?" for s in cta.split("?") if s.strip()), "What did this stir up for you?")
    tags_h = config.get("channel_hashtags") or HASHTAGS.get(topic["kind"], HASHTAGS["reflection"])
    name = config.get("channel_name", "Inklings")
    desc = (f"{title}\n\n{body}\n\n"
            f"💬 {q}\n👍 If this resonated, a like genuinely helps the channel.\n"
            f"🔔 Subscribe to {name} for more.\n\n" + " ".join(tags_h))
    kw = [w for w in re.findall(r"[a-z']+", title.lower()) if w not in STOP and len(w) > 2]
    seen, tags = set(), []
    suffix = config.get("tag_suffix") or ["stick figure animation", "video essay"]
    for t in kw + TAG_POOL.get(topic["kind"], []) + list(suffix) + [name]:
        t = t.strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            tags.append(t)
    return {"title": title[:100], "description": desc[:4900], "tags": tags[:20],
            "playlist": topic["playlist"], "hashtags": tags_h}


def _channel_style(config):
    """Overlay the active channel's palette + figure identity onto BASE_STYLE so
    every video on a channel shares the same colours, line wobble, and grain."""
    style = dict(BASE_STYLE)
    for key in ("background", "ink", "accent", "muted", "wobble", "grain", "scenery", "transition"):
        if config.get(key) is not None:
            style[key] = config[key]
    palette = config.get("palette") or {}
    for key in ("background", "ink", "accent", "muted"):
        if palette.get(key):
            style[key] = palette[key]
    # On a light/white background, default captions to dark ink for readability.
    bg = style.get("background", "#0e1320").lstrip("#")
    try:
        lum = sum(int(bg[i:i+2], 16) for i in (0, 2, 4)) / 3
    except Exception:
        lum = 0
    caption = dict(style.get("caption") or {})
    if config.get("caption_color"):
        caption["color"] = config["caption_color"]
    elif lum > 150 and not caption.get("color"):
        caption["color"] = style.get("ink", "#16181d")
    if caption:
        style["caption"] = caption
    if config.get("logo"):
        style["logo"] = config["logo"]
    return style


def produce(topic, script, config, slug=None, outroot="output"):
    slug = slug or f"auto_{_slugify(script['title'])}"
    colors = config.get("colors") or DEFAULT_COLORS
    scenes = _beats_to_scenes(script["beats"], config.get("embiggen", 1.42),
                              shorts=bool(config.get("shorts")),
                              pace=config.get("pace"), colors=colors)
    voice = dict(BASE_VOICE)
    if config.get("kokoro_voice"):
        voice["kokoro_voice"] = config["kokoro_voice"]
    if config.get("kokoro_speed"):
        voice["kokoro_speed"] = config["kokoro_speed"]
    if config.get("piper_model"):
        voice["piper_model"] = config["piper_model"]
    if "gap" in config:
        voice["gap"] = config["gap"]
    story = {"title": script["title"], "handle": config.get("handle", "@Inklings1"),
             "hook": script["hook"], "hook_dur": 2.0,
             "meta": {"playlist": topic["playlist"], "kind": topic["kind"], "auto": True,
                      "channel": config.get("channel_id", "inklings")},
             "style": _channel_style(config), "voice": voice, "scenes": scenes}
    story_path = ROOT / "stories" / f"{slug}.json"
    story_path.write_text(json.dumps(story, indent=2))

    from faceless.render import build  # lazy: needs pillow/numpy/ffmpeg
    outputs = build(str(story_path), formats=config.get("formats", ["16:9"]), outroot=outroot)
    video = next((p for p in outputs if "16x9" in p.name), outputs[0])

    thumb = make_thumbnail(
        script["hook"],
        topic.get("thumb") or config.get("thumb_default", "bubbles"),
        Path(outroot) / slug / f"{slug}_thumb.png",
        script=script,
        topic=topic,
        config=config,
        visual_style=config.get("visual_style", "stick"),
    )
    meta = build_metadata(script, topic, config)
    return {"slug": slug, "video": Path(video), "thumb": Path(thumb),
            "story": story_path, "meta": meta}
