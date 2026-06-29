"""The Stage Direction Engine — the performance director.

Turns a World Graph into believable actor performances *before* any camera
exists: where actors stand and why (blocking via proxemics + status), where they
look (eye-contact choreography), how they move (motivated movement over the nav
graph), what they do (gesture/interaction), and the timing/rhythm of it all —
emitted as a versioned **Blocking Graph** the Director AI later films.

It is the layer *above* the per-actor acting engine (which it reuses for
emotion→body-language content) and *below* the camera. The camera observes
performances; it does not create them.

Public services: ``direct_scene``/``direct_story`` plus ``plan_blocking``,
``plan_movements``, ``plan_gestures``, ``plan_eye_contact``,
``plan_interactions``, ``plan_scene_rhythm``, ``plan_emotional_performance``,
``validate_blocking``, ``update_character_state``.
"""
from .schema import (BlockingGraph, BlockingMark, PerformanceBeat,
                     SCHEMA_VERSION)
from .blocking import plan_blocking
from .performance import (plan_movements, plan_eye_contact, plan_gestures,
                          plan_interactions, plan_scene_rhythm,
                          plan_emotional_performance)
from .continuity import CharacterState, update_character_state
from .validate import validate_blocking
from .engine import StageDirector, direct_scene, direct_story

__all__ = [
    "BlockingGraph", "BlockingMark", "PerformanceBeat", "SCHEMA_VERSION",
    "plan_blocking", "plan_movements", "plan_eye_contact", "plan_gestures",
    "plan_interactions", "plan_scene_rhythm", "plan_emotional_performance",
    "CharacterState", "update_character_state", "validate_blocking",
    "StageDirector", "direct_scene", "direct_story",
]
