"""StageDirector — orchestrates blocking + performance into a Blocking Graph.

    World Graph (+ Scene Graph) ──▶ blocking ──▶ rhythm (movement/look/gesture/
    speak/react/interact/pause) ──▶ relationships ──▶ validate ──▶ BlockingGraph

``direct_story`` threads continuity state across scenes so performances persist.
"""
from __future__ import annotations

from .blocking import plan_blocking
from .continuity import update_character_state
from .performance import plan_scene_rhythm
from .proxemics import preferred_distance
from .schema import BlockingGraph
from .validate import validate_blocking


class StageDirector:
    def direct_scene(self, world, spec, state=None, seed: int = 0) -> BlockingGraph:
        marks = plan_blocking(world, spec, state)
        beats, duration = plan_scene_rhythm(world, spec, marks, state)
        graph = BlockingGraph(scene_id=spec.id, duration=duration, marks=marks,
                              beats=beats)
        graph.relationships = self._relationships(marks)
        graph.stats = {
            "actors": len(marks),
            "beats": len(beats),
            "moves": len(graph.of_kind("enter")),
            "looks": len(graph.of_kind("look")),
            "gestures": len(graph.of_kind("gesture")),
            "interactions": len(graph.of_kind("interact")),
        }
        validate_blocking(graph, world)
        return graph

    def _relationships(self, marks) -> list:
        names = list(marks)
        out = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = marks[names[i]], marks[names[j]]
                dist = abs(a.position.x - b.position.x)
                rel = ("intimate" if dist < preferred_distance("romance")
                       else "personal" if dist < preferred_distance("friend") * 1.2
                       else "social")
                out.append((names[i], names[j], round(dist, 1), rel))
        return out


def direct_scene(world, spec, state=None, seed: int = 0) -> BlockingGraph:
    return StageDirector().direct_scene(world, spec, state, seed)


def direct_story(worlds: list, specs: list, seed: int = 0):
    """Direct a sequence of scenes with persistent performance continuity."""
    director = StageDirector()
    state: dict = {}
    graphs = []
    for i, (world, spec) in enumerate(zip(worlds, specs)):
        g = director.direct_scene(world, spec, state, seed + i)
        state = update_character_state(state, g, spec)
        graphs.append(g)
    return graphs, state
