"""Weather — ambient descriptors (particles/overlay), never rendered here."""
from __future__ import annotations

_WEATHER = {
    "rain": {"particles": "rain", "overlay": "#1a2238", "intensity": 0.5, "sound": "rain"},
    "storm": {"particles": "rain", "overlay": "#10131f", "intensity": 0.8, "sound": "thunder"},
    "snow": {"particles": "snow", "overlay": "#2a3550", "intensity": 0.4, "sound": ""},
    "fog": {"particles": "fog", "overlay": "#3a4150", "intensity": 0.5, "sound": ""},
    "clear": {"particles": "", "overlay": "", "intensity": 0.0, "sound": ""},
}


def build_weather(spec, room) -> dict:
    w = dict(_WEATHER.get(spec.weather, _WEATHER["clear"]))
    w["type"] = spec.weather
    # indoors, weather shows through windows only
    w["through_window_only"] = bool(room.indoor) and room.window_x is not None
    return w
