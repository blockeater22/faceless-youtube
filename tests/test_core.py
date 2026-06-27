"""Unit tests for the pure logic the pipeline relies on.

These cover the parts that can silently regress and quietly ship a bad batch:
the Scripting SOP validator (the gate that fails non-compliant scripts), the
auto-direction inference (face/pose/prop from a sentence), and the geometry of
the whiteboard stroke-reveal. Rendering itself is exercised by the smoke test.

Run:  pytest -q
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from faceless import scripting_sop as sop          # noqa: E402
from faceless.draw import Sketcher                  # noqa: E402
from faceless.figures import _part_reveal           # noqa: E402

import direction                                    # noqa: E402


# --------------------------------------------------------------------------- #
# Scripting SOP
# --------------------------------------------------------------------------- #
GOOD_TOPIC = {
    "hook": "You reread that text three times before sending it.",
    "explain": "Psychologists call it the imaginary audience effect. "
               "Your brain stages a courtroom trial for one short message.",
    "reframe": "That's not insecurity, it's evidence you care how you land. "
               "Most people are too busy to grade your wording.",
    "cta_question": "What's the longest you've ever rehearsed a text?",
    "specificity": "three times",
    "title": "Why You Reread Every Text Before You Send It",
}


def test_good_topic_passes():
    assert sop.validate_topic(GOOD_TOPIC) == []


def test_hook_too_long_is_flagged():
    t = dict(GOOD_TOPIC, hook="One two three four five six seven eight nine ten eleven")
    assert any("hook is" in e for e in sop.validate_topic(t))


def test_banned_phrase_is_flagged():
    t = dict(GOOD_TOPIC, reframe="Basically you should subscribe to the channel now.")
    errs = sop.validate_topic(t)
    assert any("banned phrase" in e for e in errs)


def test_cta_must_be_a_question():
    t = dict(GOOD_TOPIC, cta_question="Tell me about it below.")
    assert any("question" in e for e in sop.validate_topic(t))


def test_specificity_spike_must_appear_verbatim():
    t = dict(GOOD_TOPIC, specificity="seventeen times")
    assert any("specificity" in e for e in sop.validate_topic(t))


def test_title_formula_enforced():
    assert sop.validate_title("Why You Overthink Everything") == []
    assert sop.validate_title("5 Signs You Overthink") == []
    assert sop.validate_title("An Essay About Overthinking")  # non-empty -> violation


def test_format_cta_appends_suffix_and_question_mark():
    assert sop.format_cta("How long did yours last") == "How long did yours last? Drop it below."
    assert sop.format_cta("Already a question?") == "Already a question? Drop it below."


def test_title_helpers():
    assert sop.title_why("You Overthink", "Every Text") == "Why You Overthink Every Text"
    assert sop.title_number(5, "Signs", "You Overthink") == "5 Signs You Overthink"


# --------------------------------------------------------------------------- #
# Auto-direction
# --------------------------------------------------------------------------- #
def test_infer_face_categories():
    assert direction.infer_face("You suddenly realize the truth.") == "surprised"
    assert direction.infer_face("You feel completely alone.") == "sad"
    assert direction.infer_face("Finally you win and feel proud.") == "happy"
    assert direction.infer_face("Plain statement with nothing.", "neutral") == "neutral"


def test_infer_pose_matches_meaning():
    assert direction.infer_pose("Most people are too busy rushing around.") == "walk_a"
    assert direction.infer_pose("Your brain keeps replaying it.") == "think"
    assert direction.infer_pose("The weather was mild today.", "stand") == "stand"


def test_infer_prop_picks_relevant_metaphor():
    assert direction.infer_prop("Psychologists call it surface acting.", 0)["name"] == "brain"
    assert direction.infer_prop("It quietly drains your energy.", 0)["name"] == "battery"
    assert direction.infer_prop("Everyone in the audience is watching you.", 0)["name"] == "eye"
    p = direction.infer_prop("A totally neutral line about nothing.", 0)
    assert p is None


# --------------------------------------------------------------------------- #
# Whiteboard stroke-reveal geometry
# --------------------------------------------------------------------------- #
def test_part_reveal_is_sequential():
    # part 0 fully drawn before part 1 starts, etc.
    assert _part_reveal(0.0, 0, 6) == 0.0
    assert _part_reveal(1.0 / 6, 0, 6) == 1.0      # first part done at 1/6
    assert _part_reveal(1.0 / 6, 1, 6) == 0.0      # second part not started yet
    assert _part_reveal(1.0, 5, 6) == 1.0          # everything done at the end
    # monotonic non-decreasing for a fixed part as g grows
    vals = [_part_reveal(g / 20, 3, 6) for g in range(21)]
    assert vals == sorted(vals)


def test_truncate_returns_arclength_fraction():
    pts = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]  # total length 20
    out, tip = Sketcher._truncate(pts, 0.5)        # halfway -> end of first segment
    assert tip == (10.0, 0.0)
    assert Sketcher._truncate(pts, 1.0)[1] == (10.0, 10.0)
    assert Sketcher._truncate(pts, 0.0)[1] == (0.0, 0.0)


# --------------------------------------------------------------------------- #
# Rendering smoke test (integration) - both story schemas must render a frame
# without raising, so engine changes can't silently break either pipeline.
# --------------------------------------------------------------------------- #
import pytest  # noqa: E402

from faceless import render                          # noqa: E402
from faceless.model import RESOLUTIONS, load_script  # noqa: E402

_STORIES = sorted((ROOT / "stories").glob("*.json"))


def test_sound_synthesis_shapes():
    from faceless import sound
    assert sound.pop().ndim == 1 and len(sound.pop()) > 0
    assert abs(sound.ding()).max() <= 1.0
    assert len(sound.whoosh(0.2)) == int(sound.SR * 0.2)


def test_sound_mix(tmp_path):
    import numpy as np
    import soundfile as sf

    from faceless import sound
    master = tmp_path / "m.wav"
    sf.write(str(master), np.zeros((sound.SR * 2, 2), dtype=np.float32), sound.SR)
    out = tmp_path / "scored.wav"
    assert sound.mix(master, out, cuts=[1.0], dings=[1.0])
    data, sr = sf.read(str(out))
    assert sr == sound.SR and abs(data).max() <= 1.0 and abs(data).max() > 0  # SFX got mixed in


@pytest.mark.skipif(not _STORIES, reason="no story JSONs present")
@pytest.mark.parametrize("which", ["new", "old"])
def test_render_frame_smoke(which):
    # a new-schema SOP story (beat/camera/draw_on) and an old-schema one
    new = ROOT / "stories" / "imaginary_audience.json"
    story = new if (which == "new" and new.exists()) else _STORIES[0]
    script = load_script(story)
    size = RESOLUTIONS["9:16"]
    scene = script.scenes[0]
    scene.duration = 3.0
    for fi in (0, 25, 60):       # exercise draw-on, hold, blink/effects
        img = render.render_frame(script, scene, fi / 24.0, size, min(size), fi)
    assert img.size == size
