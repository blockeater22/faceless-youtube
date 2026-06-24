"""Simple in-process background jobs for the local FastAPI UI."""
from __future__ import annotations

import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field

from autopilot.pipeline import GenerationRequest, generate_video

# Each stage maps to a cumulative % target so the UI bar advances meaningfully.
# Render is the long pole, so it spans the widest band (30 -> 88).
STAGE_TARGET: dict[str, int] = {
    "queued": 0,
    "start": 3,
    "topic": 8,
    "trends": 14,
    "script": 30,
    "render": 88,
    "metadata": 95,
    "done": 100,
    "completed": 100,
    "failed": 100,
}


@dataclass
class Job:
    id: str
    request: GenerationRequest
    status: str = "queued"
    stage: str = "queued"
    message: str = "Waiting to start"
    progress: int = 0
    eta_seconds: float | None = None
    est_render_s: float | None = None
    stage_started: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    events: list[dict] = field(default_factory=list)
    result: dict | None = None
    error: str | None = None

    def event(self, stage: str, message: str, info: dict | None = None) -> None:
        self.stage = stage
        self.message = message
        self.updated_at = time.time()
        self.stage_started = self.updated_at
        if stage in STAGE_TARGET:
            self.progress = STAGE_TARGET[stage]
        if info and info.get("est_render_s"):
            self.est_render_s = float(info["est_render_s"])
        self.events.append({"ts": self.updated_at, "stage": stage, "message": message})


_JOBS: dict[str, Job] = {}
_LOCK = threading.Lock()


def create_job(req: GenerationRequest) -> Job:
    job = Job(id=uuid.uuid4().hex[:12], request=req)
    with _LOCK:
        _JOBS[job.id] = job
    thread = threading.Thread(target=_run, args=(job,), daemon=True)
    thread.start()
    return job


def get_job(job_id: str) -> Job | None:
    with _LOCK:
        return _JOBS.get(job_id)


def list_jobs() -> list[Job]:
    with _LOCK:
        return sorted(_JOBS.values(), key=lambda j: j.created_at, reverse=True)


def _interpolated(job: Job) -> tuple[int, float | None]:
    """Smoothly advance the bar *within* the long render stage using the estimate,
    and compute an ETA so the user knows how long is left."""
    progress = job.progress
    eta = None
    now = time.time()
    if job.status == "running" and job.stage == "render" and job.est_render_s:
        span = STAGE_TARGET["render"] - STAGE_TARGET["script"]  # 30 -> 88
        frac = min(0.97, (now - job.stage_started) / max(1.0, job.est_render_s))
        progress = STAGE_TARGET["script"] + int(span * frac)
        eta = max(0.0, job.est_render_s - (now - job.stage_started))
    elif job.status == "running" and 0 < job.progress < 100:
        elapsed = now - job.created_at
        eta = max(0.0, elapsed * (100 - job.progress) / max(1, job.progress))
    elif job.status == "completed":
        progress = 100
        eta = 0.0
    return progress, eta


def serialize(job: Job) -> dict:
    progress, eta = _interpolated(job)
    return {
        "id": job.id,
        "status": job.status,
        "stage": job.stage,
        "message": job.message,
        "progress": progress,
        "eta_seconds": round(eta, 1) if eta is not None else None,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "elapsed_seconds": round(job.updated_at - job.created_at, 1),
        "events": job.events[-80:],
        "result": job.result,
        "error": job.error,
    }


def _run(job: Job) -> None:
    job.status = "running"
    job.event("start", "Starting generation")
    try:
        job.result = generate_video(job.request, progress=job.event, job_id=job.id)
        job.status = "completed"
        job.event("completed", "Ready")
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error = f"{exc}\n\n{traceback.format_exc()}"
        job.event("failed", str(exc))
