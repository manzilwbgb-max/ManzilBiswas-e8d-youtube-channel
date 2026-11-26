"""Trend scout: which history videos are taking off on YouTube right now."""
import datetime as dt
import math
import re

from . import youtube as yt
from .util import log

SHORT_QS = ["history #shorts", "ancient history #shorts", "history facts #shorts", "history mystery #shorts",
            "roman empire #shorts", "medieval history #shorts", "ancient egypt #shorts", "world war history #shorts",
            "prehistoric animals #shorts", "indian history #shorts", "archaeology discovery #shorts", "dark history #shorts"]
LONG_QS = ["history documentary", "ancient history documentary", "fall of empire history", "lost civilization documentary",
           "history mystery explained", "medieval history documentary", "ancient egypt documentary",
           "prehistoric world documentary", "indian history documentary", "roman empire documentary"]


def _secs(iso):
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return sum(int(x or 0) * k for x, k in zip(m.groups(), (86400, 3600, 60, 1))) if m else 0


def trends(fmt="short", days=21, max_queries=4):
    qs = SHORT_QS if fmt == "short" else LONG_QS
    start = dt.date.today().toordinal() % len(qs)
    picked = [qs[(start + i) % len(qs)] for i in range(min(max_queries, len(qs)))]
    after = (dt.datetime.utcnow() - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    order, qof = [], {}
    for i, q in enumerate(picked):
        dur = "short" if fmt == "short" else ("long" if i % 2 == 0 else "medium")
        try:
            j = yt.get("search", part="snippet", type="video", q=q, order="viewCount", publishedAfter=after,
                       videoDuration=dur, relevanceLanguage="en", maxResults=25)
        except Exception as e:
            log("search failed:", q, e)
            continue
        for it in j.get("items", []):
            vid = (it.get("id") or {}).get("videoId")
            if vid and vid not in qof:
                qof[vid] = q
                order.append(vid)
    videos = yt.video_stats(order) if order else []
    subs, chans = {}, sorted({v["snippet"]["channelId"] for v in videos})
    for k in range(0, len(chans), 50):
        for c in yt.get("channels", part="statistics", id=",".join(chans[k:k + 50])).get("items", []):
            st = c.get("statistics", {})
            subs[c["id"]] = None if st.get("hiddenSubscriberCount") else int(st.get("subscriberCount", 0))
    now, rows = dt.datetime.now(dt.timezone.utc), []
    for v in videos:
        sn, st = v.get("snippet", {}), v.get("statistics", {})
        views = int(st.get("viewCount", 0) or 0)
        if not views:
            continue
        secs = _secs((v.get("contentDetails") or {}).get("duration"))
        if (fmt == "short" and secs > 180) or (fmt != "short" and secs < 480):
            continue
        title = sn.get("title", "")
        letters = [c for c in title if c.isalpha()]
        if letters and sum(c.isascii() for c in letters) / len(letters) < 0.7:
            continue
        age = max((now - dt.datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))).total_seconds() / 86400, 0.5)
        s = subs.get(sn.get("channelId"))
        per_day, outlier = views / age, views / max(s or 1000, 1000)
        likes, comments = int(st.get("likeCount", 0) or 0), int(st.get("commentCount", 0) or 0)
        eng = (likes + 3 * comments) / views
        score = 0.55 * math.log10(per_day + 1) + 0.35 * math.log10(outlier + 1) + min(eng * 5, 0.4)
        rows.append({"title": title, "channel": sn.get("channelTitle"), "subs": s, "views": views,
                     "views_per_day": round(per_day), "outlier": round(outlier, 1), "age_days": round(age),
                     "seconds": secs, "query": qof.get(v["id"], ""), "url": "https://youtu.be/" + v["id"],
                     "score": round(score, 2)})
    rows.sort(key=lambda r: -r["score"])
    log(f"scout: {len(rows)} {fmt} videos ranked")
    return rows[:25]
