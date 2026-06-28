"""Depth layers + parallax — the z-ordering of the 2.5D world.

Lower ``Layer`` values are further back and draw first. Each layer has a default
parallax factor in [0, 1]: 0 = infinitely far (ignores camera pan), 1 = on the
action plane (moves fully with the camera). The Cinematic/World engines use
these to build believable depth from flat vector art.
"""
from __future__ import annotations

from enum import IntEnum


class Layer(IntEnum):
    SKY = 0          # gradient / sky dome
    FAR = 10         # distant scenery (mountains, skyline)
    BACKGROUND = 20  # room walls, far props
    MIDGROUND = 30   # furniture behind the actors
    GROUND = 40      # the ground plane + contact shadows
    ACTORS = 50      # the performers
    FOREGROUND = 60  # props in front of actors
    FX = 70          # particles / motion effects
    OVERLAY = 80     # captions / UI (screen space, not projected)


# default parallax per layer (camera-pan response)
PARALLAX: dict[int, float] = {
    Layer.SKY: 0.0,
    Layer.FAR: 0.15,
    Layer.BACKGROUND: 0.5,
    Layer.MIDGROUND: 0.85,
    Layer.GROUND: 1.0,
    Layer.ACTORS: 1.0,
    Layer.FOREGROUND: 1.15,   # >1 = closer than the action plane
    Layer.FX: 1.0,
    Layer.OVERLAY: 0.0,       # pinned to screen
}
