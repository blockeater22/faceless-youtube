"""Scene Planning Engine — Intent Graph -> abstract Scene Graph.

Produces a :class:`SceneSpec` of *semantic requirements* only. It never names a
concrete asset: prop requirements are registry-shaped *queries* (category/tags/
surface) the World Engine will later resolve. Cameras, layout, lighting, mood,
and animation notes are all symbolic, so the renderer/world/camera consume
structure, never English.
"""
from __future__ import annotations

from .lexicon import SETTING_CUES
from .schema import (Inf, SceneSpec, IntentGraph, VISUAL, COMEDY, EMOTION,
                     CHARACTER)

# semantic prop requirements per environment (queries, NOT assets)
_ENV_PROPS = {
    "office": [
        {"role": "focus", "category": "furniture", "tags": ["desk"], "surface": "floor"},
        {"role": "seat", "category": "furniture", "tags": ["chair"], "surface": "floor"},
        {"role": "detail", "category": "electronics", "tags": ["laptop"], "surface": "table", "on": "desk"},
        {"role": "set", "category": "architecture", "tags": ["window"], "surface": "wall"},
        {"role": "set", "category": "architecture", "tags": ["door"], "surface": "wall"},
        {"role": "decor", "category": "decoration", "tags": ["plant"], "surface": "any"},
    ],
    "home": [
        {"role": "focus", "category": "furniture", "tags": ["sofa"], "surface": "floor"},
        {"role": "set", "category": "furniture", "tags": ["table"], "surface": "floor"},
        {"role": "decor", "category": "decoration", "tags": ["plant"], "surface": "any"},
        {"role": "decor", "category": "decoration", "tags": ["painting"], "surface": "wall"},
    ],
    "school": [
        {"role": "focus", "category": "furniture", "tags": ["desk"], "surface": "floor"},
        {"role": "seat", "category": "furniture", "tags": ["chair"], "surface": "floor"},
    ],
}
_POSITIONS = {1: ["center"], 2: ["left", "right"], 3: ["left", "center", "right"]}


def scene_function(index: int, total: int) -> str:
    if total <= 1:
        return "standalone"
    if index == 0:
        return "setup"
    if index == total - 1:
        return "resolution"
    if index == total - 2 and total >= 3:
        return "climax"
    return "rising_action"


def recommend_scene_structure(total: int) -> list[str]:
    return [scene_function(i, total) for i in range(total)]


def infer_environment(scene_seg, analysis) -> dict:
    key = scene_seg.location_cue or ""
    if key in SETTING_CUES:
        setting, env, room, indoor = SETTING_CUES[key]
    else:
        env = analysis.extra.get("environment", Inf("", 0)).value
        room = analysis.extra.get("room_type", Inf("", 0)).value
        setting = analysis.setting.value
        indoor = analysis.extra.get("indoor", Inf(True, 0)).value
    return {"location": setting or "unspecified", "environment": env or "",
            "room_type": room or "", "indoor": bool(indoor)}


def _present(scene_seg, characters) -> list[str]:
    names = [n for n in characters
             if n in scene_seg.text or any(b.speaker == n for b in scene_seg.beats)]
    return names or (list(characters)[:1] if characters else [])


def infer_camera_focus(intent: IntentGraph, present: list[str], index: int,
                       total: int) -> list[dict]:
    shots = []
    if index == 0:
        shots.append({"type": "establishing", "target": "location",
                      "reason": "introduce the place"})
    shots.append({"type": "wide" if len(present) >= 2 else "medium",
                  "target": present[0] if present else "location",
                  "reason": "stage the action"})
    # close-up on the strongest emotional beat
    emos = intent.of_type(EMOTION)
    if emos:
        peak = max(emos, key=lambda n: n.confidence)
        who = peak.data.get("character", present[0] if present else "subject")
        shots.append({"type": "close_up", "target": who,
                      "reason": f"land the {peak.label} beat"})
    if len(present) >= 2:
        shots.append({"type": "reaction", "target": present[1],
                      "reason": "show the listener's reaction"})
    return shots


def infer_emotion_curve(understanding) -> list[dict]:
    out = []
    for sc in understanding.segmentation.scenes:
        emo = next((e for (lbl, e) in understanding.analysis.emotional_arc
                    if lbl == f"scene_{sc.index}"), "neutral")
        intensity = 0.4 + 0.15 * sum(1 for b in sc.beats if b.emotion != "neutral")
        out.append({"scene": sc.index, "emotion": emo,
                    "intensity": round(min(1.0, intensity), 2)})
    return out


def plan_scene(intent: IntentGraph, analysis, scene_seg, characters,
               index: int = 0, total: int = 1) -> SceneSpec:
    env = infer_environment(scene_seg, analysis)
    present = _present(scene_seg, characters)
    spec = SceneSpec(id=f"scene_{index}")
    spec.metadata = {"index": index, "total": total,
                     "confidence": round(analysis.genre.confidence, 2)}
    spec.narrative = {"function": scene_function(index, total),
                      "summary": scene_seg.text.strip()[:140]}
    spec.intent = intent.to_dict()
    spec.environment = env
    spec.time = analysis.time.value
    spec.weather = analysis.weather.value
    spec.mood = analysis.mood.value
    spec.lighting = _lighting(analysis, env)

    positions = _POSITIONS.get(len(present), ["left", "center", "right"] +
                               [f"pos{i}" for i in range(len(present))])
    layout = {}
    for i, name in enumerate(present):
        pos = positions[i] if i < len(positions) else f"pos{i}"
        layout[name] = pos
        c = characters[name]
        spec.characters.append({
            "name": name, "role": c.role.value, "position": pos,
            "facing": "right" if pos in ("left", "center") else "left",
            "emotion": c.current_emotion.value,
            "confidence": c.confidence_level, "stress": c.stress,
            "action": _action_for(name, scene_seg),
            "props": c.props})
    spec.spatial_layout = layout

    spec.camera_targets = infer_camera_focus(intent, present, index, total)
    spec.prop_requirements = _props(env, intent)
    spec.animation_notes = _anim_notes(intent)
    spec.dialogue_timing = [{"order": i, "speaker": b.speaker, "text": b.text,
                             "emotion": b.emotion}
                            for i, b in enumerate(b for b in scene_seg.beats if b.speaker)]
    spec.transitions = {"in": "fade" if index == 0 else "cut",
                        "out": "fade" if index == total - 1 else "cut"}
    spec.music = _music(analysis)
    spec.sound = (["rain"] if analysis.weather.value == "rain" else [])
    spec.effects = [n.label for n in intent.of_type(VISUAL)]
    spec.quality_metrics = {
        "inference_confidence": round((analysis.genre.confidence +
                                       analysis.mood.confidence) / 2, 2),
        "characters": len(present), "shots": len(spec.camera_targets)}
    return spec


def _lighting(analysis, env) -> str:
    if analysis.time.value == "night":
        return "dim"
    if analysis.mood.value in ("sad", "scared", "angry"):
        return "moody"
    if env["environment"] == "office":
        return "soft office"
    return "soft"


def _props(env, intent: IntentGraph) -> list[dict]:
    props = list(_ENV_PROPS.get(env["environment"], []))
    # a mood prop suggested by a visual opportunity
    if any("coffee" in n.label or "cup" in n.label for n in intent.of_type(VISUAL)):
        props.append({"role": "detail", "category": "decoration",
                      "tags": ["mug"], "surface": "table"})
    return props


def _anim_notes(intent: IntentGraph) -> list[str]:
    notes = []
    for n in intent.of_type(EMOTION):
        notes.append(f"{n.data.get('character', 'subject')}: perform {n.label}")
    for n in intent.of_type("retention_opportunity"):
        notes.append(f"timing: {n.label}")
    return notes


def _action_for(name, scene_seg) -> str:
    for b in scene_seg.beats:
        for a in b.actions:
            if a.subject == name and a.verb:
                return a.verb
    for b in scene_seg.beats:
        for a in b.actions:
            if a.verb:
                return a.verb
    return "idle"


def _music(analysis) -> str:
    return {"comedy": "playful", "drama": "emotional", "motivation": "uplifting",
            "action": "driving", "romance": "tender"}.get(
        analysis.genre.value,
        {"sad": "melancholy", "nervous": "tense", "excited": "upbeat"}.get(
            analysis.mood.value, "neutral"))
