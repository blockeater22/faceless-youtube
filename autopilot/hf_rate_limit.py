"""Hugging Face Inference Providers rate-limit aware throttling.

HF free accounts have tight monthly credits and HTTP 429 windows. We pace requests
proactively and honor Retry-After / RateLimit headers on 429 responses.
"""
from __future__ import annotations

import os
import re
import threading
import time

_lock = threading.Lock()
_last_request_at = 0.0
_cooldown_until = 0.0
_quota_exhausted = False


def min_interval_sec() -> float:
    return max(0.0, float(os.environ.get("HF_MIN_INTERVAL_SEC", "4")))


def max_retries() -> int:
    return max(1, int(os.environ.get("HF_MAX_RETRIES", "6")))


def max_retry_wait_sec() -> float:
    return max(5.0, float(os.environ.get("HF_RETRY_MAX_WAIT_SEC", "120")))


def is_available() -> bool:
    return not _quota_exhausted


def mark_quota_exhausted() -> None:
    global _quota_exhausted
    _quota_exhausted = True


def reset_for_tests() -> None:
    global _last_request_at, _cooldown_until, _quota_exhausted
    with _lock:
        _last_request_at = 0.0
        _cooldown_until = 0.0
        _quota_exhausted = False


def wait_before_request() -> None:
    """Block until pacing interval and any active cooldown have elapsed."""
    with _lock:
        global _last_request_at
        now = time.monotonic()
        wait = max(
            min_interval_sec() - (now - _last_request_at),
            _cooldown_until - now,
            0.0,
        )
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def schedule_cooldown(seconds: float) -> None:
    global _cooldown_until
    with _lock:
        _cooldown_until = max(_cooldown_until, time.monotonic() + max(0.0, seconds))


def parse_reset_seconds(headers) -> float | None:
    """Parse HF RateLimit / Retry-After headers (IETF draft-ietf-httpapi-ratelimit)."""
    if not headers:
        return None
    retry_after = headers.get("Retry-After") or headers.get("retry-after")
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            pass
    for key in ("RateLimit", "ratelimit"):
        raw = headers.get(key)
        if not raw:
            continue
        match = re.search(r";t=(\d+)", raw)
        if match:
            return float(match.group(1))
    return None


def looks_like_quota_error(status: int, body: str) -> bool:
    text = body.lower()
    if status in (402, 403):
        return True
    return status == 429 and any(
        phrase in text
        for phrase in (
            "credit",
            "quota",
            "billing",
            "limit reached",
            "monthly",
            "purchase credits",
        )
    )


def looks_like_model_loading(status: int, body: str) -> float | None:
    if status != 503:
        return None
    import json

    try:
        data = json.loads(body)
    except Exception:
        return None
    est = data.get("estimated_time")
    if est is None:
        return None
    try:
        return max(1.0, float(est))
    except (TypeError, ValueError):
        return None
