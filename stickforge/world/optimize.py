"""World optimization — instancing, LOD, and a cache key.

Counts asset reuse (instancing potential), assigns LOD by distance from the
focal centre, and produces a deterministic cache key so identical (scene, seed)
worlds can be memoized / streamed.
"""
from __future__ import annotations

from collections import Counter


def optimize(world, room, seed: int) -> dict:
    instances = Counter(o.asset_id for o in world.objects if o.asset_id)
    placeholders = sum(1 for o in world.objects if o.asset_id is None)
    for o in world.objects:
        far = abs(o.position.x) > room.width * 0.35
        o.lod = 1 if far else 0
    return {
        "objects": len(world.objects),
        "unique_assets": len(instances),
        "instances": dict(instances),
        "instanced_savings": sum(c - 1 for c in instances.values()),
        "placeholders": placeholders,
        "zones": len(world.zones),
        "nav_nodes": len(world.nav.nodes),
        "lights": len(world.lights),
        "cache_key": f"{world.scene_id}:{room.env}:{seed}",
    }
