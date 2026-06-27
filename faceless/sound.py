"""Procedurally-synthesized sound design - no audio assets, no licensing.

Top Shorts use three tiny audio cues to lift retention: a soft *pop* as the
hook lands, a *whoosh* on each scene cut (so the eye expects the change), and a
gentle *ding* on the emotional payoff (the reframe). All three are generated
from numpy here and mixed onto the narration master, so nothing needs to be
sourced or cleared.

An optional music bed (``style.music`` -> a path to your own cleared track,
e.g. from the YouTube Audio Library) is ducked quietly under the voice if
present; absent, it's simply skipped.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SR = 44100


def _stereo(x: np.ndarray) -> np.ndarray:
    return np.column_stack([x, x]) if x.ndim == 1 else x


def whoosh(dur: float = 0.22) -> np.ndarray:
    """A soft noise swish for a scene cut."""
    n = int(SR * dur)
    noise = np.random.uniform(-1, 1, n)
    k = 60                                              # moving-average lowpass -> "shh" not "tss"
    noise = np.convolve(noise, np.ones(k) / k, mode="same")
    a = int(n * 0.45)
    env = np.concatenate([np.linspace(0, 1, a) ** 1.5,
                          np.linspace(1, 0, n - a) ** 1.8])
    return noise * env * 0.5


def ding(dur: float = 0.6) -> np.ndarray:
    """A warm two-partial chime for the reframe payoff."""
    t = np.arange(int(SR * dur)) / SR
    tone = np.sin(2 * np.pi * 1320 * t) * 0.6 + np.sin(2 * np.pi * 1980 * t) * 0.3
    return tone * np.exp(-t * 6.0)


def pop(dur: float = 0.09) -> np.ndarray:
    """A short tick/pop for the hook landing."""
    t = np.arange(int(SR * dur)) / SR
    return np.sin(2 * np.pi * 740 * t) * np.exp(-t * 38.0) * 0.7


def _load_music(path: Path, n: int) -> np.ndarray | None:
    """Load a music bed, loop/trim to ``n`` samples, mono->stereo, soft fades."""
    try:
        import soundfile as sf  # type: ignore
    except ImportError:
        return None
    m, msr = sf.read(str(path))
    if m.ndim == 1:
        m = _stereo(m)
    if msr != SR:                                       # cheap linear resample
        idx = np.linspace(0, len(m) - 1, int(len(m) * SR / msr))
        m = np.column_stack([np.interp(idx, np.arange(len(m)), m[:, c]) for c in range(m.shape[1])])
    if len(m) < n:
        m = np.tile(m, (n // len(m) + 1, 1))
    bed = m[:n].astype(np.float64)
    fade = int(SR * 0.8)                                # in/out fades
    bed[:fade] *= np.linspace(0, 1, fade)[:, None]
    bed[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return bed


def mix(master: Path, out: Path, cuts: list[float], dings: list[float],
        sfx_gain: float = 0.22, music: str = "", music_gain: float = 0.10) -> bool:
    """Mix the SFX (and optional music bed) onto the narration master.

    ``cuts`` / ``dings`` are times in seconds. Returns True if it wrote ``out``.
    """
    try:
        import soundfile as sf  # type: ignore
    except ImportError:
        return False
    audio, sr = sf.read(str(master))
    audio = _stereo(np.asarray(audio, dtype=np.float64))
    n = len(audio)
    sfx = np.zeros((n, 2))

    def place(buf: np.ndarray, at: float) -> None:
        s = int(at * sr)
        if s >= n or s < 0:
            return
        buf = _stereo(buf)
        e = min(n, s + len(buf))
        sfx[s:e] += buf[: e - s]

    place(pop(), 0.0)
    for c in cuts:
        place(whoosh(), c - 0.06)      # lead the cut slightly
    for d in dings:
        place(ding(), d)

    mixed = audio + sfx * sfx_gain
    if music and Path(music).exists():
        bed = _load_music(Path(music), n)
        if bed is not None:
            mixed = mixed + bed * music_gain
    peak = float(np.max(np.abs(mixed))) or 1.0
    if peak > 1.0:
        mixed = mixed / peak * 0.98
    sf.write(str(out), mixed.astype(np.float32), sr)
    return True
