# History with Me — YouTube agent

An agent that runs your channel's daily production on GitHub (no app, no server):
it picks trending, search-friendly history topics, writes and fact-checks the script,
makes the pictures and voice, edits the video, and sends it to you on **Telegram**.
**Nothing reaches YouTube until you tap a button.**

```
14:11 IST every day      ──►  1 cinematic POV/trailer Short (20–32 s) + 1 loop Short (6–10 s)
15:53 IST Wed & Sun      ──►  1 history movie (≈15 min, 6 chapters, thumbnail)
                                  │
             trend scout → strategist picks topic → Wikipedia research → script
             → fact-check → director's shot list → AI video shots + voice → sound mix, captions, music
                                  │
                    Telegram preview with buttons ──► you decide
   ✅ Publish now · ⏰ Best time · 🔒 Private · 🔁 Remake · 🗑 Discard
                                  │
every hour 06:37–23:37 IST ──►  agent reads your taps → uploads to YouTube
                                (AI label on) → pinned-comment text → series playlist
Monday 16:47 IST           ──►  weekly report: progress to monetization + what to double down on
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

**Before YouTube is connected** (SETUP step 3) the agent still makes everything: it sends you the finished video with
the title, description and tags ready to copy, you upload it from the YouTube app and tap **✅ I uploaded it**.

## Your private app: History with Me Studio

A private Claude app (only you can open it; it uses your own connections) sits on top of this agent:

- **Goal**: days left to 1 Feb 2027, live subscribers (vidIQ), the last 30 days of views and watch time (Windsor.ai),
  the pace you need against the pace you have, and the fan-funding tier.
- **Create**: pick Short / Loop / History movie and a format (POV, Trailer, Time-traveller); the agent makes it.
- **Studio**: finished videos with their SEO pack (title, description, tags, pinned comment), and one-tap
  **Upload to YouTube** (now, at the best time, or private) through your vidIQ connection, plus Regenerate and Discard.
- **Ideas**: the strategist's queue and your own ideas.
- **Coach**: ask the strategist anything; Claude answers with your real numbers.

The app talks to the agent through small files in `commands/` (the *App commands* workflow runs them, for the
repository owner's own pushes only) and reads `state/app.json`, which every run refreshes.

The Claude app needs claude.ai in a browser: inside the Claude phone app its buttons can't reach your connections.
For your phone there is also an **n8n version in SDK format** in [`n8n/`](n8n/README.md): the same buttons as a
private web page, which uploads straight to YouTube and sets the AI label itself. It needs an active n8n plan.

## Free or paid — your choice, any time

| Part | Free (no billing) | With Gemini API billing |
|---|---|---|
| Brain: topics, scripts, fact-check | Gemini free tier | same, higher limits |
| Voice | Gemini voices while the free quota lasts, then a free offline voice (Piper) | Gemini voices |
| Pictures | free AI pictures (Pollinations) + real public-domain archive photos (Wikimedia Commons) | Gemini AI pictures first, archive photos for real events |
| Video | real AI video with sound from an open model (LTX-2.3) on Hugging Face's free GPUs: about 3 clips a day, so one fully AI Short daily; pictures with camera moves after that | every Short shot is real AI video with natural sound (Gemini Omni); movies get AI video for their key scenes |

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
