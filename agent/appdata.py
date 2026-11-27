"""What the private History with Me Studio app shows: one small JSON file (state/app.json) that the app reads through
your own GitHub connection. Rebuilt at the end of every run, so it is never more than about an hour old.

Commands go the other way: the app writes a small file into commands/, and the commands workflow (which only runs for
the repository owner's own pushes) carries them out - see main.commands()."""
import datetime as dt
import os

from . import freevideo, strategist, video
from .util import items, load, log, now, save, today

DEADLINE = "2027-02-01"
# YouTube Partner Program entry rules (blog.youtube, Aug 2026). Fan funding = memberships, Super Thanks, Shopping.
RULES = {
    "before": {"label": "Until 31 Jan 2027", "subs": 1000, "watch_hours_12m": 4000, "shorts_views_90d": 10_000_000},
    "after": {"label": "From 1 Feb 2027", "subs": 1000, "watch_hours_12m": 8000, "shorts_views_90d": 20_000_000},
    "fan_funding": {"label": "Fan funding (unchanged)", "subs": 500, "uploads_90d": 3, "watch_hours_12m": 3000,
                    "shorts_views_90d": 3_000_000},
}
ENGINES = {"video": "Google AI video", "free_video": "free AI video", "gemini": "AI pictures", "free_ai": "free AI pictures",
           "archive": "archive photos"}


def _engine(sources):
    """The main look of a finished video, from its shot counts."""
    if not sources:
        return ""
    top = max(sources, key=lambda k: sources[k])
    return ENGINES.get(top, top)


def _row(rid, r):
    return {"id": rid, "kind": r.get("kind"), "title": r.get("title", ""), "topic": r.get("topic", ""),
            "series": r.get("series"), "format": r.get("format"), "status": r.get("status"), "made": r.get("made"),
            "seconds": round(float(r.get("duration") or 0)), "usd": round(float(r.get("video_usd") or 0), 2),
            "engine": _engine(r.get("pictures") or {}), "video_id": r.get("video_id"), "published": r.get("published"),
            "why": (r.get("why") or "")[:200], "warnings": [w[:160] for w in (r.get("warnings") or [])[:3]]}


def _ideas(p):
    out = {}
    for k, n in (("story", 6), ("loop", 4), ("movie", 3)):
        try:
            out[k] = [{"topic": c.get("topic", ""), "series": c.get("series", ""), "source": c.get("source", ""),
                       "date": c.get("date", "")} for c in strategist.candidates(k, p)[:n]]
        except Exception as e:
            log("app: idea list unavailable:", e)
            out[k] = []
    return out


def _known(name, prev):
    """True/False when this run can see the setting; the last known value when its workflow doesn't pass it."""
    if name in os.environ:
        return bool(os.environ[name].strip())
    return prev


def snapshot(p=None):
    """Rebuild state/app.json. Never raises: the app is a window, not part of making videos."""
    try:
        p = p or strategist.plan()
        prev = load("app.json", {})
        pa = prev.get("agent", {})
        vids = sorted(items("videos"), key=lambda nr: nr[1].get("made", ""), reverse=True)
        waiting = [dict(_row(n, r), description=(r.get("description") or "")[:5000], tags=(r.get("tags") or [])[:30],
                        pinned_comment=(r.get("pinned_comment") or "")[:500],
                        public=(r.get("public") or {}).get("video", ""),
                        release=(r.get("release") or {}).get("id"),
                        assets={k: v for k, v in ((r.get("release") or {}).get("assets") or {}).items()
                                if k in ("video.mp4", "thumbnail.jpg")})
                   for n, r in vids if r.get("status") == "waiting"]
        recent = [_row(n, r) for n, r in vids if r.get("status") != "waiting"][:20]
        reports = items("reports")
        review = (reports[-1][1].get("review") if reports else None) or {}
        trends = load("trends.json", {})
        data = {
            "updated": now().isoformat(),
            "deadline": DEADLINE,
            "rules": RULES,
            "agent": {
                "paused": bool(load("control.json", {}).get("paused")),
                "youtube_connected": _known("YT_REFRESH_TOKEN", pa.get("youtube_connected")),
                "paid_key": _known("GEMINI_PAID_KEY", pa.get("paid_key")),
                "free_video": _known("HF_TOKEN", pa.get("free_video")) if freevideo.wanted() else False,
                "schedule": {"shorts": "Every day 14:11 IST", "movies": "Wed & Sun 15:53 IST",
                             "approvals": "Every hour", "report": "Monday 16:47 IST"},
            },
            "budget": {"month": today()[:7], "spent": video.month_spent(), "cap": video.month_cap(),
                       "google_video_down": video.known_dead()},
            "runs": load("runs.json", {}),
            "videos": {"waiting": waiting, "recent": recent},
            "ideas": _ideas(p),
            "trends": {"at": trends.get("at"), "items": (trends.get("items") or [])[:12]},
            "insights": load("insights.json", {}),
            "review": {"date": reports[-1][0] if reports else None, "summary": review.get("summary", ""),
                       "moves": (review.get("moves") or [])[:5],
                       "double_down": [x.get("topic", "") for x in (review.get("double_down") or [])[:5]]},
            "series": [{"name": s["name"], "about": s.get("about", "")} for s in p.get("series", [])],
        }
        save("app.json", data)
        return data
    except Exception as e:
        log("app snapshot failed:", e)
        return None


def record_run(kind, ok, title="", rid="", error=""):
    runs = load("runs.json", {})
    runs[kind] = {"at": now().isoformat(), "ok": bool(ok), "title": title[:140], "id": rid, "error": error[:300]}
    save("runs.json", runs)


def save_trends(rows):
    if rows:
        save("trends.json", {"at": now().isoformat(), "items": [
            {"title": r.get("title", "")[:140], "channel": r.get("channel", ""), "views_per_day": r.get("views_per_day"),
             "outlier": r.get("outlier"), "url": r.get("url", "")} for r in rows[:15]]})


def clean_insights(c):
    """Analytics the app read from your YouTube (via Windsor.ai / vidIQ): kept small and plain."""
    def num(x):
        try:
            return round(float(x), 2)
        except (TypeError, ValueError):
            return None
    tot = c.get("totals") or {}
    top = []
    for v in (c.get("top") or [])[:15]:
        if isinstance(v, dict) and v.get("title"):
            top.append({"title": str(v["title"])[:140], "kind": str(v.get("kind", ""))[:20], "views": num(v.get("views")),
                        "engaged_views": num(v.get("engaged_views")), "avg_pct": num(v.get("avg_pct")),
                        "subs": num(v.get("subs")), "minutes": num(v.get("minutes"))})
    return {"at": now().isoformat(), "period": str(c.get("period", "last 30 days"))[:40],
            "subscribers": num(c.get("subscribers")),
            "totals": {k: num(tot.get(k)) for k in ("views", "engaged_views", "minutes", "subs_gained", "subs_lost",
                                                    "longform_minutes", "shorts_engaged_views")},
            "top": top}


def insight_lines(n=8):
    ins = load("insights.json", {})
    top = ins.get("top") or []
    if not top:
        return ""
    fresh = ins.get("at", "")[:10]
    rows = [f"- {v['title']} | {int(v.get('views') or 0):,} views | {v.get('avg_pct') or '?'}% watched | "
            f"+{int(v.get('subs') or 0)} subs" for v in top[:n]]
    return f"(YouTube analytics, {ins.get('period', 'last 30 days')}, read {fresh})\n" + "\n".join(rows)


def days_left():
    return (dt.date.fromisoformat(DEADLINE) - now().date()).days
