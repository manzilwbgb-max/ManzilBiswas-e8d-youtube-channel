"""Render engine (from Rex Studio v2): pictures + voice -> narrated video with camera moves,
captions (Shorts), chapter cards and end card (movies), thumbnail and a small preview."""
import os
import re
import shutil
import subprocess
import threading
import wave
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from . import gemini, sources
from .voice import speak_all
from .util import log

FPS = 30
FONT_DIR = os.environ.get("FONT_DIR", "/usr/share/fonts/truetype/dejavu")
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FORMATS = {
    "short": {"w": 1080, "h": 1920, "aspect": "9:16", "captions": True, "end_card": 0.0, "crf": "20"},
    "movie": {"w": 1920, "h": 1080, "aspect": "16:9", "captions": False, "end_card": 12.0, "crf": "21"},
}
KB_PATTERNS = ["in", "lr", "out", "rl", "in_up", "out", "lr", "in"]
KB_PATTERNS_TALL = ["in", "bt", "out", "in_up", "tb", "in"]
NO_TEXT = "No text, no letters, no captions, no watermark, no logo, no border, no split screen."
SOFTEN = re.compile(r"\b(blood(y|ied)?|gore|gory|corpses?|dead bod(y|ies)|severed|behead\w*|decapitat\w*|massacr\w*|"
                    r"slaughter\w*|tortur\w*|execut\w*|mutilat\w*|wound\w*|bleed\w*|kill\w*|murder\w*|stab\w*|impal\w*)\b", re.I)


def run(cmd, timeout=5400, cwd=None):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + (p.stderr or p.stdout)[-800:])
    return p


def probe_duration(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
                       capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        return 0.0


def clean_text(s, limit):
    s = re.sub(r"[\u0000-\u0008\u000b-\u001f]", " ", str(s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def font(size):
    try:
        return ImageFont.truetype(FONT_BOLD, size)
    except OSError:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


# ---------------------------------------------------------------- timing

def silences(wav):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", wav, "-af",
                        "silencedetect=noise=-38dB:d=0.16", "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", p.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    return [(max(s, 0.0), e) for s, e in zip(starts, ends)]


def speech_span(total, sil):
    start, end = 0.0, total
    if sil and sil[0][0] <= 0.05:
        start = sil[0][1]
    if sil and sil[-1][1] >= total - 0.06:
        end = sil[-1][0]
    if end - start < 0.5:
        start, end = 0.0, total
    return start, end


def align(lengths, total, sil):
    """Times inside one voice clip where each piece of text ends (len(lengths)-1 values).

    Starts from where each piece should end if speech were even, then snaps to the
    nearest pause the voice actually made."""
    start, end = speech_span(total, sil)
    tot = float(sum(lengths)) or 1.0
    mids = [(s + e) / 2 for s, e in sil if s > start + 0.05 and e < end - 0.05]
    out, acc, prev = [], 0.0, start
    for L in lengths[:-1]:
        acc += L
        t = start + (end - start) * acc / tot
        cands = [m for m in mids if m > prev + 0.5 and abs(m - t) <= 1.6]
        b = min(cands, key=lambda m: abs(m - t)) if cands else t
        b = max(b, prev + 0.5)
        out.append(b)
        prev = b
    return out, start, end


def chunk_scenes(scenes, fmt):
    limit = 2400 if fmt == "short" else 1100
    chunks, cur, cur_len, cur_ch = [], [], 0, None
    for i, s in enumerate(scenes):
        ch = s.get("chapter") or ""
        n = len(s["narration"])
        if cur and (ch != cur_ch or cur_len + n > limit):
            chunks.append(cur)
            cur, cur_len = [], 0
        cur.append(i)
        cur_len += n
        cur_ch = ch
    if cur:
        chunks.append(cur)
    return chunks


# ---------------------------------------------------------------- pictures for overlays

def wrap_lines(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def chapter_card(number, title, w, h, out):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    band = Image.new("L", (w, h), 0)
    bd = ImageDraw.Draw(band)
    top = int(h * 0.64)
    for y in range(top, h):
        bd.line([(0, y), (w, y)], fill=int(190 * (y - top) / (h - top)))
    im.paste((0, 0, 0, 255), (0, 0), band)
    d = ImageDraw.Draw(im)
    x = int(w * 0.06)
    small, big = font(int(h * 0.04)), font(int(h * 0.075))
    lines = wrap_lines(d, title.upper(), big, int(w * 0.8))[:2]
    y = h - int(h * 0.09) - len(lines) * int(h * 0.085)
    d.text((x, y - int(h * 0.06)), f"CHAPTER {number}", font=small, fill=(255, 205, 40, 255),
           stroke_width=2, stroke_fill=(0, 0, 0, 255))
    for ln in lines:
        d.text((x, y), ln, font=big, fill=(255, 255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0, 255))
        y += int(h * 0.085)
    im.save(out)


def end_card(base_img, lines, w, h, out):
    im = Image.open(base_img).convert("RGB").resize((w, h)).filter(ImageFilter.GaussianBlur(18))
    im = Image.blend(im, Image.new("RGB", (w, h), (0, 0, 0)), 0.6)
    d = ImageDraw.Draw(im)
    sizes = [int(h * 0.075), int(h * 0.05), int(h * 0.042)]
    colors = [(255, 255, 255), (255, 205, 40), (230, 230, 230)]
    y = int(h * 0.16)
    for i, text in enumerate([t for t in lines if t][:3]):
        f = font(sizes[min(i, 2)])
        for ln in wrap_lines(d, text, f, int(w * 0.84))[:2]:
            tw = d.textlength(ln, font=f)
            d.text(((w - tw) / 2, y), ln, font=f, fill=colors[min(i, 2)], stroke_width=3, stroke_fill=(0, 0, 0))
            y += int(sizes[min(i, 2)] * 1.3)
        y += int(h * 0.02)
    im.save(out, "JPEG", quality=92)


def compose_thumbnail(base_img, text, out):
    im = ImageOps.fit(Image.open(base_img).convert("RGB"), (1280, 720), Image.LANCZOS)
    shade = Image.new("L", (1280, 720), 0)
    sd = ImageDraw.Draw(shade)
    for x in range(1280):
        sd.line([(x, 0), (x, 720)], fill=max(0, int(185 - x * 0.24)))
    im = Image.composite(Image.new("RGB", (1280, 720), (0, 0, 0)), im, shade)
    text = clean_text(text, 40).upper()
    if text:
        d = ImageDraw.Draw(im)
        words = text.split()
        if len(words) == 1:
            lines = words
        else:
            best = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(" ".join(words[k:]))))
            lines = [" ".join(words[:best]), " ".join(words[best:])]
        size = 170
        while size > 60:
            f = font(size)
            if max(d.textlength(ln, font=f) for ln in lines) <= 720 and size * 1.1 * len(lines) <= 560:
                break
            size -= 6
        f = font(size)
        y = (720 - int(size * 1.1) * len(lines)) // 2
        for i, ln in enumerate(lines):
            d.text((60, y), ln, font=f, fill=(255, 214, 0) if i == len(lines) - 1 and len(lines) > 1 else (255, 255, 255),
                   stroke_width=max(6, size // 14), stroke_fill=(0, 0, 0))
            y += int(size * 1.1)
    q = 90
    while True:
        im.save(out, "JPEG", quality=q, optimize=True)
        if os.path.getsize(out) < 1_900_000 or q <= 60:
            break
        q -= 10


# ---------------------------------------------------------------- captions (Shorts)

def ass_time(t):
    t = max(t, 0)
    h, m = int(t // 3600), int(t % 3600 // 60)
    s = t - h * 3600 - m * 60
    return f"{h}:{m:02d}:{s:05.2f}"


def ass_escape(s):
    return s.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ")


def phrases(text):
    words, out, cur = text.split(), [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 3 or len(" ".join(cur)) >= 14 or re.search(r"[.,!?;:]$", w):
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def write_ass(path, w, h, hook, cues):
    big = int(h * 0.04)
    head = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {w}\nPlayResY: {h}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding\n"
        f"Style: Cap,DejaVu Sans,{big},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,2,2,80,80,{int(h * 0.29)},1\n"
        f"Style: Hook,DejaVu Sans,{int(big * 0.95)},&H0028CDFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,2,8,70,70,{int(h * 0.12)},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = []
    if hook:
        lines.append(f"Dialogue: 1,{ass_time(0)},{ass_time(2.6)},Hook,,0,0,0,,{{\\fad(120,250)}}{ass_escape(hook.upper())}")
    for t0, t1, txt in cues:
        lines.append(f"Dialogue: 0,{ass_time(t0)},{ass_time(t1)},Cap,,0,0,0,,{{\\fad(60,60)}}{ass_escape(txt.upper())}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(lines) + "\n")


# ---------------------------------------------------------------- video

def kb_filter(pattern, frames, w, h, zoom=0.12):
    d = max(frames - 1, 1)
    p = f"(on/{d})"
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    z_in, z_out, z_fix = f"1+{zoom}*{p}", f"1+{zoom}*(1-{p})", f"{1 + zoom}"
    table = {
        "in": (z_in, cx, cy),
        "out": (z_out, cx, cy),
        "lr": (z_fix, f"(iw-iw/zoom)*{p}", cy),
        "rl": (z_fix, f"(iw-iw/zoom)*(1-{p})", cy),
        "in_up": (z_in, cx, f"(ih/2-(ih/zoom/2))*(1-0.7*{p})"),
        "bt": (z_fix, cx, f"(ih-ih/zoom)*(1-{p})"),
        "tb": (z_fix, cx, f"(ih-ih/zoom)*{p}"),
    }
    z, x, y = table.get(pattern, table["in"])
    return (f"scale={w * 2}:{h * 2}:flags=bicubic,"
            f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={FPS},setsar=1,format=yuv420p")


def render_segment(img, out, frames, w, h, pattern, crf, overlay=None, overlay_dur=0.0):
    vf = kb_filter(pattern, frames, w, h)
    enc = ["-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
           "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", str(FPS * 2), "-an", out]
    if overlay:
        od = min(overlay_dur, frames / FPS)
        fc = (f"[0:v]{vf}[bg];[1:v]format=rgba,fade=t=in:st=0.2:d=0.5:alpha=1,"
              f"fade=t=out:st={max(od - 0.7, 0.8):.2f}:d=0.5:alpha=1[ov];"
              f"[bg][ov]overlay=0:0:eof_action=pass,format=yuv420p[v]")
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", img,
               "-loop", "1", "-t", f"{od:.2f}", "-i", overlay, "-filter_complex", fc, "-map", "[v]"] + enc
    else:
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", img, "-vf", vf] + enc
    run(cmd)


def silence_wav(path, seconds, rate=24000):
    n = int(seconds * rate)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x00" * n)


def wav_rate(path):
    with wave.open(path, "rb") as wf:
        return wf.getframerate()




# ---------------------------------------------------------------- pictures: paid AI -> free AI -> free archive

_free_lock = threading.Lock()
_free_next = [0.0]


def pollinations(prompt, out_path, w, h, seed):
    """Free AI picture (Flux via pollinations.ai). Crops a strip off the bottom in case a logo is stamped there."""
    import time
    import urllib.parse
    from .util import http
    base = os.environ.get("POLLINATIONS_BASE", "https://image.pollinations.ai").rstrip("/")
    th = int(h * 1.06)
    url = (f"{base}/prompt/" + urllib.parse.quote(prompt[:900]) +
           f"?width={w}&height={th}&seed={seed}&model=flux&nologo=true&safe=true")
    headers = {}
    if os.environ.get("POLLINATIONS_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["POLLINATIONS_TOKEN"]
    gap = float(os.environ.get("POLLINATIONS_GAP", "2" if headers else "8"))
    with _free_lock:  # the free service allows one request at a time
        wait = _free_next[0] - time.time()
        if wait > 0:
            time.sleep(wait)
        try:
            r = http("GET", url, headers=headers, timeout=180, tries=3)
        finally:
            _free_next[0] = time.time() + gap
    if r is None or r.status_code != 200 or not r.headers.get("content-type", "").startswith("image"):
        raise RuntimeError(f"free AI picture failed ({getattr(r, 'status_code', 'no answer')})")
    import io
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    ImageOps.fit(img, (w, h), Image.LANCZOS, centering=(0.5, 0.0)).save(out_path, "JPEG", quality=92)


class Pictures:
    """Tries the best picture source still working, and remembers when one runs out."""

    def __init__(self, mode, style, aspect, w, h, topic):
        self.mode = mode
        self.order = {"gemini": ["gemini", "free_ai", "archive"], "free": ["free_ai", "archive"],
                      "archive": ["archive", "free_ai"]}.get(mode, ["gemini", "free_ai", "archive"])
        self.style, self.aspect, self.w, self.h, self.topic = style, aspect, w, h, topic
        self.dead, self.used_urls, self.lock, self.used = set(), set(), threading.Lock(), {}
        self.cap, self.reserved = int(os.environ.get("AI_PICTURES_MAX", "0") or 0), 0  # paid pictures per video (0 = no cap)

    def _reserve(self):
        with self.lock:
            if self.cap and self.reserved >= self.cap:
                return False
            self.reserved += 1
            return True

    def make(self, i, scene, out_path, priority=False):
        prompt = f"{self.style}. {scene['image_prompt']}. {NO_TEXT}"
        order = list(self.order)
        if scene.get("visual") == "archive" and "archive" in order and self.mode != "archive":
            order.remove("archive")
            order.insert(0, "archive")  # a real photo or painting exists: authentic beats generated
        for src in order:
            if src in self.dead:
                continue
            if src == "gemini" and not priority and not self._reserve():
                continue  # paid-picture budget for this video is used up
            try:
                if src == "gemini":
                    try:
                        gemini.image(prompt, self.aspect, out_path, self.w, self.h)
                    except RuntimeError:
                        gemini.image(f"{self.style}. A tasteful, non-graphic scene: {SOFTEN.sub('', scene['image_prompt'])}. "
                                     f"{NO_TEXT}", self.aspect, out_path, self.w, self.h)
                elif src == "free_ai":
                    pollinations(f"{self.style}, {SOFTEN.sub('', scene['image_prompt'])}, cinematic film still, no text",
                                 out_path, self.w, self.h, seed=1000 + i * 7)
                else:
                    item = None
                    for q in [scene.get("archive_query"), self.topic]:
                        if q:
                            with self.lock:
                                avoid = set(self.used_urls)
                            item = sources.commons_picture(q, out_path, self.w, self.h, avoid)
                            if item:
                                with self.lock:
                                    self.used_urls.add(item["url"])
                                break
                    if not item:
                        raise RuntimeError("no public-domain picture found")
                with self.lock:
                    self.used[src] = self.used.get(src, 0) + 1
                return src
            except gemini.Fatal as e:
                log(f"picture source {src} switched off for this run: {str(e)[:160]}")
                self.dead.add(src)
                self._release(src, priority)
            except Exception as e:
                log(f"scene {i + 1}: {src} picture failed: {str(e)[:160]}")
                self._release(src, priority)
        return None

    def _release(self, src, priority):
        if src == "gemini" and not priority:
            with self.lock:
                self.reserved = max(self.reserved - 1, 0)


def veo_clip(prompt, aspect, seconds, out_path, w, h):
    """Real AI motion for one scene with Veo (needs Gemini API billing). Returns True when the clip is ready."""
    import time as _t
    import requests as _rq
    names = {}
    r = _rq.get(f"{gemini.API}/models", params={"pageSize": 1000}, headers={"x-goog-api-key": gemini.key()}, timeout=30)
    for m in r.json().get("models", []):
        names[m["name"].split("/", 1)[-1]] = m.get("supportedGenerationMethods", [])
    veo = sorted((n for n, meth in names.items() if "veo" in n and "predictLongRunning" in meth),
                 key=lambda n: (("fast" in n) * 10 + gemini._version(n)), reverse=True)
    model = os.environ.get("VEO_MODEL") or (veo[0] if veo else None)
    if not model:
        log("no Veo model for this key")
        return False
    body = {"instances": [{"prompt": prompt}], "parameters": {"aspectRatio": aspect}}
    r = _rq.post(f"{gemini.API}/models/{model}:predictLongRunning", json=body, headers={"x-goog-api-key": gemini.key()}, timeout=60)
    if r.status_code != 200 and aspect != "16:9":
        body["parameters"]["aspectRatio"] = "16:9"
        r = _rq.post(f"{gemini.API}/models/{model}:predictLongRunning", json=body, headers={"x-goog-api-key": gemini.key()}, timeout=60)
    if r.status_code != 200:
        log("Veo refused:", r.text[:200])
        return False
    op = r.json().get("name")
    for _ in range(60):
        _t.sleep(10)
        j = _rq.get(f"{gemini.API}/{op}", headers={"x-goog-api-key": gemini.key()}, timeout=30).json()
        if j.get("done"):
            if j.get("error"):
                log("Veo failed:", str(j["error"])[:200])
                return False
            resp = j.get("response", {})
            samples = (resp.get("generateVideoResponse") or resp).get("generatedSamples") or resp.get("videos") or []
            uri = samples and ((samples[0].get("video") or {}).get("uri") or samples[0].get("uri"))
            if not uri:
                log("Veo returned no video")
                return False
            v = _rq.get(uri, headers={"x-goog-api-key": gemini.key()}, timeout=300, allow_redirects=True)
            raw = out_path + ".raw.mp4"
            with open(raw, "wb") as f:
                f.write(v.content)
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-stream_loop", "-1", "-i", raw, "-t", f"{seconds:.3f}",
                 "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS},format=yuv420p",
                 "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS), "-g", str(FPS * 2), out_path])
            return True
    log("Veo took too long")
    return False


# ---------------------------------------------------------------- music

MUSIC_DIR = os.environ.get("MUSIC_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "music"))


def pick_music(spec):
    """A track from music/ (put YouTube Audio Library tracks there). Files in music/<series-word>/ win for that series."""
    if os.environ.get("MUSIC", "on").lower() in ("off", "0", "no"):
        return None
    import random
    pool = []
    for root, _, files in os.walk(MUSIC_DIR):
        pool += [os.path.join(root, f) for f in files if f.lower().endswith((".mp3", ".m4a", ".wav", ".ogg", ".flac"))]
    if not pool:
        return None
    key = (spec.get("series") or "").lower()
    top = os.path.normpath(MUSIC_DIR)
    fit = [p for p in pool if os.path.normpath(os.path.dirname(p)) != top and os.path.basename(os.path.dirname(p)).lower() in key]
    general = [p for p in pool if os.path.normpath(os.path.dirname(p)) == top]
    return random.Random(spec.get("topic", "") + spec.get("hook", "")).choice(fit or general or pool)


# ---------------------------------------------------------------- the whole video

def make(spec, work):
    """spec: format short|movie, scenes [{narration, image_prompt, archive_query, chapter}], hook, voice, style,
    outro [3 lines], thumbnail {prompt, text}, pictures gemini|free|archive, motion (int: scenes to animate with Veo).
    Returns {video, preview, thumbnail, duration, chapters, sources, warnings}."""
    fmt = spec["format"]
    F = FORMATS[fmt]
    w, h = F["w"], F["h"]
    d = work
    os.makedirs(d, exist_ok=True)
    scenes = spec["scenes"]
    n = len(scenes)
    warnings = []
    pics = Pictures(spec.get("pictures", "gemini"), spec["style"], F["aspect"], w, h, spec.get("topic", ""))

    # pictures and voice side by side
    got = [None] * n

    def picture(i):
        got[i] = pics.make(i, scenes[i], os.path.join(d, f"img_{i:03d}.jpg"))

    chunks = chunk_scenes(scenes, fmt)
    voice = [os.path.join(d, f"voice_{k:03d}.wav") for k in range(len(chunks))]
    voice_err, engine = [], []

    def voices():
        try:
            engine.append(speak_all([" ".join(scenes[i]["narration"] for i in idx) for idx in chunks],
                                    spec.get("voice", "Charon"), voice, spec.get("voice_engine", "auto")))
        except Exception as e:
            voice_err.append(e)

    vt = threading.Thread(target=voices, daemon=True)
    vt.start()
    with ThreadPoolExecutor(max_workers=int(os.environ.get("IMAGE_WORKERS", "3"))) as ex:
        list(ex.map(picture, range(n)))
    thumb_src = None
    if fmt == "movie":
        thumb_src = os.path.join(d, "thumb_base.jpg")
        tp = spec.get("thumbnail", {}).get("prompt") or scenes[0]["image_prompt"]
        if not pics.make(0, {"image_prompt": f"Dramatic, high-contrast YouTube thumbnail picture, one clear subject, close "
                                            f"and bold, empty space on the left side. {tp}",
                             "archive_query": scenes[0].get("archive_query")}, thumb_src, priority=True):
            thumb_src = None
    vt.join()
    if voice_err:
        raise voice_err[0]
    failed = [i for i in range(n) if not got[i]]
    if len(failed) == n:
        raise RuntimeError("no pictures could be made from any source")
    for i in failed:
        good = [j for j in range(n) if got[j]]
        shutil.copy(os.path.join(d, f"img_{min(good, key=lambda j: abs(j - i)):03d}.jpg"), os.path.join(d, f"img_{i:03d}.jpg"))
        warnings.append(f"scene {i + 1} reused a neighbouring picture")

    # timings
    rate = wav_rate(voice[0])
    starts, ends, speech_ends = [0.0] * n, [0.0] * n, [0.0] * n
    audio_parts, t = [], 0.0
    for k, idx in enumerate(chunks):
        total = probe_duration(voice[k])
        bounds, sp0, sp1 = align([len(scenes[i]["narration"]) for i in idx], total, silences(voice[k]))
        cuts = [0.0] + bounds + [total]
        last = k == len(chunks) - 1
        new_ch = not last and scenes[chunks[k + 1][0]].get("chapter") != scenes[idx[-1]].get("chapter")
        pause = 0.0 if last else (0.7 if new_ch else 0.3)
        for j, i in enumerate(idx):
            starts[i], ends[i] = t + cuts[j], t + cuts[j + 1]
            speech_ends[i] = t + (min(cuts[j + 1], sp1) if j == len(idx) - 1 else cuts[j + 1])
        ends[idx[-1]] += pause
        audio_parts.append(voice[k])
        if pause:
            p = os.path.join(d, f"pause_{k:03d}.wav")
            silence_wav(p, pause, rate)
            audio_parts.append(p)
        t += total + pause
    tail = F["end_card"] or float(spec.get("tail", 0.3))
    p = os.path.join(d, "tail.wav")
    silence_wav(p, tail, rate)
    audio_parts.append(p)
    if not F["end_card"]:
        ends[-1] += tail

    with open(os.path.join(d, "audio.txt"), "w") as f:
        f.writelines(f"file '{os.path.basename(x)}'\n" for x in audio_parts)
    audio = os.path.join(d, "audio.m4a")
    track = pick_music(spec)
    if track:
        vol = float(os.environ.get("MUSIC_VOLUME", "0.22" if fmt == "short" else "0.16"))
        total = t + tail
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i",
             os.path.join(d, "audio.txt"), "-stream_loop", "-1", "-i", track, "-filter_complex",
             f"[0:a]aresample=48000,asplit=2[v1][v2];"
             f"[1:a]aresample=48000,volume={vol},afade=t=in:d=1.5,afade=t=out:st={max(total - 3, 0):.2f}:d=3[m];"
             f"[m][v1]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=500[duck];"
             f"[v2][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]",
             "-map", "[a]", "-t", f"{total:.3f}", "-c:a", "aac", "-b:a", "160k", audio])
        log("music:", os.path.basename(track))
    else:
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i",
             os.path.join(d, "audio.txt"), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-c:a", "aac",
             "-b:a", "160k", audio])

    chapters, cur = [], object()
    for i, s in enumerate(scenes):
        if s.get("chapter") != cur:
            cur = s.get("chapter")
            chapters.append({"title": cur or ("Introduction" if not chapters else f"Part {len(chapters) + 1}"),
                             "start": round(starts[i], 2), "scene": i})
    if chapters:
        chapters[0]["start"] = 0.0

    # Veo motion for the first scenes when asked and billing allows
    motion = int(spec.get("motion", 0) or 0)
    clips = {}
    for i in range(min(motion, n)):
        seg = os.path.join(d, f"veo_{i:03d}.mp4")
        try:
            if veo_clip(f"{spec['style']}. {scenes[i]['image_prompt']}. Slow cinematic camera move, no text, no speech.",
                        F["aspect"], ends[i] - starts[i], seg, w, h):
                clips[i] = seg
        except Exception as e:
            log("Veo clip skipped:", str(e)[:200])
    if motion and not clips:
        warnings.append("AI motion clips were skipped (Veo needs Gemini API billing); used camera moves instead")

    patterns = KB_PATTERNS_TALL if h > w else KB_PATTERNS
    first_of = {c["scene"]: k for k, c in enumerate(chapters)}
    segs, pos = [], 0
    for i in range(n):
        frames = max(round(ends[i] * FPS) - pos, 2)
        pos += frames
        seg = os.path.join(d, f"seg_{i:03d}.mp4")
        if i in clips:
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", clips[i], "-frames:v", str(frames), "-c:v", "libx264",
                 "-preset", "veryfast", "-crf", F["crf"], "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", str(FPS * 2), "-an", seg])
        else:
            overlay, od = None, 0.0
            if fmt == "movie" and first_of.get(i, 0) > 0 and scenes[i].get("chapter"):
                overlay = os.path.join(d, f"chap_{i:03d}.png")
                chapter_card(first_of[i] + 1, scenes[i]["chapter"], w, h, overlay)
                od = 3.6
            render_segment(os.path.join(d, f"img_{i:03d}.jpg"), seg, frames, w, h, patterns[i % len(patterns)], F["crf"], overlay, od)
        segs.append(seg)
        if (i + 1) % 10 == 0:
            log(f"rendered {i + 1}/{n} scenes")
    if F["end_card"]:
        card = os.path.join(d, "endcard.jpg")
        end_card(os.path.join(d, f"img_{n - 1:03d}.jpg"), spec.get("outro", []), w, h, card)
        seg = os.path.join(d, "seg_end.mp4")
        render_segment(card, seg, round(tail * FPS), w, h, "in", F["crf"])
        segs.append(seg)
    with open(os.path.join(d, "video.txt"), "w") as f:
        f.writelines(f"file '{os.path.basename(s)}'\n" for s in segs)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(d, "video.txt"),
         "-c", "copy", os.path.join(d, "joined.mp4")])
    final = os.path.join(d, "video.mp4")
    grain = "noise=alls=4:allf=t,"
    if F["captions"]:
        cues = []
        for i, s in enumerate(scenes):
            ph = phrases(s["narration"])
            t0, t1 = starts[i], max(speech_ends[i], starts[i] + 0.4)
            tot, acc = float(sum(len(x) for x in ph)) or 1.0, 0.0
            for x in ph:
                a = t0 + (t1 - t0) * acc / tot
                acc += len(x)
                cues.append((a, t0 + (t1 - t0) * acc / tot, x))
        write_ass(os.path.join(d, "captions.ass"), w, h, spec.get("hook", ""), cues)
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", "joined.mp4", "-i", "audio.m4a",
             "-vf", f"{grain}vignette=PI/5,subtitles=captions.ass:fontsdir={FONT_DIR}", "-map", "0:v", "-map", "1:a",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", F["crf"], "-maxrate", "12M", "-bufsize", "24M",
             "-pix_fmt", "yuv420p", "-c:a", "copy",
             "-shortest", "-movflags", "+faststart", "video.mp4"], cwd=d)
    else:
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", os.path.join(d, "joined.mp4"), "-i", audio,
             "-map", "0:v", "-map", "1:a", "-c", "copy", "-shortest", "-movflags", "+faststart", final])
    preview = os.path.join(d, "preview.mp4")
    if fmt == "short":
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", final, "-vf", "scale=540:-2", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", preview])
    else:
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-t", "90", "-i", final, "-vf", "scale=-2:480", "-c:v",
             "libx264", "-preset", "veryfast", "-crf", "30", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", preview])
    out = {"video": final, "preview": preview, "duration": round(probe_duration(final), 2), "warnings": warnings,
           "chapters": [{"title": c["title"], "start": c["start"]} for c in chapters], "sources": pics.used,
           "motion_clips": len(clips), "voice_engine": engine[0] if engine else ""}
    if fmt == "movie":
        thumb = os.path.join(d, "thumbnail.jpg")
        compose_thumbnail(thumb_src or os.path.join(d, "img_000.jpg"), spec.get("thumbnail", {}).get("text", ""), thumb)
        out["thumbnail"] = thumb
    return out
