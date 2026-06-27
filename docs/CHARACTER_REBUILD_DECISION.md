# Character system rebuild — should we, and how?

> A senior-engineer write-up. **Read this before deciding.** I would not
> implement the prompt as literally written without your sign-off, because the
> result wouldn't match the expectation set by the reference images.

## Where we are today

We already shipped a **bold cartoon character renderer** this session
(`figures.draw_character`). It draws: rounded head, expressive face, thick
ink outlines, yellow tee with sleeves, black shorts, white mitten hands,
oval shoes, ground shadow. Effects (sparkle/sweat/shock/`?`/motion lines)
are auto-applied per emotion. You saw it in `social_comparison_9x16.mp4`.

Honest visual gap vs. the reference (the yellow-shirt cartoon with hair,
holding a box, etc.):

| Element in the reference | Have it | Notes |
|---|---|---|
| Round head, bold outline | **Yes** | Match |
| Yellow tee with sleeves | **Yes** | Match |
| Black shorts | **Yes** | Match |
| Mitten/glove hands | **Yes** | Match |
| Shoes + ground shadow | **Yes** | Match |
| Speed/motion lines | **Yes** | Auto on motion poses |
| Sweat, `?`, sparkle, shock | **Yes** | Auto-derived from emotion |
| **Hair tufts on top of head** | **No** | Missing |
| **Eye whites + visible pupils** | **No** | We use solid dots |
| **Wide mouth shapes** (open laugh, cry, smug curl, wobble) | **Partial** | Have 6, ref needs ~10 |
| **Crossed arms, hands-on-hips, holding-box poses** | **No** | Have ~14 poses, need ~6 more |
| **Genuine "illustrator-drawn" line quality** | **Hard cap** | This is the real ceiling — see below |

The first four "No" rows are **closable on the current system** with focused
work. The last row is not.

## The real question: why won't more procedural work get us all the way?

A Toonly/Vyond-quality character isn't shapes assembled cleverly — it's
**hand-drawn artwork by an illustrator**. Their engine is simple; their
*assets* are the product. A pro stickman pack is hundreds of SVGs drawn by a
human, each with intentional curves no procedural code reproduces.

I (Claude) cannot draw SVGs by hand. I can generate them programmatically,
but a procedurally-generated SVG looks **exactly like** what we already
produce with PIL — same circles, same line weights, same clean-but-stiff
feel. Changing the file format from PNG to SVG would not change how the
character looks. **The Lego pieces have to come from a human illustrator.**

## What "modify our current system only" gets you

This is genuinely my recommendation for *most* of the gap. Specific
upgrades, each ~30–90 min of work, all on the existing engine:

1. **Hair tufts** — 2–3 small black wedges on top of the head, with 3–4
   style variants (none / tufts / side-swoosh / wild). Closes the biggest
   "missing feature" gap vs the reference.
2. **Eye whites + pupils** — white discs with smaller black pupils, so eyes
   read directionally (looking up/sideways) and blink reads better.
3. **Wider mouth library** — open-laugh, cry-wobble, smug-curl, teeth-grit,
   tongue-out. Currently 6 shapes, target ~12.
4. **6 new poses** — crossed arms, hands on hips, holding a box (arms
   forward), looking around (head turn), face-palm, two-hands-raised
   celebrate. Each is a row in the poses table.
5. **Configurable head shape** (round vs egg) and **shirt colour per actor**
   so 'you' vs 'other' contrast deeper.

**Realistic ceiling for this path:** ~90% of the visual quality of the
reference, on the bold style we already ship. Not the *last* 10% (the
illustrator-drawn feel).

## What "rebuild around modular asset system" gets you

If we did the full prompt — `CharacterAssembler`, `ExpressionEngine`,
`PoseEngine`, part registries, every body part as a swappable module — and
filled it with **procedural** parts, we get:

- A more refactored, more testable codebase.
- The same visual quality (because the parts are still procedural).
- ~1 full session of refactor work.

It only becomes a real visual win when we **drop in a real SVG pack**, at
which point the assembler is doing what it was designed for. The pack is
the unlock. Options (you'd pick, I'd integrate):

- **Free, immediate:** Open Peeps (openpeeps.com), unDraw (undraw.co), Humaaans
  — generous CC0 licenses, illustrator-drawn, but stylized differently from a
  classic stickman.
- **Paid, $30–$50 once, classic stickman style:** Envato Elements stickman
  packs, GraphicRiver doodle character packs. License covers YouTube
  monetization. Closest match to the reference.
- **DIY:** you or an illustrator on Fiverr draws a small pack ($50–200).

## My recommendation

A 2-step plan, smallest-risk-first:

### Step 1 — Push the current system (1 session, no assets)
Implement items 1–5 above. We re-render the 6 published shorts so you can
A/B the result visually against the reference image. **This is the "modify
our current system" path.** Probably gets you 85–90% of what you want.

### Step 2 (only if needed after Step 1) — Decide on the rebuild
After Step 1, look at the new output side-by-side with the reference.
- If you're satisfied → stop, ship more content with the upgraded engine.
- If the remaining gap matters → pick an SVG pack from the options above,
  I rebuild around it (the full prompt architecture, but with real
  artwork). This becomes worth the engineering time because the assets
  justify it.

Doing Step 2 *before* Step 1 risks spending a session on a refactor whose
visual payoff depends on assets we don't have yet.

## Tradeoffs at a glance

| Path | Effort | Asset cost | Visual jump | Code quality |
|---|---|---|---|---|
| **Polish current system** (recommended) | ~1 session | $0 | Big (to ~85–90%) | Same |
| **Refactor + procedural rebuild** (literal prompt) | ~1 session | $0 | Marginal | Better |
| **Refactor + buy SVG pack** | ~1 session + asset time | $0–$50 | Largest (to ~100%) | Best |
| **Pause and ship** | 0 | $0 | None | Same |

## What I'd do if it were my channel

I'd do **Step 1** this session (close the obvious gaps on the existing
engine, see how close that gets us), then make the buy/refactor decision
with the actual numbers in front of us — not on a hypothesis.

But it's your channel. Tell me which path and I'll execute it cleanly.
