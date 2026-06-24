"""Reusable orchestration for one faceless video generation job."""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from autopilot import channels, produce, scriptwriter, scheduler, topics, trends as _trends
from autopilot.generate import _pick_topic, _write_sidecar
from autopilot.run import load_config, load_state, save_state
from faceless.model import Voice


Progress = Callable[..., None]


@dataclass
class GenerationRequest:
    topic: str = ""
    channel_id: str = "inklings"
    style: str = "stick"   # procedural sketch engine (not Pollinations)
    formats: tuple[str, ...] = ("16:9",)
    backend: str = "auto"
    provider: str = "auto"
    desired_length: str = "3-5"
    voice: str = ""        # blank -> use the channel's narrator
    speed: float = 0.0     # 0 -> use the channel's speed
    gap: float = 0.0
    outroot: str = "output"
    use_state: bool = True
    image_style: str | None = None
    image_model: str | None = None
    gemini_model: str | None = None


def generate_video(req: GenerationRequest, *, progress: Progress | None = None,
                   job_id: str | None = None) -> dict:
    """Generate script, images, voice, video, and metadata for one request."""
    progress = progress or (lambda *a, **k: None)
    channel = channels.get_channel(req.channel_id)
    cfg = channels.apply_to_config(load_config(), channel)
    state = load_state()
    cfg["kokoro_voice"] = req.voice or channel["voice"]["kokoro_voice"]
    cfg["kokoro_speed"] = req.speed or channel["voice"]["kokoro_speed"]
    cfg["gap"] = req.gap

    progress("topic", f"Selecting topic for {channel['name']}")
    topic = _topic_from_request(req, cfg, state)
    topic["desired_length"] = req.desired_length
    if req.desired_length == "shorts":
        req = GenerationRequest(**{**asdict(req), "formats": ("9:16",), "gap": min(req.gap, 0.05)})
        cfg["shorts"] = True

    progress("trends", "Collecting trend inspiration")
    trend_titles = []
    try:
        trend_titles = _trends.trending_titles()
    except Exception:
        pass

    progress("script", "Writing script and scene prompts")
    script = scriptwriter.write_script(
        topic,
        backend=req.backend or cfg.get("script_backend", "auto"),
        model=cfg.get("model"),
        gemini_model=req.gemini_model or cfg.get("gemini_model"),
        trends=trend_titles,
        desired_length=req.desired_length,
        job_id=job_id,
        persona=cfg.get("persona"),
        cta_style=cfg.get("cta_style", "warm"),
    )
    if req.desired_length == "shorts":
        script = _trim_shorts_script(script)
    _write_artifact(req.outroot, job_id, "script.json", script)

    slug = f"gen_{dt.datetime.now(dt.timezone.utc):%Y%m%d_%H%M%S}_{topic['kind']}"
    meta = scheduler.enrich_metadata(
        produce.build_metadata(script, topic, cfg),
        script,
        topic,
        slots_utc=cfg.get("publish_slots_utc"),
    )
    meta["channel_id"] = channel["id"]
    meta["channel_name"] = channel["name"]
    meta["channel_handle"] = channel.get("handle", "")

    n_beats = len(script.get("beats", []))
    est_render_s = _estimate_render_seconds(n_beats, req.formats, req.style)
    progress("render", f"Rendering {n_beats} scenes", {"beats": n_beats, "est_render_s": est_render_s})
    if req.style == "stick":
        cfg_local = dict(cfg, formats=list(req.formats), gap=req.gap)
        art = produce.produce(topic, script, cfg_local, slug=slug, outroot=req.outroot)
        video, thumb, story = art["video"], art["thumb"], art["story"]
    else:
        from autopilot.imagevideo import render_image_video

        outdir = Path(req.outroot) / slug
        voice = Voice(
            backend="kokoro",
            kokoro_voice=cfg.get("kokoro_voice", "am_liam"),
            kokoro_speed=cfg.get("kokoro_speed", 1.0),
            gap=req.gap,
        )
        videos = render_image_video(
            script,
            outdir,
            formats=req.formats,
            voice=voice,
            provider=req.provider or cfg.get("image_provider", "auto"),
            image_style=req.image_style if req.image_style is not None else cfg.get("image_style"),
            image_model=req.image_model if req.image_model is not None else cfg.get("image_model"),
            provider_order=None,
            logo_path=cfg.get("logo"),
        )
        video, thumb, story = videos[0], None, None

    progress("metadata", "Writing metadata and thumbnail")
    thumb = _generate_thumbnail(script, topic, Path(video), thumb, cfg=cfg, visual_style=req.style)
    side = _write_sidecar(meta, Path(video))
    Path(video).with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    Path(video).with_suffix(".script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

    if req.use_state:
        state["used_briefs"].append(topic["brief"])
        save_state(state)

    result = {
        "slug": slug,
        "channel": {"id": channel["id"], "name": channel["name"], "handle": channel.get("handle", "")},
        "topic": topic,
        "script": script,
        "video": str(video),
        "thumb": str(thumb) if thumb else None,
        "story": str(story) if story else None,
        "sidecar": str(side),
        "meta": meta,
    }
    progress("done", "Generation complete")
    return result


def _estimate_render_seconds(n_beats: int, formats, style: str) -> float:
    """Rough wall-clock estimate for the heavy render stage (for the UI ETA bar).

    Per-beat cost = TTS synth + frame drawing; image mode adds API image fetches.
    Multiple formats roughly multiply the frame-drawing cost.
    """
    per_beat = 8.5 if style == "stick" else 11.0
    fmt_factor = 1.0 + 0.8 * (max(1, len(tuple(formats))) - 1)
    return round(10.0 + n_beats * per_beat * fmt_factor, 1)


def _topic_from_request(req: GenerationRequest, cfg: dict, state: dict) -> dict:
    if req.topic:
        brief = req.topic.strip()
        kind = "howto" if brief.lower().startswith("how") else \
               "whatif" if brief.lower().startswith("what if") else "reflection"
        spec = topics.KINDS.get(kind, topics.KINDS["reflection"])
        return {"kind": kind, "playlist": spec["playlist"], "thumb": spec["thumb"], "brief": brief}
    return _pick_topic(state, cfg, None)


def _write_artifact(outroot: str, job_id: str | None, name: str, data: dict) -> None:
    if not job_id:
        return
    path = Path(outroot) / "_jobs" / job_id
    path.mkdir(parents=True, exist_ok=True)
    path.joinpath(name).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _generate_thumbnail(script: dict, topic: dict, video: Path,
                        existing: Path | None = None, *, cfg: dict | None = None,
                        visual_style: str = "stick") -> Path:
    """Create a high-CTR thumbnail beside the rendered video."""
    if existing and Path(existing).exists():
        return Path(existing)
    from autopilot.thumbnail import make_thumbnail

    hook = script.get("hook") or script.get("title") or topic.get("brief", "Untitled")
    kind = topic.get("thumb") or "bubbles"
    out = video.with_name(f"{video.stem}_thumb.png")
    return make_thumbnail(
        hook,
        kind,
        out,
        script=script,
        topic=topic,
        config=cfg or {},
        visual_style=visual_style,
    )


def _trim_shorts_script(script: dict, max_beats: int = 9) -> dict:
    """Keep Shorts under ~1 minute: hook + body + cta, capped beat count."""
    beats = script.get("beats", [])
    if len(beats) <= max_beats:
        return script
    hook = beats[0] if beats[0].get("template") == "hook" else None
    cta = next((b for b in reversed(beats) if b.get("template") == "cta"), None)
    body = [b for b in beats if b is not hook and b is not cta]
    keep_body = max(1, max_beats - (1 if hook else 0) - (1 if cta else 0))
    trimmed = []
    if hook:
        trimmed.append(hook)
    trimmed.extend(body[:keep_body])
    if cta and cta not in trimmed:
        trimmed.append(cta)
    out = dict(script)
    out["beats"] = trimmed
    return out


def request_from_form(data: dict) -> GenerationRequest:
    desired = data.get("desired_length", "3-5")
    fmt = data.get("format", "16:9")
    if desired == "shorts":
        fmt = "9:16"
    formats = ("16:9", "9:16") if fmt == "both" else (fmt,)
    return GenerationRequest(
        topic=data.get("topic", ""),
        channel_id=data.get("channel_id") or "inklings",
        style=data.get("style", "stick"),
        formats=formats,
        backend=data.get("backend", "auto"),
        provider=data.get("provider", "auto"),
        desired_length=desired,
        voice=data.get("voice", "") or "",
        speed=float(data.get("speed") or 0.0),
        gap=float(data.get("gap") or 0.0),
        outroot=data.get("outroot", "output"),
        use_state=bool(data.get("use_state", True)),
        image_style=data.get("image_style") or None,
        image_model=data.get("image_model") or None,
        gemini_model=data.get("gemini_model") or None,
    )


def asdict_request(req: GenerationRequest) -> dict:
    data = asdict(req)
    data["formats"] = list(req.formats)
    return data
