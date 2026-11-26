"""Free AI video: an open video model (LTX-2.3 by Lightricks) running on Hugging Face's free GPUs (ZeroGPU),
called through gradio_client like any other Hugging Face Space.

- No money involved. A free Hugging Face account (secret HF_TOKEN) gets a small daily GPU allowance, enough for about
  3 clips a day; without a token Hugging Face gives an even smaller anonymous allowance.
- Clips are up to 10 seconds, vertical 9:16 works, and they come with sound.
- Commercial use (a monetized channel) is allowed for creators under $10M a year (LTX-2 community license).
Every failure is reported so the caller can fall back to Google's video model or to pictures."""
import os
import random
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
            try:
                client = Client(space, token=_token(), verbose=False)
            except TypeError:  # older gradio_client
                client = Client(space, hf_token=_token(), verbose=False)
            _state["endpoint"], _state["params"] = _endpoint(client)
            _state["client"], _state["space"] = client, space
            return space
        except Exception as e:
            last = e
            log(f"free AI video: can't open {space}: {str(e)[:160]}")
    raise RuntimeError(f"free AI video unavailable: {str(last)[:200]}")


def _video_path(result):
    v = result[0] if isinstance(result, (list, tuple)) else result
    for _ in range(3):
        if isinstance(v, dict):
            v = v.get("video") or v.get("path") or v.get("value") or v.get("url")
    if not v or not os.path.exists(str(v)):
        raise RuntimeError(f"no video file came back ({str(result)[:160]})")
    return str(v)


def clip(prompt, aspect, seconds, out_path, first_frame=None):
    """One shot of up to FREE_VIDEO_MAX_SECONDS (default 8). first_frame: an image to start from."""
    if not available():
        raise RuntimeError("free AI video is not available: " + why_off())
    width, height = SIZES.get(aspect, SIZES["9:16"])
    secs = round(min(max(float(seconds), 2.0), max_seconds()), 1)
    text = (f"{prompt}. Photorealistic cinematic footage, {'vertical portrait framing' if aspect == '9:16' else 'wide framing'}"
            ". No on-screen text, captions, logos or watermarks.")
    with _lock:
        if _state["dead"]:
            raise RuntimeError("free AI video is used up for today: " + _state["dead"])
        connect()
        args = {"prompt": text, "duration": secs, "enhance_prompt": False, "seed": random.randint(1, 2 ** 31 - 1),
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
        shutil.copyfile(_video_path(result), out_path)
        _state["used"] += 1
        log(f"free AI video shot ready ({secs:.0f}s, {_state['space']}, {time.time() - t0:.0f}s)")
        return out_path
