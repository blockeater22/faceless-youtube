"""Synthetic story corpus — for stress-testing the cognitive layer at volume.

Hand-written exemplars per genre plus a templated generator, so understanding +
planning + validation can be benchmarked across hundreds of stories (comedy,
drama, education, motivation, action, sci-fi, business, children, …).
"""
from __future__ import annotations

import random

SAMPLES: dict[str, list[str]] = {
    "business": [
        "John nervously entered his first interview on a rainy morning. "
        "The interviewer smiled. John hoped to pass and prove himself.",
    ],
    "comedy": [
        "Mia tried to look cool at the party. She tripped on the rug. "
        "It was awkward and silly, but everyone laughed.",
    ],
    "drama": [
        "Sam stood alone in the empty kitchen at night. He felt sad and lost. "
        "He wished he had said goodbye.",
    ],
    "motivation": [
        "Aria was afraid she would fail. But she decided to never give up. "
        "She rose, determined to achieve her dream.",
    ],
    "education": [
        "Today we will learn how rain forms. First, water evaporates. "
        "Then it cools and falls. That is the water cycle.",
    ],
    "children": [
        "A happy little bunny hopped in the park. The puppy wanted to play. "
        "They became friends and laughed all afternoon.",
    ],
    "scifi": [
        "On the spaceship, Nova watched an alien signal appear. She was curious. "
        "The robot warned of danger. Suddenly the lights went dark.",
    ],
}

_NAMES = ["John", "Mia", "Sam", "Aria", "Nova", "Leo", "Zoe", "Max", "Ivy", "Kai"]
_SETTINGS = ["office", "kitchen", "classroom", "park", "street", "spaceship"]
_EMOTIONS = ["nervous", "happy", "sad", "excited", "angry", "confident", "scared"]
_GOALS = ["wanted to pass", "hoped to win", "needed to escape", "decided to prove herself",
          "tried to find the truth", "wished to be brave"]
_TIMES = ["morning", "evening", "night"]
_WEATHER = ["", "on a rainy day", "in the snow", "under a clear sky"]


def generate(n: int, seed: int = 0) -> list[str]:
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        a, b = rng.sample(_NAMES, 2)
        s = rng.choice(_SETTINGS)
        emo = rng.choice(_EMOTIONS)
        goal = rng.choice(_GOALS)
        t = rng.choice(_TIMES)
        w = rng.choice(_WEATHER)
        scene2 = rng.choice([
            f"Later, {b} arrived at the {s}. {b} said hello.",
            f"Meanwhile, {a} {goal}.",
            f"That {t}, everything changed.",
        ])
        out.append(
            f"{a} felt {emo} as the scene opened in the {s} {w}. {a} {goal}. "
            f"{scene2}")
    return out


def all_samples() -> list[str]:
    return [s for lst in SAMPLES.values() for s in lst]
