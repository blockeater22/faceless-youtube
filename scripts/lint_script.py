#!/usr/bin/env python3
"""Gate: every story JSON must pass the Inklings Scripting SOP before it's
allowed to render. This is what replaces "eyeball it before the batch goes
out" - the thing that let 50 templated, subscribe-asking scripts through.

Run before ``python -m faceless build``:

    python scripts/lint_script.py stories/some_short.json
    python scripts/lint_script.py "stories/*.json"

Generators opt in by writing the SOP fields into ``meta.sop`` on the story
JSON (hook, explain, reframe, cta_question, specificity) - see
``scripts/generate_sop_shorts.py``. Stories with no ``meta.sop`` (everything
written before this module existed) are skipped, not failed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from faceless.scripting_sop import BEAT_ORDER, validate_topic  # noqa: E402


def check_beat_order(scenes: list[dict]) -> list[str]:
    beats = [s.get("beat") for s in scenes if s.get("beat")]
    if not beats:
        return ["no scene declares a `beat`"]
    errors = []
    if beats[0] != "hook":
        errors.append(f"first beat is {beats[0]!r}, must be 'hook'")
    if beats[-1] != "cta":
        errors.append(f"last beat is {beats[-1]!r}, must be 'cta'")
    last_idx = -1
    for b in beats:
        if b not in BEAT_ORDER:
            errors.append(f"unknown beat {b!r}, must be one of {BEAT_ORDER}")
            continue
        idx = BEAT_ORDER.index(b)
        if idx < last_idx:
            errors.append(f"beat {b!r} appears out of order after {BEAT_ORDER[last_idx]!r}")
        last_idx = max(last_idx, idx)
    return errors


def lint_story(path: Path) -> tuple[list[str], bool]:
    """Returns (errors, skipped)."""
    data = json.loads(path.read_text())
    sop = data.get("meta", {}).get("sop")
    if sop is None:
        return [], True
    topic = dict(sop)
    topic["title"] = data.get("title", "")
    errors = validate_topic(topic) + check_beat_order(data.get("scenes", []))
    return errors, False


def _resolve(arg: str) -> list[Path]:
    p = Path(arg)
    if p.exists():
        return [p]
    return sorted(Path().glob(arg))


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: lint_script.py <story.json> [...]")
        return 2
    paths = [p for arg in argv for p in _resolve(arg)]
    if not paths:
        print(f"no files matched: {argv}")
        return 2

    all_errors, skipped = [], 0
    for path in paths:
        errors, was_skipped = lint_story(path)
        if was_skipped:
            skipped += 1
            continue
        all_errors.extend(f"{path.name}: {e}" for e in errors)

    if all_errors:
        print(f"FAIL - {len(all_errors)} violation(s) across {len(paths) - skipped} linted file(s):")
        for e in all_errors:
            print(f"  - {e}")
        return 1
    print(f"PASS - {len(paths) - skipped} file(s) clean ({skipped} skipped, no meta.sop)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
