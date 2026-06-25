"""The "Inklings" Scripting SOP, encoded as code instead of left as a doc.

Source: the channel's own extracted SOP from its best-performing video
(8qkmSjGpeFU) plus the vidIQ content-mill audit. The point of this module is
that a script can FAIL these rules mechanically (via ``scripts/lint_script.py``)
instead of relying on someone remembering the doc under volume pressure -
that drift is exactly what produced the 36-videos/week problem in the first
place.

Public surface:
    BEAT_ORDER                         the 4 required beats, in order
    validate_topic(topic) -> [str]     hard-rule violations for one topic dict
    validate_title(title) -> [str]     title-formula violations
    title_why(behavior, outcome)       SOP title formula 1
    title_number(n, noun, benefit)     SOP title formula 2
    format_cta(question)               wraps a question into the CTA line
"""
from __future__ import annotations

import re

BEAT_ORDER = ("hook", "explain", "reframe", "cta")

# Rule 2 ("Explicit NO rules") + rule 7 (never ask for Subscribe): a deny-list
# checked against every spoken line, not just the CTA.
BANNED_PHRASES = (
    "hi everyone", "welcome back", "hey guys", "hey everyone",
    "subscribe", "smash that", "like this video", "hit the bell",
    "basically", "actually", "so yeah", "kind of", "sort of",
)

CTA_SUFFIX = "Drop it below."
MAX_HOOK_WORDS = 9              # ~3s of speech at a contemplative pace
SENTENCE_WORDS_RANGE = (4, 13)  # rule 2's "5-12 words" with a little slack

_NUM_TITLE_RE = re.compile(r"^\d+\s+\S")
_WHY_TITLE_RE = re.compile(r"^Why\s+\S", re.I)


def banned_phrase_hits(text: str) -> list[str]:
    t = (text or "").lower()
    return [p for p in BANNED_PHRASES if p in t]


def hook_word_count(hook: str) -> int:
    return len((hook or "").split())


def sentence_lengths(text: str) -> list[int]:
    sentences = [s.strip() for s in re.split(r"[.!?]+", text or "") if s.strip()]
    return [len(s.split()) for s in sentences]


def has_specificity_spike(spike: str, *texts: str) -> bool:
    joined = " ".join(texts).lower()
    return bool(spike) and spike.lower() in joined


def is_question_cta(cta: str) -> bool:
    return "?" in (cta or "")


def title_why(behavior: str, outcome: str) -> str:
    """SOP title formula: "Why [uncomfortable behavior] [psychological outcome]"."""
    return f"Why {behavior} {outcome}"


def title_number(n: int, noun: str, benefit: str) -> str:
    """SOP title formula: "[Number] [Habits/Effects/Signs] [Benefit]"."""
    return f"{n} {noun} {benefit}"


def validate_title(title: str) -> list[str]:
    if _NUM_TITLE_RE.match(title or "") or _WHY_TITLE_RE.match(title or ""):
        return []
    return [f"title {title!r} matches neither the '[N] ...' nor the 'Why ...' SOP formula"]


def format_cta(question: str) -> str:
    q = (question or "").strip()
    if not q.endswith("?"):
        q += "?"
    return f"{q} {CTA_SUFFIX}"


def validate_topic(t: dict) -> list[str]:
    """Run every hard rule against one topic dict. Topic dicts must provide:
    hook, explain, reframe, cta_question, specificity, title."""
    errors: list[str] = []
    hook, explain, reframe = t.get("hook", ""), t.get("explain", ""), t.get("reframe", "")
    cta_question, spike, title = t.get("cta_question", ""), t.get("specificity", ""), t.get("title", "")

    n = hook_word_count(hook)
    if n > MAX_HOOK_WORDS:
        errors.append(f"hook is {n} words, must be <= {MAX_HOOK_WORDS} (~3s of speech)")

    for field_name, text in (("hook", hook), ("explain", explain), ("reframe", reframe),
                              ("cta_question", cta_question)):
        hits = banned_phrase_hits(text)
        if hits:
            errors.append(f"{field_name} contains banned phrase(s): {hits}")

    if not has_specificity_spike(spike, hook, explain):
        errors.append(f"specificity spike {spike!r} not found verbatim in hook/explain")

    if not is_question_cta(cta_question):
        errors.append("cta_question must be phrased as a question (rule 6/7: ask, don't ask-to-subscribe)")

    for field_name, text in (("explain", explain), ("reframe", reframe)):
        for ln in sentence_lengths(text):
            if not (SENTENCE_WORDS_RANGE[0] <= ln <= SENTENCE_WORDS_RANGE[1]):
                errors.append(f"{field_name} has a {ln}-word sentence (target {SENTENCE_WORDS_RANGE})")

    errors.extend(f"title: {e}" for e in validate_title(title))
    return errors
