import json

import pytest

from studio.script_gen import parse_script_json


def _payload(**overrides) -> str:
    data = {
        "title": "Why Most Budgets Fail",
        "segments": [
            {"kind": "avatar", "text": "Most budgets fail in week two. Here's why.", "broll_keywords": []},
            {"kind": "broll", "text": "It's not a discipline problem.", "broll_keywords": ["empty wallet", "calculator"]},
            {"kind": "avatar", "text": "Follow for the fix.", "broll_keywords": []},
        ],
    }
    data.update(overrides)
    return json.dumps(data)


def test_parse_valid_script():
    script = parse_script_json(_payload(), topic="budgeting")
    assert script.title == "Why Most Budgets Fail"
    assert len(script.segments) == 3
    assert script.segments[0].kind == "avatar"
    assert script.segments[1].broll_keywords == ["empty wallet", "calculator"]


def test_parse_tolerates_markdown_fence():
    raw = f"Here you go:\n```json\n{_payload()}\n```"
    script = parse_script_json(raw, topic="budgeting")
    assert script.title == "Why Most Budgets Fail"


def test_requires_avatar_open_and_close():
    data = json.loads(_payload())
    data["segments"][0]["kind"] = "broll"
    with pytest.raises(ValueError, match="open and close"):
        parse_script_json(json.dumps(data), topic="budgeting")


def test_rejects_empty_segments():
    with pytest.raises(ValueError, match="no segments"):
        parse_script_json(json.dumps({"title": "x", "segments": []}), topic="t")


def test_rejects_missing_json():
    with pytest.raises(ValueError, match="no JSON object"):
        parse_script_json("sorry, I can't help with that", topic="t")
