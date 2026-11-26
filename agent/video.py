"""Real AI video shots with Google's video model (Gemini Omni Flash, Gemini API "interactions").
Paid only (about $0.10 per second at 720p). Every failure is reported so the caller can fall back to pictures."""
import base64
import json
import os
import subprocess
import threading
import time

from . import gemini
from .util import http, log, today

PRICE = {"360p": 0.034, "720p": 0.10, "1080p": 0.15, "4k": 0.30}  # USD per second (Gemini API list price)
MODELS = [m for m in os.environ.get("VIDEO_MODEL", "gemini-omni-1.1-flash,gemini-omni-flash").split(",") if m.strip()]
RES = os.environ.get("VIDEO_RESOLUTION", "720p")
_lock = threading.Lock()
_state = {"dead": None, "spent": 0.0, "budget": 0.0}

BUDGET_ENV = {"story": ("SHORT_VIDEO_BUDGET", "3"), "loop": ("LOOP_VIDEO_BUDGET", "1"), "movie": ("MOVIE_VIDEO_BUDGET", "3")}


def start(kind):
    """A fresh budget for one video: dollars of AI video it may use (0 = pictures only)."""
    env, default = BUDGET_ENV.get(kind, ("SHORT_VIDEO_BUDGET", "3"))
    with _lock:
        _state["spent"] = 0.0
        _state["budget"] = float(os.environ.get(env, default) or 0)
    return _state["budget"]


def price(seconds):
    return round(seconds * float(os.environ.get("VIDEO_PRICE_PER_SEC", PRICE.get(RES, 0.10))), 2)


def spent_today():
    from .util import items
    return sum(float(r.get("usd", 0)) for n, r in items("spend") if n.startswith(today()))


def budget_left():
    with _lock:
        return _state["budget"] - _state["spent"]


def available():
    return bool(os.environ.get("GEMINI_API_KEY")) and _state["dead"] is None and \
        os.environ.get("CINEMATIC", "auto").lower() not in ("off", "0", "no")


def _find_video(obj):
    """The response nests the video somewhere under steps/content; find the first video part."""
    if isinstance(obj, dict):
        if obj.get("type") == "video" and (obj.get("data") or obj.get("uri")):
            return obj
        for k in ("output_video", "steps", "content", "outputs", "output"):
            if k in obj:
                v = _find_video(obj[k])
                if v:
                    return v
        for v in obj.values():
            f = _find_video(v)
            if f:
                return f
    elif isinstance(obj, list):
        for v in obj:
            f = _find_video(v)
            if f:
                return f
    return None


def _download(uri, out):
    key = gemini.key()
    if "/files/" in uri and ":download" not in uri:
        for _ in range(60):
            j = http("GET", uri, headers={"x-goog-api-key": key}, timeout=60).json()
            if j.get("state") in ("ACTIVE", None):
                break
            if j.get("state") == "FAILED":
                raise RuntimeError("the video file failed on Google's side")
            time.sleep(5)
        uri = uri + ":download?alt=media"
    r = http("GET", uri, headers={"x-goog-api-key": key}, timeout=600, allow_redirects=True)
    if r.status_code != 200:
        raise RuntimeError(f"video download failed ({r.status_code})")
    with open(out, "wb") as f:
        f.write(r.content)


def clip(prompt, aspect, seconds, out_path, refs=None, first_frame=None):
    """One shot. refs: list of image paths for character/style consistency; first_frame: image to animate.
    Returns the raw clip path, or raises (gemini.Fatal when video can't be used at all this run)."""
    if not available():
        raise gemini.Fatal("AI video is off or unavailable")
    seconds = int(min(max(round(seconds), 3), 10))
    cost = price(seconds)
    with _lock:
        if _state["budget"] - _state["spent"] < cost - 1e-9:
            raise RuntimeError("this video's AI video budget is used up")
        _state["spent"] += cost  # reserve
    parts = []
    for i, p in enumerate((refs or [])[:7]):
        with open(p, "rb") as f:
            parts.append({"type": "image", "data": base64.b64encode(f.read()).decode(), "mime_type": "image/jpeg"})
    if first_frame:
        with open(first_frame, "rb") as f:
            parts.append({"type": "image", "data": base64.b64encode(f.read()).decode(), "mime_type": "image/jpeg"})
    text = (f"{prompt}\nDuration: about {seconds} seconds. Aspect ratio {aspect}. "
            "Photorealistic cinematic footage. No on-screen text, captions, logos or watermarks.")
    if refs:
        text = " ".join(f"<IMAGE_REF_{i}>" for i in range(len(refs[:7]))) + " are references for the same character. " + text
    body = {"input": parts + [{"type": "text", "text": text}] if parts else text,
            "response_format": {"type": "video", "aspect_ratio": aspect, "resolution": RES, "duration": f"{seconds}s"}}
    if first_frame:
        body["generation_config"] = {"video_config": {"task": "image_to_video"}}
    elif refs:
        body["generation_config"] = {"video_config": {"task": "reference_to_video"}}
    url = os.environ.get("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta").rstrip("/") + "/interactions"
    last = ""
    try:
        for model in MODELS:
            b = dict(body, model=model.strip())
            for attempt in range(2):
                r = http("POST", url, headers={"x-goog-api-key": gemini.key(), "Content-Type": "application/json"},
                         data=json.dumps(b), timeout=900, tries=3)
                if r is not None and r.status_code == 400 and "duration" in r.text.lower() and "duration" in b["response_format"]:
                    b = json.loads(json.dumps(b))
                    b["response_format"].pop("duration")  # some versions take the length from the prompt only
                    continue
                break
            if r is not None and r.status_code == 200:
                v = _find_video(r.json())
                if not v:
                    raise RuntimeError("the video model answered without a video (probably blocked by safety filters)")
                if v.get("data"):
                    with open(out_path, "wb") as f:
                        f.write(base64.b64decode(v["data"]))
                else:
                    _download(v["uri"], out_path)
                log(f"AI video shot ready ({seconds}s, {model}, ≈${cost})")
                return out_path
            last = f"{getattr(r, 'status_code', 'no answer')}: {getattr(r, 'text', '')[:300]}"
            if r is not None and r.status_code == 404:
                continue  # try the next model name
            break
    except Exception:
        with _lock:
            _state["spent"] -= cost
        raise
    with _lock:
        _state["spent"] -= cost
    low = last.lower()
    if any(w in low for w in ("billing", "free tier", "not available", "permission", "api key", "limit: 0", "quota")) \
            or last[:3] in ("401", "403", "404"):
        _state["dead"] = last
        raise gemini.Fatal("AI video unavailable: " + last)
    raise RuntimeError("AI video failed: " + last)


def spent():
    with _lock:
        return round(_state["spent"], 2)


def record_spend(rec_id, kind):
    """Save what this video spent on AI video (one small file per video; the weekly report adds them up)."""
    from .util import put
    usd = spent()
    if usd > 0:
        put("spend", f"{today()}-{rec_id}", {"usd": usd, "kind": kind, "resolution": RES})
    return usd


def has_audio(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0",
                        path], capture_output=True, text=True)
    return bool(p.stdout.strip())
