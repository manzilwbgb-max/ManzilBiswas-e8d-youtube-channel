# History with Me — channel playbook

The agent's strategist follows this. Change it any time; the plan lives in `data/plan.json`.

## Positioning

**Cinematic AI history — the moments that changed everything, told in 30 seconds or 15 minutes.**
Six series, so the channel feels like a show, not a random feed:

| Series | Promise | Example |
|---|---|---|
| Prehistoric Giants | real paleontology, giant scale | Megalodon, Titanoboa, mammoths |
| Timeline Twists | famous moments with a twist | the Emu War, the 12-second first flight |
| World War Stories | human stories, told with respect | the radar warning at Pearl Harbor |
| Dig Discoveries | finds that rewrote history | Terracotta Army, Göbekli Tepe |
| India's Genius | inventions, cities and rulers of India | zero, Rani ki Vav, the Iron Pillar |
| Myth Busters | myth → evidence → truth | Vikings' horns, Napoleon's height |

## Formats

The Shorts are **cinematic AI video**, not slideshows: every shot is a real generated video clip with natural sound
(Google's Gemini Omni video model), cut together with narration, music, captions and a hook.

- **POV Short (20–32 s), daily** — the format driving the biggest AI history hits right now: "POV: You're a passenger
  on the Titanic, 11:40 PM". First-person camera, the viewer's own hands in frame, period-perfect world, second-person
  narration ("You wake up to..."), the hook written on screen for 3 seconds.
- **Trailer Short** — the same story cut like a movie trailer: epic establishing shot, rising tension, one reveal.
- **Time-traveller vlog** (optional, `CINE_FORMATS=pov,trailer,timetraveler`) — a recurring modern character vlogs
  from inside history; the same face in every shot. Characters build loyal subscribers, but keep the AI label on
  and the facts tight.
- **Loop Short (6–10 s), daily** — one breathtaking shot plus one fact that runs back into its own start.
- **History movie (~15 min), Wednesday + Sunday** — cold open, 6 chapters, open loops; the key scenes (cold open and
  chapter openers) are real AI video, the rest high-quality pictures with camera moves. This is the watch-hours engine.

Without Gemini billing the same scripts are rendered with pictures and camera moves, and the agent sends you the shot
prompts so you can make the real-video version free inside YouTube's own apps (YouTube Create / Shorts).

## What AI video costs (Gemini API list price, Nov 2026)

About $0.07 per second at 720p on Gemini Omni 1.2 (the agent upscales to 1080p for free); a 25-second cinematic Short is about $1.75, so $10 a month buys five or six. Default caps per video:
story Short $3 (≈ 30 s of video), loop $1, movie $3 (≈ 4 key scenes) — at most ≈ $4 a day plus ≈ $3 per movie,
roughly $150 a month if every video used its full cap. On top of that, `MONTHLY_VIDEO_BUDGET` (default $10)
caps the whole month: once it is reached, videos use pictures until the 1st. Keep it below your prepaid Gemini
balance plus your plan's monthly credit, because at $0 Google pauses every key on the account, the agent's brain
included. Change the per-video caps with the `SHORT_VIDEO_BUDGET`, `LOOP_VIDEO_BUDGET` and `MOVIE_VIDEO_BUDGET`
variables (0 = pictures only). The weekly report shows the real spend.

## The rules the writer follows

1. Truth first — Wikipedia research for every video, then a separate strict fact-check pass that fixes or
   hedges anything it can't support. You see the fact-check result in every preview.
2. No graphic violence, no mocking victims, advertiser-friendly wording.
3. Never copy a trending video — trends only tell us which *topics* people want right now.
4. Real archive photos (public domain) for real events; AI pictures for what no camera saw.
5. Every upload carries YouTube's AI label and a plain description of what is AI-made.

## Growth loop

- **Shorts → movie funnel:** each Short's description points to the movies; set each Short's
  *Related video* to the newest movie in YouTube Studio (the API can't do this).
- **Series playlists** are created and filled automatically — they chain viewers from one video to the next.
- **Double down on outliers:** every Monday the agent finds Shorts with ≥3× the median views and queues
  three follow-ups plus a movie on the same topic.
- **Dates that matter:** anniversaries are pinned in the plan (Napoleon 2 Dec, Pearl Harbor 85 years on 7 Dec,
  Delhi Durbar 12 Dec, Wright brothers 17 Dec, winter solstice at Newgrange 21 Dec, Christmas Truce 24 Dec).

## Numbers to watch (rules of thumb, YouTube Studio → Analytics)

| Shorts | Movies |
|---|---|
| "Viewed vs swiped away": 70%+ viewed | Click-through rate: 5%+ |
| Average % viewed: 80%+ for 20–35 s, 100%+ for loops | Average view duration: 35%+ (≈5 min of 15) |
| Subscribers per 1,000 views: 2+ | Returning viewers growing week by week |

## The honest maths (as of 26 Nov 2026)

YouTube's current bar is 1,000 subscribers plus either 4,000 public watch hours in 12 months or 10 million
Shorts views in 90 days. From 1 Feb 2027 new applicants need 8,000 hours or 20 million Shorts views
(the 1,000 subscribers stay). So the target is to **meet today's bar and apply before 1 Feb 2027**.

- **Subscribers 523 → 1,000:** at the recent ~11 a day, reachable by mid-January. Most likely to happen.
- **4,000 watch hours:** about 60 hours a day from now — roughly 700 movie views a day at ~5 minutes each.
  Needs at least one movie that takes off in search or suggested. This is the real battle; it's why movies come
  twice a week and why Shorts push viewers to them.
- **10M Shorts views in 90 days:** about 110,000 views a day. Only happens if several Shorts go viral — the
  daily cadence gives the most lottery tickets, but don't count on it.

If the deadline is missed, the channel keeps growing toward the new bar — and the lower fan-funding level
(memberships, Super Thanks; it starts at 500 subscribers with its own, lower watch requirements) is unchanged.
