"""Turn a topic into a structured script the rest of the pipeline can render.

Only the intro and outro are marked as "avatar" segments, since the user
supplies a single ~15s face clip — not enough footage for a believable
full-length talking head. The body runs as voiceover over b-roll instead.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

SEGMENT_KINDS = ("avatar", "broll")


@dataclass
class Segment:
    kind: str  # "avatar" | "broll"
    text: str  # narration for this segment
    broll_keywords: list[str]  # stock-footage search terms; empty for avatar segments

    def __post_init__(self) -> None:
        if self.kind not in SEGMENT_KINDS:
            raise ValueError(f"unknown segment kind: {self.kind!r}")
        if not self.text.strip():
            raise ValueError("segment text must not be empty")


@dataclass
class Script:
    title: str
    topic: str
    segments: list[Segment]

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def full_narration(self) -> str:
        return " ".join(s.text for s in self.segments)


SCRIPT_PROMPT_TEMPLATE = """\
You are a scriptwriter for short-form marketing/blogging videos.

Write a {target_seconds}-second video script about: "{topic}"

Rules:
- The FIRST segment must be "avatar" (a punchy on-camera hook, 1-2 sentences).
- The LAST segment must be "avatar" (a call to action, 1-2 sentences).
- All middle segments must be "broll": voiceover narration that plays over
  stock b-roll footage. Each broll segment needs 2-5 short search keywords
  describing footage that matches the narration.
- Aim for natural spoken pacing (~2.4 words/second) to fill the target length.
- Tone: confident, clear, no fluff, no emoji, no markdown.

Respond with ONLY a JSON object matching this shape, no commentary:
{{
  "title": "short video title",
  "segments": [
    {{"kind": "avatar", "text": "...", "broll_keywords": []}},
    {{"kind": "broll", "text": "...", "broll_keywords": ["...", "..."]}},
    {{"kind": "avatar", "text": "...", "broll_keywords": []}}
  ]
}}
"""


def build_prompt(topic: str, target_seconds: int) -> str:
    return SCRIPT_PROMPT_TEMPLATE.format(topic=topic, target_seconds=target_seconds)


def parse_script_json(raw: str, topic: str) -> Script:
    """Parse and validate the LLM's JSON response into a Script.

    Tolerates the model wrapping the JSON in a markdown code fence.
    """
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object found in script response: {raw!r}")
    data = json.loads(match.group(0))

    segments_data = data.get("segments")
    if not segments_data:
        raise ValueError("script JSON has no segments")

    segments = [
        Segment(
            kind=seg["kind"],
            text=seg["text"],
            broll_keywords=list(seg.get("broll_keywords") or []),
        )
        for seg in segments_data
    ]

    if segments[0].kind != "avatar" or segments[-1].kind != "avatar":
        raise ValueError("script must open and close on an 'avatar' segment")

    return Script(title=data.get("title", topic), topic=topic, segments=segments)


def generate_script(topic: str, target_seconds: int, model: str, api_key: str) -> Script:
    """Call the Anthropic API to draft a script for `topic`."""
    import anthropic  # imported lazily so the module loads without the dep installed

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": build_prompt(topic, target_seconds)}],
    )
    raw = "".join(block.text for block in response.content if block.type == "text")
    return parse_script_json(raw, topic)
