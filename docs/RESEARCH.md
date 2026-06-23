# Research: trending faceless videos, voice, and monetizing fast

This is the "do the research, play devil's advocate, research again" writeup behind
the `generate` pipeline. Sources are linked inline; treat numbers as 2026-current.

---

## 1. The honest monetization timeline (read this first)

**You asked to monetize in one month. Be clear-eyed about what that means in 2026.**

YouTube now has a **two-tier** Partner Program:

| Tier | Subs | Long-form watch hours (12 mo) | OR Shorts views (90 days) |
|---|---|---|---|
| Early access (fan funding, not full ads) | **500** | 3,000 | **3M** |
| Full ad revenue | **1,000** | 4,000 | **10M** |

Sources: [YouTube Help — YPP eligibility](https://support.google.com/youtube/answer/72851),
[vidIQ 2026 guide](https://vidiq.com/blog/post/youtube-partner-program-guide/),
[MilX 2026](https://milx.app/en/trends/youtube-monetization-requirements-for-2026).

**Devil's advocate / reality check:**
- A brand-new channel hitting **3M Shorts views in 90 days** is *possible but uncommon* —
  it needs at least one Short to break out. The long-form path (3,000 hours) in 30 days
  from zero is effectively unrealistic.
- So the only credible "fast" lane is **Shorts-led**: post 1–3 Shorts/day, treat each as a
  lottery ticket for the algorithm, and convert breakouts into subscribers.
- **The biggest risk to this exact pipeline:** in 2026 YouTube is actively demoting/denying
  monetization for **"inauthentic" mass-produced AI content** — AI script + AI voice over
  generic stock/AI images with no original value
  ([influenceflow 2026](https://influenceflow.io/resources/youtube-channel-monetization-requirements-the-complete-2026-guide/)).
  A fleet of near-identical auto-generated videos is the textbook thing they penalize.

**What this means for how you use this tool (the mitigations baked into the design):**
1. **Original framing, every time.** The scriptwriter is told to *never copy* a trending
   title — only borrow angle/energy. Keep it that way.
2. **A distinct, consistent brand look.** The procedural stick-figure style (`--style stick`)
   is more original and more "authentic" than AI-photo slideshows — it's a *drawn show*, not
   recycled images. Prefer it as the channel's identity; use `--style image` for variety, not
   as the whole channel.
3. **Human-in-the-loop.** `generate` produces a file + metadata for **you to review**, it does
   not auto-publish. Review every video. That single habit is what separates a monetizable
   channel from a banned content farm.
4. **Realistic plan:** aim for **early-access (500 subs + 3M Shorts views)** as the 1–3 month
   goal, full ads as the 3–6 month goal. Anyone promising guaranteed 30-day full monetization
   is selling something.

---

## 2. Format & length (Shorts vs long-form)

- **Shorts: 15–34s is the growth sweet spot.** Long enough for a hook + payoff, short enough
  for high loop/replay rate (replays are weighted heavily). Hard cap is 3 min but new channels
  should stay short. Vertical 9:16, captions always on, payoff in the first 1–2 seconds.
- **Long-form: 6–10 min** is the watch-time/ad sweet spot for this niche (mid-rolls need ≥8 min,
  but don't pad — retention beats length). 3–5 min for a tight single-idea piece.
- **Hook in the first 3 seconds or you lose them.** Open on a question or a vivid image, not a
  channel intro. The engine puts a big on-screen `hook` on beat one for exactly this.
- **End on a question** (the `cta` beat) to drive comments — comments are a strong ranking signal.
- **One idea per video.** A story or a question, not a list. Bingeable > comprehensive.

This is why `generate` defaults to a self-sizing script and exports both 9:16 and 16:9 from one
source: **Shorts are the discovery engine, long-form is the watch-time/ad-revenue engine.**

---

## 3. Voice: pitch, pace, and the "Liam" choice

You asked for **Kokoro-82M, Liam voice** (`am_liam`). Verified specs
([voicerankings](https://voicerankings.com/voice/kokoro-82M/male/am_liam),
[Kokoro VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)):

- `am_liam` — American male, **~133 Hz** base pitch, native **~200 WPM**, described as
  *conversational, friendly, upbeat* — great for **explainer/energetic Shorts**.

**Devil's advocate:** 200 WPM upbeat is *too fast and too peppy* for calm, reflective
philosophy long-form (the channel's existing lane), where retention comes from letting lines
*land*. Research on narration retention puts the comfortable comprehension band at **~150–170
WPM**, with **pitch/pace variation** (not monotone) being the real retention lever.

**So the tuning baked into config:**
- `kokoro_speed: 0.9` slows Liam to a more deliberate ~175–180 WPM — keeps his warmth, loses the
  rush. Use **0.85** for somber pieces, **1.0–1.1** for punchy Shorts.
- Per-line trailing silence (`gap`) gives each sentence room — this is what makes it feel
  *narrated*, not *read*.
- The `polish` chain (gentle EQ + compression + −16 LUFS loudness) makes a free voice sit like a
  paid one. Loudness-normalising to **−14 to −16 LUFS** is also what YouTube expects.
- **Alternatives in the same model:** `am_michael` (deeper, more neutral), `am_onyx` (gravelly),
  `af_heart` (warm female, the previous default). Swap with `--voice`.

> Pitch is a property of the chosen Kokoro voice, not a free dial — to go lower/higher you switch
> voices (e.g. `am_onyx`/`am_michael` are lower than `am_liam`). Espeak fallback *does* expose a
> numeric pitch, but it's a last resort, not channel quality.

---

## 4. The stick-figure / "stickman" niche (what actually works)

Distilled from how channels like minimalist stick-figure storytellers are produced (the
[@Zenn0009](https://www.youtube.com/@Zenn0009) style this engine emulates):

- **High-contrast figures on a dark stage** read instantly on a phone thumbnail and at 9:16.
- **The hand-drawn "wobble" + grain is the brand** — it signals *made by a person*, which is
  exactly the authenticity signal that protects against the AI-content crackdown.
- **Captions do half the work** (most watch muted) — last word highlighted draws the eye.
- **Emotional or mind-bending single ideas** ("what if every choice you never made still
  happened?") travel further than information.
- **Consistency + batching:** one lane, one look, daily cadence. Because a video is *just a JSON
  script*, you can batch-write and render overnight.

**Devil's advocate on `--style image` (AI photos):** photoreal AI slideshows look generic, have
inconsistent faces/hands frame-to-frame, depend on a free service with no SLA, and put you
squarely in the "AI content farm" bucket YouTube is policing. Keep it as an *occasional* texture
(e.g. a cosmic/landscape piece), not the channel identity. The stick-figure engine is the moat.

---

## 5. Free tooling: what's actually free, and the catches

- **Gemini (script):** free tier in 2026 — `gemini-2.5-flash` ≈ **10 req/min, 250 req/day**;
  `flash-lite` ≈ 15 RPM / 1,000 RPD. `gemini-2.0-flash` **retired March 2026** → the code
  defaults to `2.5-flash`. Get a key at https://aistudio.google.com/apikey.
  ([rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)) — plenty for 1–3 videos/day,
  not enough for a 100-video/day farm (which is a feature, not a bug, see §1).
- **Kokoro-82M (voice):** fully local, no key, runs comfortably on an M3 (82M params, <2 GB),
  real-time or faster. #1-tier free TTS quality.
- **Pollinations (images):** no key, FLUX under the hood, but it's a *shared free service*: it
  queues under load, can rate-limit, and quality varies. The code retries with backoff and falls
  back to a clean card so a render never dies. For reliability/volume, switch `image_provider` to
  `cloudflare` (Workers AI free tier ~10k neurons/day ≈ 100+ images) or `huggingface`.
  ([Pollinations API](https://github.com/pollinations/pollinations/blob/main/APIDOCS.md))

---

## 6. The 30→90 day playbook (using this tool)

1. **Week 1:** pick ONE lane (recommend the stick-figure "what if / 3 AM thoughts" lane).
   `python -m autopilot.generate --shorts` once or twice a day. Review, tweak the title, publish
   manually. Watch which hooks pop.
2. **Weeks 2–4:** double down on whatever hook style retained best. Keep Shorts daily; start one
   6–8 min long-form/week by stitching your best Short ideas (`--format 16:9`).
3. **Month 2–3:** consistency compounds. Target **500 subs + 3M Shorts views → early-access
   monetization**. Convert breakout Shorts viewers with a pinned comment + a strong channel page.
4. **Always:** original scripts, your own brand look, human review before publish. That's the
   whole game in 2026.

---

### Sources
- [YouTube Partner Program eligibility (Help)](https://support.google.com/youtube/answer/72851)
- [vidIQ — YPP requirements 2026](https://vidiq.com/blog/post/youtube-partner-program-guide/)
- [MilX — monetization requirements 2026](https://milx.app/en/trends/youtube-monetization-requirements-for-2026)
- [influenceflow — 2026 monetization guide (inauthentic-content crackdown)](https://influenceflow.io/resources/youtube-channel-monetization-requirements-the-complete-2026-guide/)
- [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Kokoro-82M VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) ·
  [am_liam specs](https://voicerankings.com/voice/kokoro-82M/male/am_liam)
- [Pollinations API docs](https://github.com/pollinations/pollinations/blob/main/APIDOCS.md)
</content>
