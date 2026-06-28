"""The pose test loop: generate many poses, score them, reject the weak ones.

This operationalises "generate 100 poses, score, reject, repeat" — a quick,
deterministic way to measure the average quality of the generative pose system
and to harvest the strongest poses.
"""
from __future__ import annotations

import random

from .builder import ARM_LEFT, build_pose
from .score import score_pose

_ARMS = list(ARM_LEFT)


def random_intent(rng: random.Random) -> dict:
    return {
        "loa": rng.uniform(-22, 22),
        "weight": rng.uniform(-1, 1),
        "head": rng.uniform(-10, 10),
        "arm_l": rng.choice(_ARMS),
        "arm_r": rng.choice(_ARMS),
        "crouch": rng.choice([0.0, 0.0, 0.0, rng.uniform(0.0, 0.8)]),
    }


def generate(n: int = 100, seed: int = 0) -> list[dict]:
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        intent = random_intent(rng)
        pose = build_pose(**intent)
        total, breakdown = score_pose(pose)
        out.append({"intent": intent, "pose": pose, "score": total,
                    "breakdown": breakdown})
    out.sort(key=lambda r: -r["score"])
    return out


def evaluate(n: int = 100, keep: float = 0.3, seed: int = 0) -> dict:
    """Generate ``n`` poses, score, and report all-mean vs kept-top mean."""
    results = generate(n, seed)
    all_mean = sum(r["score"] for r in results) / len(results)
    k = max(1, int(len(results) * keep))
    top = results[:k]
    top_mean = sum(r["score"] for r in top) / k
    return {"n": n, "all_mean": round(all_mean, 2), "top_mean": round(top_mean, 2),
            "kept": k, "best": results[0], "worst": results[-1], "results": results}
