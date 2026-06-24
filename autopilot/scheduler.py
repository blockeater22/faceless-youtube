"""Metadata enrichment and lightweight publish-time recommendations."""
from __future__ import annotations

import datetime as dt


DEFAULT_WINDOWS_UTC = ("13:00", "01:00")


def recommend_schedule(topic: dict, *, audience_tz: str = "US/Eastern",
                       slots_utc: list[str] | None = None) -> dict:
    """Pick a practical publish window without requiring YouTube Analytics."""
    slots = slots_utc or list(DEFAULT_WINDOWS_UTC)
    kind = topic.get("kind", "reflection")
    preferred = "01:00" if kind in {"reflection", "otheryou"} else "13:00"
    slot = preferred if preferred in slots else slots[0]
    publish_at = _next_slot(slot)
    return {
        "recommended_utc": publish_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "slot_utc": slot,
        "audience_tz": audience_tz,
        "reason": _reason(kind, slot),
    }


def enrich_metadata(meta: dict, script: dict, topic: dict, *, slots_utc: list[str] | None = None) -> dict:
    schedule = recommend_schedule(topic, slots_utc=slots_utc)
    hook = script.get("hook") or meta.get("title", "")
    title = meta.get("title", "")
    title_variants = [
        title,
        f"{hook}: {title}"[:96],
        f"What if {topic.get('brief', title).rstrip('?')}?"[:96],
    ]
    pinned = _pinned_comment(script, topic)
    enriched = dict(meta)
    enriched.update({
        "title_variants": _dedupe(title_variants),
        "thumbnail_prompt": _thumbnail_prompt(script, topic),
        "pinned_comment": pinned,
        "schedule": schedule,
    })
    return enriched


def _next_slot(slot: str) -> dt.datetime:
    now = dt.datetime.now(dt.timezone.utc)
    hh, mm = (int(x) for x in slot.split(":"))
    for day in range(4):
        cand = now + dt.timedelta(days=day)
        cand = cand.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if cand > now + dt.timedelta(minutes=20):
            return cand
    return now + dt.timedelta(hours=2)


def _reason(kind: str, slot: str) -> str:
    if slot == "01:00":
        return "Evening US window fits reflective and emotional videos that perform well during late scrolling."
    if kind == "howto":
        return "Morning US window fits self-improvement viewers looking for practical ideas."
    return "Midday US window is a safe default for broad English-speaking reach."


def _thumbnail_prompt(script: dict, topic: dict) -> str:
    headline = script.get("thumbnail_text") or script.get("hook") or script.get("title", "")
    return (
        "High-CTR YouTube thumbnail background, cinematic, one bold symbolic subject, "
        f"topic mood: {headline or topic.get('brief', '')}, "
        "dramatic lighting, dark background, amber/teal accents, "
        "NO text, NO words, NO watermark, mobile-readable composition."
    )


def _pinned_comment(script: dict, topic: dict) -> str:
    for beat in reversed(script.get("beats", [])):
        text = beat.get("narration", "")
        if "?" in text:
            return text.split("?")[0].strip() + "?"
    return f"Which part of {topic.get('brief', 'this idea')} stayed with you?"


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        clean = item.strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            out.append(clean)
    return out
