"""Gemini API key rotation for free-tier account pools.

Keys are read from ``GEMINI_API_KEYS`` first (comma-separated), then the legacy
single-key variables. The browser UI never sees the key values; logs should only
refer to key indexes.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass

from autopilot.env_loader import load_dotenv


COOLDOWN_SECONDS = 15 * 60
# Valid Gemini models — try each model on a key before moving to the next key.
# Only models with a confirmed Free Tier (no credit card required) are included.
MODEL_FALLBACKS = (
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)

class GeminiTransientError(Exception):
    """Gemini returned a retryable capacity/availability error."""


class GeminiQuotaError(Exception):
    """Gemini key hit quota or rate limits."""


class GeminiInvalidKeyError(Exception):
    """Gemini API key is expired, revoked, or otherwise unusable."""


class GeminiJsonError(Exception):
    """Gemini returned malformed/incomplete JSON."""


@dataclass
class GeminiKey:
    index: int
    value: str
    cooldown_until: float = 0.0
    dead: bool = False
    last_error: str = ""

    @property
    def available(self) -> bool:
        return not self.dead and time.time() >= self.cooldown_until


_POOL: list[GeminiKey] | None = None


def keys() -> list[GeminiKey]:
    global _POOL
    load_dotenv()
    if _POOL is not None:
        return _POOL
    raw = os.environ.get("GEMINI_API_KEYS", "")
    values = [k.strip() for k in raw.replace("\n", ",").split(",") if k.strip()]
    for env in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(env)
        if val and val not in values:
            values.append(val)
    _POOL = [GeminiKey(i, v) for i, v in enumerate(values)]
    return _POOL


def has_key() -> bool:
    return bool(keys())


def reset_for_tests() -> None:
    global _POOL
    _POOL = None


def reload_keys() -> int:
    """Re-read ``.env`` and rebuild the key pool (e.g. after editing keys)."""
    global _POOL
    _POOL = None
    load_dotenv()
    return len(keys())


def _quota_is_rate_limit(exc: Exception) -> bool:
    """True when we should briefly cool down a key (RPM), not just skip this model."""
    text = str(exc).lower()
    return any(s in text for s in (
        "retry in", "retry_delay", "per minute", "requests per minute",
        "too many requests",
    ))


def probe_keys(model: str | None = None) -> list[dict]:
    """Health check per key — tries each model until one succeeds."""
    load_dotenv()
    pool = keys()
    models = _model_candidates(model if (model and model.startswith("gemini")) else None)
    out: list[dict] = []
    for key in pool:
        row = {"index": key.index, "status": "unknown", "detail": "", "model": ""}
        if key.dead:
            row["status"] = "invalid"
            row["detail"] = "Previously marked invalid — remove from GEMINI_API_KEYS"
            out.append(row)
            continue
        for model_name in models:
            try:
                _generate_json_with_key(
                    key.value,
                    'Reply with JSON: {"ok": true}',
                    system_instruction="Return only JSON.",
                    model=model_name,
                    temperature=0.1,
                    max_output_tokens=64,
                )
                row["status"] = "ok"
                row["model"] = model_name
                row["detail"] = f"Works with {model_name}"
                break
            except Exception as exc:  # noqa: BLE001
                if _looks_invalid_key_error(exc):
                    key.dead = True
                    row["status"] = "invalid"
                    row["detail"] = "Expired or revoked — remove this key from GEMINI_API_KEYS"
                    break
                row["status"] = "quota" if _looks_quota_error(exc) else (
                    "busy" if _looks_transient_error(exc) else (
                        "error" if not _looks_not_found_error(exc) else "not_found"
                    )
                )
                if row["status"] == "not_found":
                    row["detail"] = f"{model_name} not found (404)"
                else:
                    row["detail"] = f"{model_name}: {str(exc)[:100]}"
        out.append(row)
    return out


def _start_index(job_id: str | None) -> int:
    pool = keys()
    if not pool:
        return 0
    if not job_id:
        return int(time.time()) % len(pool)
    digest = hashlib.sha256(job_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % len(pool)


def _looks_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(s in text for s in (
        "429", "quota", "rate limit", "resource_exhausted", "too many requests",
    ))


def _looks_transient_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(s in text for s in (
        "503", "unavailable", "high demand", "overloaded", "temporarily",
        "500", "internal error", "deadline", "timeout", "try again later",
    ))


def _looks_invalid_key_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(s in text for s in (
        "api_key_invalid", "api key expired", "api key not valid",
        "invalid api key", "apikey not valid", "api key invalid",
    ))


def _looks_not_found_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(s in text for s in (
        "404", "not_found", "not found", "is not found",
    ))


def model_fallbacks() -> tuple[str, ...]:
    raw = os.environ.get("GEMINI_MODELS", "")
    if raw.strip():
        return tuple(m.strip() for m in raw.replace("\n", ",").split(",") if m.strip())
    return MODEL_FALLBACKS


def _model_candidates(model: str | None) -> tuple[str, ...]:
    fallbacks = model_fallbacks()
    if model and model.startswith("gemini") and model != "gemini-auto":
        return (model,) + tuple(m for m in fallbacks if m != model)
    return fallbacks


def _extract_json(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) >= 2:
            t = parts[1]
            if t.lstrip().lower().startswith("json"):
                t = t.lstrip()[4:]
    start = t.find("{")
    if start == -1:
        raise ValueError("no JSON object in Gemini response")
    depth = 0
    for i in range(start, len(t)):
        if t[i] == "{":
            depth += 1
        elif t[i] == "}":
            depth -= 1
            if depth == 0:
                return t[start:i + 1]
    raise ValueError("unbalanced JSON in Gemini response")


def generate_json(
    prompt: str,
    *,
    system_instruction: str,
    model: str | None = None,
    temperature: float = 0.8,
    max_output_tokens: int = 16000,
    job_id: str | None = None,
) -> dict:
    """Generate a JSON object using the key pool with model + transient fallbacks."""
    pool = keys()
    if not pool:
        raise RuntimeError("No Gemini keys configured; set GEMINI_API_KEYS or GEMINI_API_KEY")

    models = _model_candidates(model if (model and model.startswith("gemini")) else None)
    start = _start_index(job_id)
    last_exc: Exception | None = None

    # Per key: walk all models before advancing to the next key.
    for offset in range(len(pool)):
        key = pool[(start + offset) % len(pool)]
        if not key.available:
            continue
        for model_name in models:
            print(f"  [gemini] key #{key.index} → {model_name} …")
            try:
                result = _generate_json_with_retries(
                    key,
                    prompt,
                    system_instruction=system_instruction,
                    model=model_name,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
                print(f"  [gemini] ok via {model_name} (key #{key.index})")
                return result
            except GeminiInvalidKeyError as exc:
                last_exc = exc
                key.dead = True
                key.last_error = str(exc)
                print(f"  [gemini] key #{key.index} invalid/expired — next key")
                break
            except GeminiQuotaError as exc:
                last_exc = exc
                key.last_error = str(exc)
                if _quota_is_rate_limit(exc):
                    key.cooldown_until = time.time() + COOLDOWN_SECONDS
                    print(f"  [gemini] key #{key.index} rate-limited on {model_name} — next model")
                else:
                    print(f"  [gemini] key #{key.index} quota on {model_name} — next model")
                continue
            except GeminiTransientError as exc:
                last_exc = exc
                key.last_error = str(exc)
                print(f"  [gemini] key #{key.index} {model_name} busy — next model")
                continue
            except GeminiJsonError as exc:
                last_exc = exc
                print(f"  [gemini] key #{key.index} {model_name} bad JSON — next model")
                continue
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if _looks_invalid_key_error(exc):
                    key.dead = True
                    key.last_error = str(exc)
                    print(f"  [gemini] key #{key.index} invalid/expired — next key")
                    break
                if _looks_quota_error(exc):
                    key.last_error = str(exc)
                    if _quota_is_rate_limit(exc):
                        key.cooldown_until = time.time() + COOLDOWN_SECONDS
                    print(f"  [gemini] key #{key.index} quota on {model_name} — next model")
                    continue
                if _looks_transient_error(exc):
                    key.last_error = str(exc)
                    print(f"  [gemini] key #{key.index} {model_name} busy — next model")
                    continue
                if _looks_not_found_error(exc):
                    key.last_error = str(exc)
                    print(f"  [gemini] key #{key.index} {model_name} not found (404) — next model")
                    continue
                raise

    if last_exc:
        raise last_exc
    raise RuntimeError("All Gemini keys exhausted (cooling down or invalid)")


def _generate_json_with_retries(
    key: GeminiKey,
    prompt: str,
    *,
    system_instruction: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
) -> dict:
    """Single attempt per model — caller rotates models/keys on failure."""
    try:
        return _generate_json_with_key(
            key.value,
            prompt,
            system_instruction=system_instruction,
            model=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
    except Exception as exc:  # noqa: BLE001
        if _looks_invalid_key_error(exc):
            raise GeminiInvalidKeyError(str(exc)) from exc
        if _looks_quota_error(exc):
            raise GeminiQuotaError(str(exc)) from exc
        if "json" in str(exc).lower() or "unbalanced" in str(exc).lower():
            raise GeminiJsonError(str(exc)) from exc
        if _looks_transient_error(exc):
            raise GeminiTransientError(str(exc)) from exc
        raise


def _generate_json_with_key(
    key: str,
    prompt: str,
    *,
    system_instruction: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
) -> dict:
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                max_output_tokens=max_output_tokens,
                temperature=temperature,
            ),
        )
        return json.loads(_extract_json(resp.text))
    except ImportError:
        pass

    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:
        raise RuntimeError("install the Gemini SDK: `pip install google-genai`") from exc

    genai.configure(api_key=key)
    gmodel = genai.GenerativeModel(model, system_instruction=system_instruction)
    resp = gmodel.generate_content(
        prompt,
        generation_config={
            "response_mime_type": "application/json",
            "max_output_tokens": max_output_tokens,
            "temperature": temperature,
        },
    )
    return json.loads(_extract_json(resp.text))
