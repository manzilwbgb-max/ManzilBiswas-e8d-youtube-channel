"""YouTube Data API: upload as private, thumbnail, make public, comments, stats, search."""
import json
import os
import time

import requests

from .util import http, log

API = os.environ.get("YT_API_BASE", "https://www.googleapis.com/youtube/v3")
UP = os.environ.get("YT_UPLOAD_BASE", "https://www.googleapis.com/upload/youtube/v3")
ANALYTICS = os.environ.get("YT_ANALYTICS_BASE", "https://youtubeanalytics.googleapis.com/v2")
TOKEN_URL = os.environ.get("YT_TOKEN_URL", "https://oauth2.googleapis.com/token")
_tok = {"v": None, "exp": 0.0}


def token():
    if _tok["v"] and time.time() < _tok["exp"] - 120:
        return _tok["v"]
    need = [k for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") if not os.environ.get(k)]
    if need:
        raise RuntimeError("Missing YouTube secrets: " + ", ".join(need))
    r = requests.post(TOKEN_URL, data={
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError("YouTube sign-in failed (check the three YT_ secrets): " + r.text[:300])
    j = r.json()
    _tok.update(v=j["access_token"], exp=time.time() + int(j.get("expires_in", 3600)))
    return _tok["v"]


def _h(extra=None):
    h = {"Authorization": "Bearer " + token()}
    h.update(extra or {})
    return h


def get(path, **params):
    r = http("GET", f"{API}/{path}", headers=_h(), params=params)
    if r.status_code != 200:
        raise RuntimeError(f"YouTube {path} failed: {r.text[:300]}")
    return r.json()


STATUS = {"selfDeclaredMadeForKids": False, "containsSyntheticMedia": True, "embeddable": True,
          "license": "youtube", "publicStatsViewable": True}


def upload(path, title, description, tags, privacy="private", publish_at=None, category="27"):
    """Resumable upload. privacy: public, private or unlisted; publish_at (UTC ISO) schedules a private video.
    Returns the video id."""
    st = dict(STATUS, privacyStatus="private" if publish_at else privacy)
    if publish_at:
        st["publishAt"] = publish_at
    meta = {"snippet": {"title": title[:100], "description": description[:4900], "tags": [t[:60] for t in tags][:25],
                        "categoryId": category, "defaultLanguage": "en", "defaultAudioLanguage": "en"},
            "status": st}
    size = os.path.getsize(path)
    r = requests.post(f"{UP}/videos?uploadType=resumable&part=snippet,status", data=json.dumps(meta), timeout=60,
                      headers=_h({"Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": "video/mp4",
                                  "X-Upload-Content-Length": str(size)}))
    if r.status_code != 200:
        raise RuntimeError("YouTube refused the upload: " + r.text[:400])
    url, offset = r.headers["Location"], 0
    for attempt in range(5):
        try:
            with open(path, "rb") as f:
                f.seek(offset)
                hdr = {"Content-Type": "video/mp4", "Content-Length": str(size - offset)}
                if offset:
                    hdr["Content-Range"] = f"bytes {offset}-{size - 1}/{size}"
                r = requests.put(url, headers=_h(hdr), data=f, timeout=(30, 3600))
            if r.status_code in (200, 201):
                return r.json()["id"]
            if r.status_code in (400, 401, 403):
                raise RuntimeError("YouTube refused the upload: " + r.text[:400])
        except requests.RequestException as e:
            log("upload interrupted:", e)
        q = requests.put(url, headers=_h({"Content-Range": f"bytes */{size}", "Content-Length": "0"}), timeout=60)
        if q.status_code in (200, 201):
            return q.json()["id"]
        if q.status_code == 308:
            rng = q.headers.get("Range")
            offset = int(rng.split("-")[-1]) + 1 if rng else 0
        time.sleep(5 * (attempt + 1))
    raise RuntimeError("YouTube upload did not finish")


def thumbnail(video_id, jpg):
    with open(jpg, "rb") as f:
        r = requests.post(f"{UP}/thumbnails/set", params={"videoId": video_id}, data=f, timeout=120,
                          headers=_h({"Content-Type": "image/jpeg"}))
    if r.status_code != 200:
        log("thumbnail not set (the channel may need phone verification):", r.text[:200])
        return False
    return True


def publish(video_id):
    r = requests.put(f"{API}/videos", params={"part": "status"}, timeout=60, headers=_h({"Content-Type": "application/json"}),
                     data=json.dumps({"id": video_id, "status": dict(STATUS, privacyStatus="public")}))
    if r.status_code != 200:
        raise RuntimeError("YouTube did not make it public: " + r.text[:300])
    return r.json().get("status", {}).get("privacyStatus")


def comment(video_id, text):
    r = requests.post(f"{API}/commentThreads", params={"part": "snippet"}, timeout=60,
                      headers=_h({"Content-Type": "application/json"}),
                      data=json.dumps({"snippet": {"videoId": video_id, "topLevelComment": {"snippet": {"textOriginal": text}}}}))
    if r.status_code != 200:
        log("comment not posted:", r.text[:200])
        return False
    return True


def playlist_add(playlist_id, video_id):
    if not playlist_id:
        return
    r = requests.post(f"{API}/playlistItems", params={"part": "snippet"}, timeout=60,
                      headers=_h({"Content-Type": "application/json"}),
                      data=json.dumps({"snippet": {"playlistId": playlist_id,
                                                   "resourceId": {"kind": "youtube#video", "videoId": video_id}}}))
    if r.status_code != 200:
        log("playlist add failed:", r.text[:200])
        return False
    return True


def channel():
    items = get("channels", part="statistics,snippet", mine="true").get("items", [])
    return items[0] if items else {}


def video_stats(ids):
    out = []
    for k in range(0, len(ids), 50):
        out += get("videos", part="statistics,snippet,contentDetails", id=",".join(ids[k:k + 50])).get("items", [])
    return out


def schedule(video_id, when_utc):
    """Keep private now, YouTube makes it public at when_utc (ISO 8601, e.g. 2026-12-01T13:30:00Z)."""
    r = requests.put(f"{API}/videos", params={"part": "status"}, timeout=60, headers=_h({"Content-Type": "application/json"}),
                     data=json.dumps({"id": video_id, "status": dict(STATUS, privacyStatus="private", publishAt=when_utc)}))
    if r.status_code != 200:
        raise RuntimeError("YouTube did not schedule it: " + r.text[:300])
    return r.json().get("status", {})


def keep_private(video_id):
    r = requests.put(f"{API}/videos", params={"part": "status"}, timeout=60, headers=_h({"Content-Type": "application/json"}),
                     data=json.dumps({"id": video_id, "status": dict(STATUS, privacyStatus="private")}))
    if r.status_code != 200:
        raise RuntimeError("YouTube did not update it: " + r.text[:300])


def delete(video_id):
    r = requests.delete(f"{API}/videos", params={"id": video_id}, headers=_h(), timeout=60)
    if r.status_code not in (200, 204):
        raise RuntimeError("YouTube did not delete it: " + r.text[:300])


def status(ids):
    """{video_id: status dict} for your own videos (privacyStatus, publishAt, uploadStatus...)."""
    out = {}
    for k in range(0, len(ids), 50):
        for it in get("videos", part="status", id=",".join(ids[k:k + 50])).get("items", []):
            out[it["id"]] = it.get("status", {})
    return out


def playlist_for(title, description=""):
    """Find your playlist by title, or create it (public). Returns its id."""
    token = None
    while True:
        params = {"part": "snippet", "mine": "true", "maxResults": 50}
        if token:
            params["pageToken"] = token
        j = get("playlists", **params)
        for p in j.get("items", []):
            if p["snippet"]["title"].strip().lower() == title.strip().lower():
                return p["id"]
        token = j.get("nextPageToken")
        if not token:
            break
    r = requests.post(f"{API}/playlists", params={"part": "snippet,status"}, timeout=60,
                      headers=_h({"Content-Type": "application/json"}),
                      data=json.dumps({"snippet": {"title": title[:150], "description": description[:4900],
                                                   "defaultLanguage": "en"}, "status": {"privacyStatus": "public"}}))
    if r.status_code != 200:
        raise RuntimeError("playlist not created: " + r.text[:200])
    return r.json()["id"]


def recent_uploads(n=25):
    ch = get("channels", part="contentDetails", mine="true").get("items", [])
    if not ch:
        return []
    up = ch[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    return get("playlistItems", part="snippet,contentDetails", playlistId=up, maxResults=min(n, 50)).get("items", [])


def analytics(start, end, metrics, dimensions=None, filters=None, sort=None, max_results=None):
    """YouTube Analytics (needs the yt-analytics.readonly permission). Returns rows as dicts."""
    params = {"ids": "channel==MINE", "startDate": start, "endDate": end, "metrics": metrics}
    for k, v in (("dimensions", dimensions), ("filters", filters), ("sort", sort), ("maxResults", max_results)):
        if v:
            params[k] = v
    r = http("GET", f"{ANALYTICS}/reports", headers=_h(), params=params)
    if r.status_code != 200:
        raise RuntimeError(f"YouTube Analytics failed: {r.text[:300]}")
    j = r.json()
    cols = [c["name"] for c in j.get("columnHeaders", [])]
    return [dict(zip(cols, row)) for row in j.get("rows", []) or []]
