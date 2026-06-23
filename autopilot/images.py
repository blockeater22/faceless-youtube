"""Free AI image generation for the 'image' visual style.

Three providers, in order of zero-friction:
  - "pollinations" (default): a plain HTTP GET, **no API key**, no signup. Uses
        FLUX under the hood. https://image.pollinations.ai/prompt/<prompt>
  - "cloudflare": Cloudflare Workers AI (generous free tier ~10k neurons/day).
        Needs CF_ACCOUNT_ID + CF_API_TOKEN. Model flux-1-schnell.
  - "huggingface": HF Serverless Inference API. Needs HF_TOKEN. Rate-limited but
        free.

Every provider returns a PNG written to `out_path`. A consistent STYLE_SUFFIX is
appended to each prompt so frames across one video share a look (this is the
single biggest lever for a slideshow not feeling random).
"""
from __future__ import annotations

import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Appended to every prompt so a whole video reads as one coherent set of frames.
# Override per channel via config["image_style"].
STYLE_SUFFIX = (
    "cinematic, dramatic soft lighting, muted teal-and-amber palette, "
    "shallow depth of field, film grain, highly detailed, 4k, no text, no watermark"
)

_UA = {"User-Agent": "faceless-youtube/1.0 (+https://github.com)"}


def build_prompt(scene_prompt: str, style: str | None = None) -> str:
    style = (style or STYLE_SUFFIX).strip()
    return f"{scene_prompt.strip()}. {style}" if style else scene_prompt.strip()


def generate_image(scene_prompt: str, out_path: str | Path, *, width: int = 1280,
                   height: int = 720, provider: str = "pollinations",
                   style: str | None = None, seed: int | None = None,
                   model: str | None = None, retries: int = 3) -> Path:
    """Generate one image to `out_path`. Falls back to a solid card on failure so
    a render never dies for one bad frame."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt(scene_prompt, style)
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            if provider == "pollinations":
                _pollinations(prompt, out_path, width, height, seed, model)
            elif provider == "cloudflare":
                _cloudflare(prompt, out_path, width, height, model)
            elif provider == "huggingface":
                _huggingface(prompt, out_path, model)
            else:
                raise ValueError(f"unknown image provider: {provider}")
            if out_path.exists() and out_path.stat().st_size > 1024:
                return out_path
            raise RuntimeError("empty image returned")
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(2 * (attempt + 1))  # backoff; pollinations queues under load
    print(f"  [images] '{provider}' failed ({last_exc}); using a fallback card")
    _fallback_card(out_path, width, height, scene_prompt)
    return out_path


# --------------------------------------------------------------------------- #
# Providers
# --------------------------------------------------------------------------- #
def _pollinations(prompt: str, out: Path, w: int, h: int, seed, model) -> None:
    enc = urllib.parse.quote(prompt)
    params = {"width": w, "height": h, "nologo": "true", "model": model or "flux"}
    if seed is not None:
        params["seed"] = int(seed)
    url = f"https://image.pollinations.ai/prompt/{enc}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=180) as r, open(out, "wb") as f:
        f.write(r.read())


def _cloudflare(prompt: str, out: Path, w: int, h: int, model) -> None:
    import base64
    import json
    acct = os.environ.get("CF_ACCOUNT_ID")
    token = os.environ.get("CF_API_TOKEN")
    if not (acct and token):
        raise RuntimeError("set CF_ACCOUNT_ID and CF_API_TOKEN for Cloudflare Workers AI")
    model = model or "@cf/black-forest-labs/flux-1-schnell"
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}"
    body = json.dumps({"prompt": prompt}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Type": "application/json", **_UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    # flux-schnell returns base64 JPEG in result.image
    b64 = (data.get("result") or {}).get("image")
    if not b64:
        raise RuntimeError(f"cloudflare returned no image: {str(data)[:200]}")
    out.write_bytes(base64.b64decode(b64))


def _huggingface(prompt: str, out: Path, model) -> None:
    import json
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        raise RuntimeError("set HF_TOKEN for the Hugging Face Inference API")
    model = model or "black-forest-labs/FLUX.1-schnell"
    url = f"https://api-inference.huggingface.co/models/{model}"
    body = json.dumps({"inputs": prompt}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Type": "application/json", **_UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        out.write_bytes(r.read())  # raw image bytes


def _fallback_card(out: Path, w: int, h: int, text: str) -> None:
    """A dark gradient card with the prompt — keeps the video intact offline."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (w, h), (14, 19, 32))
    d = ImageDraw.Draw(img)
    for y in range(h):  # subtle vertical gradient
        c = 14 + int(10 * y / h)
        d.line([(0, y), (w, y)], fill=(c, c + 4, c + 10))
    words, line, lines = text.split(), "", []
    for word in words:
        if len(line) + len(word) > 38:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    y = h // 2 - len(lines) * 18
    for ln in lines[:6]:
        d.text((w // 2, y), ln, fill=(180, 188, 200), anchor="mm")
        y += 38
    img.save(out)
