"""One command -> one finished video + title/description/tags.

    python -m autopilot.generate                  # pick a trending topic, stick-figure long-form
    python -m autopilot.generate --style image     # AI-image slideshow instead
    python -m autopilot.generate --shorts          # 9:16 Short
    python -m autopilot.generate --topic "What if your phone showed why you really open it?"
    python -m autopilot.generate --voice am_liam --speed 0.9 --provider pollinations

It writes the .mp4 plus a sidecar `<slug>.txt` (paste-ready title, description,
tags) into output/<slug>/. It does NOT upload — you review, then publish (or run
`python -m autopilot.run` for the upload pipeline). Free by default: Gemini key
for the script (falls back to offline), Kokoro for voice, Pollinations for images.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from autopilot import produce as _produce  # noqa: E402
from autopilot import scriptwriter, topics, trends as _trends  # noqa: E402
from autopilot.run import CONFIG_PATH, STATE_PATH, load_config, load_state, save_state  # noqa: E402


def _pick_topic(state, cfg, brief: str | None):
    if brief:
        kind = "howto" if brief.lower().startswith("how") else \
               "whatif" if brief.lower().startswith("what if") else "reflection"
        return {"kind": kind, "playlist": "3 AM Thoughts", "thumb": "stars", "brief": brief}
    today = int(dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d"))
    picks = topics.next_batch(1, state["used_briefs"], cfg.get("rotation", []),
                              seed=today + len(state["used_briefs"]))
    return picks[0]


def _write_sidecar(meta: dict, video: Path) -> Path:
    side = video.with_suffix(".txt")
    body = (f"TITLE\n{meta['title']}\n\n"
            f"DESCRIPTION\n{meta['description']}\n\n"
            f"TAGS\n{', '.join(meta['tags'])}\n\n"
            f"HASHTAGS\n{' '.join(meta.get('hashtags', []))}\n")
    side.write_text(body, encoding="utf-8")
    video.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return side


def main(argv=None):
    p = argparse.ArgumentParser(prog="autopilot.generate")
    p.add_argument("--style", choices=["stick", "image"], default="stick",
                   help="stick = procedural stick-figures (on-brand, fully offline); "
                        "image = AI-image slideshow (Pollinations/Cloudflare/HF)")
    p.add_argument("--format", choices=["16:9", "9:16", "both"], default="16:9")
    p.add_argument("--shorts", action="store_true", help="shorthand for --format 9:16")
    p.add_argument("--topic", help="a free-text brief; omit to auto-pick a trending one")
    p.add_argument("--backend", choices=["auto", "gemini", "claude_code", "claude", "offline"],
                   default=None)
    p.add_argument("--voice", help="Kokoro voice id, e.g. am_liam, am_michael, af_heart")
    p.add_argument("--speed", type=float, help="Kokoro speed (0.85 calm .. 1.1 punchy)")
    p.add_argument("--provider", choices=["pollinations", "cloudflare", "huggingface"],
                   default=None, help="image provider (image style only)")
    p.add_argument("--outroot", default="output")
    p.add_argument("--no-state", action="store_true", help="don't record the brief as used")
    args = p.parse_args(argv)

    cfg = load_config()
    state = load_state()
    if args.voice:
        cfg["kokoro_voice"] = args.voice
    if args.speed:
        cfg["kokoro_speed"] = args.speed
    formats = ["9:16"] if args.shorts else [args.format] if args.format != "both" else ["16:9", "9:16"]
    backend = args.backend or cfg.get("script_backend", "auto")

    topic = _pick_topic(state, cfg, args.topic)
    print(f"Topic [{topic['kind']}]: {topic['brief']}")

    trend_titles = []
    try:
        trend_titles = _trends.trending_titles()
    except Exception:  # noqa: BLE001
        pass

    print(f"Writing script (backend={backend}) ...")
    script = scriptwriter.write_script(topic, backend=backend, model=cfg.get("model"),
                                       trends=trend_titles)
    print(f"  title: {script['title']}  ({len(script['beats'])} beats)")

    slug = f"gen_{dt.datetime.now(dt.timezone.utc):%Y%m%d_%H%M}_{topic['kind']}"
    meta = _produce.build_metadata(script, topic)

    if args.style == "image":
        from autopilot.imagevideo import render_image_video
        from faceless.model import Voice
        voice = Voice(backend="kokoro",
                      kokoro_voice=cfg.get("kokoro_voice", "am_liam"),
                      kokoro_speed=cfg.get("kokoro_speed", 0.9))
        outdir = Path(args.outroot) / slug
        provider = args.provider or cfg.get("image_provider", "pollinations")
        videos = render_image_video(script, outdir, formats=tuple(formats), voice=voice,
                                    provider=provider, image_style=cfg.get("image_style"),
                                    image_model=cfg.get("image_model"))
        video = videos[0]
        thumb = None
    else:
        cfg_local = dict(cfg, formats=formats)
        art = _produce.produce(topic, script, cfg_local, slug=slug, outroot=args.outroot)
        video, thumb, meta = art["video"], art["thumb"], art["meta"]

    side = _write_sidecar(meta, Path(video))
    if not args.no_state:
        state["used_briefs"].append(topic["brief"])
        save_state(state)

    print("\n" + "=" * 60)
    print(f"DONE  ->  {video}")
    if thumb:
        print(f"thumb ->  {thumb}")
    print(f"meta  ->  {side}")
    print(f"\nTitle: {meta['title']}")
    print(f"Tags:  {', '.join(meta['tags'][:12])}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
