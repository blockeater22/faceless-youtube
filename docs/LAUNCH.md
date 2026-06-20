# Launch playbook — Inklings

Everything to launch and run the channel at **2 videos/day**, batch-produced
**14 every Sunday**.

---

## 1) Playlists

Create these **4 playlists** and drop every upload into one (playlists fuel
"binge" recommendations and watch-time). Keep titles short — they show in the
sidebar.

| Playlist | What goes in it | Use as |
|---|---|---|
| **What If…** | speculative, mind-bending hooks ("what if X were true?") | 🏠 flagship / pinned playlist |
| **The Other You** | parallel lives, alternate selves, the road not taken | emotional core |
| **3 AM Thoughts** | quiet, existential, the ones that linger before sleep | reflective |
| **The Twist** | 60-second stories with an emotional turn or reveal | high-comment |

**Playlist descriptions (paste these):**
- *What If…* — "Tiny stick-figure stories that start with two words: what if. New mind-benders every day."
- *The Other You* — "Somewhere there's a version of you who chose differently. Short hand-drawn stories about the lives running parallel to yours."
- *3 AM Thoughts* — "The thoughts that keep you up at night, drawn in 60 seconds. Watch before you sleep."
- *The Twist* — "Little stories, big feelings. Stay till the end."

> Set **What If…** as the channel's featured/pinned playlist in Customisation.

---

## 2) First 14 titles (one week, 2/day)

Title + the one-line premise that seeds each script. Balanced across playlists,
front-loaded with the strongest hooks.

| # | Day · slot | Title | Playlist | Premise (script seed) |
|---|---|---|---|---|
| 1 | Mon AM | **What If Every Choice You Never Made Still Happened?** | What If… | Parallel selves live out your unmade choices. *(already produced)* |
| 2 | Mon PM | **Everyone You Walk Past Has a Life as Deep as Yours** | 3 AM Thoughts | Sonder — a crowd where every figure hides a whole universe. |
| 3 | Tue AM | **What If You Could See How Many Days People Had Left?** | What If… | Numbers float above heads; a stranger's reads "1." |
| 4 | Tue PM | **He Waved at the Same Stranger Every Day** | The Twist | …until the morning she didn't come back. |
| 5 | Wed AM | **Somewhere, There's a You Who Never Gave Up** | The Other You | One moment splits into two lives. |
| 6 | Wed PM | **One Day You'll Do Everything for the Last Time** | 3 AM Thoughts | The "last times" you never notice happening. |
| 7 | Thu AM | **What If Every Lie Took One Day Off Your Life?** | What If… | The honest man vs. the one who couldn't stop. |
| 8 | Thu PM | **The Old Man Fed the Birds Every Morning** | The Twist | Reveal: he's keeping a promise to someone gone. |
| 9 | Fri AM | **You Met the You From Ten Years Ago. He's Watching.** | The Other You | Your younger self sees who you became. |
| 10 | Fri PM | **You're Not Afraid of the Dark** | 3 AM Thoughts | You're afraid of being alone in it. |
| 11 | Sat AM | **What If You Woke Up as the Version of You Who Won?** | What If… | Trading places with your best timeline. |
| 12 | Sat PM | **She Left One Seat Empty on Every Bus** | The Twist | For the person who used to sit there. |
| 13 | Sun AM | **There's a You That Stayed Home. Is He Happier?** | The Other You | The road not taken, revisited. |
| 14 | Sun PM | **What If You Remembered Every Future You'll Never Live?** | What If… | Glimpses of the lives you almost had. |

*Spread:* What If… ×5 · The Other You ×3 · 3 AM Thoughts ×3 · The Twist ×3.

> Tip: keep the searchable phrase at the **front** of the title ("What if…",
> "Somewhere…") — that's what shows before truncation in feeds.

---

## 3) First pinned comment

Pin this on video #1 (it invites replies, which the algorithm rewards):

> Somewhere out there is a version of you that made the other choice. 🌌
> The one "what if" I can't stop thinking about is the night I almost didn't go.
> What's yours? I read every single reply. 💬
> *(New stories twice a day — if this one stayed with you, that's what the 🔔 is for.)*

**Reusable template** (swap the middle line per video):

> {one-line restated hook} 🌌
> {your own honest answer to the question}
> What's yours? I read every reply. 💬 — new stories twice a day.

---

## 4) Community-tab intro post

> ℹ️ The Community tab unlocks once you hit YouTube's subscriber threshold
> (currently 500). Save this for your first post; attach `branding/profile.png`.

> **Welcome to Inklings** 👋
> Little ink figures. Big questions.
>
> I take the thoughts that keep me up at night — the what-ifs, the other lives,
> the quietly mind-bending — and turn them into 60-second hand-drawn stories.
> New ones drop **twice a day**.
>
> Let's start here 👇 If you could see one number floating above everyone's
> head, what would you want it to be?

---

## 5) The Sunday batch workflow

1. **Write** — copy `stories/what_if_unmade_choices.json` 14× (or edit the
   narration + scenes); use the premises above as seeds. ~1 idea = 8–9 scenes.
2. **Render** — `for f in stories/week/*.json; do python -m faceless build "$f"; done`
   (renders 9:16 + 16:9 for each; ~2 min each on CPU).
3. **Schedule** — upload all 14, set Visibility → **Schedule**, 2/day (one AM,
   one PM) across the week, each added to its playlist with the title +
   description template from `docs/CHANNEL.md`.
4. **Repeat** every Sunday. The backlog means you never miss a day.

> Want me to generate the 13 remaining story JSONs from these premises so the
> renders are one command away? Just say so.
