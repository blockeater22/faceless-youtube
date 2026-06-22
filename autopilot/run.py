"""Autopilot entry point: generate -> render -> thumbnail -> upload, N videos.

    python -m autopilot.run                 # use config defaults
    python -m autopilot.run --count 2
    python -m autopilot.run --no-upload     # produce locally, skip YouTube
    python -m autopilot.run --backend offline

State (autopilot/state.json) tracks used briefs (no repeats) and published videos.
In CI the workflow commits state.json back to the repo after each run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from autopilot import produce as _produce  # noqa: E402
from autopilot import scriptwriter, topics, trends as _trends  # noqa: E402

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
STATE_PATH = Path(__file__).resolve().parent / "state.json"


def load_config():
    cfg = json.loads(CONFIG_PATH.read_text())
    # environment overrides (handy for CI without editing the file)
    for env, key, cast in [("VIDEOS_PER_DAY", "videos_per_day", int),
                           ("PUBLISH_MODE", "publish_mode", str),
                           ("SCRIPT_BACKEND", "script_backend", str),
                           ("MODEL", "model", str)]:
        if os.environ.get(env):
            cfg[key] = cast(os.environ[env])
    return cfg


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"used_briefs": [], "published": []}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2))


def compute_publish_at(slots, index):
    """RFC3339 UTC for the index-th upcoming slot (HH:MM strings, UTC)."""
    now = dt.datetime.now(dt.timezone.utc)
    cands = []
    for day in range(0, 4):
        base = (now + dt.timedelta(days=day)).date()
        for s in slots:
            hh, mm = (int(x) for x in s.split(":"))
            t = dt.datetime(base.year, base.month, base.day, hh, mm, tzinfo=dt.timezone.utc)
            if t > now + dt.timedelta(minutes=10):
                cands.append(t)
    cands.sort()
    pick = cands[index % len(cands)] if cands else now + dt.timedelta(hours=2)
    return pick.strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv=None):
    p = argparse.ArgumentParser(prog="autopilot.run")
    p.add_argument("--count", type=int)
    p.add_argument("--publish", choices=["schedule", "public", "private"])
    p.add_argument("--backend", choices=["auto", "claude", "offline"])
    p.add_argument("--no-upload", action="store_true", help="produce only, skip YouTube")
    p.add_argument("--outroot", default="output")
    args = p.parse_args(argv)

    cfg = load_config()
    state = load_state()
    count = args.count or cfg.get("videos_per_day", 2)
    backend = args.backend or cfg.get("script_backend", "auto")
    publish_mode = args.publish or cfg.get("publish_mode", "schedule")
    today = int(dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d"))

    picks = topics.next_batch(count, state["used_briefs"], cfg.get("rotation", []),
                              seed=today + len(state["used_briefs"]))
    print(f"Autopilot: {count} video(s) | backend={backend} | publish={publish_mode}")

    trend_titles = []
    try:
        trend_titles = _trends.trending_titles()
        if trend_titles:
            print(f"  pulled {len(trend_titles)} trending niche titles for inspiration")
    except Exception as exc:  # noqa: BLE001
        print(f"  [trends] skipped ({exc})")

    results, failures = [], 0
    for i, topic in enumerate(picks):
        print(f"\n=== [{i+1}/{count}] {topic['kind']}: {topic['brief']} ===")
        try:
            script = scriptwriter.write_script(topic, backend=backend, model=cfg.get("model"),
                                               trends=trend_titles)
            slug = f"auto_{dt.datetime.now(dt.timezone.utc):%Y%m%d}_{topic['kind']}_{i}"
            art = _produce.produce(topic, script, cfg, slug=slug, outroot=args.outroot)
            print(f"  rendered {art['video'].name}  ({art['video'].stat().st_size/1e6:.1f} MB)")
            state["used_briefs"].append(topic["brief"])
            entry = {"date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                     "title": art["meta"]["title"], "slug": slug,
                     "playlist": topic["playlist"], "video_id": None}
            if not args.no_upload:
                from autopilot import youtube  # lazy: needs google libs
                publish_at = compute_publish_at(cfg.get("publish_slots_utc", ["13:00"]), i) \
                    if publish_mode == "schedule" else None
                privacy = "public" if publish_mode == "public" else "private"
                vid = youtube.publish(art, privacy=privacy, publish_at=publish_at,
                                      category_id=cfg.get("category_id", "22"))
                entry["video_id"] = vid
                entry["publish_at"] = publish_at
                print(f"  uploaded: https://youtu.be/{vid}"
                      + (f"  (goes public {publish_at})" if publish_at else f"  ({privacy})"))
            state["published"].append(entry)
            results.append(entry)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  FAILED: {exc}")
            traceback.print_exc()

    save_state(state)
    print(f"\nDone: {len(results)} ok, {failures} failed.")
    return 1 if failures and not results else 0


if __name__ == "__main__":
    raise SystemExit(main())
