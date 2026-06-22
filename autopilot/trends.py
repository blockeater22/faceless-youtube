"""See what's working *right now* in our niche, to steer topic + framing choices.

Queries the YouTube Data API for recent high-view videos in the channel's themes
and returns their titles. The scriptwriter uses these as inspiration (angle,
framing, title energy) — never to copy. Best-effort: returns [] if creds/quota
are unavailable, so the pipeline still runs on its built-in topic pool.

Cost note: search.list is 100 quota units per call; keep NICHE_QUERIES small.
"""
from __future__ import annotations

import datetime as dt

NICHE_QUERIES = [
    "what if philosophy animation",
    "deep thoughts that will change you",
    "how to stop overthinking",
    "psychology of being alone",
    "stoic philosophy motivation",
]


def trending_titles(n: int = 12, days: int = 150, queries: list[str] | None = None) -> list[str]:
    """Up to ``n`` recent, high-view video titles in our niche (sorted by views)."""
    try:
        from autopilot.youtube import service
        yt = service()
    except Exception:
        return []
    after = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen, titles = set(), []
    for q in (queries or NICHE_QUERIES):
        try:
            resp = yt.search().list(
                part="snippet", q=q, type="video", order="viewCount",
                publishedAfter=after, maxResults=5,
                relevanceLanguage="en", videoDuration="medium",
            ).execute()
        except Exception:
            continue
        for item in resp.get("items", []):
            t = (item.get("snippet", {}).get("title") or "").strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                titles.append(t)
    return titles[:n]
