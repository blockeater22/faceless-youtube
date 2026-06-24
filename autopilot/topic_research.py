"""AI-assisted topic research for the local video generator UI.

Does light "research" before suggesting: pulls recent high-view titles in the
channel's niche (best-effort via the YouTube API), then asks the model to analyse
what's working and propose *original* outlier angles with full packaging (title +
thumbnail idea + why-now rationale), rather than generic ideas.
"""
from __future__ import annotations

import datetime as dt

from autopilot import channels as _channels
from autopilot import gemini_pool, topics
from autopilot import trends as _trends


SYSTEM = """You are a senior YouTube packaging strategist + researcher for a faceless
animated channel. You think in terms of curiosity gaps, click-through rate, browse/
suggested traffic, and audience retention.

Your job: study the signals provided (the channel's niche, persona, the user's notes,
and recent high-performing titles in this niche), infer the PATTERNS that make them
work, then propose ORIGINAL "outlier" topic ideas — not copies. Each idea must be
packaged: a scroll-stopping angle, a thumbnail concept, and a clear reason it can win
attention right now.

Rules: never copy a supplied title; avoid medical/financial claims, celebrity drama,
politics, and copyrighted characters; keep ideas on-brand for the channel persona.
Return JSON only."""


def suggest_topics(
    seed_topics: str = "",
    *,
    count: int = 6,
    model: str | None = None,
    job_id: str | None = None,
    channel_id: str | None = None,
) -> dict:
    """Return ranked topic cards. Falls back to the built-in rotation when Gemini is down."""
    channel = _channels.get_channel(channel_id) if channel_id else None
    if gemini_pool.has_key():
        researched = _research_signals(channel)
        prompt = _build_prompt(seed_topics, count, channel, researched)
        try:
            data = gemini_pool.generate_json(
                prompt,
                system_instruction=SYSTEM,
                model=model,
                temperature=0.75,
                max_output_tokens=6000,
                job_id=job_id or seed_topics or "topic-research",
            )
            return {
                "topics": _sanitize(data.get("topics", []), count),
                "source": "gemini",
                "warning": None,
            }
        except Exception as exc:  # noqa: BLE001
            print(f"  [topics] Gemini unavailable ({exc}); using offline rotation")
            return {
                "topics": _offline_topics(count),
                "source": "fallback",
                "warning": (
                    "Gemini is temporarily busy. Showing offline topic ideas — "
                    "try AI Suggest again in a minute, or type your own topic."
                ),
            }

    return {
        "topics": _offline_topics(count),
        "source": "fallback",
        "warning": "No Gemini key configured; showing offline topic rotation.",
    }


def _research_signals(channel: dict | None) -> list[str]:
    """Best-effort recent high-view titles in this channel's niche (may be empty)."""
    queries = None
    if channel:
        rot = channel.get("rotation") or []
        name = channel.get("name", "")
        queries = [f"{k} {name}".strip() for k in rot][:5] or None
    try:
        return _trends.trending_titles(n=12, queries=queries)
    except Exception:  # noqa: BLE001
        return []


def _build_prompt(seed_topics: str, count: int, channel: dict | None = None,
                  researched: list[str] | None = None) -> str:
    persona = (channel or {}).get("persona", "a faceless reflective animation channel")
    niche = ", ".join((channel or {}).get("rotation", [])) or "reflection, what-if, how-to"
    research_block = ""
    if researched:
        joined = "\n".join(f"- {t}" for t in researched[:12])
        research_block = (
            "\n\nRecent high-performing titles in this niche (analyse the PATTERNS — "
            "curiosity, specificity, emotion — do NOT copy them):\n" + joined
        )
    return f"""Channel persona: {persona}
Channel content lanes: {niche}

Suggest {count} viral-but-ORIGINAL video topics for THIS channel. First infer what makes
work in this niche spread, then propose outlier angles with strong packaging.

User supplied notes / seed topics:
{seed_topics or '(none)'}{research_block}

For EACH idea also estimate, vidIQ-style, the YouTube demand and competition so we
can rank by opportunity (like vidIQ's Keyword Score = search volume vs competition):
- search_volume: "low" | "medium" | "high"  (how many people search this on YouTube)
- competition:   "low" | "medium" | "high"  (how many strong videos already rank)
Favour HIGH volume + LOW/MEDIUM competition (the "outlier" sweet spot).

Return this JSON shape:
{{
  "topics": [
    {{
      "brief": "one sentence topic brief",
      "kind": "whatif|howto|otheryou|reflection",
      "playlist": "playlist name",
      "thumb": "stars|bubbles|split|bigface",
      "title_angle": "clickable title angle",
      "audience": "who this is for",
      "trend_reason": "why it can work now",
      "search_volume": "low|medium|high",
      "competition": "low|medium|high",
      "novelty_score": 1,
      "risk_notes": "policy or originality risks",
      "desired_length": "shorts|3-5|6-8"
    }}
  ]
}}"""


# vidIQ-style Keyword Score: reward high search volume, penalise high competition.
_VOL_W = {"low": 22, "medium": 55, "high": 92}
_COMP_W = {"low": 0, "medium": 18, "high": 40}


def _keyword_score(volume: str, competition: str) -> int:
    """0..100 opportunity score, mirroring vidIQ's volume-vs-competition logic."""
    vol = _VOL_W.get(str(volume).lower(), 45)
    comp = _COMP_W.get(str(competition).lower(), 22)
    return max(1, min(100, round(vol - comp + 8)))


def _offline_topics(count: int) -> list[dict]:
    today = int(dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d"))
    picks = topics.next_batch(count, [], ["whatif", "howto", "otheryou", "reflection"], seed=today)
    for i, p in enumerate(picks, 1):
        p.update({
            "title_angle": p["brief"],
            "audience": "Viewers interested in deep thoughts and self-reflection",
            "trend_reason": "Evergreen curiosity topic from the channel rotation",
            "search_volume": "medium",
            "competition": "low",
            "keyword_score": _keyword_score("medium", "low"),
            "novelty_score": max(1, 8 - i),
            "risk_notes": "Offline fallback; review originality before publishing",
            "desired_length": "3-5",
        })
    return picks


def _sanitize(items: list[dict], count: int) -> list[dict]:
    out = []
    for item in items:
        if not isinstance(item, dict) or not item.get("brief"):
            continue
        kind = item.get("kind") if item.get("kind") in topics.KINDS else "reflection"
        spec = topics.KINDS[kind]
        volume = str(item.get("search_volume") or "medium").lower()
        competition = str(item.get("competition") or "medium").lower()
        score = item.get("keyword_score")
        score = int(score) if isinstance(score, (int, float)) else _keyword_score(volume, competition)
        out.append({
            "brief": str(item["brief"]).strip(),
            "kind": kind,
            "playlist": item.get("playlist") or spec["playlist"],
            "thumb": item.get("thumb") or spec["thumb"],
            "title_angle": item.get("title_angle") or item["brief"],
            "audience": item.get("audience") or "Reflective YouTube viewers",
            "trend_reason": item.get("trend_reason") or "High-curiosity evergreen angle",
            "search_volume": volume,
            "competition": competition,
            "keyword_score": max(1, min(100, score)),
            "novelty_score": int(item.get("novelty_score") or 5),
            "risk_notes": item.get("risk_notes") or "Review for originality",
            "desired_length": item.get("desired_length") or "3-5",
        })
    # Rank by opportunity (vidIQ-style): best keyword score first.
    out.sort(key=lambda t: t["keyword_score"], reverse=True)
    return out[:count]
