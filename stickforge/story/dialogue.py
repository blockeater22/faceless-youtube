"""Multi-character dialogue: staging, turn-taking, and eye contact.

Parses a screenplay-style script ("NAME: line"), stages the cast facing one
another, and compiles a synchronized performance where the speaker acts + talks
(lip-sync) while everyone else *listens* — turning to look at the speaker. The
result is one Scene with several actors and timed "NAME: line" subtitles.
"""
from __future__ import annotations

import re

from ..acting.performance import Beat, compile_performance
from ..character.character import build_character
from ..scene.camera import Camera
from ..scene.scene import Actor, Scene
from ..voice.engine import estimate_duration
from .script import infer_emotion


def parse_dialogue(text: str) -> list[tuple[str | None, str, str]]:
    """-> list of (speaker | None, line, emotion). None speaker = narration."""
    out: list[tuple[str | None, str, str]] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("(") and s.endswith(")"):
            body = s.strip("() ").strip()
            out.append((None, body, infer_emotion(body)))
            continue
        m = re.match(r"^([A-Za-z][\w'-]*)\s*:\s*(.+)$", s)
        if m:
            out.append((m.group(1), m.group(2).strip(), infer_emotion(m.group(2))))
        else:
            out.append((None, s, infer_emotion(s)))
    return out


def _stage_positions(n: int) -> list[tuple[float, int]]:
    """(x fraction, facing) per actor — placed facing one another."""
    if n <= 1:
        return [(0.5, 1)]
    if n == 2:
        return [(0.30, 1), (0.70, -1)]
    if n == 3:
        return [(0.22, 1), (0.5, 1), (0.78, -1)]
    xs = [(i + 0.5) / n for i in range(n)]
    return [(x, 1 if x < 0.5 else -1) for x in xs]


def stage_dialogue(script: str, cast: dict[str, str],
                   background: str = "night", library=None) -> Scene:
    """Compile a dialogue script into a staged, multi-actor Scene.

    ``cast`` maps speaker names (as written) to character ids. Speakers not in
    the cast are mapped to the first cast member.
    """
    if library is None:
        from .. import studio
        library = studio.load_core_library()
    lines = parse_dialogue(script)
    names = list(cast)
    lut = {n.lower(): n for n in names}
    positions = _stage_positions(len(names))

    beats: dict[str, list[Beat]] = {n: [] for n in names}
    subtitles: list[dict] = []
    t = 0.0
    for speaker, line, emo in lines:
        d = estimate_duration(line)
        spk = lut.get((speaker or "").lower(), names[0] if speaker else None)
        for n in names:
            if n == spk:                                   # the speaker: act + talk
                beats[n].append(Beat(emo, d, "act", text=line,
                                     gaze=(0.42, 0.0), talk=True))
            else:                                          # listeners: turn & watch
                beats[n].append(Beat("neutral", d, "act",
                                     gaze=(0.42, -0.03), talk=False))
        label = f"{spk}: {line}" if spk else line
        subtitles.append({"t": round(t, 3), "text": label})
        t += d

    actors = []
    for i, n in enumerate(names):
        clip = compile_performance(beats[n], loop=False, fixed_timing=True)
        x, facing = positions[i]
        src = library.get(cast[n]) if cast[n] in library else {"id": cast[n]}
        actors.append(Actor(character=build_character(src, library), clip=clip,
                            pos=(x, 0.66), unit_scale=0.30, life=1.0,
                            facing=facing, id=n))
    return Scene(id="dialogue", duration=round(t, 3),
                 background={"type": background}, actors=actors,
                 camera=Camera(zoom=1.04), subtitles=subtitles)
