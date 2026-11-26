# One-time setup

**Fastest start, all from your phone (about 10 minutes):** do steps 1 and 2 only. With those 3 secrets the agent
already makes your daily Shorts and movies and sends each finished video to Telegram with the title, description
and tags ready to copy — you upload it from the YouTube app and tap **✅ I uploaded it**.
Do step 3 later (on a computer) and the agent uploads by itself after your tap.

You'll create 6 secrets in this GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**.
Never paste these keys into a chat, an issue or a file.

| Secret | What it is |
|---|---|
| `TELEGRAM_BOT_TOKEN` | your Telegram bot's token (step 1) |
| `TELEGRAM_CHAT_ID` | your own Telegram chat id (step 1) |
| `GEMINI_API_KEY` | Gemini API key (step 2) |
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | permission to post on your channel (step 3) |

A computer browser is easiest for step 3; the rest works from a phone.
The schedules are already switched on: until the secrets are in, each run just notes "Setup not finished" and stops.

## 1. Telegram bot (5 min)

1. In Telegram open **@BotFather** → send `/newbot` → name it (e.g. *History with Me Agent*) →
   pick a username ending in `bot`. BotFather replies with a **token** → save it as the secret `TELEGRAM_BOT_TOKEN`.
2. Open your new bot and send it any message (e.g. `hi`).
3. In GitHub: **Actions → Check setup → Run workflow**. The bot replies with your chat id →
   save it as the secret `TELEGRAM_CHAT_ID`. (Only messages from this chat are obeyed.)

## 2. Gemini API key (3 min)

1. Open https://aistudio.google.com/apikey → **Create API key** → save it as `GEMINI_API_KEY`.
   The free tier is enough for the agent's brain and, while its quota lasts, the voice.
2. For cinematic AI video (and Gemini pictures): in AI Studio, **set up billing** on the key's project — video has no
   free tier. See PLAYBOOK.md for what it costs and how to cap it.
   Your Gemini (Google AI Pro) app subscription doesn't pay for API calls by itself, but Google AI Pro can come with
   monthly Google Cloud credits you can claim in AI Studio and spend on the Gemini API (availability varies by country).
   Set a budget alert in Google Cloud Billing.

## 3. YouTube permission (15 min, computer recommended)

1. https://console.cloud.google.com → create a project, e.g. *History with Me Agent*.
2. **APIs & Services → Library** → enable **YouTube Data API v3** and **YouTube Analytics API**.
3. **Google Auth Platform** (OAuth consent screen): user type **External**, app name, your email.
   Under **Audience**, add your Gmail as a test user, then press **Publish app** (status *In production*).
   This matters: in *Testing* status the permission expires every 7 days. Google will show an
   "unverified app" warning when you sign in — that's expected for your own private app (Advanced → continue).
4. **Clients / Credentials → Create OAuth client ID** → type **Web application** →
   Authorized redirect URI: `https://developers.google.com/oauthplayground` → create →
   save the **Client ID** as `YT_CLIENT_ID` and the **Client secret** as `YT_CLIENT_SECRET`.
5. Open https://developers.google.com/oauthplayground → ⚙️ (top right) → tick **Use your own OAuth credentials** →
   paste the client ID and secret.
6. In "Input your own scopes" paste (one line):
   `https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/youtube.force-ssl https://www.googleapis.com/auth/yt-analytics.readonly`
   → **Authorize APIs** → sign in with the Google account that owns the channel → **choose the History with Me channel**
   → allow.
7. **Exchange authorization code for tokens** → copy the **Refresh token** → save it as `YT_REFRESH_TOKEN`.

## 4. Check everything

**Actions → Check setup → Run workflow.** It tests Gemini, YouTube (channel name, subscribers, watch hours),
Telegram and the free voice, and lists anything missing. Your bot says *"History with Me agent is connected"*.

## 5. First test run

Want to see the free production line first? **Actions → Demo Short (free) → Run workflow** makes one real Short with
no keys at all (free pictures, archive photos, free voice); with Telegram set up it arrives in your chat.

**Actions → Make Shorts → Run workflow**, tick **Test only** → in about 10 minutes the preview arrives on Telegram
(nothing is kept or uploaded). Then run it again without *Test only*, tap **✅ Publish now** under the preview,
and within an hour the Short is live. You can also start **Approvals (Telegram)** by hand to act at once.

From then on everything runs on its own (times in IST):

| Workflow | When |
|---|---|
| Make Shorts (story + loop) | every day 06:11 |
| Make history movie | Wednesday and Sunday 05:53 |
| Approvals (Telegram) | every hour 06:37–23:37 |
| Weekly report | Monday 08:47 |

"Best time" publishes at 19:00 (story), 12:30 (loop) and 18:30 (movie) — change these in `data/plan.json`.

## 6. Optional settings (Settings → Secrets and variables → Actions → **Variables**)

| Variable | Values | Default |
|---|---|---|
| `PICTURES` | `auto` (Gemini AI if billing works, else free AI; real archive photos for real events), `free`, `archive`, `gemini` | `auto` |
| `MOVIE_PICTURES` | same, for movies only (set `free` to keep costs low) | `PICTURES` |
| `SHORTS_AI_PICTURES_MAX` / `MOVIE_AI_PICTURES_MAX` | most paid AI pictures per video (0 = no limit); the rest are free | `0` / `30` |
| `CINEMATIC` | `auto` = Shorts are real AI video shots when billing allows; `off` = pictures with camera moves | `auto` |
| `CINE_FORMATS` | Short formats to rotate: `pov`, `trailer`, `timetraveler` | `pov,trailer` |
| `SHORT_VIDEO_BUDGET` / `LOOP_VIDEO_BUDGET` / `MOVIE_VIDEO_BUDGET` | most dollars of AI video per video (0 = none) | `3` / `1` / `3` |
| `VIDEO_RESOLUTION` | `720p` (≈ $0.10/s, upscaled to 1080p for free) or `1080p` (≈ $0.15/s) | `720p` |
| `MOVIE_MOTION` | how many key movie scenes become AI video | `4` |
| `VOICE` | `auto`, `gemini`, `free` | `auto` |
| `TEXT_MODEL`, `TTS_MODEL`, `IMAGE_MODEL` | pin a Gemini model; empty = newest Flash model the key can use | empty |

Secret `POLLINATIONS_TOKEN` (recommended if you stay on the free route): without it, the free AI picture service is slow
(about one picture every 15 seconds) and in our first real run it refused about half the requests — the agent then used
real archive photos instead. A free account at https://auth.pollinations.ai gives a token that makes free AI pictures
reliable. With Gemini billing on, Gemini draws the pictures and this doesn't matter.

## 7. Music (optional, recommended)

See `music/README.md` — drop a few tracks from the YouTube Audio Library into `music/`.

## Good to know

- **Approval first:** finished videos wait as private files in a *draft release* of this repo (Code → Releases).
  Nothing goes to YouTube until you tap. Discarded or uploaded videos are removed from there.
- **Two things YouTube's API can't do** (the agent reminds you): pinning the comment it posts, and setting a
  Short's *Related video*. Do both in YouTube Studio — link each Short to the newest movie.
- **Custom thumbnails** need a phone-verified channel: verify once at https://www.youtube.com/verify.
- **AI label:** every upload is marked "altered or synthetic content" and the description says what is AI-made.
- **Public or private repo:** in a *public* repo, Actions minutes are free and unlimited, but anyone can read the code,
  the plan, the agent's memory (`state/`) and the run logs. Secrets and the videos waiting for approval stay hidden either way.
  In a *private* repo only you see everything, within 2,000 free minutes a month (this setup uses roughly 1,200–1,500;
  if you run short, make approvals run every 2 hours: `cron: "7 1-18/2 * * *"` in `approvals.yml`).
  Change it in Settings → General → Danger Zone → Change visibility.
- **Something failed?** The bot tells you. Details: Actions → the red run → open the step.
