"""Proxemics, status, and posture — the why behind where actors stand.

Hall's interpersonal distances mapped to world units, relationship → preferred
distance, and a status/power model (theater "status transactions"): confident/
high-role characters claim space and stillness; fearful/low characters shrink
and edge toward exits. These drive blocking — never random coordinates.
"""
from __future__ import annotations

METER = 110.0
# Hall's zones in world units
DIST = {"intimate": 0.5 * METER, "personal": 1.2 * METER,
        "social": 3.0 * METER, "public": 5.0 * METER}

REL_DIST = {"romance": "intimate", "family": "personal", "friend": "personal",
            "acquaintance": "social", "professional": "social",
            "stranger": "social", "conflict": "social"}

_STATUS_EMO = {"confident": 0.9, "proud": 0.88, "determined": 0.82, "angry": 0.78,
               "excited": 0.62, "happy": 0.6, "curious": 0.55, "neutral": 0.5,
               "surprised": 0.45, "shocked": 0.4, "confused": 0.4, "sad": 0.3,
               "embarrassed": 0.3, "nervous": 0.25, "anxious": 0.22, "scared": 0.2}
_ROLE_STATUS = {"boss": 0.22, "interviewer": 0.22, "manager": 0.2, "teacher": 0.2,
                "villain": 0.18, "parent": 0.15, "hero": 0.1,
                "student": -0.12, "child": -0.15}


def preferred_distance(relation: str) -> float:
    return DIST[REL_DIST.get(relation, "social")]


def status_for(emotion: str, role: str = "character") -> float:
    s = _STATUS_EMO.get(emotion, 0.5) + _ROLE_STATUS.get(role, 0.0)
    return max(0.05, min(1.0, s))


def posture_for(emotion: str) -> str:
    if emotion in ("confident", "proud", "excited", "determined"):
        return "open"
    if emotion in ("angry",):
        return "aggressive"
    if emotion in ("nervous", "anxious", "scared", "sad", "embarrassed"):
        return "small"
    if emotion in ("suspicious",):
        return "closed"
    return "neutral"
