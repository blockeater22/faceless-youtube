from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

from autopilot import gemini_pool, hf_rate_limit, provider_router, scheduler, scriptwriter
from autopilot.pipeline import request_from_form


class FacelessUiPipelineTests(unittest.TestCase):
    def tearDown(self) -> None:
        gemini_pool.reset_for_tests()
        hf_rate_limit.reset_for_tests()

    def test_gemini_pool_reads_multiple_keys(self) -> None:
        with mock.patch.dict(os.environ, {"GEMINI_API_KEYS": "a,b,c"}, clear=True):
            gemini_pool.reset_for_tests()
            self.assertEqual([k.value for k in gemini_pool.keys()], ["a", "b", "c"])

    def test_gemini_invalid_key_detection(self) -> None:
        err = Exception(
            "400 INVALID_ARGUMENT API key expired. Please renew the API key. "
            "reason: API_KEY_INVALID"
        )
        self.assertTrue(gemini_pool._looks_invalid_key_error(err))
        self.assertFalse(gemini_pool._looks_quota_error(err))

    def test_gemini_model_fallback_chain(self) -> None:
        chain = gemini_pool._model_candidates("gemini-3.5-flash")
        self.assertEqual(chain[0], "gemini-3.5-flash")
        self.assertIn("gemini-3.1-flash-lite", chain)
        auto = gemini_pool._model_candidates(None)
        self.assertEqual(auto[0], "gemini-3.5-flash")
        self.assertEqual(len(auto), 5)

    def test_sanitize_preserves_image_fields(self) -> None:
        script = scriptwriter._sanitize({
            "title": "A test",
            "hook": "Look closer",
            "beats": [{
                "template": "hook",
                "narration": "What if your phone told the truth?",
                "image_prompt": "A glowing phone on a dark table, no text",
                "negative_prompt": "text, logo",
                "visual_style": "dark cinematic",
                "visual_effect": "rays",
                "scene_type": "object",
                "duration_hint": 6,
                "caption_emphasis": "told the truth",
            }],
        })
        beat = script["beats"][0]
        self.assertEqual(beat["image_prompt"], "A glowing phone on a dark table, no text")
        self.assertEqual(beat["negative_prompt"], "text, logo")
        self.assertEqual(beat["visual_effect"], "rays")
        self.assertEqual(beat["scene_type"], "object")

    def test_provider_order_defaults_to_fallback_chain(self) -> None:
        self.assertEqual(
            provider_router.normalize_order("auto"),
            ["pollinations", "cloudflare", "huggingface"],
        )
        self.assertEqual(
            provider_router.normalize_order("pollinations,cloudflare,pollinations"),
            ["pollinations", "cloudflare"],
        )
        self.assertEqual(
            provider_router.normalize_order("huggingface"),
            ["huggingface", "pollinations"],
        )

    def test_hf_rate_limit_header_parsing(self) -> None:
        wait = hf_rate_limit.parse_reset_seconds({"RateLimit": '"api";r=0;t=55'})
        self.assertEqual(wait, 55.0)
        self.assertTrue(hf_rate_limit.looks_like_quota_error(402, "purchase credits"))
        self.assertEqual(
            hf_rate_limit.looks_like_model_loading(503, '{"estimated_time": 12}'),
            12.0,
        )

    def test_kinetic_caption_word_timings(self) -> None:
        from faceless import captions

        wts = captions.estimate_word_timings("AI can imagine dreams", 4.0, "AI, imagine")
        self.assertEqual(len(wts), 4)
        self.assertTrue(wts[0].emphasis)
        self.assertTrue(wts[2].emphasis)
        self.assertEqual(captions.visible_word_count(wts, 0.0), 0)
        self.assertEqual(captions.visible_word_count(wts, wts[0].start), 1)
        self.assertEqual(captions.visible_word_count(wts, wts[2].start), 3)

    def test_ass_karaoke_writer(self) -> None:
        from faceless import captions
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "cap.ass"
            captions.write_ass_karaoke(
                [{
                    "start": 0.0,
                    "end": 3.0,
                    "spoken_dur": 2.5,
                    "text": "AI dreams",
                    "caption_emphasis": "AI",
                }],
                path,
                width=720,
                height=1280,
            )
            body = path.read_text(encoding="utf-8")
            self.assertIn("\\k", body)
            self.assertIn("AI", body)
            self.assertIn("PlayResX: 720", body)

    def test_thumbnail_copy_extraction(self) -> None:
        from autopilot.thumbnail import extract_thumbnail_copy

        script = {
            "title": "AI in Your Dreams: The Ultimate Invasion?",
            "hook": "YOUR DREAMS AREN'T YOURS",
            "beats": [{
                "template": "hook",
                "narration": "Your subconscious mind holds secrets.",
                "text": "SECRETS",
                "caption_emphasis": "AI, dreams",
            }],
        }
        self.assertEqual(
            extract_thumbnail_copy({"thumbnail_text": "AI OWNS DREAMS"}, None, ""),
            "AI OWNS DREAMS",
        )
        self.assertIn("YOUR DREAMS", extract_thumbnail_copy(script, None, ""))
        self.assertIn("SECRETS", extract_thumbnail_copy(
            {"beats": script["beats"]}, None, "fallback"
        ))

    def test_make_thumbnail_writes_png(self) -> None:
        from autopilot.thumbnail import make_thumbnail
        import tempfile

        script = {
            "hook": "AI IN YOUR DREAMS",
            "beats": [{"template": "hook", "narration": "test", "text": "AI", "icon": "eye"}],
        }
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "thumb.png"
            make_thumbnail("AI IN YOUR DREAMS", "stars", out, script=script, visual_style="stick")
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 5000)

    def test_scheduler_enriches_metadata(self) -> None:
        meta = scheduler.enrich_metadata(
            {"title": "Why You Keep Scrolling", "description": "", "tags": [], "hashtags": []},
            {"hook": "Your phone knows", "beats": [{"narration": "What would you change?"}]},
            {"kind": "howto", "brief": "How to stop doomscrolling", "playlist": "3 AM Thoughts"},
            slots_utc=["13:00", "01:00"],
        )
        self.assertIn("schedule", meta)
        self.assertIn("thumbnail_prompt", meta)
        self.assertTrue(meta["title_variants"])

    def test_voice_preview_line(self) -> None:
        from web import voices as voice_catalog

        self.assertEqual(voice_catalog.preview_line("am_liam"), "Hello Creator, I am Liam.")
        self.assertEqual(voice_catalog.catalog_for_api()["default"], "am_liam")

    def test_images_ssl_context_uses_certifi_when_available(self) -> None:
        from autopilot import images

        ctx = images._ssl_context()
        self.assertIsNotNone(ctx)

    def test_huggingface_uses_router_endpoint(self) -> None:
        from autopilot import images

        self.assertIn("router.huggingface.co", images.HF_INFERENCE_BASE)
        self.assertNotIn("api-inference.huggingface.co", images.HF_INFERENCE_BASE)

    def test_gemini_transient_error_detection(self) -> None:
        from autopilot import gemini_pool

        err = Exception("503 UNAVAILABLE. high demand. try again later")
        self.assertTrue(gemini_pool._looks_transient_error(err))
        self.assertFalse(gemini_pool._looks_quota_error(err))

    def test_channels_have_presets_and_apply(self) -> None:
        from autopilot import channels

        chs = channels.list_channels()
        self.assertGreaterEqual(len(chs), 1)
        ids = {c["id"] for c in chs}
        self.assertIn("inklings", ids)
        ch = channels.get_channel("inklings")
        cfg = channels.apply_to_config({}, ch)
        self.assertEqual(cfg["accent"], ch["palette"]["accent"])
        self.assertEqual(cfg["channel_name"], "Inklings")
        self.assertIn("persona", cfg)
        self.assertTrue(cfg["channel_hashtags"])

    def test_add_channel_validates_hex(self) -> None:
        from autopilot import channels

        with self.assertRaises(ValueError):
            channels.add_channel({"name": "X", "palette": {"accent": "nothex"}, "generate_assets": False})

    def test_add_channel_generates_brand_assets(self) -> None:
        from autopilot import channels

        assets = {
            "profile": "branding/testchan/profile.png",
            "banner": "branding/testchan/banner.png",
            "watermark": "branding/testchan/watermark.png",
        }
        tmp = Path(self.id().split(".")[-1] + "_ch.json")
        try:
            with mock.patch.object(channels, "CHANNELS_PATH", tmp):
                tmp.write_text("[]", encoding="utf-8")
                with mock.patch("autopilot.channel_architect.generate_brand_assets", return_value=assets) as gen:
                    ch = channels.add_channel({
                        "id": "testchan",
                        "name": "Test Chan",
                        "handle": "@TestChan",
                        "palette": {
                            "background": "#0e1320",
                            "ink": "#f2ede1",
                            "accent": "#ffb454",
                            "muted": "#6f7791",
                        },
                    })
            gen.assert_called_once()
            self.assertEqual(ch["assets"], assets)
        finally:
            tmp.unlink(missing_ok=True)

    def test_build_system_includes_persona_and_retention(self) -> None:
        from autopilot import scriptwriter

        sysp = scriptwriter.build_system("AcmeChannel — wild science", "energetic")
        self.assertIn("AcmeChannel", sysp)
        self.assertIn("RETENTION", sysp)
        self.assertIn("label_above", sysp)  # body templates preserved

    def test_request_from_form_reads_channel(self) -> None:
        req = request_from_form({"topic": "t", "channel_id": "inklings"})
        self.assertEqual(req.channel_id, "inklings")
        self.assertEqual(req.voice, "")

    def test_jobs_progress_advances_with_stage(self) -> None:
        from autopilot import jobs
        from autopilot.pipeline import GenerationRequest

        job = jobs.Job(id="t", request=GenerationRequest())
        job.event("script", "writing")
        self.assertEqual(jobs.serialize(job)["progress"], 30)
        job.status = "running"
        job.event("render", "rendering", {"est_render_s": 100})
        self.assertGreaterEqual(jobs.serialize(job)["progress"], 30)

    def test_scene_at_respects_hook_padding(self) -> None:
        from faceless.model import Scene, Script, Style, Voice
        from faceless.render import scene_at

        script = Script(
            title="t",
            style=Style(),
            voice=Voice(),
            scenes=[Scene(id="a", duration=4.0), Scene(id="b", duration=3.0)],
            hook="Hello",
            hook_dur=2.0,
        )
        self.assertIsNone(scene_at(script, 1.0)[0])
        self.assertEqual(scene_at(script, 2.5)[0], 0)
        self.assertAlmostEqual(scene_at(script, 5.0)[1], 3.0)
        req = request_from_form({"topic": "What if time was visible?", "format": "both", "speed": "1.0"})
        self.assertEqual(req.formats, ("16:9", "9:16"))
        self.assertEqual(req.speed, 1.0)


    def test_channel_applies_transition_pace_colors(self) -> None:
        from autopilot import channels

        cfg = channels.apply_to_config({}, channels.get_channel("inklings"))
        self.assertGreaterEqual(cfg["transition"], 0)
        self.assertGreater(cfg["pace"], 0)
        self.assertTrue(cfg["colors"])

    def test_inklings_palette(self) -> None:
        from autopilot import channels

        ch = channels.get_channel("inklings")
        self.assertEqual(ch["id"], "inklings")
        # vibrant creative direction: bright palette + a vivid figure colour set
        self.assertEqual(ch["palette"]["background"], "#101a2e")
        self.assertTrue(ch.get("colors"))
        self.assertEqual(ch["handle"], "@Inklings1")

    def test_colorize_cycles_vivid_colors_onto_props(self) -> None:
        from autopilot import produce

        colors = ["#111111", "#222222", "#333333"]
        _, props0 = produce._colorize([], [{"type": "label", "text": "hi"}], colors, 0)
        _, props1 = produce._colorize([], [{"type": "label", "text": "yo"}], colors, 1)
        self.assertEqual(props0[0]["color"], "#111111")
        self.assertEqual(props1[0]["color"], "#222222")

    def test_beats_to_scenes_honors_pace(self) -> None:
        from autopilot import produce

        beats = [{"template": "solo", "narration": "a sentence"}]
        scenes = produce._beats_to_scenes(beats, 1.4, shorts=False, pace=2.5)
        self.assertEqual(scenes[0]["min_dur"], 2.5)

    def test_phone_icon_only_rays_when_requested(self) -> None:
        from autopilot import produce

        beats = [{"template": "solo", "narration": "Your phone pulls you back.", "icon": "phone"}]
        scenes = produce._beats_to_scenes(beats, 1.4, colors=["#00d4ff"])
        phone = next(p for p in scenes[0]["props"] if p.get("name") == "phone")
        self.assertIsNone(phone.get("effect"))
        self.assertFalse(phone.get("rays"))

        beats2 = [{"template": "solo", "narration": "Your phone glows.", "icon": "phone",
                   "visual_effect": "rays", "caption_emphasis": "phone"}]
        scenes2 = produce._beats_to_scenes(beats2, 1.4)
        phone2 = next(p for p in scenes2[0]["props"] if p.get("name") == "phone")
        self.assertEqual(phone2.get("effect"), "rays")

    def test_word_sync_fraction(self) -> None:
        from faceless.render import _word_appear_fraction

        frac = _word_appear_fraction(
            "What tiny choice will you make today that will gently reshape your tomorrow?",
            "tomorrow",
        )
        self.assertGreater(frac, 0.75)

    def test_style_for_image_has_consistent_anchor(self) -> None:
        from autopilot import imagevideo

        s = imagevideo._style_for({}, None)
        self.assertIn("consistent", s.lower())
        self.assertIn("Avoid:", s)
        # stable per-video seed is deterministic
        self.assertEqual(imagevideo._base_seed("Hello"), imagevideo._base_seed("Hello"))
        self.assertNotEqual(imagevideo._base_seed("Hello"), imagevideo._base_seed("World"))

    def test_topic_research_prompt_includes_persona_and_research(self) -> None:
        from autopilot import topic_research

        ch = {"persona": "Sketch Lab energetic doodles", "rotation": ["howto", "whatif"]}
        prompt = topic_research._build_prompt("phones", 6, ch, ["Why you can't focus"])
        self.assertIn("Sketch Lab", prompt)
        self.assertIn("Why you can't focus", prompt)

    def test_custom_length_is_not_treated_as_shorts(self) -> None:
        req = request_from_form({"topic": "t", "desired_length": "about 2 minutes"})
        self.assertEqual(req.desired_length, "about 2 minutes")
        self.assertNotEqual(req.desired_length, "shorts")

    def test_transition_blends_at_scene_edge(self) -> None:
        from faceless.model import Scene, Script, Style, Voice
        from faceless import render

        script = Script(
            title="t", style=Style(transition=0.4), voice=Voice(),
            scenes=[Scene(id="a", duration=4.0), Scene(id="b", duration=3.0)],
        )
        base = render.render_frame(script, script.scenes[0], 2.0, (160, 90), 90, 0)
        # near the end of scene 0 the frame should be blended toward paper
        blended = render._apply_transition(base.copy(), script, 0, 3.95, (160, 90), 90, 0, 0.4)
        self.assertEqual(blended.size, base.size)


if __name__ == "__main__":
    unittest.main()
