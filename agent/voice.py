"""Narration voice. Gemini voices first; a free offline voice (Piper) when Gemini can't speak
(no free quota left, no billing, or no key). One video always uses one voice from start to end."""
import os
import wave

from . import gemini
from .util import http, log

PIPER_VOICE = os.environ.get("PIPER_VOICE", "en_US-ryan-high")
_piper = {}


def _piper_model():
    """Download the free Piper voice once (about 60-120 MB) from the official voice library."""
    name = PIPER_VOICE
    lang, speaker, quality = name.split("-", 2)
    root = os.environ.get("PIPER_BASE", "https://huggingface.co/rhasspy/piper-voices/resolve/main").rstrip("/")
    base = f"{root}/{lang.split('_')[0]}/{lang}/{speaker}/{quality}/{name}"
    d = os.path.join(os.path.expanduser("~"), ".cache", "piper")
    os.makedirs(d, exist_ok=True)
    for ext in (".onnx", ".onnx.json"):
        p = os.path.join(d, name + ext)
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            continue
        r = http("GET", base + ext + "?download=true", timeout=900, allow_redirects=True)
        if r is None or r.status_code != 200:
            raise RuntimeError(f"could not download the free voice {name} ({getattr(r, 'status_code', 'no answer')})")
        with open(p, "wb") as f:
            f.write(r.content)
    return os.path.join(d, name + ".onnx")


def _piper_class(name):
    try:
        return getattr(__import__("piper", fromlist=[name]), name)
    except (ImportError, AttributeError):
        return getattr(__import__("piper.voice", fromlist=[name]), name)  # raises ImportError if piper is missing


def piper(text, out_wav):
    if "v" not in _piper:
        _piper["v"] = _piper_class("PiperVoice").load(_piper_model())  # pip install piper-tts
        log("free voice ready:", PIPER_VOICE)
    v, pace = _piper["v"], float(os.environ.get("PIPER_PACE", "1.08"))
    with wave.open(out_wav, "wb") as wf:
        if hasattr(v, "synthesize_wav"):  # piper-tts 1.3+
            try:
                cfg = _piper_class("SynthesisConfig")(length_scale=pace)
            except (ImportError, AttributeError, TypeError):
                cfg = None
            if cfg is not None:
                v.synthesize_wav(text, wf, syn_config=cfg)
            else:
                v.synthesize_wav(text, wf)
        else:  # piper-tts 1.2
            v.synthesize(text, wf, length_scale=pace)


def _gemini(text, voice, out_wav):
    for attempt in range(2):
        gemini.tts(text, voice, out_wav)
        with wave.open(out_wav) as w:
            secs = w.getnframes() / float(w.getframerate() or 24000)
        if secs >= len(text) / 15.0 * 0.45 or attempt == 1:
            return
        log("voice clip came back too short, asking again")


def speak_all(texts, voice, outs, engine="auto"):
    """Speak every chunk with ONE engine so the voice never changes mid-video. Returns the engine used."""
    order = {"auto": ["gemini", "free"], "gemini": ["gemini", "free"], "free": ["free", "gemini"]}.get(engine, ["gemini", "free"])
    errors = []
    for eng in order:
        try:
            for t, p in zip(texts, outs):
                if eng == "gemini":
                    _gemini(t, voice, p)
                else:
                    piper(t, p)
            if errors:
                log("voice: used", eng, "after", "; ".join(errors))
            return eng
        except ImportError:
            errors.append("free voice engine is not installed (pip install piper-tts)")
        except Exception as e:  # quota, billing, network...
            errors.append(f"{eng} voice failed: {str(e)[:200]}")
        log(errors[-1])
    raise RuntimeError("No voice could be made. " + " | ".join(errors))
