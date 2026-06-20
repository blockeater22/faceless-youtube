# Script — "What If Every Choice You Never Made Still Happened?"

**Format:** 9:16 Short + 16:9 long-form (same script) · **Runtime:** ~52s ·
**Voice:** calm, reflective, unhurried · **Concept:** many-worlds / parallel lives.

This is the voiceover script + on-screen direction for
`stories/what_if_unmade_choices.json`. Paste the **narration** column straight
into Piper / ElevenLabs / your own mic. Timestamps are from the rendered sample.

---

| # | Time | Narration (voiceover) | On-screen |
|---|------|-----------------------|-----------|
| 1 | 0:00 | *What if every choice you never made… still happened somewhere?* | Figure alone, shifts into a **think** pose; a big amber **?** pops in above. |
| 2 | 0:05 | *Every morning, you pick one path. Left… or right.* | Figure **shrugs**; two arrows draw outward — left in amber, right in grey. |
| 3 | 0:11 | *But the other you… the one who went the other way? They didn't disappear.* | The figure splits — a faint **second self** separates and solidifies. |
| 4 | 0:17 | *They kept walking. Building a whole life out of your what-ifs.* | The other self **walks** off; a sun rises and a little **house** is drawn. |
| 5 | 0:23 | *Somewhere, you finally said yes to the thing that scared you most.* | Figure **celebrates**, arms up; amber **!** sparks pop on either side. |
| 6 | 0:29 | *Somewhere, you stayed. And somewhere, you left.* | One figure stays (grey, **sad**); another **walks** out of frame. |
| 7 | 0:33 | *Thousands of you. Living every single life you almost chose.* | A **crowd** of small figures fades in across the frame in varied poses. |
| 8 | 0:39 | *So tonight, when you wonder what if… remember: somewhere, you already are.* | Single figure **looks up** at a sky of amber/white stars. |
| 9 | 0:46 | *Which you do you think made it? Follow, and decide for yourself.* | Figure **waves**; a soft accent mark drifts up. (Comment-bait CTA.) |

---

## Notes for re-voicing
- Pause on the ellipses (`…`) — they're the beats that sell the idea.
- Keep it **slow and warm**. This concept lands on reflection, not energy.
- If recording yourself: record each line separately and name them
  `scene_00.wav … scene_08.wav`; the engine can be pointed at pre-recorded clips
  by setting `"backend": "none"` and dropping files into the story's `_audio/`
  folder, or just use the `piper`/`elevenlabs` backends to auto-generate.

## Remix ideas (same engine, new script)
- *"What if you could see how many days everyone had left?"* (lifespan numbers
  floating above heads — use `label` props with `follow`).
- *"What if every lie you told took one day off your life?"*
- *"What if the person you miss is missing you back, right now?"* (emotional).
- *"What if you woke up as the version of you that never gave up?"* (motivational).

Each is ~8–9 scenes of `narration` + a handful of figures/props. Copy the sample
JSON and rewrite.
