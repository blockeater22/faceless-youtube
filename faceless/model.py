"""Story schema: dataclasses + JSON loading + colour/resolution helpers."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Aspect ratio -> (width, height). min-dimension is 1080 for all so figures and
# line weights stay identical across formats.
RESOLUTIONS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),   # Shorts / Reels / TikTok
    "16:9": (1920, 1080),   # long-form YouTube
    "1:1": (1080, 1080),    # square (feed posts)
}


def _hex(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


@dataclass
class Style:
    background: str = "#0e1320"
    ink: str = "#f2ede1"
    accent: str = "#ffb454"
    muted: str = "#8a93a6"
    ink_width: float = 0.0058     # fraction of min(W,H)
    wobble: float = 1.7           # px at 1080 min-dim
    boil_every: int = 2           # re-seed wobble every N frames ("on twos")
    fps: int = 24
    grain: float = 0.05           # film-grain strength 0..1
    vignette: float = 0.55        # corner darkening 0..1
    life: float = 1.0             # idle motion (breath/sway/blink); 0 = off
    cam: float = 0.05             # Ken Burns zoom amplitude per scene; 0 = locked off
    draw_in: bool = True          # sketch figures on (strokes appear) as they enter
    draw_in_dur: float = 0.45     # seconds of the draw-on reveal
    shadow: float = 0.16          # contact-shadow opacity 0..1; 0 = off
    scenery: bool = True          # draw an atmospheric night backdrop (sky/moon/stars/ground)
    music: str = ""               # path to a bg music track, mixed (ducked) under the VO
    music_gain: float = -19.0     # music level in dB relative to the voice
    caption: dict = field(default_factory=dict)
    logo: str = ""                # path to a corner watermark png (e.g. branding/watermark.png)
    logo_pos: str = "tl"          # corner: tl | tr | bl | br
    logo_scale: float = 0.10      # fraction of short edge
    logo_opacity: float = 0.72

    def color(self, value) -> tuple[int, int, int]:
        """Resolve a colour: keyword, '#rrggbb', or [r,g,b]."""
        if value is None:
            return _hex(self.ink)
        if isinstance(value, (list, tuple)):
            return tuple(int(v) for v in value[:3])  # type: ignore[return-value]
        named = {"ink": self.ink, "accent": self.accent,
                 "bg": self.background, "muted": self.muted}
        return _hex(named.get(value, value))


@dataclass
class Voice:
    # backend: espeak (incl. mbrola "mb-*" voices) | piper | gtts | elevenlabs | none
    backend: str = "espeak"
    voice: str = "en-us+m3"        # espeak voice id, or mbrola e.g. "mb-us2"
    rate: int = 156                # espeak words-per-minute
    pitch: int = 42                # espeak pitch 0..99
    polish: bool = True            # apply ffmpeg warmth chain
    lang: str = "en"               # gTTS language
    eleven_voice: str = "Rachel"   # ElevenLabs voice name/id
    piper_model: str = ""          # path to a local piper .onnx voice (+ .json sibling)
    piper_length: float = 1.0      # piper length_scale (>1 = slower)
    kokoro_voice: str = "af_heart" # kokoro-onnx voice (af_heart, bm_george, am_michael, ...)
    kokoro_model: str = "voices/kokoro-v1.0.onnx"
    kokoro_voices: str = "voices/voices-v1.0.bin"
    kokoro_lang: str = "en-us"
    kokoro_speed: float = 1.0      # 1.0 = normal; <1 slower, calmer
    gap: float = 0.28              # trailing silence after each line (s)


@dataclass
class Scene:
    id: str
    narration: str = ""
    min_dur: float = 2.2
    bg: str | None = None          # optional per-scene background override
    caption: str | None = None     # override caption text (defaults to narration)
    actors: list[dict] = field(default_factory=list)
    props: list[dict] = field(default_factory=list)
    # filled in during the build:
    audio: str | None = None
    duration: float = 0.0


@dataclass
class Script:
    title: str
    style: Style
    voice: Voice
    scenes: list[Scene]
    handle: str = ""               # e.g. "@Inklings1" watermark
    hook: str = ""                 # big on-screen text shown for the first ~1.7s
    hook_dur: float = 1.7
    meta: dict = field(default_factory=dict)


def load_script(path: str | Path) -> Script:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    style = Style(**data.get("style", {}))
    voice = Voice(**data.get("voice", {}))
    scenes = [Scene(**s) for s in data["scenes"]]
    return Script(
        title=data.get("title", "Untitled"),
        style=style,
        voice=voice,
        scenes=scenes,
        handle=data.get("handle", ""),
        hook=data.get("hook", ""),
        hook_dur=data.get("hook_dur", 1.7),
        meta=data.get("meta", {}),
    )
