"""Procedural lip-sync: text -> timed mouth shapes (visemes).

No audio required. We approximate speech as a sequence of syllables; each
syllable opens the mouth on its vowel (the viseme) and closes between
syllables. The vowel selects how open the mouth is (A wide, I narrow, etc.),
which is most of what a viewer reads as "talking". Output is a list of
``(t_offset, mouth_open, mouth_curve)`` within ``[0, duration]``.
"""
from __future__ import annotations

import re

# how open the mouth is per vowel viseme
VISEME_OPEN = {"a": 0.72, "e": 0.5, "i": 0.34, "o": 0.62, "u": 0.4, "y": 0.45}
_CLOSED = 0.06


def _syllable_vowels(text: str) -> list[str]:
    """The ordered vowel nuclei of the line (≈ one per syllable)."""
    vowels: list[str] = []
    for word in re.findall(r"[a-zA-Z]+", text.lower()):
        for grp in re.findall(r"[aeiouy]+", word):
            vowels.append(grp[0])
    return vowels or ["a"]


def visemes_for(text: str, duration: float) -> list[tuple[float, float, float]]:
    if duration <= 0:
        return []
    vowels = _syllable_vowels(text)
    # cap density so the mouth doesn't flicker faster than it reads
    n = min(len(vowels), max(2, int(duration * 6)))
    lead = min(0.12, duration * 0.12)
    span = max(1e-3, duration - lead * 2)
    seg = span / n
    keys: list[tuple[float, float, float]] = [(0.0, _CLOSED, 0.0)]
    t = lead
    for k in range(n):
        v = vowels[k % len(vowels)]
        keys.append((round(t, 3), VISEME_OPEN.get(v, 0.5), 0.05))      # open on vowel
        keys.append((round(t + seg * 0.55, 3), _CLOSED, 0.0))          # close after
        t += seg
    keys.append((round(min(duration - 0.01, t), 3), _CLOSED, 0.0))     # rest
    return keys
