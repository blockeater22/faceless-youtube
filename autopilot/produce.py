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


def _icon_prop(name):
    """A scene-relevant object that pops in beside the figure (illustrates the line)."""
    return {"type": "icon", "name": name, "color": "accent", "size": 0.12, "front": True,
            "keys": [{"t": 0.18, "pos": [0.72, 0.32], "alpha": 0, "scale": 0.4},
                     {"t": 0.4, "pos": [0.72, 0.30], "alpha": 1, "scale": 1.0, "ease": "pop"},
                     {"t": 1, "pos": [0.72, 0.30], "alpha": 1, "scale": 1.0}]}


def _beats_to_scenes(beats, embiggen):
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
        if b.get("icon"):
            props = list(props) + [_icon_prop(b["icon"])]
        scenes.append({"id": f"{i:02d}_{t}", "narration": b["narration"],
                       "min_dur": 3.4 if t == "chapter" else 5.6,
                       "actors": actors, "props": props})
    return scenes


def _slugify(text):
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:48] or "video"


def build_metadata(script, topic):
    title = script["title"]
    body = next((b["narration"] for b in script["beats"] if b["template"] != "hook"), title)
    cta = next((b["narration"] for b in reversed(script["beats"]) if b["template"] == "cta"), "")
    q = next((s.strip() + "?" for s in cta.split("?") if s.strip()), "What did this stir up for you?")
    tags_h = HASHTAGS.get(topic["kind"], HASHTAGS["reflection"])
    desc = (f"{title}\n\n{body}\n\n"
            f"💬 {q}\n🔔 Subscribe for hand-drawn videos about the mind, calm, and the "
            f"quietly mind-bending.\n\n" + " ".join(tags_h))
    kw = [w for w in re.findall(r"[a-z']+", title.lower()) if w not in STOP and len(w) > 2]
    seen, tags = set(), []
    for t in kw + TAG_POOL.get(topic["kind"], []) + \
             ["stick figure animation", "video essay", "Inklings"]:
        t = t.strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            tags.append(t)
    return {"title": title[:100], "description": desc[:4900], "tags": tags[:20],
            "playlist": topic["playlist"], "hashtags": tags_h}


def produce(topic, script, config, slug=None, outroot="output"):
    slug = slug or f"auto_{_slugify(script['title'])}"
    scenes = _beats_to_scenes(script["beats"], config.get("embiggen", 1.42))
    voice = dict(BASE_VOICE)
    if config.get("kokoro_voice"):
        voice["kokoro_voice"] = config["kokoro_voice"]
    if config.get("kokoro_speed"):
        voice["kokoro_speed"] = config["kokoro_speed"]
    if config.get("piper_model"):
        voice["piper_model"] = config["piper_model"]
    story = {"title": script["title"], "handle": config.get("handle", "@Inklings1"),
             "hook": script["hook"], "hook_dur": 2.0,
             "meta": {"playlist": topic["playlist"], "kind": topic["kind"], "auto": True},
             "style": BASE_STYLE, "voice": voice, "scenes": scenes}
    story_path = ROOT / "stories" / f"{slug}.json"
    story_path.write_text(json.dumps(story, indent=2))

    from faceless.render import build  # lazy: needs pillow/numpy/ffmpeg
    outputs = build(str(story_path), formats=config.get("formats", ["16:9"]), outroot=outroot)
    video = next((p for p in outputs if "16x9" in p.name), outputs[0])

    thumb = make_thumbnail(script["hook"], topic["thumb"],
                           ROOT / "branding" / f"thumb_{slug}.png")
    meta = build_metadata(script, topic)
    return {"slug": slug, "video": Path(video), "thumb": Path(thumb),
            "story": story_path, "meta": meta}
