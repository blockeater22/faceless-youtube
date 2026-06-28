"""Director: compile a parsed script into a performed, subtitled Scene."""
from __future__ import annotations

from ..acting.performance import Beat, compile_performance
from ..character.character import build_character
from ..scene.scene import Actor, Scene
from ..scene.camera import Camera
from .script import parse_script, ScriptLine


def _beat_duration(text: str) -> float:
    """Reading time for a line — a beat should last as long as its thought."""
    return max(1.3, min(4.2, 0.9 + 0.055 * len(text)))


def script_to_beats(lines: list[ScriptLine]) -> list[Beat]:
    beats: list[Beat] = [Beat("neutral", 0.8, "act")]
    for ln in lines:
        if ln.think:
            # never react instantly — notice, pause, eyes drift, THEN react
            beats.append(Beat("thinking", 0.9, "think", look=(0.4, -0.4)))
            beats.append(Beat(ln.emotion, _beat_duration(ln.text), "react",
                              text=ln.text))
        else:
            kind = "act" if ln.kind == "dialogue" else "act"
            beats.append(Beat(ln.emotion, _beat_duration(ln.text), kind,
                              text=ln.text if ln.kind == "dialogue" else ""))
    return beats


def storyboard(script: str, *, actor_id: str = "actor.max",
               background: str = "night", library=None) -> Scene:
    """Compile a script string into a ready-to-render performed Scene."""
    lines = parse_script(script)
    beats = script_to_beats(lines)
    clip, marks = compile_performance(beats, loop=False, return_marks=True)

    # subtitles: each beat's start time carries its (possibly empty) text,
    # so dialogue appears in sync and actions clear the bar.
    subtitles = [{"t": m["start"], "text": m["text"]} for m in marks]

    actor = Actor(character=build_character({"id": actor_id}), clip=clip,
                  pos=(0.5, 0.63), unit_scale=0.34, life=1.0, id="narrator")
    return Scene(id="story", duration=clip.duration,
                 background={"type": background}, actors=[actor],
                 camera=Camera(zoom=1.06), subtitles=subtitles,
                 caption="")
