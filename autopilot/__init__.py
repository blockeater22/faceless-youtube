"""Autopilot — continuously generate and publish faceless videos.

This package is designed to run on a schedule (e.g. a GitHub Actions cron) on a
machine you control — NOT inside the ephemeral Claude session, which is wiped
when the session ends. See docs/AUTOPILOT.md for setup.

Pipeline:  topics -> scriptwriter -> produce (render + thumbnail) -> youtube upload
Entry point:  python -m autopilot.run --count 2
"""
