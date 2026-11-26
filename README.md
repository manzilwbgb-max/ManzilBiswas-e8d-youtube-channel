# History with Me — YouTube agent

An agent that runs your channel's daily production on GitHub (no app, no server):
it picks trending, search-friendly history topics, writes and fact-checks the script,
makes the pictures and voice, edits the video, and sends it to you on **Telegram**.
**Nothing reaches YouTube until you tap a button.**

```
06:11 IST every day      ──►  1 story Short (20–35 s) + 1 loop Short (5–12 s)
05:53 IST Wed & Sun      ──►  1 history movie (≈15 min, 6 chapters, thumbnail)
                                  │
             trend scout → strategist picks topic → Wikipedia research → script
             → fact-check → pictures + voice → camera moves, captions, music → video
                                  │
                    Telegram preview with buttons ──► you decide
   ✅ Publish now · ⏰ Best time · 🔒 Private · 🔁 Remake · 🗑 Discard
                                  │
every hour 06:37–23:37 IST ──►  agent reads your taps → uploads to YouTube
                                (AI label on) → pinned-comment text → series playlist
Monday 08:47 IST           ──►  weekly report: progress to monetization + what to double down on
```

## Talk to it on Telegram

| You send | It does |
|---|---|
| `/make Titanic` | makes a story Short about it now (topic optional) |
| `/loop` · `/movie Fall of Rome` | a loop Short or a 15-minute movie now |
| `/idea movie: The lost city of Dwarka` | saves a topic for later |
| `/next` · `/pending` · `/trends` · `/status` | what's coming · what waits for you · what's hot · progress |
| `/pause` · `/resume` | stop / restart the daily videos |
| plain words ("make a short about Ashoka") | understood too |

It checks Telegram once an hour, so give it up to an hour to react.

## Free or paid — your choice, any time

| Part | Free (no billing) | With Gemini API billing |
|---|---|---|
| Brain: topics, scripts, fact-check | Gemini free tier | same, higher limits |
| Voice | Gemini voices while the free quota lasts, then a free offline voice (Piper) | Gemini voices |
| Pictures | free AI pictures (Pollinations) + real public-domain archive photos (Wikimedia Commons) | Gemini AI pictures first, archive photos for real events |
| Motion | cinematic camera moves on every picture | optional real AI video clips (Veo) for the opening scenes |

The agent switches automatically: if billing is off or a quota runs out mid-video, it falls back
to the free source and keeps one voice for the whole video. Change the defaults with repository
**Variables** (see SETUP.md, step 6).

## Files

- `agent/` — the agent (strategist, renderer, YouTube, Telegram, storage)
- `data/plan.json` — the 30-day plan: 30 story Shorts, 20 loops, 9 movies, series, publish times
- `state/` — the agent's memory (videos, ideas used, your saved ideas) — written by the agent
- `music/` — put royalty-free tracks here (see `music/README.md`)
- `.github/workflows/` — the schedules
- `SETUP.md` — one-time setup (about 30–40 minutes)
- `PLAYBOOK.md` — the channel strategy the agent follows
