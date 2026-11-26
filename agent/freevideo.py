"""Free AI video: an open video model (LTX-2.3 by Lightricks) running on Hugging Face's free GPUs (ZeroGPU),
called through gradio_client like any other Hugging Face Space.

- No money involved. A free Hugging Face account (secret HF_TOKEN) gets a small daily GPU allowance, enough for about
  3 clips a day; without a token Hugging Face gives an even smaller anonymous allowance.
- Clips are up to 10 seconds, vertical 9:16 works, and they come with sound.
- Commercial use (a monetized channel) is allowed for creators under $10M a year (LTX-2 community license).
Every failure is reported so the caller can fall back to Google's video model or to pictures."""
import os
import random
import re
import shutil
import threading
import time

from .util import log

SPACES = [s.strip() for s in os.environ.get("FREE_VIDEO_SPACE", "Lightricks/LTX-2-3").split(",") if s.strip()]
SIZES = {"9:16": (1024, 1536), "16:9": (1536, 1024), "1:1": (1024, 1024)}  # width, height (the Space's own presets)
_lock = threading.Lock()  # one clip at a time: the free GPU queue serves one job per account
_state = {"dead": None, "used": 0, "client": None, "space": None, "endpoint": None, "params": None}
QUOTA_WORDS = ("quota", "exceeded", "too many", "rate limit", "limit reached", "try again in", "pro subscription")


def wanted():
    return os.environ.get("FREE_VIDEO", "auto").strip().lower() not in ("off", "0", "no", "false")


def max_seconds():
    return float(os.environ.get("FREE_VIDEO_MAX_SECONDS", "8") or 8)


def available():
    """True while the free engine is switched on, installed and not used up in this run."""
    if not wanted() or _state["dead"]:
        return False
    try:
        import gradio_client  # noqa: F401
    except ImportError:
        return False
    return True


def used():
    return _state["used"]


def why_off():
    return _state["dead"] or ("switched off (FREE_VIDEO=off)" if not wanted() else "gradio_client is not installed")


_NOUNS = r"(?:text|captions?|subtitles?|logos?|watermarks?|letters|words|dialogue|music|talking|speech)"
_NEGATED = re.compile(rf",?\s*\b(?:no|without)\s+(?:[\w-]+\s+)?{_NOUNS}\b(?:\s*(?:,|or|and)\s*(?:no\s+)?(?:[\w-]+\s+)?{_NOUNS}\b)*",
                      re.I)


def positive(prompt):
    """Open video models tend to draw whatever a prompt names, even after "no" ("no text, no logos" gives fake logos
    and junk lettering), so the free engine only gets the positive description."""
    p = _NEGATED.sub("", prompt)
    p = re.sub(r"\bin the (?:picture|frame)\b\.?", "", p, flags=re.I)
    p = re.sub(r"\s+([.,;:])", r"\1", re.sub(r"\s{2,}", " ", p))
    p = re.sub(r"([.,;:])(?:\s*[.,;:])+", r"\1", p)
    return p.strip(" ,;")


def _token():
    return os.environ.get("HF_TOKEN", "").strip() or None


def _endpoint(client):
    """Find the Space's video endpoint by its parameters, so a renamed button or a new option doesn't break us."""
    try:
        info = client.view_api(print_info=False, return_format="dict") or {}
    except Exception:
        info = {}
    for name, ep in (info.get("named_endpoints") or {}).items():
        names = [p.get("parameter_name") or p.get("label") for p in ep.get("parameters", [])]
        if "prompt" in names and "duration" in names:
            return name, names
    return "/generate_video", None


def connect():
    """Open the Space (no GPU time is used for this). Returns the Space name."""
    if _state["client"]:
        return _state["space"]
    from gradio_client import Client
    last = None
    for space in SPACES:
        try:
            # download_files=False: we fetch the finished clip ourselves, with retries (a refused download would
            # otherwise throw away a clip that already used one of the day's free GPU runs)
            try:
                client = Client(space, token=_token(), verbose=False, download_files=False)
            except TypeError:  # older gradio_client
                client = Client(space, hf_token=_token(), verbose=False, download_files=False)
            _state["endpoint"], _state["params"] = _endpoint(client)
            _state["client"], _state["space"] = client, space
            return space
        except Exception as e:
            last = e
            log(f"free AI video: can't open {space}: {str(e)[:160]}")
    raise RuntimeError(f"free AI video unavailable: {str(last)[:200]}")


def _video_ref(result):
    """The output video in the Space's answer: a local path, a URL, or the Space's file info (path / url)."""
    todo = [result]
    while todo:
        v = todo.pop(0)
        if isinstance(v, (list, tuple)):
            todo.extend(v)
        elif isinstance(v, dict):
            if v.get("url") or (v.get("path") and not isinstance(v.get("path"), dict)):
                return v
            todo.extend(x for x in v.values() if isinstance(x, (dict, list, tuple, str)))
        elif isinstance(v, str) and (v.startswith("http") or v.lower().endswith((".mp4", ".webm", ".mov"))):
            return v
    raise RuntimeError(f"no video came back ({str(result)[:160]})")


def _fetch(ref, out_path):
    """Save the clip: copy a local file, or download it from the Space (a few tries; downloads are free)."""
    import requests
    client = _state["client"]
    if isinstance(ref, dict):
        url, path = ref.get("url"), ref.get("path")
    else:
        url, path = (ref, None) if str(ref).startswith("http") else (None, ref)
    if path and os.path.exists(str(path)):
        shutil.copyfile(str(path), out_path)
        return
    if not url and path:
        from gradio_client import utils as gu
        url = client.src_prefixed + "file=" + gu.encode_file_path(path)
    last = "no address"
    for wait in (0, 3, 8, 15, 30):
        time.sleep(wait)
        try:
            with requests.get(url, headers=dict(getattr(client, "headers", None) or {}),
                              cookies=dict(getattr(client, "cookies", None) or {}), stream=True, timeout=120) as r:
                if r.status_code == 200:
                    with open(out_path, "wb") as f:
                        for chunk in r.iter_content(1 << 16):
                            f.write(chunk)
                    if os.path.getsize(out_path) > 1000:
                        return
                last = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last = str(e)[:120]
    raise RuntimeError(f"the clip was made but couldn't be downloaded from the Space ({last})")


def clip(prompt, aspect, seconds, out_path, first_frame=None):
    """One shot of up to FREE_VIDEO_MAX_SECONDS (default 8). first_frame: an image to start from."""
    if not available():
        raise RuntimeError("free AI video is not available: " + why_off())
    width, height = SIZES.get(aspect, SIZES["9:16"])
    secs = round(min(max(float(seconds), 2.0), max_seconds()), 1)
    text = positive(prompt).rstrip(".") + ". Photorealistic cinematic film footage, natural light and real-world detail."
    with _lock:
        if _state["dead"]:
            raise RuntimeError("free AI video is used up for today: " + _state["dead"])
        connect()
        enhance = os.environ.get("FREE_VIDEO_ENHANCE", "1").lower() not in ("0", "off", "no", "false")
        args = {"prompt": text, "duration": secs, "enhance_prompt": enhance, "seed": random.randint(1, 2 ** 31 - 1),
                "randomize_seed": False, "height": height, "width": width}
        if first_frame:
            from gradio_client import handle_file
            args["input_image"] = handle_file(first_frame)
        elif not _state["params"] or "input_image" in _state["params"]:
            args["input_image"] = None
        if _state["params"]:
            args = {k: v for k, v in args.items() if k in _state["params"]}
        t0 = time.time()
        try:
            result = _state["client"].predict(api_name=_state["endpoint"], **args)
        except Exception as e:
            msg = str(e).replace("\n", " ")
            if any(w in msg.lower() for w in QUOTA_WORDS):
                _state["dead"] = "free daily GPU allowance used up (" + msg[:160] + ")"
            raise RuntimeError("free AI video failed: " + msg[:300])
        _fetch(_video_ref(result), out_path)
        _state["used"] += 1
        log(f"free AI video shot ready ({secs:.0f}s, {_state['space']}, {time.time() - t0:.0f}s)")
        return out_path
