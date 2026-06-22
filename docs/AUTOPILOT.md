# Autopilot — auto-generate & publish 2 videos/day

A hands-off pipeline that **generates a fresh script → renders the video with
Piper → makes a thumbnail → uploads to YouTube**, twice a day.

## The one hard constraint

This **can't run inside the Claude chat session** — that container is ephemeral
and is wiped when the session ends. The continuous "backend" is **GitHub Actions**:
GitHub runs the pipeline on a schedule, in its own cloud, for free. No server for
you to maintain.

```
GitHub Actions cron (06:00 / 18:00 UTC)
  └─ autopilot.run
       topics.py     → pick fresh, non-repeating briefs (rotates kinds)
       scriptwriter  → Claude writes the script (or offline templated fallback)
       produce.py    → render 16:9 (Piper voice) + auto thumbnail + metadata
       youtube.py    → upload, set thumbnail, add to playlist, schedule publish
  └─ commit state.json  (so nothing repeats)
```

---

## Setup (one time, ~20 minutes)

### 1. YouTube API access (OAuth)
1. [Google Cloud Console](https://console.cloud.google.com/) → create a project.
2. **APIs & Services → Enable APIs → "YouTube Data API v3" → Enable.**
3. **OAuth consent screen** → External → add your Google account as a *Test user*.
4. **Credentials → Create credentials → OAuth client ID → Desktop app.** Copy the
   **Client ID** and **Client secret**.
5. On your own machine:
   ```bash
   pip install google-auth-oauthlib
   YT_CLIENT_ID=xxx YT_CLIENT_SECRET=yyy python scripts/youtube_authorize.py
   ```
   A browser opens; approve. It prints `YT_REFRESH_TOKEN` (plus the id/secret).

### 2. (Recommended) Claude API key — for script quality
The "auto-generated daily" topics are written by Claude when a key is present;
without it, a lower-quality **offline templated** writer runs. Get a key at
[platform.claude.com](https://platform.claude.com/) → `ANTHROPIC_API_KEY`.
Quality is the main lever on views, so this is strongly recommended.

### 3. Add the secrets to GitHub
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Required | What |
|---|---|---|
| `YT_CLIENT_ID` | ✅ | from step 1 |
| `YT_CLIENT_SECRET` | ✅ | from step 1 |
| `YT_REFRESH_TOKEN` | ✅ | from step 1 |
| `ANTHROPIC_API_KEY` | recommended | script quality |

### 4. Turn it on
The workflow (`.github/workflows/daily-publish.yml`) runs automatically on cron.
**Test it first:** Actions tab → *Daily publish* → **Run workflow** with
`count=1`, `publish_mode=private`. Check the run logs and your YouTube Studio.

---

## ⚠️ The audit caveat (read this)

Until your Google Cloud project passes the **YouTube API Services audit**, videos
uploaded *via the API* are **locked to Private** regardless of the status we
request. They appear in your Studio and you publish them manually.

- **Day 1 reality:** this is effectively a review queue — exactly the safe default.
- **To unlock auto-public/scheduled:** submit the *YouTube API Services Audit and
  Quota Extension* form. Auto-generated content can be scrutinized, so quality and
  variety matter. Once approved, `publish_mode: schedule` makes videos go public
  automatically at the configured slots.

---

## Quota & cost
- **YouTube quota:** an upload ≈ 1,600 units; 2/day ≈ 3,200 of the default
  10,000/day. Comfortable.
- **Claude:** a script is a few cents on `claude-opus-4-8`. To cut cost, set
  `"model": "claude-sonnet-4-6"` in `autopilot/config.json`.
- **GitHub Actions:** free for public repos; private repos get 2,000 min/month.
  Each run is ~15–30 min.

---

## Configure — `autopilot/config.json`
| Key | Meaning |
|---|---|
| `videos_per_day` | how many per run (default 2) |
| `publish_mode` | `schedule` (private + publishAt), `public`, or `private` |
| `publish_slots_utc` | when scheduled videos go public (UTC; `13:00`≈8AM ET, `01:00`≈8PM ET) |
| `script_backend` | `auto` (Claude if key present, else offline), `claude`, `offline` |
| `model` | Claude model id |
| `rotation` | order of topic kinds: `whatif`, `howto`, `otheryou`, `reflection` |
| `category_id` | YouTube category (`22` = People & Blogs) |

Env vars override per-run in CI: `VIDEOS_PER_DAY`, `PUBLISH_MODE`, `SCRIPT_BACKEND`, `MODEL`.

## Topics
Auto-generated in `autopilot/topics.py` — edit the `briefs` lists to steer or
expand. `autopilot/state.json` tracks used briefs so videos don't repeat.

## Run locally
```bash
pip install -r requirements.txt -r autopilot/requirements.txt
bash scripts/setup_piper.sh                 # or let it fall back to Festival
python -m autopilot.run --count 1 --no-upload      # produce only, inspect output/
python -m autopilot.run --count 1 --publish private # produce + upload as private
```

## Honest note on policy & quality
Fully automated faceless uploads can trip YouTube's **repetitive / inauthentic
content** policies, which also affect monetization. Lowest-risk path: keep
`publish_mode` at `schedule`/`private` and skim each before it goes public, keep
topic variety high, and use the Claude backend so every script is genuinely fresh.
This is why the 0-views problem is fixed by *quality + thumbnails/titles*, not by
volume alone.
