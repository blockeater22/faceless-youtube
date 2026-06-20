# faceless — stick-figure story videos, generated from a script

A tiny, dependency-light engine that turns **one JSON story file** into narrated
**hand-drawn stick-figure videos**, rendered to **both 9:16 (Shorts) and 16:9
(long-form)** from the same source. Built for running a *faceless* YouTube
channel in the minimalist "sketch that tells a story" style
(à la [@Zenn0009](https://www.youtube.com/@Zenn0009)).

```
story.json ──▶ TTS (per scene) ──▶ procedural frames (Pillow) ──▶ ffmpeg ──▶ .mp4 ×N
```

Everything is procedural — no external art assets, no GUI, no paid APIs
required. The signature "boiling line" wobble, poses, captions, motion, voice
and grain are all generated in code.

| | |
|---|---|
| **Sample story** | `stories/what_if_unmade_choices.json` |
| **Sample output** | `output/what_if_unmade_choices/*.mp4` (9:16 + 16:9) |
| **Voiceover** | offline & free by default (espeak/MBROLA); Piper or ElevenLabs optional |
| **Render speed** | ~2 min for a 50s video in *both* formats on CPU |

---

## Quickstart

```bash
# 1. system tools (Debian/Ubuntu): ffmpeg + offline TTS voices
sudo apt-get install -y ffmpeg espeak-ng mbrola mbrola-us1 mbrola-us2 mbrola-us3

# 2. python deps (isolated venv)
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 3. render the sample story to both aspect ratios
python -m faceless build stories/what_if_unmade_choices.json

# only one format:
python -m faceless build stories/what_if_unmade_choices.json --formats 9:16

# a cheat-sheet of all available poses (handy when writing a story):
python -m faceless poses --out output/_pose_sheet.png
```

Outputs land in `output/<story-name>/<story-name>_9x16.mp4` (and `_16x9.mp4`).

---

## How a story works

A story is a JSON file with `style`, `voice`, and a list of `scenes`. Each scene
has **narration** (drives the voiceover *and* the on-screen captions, and sets
the scene's length automatically) plus **actors** (stick figures) and **props**
(shapes, labels, arrows). Time inside a scene is a fraction `t` in `0..1`.

```jsonc
{
  "id": "hook",
  "narration": "What if every choice you never made... still happened somewhere?",
  "min_dur": 3.2,                     // floor; real length = max(min_dur, narration)
  "actors": [
    { "type": "figure", "id": "hero", "color": "ink", "face": "neutral",
      "keys": [                        // keyframes interpolated with easing
        { "t": 0.0, "pos": [0.5, 0.62], "pose": "stand", "scale": 0.30, "alpha": 0 },
        { "t": 0.2, "pos": [0.5, 0.62], "pose": "stand", "scale": 0.30, "alpha": 1 },
        { "t": 0.6, "pos": [0.5, 0.62], "pose": "think", "scale": 0.30, "alpha": 1 }
      ] }
  ],
  "props": [
    { "type": "label", "text": "?", "color": "accent", "size": 0.16,
      "keys": [ { "t": 0.45, "pos": [0.66,0.34], "alpha": 0, "scale": 0.4 },
                { "t": 0.70, "pos": [0.66,0.31], "alpha": 1, "scale": 1.0, "ease": "pop" } ] }
  ]
}
```

**Coordinates** are relative (`0..1` of width/height) so a single script composes
correctly in every aspect ratio. **Sizes** (figure `scale`, line width, shape
radii) are measured against the *short* edge, so figures never distort.

### Keyframe fields
`pos` `[x,y]` · `scale` (figure: fraction of short edge; label: font fraction) ·
`alpha` `0..1` · `pose` (name or inline angles) · `face` · `ease`
(`ease_in_out`·`ease_out`·`ease_in`·`pop`·`linear`) · for lines/arrows `p1`,`p2`.

### Element types
- **figure** — a stick person. `face`: `dots`·`neutral`·`happy`·`sad`·`surprised`·`shut`.
- **label** — text (great for `?`, `!`, numbers, words). `size` = fraction of short edge.
- **circle / rect / line / arrow** — sketchy shapes.
- **path** — a freehand polyline. Use `anchor`+`unit` with offset points for a
  rigid, aspect-safe shape (see the `house` in the sample); or raw `points` for
  full-frame lines. Set `"front": true` on any prop to draw it *over* the figures.

### Poses
`stand · idle · think · look_up · arms_up · celebrate · point_up · point_r ·
point_l · reach · wave · shrug · sit · walk_a · walk_b`
— alternate `walk_a`/`walk_b` across keys to make a figure stride while its
`pos` moves. Run `python -m faceless poses` to see them all.

### Style block
```jsonc
"style": {
  "background": "#0e1320", "ink": "#f2ede1", "accent": "#ffb454", "muted": "#6f7791",
  "fps": 24, "wobble": 1.7, "grain": 0.05, "vignette": 0.55,
  "caption": { "size": 0.05, "color": "#ffffff" }
}
```
Swap to a "paper" look with `background:#f7f3e9`, `ink:#1c1c1c`. `wobble` controls
the hand-drawn shake; `grain`/`vignette` add cinematic texture.

---

## Voice / narration (free, no API key)

The `voice` block is **pluggable** — see **[docs/VOICES.md](docs/VOICES.md)** for the
full rundown of open-source options (you don't need ElevenLabs). Defaults used by
the sample:

```jsonc
"voice": { "backend": "festival", "voice": "cmu_us_slt_arctic_hts", "rate": 150, "polish": true }
```

| Backend | Quality | Cost | Notes |
|---|---|---|---|
| `festival` HTS (`cmu_us_slt_arctic_hts`) | good, **smooth** | free, offline | **default**; statistical voice, no diphone seams, no key |
| `espeak` + MBROLA (`mb-us2`) | decent | free, offline | choppier; `mb-us1` female / `mb-us2` male |
| `piper` | **very good** | free, offline | best free option; set `piper_model` to a `.onnx` |
| `elevenlabs` | best | paid key | set `ELEVENLABS_API_KEY`, `backend:"elevenlabs"` |
| `gtts` | good | free (online) | needs network; blocked on some hosts |

`polish:true` runs an ffmpeg "warmth" chain (EQ + light room + loudness-normalise
to ~-16 LUFS) so even the offline voice sits well in a video.

---

## The faceless-channel playbook (research summary)

What makes this niche work, distilled from how these channels are produced:

- **One strong idea per video.** A *story or a question*, not a list. The opening
  3 seconds must pose a hook ("What if every choice you never made still
  happened?"). Retention lives or dies in the first line.
- **Short and bingeable.** 30–60s Shorts are the growth engine; repackage the
  best ones as 3–8 min compilations/long-form for watch-time + ad revenue. This
  engine exports both from one script.
- **Minimal art, maximal story.** High-contrast stick figures on a dark stage
  read instantly on a phone. The *wobble* + *grain* make it feel handmade, not
  sterile — that texture is the brand.
- **Captions always on.** Most viewers watch muted; the synced word-by-word
  captions (last word highlighted in accent) are doing half the work.
- **End on a question.** A CTA that invites a comment ("Which *you* made it?")
  feeds the algorithm. The sample does this in its last scene.
- **Consistency & batching.** Pick a lane (mind-bending "what ifs", motivational
  fables, emotional twists) and a fixed look. Because a video is *just a JSON
  file*, you can batch-write 10 scripts and render overnight.

**Title/packaging patterns that travel:** "What if …", "The reason you …",
"Nobody tells you …", "This is why …". Keep the figure + one bold accent element
in the thumbnail.

> ⚠️ Originality & policy: write your own scripts (or use them as a base, then
> rewrite). Mass-produced, near-identical AI videos risk YouTube's "inauthentic
> content" rules. This tool is a *production pipeline*, not a copy machine — the
> story is yours.

---

## Project layout

```
faceless/
  draw.py      sketch primitives (the wobbly hand-drawn line)
  figures.py   stick-figure skeleton + named poses
  anim.py      easing, interpolation, keyframe sampling
  model.py     story schema (dataclasses) + JSON loader + colours/resolutions
  tts.py       pluggable TTS backends (espeak/mbrola, piper, elevenlabs, gtts)
  media.py     ffmpeg discovery + audio helpers
  render.py    the engine: scene -> frames -> mp4 (+ audio mux), per aspect
  cli.py       `python -m faceless build|poses`
stories/       story JSON files
branding/      make_brand.py -> profile.png + banner.png (channel art)
docs/          SCRIPT.md (VO script) · VOICES.md (TTS guide) · CHANNEL.md (brand kit)
output/        rendered videos
```

## Channel branding
Run `python branding/make_brand.py` to (re)generate the profile picture and
banner. Name, tagline, and description live in **[docs/CHANNEL.md](docs/CHANNEL.md)**.

## Roadmap ideas
- word-level caption timing via forced alignment (whisper) for perfect karaoke sync
- more poses + simple props (speech bubbles, clocks, doors)
- background music bed + auto-ducking under narration
- a `new` command that scaffolds a story from a plain-text script
