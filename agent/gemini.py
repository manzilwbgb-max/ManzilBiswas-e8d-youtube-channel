"""Gemini: the agent's brain (text), voice (TTS) and AI pictures (images)."""
import base64
import io
import json
import os
import random
import re
import threading
import time
import wave

import requests
from PIL import Image, ImageOps

from .util import log, parse_json

API = os.environ.get("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")


_use_paid = {}  # kind -> True once the free key's allowance ran out in this run
_paid_dead = []  # set when GEMINI_PAID_KEY turns out to have no billing


def paid_key():
    return "" if _paid_dead else os.environ.get("GEMINI_PAID_KEY", "").strip()


def key(kind="text"):
    """The key for one request. With GEMINI_PAID_KEY set, pictures and video always use it, while the brain and
    the voice use the free GEMINI_API_KEY until its daily allowance runs out, then the paid key for the rest of the run."""
    free = os.environ.get("GEMINI_API_KEY", "").strip()
    paid = paid_key()
    if paid and (kind in ("image", "video") or _use_paid.get(kind) or not free):
        return paid
    if not free:
        raise Fatal("GEMINI_API_KEY is missing. Add it under Settings > Secrets and variables > Actions.")
    return free


class Fatal(Exception):
    """An error that retrying cannot fix (bad key, no billing, refused request)."""


class Limiter:
    def __init__(self, rpm):
        self.gap, self.lock, self.next = 60.0 / max(rpm, 0.1), threading.Lock(), 0.0

    def wait(self):
        with self.lock:
            t = max(time.time(), self.next)
            self.next = t + self.gap
        if t > time.time():
            time.sleep(t - time.time())


TEXT_LIMIT = Limiter(float(os.environ.get("TEXT_RPM", "8")))
IMAGE_LIMIT = Limiter(float(os.environ.get("IMAGE_RPM", "8")))
TTS_LIMIT = Limiter(float(os.environ.get("TTS_RPM", "3")))
_models = {}
_ranked = {}
_all = {}
_banned = set()
_rounds = {}


def _version(n):
    m = re.search(r"(\d+(?:\.\d+)?)", n)
    return float(m.group(1)) if m else 0.0


def models():
    """Pick the text, picture and voice models this key can use (newest flash first)."""
    if _models:
        return _models
    names, token = {}, None
    while True:
        params = {"pageSize": 1000}
        if token:
            params["pageToken"] = token
        r = requests.get(f"{API}/models", params=params, headers={"x-goog-api-key": key()}, timeout=30)
        if r.status_code != 200:
            raise Fatal(f"Gemini key check failed ({r.status_code}): {r.text[:300]}")
        j = r.json()
        for m in j.get("models", []):
            names[m["name"].split("/", 1)[-1]] = m.get("supportedGenerationMethods", [])
        token = j.get("nextPageToken")
        if not token:
            break

    def text_score(n):
        meth = names[n]
        if "generateContent" not in meth or not n.startswith("gemini"):
            return None
        if any(x in n for x in ("image", "tts", "embedding", "live", "audio", "vision", "aqa", "robotics", "computer",
                                "omni", "veo")):
            return None  # video and media models are not writers
        return 50 + 10 * ("flash" in n) - 4 * ("lite" in n) - 6 * ("pro" in n) - 2 * ("preview" in n or "exp" in n) + _version(n)

    def image_score(n):
        meth = names[n]
        if "imagen" in n and "predict" in meth:
            s = 40
        elif n.startswith("gemini") and "image" in n and "generateContent" in meth:
            s = 50
        else:
            return None
        return s + 10 * ("flash" in n) + 4 * ("fast" in n) - 6 * ("pro" in n or "ultra" in n) - 2 * ("preview" in n) + _version(n)

    def tts_score(n):
        if "tts" not in n or "generateContent" not in names[n]:
            return None
        return 50 + 10 * ("flash" in n) - 6 * ("pro" in n) - 2 * ("preview" in n) + _version(n)

    def ranked(kind, env, score):
        order = sorted((n for n in names if score(n) is not None), key=score, reverse=True)
        want = os.environ.get(env, "").strip()
        if want and want in names:
            order = [want] + [n for n in order if n != want]
        _ranked[kind] = order[:6]
        _all[kind] = list(order[:6])
        return order[0] if order else None

    _models.update(text=ranked("text", "TEXT_MODEL", text_score), image=ranked("image", "IMAGE_MODEL", image_score),
                   tts=ranked("tts", "TTS_MODEL", tts_score))
    log("Gemini models:", _models)
    return _models


def _fallback(kind, failed, err, busy=False):
    """Move to the next best model. A refused model is dropped for good; when every model is only busy
    (high demand), wait a little and go round again (up to 3 rounds). Returns False when nothing is left."""
    if not busy:
        _banned.add(failed)
    order = [n for n in _ranked.get(kind, []) if n != failed]
    _ranked[kind] = order
    if order:
        log(f"Gemini {kind} model {failed} {'busy' if busy else 'refused'} ({str(err)[:120]}); switching to {order[0]}")
        _models[kind] = order[0]
        return True
    left = [n for n in _all.get(kind, []) if n not in _banned]
    if (busy or left) and left and _rounds.get(kind, 0) < 3:
        _rounds[kind] = _rounds.get(kind, 0) + 1
        wait = 45 * _rounds[kind]
        log(f"all Gemini {kind} models are busy right now; waiting {wait}s and trying again")
        time.sleep(wait)
        order = [n for n in _all.get(kind, []) if n not in _banned]
        _ranked[kind] = order
        if order:
            _models[kind] = order[0]
            return True
    return False


class Overloaded(RuntimeError):
    """The model keeps answering 'busy' (5xx): better to switch to the next model than to wait."""


def quota_summary(body_text):
    """Google's quota details in short form: which limit was hit, its size, and when to retry."""
    try:
        details = (json.loads(body_text).get("error") or {}).get("details") or []
    except Exception:
        return ""
    out = []
    for d in details:
        t = str(d.get("@type", ""))
        if t.endswith("QuotaFailure"):
            for v in d.get("violations") or []:
                model = str((v.get("quotaDimensions") or {}).get("model", ""))
                out.append(f"{v.get('quotaId') or v.get('quotaMetric') or 'quota'}={v.get('quotaValue', '?')}"
                           + (f" ({model})" if model else ""))
        elif t.endswith("RetryInfo") and d.get("retryDelay"):
            out.append(f"retry in {d['retryDelay']}")
    return "; ".join(out[:4])


def quota_verdict(err):
    """Plain words for a Gemini quota or billing refusal ('' when it isn't one)."""
    s = str(err)
    low = s.lower()
    if "freetier" in low or "free_tier" in low or "free tier" in low:
        if re.search(r"FreeTier=0\b", s):
            return "this key's project gets no free quota for that model, so billing is needed"
        if "PerDay" in s:
            return ("today's free allowance is used up (it refills at about 1:30 pm India time); "
                    "billing removes this limit")
        if "PerMinute" in s:
            return "too many free-tier requests this minute; it clears within a minute"
        return "a free-tier limit was hit; billing removes it"
    if any(w in low for w in ("prepay", "balance", "depleted")):
        return "the billing account has no prepaid balance left: add credit at aistudio.google.com/billing"
    if "billing" in low or "quota" in low:
        return "Google refused for quota or billing reasons (billing not active, or a limit was reached)"
    return ""


def post(model, method, body, limiter, timeout=180, tries=6, kind="text"):
    url = f"{API}/models/{model}:{method}"
    delay, err, busy = 5.0, "unknown error", 0
    for _ in range(tries):
        limiter.wait()
        k, paid = key(kind), paid_key()
        try:
            r = requests.post(url, json=body, headers={"x-goog-api-key": k}, timeout=timeout)
        except requests.RequestException as e:
            r, err = None, str(e)
            busy += 1
            if busy >= 2:
                raise Overloaded(err)
        if r is not None:
            if r.status_code == 200:
                return r.json()
            qs = quota_summary(r.text) if r.status_code == 429 else ""
            err = f"{r.status_code}: " + (f"[{qs}] " if qs else "") + r.text[:300]
            low = r.text.lower()
            free_tier = r.status_code == 429 and "freetier" in (low + qs.lower()).replace("_", "").replace(" ", "")
            if free_tier and paid and k != paid and kind in ("text", "tts"):
                _use_paid[kind] = True
                log(f"Gemini's free {kind} allowance is used up for today; the paid key takes over for this run")
                continue
            if free_tier and paid and k == paid:
                _paid_dead.append(True)
                _use_paid.clear()
                log("GEMINI_PAID_KEY has no billing yet (Google treats it as free tier), so it isn't used this run")
            if r.status_code in (400, 401, 403, 404):
                raise Fatal(err)
            if r.status_code == 429 and any(w in low for w in ("billing", "prepay", "credit", "free_tier", "free tier", "per day")):
                raise Fatal("Gemini quota or billing limit: " + err)
            if r.status_code >= 500:
                busy += 1
                if busy >= 2:
                    raise Overloaded(err)
            ra = r.headers.get("Retry-After", "")
            if ra.isdigit():
                delay = max(delay, float(ra))
        time.sleep(delay + random.random() * 2)
        delay = min(delay * 2, 60)
    raise RuntimeError(err)


def text_json(prompt, temperature=0.8, max_tokens=32000):
    """Ask Gemini for one JSON value."""
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens,
                                 "responseMimeType": "application/json"}}
    last = None
    for attempt in range(3):
        while True:
            model = models()["text"]
            if not model:
                raise Fatal("No Gemini text model is available for this key")
            try:
                j = post(model, "generateContent", body, TEXT_LIMIT, timeout=150)
                break
            except Fatal as e:
                if "API key" in str(e) or not _fallback("text", model, e):
                    raise
            except Overloaded as e:
                if not _fallback("text", model, e, busy=True):
                    raise
        txt = "".join(p.get("text", "") for c in j.get("candidates", [])
                      for p in (c.get("content") or {}).get("parts", []) if not p.get("thought"))
        try:
            return parse_json(txt)
        except ValueError as e:
            last = e
            log("model reply was not JSON, asking again")
    raise RuntimeError(f"Gemini did not return JSON: {last}")


def _inline(resp, prefix):
    for c in resp.get("candidates", []) or []:
        for p in (c.get("content") or {}).get("parts", []) or []:
            d = p.get("inlineData") or p.get("inline_data")
            if d and str(d.get("mimeType", d.get("mime_type", ""))).startswith(prefix):
                return d
    return None


def image(prompt, aspect, out_path, w, h):
    model = models()["image"]
    if not model:
        raise Fatal("No Gemini picture model is available for this key")
    if "imagen" in model:
        j = post(model, "predict", {"instances": [{"prompt": prompt}],
                                     "parameters": {"sampleCount": 1, "aspectRatio": aspect}}, IMAGE_LIMIT, kind="image")
        preds = j.get("predictions") or []
        data = preds[0].get("bytesBase64Encoded") if preds else None
    else:
        data = None
        for gc in ({"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}},
                   {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": {"aspectRatio": aspect}},
                   {"responseModalities": ["TEXT", "IMAGE"]}):
            try:
                j = post(model, "generateContent", {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                                                    "generationConfig": gc}, IMAGE_LIMIT, kind="image")
            except Fatal as e:
                if str(e).startswith("400") and "billing" not in str(e).lower():
                    continue
                raise
            except Overloaded as e:
                if not _fallback("image", model, e, busy=True):
                    raise
                return image(prompt, aspect, out_path, w, h)
            part = _inline(j, "image/")
            data = part["data"] if part else None
            break
    if not data:
        raise RuntimeError("no picture returned (probably blocked)")
    img = Image.open(io.BytesIO(base64.b64decode(data))).convert("RGB")
    ImageOps.fit(img, (w, h), Image.LANCZOS, centering=(0.5, 0.45)).save(out_path, "JPEG", quality=92)


def tts(text, voice, out_wav):
    model = models()["tts"]
    if not model:
        raise Fatal("No Gemini voice model is available for this key")
    style = os.environ.get("TTS_STYLE", "").strip()
    spoken = f"{style}: {text}" if style else text
    j = None
    while j is None:
        for v in (voice, "Charon"):
            body = {"contents": [{"parts": [{"text": spoken}]}],
                    "generationConfig": {"responseModalities": ["AUDIO"],
                                         "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": v}}}}}
            try:
                j = post(model, "generateContent", body, TTS_LIMIT, timeout=300, kind="tts")
                break
            except Fatal as e:
                if v != "Charon" and str(e).startswith("400"):
                    continue
                if not _fallback("tts", model, e):
                    raise
                model = _models["tts"]
                break
            except Overloaded as e:
                if not _fallback("tts", model, e, busy=True):
                    raise
                model = _models["tts"]
                break
    part = _inline(j or {}, "audio/")
    if not part:
        raise RuntimeError("no voice returned: " + json.dumps(j)[:300])
    raw = base64.b64decode(part["data"])
    mime = part.get("mimeType", part.get("mime_type", ""))
    if "wav" in mime:
        with open(out_wav, "wb") as f:
            f.write(raw)
        return
    m = re.search(r"rate=(\d+)", mime)
    with wave.open(out_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(m.group(1)) if m else 24000)
        wf.writeframes(raw)
