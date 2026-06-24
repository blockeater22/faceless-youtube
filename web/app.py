"""Local FastAPI UI for the faceless viral video generator.

Run:
    uvicorn web.app:app --reload --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from autopilot.env_loader import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load_dotenv() -> None:
    load_dotenv()


_load_dotenv()

from autopilot import channels, jobs, topic_research, channel_architect  # noqa: E402
from autopilot.pipeline import request_from_form  # noqa: E402
from web import voices as voice_catalog  # noqa: E402

app = FastAPI(title="Faceless Viral Video Generator")

OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)
app.mount("/output", StaticFiles(directory=str(OUTPUT)), name="output")

BRANDING = ROOT / "branding"
BRANDING.mkdir(exist_ok=True)
app.mount("/branding", StaticFiles(directory=str(BRANDING)), name="branding")


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return HTML


@app.post("/api/channels/generate")
async def generate_channel(request: Request) -> dict:
    """AI channel concept + profile/banner/watermark assets + save to registry."""
    body: dict = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    image_provider = body.get("image_provider") or "auto"
    try:
        concept = channel_architect.generate_channel_concept()
        ch = channels.add_channel({
            "name": concept.get("name"),
            "handle": concept.get("handle"),
            "description": concept.get("description"),
            "persona": concept.get("persona"),
            "palette": concept.get("palette", {}),
            "colors": concept.get("colors", []),
            "figure": concept.get("figure", {}),
            "rotation": concept.get("rotation", []),
            "logo_prompt": concept.get("logo_prompt"),
            "banner_prompt": concept.get("banner_prompt"),
            "cta_style": concept.get("cta_style", "energetic"),
            "hashtags": concept.get("hashtags", []),
            "image_provider": image_provider,
            "generate_assets": True,
        })
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    row = dict(ch)
    row["description"] = concept.get("description")
    row["asset_urls"] = _channel_assets_urls(ch)
    listed = []
    for c in channels.list_channels():
        item = dict(c)
        item["asset_urls"] = _channel_assets_urls(c)
        listed.append(item)
    return {"channel": row, "channels": listed}


@app.get("/api/gemini")
def gemini_status(probe: bool = Query(False)) -> dict:
    """Gemini key pool + model fallback chain (for the script UI)."""
    from autopilot import gemini_pool

    pool = gemini_pool.keys()
    payload = {
        "configured": len(pool),
        "available_keys": sum(1 for k in pool if k.available),
        "dead_keys": [k.index for k in pool if k.dead],
        "models": [
            {"id": "gemini-auto", "name": "Auto (try all)", "description": "Cycles through all free-tier models"},
            {"id": "gemini-3.5-flash", "name": "3.5 Flash", "description": "Latest free frontier model"},
            {"id": "gemini-3.1-flash-lite", "name": "3.1 Flash Lite", "description": "Fastest efficient model"},
            {"id": "gemini-3-flash", "name": "3.0 Flash", "description": "Standard flash model"},
            {"id": "gemini-2.5-flash", "name": "2.5 Flash", "description": "Reliable fallback"},
            {"id": "gemini-2.5-flash-lite", "name": "2.5 Flash Lite", "description": "Lightweight fallback"},
        ],
        "fallback_chain": list(gemini_pool.model_fallbacks()),
        "default": "gemini-auto",
    }
    if probe:
        payload["key_health"] = gemini_pool.probe_keys()
        payload["available_keys"] = sum(1 for r in payload["key_health"] if r["status"] == "ok")
    return payload


@app.get("/api/providers")
def list_providers() -> dict:
    """Image providers + whether their API keys are configured (Pollinations needs none)."""
    cf = bool(os.environ.get("CF_ACCOUNT_ID") and os.environ.get("CF_API_TOKEN"))
    hf = bool(os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN"))
    return {
        "providers": [
            {"id": "pollinations", "name": "Pollinations", "ready": True, "needs_key": False},
            {"id": "cloudflare", "name": "Cloudflare Workers AI", "ready": cf, "needs_key": True},
            {
                "id": "huggingface",
                "name": "Hugging Face",
                "ready": hf,
                "needs_key": True,
                "note": "Rate-limited (~1 req/4s). Auto falls back to Pollinations on 429/quota.",
            },
            {"id": "auto", "name": "Auto (failover)", "ready": True, "needs_key": False},
        ],
        "default": "auto",
    }


def _output_url(path: Path) -> str | None:
    try:
        rel = path.resolve().relative_to(OUTPUT.resolve())
        return f"/output/{rel.as_posix()}"
    except Exception:
        return None


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@app.get("/api/videos")
def list_videos() -> dict:
    """List generated videos with metadata/download links for the UI library."""
    videos = []
    for video in sorted(OUTPUT.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        if "_imgwork" in video.parts:
            continue
        base = video.with_suffix("")
        meta_path = base.with_suffix(".meta.json")
        script_path = base.with_suffix(".script.json")
        sidecar_path = base.with_suffix(".txt")
        meta = _read_json(meta_path)
        script = _read_json(script_path)
        thumb = video.with_name(video.stem.replace("_9x16", "").replace("_16x9", "") + "_thumb.png")
        if not thumb.exists():
            thumbs = list(video.parent.glob("*_thumb.png"))
            thumb = thumbs[0] if thumbs else Path()
        videos.append({
            "id": f"{video.parent.name}/{video.name}",
            "name": video.stem,
            "title": meta.get("title") or script.get("title") or video.stem,
            "channel_id": meta.get("channel_id") or "",
            "channel_name": meta.get("channel_name") or "",
            "channel_handle": meta.get("channel_handle") or "",
            "created": video.stat().st_mtime,
            "size": video.stat().st_size,
            "video_url": _output_url(video),
            "thumb_url": _output_url(thumb) if thumb and thumb.exists() else None,
            "meta_url": _output_url(meta_path) if meta_path.exists() else None,
            "script_url": _output_url(script_path) if script_path.exists() else None,
            "sidecar_url": _output_url(sidecar_path) if sidecar_path.exists() else None,
            "description": (meta.get("description") or "")[:220],
            "tags": meta.get("tags") or [],
            "hashtags": meta.get("hashtags") or [],
        })
    return {"videos": videos}


def _channel_assets_urls(channel: dict) -> dict[str, str | None]:
    assets = channel.get("assets") or {}
    out: dict[str, str | None] = {}
    for key in ("profile", "banner", "watermark"):
        rel = assets.get(key)
        if rel:
            out[key] = f"/{rel.lstrip('/')}"
        else:
            out[key] = None
    return out


@app.get("/api/channels")
def list_channels_api() -> dict:
    """All channels with per-channel video counts from the output library."""
    counts: dict[str, int] = {}
    for video in OUTPUT.rglob("*.mp4"):
        if "_imgwork" in video.parts:
            continue
        meta = _read_json(video.with_suffix(".meta.json"))
        cid = meta.get("channel_id") or ""
        if cid:
            counts[cid] = counts.get(cid, 0) + 1
    out = []
    for ch in channels.list_channels():
        row = dict(ch)
        row["video_count"] = counts.get(ch["id"], 0)
        row["asset_urls"] = _channel_assets_urls(ch)
        out.append(row)
    return {"channels": out}


@app.post("/api/channels")
async def create_channel(request: Request) -> dict:
    data = await request.json()
    try:
        ch = channels.add_channel(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = dict(ch)
    row["asset_urls"] = _channel_assets_urls(ch)
    listed = []
    for c in channels.list_channels():
        item = dict(c)
        item["asset_urls"] = _channel_assets_urls(c)
        listed.append(item)
    return {"channel": row, "channels": listed}


@app.get("/api/voices")
def list_voices() -> dict:
    return voice_catalog.catalog_for_api()


@app.get("/api/voices/{voice_id}/preview")
def preview_voice(voice_id: str, speed: float = Query(1.0, ge=0.5, le=2.0)) -> FileResponse:
    try:
        path = voice_catalog.ensure_preview(voice_id, speed=speed)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"preview failed: {exc}") from exc
    return FileResponse(path, media_type="audio/wav", filename=f"{voice_id}.wav")


def _resolve_gemini_model(value: str | None) -> str | None:
    if not value or value == "gemini-auto":
        return None
    return value


@app.post("/api/suggest")
async def suggest(request: Request) -> dict:
    data = await request.json()
    return topic_research.suggest_topics(
        data.get("seed_topics", ""),
        count=int(data.get("count") or 6),
        model=_resolve_gemini_model(data.get("gemini_model")),
        channel_id=data.get("channel_id") or None,
    )


@app.post("/api/jobs")
async def create_job(request: Request) -> dict:
    data = await request.json()
    job = jobs.create_job(request_from_form(data))
    return jobs.serialize(job)


@app.get("/api/jobs")
def list_jobs() -> dict:
    return {"jobs": [jobs.serialize(j) for j in jobs.list_jobs()]}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    data = jobs.serialize(job)
    if data.get("result"):
        _make_browser_paths(data["result"])
    return data


def _make_browser_paths(result: dict) -> None:
    for key in ("video", "thumb"):
        value = result.get(key)
        if not value:
            continue
        path = Path(value)
        try:
            rel = path.resolve().relative_to(OUTPUT.resolve())
            result[f"{key}_url"] = f"/output/{rel.as_posix()}"
        except Exception:
            if not path.is_absolute():
                result[f"{key}_url"] = "/" + path.as_posix()


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Faceless Viral Video Generator</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    body { margin: 0; background: #090b12; color: #f5f2ea; }
    .site-header { border-bottom: 1px solid #242938; background: #0c0f18; position: sticky; top: 0; z-index: 20; }
    .site-header-inner { max-width: 1180px; margin: 0 auto; padding: 18px 20px 0; display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 14px; }
    .site-brand h1 { margin: 0 0 4px; font-size: 28px; letter-spacing: -0.04em; }
    .site-brand p { margin: 0 0 12px; color: #8f98ad; font-size: 13px; line-height: 1.4; }
    .site-nav { display: flex; gap: 6px; padding-bottom: 0; }
    .nav-tab { border: 1px solid transparent; border-radius: 12px 12px 0 0; padding: 10px 18px; font-weight: 700; cursor: pointer; background: transparent; color: #9ea7bc; }
    .nav-tab.active { background: #10131d; color: #ffb454; border-color: #242938; border-bottom-color: #10131d; margin-bottom: -1px; }
    .view-panel { display: none; }
    .view-panel.active { display: block; }
    main { max-width: 1180px; margin: 0 auto; padding: 24px 20px 80px; }
    h1 { margin: 0 0 8px; font-size: 34px; letter-spacing: -0.04em; }
    h2 { margin: 0 0 6px; font-size: 20px; letter-spacing: -0.02em; }
    p { color: #aab1c3; line-height: 1.55; }
    .grid { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 18px; }
    .card { border: 1px solid #242938; background: #10131d; border-radius: 18px; padding: 18px; }
    label { display: block; margin: 14px 0 6px; color: #d9dded; font-size: 13px; font-weight: 650; }
    input, textarea, select { width: 100%; box-sizing: border-box; border: 1px solid #30374b; border-radius: 12px; background: #090b12; color: #f5f2ea; padding: 11px 12px; font: inherit; }
    textarea { min-height: 130px; resize: vertical; }
    button { border: 0; border-radius: 999px; padding: 11px 16px; font-weight: 750; cursor: pointer; background: #ffb454; color: #15110a; }
    button.secondary { background: #202637; color: #f5f2ea; border: 1px solid #343c52; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
    .topic { border: 1px solid #293149; border-radius: 14px; padding: 12px; margin-top: 10px; background: #0b0e16; }
    .topic strong { display: block; margin-bottom: 5px; }
    .topic small { color: #9ea7bc; }
    pre { white-space: pre-wrap; word-break: break-word; background: #080a10; border-radius: 12px; padding: 12px; border: 1px solid #252b3b; color: #cbd5e1; max-height: 360px; overflow: auto; }
    video, .thumb { width: 100%; margin-top: 14px; border-radius: 14px; border: 1px solid #293149; }
    .media-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 14px; }
    .copy-block { margin-top: 14px; }
    .copy-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 6px; }
    .copy-head label { margin: 0; font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: #9ea7bc; }
    .copy-head button { padding: 6px 12px; font-size: 12px; border-radius: 999px; }
    .copy-area { width: 100%; min-height: 54px; box-sizing: border-box; border: 1px solid #30374b; border-radius: 12px; background: #090b12; color: #f5f2ea; padding: 10px 12px; font: inherit; resize: vertical; }
    .copy-area.tall { min-height: 160px; }
    .toast { position: fixed; right: 18px; bottom: 18px; background: #1d2433; border: 1px solid #3a4358; color: #f5f2ea; padding: 10px 14px; border-radius: 12px; opacity: 0; transition: opacity .2s; pointer-events: none; }
    .toast.show { opacity: 1; }
    a { color: #ffcf8a; }
    .status { color: #ffcf8a; font-weight: 700; }
    .voice-picker { display: flex; gap: 8px; align-items: center; }
    .voice-picker select { flex: 1; min-width: 0; }
    .voice-picker button { flex: 0 0 auto; white-space: nowrap; padding: 10px 14px; }
    .voice-hint { margin-top: 6px; font-size: 12px; color: #8f98ad; min-height: 18px; }
    .warn { margin-top: 10px; padding: 10px 12px; border-radius: 12px; border: 1px solid #5a4520; background: #1f1810; color: #ffcf8a; font-size: 13px; line-height: 1.45; }
    .channel-bar { display: flex; gap: 10px; align-items: flex-end; }
    .channel-bar > div:first-child { flex: 1; }
    .swatches { display: flex; gap: 6px; margin-top: 8px; }
    .swatch { width: 22px; height: 22px; border-radius: 6px; border: 1px solid #00000055; }
    .chip { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: #aab1c3; margin-top: 6px; }
    .addchan { margin-top: 12px; border: 1px dashed #343c52; border-radius: 12px; padding: 12px; display: none; }
    .addchan.open { display: block; }
    .addchan .row { grid-template-columns: 1fr 1fr; }
    .progress-wrap { margin: 8px 0 4px; }
    .progress-track { width: 100%; height: 12px; background: #0a0d15; border: 1px solid #2a3142; border-radius: 999px; overflow: hidden; }
    .progress-fill { height: 100%; width: 0%; background: linear-gradient(90deg, #ffb454, #ffcf8a); border-radius: 999px; transition: width .5s ease; }
    .progress-meta { display: flex; justify-content: space-between; font-size: 12px; color: #aab1c3; margin-top: 6px; }
    input[type=color] { padding: 2px; height: 42px; }
    @media (max-width: 860px) { .grid, .row, .media-grid { grid-template-columns: 1fr; } }
    .gen-btn { background: #3b2b50 !important; color: #e2c1ff !important; border: 1px solid #6b4d8c !important; }
    .gen-btn:hover { background: #4a3663 !important; }
    .ai-concept-preview { background: #16181d; padding: 12px; border-radius: 6px; font-size: 13px; font-family: monospace; white-space: pre-wrap; margin-top: 10px; border: 1px solid #333; max-height: 200px; overflow-y: auto; color: #a1aab8; display: none; }
    .library-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
    .library-section { margin-top: 22px; }
    .library-section:first-child { margin-top: 0; }
    .library-section > p { margin: 4px 0 0; font-size: 13px; }
    .channel-list, .video-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; margin-top: 14px; }
    .channel-card { border: 1px solid #293149; background: #0b0e16; border-radius: 14px; padding: 14px; }
    .channel-card h3 { margin: 10px 0 4px; font-size: 16px; line-height: 1.25; }
    .channel-card .handle { color: #ffb454; font-size: 13px; font-weight: 650; }
    .channel-card .persona { color: #9ea7bc; font-size: 12px; line-height: 1.45; margin: 8px 0 10px; min-height: 34px; }
    .channel-card .meta-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
    .badge { display: inline-block; font-size: 11px; font-weight: 700; padding: 4px 8px; border-radius: 999px; background: #202637; color: #cbd5e1; border: 1px solid #343c52; }
    .channel-banner { height: 54px; border-radius: 10px; border: 1px solid #00000044; display: flex; align-items: center; justify-content: space-between; padding: 0 12px; overflow: hidden; position: relative; }
    .channel-banner.has-img { height: 96px; padding: 0; border: none; }
    .channel-banner.has-img img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .channel-banner .swatches { margin: 0; position: relative; z-index: 1; }
    .channel-banner .banner-overlay { position: absolute; inset: 0; display: flex; align-items: flex-end; justify-content: space-between; padding: 8px 10px; background: linear-gradient(180deg, transparent 30%, #00000088); }
    .channel-profile-row { display: flex; align-items: center; gap: 10px; margin: -22px 0 8px 10px; position: relative; z-index: 2; }
    .channel-profile-row img { width: 52px; height: 52px; border-radius: 50%; border: 2px solid #0b0e16; object-fit: cover; background: #0b0e16; }
    .ch-assets-preview { display: none; margin-top: 10px; padding: 10px; border: 1px solid #293149; border-radius: 10px; background: #0b0e16; }
    .ch-assets-preview.open { display: block; }
    .ch-assets-preview .asset-grid { display: grid; grid-template-columns: 80px 1fr; gap: 10px; align-items: start; }
    .ch-assets-preview img.profile { width: 72px; height: 72px; border-radius: 50%; object-fit: cover; border: 1px solid #343c52; }
    .ch-assets-preview img.banner { width: 100%; max-height: 90px; object-fit: cover; border-radius: 8px; border: 1px solid #343c52; }
    .ch-assets-preview img.watermark { width: 56px; height: 56px; object-fit: contain; }
    .video-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; margin-top: 14px; }
    .video-card { border: 1px solid #293149; background: #0b0e16; border-radius: 14px; padding: 12px; }
    .video-card h3 { margin: 8px 0 6px; font-size: 15px; line-height: 1.25; }
    .video-card small { color: #8f98ad; display: block; margin-bottom: 8px; }
    .video-card .actions { margin-top: 10px; }
    .video-card .actions a { border: 1px solid #343c52; background: #202637; color: #f5f2ea; border-radius: 999px; padding: 7px 10px; text-decoration: none; font-size: 12px; font-weight: 700; }
  </style>
</head>
<body>
<header class="site-header">
  <div class="site-header-inner">
    <div class="site-brand">
      <h1>Faceless Viral Video Generator</h1>
      <p>Stick-figure &amp; AI-image YouTube studio — generate, browse channels, review videos.</p>
    </div>
    <nav class="site-nav">
      <button type="button" class="nav-tab active" data-view="generate" onclick="showView('generate')">Generate</button>
      <button type="button" class="nav-tab" data-view="channels" onclick="showView('channels')">Channels</button>
      <button type="button" class="nav-tab" data-view="videos" onclick="showView('videos')">Videos</button>
    </nav>
  </div>
</header>
<main>
  <div id="view-generate" class="view-panel active">
  <p style="margin-top:0">Generate a topic, video, thumbnail, Kokoro voiceover, and copy-ready YouTube metadata.</p>
  <div class="grid">
    <section class="card">
      <div class="channel-bar">
        <div>
          <label>Channel</label>
          <select id="channel" onchange="onChannelPick()"></select>
        </div>
        <button type="button" class="secondary" onclick="toggleAddChannel()">+ Add channel</button>
        <button type="button" class="secondary gen-btn" onclick="generateChannel()" id="btn_gen_chan" title="Creates channel + profile, banner, and watermark (30–90s)">✨ AI Generate channel</button>
      </div>
      <div class="chip" id="channel_chip"></div>
      <div class="swatches" id="channel_swatches"></div>
      <div class="addchan" id="addchan">
        <div class="ai-concept-preview" id="ai_concept_preview"></div>
        <div class="row">
          <div><label>Name</label><input id="ch_name" placeholder="My Channel" /></div>
          <div><label>Handle</label><input id="ch_handle" placeholder="@MyChannel" /></div>
        </div>
        <label>Persona / niche (guides the writing)</label>
        <textarea id="ch_persona" style="min-height:70px" placeholder="e.g. punchy psychology explainers, confident second-person, one idea per beat"></textarea>
        <div class="row">
          <div><label>Background</label><input type="color" id="ch_bg" value="#0e1320" /></div>
          <div><label>Ink (figure)</label><input type="color" id="ch_ink" value="#f2ede1" /></div>
        </div>
        <div class="row">
          <div><label>Accent</label><input type="color" id="ch_accent" value="#ffb454" /></div>
          <div><label>Muted</label><input type="color" id="ch_muted" value="#6f7791" /></div>
        </div>
        <div class="row">
          <div><label>Voice</label><select id="ch_voice"></select></div>
          <div><label>Voice speed</label><input id="ch_speed" value="0.95" /></div>
        </div>
        <div class="actions"><button type="button" onclick="saveChannel()">Save channel</button></div>
        <div class="ch-assets-preview" id="ch_assets_preview"></div>
        <div class="voice-hint" id="ch_msg"></div>
      </div>
      <label>Trending topics or final topic</label>
      <textarea id="topic" placeholder="Paste YouTube suggestions, trend notes, or one final topic..."></textarea>
      <div class="row">
        <div><label>Length</label><select id="desired_length" onchange="onLengthChange()"><option value="shorts">Shorts</option><option value="3-5" selected>3-5 min</option><option value="6-8">6-8 min</option><option value="custom">Custom…</option></select></div>
        <div id="custom_len_wrap" style="display:none"><label>Custom minutes</label><input id="custom_len" type="number" min="0.5" max="30" step="0.5" value="2" /></div>
        <div><label>Format</label><select id="format"><option>16:9</option><option>9:16</option><option>both</option></select></div>
        <div><label>Visuals</label><select id="style" onchange="toggleImageOpts()"><option value="stick" selected>Stickman sketch</option><option value="image">AI image slideshow</option></select></div>
      </div>
      <div class="row">
        <div>
          <label>Script model (Gemini)</label>
          <select id="gemini_model" onchange="onGeminiModelPick()"></select>
          <div class="voice-hint" id="gemini_hint"></div>
        </div>
      </div>
      <div class="row" id="image_opts" style="display:none">
        <div><label>Image provider</label><select id="provider" onchange="onProviderPick()"></select><div class="voice-hint" id="provider_hint"></div></div>
        <div>
          <label>Voice</label>
          <div class="voice-picker">
            <select id="voice" onchange="onVoicePick('image')"></select>
            <button type="button" class="secondary" onclick="previewVoice('image')">▶ Preview</button>
          </div>
          <div class="voice-hint" id="voice_hint_image"></div>
          <audio id="preview_audio_image"></audio>
        </div>
        <div><label>Voice speed</label><input id="speed" value="1.0" onchange="onSpeedChange('image')" /></div>
      </div>
      <div class="row" id="voice_opts">
        <div>
          <label>Voice</label>
          <div class="voice-picker">
            <select id="voice_stick" onchange="onVoicePick('stick')"></select>
            <button type="button" class="secondary" onclick="previewVoice('stick')">▶ Preview</button>
          </div>
          <div class="voice-hint" id="voice_hint_stick">Select a voice to hear: “Hello Creator, I am …”</div>
          <audio id="preview_audio_stick"></audio>
        </div>
        <div><label>Voice speed</label><input id="speed_stick" value="1.0" onchange="onSpeedChange('stick')" /></div>
        <div></div>
      </div>
      <label id="image_style_label" style="display:none">Optional shared image style</label>
      <input id="image_style" style="display:none" placeholder="cinematic dark minimal, amber accent, no text..." />
      <div class="actions">
        <button onclick="suggestTopics()">AI Suggest Topics</button>
        <button onclick="generate()" class="secondary">Generate Video</button>
      </div>
    </section>
    <section class="card">
      <div class="status" id="status">Idle</div>
      <div class="progress-wrap" id="progress_wrap" style="display:none">
        <div class="progress-track"><div class="progress-fill" id="progress_fill"></div></div>
        <div class="progress-meta"><span id="progress_pct">0%</span><span id="progress_eta"></span></div>
      </div>
      <div id="topics"></div>
      <pre id="log"></pre>
    </section>
  </div>
  <section class="card" style="margin-top:18px">
    <h2>Result</h2>
    <div id="result"></div>
  </section>
  </div>

  <div id="view-channels" class="view-panel">
    <section class="card">
      <div class="library-head">
        <div>
          <h2>Channels</h2>
          <p>All preset and custom channel brands — palette, voice, persona, and video count.</p>
        </div>
        <button type="button" class="secondary" onclick="loadChannelLibrary()">Refresh</button>
      </div>
      <div id="channel_library" class="channel-list"></div>
    </section>
  </div>

  <div id="view-videos" class="view-panel">
    <section class="card">
      <div class="library-head">
        <div>
          <h2>Videos</h2>
          <p>Generated videos with preview, metadata, thumbnails, and download links.</p>
        </div>
        <button type="button" class="secondary" onclick="loadVideoLibrary()">Refresh</button>
      </div>
      <div id="video_library" class="video-list"></div>
    </section>
  </div>
</main>
<div id="toast" class="toast">Copied</div>
<script>
const $ = (id) => document.getElementById(id);
let lastResult = null;
let voiceCatalog = null;
let channelList = [];
let pendingAiChannelData = {};
let previewToken = 0;

async function loadGeminiModels() {
  const sel = $("gemini_model");
  if (!sel) return;
  try {
    const res = await fetch("/api/gemini?probe=1");
    const data = await res.json();
    sel.innerHTML = (data.models || []).map(m =>
      `<option value="${esc(m.id)}">${esc(m.name)}</option>`).join("");
    sel.value = data.default || "gemini-auto";
    sel._gemini = data;
    onGeminiModelPick();
    if (data.key_health && data.key_health.some(k => k.status === "invalid")) {
      const bad = data.key_health.filter(k => k.status === "invalid").map(k => `#${k.index}`).join(", ");
      const hint = $("gemini_hint");
      if (hint) hint.textContent = `⚠ Key(s) ${bad} expired — remove from .env (other keys still work). ` + (hint.textContent || "");
    }
  } catch (err) {
    sel.innerHTML = `<option value="gemini-auto">Auto (try all)</option>`;
  }
}
function onGeminiModelPick() {
  const sel = $("gemini_model");
  const hint = $("gemini_hint");
  if (!sel || !hint) return;
  const data = sel._gemini || {};
  const m = (data.models || []).find(x => x.id === sel.value);
  const keys = data.available_keys != null ? `${data.available_keys}/${data.configured} keys ready` : "";
  const chain = (data.fallback_chain || []).join(" → ");
  if (sel.value === "gemini-auto") {
    hint.textContent = keys ? `${keys}. Auto tries: ${chain}` : `Auto tries: ${chain}`;
  } else if (m) {
    hint.textContent = [m.description, keys].filter(Boolean).join(" · ");
  } else {
    hint.textContent = keys;
  }
}

async function loadProviders() {
  const sel = $("provider");
  if (!sel) return;
  try {
    const res = await fetch("/api/providers");
    const data = await res.json();
    sel.innerHTML = data.providers.map(p => {
      const tag = p.id === "auto" ? "" : (p.ready ? " ✓" : (p.needs_key ? " (no key)" : ""));
      return `<option value="${esc(p.id)}">${esc(p.name)}${tag}</option>`;
    }).join("");
    sel.value = data.default || "pollinations";
    sel._providers = data.providers;
    onProviderPick();
  } catch (err) {
    sel.innerHTML = `<option value="pollinations">Pollinations</option><option value="auto">Auto (failover)</option>`;
  }
}
function onProviderPick() {
  const sel = $("provider");
  const list = sel._providers || [];
  const p = list.find(x => x.id === sel.value);
  const hint = $("provider_hint");
  if (!hint) return;
  if (!p) { hint.textContent = ""; return; }
  if (p.id === "auto") hint.textContent = "Tries Cloudflare → Pollinations → Hugging Face.";
  else if (p.needs_key && !p.ready) hint.textContent = "No API key set — add it to .env, then restart.";
  else if (p.needs_key) hint.textContent = "API key detected.";
  else hint.textContent = "No API key needed.";
}

async function loadChannels() {
  const res = await fetch("/api/channels");
  const data = await res.json();
  channelList = data.channels || [];
  const sel = $("channel");
  sel.innerHTML = channelList.map(c => `<option value="${esc(c.id)}">${esc(c.name)}</option>`).join("");
  onChannelPick(false);
}
function currentChannel() {
  return channelList.find(c => c.id === $("channel").value) || channelList[0];
}
function onChannelPick(applyVoice = true) {
  const c = currentChannel();
  if (!c) return;
  const p = c.palette || {};
  $("channel_swatches").innerHTML = ["background","ink","accent","muted"]
    .map(k => `<div class="swatch" title="${k}: ${esc(p[k]||"")}" style="background:${esc(p[k]||"#000")}"></div>`).join("");
  $("channel_chip").textContent = (c.handle ? c.handle + " · " : "") + (c.persona ? c.persona.slice(0, 90) + (c.persona.length > 90 ? "…" : "") : "");
  if (applyVoice && c.voice) {
    if ($("voice_stick")) $("voice_stick").value = c.voice.kokoro_voice;
    if ($("voice")) $("voice").value = c.voice.kokoro_voice;
    if ($("speed_stick")) $("speed_stick").value = c.voice.kokoro_speed;
    if ($("speed")) $("speed").value = c.voice.kokoro_speed;
    if (typeof onVoicePick === "function") onVoicePick("stick", false);
  }
}
function toggleAddChannel() { $("addchan").classList.toggle("open"); }
async function saveChannel() {
  const body = {
    name: $("ch_name").value.trim(),
    handle: $("ch_handle").value.trim(),
    persona: $("ch_persona").value.trim(),
    palette: { background: $("ch_bg").value, ink: $("ch_ink").value, accent: $("ch_accent").value, muted: $("ch_muted").value },
    voice: { kokoro_voice: $("ch_voice").value, kokoro_speed: parseFloat($("ch_speed").value || "0.95") || 0.95 },
    image_provider: ($("provider") && $("provider").value) || "auto",
    generate_assets: !pendingAiChannelData.assets,
    ...pendingAiChannelData,
  };
  if (!body.name) { $("ch_msg").textContent = "Name is required."; return; }
  $("ch_msg").textContent = "Saving channel and generating profile, banner & watermark…";
  const res = await fetch("/api/channels", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body)});
  const data = await res.json();
  if (!res.ok) { $("ch_msg").textContent = data.detail || "Save failed."; return; }
  channelList = data.channels || [];
  $("channel").innerHTML = channelList.map(c => `<option value="${esc(c.id)}">${esc(c.name)}</option>`).join("");
  $("channel").value = data.channel.id;
  pendingAiChannelData = {};
  onChannelPick();
  showChannelAssetsPreview(data.channel);
  $("ch_msg").textContent = "Channel saved with profile, banner, and watermark.";
  toast("Channel saved");
}

function showChannelAssetsPreview(ch) {
  const box = $("ch_assets_preview");
  if (!box || !ch) return;
  const urls = ch.asset_urls || {};
  if (!urls.profile && !urls.banner && !urls.watermark) {
    box.classList.remove("open");
    box.innerHTML = "";
    return;
  }
  box.classList.add("open");
  const bust = `?t=${Date.now()}`;
  box.innerHTML = `<div style="font-size:12px;color:#8f98ad;margin-bottom:8px">Brand assets (ready for YouTube + video watermark)</div>
    <div class="asset-grid">
      <div>
        ${urls.profile ? `<img class="profile" src="${esc(urls.profile)}${bust}" alt="Profile" />` : ""}
        ${urls.watermark ? `<div style="margin-top:8px;font-size:11px;color:#8f98ad">Watermark</div><img class="watermark" src="${esc(urls.watermark)}${bust}" alt="Watermark" />` : ""}
      </div>
      <div>
        ${urls.banner ? `<img class="banner" src="${esc(urls.banner)}${bust}" alt="Banner" />` : `<div class="voice-hint">No banner yet — click Save channel to generate</div>`}
        <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
          ${urls.profile ? `<a href="${esc(urls.profile)}" download>Profile</a>` : ""}
          ${urls.banner ? `<a href="${esc(urls.banner)}" download>Banner</a>` : ""}
          ${urls.watermark ? `<a href="${esc(urls.watermark)}" download>Watermark</a>` : ""}
        </div>
      </div>
    </div>`;
}

async function generateChannel() {
  const btn = $("btn_gen_chan");
  btn.textContent = "✨ Generating...";
  btn.disabled = true;
  $("ai_concept_preview").style.display = "block";
  $("ai_concept_preview").textContent = "Step 1/2: Researching niche and brand identity…";
  if (!$("addchan").classList.contains("open")) {
    toggleAddChannel();
  }

  try {
    const res = await fetch("/api/channels/generate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        image_provider: ($("provider") && $("provider").value) || "auto",
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
    const ch = data.channel;

    $("ai_concept_preview").textContent = "Step 2/2: Done — profile, banner, and watermark created.";
    $("ch_name").value = ch.name || "";
    $("ch_handle").value = ch.handle || "";
    $("ch_persona").value = ch.persona || "";
    if (ch.palette) {
      $("ch_bg").value = ch.palette.background || "#0e1320";
      $("ch_ink").value = ch.palette.ink || "#f2ede1";
      $("ch_accent").value = ch.palette.accent || "#ffb454";
      $("ch_muted").value = ch.palette.muted || "#6f7791";
    }
    pendingAiChannelData = {};

    channelList = data.channels || channelList;
    $("channel").innerHTML = channelList.map(c => `<option value="${esc(c.id)}">${esc(c.name)}</option>`).join("");
    $("channel").value = ch.id;
    onChannelPick();

    const pillars = (ch.rotation || []).join(", ");
    $("ai_concept_preview").innerHTML = `<strong>${esc(ch.name)}</strong> ${esc(ch.handle || "")} saved with brand assets.<br>
      <span style="color:#8f98ad">${esc(ch.description || "")}</span><br>
      <span style="color:#8f98ad">Pillars: ${esc(pillars)}</span>`;
    showChannelAssetsPreview(ch);
    $("ch_msg").textContent = "Channel saved — download assets below or from the Channels tab.";
    toast("Channel created with images");
  } catch (err) {
    $("ai_concept_preview").textContent = `Error: ${err.message || err}`;
    $("ch_msg").textContent = "";
  } finally {
    btn.textContent = "✨ AI Generate";
    btn.disabled = false;
  }
}

function voiceFields(which) {
  if (which === "image") {
    return { select: $("voice"), speed: $("speed"), hint: $("voice_hint_image"), audio: $("preview_audio_image"), other: $("voice_stick") };
  }
  return { select: $("voice_stick"), speed: $("speed_stick"), hint: $("voice_hint_stick"), audio: $("preview_audio_stick"), other: $("voice") };
}

function selectedVoiceName(id) {
  const opt = document.querySelector(`option[value="${id}"]`);
  return opt ? opt.textContent.split(" — ")[0].trim() : id;
}

function previewPhrase(id) {
  return `“Hello Creator, I am ${selectedVoiceName(id)}.”`;
}

function fillVoiceSelect(select, catalog) {
  select.innerHTML = catalog.groups.map(g => `
    <optgroup label="${esc(g.label)}">
      ${g.voices.map(v => `<option value="${esc(v.id)}">${esc(v.name)} — ${esc(g.label)}</option>`).join("")}
    </optgroup>`).join("");
  select.value = catalog.default || "am_liam";
}

async function loadVoices() {
  const res = await fetch("/api/voices");
  voiceCatalog = await res.json();
  fillVoiceSelect($("voice_stick"), voiceCatalog);
  fillVoiceSelect($("voice"), voiceCatalog);
  if ($("ch_voice")) fillVoiceSelect($("ch_voice"), voiceCatalog);
  onVoicePick("stick", false);
}

function syncVoice(fromWhich) {
  const from = voiceFields(fromWhich);
  from.other.value = from.select.value;
  const otherWhich = fromWhich === "image" ? "stick" : "image";
  const hint = voiceFields(otherWhich).hint;
  if (hint) hint.textContent = previewPhrase(from.select.value);
}

function onVoicePick(which, play = true) {
  syncVoice(which);
  const f = voiceFields(which);
  f.hint.textContent = play ? "Playing preview…" : previewPhrase(f.select.value);
  if (play) previewVoice(which);
  else f.hint.textContent = previewPhrase(f.select.value);
}

function onSpeedChange(which) {
  const other = which === "image" ? "stick" : "image";
  voiceFields(other).speed.value = voiceFields(which).speed.value;
}

async function previewVoice(which) {
  const f = voiceFields(which);
  const voice = f.select.value;
  const speed = parseFloat(f.speed.value || "1") || 1;
  const token = ++previewToken;
  f.hint.textContent = `Playing ${previewPhrase(voice)}`;
  try {
    f.audio.src = `/api/voices/${encodeURIComponent(voice)}/preview?speed=${speed}&_=${Date.now()}`;
    await f.audio.play();
    if (token === previewToken) f.hint.textContent = previewPhrase(voice);
  } catch (err) {
    if (token === previewToken) f.hint.textContent = "Preview failed — is Kokoro set up?";
  }
}

function toggleImageOpts() {
  const image = $("style").value === "image";
  $("image_opts").style.display = image ? "grid" : "none";
  $("voice_opts").style.display = image ? "none" : "grid";
  $("image_style").style.display = image ? "block" : "none";
  $("image_style_label").style.display = image ? "block" : "none";
}
function onLengthChange() {
  const v = $("desired_length").value;
  $("custom_len_wrap").style.display = v === "custom" ? "block" : "none";
  if (v === "shorts") $("format").value = "9:16";
}
function lengthValue() {
  const v = $("desired_length").value;
  if (v !== "custom") return v;
  const mins = parseFloat($("custom_len").value || "2") || 2;
  return `about ${mins} minutes`;
}
function payload() {
  const image = $("style").value === "image";
  return {
    topic: $("topic").value,
    channel_id: $("channel").value,
    desired_length: lengthValue(),
    format: $("desired_length").value === "shorts" ? "9:16" : $("format").value,
    style: $("style").value,
    provider: image ? $("provider").value : "pollinations",
    voice: image ? $("voice").value : $("voice_stick").value,
    speed: image ? $("speed").value : $("speed_stick").value,
    gap: 0,
    image_style: $("image_style").value,
    gemini_model: $("gemini_model") ? $("gemini_model").value : "gemini-auto",
    backend: "auto",
    outroot: "output"
  };
}
async function suggestTopics() {
  $("status").textContent = "Researching topics...";
  $("topics").innerHTML = "";
  try {
    const res = await fetch("/api/suggest", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({
      seed_topics: $("topic").value,
      channel_id: $("channel").value,
      gemini_model: $("gemini_model") ? $("gemini_model").value : "gemini-auto",
    })});
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Topic suggestion failed");
    const warn = data.warning ? `<div class="warn">${esc(data.warning)}</div>` : "";
    $("topics").innerHTML = warn + data.topics.map((t) => {
      const score = t.keyword_score || 0;
      const col = score >= 70 ? "#22c1a4" : score >= 45 ? "#ffb454" : "#ff6b6b";
      const badge = score ? `<span title="vidIQ-style Keyword Score: search volume vs competition" style="float:right;font-weight:700;color:#0a0d14;background:${col};border-radius:999px;padding:2px 10px;font-size:12px">${score}</span>` : "";
      const meta = (t.search_volume || t.competition)
        ? `<small style="opacity:.8">📈 vol: ${esc(t.search_volume || "?")} · 🥊 comp: ${esc(t.competition || "?")}</small>` : "";
      return `<div class="topic">${badge}<strong>${esc(t.title_angle || t.brief)}</strong><small>${esc(t.trend_reason || "")}</small>${meta}<div class="actions"><button class="secondary" onclick='useTopic(${JSON.stringify(t.brief)})'>Use this topic</button><button class="secondary" onclick='copyText(${JSON.stringify(t.brief)})'>Copy topic</button></div></div>`;
    }).join("");
    $("status").textContent = data.source === "gemini"
      ? "Choose a topic or generate from your input."
      : "Offline topic ideas shown — you can still generate, or retry AI Suggest.";
  } catch (err) {
    $("status").textContent = "Topic suggestion failed.";
    $("topics").innerHTML = `<div class="warn">${esc(err.message || String(err))}</div>`;
  }
}
function useTopic(t) { $("topic").value = t; $("status").textContent = "Topic selected."; }
async function generate() {
  $("status").textContent = "Submitting job...";
  $("result").innerHTML = "";
  $("progress_wrap").style.display = "block";
  setProgress(2, null);
  const res = await fetch("/api/jobs", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload())});
  const job = await res.json();
  poll(job.id);
}
function fmtEta(s) {
  if (s === null || s === undefined) return "";
  s = Math.max(0, Math.round(s));
  if (s < 60) return `~${s}s left`;
  const m = Math.floor(s / 60), r = s % 60;
  return `~${m}m ${r}s left`;
}
function setProgress(pct, eta) {
  pct = Math.max(0, Math.min(100, Math.round(pct)));
  $("progress_fill").style.width = pct + "%";
  $("progress_pct").textContent = pct + "%";
  $("progress_eta").textContent = eta !== undefined ? fmtEta(eta) : "";
}
async function poll(id) {
  const res = await fetch(`/api/jobs/${id}`);
  const job = await res.json();
  $("status").textContent = `${job.status}: ${job.stage} - ${job.message}`;
  setProgress(job.progress ?? 0, job.eta_seconds);
  $("log").textContent = (job.events || []).map(e => `${new Date(e.ts * 1000).toLocaleTimeString()}  ${e.stage}: ${e.message}`).join("\n");
  if (job.status === "completed") { setProgress(100, 0); showResult(job.result); return; }
  if (job.status === "failed") { $("result").innerHTML = `<pre>${esc(job.error || "failed")}</pre>`; return; }
  setTimeout(() => poll(id), 1500);
}
function showResult(r) {
  lastResult = r;
  const meta = r.meta || {};
  const sched = meta.schedule || {};
  const fields = [
    ["Title", meta.title || ""],
    ["Title variants", (meta.title_variants || []).join("\n")],
    ["Description", meta.description || ""],
    ["Tags", (meta.tags || []).join(", ")],
    ["Hashtags", (meta.hashtags || []).join(" ")],
    ["Pinned comment", meta.pinned_comment || ""],
    ["Best schedule (UTC)", sched.recommended_utc || ""],
    ["Schedule reason", sched.reason || ""],
    ["Thumbnail prompt", meta.thumbnail_prompt || ""],
    ["Video path", r.video || ""],
    ["Thumbnail path", r.thumb || ""],
  ];
  const copyBlocks = fields.map(([label, value], i) => `
    <div class="copy-block">
      <div class="copy-head">
        <label>${esc(label)}</label>
        <button class="secondary" onclick="copyFrom('field-${i}')">Copy</button>
      </div>
      <textarea class="copy-area ${label === "Description" ? "tall" : ""}" id="field-${i}" readonly>${esc(value)}</textarea>
    </div>`).join("");
  const chan = r.channel ? `<div class="chip">Channel: <strong>${esc(r.channel.name)}</strong> ${esc(r.channel.handle || "")}</div>` : "";
  $("result").innerHTML = `
    ${chan}
    <div class="actions">
      <button onclick="copyAll()">Copy all metadata</button>
      <button class="secondary" onclick="copySidecar()">Copy upload sidecar</button>
    </div>
    <div class="media-grid">
      <div>${r.video_url ? `<video src="${r.video_url}" controls></video>` : `<p>No video preview</p>`}</div>
      <div>${r.thumb_url ? `<img class="thumb" src="${r.thumb_url}" alt="Thumbnail" />` : `<p>No thumbnail</p>`}</div>
    </div>
    ${copyBlocks}
    <div class="copy-block">
      <div class="copy-head"><label>Full metadata JSON</label><button class="secondary" onclick="copyText(JSON.stringify(lastResult.meta, null, 2))">Copy</button></div>
      <textarea class="copy-area tall" readonly>${esc(JSON.stringify(meta, null, 2))}</textarea>
    </div>`;
}
async function loadVideoLibrary() {
  const box = $("video_library");
  if (!box) return;
  box.innerHTML = `<div class="voice-hint">Loading videos…</div>`;
  try {
    const res = await fetch("/api/videos");
    const data = await res.json();
    const videos = data.videos || [];
    if (!videos.length) {
      box.innerHTML = `<div class="voice-hint">No generated videos yet.</div>`;
      return;
    }
    box.innerHTML = videos.map((v, i) => {
      const created = v.created ? new Date(v.created * 1000).toLocaleString() : "";
      const mb = v.size ? (v.size / (1024 * 1024)).toFixed(1) + " MB" : "";
      return `<div class="video-card">
        ${v.video_url ? `<video src="${esc(v.video_url)}" controls preload="metadata"></video>` : ""}
        <h3>${esc(v.title || v.name)}</h3>
        <small>${v.channel_name ? esc(v.channel_name) + " · " : ""}${esc(created)} ${mb ? " · " + esc(mb) : ""}</small>
        <div class="actions">
          ${v.video_url ? `<a href="${esc(v.video_url)}" download>Download video</a>` : ""}
          ${v.thumb_url ? `<a href="${esc(v.thumb_url)}" download>Thumbnail</a>` : ""}
          ${v.sidecar_url ? `<a href="${esc(v.sidecar_url)}" target="_blank">Upload text</a>` : ""}
          ${v.meta_url ? `<a href="${esc(v.meta_url)}" target="_blank">Metadata</a>` : ""}
          ${v.script_url ? `<a href="${esc(v.script_url)}" target="_blank">Script</a>` : ""}
        </div>
      </div>`;
    }).join("");
  } catch (err) {
    box.innerHTML = `<div class="warn">Could not load video library: ${esc(err.message || String(err))}</div>`;
  }
}
async function copyFrom(id) {
  const el = $(id);
  if (!el) return;
  await copyText(el.value);
}
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text || "");
    toast("Copied");
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text || "";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
    toast("Copied");
  }
}
function copyAll() {
  if (!lastResult) return;
  const m = lastResult.meta || {};
  const s = m.schedule || {};
  const body = [
    `TITLE\n${m.title || ""}`,
    `DESCRIPTION\n${m.description || ""}`,
    `TAGS\n${(m.tags || []).join(", ")}`,
    `HASHTAGS\n${(m.hashtags || []).join(" ")}`,
    `PINNED COMMENT\n${m.pinned_comment || ""}`,
    `SCHEDULE UTC\n${s.recommended_utc || ""}`,
    `VIDEO\n${lastResult.video || ""}`,
    `THUMBNAIL\n${lastResult.thumb || ""}`,
  ].join("\n\n");
  copyText(body);
}
function copySidecar() {
  if (!lastResult) return;
  const m = lastResult.meta || {};
  const body = `TITLE\n${m.title || ""}\n\nDESCRIPTION\n${m.description || ""}\n\nTAGS\n${(m.tags || []).join(", ")}\n\nHASHTAGS\n${(m.hashtags || []).join(" ")}`;
  copyText(body);
}
function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 1200);
}
function esc(s) { return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }

function showView(name) {
  document.querySelectorAll(".nav-tab").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.view === name);
  });
  document.querySelectorAll(".view-panel").forEach(panel => {
    panel.classList.toggle("active", panel.id === `view-${name}`);
  });
  if (name === "channels") loadChannelLibrary();
  if (name === "videos") loadVideoLibrary();
}

function swatchHtml(palette) {
  const p = palette || {};
  return ["background","ink","accent","muted"]
    .map(k => `<div class="swatch" title="${k}" style="background:${esc(p[k]||"#000")}"></div>`).join("");
}

async function loadChannelLibrary() {
  const box = $("channel_library");
  if (!box) return;
  box.innerHTML = `<div class="voice-hint">Loading channels…</div>`;
  try {
    const res = await fetch("/api/channels");
    const data = await res.json();
    const list = data.channels || [];
    if (!list.length) {
      box.innerHTML = `<div class="voice-hint">No channels yet.</div>`;
      return;
    }
    box.innerHTML = list.map(c => {
      const p = c.palette || {};
      const bg = p.background || "#0e1320";
      const urls = c.asset_urls || {};
      const persona = (c.persona || "").slice(0, 120) + ((c.persona || "").length > 120 ? "…" : "");
      const rotation = (c.rotation || []).slice(0, 4).map(r => `<span class="badge">${esc(r)}</span>`).join("");
      const voice = c.voice ? `${esc(c.voice.kokoro_voice || "am_liam")} · ${esc(String(c.voice.kokoro_speed || "1"))}x` : "";
      const bannerInner = urls.banner
        ? `<img src="${esc(urls.banner)}" alt="" /><div class="banner-overlay"><div class="swatches">${swatchHtml(p)}</div><span class="badge">${esc(String(c.video_count || 0))} videos</span></div>`
        : `<div class="swatches">${swatchHtml(p)}</div><span class="badge">${esc(String(c.video_count || 0))} videos</span>`;
      const profileRow = urls.profile
        ? `<div class="channel-profile-row"><img src="${esc(urls.profile)}" alt="" /><div><strong>${esc(c.name || c.id)}</strong><div class="handle">${esc(c.handle || "")}</div></div></div>`
        : `<h3>${esc(c.name || c.id)}</h3><div class="handle">${esc(c.handle || "")}</div>`;
      return `<div class="channel-card">
        <div class="channel-banner${urls.banner ? " has-img" : ""}" style="${urls.banner ? "" : `background:linear-gradient(135deg, ${esc(bg)}, ${esc(p.accent || "#ffb454")}33)`}">
          ${bannerInner}
        </div>
        ${profileRow}
        <div class="persona">${esc(persona)}</div>
        <div class="meta-row">
          <span class="badge">${esc(c.default_style || "stick")}</span>
          <span class="badge">${esc(c.default_length || "3-5")}</span>
          ${voice ? `<span class="badge">${voice}</span>` : ""}
          ${urls.watermark ? `<span class="badge">watermark</span>` : ""}
        </div>
        <div class="meta-row">${rotation}</div>
        <div class="actions">
          <button type="button" class="secondary" onclick="useChannel('${esc(c.id)}')">Use for generate</button>
          ${urls.banner ? `<a href="${esc(urls.banner)}" download>Banner</a>` : ""}
          ${urls.profile ? `<a href="${esc(urls.profile)}" download>Profile</a>` : ""}
        </div>
      </div>`;
    }).join("");
  } catch (err) {
    box.innerHTML = `<div class="warn">Could not load channels: ${esc(err.message || String(err))}</div>`;
  }
}

function useChannel(id) {
  showView("generate");
  const sel = $("channel");
  if (sel) {
    sel.value = id;
    onChannelPick();
  }
  $("status").textContent = `Channel selected: ${id}`;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

toggleImageOpts();
(async () => { await loadVoices(); await loadChannels(); await loadGeminiModels(); await loadProviders(); })();
</script>
</body>
</html>"""
