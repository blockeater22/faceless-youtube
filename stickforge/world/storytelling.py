"""Environmental storytelling — the world reinforces the story.

Derives world parameters (wealth, cleanliness, decoration density, dominant
style, occupation, palette) from the Scene Graph, so the same office reads as
"tense startup at night" vs "calm corporate morning". These bias room size,
asset/variant selection, and decoration.
"""
from __future__ import annotations

_STYLE_BY_ENV = {
    "office": ["modern", "corporate"], "home": ["modern", "cute"],
    "school": ["flat", "cute"], "restaurant": ["modern"],
    "shop": ["modern"], "park": ["flat"], "street": ["modern"],
    "studio": ["sci-fi", "minimal"], "outdoor": ["flat"],
}
_OCCUPATION = {"office": "professional", "school": "student",
               "home": "resident", "restaurant": "diner"}


def derive(spec) -> dict:
    env = spec.environment.get("environment", "")
    mood = spec.mood
    wealth = {"office": "mid", "home": "mid", "restaurant": "mid",
              "studio": "high"}.get(env, "mid")
    if "luxury" in (spec.metadata.get("tags") or []):
        wealth = "high"
    cleanliness = "worn" if mood in ("sad", "gloomy", "angry") else "tidy"
    density = {"home": 0.7, "restaurant": 0.6, "office": 0.4,
               "school": 0.4}.get(env, 0.4)
    if mood in ("sad", "scared"):
        density *= 0.6
    return {
        "wealth": wealth,
        "cleanliness": cleanliness,
        "decoration_density": round(density, 2),
        "styles": _STYLE_BY_ENV.get(env, ["flat"]),
        "occupation": _OCCUPATION.get(env, "person"),
        "mood": mood,
        "palette": _palette(spec),
        "reads_as": f"{mood} {wealth}-class {env or 'place'}",
    }


def _palette(spec) -> dict:
    t = spec.time
    if t == "night":
        return {"key": "#2a3550", "ambient": "#141a2c"}
    if spec.mood in ("sad", "scared", "angry"):
        return {"key": "#5a5f6e", "ambient": "#2c2f3a"}
    if t in ("evening",):
        return {"key": "#f0b878", "ambient": "#4a3b52"}
    return {"key": "#fff3da", "ambient": "#cfe0f5"}
