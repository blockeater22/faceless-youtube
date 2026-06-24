"""Image provider routing, cache, and validation."""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageStat

from autopilot import hf_rate_limit, images


# Pollinations first (no key, no HF credits); HF last because of rate/credit limits.
DEFAULT_ORDER = ("pollinations", "cloudflare", "huggingface")


@dataclass
class ImageResult:
    path: str
    provider: str
    cache_hit: bool
    prompt_hash: str
    model: str | None = None


def normalize_order(provider: str | None, provider_order: list[str] | tuple[str, ...] | None = None) -> list[str]:
    if provider_order:
        order = [p for p in provider_order if p]
    elif provider and provider not in ("auto", "router"):
        order = [p.strip() for p in provider.split(",") if p.strip()]
    else:
        order = list(DEFAULT_ORDER)
    seen, clean = set(), []
    for p in order:
        if p not in seen:
            seen.add(p)
            clean.append(p)
    clean = clean or list(DEFAULT_ORDER)
    if not hf_rate_limit.is_available():
        clean = [p for p in clean if p != "huggingface"]
    # HF-only jobs still need a free fallback when credits/rate limits hit.
    if clean == ["huggingface"]:
        clean = ["huggingface", "pollinations"]
    return clean


def prompt_hash(prompt: str, *, width: int, height: int, style: str | None,
                seed: int | None, model: str | None) -> str:
    payload = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "style": style or "",
        "seed": seed,
        "model": model or "",
    }
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def generate_scene_image(
    scene_prompt: str,
    out_path: str | Path,
    *,
    width: int,
    height: int,
    provider: str | None = None,
    provider_order: list[str] | tuple[str, ...] | None = None,
    style: str | None = None,
    seed: int | None = None,
    model: str | None = None,
    cache_dir: str | Path | None = None,
    retries: int = 2,
) -> ImageResult:
    """Generate one image with cache + provider failover."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    phash = prompt_hash(scene_prompt, width=width, height=height, style=style, seed=seed, model=model)
    cache_root = Path(cache_dir or out_path.parent / "_cache")
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_img = cache_root / f"{phash}.png"
    cache_meta = cache_root / f"{phash}.json"

    if _valid_image(cache_img):
        shutil.copyfile(cache_img, out_path)
        provider_name = _read_provider(cache_meta) or "cache"
        return ImageResult(str(out_path), provider_name, True, phash, model)

    last_exc: Exception | None = None
    for name in normalize_order(provider, provider_order):
        try:
            tmp = out_path.with_suffix(f".{name}.tmp.png")
            images.generate_image(
                scene_prompt,
                tmp,
                width=width,
                height=height,
                provider=name,
                style=style,
                seed=seed,
                model=model,
                retries=retries,
                fallback=False,
            )
            if not _valid_image(tmp):
                raise RuntimeError("generated image failed validation")
            shutil.copyfile(tmp, cache_img)
            shutil.move(str(tmp), out_path)
            result = ImageResult(str(out_path), name, False, phash, model)
            cache_meta.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
            return result
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            print(f"  [images] provider '{name}' failed ({exc}); trying fallback")

    print(f"  [images] all providers failed ({last_exc}); using a fallback card")
    images.fallback_card(out_path, width, height, scene_prompt)
    result = ImageResult(str(out_path), "fallback", False, phash, model)
    cache_meta.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    return result


def _read_provider(path: Path) -> str | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("provider")
    except Exception:
        return None


def _valid_image(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 1024:
        return False
    try:
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            if img.width < 256 or img.height < 256:
                return False
            stat = ImageStat.Stat(img.convert("L").resize((32, 32)))
            return bool(stat.stddev and stat.stddev[0] > 2.0)
    except Exception:
        return False
