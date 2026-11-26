"""History with Me - the YouTube agent.

  python -m agent.main make --kind story|loop|both|movie [--topic "..."] [--pictures auto|gemini|free|archive] [--motion N]
  python -m agent.main approvals   read your Telegram taps and messages and act on them
  python -m agent.main report      weekly progress + strategy review on Telegram
  python -m agent.main scout       this week's trending history videos, on Telegram
  python -m agent.main check       test every connection (Gemini, YouTube, Telegram, GitHub)
"""
import argparse
import datetime as dt
import os
import shutil
import sys
import time
import traceback

import requests

from . import freevideo, gemini, render, scout, store, strategist, telegram, video, youtube
from .util import DRY, WORK, get_item, items, load, log, now, put, save, slug, stamp, today

GOAL_DATE = dt.date(2027, 2, 1)
GOALS = {"subscribers": 1000, "watch_hours_12m": 4000, "shorts_views_90d": 10_000_000}
LABEL = {"story": "Story Short", "loop": "Loop Short", "movie": "History movie"}
HELP = """<b>History with Me agent</b> - I make history Shorts and movies and wait for your OK.

<b>Buttons under each video</b>
✅ Publish now · ⏰ Best time (scheduled) · 🔒 Private upload · 🔁 Remake · 🗑 Discard
Until YouTube is connected I send you the finished file to upload from the YouTube app, then you tap ✅ I uploaded it.
I check Telegram every hour, then act and update the message.

<b>Commands</b> (or just write normally)
/make topic - a story Short now (topic optional)
/loop topic - a 5-12 s loop Short now
/movie topic - a 15-minute history movie now
/idea topic - save a topic for later (/idea movie: topic)
/next - what's coming up
/pending - videos waiting for you
/trends - what's trending in history right now
/status - progress to monetization
/pause and /resume - stop or restart the daily videos"""


def plan():
    return strategist.plan()


def has_telegram():
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and telegram.chat())


def tell(text, rows=None):
    if not has_telegram():
        log("(telegram not set up)", text)
        return None
    try:
        return telegram.send(text, rows)
    except Exception as e:
        log("telegram send failed:", e)
        return None


def recent_videos(n=12):
    out = []
    for name, r in reversed(items("videos")):
        out.append({"kind": r.get("kind"), "title": r.get("title"), "series": r.get("series"), "format": r.get("format"),
                    "status": r.get("status")})
        if len(out) >= n:
            break
    return out


def slot_time(kind, p):
    hhmm = p.get("publish_slots_ist", {}).get(kind, "19:00")
    h, m = (int(x) for x in hhmm.split(":"))
    t = now().replace(hour=h, minute=m, second=0, microsecond=0)
    if t < now() + dt.timedelta(minutes=30):
        t += dt.timedelta(days=1)
    return t


def slot_label(kind, p):
    hhmm = p.get("publish_slots_ist", {}).get(kind, "19:00")
    h, m = (int(x) for x in hhmm.split(":"))
    return dt.time(h, m).strftime("%I:%M %p").lstrip("0") + " IST"


def youtube_ready():
    return all(os.environ.get(k, "").strip() for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def buttons(rid, kind, p, phone=None):
    if phone if phone is not None else not youtube_ready():
        return [[("✅ I uploaded it", f"up:{rid}")], [("🔁 Remake", f"re:{rid}"), ("🗑 Discard", f"del:{rid}")]]
    return [[("✅ Publish now", f"pub:{rid}"), (f"⏰ {slot_label(kind, p)}", f"sch:{rid}")],
            [("🔒 Private", f"prv:{rid}"), ("🔁 Remake", f"re:{rid}"), ("🗑 Discard", f"del:{rid}")]]


def copy_pack(meta, kind, p):
    """Everything to paste into the YouTube app, as tap-to-copy blocks."""
    e = telegram.esc
    return "\n".join([
        "📋 <b>Copy into the YouTube app</b>", "", "<b>Title</b>", f"<code>{e(meta['title'])}</code>", "",
        "<b>Description</b>", f"<pre>{e(meta['description'][:2600])}</pre>", "",
        "<b>Tags</b> (Show more → Tags)", f"<code>{e(', '.join(meta['tags']))[:600]}</code>", "",
        "⚙️ Altered or synthetic content: <b>Yes</b> · Made for kids: <b>No</b>",
        f"⏰ Best time to post: {slot_label(kind, p)}",
        "Pinned comment: " + (f"<code>{e(meta['pinned_comment'])}</code>" if meta.get("pinned_comment") else "-")])


def fit(lines, limit=1000):
    out = ""
    for ln in lines:
        if ln is None:
            continue
        if len(out) + len(ln) + 1 > limit:
            break
        out += ln + "\n"
    return out.strip()


# ------------------------------------------------------------------ make

def make_one(kind, topic=None, pictures=None, motion=None, trends=None):
    p = plan()
    os.environ.setdefault("TTS_STYLE", p["channel"].get("voice_style", ""))
    recent = recent_videos()
    if trends is None:
        try:
            trends = scout.trends("long" if kind == "movie" else "short", days=30 if kind == "movie" else 14, max_queries=3)
        except Exception as e:
            trends = []
            log("trend scout skipped:", e)
    idea = strategist.choose(kind, topic, trends, recent)
    facts = strategist.research(idea, kind)
    cine = strategist.cinematic_mode() and kind in ("story", "loop")
    budget = video.start(kind)
    if cine:
        script = strategist.write_cinematic(kind, idea, facts, recent)
        spec = strategist.cine_spec(kind, script, idea, p, pictures)
    else:
        script = strategist.write(kind, idea, facts, recent, trends)
        spec = strategist.spec(kind, script, idea, p, pictures, motion)
    if not budget:
        spec["motion"] = 0
    rid = f"{stamp()}-{kind}"
    work = os.path.join(WORK, rid)
    out = render.make_cinematic(spec, work) if cine else render.make(spec, work)
    usd = video.spent()
    meta = strategist.metadata(kind, script, idea, facts, out, p)
    dur = out["duration"]
    warn = list(out.get("warnings", []))
    if kind == "story" and dur > 45:
        warn.append(f"{dur:.0f} s is long for a story Short (aim 20-35 s)")
    if kind == "loop" and dur > 14:
        warn.append(f"{dur:.0f} s is long for a loop (aim 5-12 s)")
    if kind == "movie" and not 600 <= dur <= 1200:
        warn.append(f"the movie runs {dur / 60:.1f} minutes (aim 13-16)")
    fc = script.get("fact_check", {})
    srcs = {"video": "AI video", "gemini": "Gemini picture", "free_ai": "free AI picture", "archive": "archive photo"}
    pics = ", ".join(f"{v} {srcs.get(k, k)}" for k, v in out.get("sources", {}).items())
    if usd:
        pics += f" · AI video {out.get('video_seconds', 0):.0f}s ≈ ${usd:.2f}"
        if video.month_cap() is not None:
            pics += f" (this month ${video.month_spent() + usd:.2f} of ${video.month_cap():.0f})"
    if video.cap_note():
        warn.insert(0, video.cap_note())
    mins = f"{dur / 60:.1f} min" if kind == "movie" else f"{dur:.0f} s"
    caption = fit([
        f"🎬 <b>{LABEL[kind]} ready</b> · {mins} · {telegram.esc(idea['series'])}",
        f"<b>{telegram.esc(meta['title'])}</b>",
        f"Hook: “{telegram.esc((script.get('hook_text') if cine else '') or script['scenes'][0]['narration'][:140])}”",
        f"Why now: {telegram.esc(idea.get('why', '')[:160])}" if idea.get("why") else None,
        f"Fact check: {fc.get('confidence', 'unchecked')} ({len(fc.get('changes', []))} fixes)"
        + (f" · source: {telegram.esc(facts['sources'][0]['title'])}" if facts.get("sources") else ""),
        f"Format: {script.get('format') or idea.get('format', '')} · Shots: {pics} · Voice: {out.get('voice_engine') or '-'}",
        *(f"⚠️ {telegram.esc(w)}" for w in warn[:3]),
        "Not on YouTube yet. Tap a button - I check every hour." if youtube_ready() else
        "YouTube isn't connected yet: save this video and upload it from the YouTube app, then tap ✅.",
    ])
    if kind == "movie":
        caption = fit([caption, "", "<b>Chapters</b>"] + [f"{strategist._stamp_time(c['start'])} {telegram.esc(c['title'])}"
                                                           for c in out.get("chapters", [])])
    rec = {"id": rid, "kind": kind, "title": meta["title"], "description": meta["description"], "tags": meta["tags"],
           "pinned_comment": meta["pinned_comment"], "series": idea["series"], "format": idea.get("format"),
           "topic": idea["topic"], "idea": idea["id"], "idea_source": idea.get("source"), "why": idea.get("why", ""),
           "made": now().isoformat(), "duration": dur, "status": "waiting", "caption": caption,
           "fact_check": fc, "sources": facts.get("sources", []), "warnings": warn, "pictures": out.get("sources", {}),
           "video_usd": usd}
    if DRY:
        log("DRY RUN - nothing uploaded.", rec["title"], f"{dur:.1f}s", out["video"])
        if os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPOSITORY"):
            import json
            kept = store.keep(f"{rid}-test", {"test-video.mp4": out["video"]}, f"TEST: {meta['title']}\n\n{caption}")
            print("TEST STORED " + json.dumps(kept), flush=True)
        if has_telegram():
            telegram.send_video(out["preview"], "🧪 <b>TEST RUN</b> (not stored, not uploaded)\n" + caption)
            if out.get("thumbnail"):
                telegram.send_photo(out["thumbnail"], "Thumbnail")
        return rec
    if cine and not out.get("sources", {}).get("video") and has_telegram() and not DRY:
        cards = [f"{i + 1}. {telegram.esc(sh['visual'][:300])}" for i, sh in enumerate(script["shots"])]
        tell(fit(["🎬 <b>Want this one as real AI video for free?</b> YouTube's own apps (YouTube Create, Shorts) include "
                  "Google's video model. Paste these shot prompts there, one per clip:", ""] + cards, 4000))
    files = {"video.mp4": out["video"]}
    if out.get("thumbnail"):
        files["thumbnail.jpg"] = out["thumbnail"]
    rec["release"] = store.keep(rid, files, f"{meta['title']}\n\n{meta['description'][:1500]}")
    video.record_spend(rid, kind)
    put("videos", rid, rec)
    strategist.mark_used(idea, rid)
    if has_telegram():
        phone = not youtube_ready()
        if out.get("thumbnail"):
            if phone:
                telegram.send_document(out["thumbnail"], f"Thumbnail for: <b>{telegram.esc(meta['title'])}</b>",
                                       filename="thumbnail.jpg", mime="image/jpeg")
            else:
                telegram.send_photo(out["thumbnail"], f"Thumbnail for: <b>{telegram.esc(meta['title'])}</b>")
        if phone:
            if kind == "movie":
                link_ = (rec["release"].get("links") or {}).get("video.mp4", "")
                caption = fit([caption, "", f"Full movie (sign in to GitHub to download): {link_}" if link_ else
                               "Full movie: GitHub → your repo → Releases (draft)."], 1024)
                msg = telegram.send_video(out["preview"], caption, buttons(rid, kind, p, phone=True))
            else:
                final = render.fit_size(out["video"], os.path.join(work, "telegram.mp4"))
                msg = telegram.send_video(final, caption, buttons(rid, kind, p, phone=True),
                                          filename=f"{slug(meta['title'], 50)}.mp4")
            telegram.send(copy_pack(meta, kind, p))
        else:
            msg = telegram.send_video(out["preview"], caption, buttons(rid, kind, p))
        rec["caption"] = caption
        rec["message_id"] = msg.get("message_id")
        put("videos", rid, rec)
    shutil.rmtree(work, ignore_errors=True)
    log(f"made {kind}: {meta['title']} ({dur:.1f}s) -> waiting for approval as {rid}")
    return rec


def make(kind, topic=None, pictures=None, motion=None):
    if load("control.json", {}).get("paused") and not topic:
        log("the agent is paused (send /resume on Telegram)")
        return 0
    if not DRY and not telegram.reachable():
        print("::error::Telegram can't reach your chat, so nothing was made and nothing was spent. "
              "Run 'Check setup': it tells you what to fix (usually the TELEGRAM_CHAT_ID secret).")
        return 1
    kinds = ["story", "loop"] if kind == "both" else [kind]
    trends, failed = None, 0
    if len(kinds) > 1:
        try:
            trends = scout.trends("short", days=14, max_queries=3)
        except Exception as e:
            trends = []
            log("trend scout skipped:", e)
    for k in kinds:
        try:
            make_one(k, topic if k == kinds[0] else None, pictures, motion, trends)
        except Exception as e:
            failed += 1
            traceback.print_exc()
            why = gemini.quota_verdict(e)
            if why:
                tell(f"⚠️ Today's {LABEL[k].lower()} wasn't made: Gemini refused ({telegram.esc(why)}).\n"
                     "Nothing was paid for. Billing: aistudio.google.com/billing")
            else:
                tell(f"⚠️ Today's {LABEL[k].lower()} failed: <code>{telegram.esc(str(e)[:600])}</code>\n"
                     f"I'll try again at the next run. If it repeats, open GitHub → Actions to see the log.")
    return 1 if failed == len(kinds) else 0


# ------------------------------------------------------------------ approvals

def after_publish(rec, p):
    try:
        _after_publish(rec, p)
    except Exception as e:
        log("comment/playlist step skipped:", e)


def _after_publish(rec, p):
    vid = rec.get("video_id")
    if not vid:
        return
    if rec.get("pinned_comment") and not rec.get("comment_done"):
        rec["comment_done"] = youtube.comment(vid, rec["pinned_comment"])
    if not rec.get("playlist_done"):
        s = strategist.series_of(rec.get("series"), p)
        title = s.get("playlist")
        if title:
            try:
                pls = load("playlists.json", {})
                pid = pls.get(title) or youtube.playlist_for(title, s.get("about", ""))
                pls[title] = pid
                save("playlists.json", pls)
                rec["playlist_done"] = youtube.playlist_add(pid, vid)
            except Exception as e:
                log("playlist skipped:", e)


def link(rec):
    vid = rec.get("video_id", "")
    return f"https://youtube.com/shorts/{vid}" if rec.get("kind") != "movie" else f"https://youtu.be/{vid}"


def latest_movie():
    for _, r in reversed(items("videos")):
        if r.get("kind") == "movie" and r.get("status") in ("published", "scheduled") and r.get("video_id"):
            return r
    return None


def upload_from_store(rec, privacy, publish_at=None):
    rel = rec.get("release") or {}
    vid_asset = (rel.get("assets") or {}).get("video.mp4")
    if not vid_asset:
        raise RuntimeError("the stored video is missing")
    d = os.path.join(WORK, "upload-" + rec["id"])
    os.makedirs(d, exist_ok=True)
    try:
        path = store.fetch(vid_asset, os.path.join(d, "video.mp4"))
        vid = youtube.upload(path, rec["title"], rec["description"], rec.get("tags", []), privacy, publish_at)
        thumb = (rel.get("assets") or {}).get("thumbnail.jpg")
        if thumb:
            youtube.thumbnail(vid, store.fetch(thumb, os.path.join(d, "thumbnail.jpg")))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    rec["video_id"] = vid
    rec["uploaded"] = now().isoformat()
    rec["release"] = None
    put("videos", rec["id"], rec)  # saved at once: the upload must never be repeated
    store.forget(rel.get("id"))
    return vid


def to_youtube(rec, privacy, publish_at=None):
    """Upload the stored video - or, if an earlier run already uploaded it, just change its status."""
    vid = rec.get("video_id")
    if not vid:
        return upload_from_store(rec, privacy, publish_at)
    if publish_at:
        youtube.schedule(vid, publish_at)
    elif privacy == "public":
        youtube.publish(vid)
    else:
        youtube.keep_private(vid)
    return vid


def dispatch(workflow, inputs):
    tok, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not (tok and repo):
        return False
    r = requests.post(f"{store.API}/repos/{repo}/actions/workflows/{workflow}/dispatches", timeout=30,
                      headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"},
                      json={"ref": os.environ.get("GITHUB_REF_NAME", "main"), "inputs": inputs})
    if r.status_code != 204:
        log("could not start", workflow, r.status_code, r.text[:200])
    return r.status_code == 204


def remake(kind, topic):
    if kind == "movie":
        return dispatch("make-movie.yml", {"topic": topic or ""})
    return dispatch("make-shorts.yml", {"kind": kind, "topic": topic or ""})


def handle_tap(tap, p):
    """Returns False when the video's record isn't saved yet (the tap is kept and retried next run)."""
    action, _, rid = tap.get("data", "").partition(":")
    rec = get_item("videos", rid)
    if rec is None:
        return False
    mid, base = tap.get("message_id"), rec.get("caption", rec.get("title", ""))
    status = rec.get("status")

    def show(line, rows=None):
        rest = base.replace("Not on YouTube yet. Tap a button - I check every hour.", "").strip().split("\n")
        telegram.edit_caption(mid, fit([line, ""] + rest, 1024), rows)

    if status in ("published", "scheduled", "private", "discarded", "deleted", "uploaded") and action not in ("back",):
        telegram.answer(tap.get("id", ""), f"Already {status}")
        return True
    note = ""
    if action in ("pub", "sch", "prv") and not youtube_ready():
        telegram.answer(tap.get("id", ""), "YouTube isn't connected yet - upload it from the app, then tap ✅ I uploaded it")
        return True
    if action == "up":
        store.forget((rec.get("release") or {}).get("id"))
        rec.update(status="uploaded", release=None, uploaded=now().isoformat())
        note = "✅ Marked as uploaded. Remember: pin the comment and set the Related video in YouTube Studio."
    elif action == "pub":
        to_youtube(rec, "public")
        st = youtube.status([rec["video_id"]]).get(rec["video_id"], {})
        if st.get("privacyStatus") == "public":
            rec.update(status="published", published=now().isoformat())
            after_publish(rec, p)
            mv = latest_movie() if rec["kind"] != "movie" else None
            tip = (f"\nTip: in YouTube Studio set this Short's Related video to “{telegram.esc(mv['title'])}”."
                   if mv else "")
            note = f"✅ Published: {link(rec)}{tip}"
        else:
            rec["status"] = "private"
            note = (f"⚠️ Uploaded, but YouTube kept it {st.get('privacyStatus', 'private')}: {link(rec)} - "
                    f"check YouTube Studio (account settings or a claim may block publishing).")
    elif action == "sch":
        when = slot_time(rec["kind"], p)
        utc = when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        to_youtube(rec, "private", utc)
        rec.update(status="scheduled", publish_at=utc)
        note = f"⏰ Scheduled for {when.strftime('%a %d %b, %I:%M %p')} IST: {link(rec)}"
    elif action == "prv":
        to_youtube(rec, "private")
        rec["status"] = "private"
        note = f"🔒 Uploaded as private: {link(rec)} - publish it from YouTube Studio when you like."
    elif action == "del":
        show("Discard this video?", [[("🗑 Yes, discard", f"del!:{rid}"), ("↩️ No", f"back:{rid}")]])
        telegram.answer(tap.get("id", ""), "Sure?")
        return True
    elif action == "back":
        telegram.edit_caption(mid, base, buttons(rid, rec["kind"], p, phone=rec.get("video_id") is None and not youtube_ready())
                              if rec.get("status") == "waiting" else None)
        return True
    elif action == "del!":
        store.forget((rec.get("release") or {}).get("id"))
        rec.update(status="discarded", release=None)
        note = "🗑 Discarded. Nothing was uploaded."
    elif action == "re":
        store.forget((rec.get("release") or {}).get("id"))
        rec.update(status="discarded", release=None)
        started = remake(rec["kind"], rec.get("topic"))
        note = ("🔁 Discarded - making a new version of this topic now (about 10 minutes for a Short)." if started else
                "🔁 Discarded. Start a new one from GitHub → Actions → Run workflow.")
    else:
        return True
    put("videos", rid, rec)
    show(note)
    telegram.answer(tap.get("id", ""), note[:180])
    return True


def finish_scheduled(p):
    due = [(n, r) for n, r in items("videos") if r.get("status") == "scheduled" and r.get("publish_at", "9") <=
           dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") and r.get("video_id")]
    if not due:
        return
    st = youtube.status([r["video_id"] for _, r in due])
    for n, r in due:
        if st.get(r["video_id"], {}).get("privacyStatus") == "public":
            r.update(status="published", published=now().isoformat())
            after_publish(r, p)
            put("videos", n, r)
            tell(f"✅ Now live: <b>{telegram.esc(r['title'])}</b>\n{link(r)}")


def status_text(p):
    lines = []
    if not youtube_ready():
        lines.append("YouTube isn't connected yet (SETUP step 3), so I can't read your numbers.")
    else:
        try:
            lines += progress_lines(progress())
        except Exception as e:
            lines.append(f"(YouTube numbers unavailable: {telegram.esc(str(e)[:160])})")
    waiting = [r for _, r in items("videos") if r.get("status") == "waiting"]
    sched = [r for _, r in items("videos") if r.get("status") == "scheduled"]
    lines += ["", f"Waiting for you: {len(waiting)} · Scheduled: {len(sched)}",
              "Paused" if load("control.json", {}).get("paused") else "Daily videos: on"]
    return "\n".join(lines)


def handle_text(text, p):
    t = text.strip()
    if t.startswith("/"):
        cmd, _, arg = t.partition(" ")
        action, kind = cmd[1:].split("@")[0].lower(), "story"
        reply = ""
    else:
        try:
            j = strategist.intent(t)
        except Exception as e:
            log("intent failed:", e)
            j = {"action": "help"}
        action, arg, kind, reply = j.get("action", "chat"), j.get("topic", "") or "", j.get("kind", "story"), j.get("reply", "")
    arg = arg.strip()
    if action in ("start", "help"):
        tell(HELP)
    elif action in ("make", "loop", "movie"):
        k = {"make": "story", "loop": "loop", "movie": "movie"}[action]
        ok = remake(k, arg)
        tell(f"🛠 Making a {LABEL[k].lower()}{' about ' + telegram.esc(arg) if arg else ''} now. "
             f"Preview in about {'40' if k == 'movie' else '10'} minutes." if ok else
             "I couldn't start a run from here - open GitHub → Actions → Run workflow.")
    elif action == "idea":
        k = kind if kind in ("story", "loop", "movie") else "story"
        low = arg.lower()
        for pre in ("movie:", "movie ", "loop:", "loop ", "short:", "short "):
            if low.startswith(pre):
                k = {"movie": "movie", "loop": "loop", "short": "story"}[pre.strip(": ")]
                arg = arg[len(pre):].strip()
                break
        if not arg:
            tell("Send it like: /idea The lost city of Dwarka")
        else:
            put("inbox", f"{stamp()}-{slug(arg, 30)}", {"kind": k, "topic": arg, "added": now().isoformat()})
            tell(f"💡 Saved for the next {LABEL[k].lower()}: {telegram.esc(arg)}")
    elif action == "status":
        tell(status_text(p))
    elif action in ("trends", "scout"):
        scout_cmd()
    elif action == "next":
        out = []
        for k in ("story", "loop", "movie"):
            c = strategist.candidates(k, p)[:3]
            out.append(f"<b>{LABEL[k]}</b>: " + ("; ".join(telegram.esc(x["topic"]) for x in c) or "fresh ideas from trends"))
        tell("\n".join(out))
    elif action == "pending":
        w = [r for _, r in items("videos") if r.get("status") == "waiting"]
        tell("\n".join(f"• {LABEL[r['kind']]}: {telegram.esc(r['title'])}" for r in w) or "Nothing is waiting for you.")
    elif action in ("pause", "resume"):
        save("control.json", {"paused": action == "pause", "changed": now().isoformat()})
        tell("⏸ Paused. I won't make the daily videos until you send /resume." if action == "pause" else
             "▶️ Back on. Daily videos resume at the next run.")
    else:
        tell(telegram.esc(reply) if reply else HELP)


def approvals():
    p = plan()
    if not has_telegram():
        log("Telegram is not set up (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")
        return 1
    st = load("telegram.json", {"offset": 0, "deferred": []})
    keep = []
    for tap in st.get("deferred", []):
        try:
            if not handle_tap(tap, p) and tap.get("at", "") > (now() - dt.timedelta(days=2)).isoformat():
                keep.append(tap)
        except Exception as e:
            log("deferred tap failed:", e)
    st["deferred"] = keep
    try:
        ups = telegram.updates(int(st.get("offset", 0)) + 1)
    except Exception as e:
        log("could not read Telegram:", e)
        ups = []
    owner_ok, replied = None, set()
    for u in ups:
        st["offset"] = max(int(st.get("offset", 0)), u["update_id"])
        save("telegram.json", st)
        if not telegram.from_owner(u):
            log("ignored a message from another chat")
            c = telegram.private_chat(u)
            if c and c not in replied and len(replied) < 3:
                if owner_ok is None:
                    owner_ok = telegram.reachable()
                if not owner_ok:  # setup unfinished: tell the sender their chat id so the owner can save it
                    replied.add(c)
                    try:
                        telegram.call("sendMessage", chat_id=c, text="🔒 This bot only takes orders from its owner.\n\n"
                                      "If that's you: " + telegram.chat_id_note(c))
                    except Exception:
                        pass
            continue
        try:
            cq = u.get("callback_query")
            if cq:
                tap = {"data": cq.get("data", ""), "message_id": (cq.get("message") or {}).get("message_id"),
                       "id": cq.get("id", ""), "at": now().isoformat()}
                if not handle_tap(tap, p):
                    st["deferred"].append(tap)
            elif (u.get("message") or {}).get("text"):
                handle_text(u["message"]["text"], p)
        except Exception as e:
            traceback.print_exc()
            tell(f"⚠️ That didn't work: <code>{telegram.esc(str(e)[:500])}</code>")
    save("telegram.json", st)
    try:
        if youtube_ready():
            finish_scheduled(p)
    except Exception as e:
        log("scheduled check failed:", e)
    log(f"approvals: {len(ups)} updates handled")
    return 0


# ------------------------------------------------------------------ progress and weekly report

def progress():
    out = {"subscribers": None, "watch_hours_12m": None, "shorts_views_90d": None,
           "days_left": (GOAL_DATE - now().date()).days}
    ch = youtube.channel()
    out["subscribers"] = int((ch.get("statistics") or {}).get("subscriberCount", 0) or 0)
    end = now().date()
    try:
        rows = youtube.analytics((end - dt.timedelta(days=364)).isoformat(), end.isoformat(), "estimatedMinutesWatched",
                                 dimensions="creatorContentType")
        out["watch_hours_12m"] = round(sum(float(r.get("estimatedMinutesWatched") or 0) for r in rows
                                           if "short" not in str(r.get("creatorContentType", "")).lower()) / 60, 1)
        rows, key = None, "engagedViews"
        try:
            rows = youtube.analytics((end - dt.timedelta(days=89)).isoformat(), end.isoformat(), key,
                                     dimensions="creatorContentType")
        except RuntimeError:
            key = "views"
            rows = youtube.analytics((end - dt.timedelta(days=89)).isoformat(), end.isoformat(), key,
                                     dimensions="creatorContentType")
        out["shorts_views_90d"] = int(sum(float(r.get(key) or 0) for r in rows
                                          if "short" in str(r.get("creatorContentType", "")).lower()))
    except Exception as e:
        out["note"] = "watch hours need the YouTube Analytics permission (see SETUP step 4)"
        log("analytics unavailable:", e)
    return out


def bar(v, goal):
    if v is None:
        return "n/a"
    f = min(v / goal, 1.0)
    k = int(round(f * 10))
    return "▰" * k + "▱" * (10 - k) + f" {f * 100:.0f}%"


def progress_lines(g):
    fmt = lambda v: "n/a" if v is None else (f"{v / 1e6:.2f}M" if v >= 1e6 else f"{v:,.0f}")
    lines = [f"⏳ <b>{g['days_left']} days</b> left to qualify under today's rules (before 1 Feb 2027)",
             f"Subscribers: {fmt(g['subscribers'])} / 1,000  {bar(g['subscribers'], GOALS['subscribers'])}",
             f"Watch hours, 12 mo (long videos): {fmt(g['watch_hours_12m'])} / 4,000  {bar(g['watch_hours_12m'], GOALS['watch_hours_12m'])}",
             f"Shorts views, 90 days: {fmt(g['shorts_views_90d'])} / 10M  {bar(g['shorts_views_90d'], GOALS['shorts_views_90d'])}"]
    if g.get("note"):
        lines.append(f"({g['note']})")
    subs_ok = (g["subscribers"] or 0) >= 1000
    if subs_ok and ((g["watch_hours_12m"] or 0) >= 4000 or (g["shorts_views_90d"] or 0) >= 10_000_000):
        lines.append("🎉 <b>You qualify!</b> Apply now: YouTube Studio → Earn → Apply.")
    return lines


def report():
    p = plan()
    g = progress()
    since = (now() - dt.timedelta(days=28)).isoformat()
    recs = [r for _, r in items("videos") if r.get("video_id") and r.get("status") == "published" and r.get("made", "") >= since]
    rows = {r["video_id"]: {"title": r["title"], "kind": r["kind"], "series": r.get("series"), "format": r.get("format"),
                            "views": 0, "age_days": (now() - dt.datetime.fromisoformat(r["made"])).days} for r in recs}
    if rows:
        for v in youtube.video_stats(list(rows)):
            rows[v["id"]].update(views=int(v["statistics"].get("viewCount", 0)), likes=int(v["statistics"].get("likeCount", 0)),
                                 comments=int(v["statistics"].get("commentCount", 0)))
        try:
            end = now().date().isoformat()
            for a in youtube.analytics((now().date() - dt.timedelta(days=30)).isoformat(), end,
                                       "views,averageViewPercentage,subscribersGained", dimensions="video",
                                       filters="video==" + ",".join(list(rows)[:200])):
                if a.get("video") in rows:
                    rows[a["video"]].update(avg_viewed_pct=round(float(a.get("averageViewPercentage") or 0), 1),
                                            subs_gained=int(a.get("subscribersGained") or 0))
        except Exception as e:
            log("per-video analytics unavailable:", e)
    table = sorted(rows.values(), key=lambda r: -r["views"])
    review = {}
    try:
        review = strategist.weekly_review(table, g, [r["title"] for r in table])
    except Exception as e:
        log("weekly review failed:", e)
    week = [r for r in table if r["age_days"] <= 7]
    week_ago = (now().date() - dt.timedelta(days=7)).strftime("%Y%m%d")
    spend = sum(float(x.get("usd", 0)) for n, x in items("spend") if n[:10].replace("-", "") >= week_ago)
    lines = [f"📊 <b>History with Me - weekly report</b> ({now().strftime('%a %d %b')})", ""] + progress_lines(g) + [""]
    lines.append(f"Last 7 days: {sum(r['kind'] != 'movie' for r in week)} Shorts, {sum(r['kind'] == 'movie' for r in week)} movies published"
                 + (f" · AI video spend ≈ ${spend:.2f}" if spend else ""))
    for r in table[:3]:
        lines.append(f"🏆 {telegram.esc(r['title'][:70])} - {r['views']:,} views"
                     + (f", {r['avg_viewed_pct']}% watched" if r.get("avg_viewed_pct") else "")
                     + (" (outlier!)" if r.get("outlier") else ""))
    if review.get("summary"):
        lines += ["", f"<b>Strategist:</b> {telegram.esc(review['summary'])}"]
    for i, m in enumerate(review.get("moves", [])[:3], 1):
        lines.append(f"{i}. {telegram.esc(m)}")
    dd = review.get("double_down") or []
    if dd:
        lines += ["", "Queued follow-ups: " + "; ".join(telegram.esc(x.get("topic", "")) for x in dd[:3])]
    tell("\n".join(lines)[:4000])
    put("reports", today(), {"progress": g, "videos": table, "review": review})
    return 0


def scout_cmd():
    s = scout.trends("short", days=14, max_queries=4)
    l = scout.trends("long", days=30, max_queries=2)
    lines = ["🔭 <b>Trending history right now</b>", "", "<b>Shorts</b>"]
    lines += [f"• {telegram.esc(r['title'][:80])} - {r['views_per_day']:,}/day ({r['outlier']}x)" for r in s[:8]]
    lines += ["", "<b>Long videos</b>"]
    lines += [f"• {telegram.esc(r['title'][:80])} - {r['views_per_day']:,}/day" for r in l[:5]]
    tell("\n".join(lines))
    return 0


DEMO = {
    "title": "The First Airplane Flight Lasted 12 Seconds",
    "hook": "12 SECONDS",
    "topic": "Wright Flyer first flight 1903",
    "series": "Timeline Twists",
    "wiki": ["Wright Flyer"],
    "scenes": [
        {"narration": "The first airplane flight lasted just twelve seconds.", "visual": "ai", "archive_query": "Wright Flyer",
         "image_prompt": "close-up of the 1903 Wright Flyer's wooden propeller and canvas wing on a windswept sand dune, grey December sky"},
        {"narration": "December 1903. An icy wind sweeps the dunes near Kitty Hawk, North Carolina.", "visual": "ai",
         "archive_query": "Kill Devil Hills 1903",
         "image_prompt": "wide shot of desolate sand dunes at Kill Devil Hills, North Carolina in 1903, a wooden shed and a long wooden launch rail, cold wind"},
        {"narration": "Orville Wright lies flat on the wing as his brother Wilbur runs beside it.", "visual": "ai",
         "archive_query": "Wright brothers 1903",
         "image_prompt": "a man in a dark 1900s suit lying flat on the lower wing of the Wright Flyer biplane, a second man in a cap running beside the wingtip"},
        {"narration": "The Flyer lifts off and covers about 120 feet, less than a jumbo jet's wingspan.", "visual": "archive",
         "archive_query": "Wright Flyer first flight 1903",
         "image_prompt": "the Wright Flyer biplane lifting off its launch rail a few feet above the sand"},
        {"narration": "A lifesaver named John Daniels pressed the shutter and caught the moment.", "visual": "ai",
         "archive_query": "glass plate camera 1900",
         "image_prompt": "a man in a 1900s lifesaving station uniform behind a large wooden box camera on a tripod on a sand dune"},
        {"narration": "By the fourth flight that day, they stayed up fifty-nine seconds.", "visual": "ai",
         "archive_query": "Wright Flyer 1903 flight",
         "image_prompt": "the Wright Flyer biplane soaring low over the dunes, its long shadow on the sand, late afternoon light"},
        {"narration": "Sixty-six years later, a piece of that Flyer flew to the Moon.", "visual": "archive",
         "archive_query": "Apollo 11 Lunar Module Eagle",
         "image_prompt": "the Apollo 11 lunar module on the grey surface of the Moon, Earth in the black sky"},
    ],
}


def demo():
    """A real Short made only with the free services (script written in advance, so no keys are needed).
    It proves the free picture, voice and editing line on GitHub's servers."""
    import json
    p = plan()
    idea = {"id": "demo", "topic": DEMO["topic"], "series": DEMO["series"], "wiki": DEMO["wiki"], "format": "one-number"}
    facts = strategist.research(idea, "story")
    script = {"title": DEMO["title"], "hook_text": DEMO["hook"], "scenes": [dict(x) for x in DEMO["scenes"]]}
    spec = strategist.spec("story", script, idea, p, pictures="free", motion=0)
    spec["voice_engine"] = "free"
    rid = f"{stamp()}-demo"
    out = render.make(spec, os.path.join(WORK, rid))
    report = {"duration": out["duration"], "pictures": out["sources"], "voice": out.get("voice_engine"),
              "warnings": out["warnings"], "wikipedia": facts["sources"]}
    print("DEMO RESULT " + json.dumps(report), flush=True)
    if has_telegram():
        telegram.send_video(out["video"], f"🧪 <b>Demo Short</b> (free pictures + free voice): {telegram.esc(DEMO['title'])}")
    if os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPOSITORY"):
        rel = store.keep(rid, {"demo-short.mp4": out["video"]}, "Demo Short made with the free services only")
        print("DEMO STORED " + json.dumps(rel), flush=True)
    return 0


def check_telegram():
    """Bot token, chat id and a hello. A wrong chat id gets the right one sent to you in Telegram."""
    if not os.environ.get("TELEGRAM_BOT_TOKEN", "").strip():
        print("❌ Telegram: TELEGRAM_BOT_TOKEN is missing")
        return False
    try:
        me = telegram.call("getMe")
        bot = me.get("username", "") if isinstance(me, dict) else ""
        print(f"✅ Telegram bot token works (@{bot or '?'})")
    except Exception as e:
        print("❌ Telegram:", e, "| If it says Unauthorized, the TELEGRAM_BOT_TOKEN secret is not the bot's token: "
              "copy it again from @BotFather → /mybots → your bot → API Token.")
        return False
    problem = telegram.chat_problem()
    if not problem:
        try:
            telegram.send("✅ History with Me agent is connected. Send /help to see what I can do.")
            print("✅ Telegram message sent to your chat")
            return True
        except Exception as e:
            problem = (f"Telegram can't deliver to it ({str(e)[:120]}) - the number is wrong, or you haven't pressed "
                       "Start in the bot yet")
    print(f"❌ TELEGRAM_CHAT_ID: {problem}.")
    try:
        seen = []
        for u in telegram.updates(0):  # offset 0 reads without confirming, so no message is used up
            c = telegram.private_chat(u)
            if c and c not in seen:
                seen.append(c)
        for cid in seen[-3:]:
            telegram.call("sendMessage", chat_id=cid, text=telegram.chat_id_note(cid))
        if seen:
            print("ℹ️ I sent your chat id to you in Telegram (not shown here because these logs are public). "
                  "Save it as the secret TELEGRAM_CHAT_ID, then run Check setup again.")
        else:
            print(f"ℹ️ Open https://t.me/{bot or 'your_bot'} in Telegram, press Start (or send hi), then run Check "
                  "setup again - the bot will send you your chat id.")
    except Exception as e:
        print("ℹ️ Couldn't read the bot's messages:", str(e)[:150])
    return False


def check_free_video(probe=False):
    """The free AI video engine: reachable, and with whose allowance. probe=True makes one real clip (uses one of the
    day's free clips) and sends it to Telegram."""
    if not freevideo.wanted():
        print("ℹ️ Free AI video is switched off (FREE_VIDEO=off)")
        return True
    if not freevideo.available():
        print("ℹ️ Free AI video engine isn't installed here (gradio_client); the GitHub workflows install it")
        return True
    try:
        space = freevideo.connect()
    except Exception as e:
        print("❌ Free AI video:", str(e)[:200])
        return False
    acct = ("using your free Hugging Face account (about 3 clips a day)" if os.environ.get("HF_TOKEN", "").strip() else
            "no HF_TOKEN yet, so only Hugging Face's tiny anonymous allowance - add HF_TOKEN (SETUP step 2)")
    print(f"✅ Free AI video engine reachable ({space}), {acct}")
    if not probe:
        return True
    import tempfile
    out, t0 = os.path.join(tempfile.gettempdir(), "free-video-test.mp4"), time.time()
    try:
        freevideo.clip("POV: you stand on the deck of the Titanic at night, icy breath in the air, stars overhead, crew "
                       "lowering a lifeboat beside you, handheld camera. Natural ambient sound only, no dialogue, no music",
                       "9:16", 4, out)
    except Exception as e:
        print("❌ Free AI video test clip failed:", str(e)[:300])
        return False
    print(f"✅ Free AI video test clip made: {render.probe_duration(out):.1f}s, "
          f"{'with' if video.has_audio(out) else 'without'} sound, in {time.time() - t0:.0f}s")
    if has_telegram():
        try:
            telegram.send_video(out, "🧪 <b>Free AI video test</b> (LTX-2.3 on Hugging Face's free GPUs). This is the engine "
                                "for your free daily cinematic Shorts.", filename="free-video-test.mp4")
        except Exception as e:
            print("ℹ️ Couldn't send the test clip to Telegram:", str(e)[:150])
    return True


def check(video_test=False):
    ok = True
    print("Checking the History with Me agent...\n")
    try:
        m = gemini.models()
        print("✅ Gemini key works. Models:", m)
        try:
            print("   Brain test:", gemini.text_json('Reply with JSON {"ok": true}', temperature=0, max_tokens=2000))
        except Exception as e:
            ok = False
            why = gemini.quota_verdict(e) or ("often Google being overloaded for a while - the agent waits and retries "
                                              "during real runs")
            print(f"❌ Gemini brain test failed: {why}. Google says:", str(e)[:260].replace("\n", " "))
        paid = bool(os.environ.get("GEMINI_PAID_KEY", "").strip())
        try:  # one tiny paid picture (a few cents) tells us whether billing is on (on the paid key when there is one)
            import tempfile
            gemini.image("A small red apple on a wooden table, photo", "1:1", os.path.join(tempfile.gettempdir(), "probe.jpg"), 64, 64)
            print("✅ GEMINI_PAID_KEY has billing: AI video and AI pictures are on; the free key still writes the scripts"
                  if paid else "✅ Gemini billing is active on GEMINI_API_KEY: AI video and AI pictures are on")
            if video.month_cap() is not None:
                print(f"   AI budget: ${video.month_cap():.0f} a month, spread evenly over the month; "
                      f"spent this month: ${video.month_spent():.2f}")
        except Exception as e:
            ok = False
            why = gemini.quota_verdict(e)
            if paid:
                print("❌ GEMINI_PAID_KEY can't use paid models yet, so no AI video or AI pictures.",
                      f"Why: {why}." if why else "", "Google says:", str(e)[:200].replace("\n", " "),
                      "| Fix: aistudio.google.com/billing → set up billing for the paid key's project.")
            else:
                print("❌ No Gemini billing yet, so no AI video or Gemini pictures (free route only).",
                      f"Why: {why}." if why else "", "Google says:", str(e)[:200].replace("\n", " "),
                      "| Fix: SETUP step 2 - a second key with billing, saved as GEMINI_PAID_KEY.")
    except Exception as e:
        ok = False
        print("❌ Gemini:", e)
    try:
        ch = youtube.channel()
        print("✅ YouTube channel:", ch.get("snippet", {}).get("title"), "-",
              ch.get("statistics", {}).get("subscriberCount"), "subscribers")
        g = progress()
        print("   Progress:", g)
    except Exception as e:
        if youtube_ready():
            ok = False
            print("❌ YouTube:", e)
        else:
            print("ℹ️ YouTube not connected yet: finished videos come to Telegram and you upload them from the YouTube app."
                  " SETUP step 3 makes uploading automatic.")
    ok = check_telegram() and ok
    ok = check_free_video(video_test) and ok
    try:
        import piper  # noqa: F401
        print("✅ Free voice engine installed (used if Gemini can't speak)")
    except ImportError:
        print("ℹ️ Free voice engine not installed - only Gemini voices will be used")
    print("✅ GitHub storage available" if os.environ.get("GITHUB_TOKEN") else "ℹ️ GITHUB_TOKEN not set (fine outside GitHub)")
    print("\nAll good!" if ok else "\nFix the ❌ items above (see SETUP.md), then run Check setup again.")
    return 0 if ok else 1


NEEDS = {"make": ["GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
         "approvals": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
         "report": ["GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "YT_CLIENT_ID", "YT_CLIENT_SECRET",
                    "YT_REFRESH_TOKEN"]}


def setup_missing(cmd):
    """Scheduled runs before setup is finished stop politely instead of failing every hour."""
    need = NEEDS.get(cmd, [])
    if cmd == "make" and DRY:
        need = ["GEMINI_API_KEY"]
    gone = [n for n in need if not os.environ.get(n, "").strip()]
    if gone:
        print(f"::warning::Setup not finished - add these repository secrets: {', '.join(gone)} (see SETUP.md). "
              "Then run 'Check setup'.")
    return gone


def main(argv=None):
    ap = argparse.ArgumentParser(prog="agent", description="History with Me YouTube agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make")
    mk.add_argument("--kind", default="both", choices=["story", "loop", "both", "movie"])
    mk.add_argument("--topic", default="")
    mk.add_argument("--pictures", default="", choices=["", "auto", "gemini", "free", "archive"])
    mk.add_argument("--motion", type=int, default=None)
    for name in ("approvals", "report", "scout", "demo"):
        sub.add_parser(name)
    ck = sub.add_parser("check")
    ck.add_argument("--video", action="store_true", help="also make one free AI video test clip")
    a = ap.parse_args(argv)
    if setup_missing(a.cmd):
        return 0
    if a.cmd == "make":
        return make(a.kind, a.topic.strip() or None, a.pictures or None, a.motion)
    if a.cmd == "check":
        return check(video_test=a.video)
    return {"approvals": approvals, "report": report, "scout": scout_cmd, "demo": demo}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
