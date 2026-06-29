"""Validation — no invalid Scene Graph reaches the renderer.

Checks for the failure modes the prompt calls out: missing location / camera
focus / narrative purpose, contradictory emotions, impossible time, empty
scenes, incomplete metadata. Errors block; warnings advise. The result is
written back into ``spec.validation`` so downstream can trust the contract.
"""
from __future__ import annotations

from .schema import SceneSpec, IntentGraph, CHARACTER, GOAL

_TIMES = {"morning", "noon", "evening", "night", "day"}
# emotions that shouldn't co-exist on one character in one scene
_CONTRADICTIONS = {frozenset({"happy", "sad"}), frozenset({"calm", "angry"}),
                   frozenset({"confident", "scared"})}


def validate_scene_graph(spec: SceneSpec) -> list[dict]:
    issues: list[dict] = []

    def err(field, msg): issues.append({"level": "error", "field": field, "msg": msg})
    def warn(field, msg): issues.append({"level": "warning", "field": field, "msg": msg})

    if not spec.environment.get("location"):
        err("environment", "missing location")
    if not spec.camera_targets:
        err("camera_targets", "scene has no camera focus")
    if not spec.narrative.get("function"):
        err("narrative", "missing narrative function")
    if not spec.intent.get("nodes"):
        warn("intent", "scene has no intent nodes")
    if spec.time not in _TIMES:
        warn("time", f"unusual time {spec.time!r}")
    if not spec.characters and not spec.dialogue_timing:
        warn("characters", "scene has neither characters nor narration")

    # contradictory emotions per character
    seen: dict[str, set] = {}
    for c in spec.characters:
        seen.setdefault(c["name"], set()).add(c.get("emotion", "neutral"))
    for name, emos in seen.items():
        for pair in _CONTRADICTIONS:
            if pair <= emos:
                err("characters", f"{name} has contradictory emotions {sorted(pair)}")

    status = "valid" if not any(i["level"] == "error" for i in issues) else "invalid"
    spec.validation = {"status": status, "issues": issues}
    return issues


def validate_intent_graph(g: IntentGraph) -> list[dict]:
    issues: list[dict] = []
    chars = g.of_type(CHARACTER)
    goals = {n.data.get("character") for n in g.of_type(GOAL)}
    for c in chars:
        if c.label not in goals:
            issues.append({"level": "warning", "field": "goal",
                           "msg": f"{c.label} has no inferred goal"})
    if not g.nodes:
        issues.append({"level": "error", "field": "graph", "msg": "empty intent graph"})
    return issues
