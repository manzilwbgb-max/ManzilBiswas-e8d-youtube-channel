"""The strategist: decides what to make next and writes it the way top history creators do.

Order of ideas: what you asked for on Telegram -> follow-ups to videos that took off ->
the 30-day plan (dated ones on their day) -> fresh ideas from this week's trends."""
import datetime as dt
import json
import os
import re

from . import gemini, sources
from .util import data, drop, items, log, now, put, slug, stamp, today, words

PLAYBOOK = """You are the head strategist and lead writer of "History with Me" (@ManzilBiswas-e8d), an English YouTube channel of
cinematic AI history: true stories told fast in Shorts and deep in 15-minute "history movies".
Audience: curious people aged 18-45 in India, the US, the UK and worldwide who love mysteries, empires, wars,
inventions, ancient India and prehistoric giants.
The channel grows only by keeping promises: every title and hook must be paid off. No padding, no bait-and-switch.

House rules
1. Truth first. Use facts from the SOURCE TEXT or basic, uncontested history. Label legends and disputes
   ("legend says", "historians still argue"). Never invent quotes, numbers, names or dates.
2. The first sentence is the hook: a contradiction, a shocking specific, or an open question, at most 12 words.
   No greeting, no "Did you know", no channel name.
3. One story, one throughline. Every sentence raises a question or answers one. Cut filler.
4. Specific beats vague: names, places, years, numbers, objects.
5. Respect tragedy: no graphic detail of violence or death, no mocking victims, no glorifying perpetrators.
   Advertiser-friendly words only.
6. Write for the ear: short sentences, active voice, rhythm; spell out tricky abbreviations.
7. Be original: never copy another creator's title, script or structure; vary format and opening from recent videos.
8. Pictures: each scene gets its own image description: cinematic, historically accurate clothing, architecture,
   weapons and landscape for the exact era and place; vary the shot (wide establishing, close detail, portrait,
   overhead, silhouette); no text, letters or logos in pictures."""

FORMATS = {
    "story": {
        "mystery": "open on an unsolved question, lay out clues, end on the strongest answer historians have",
        "you-are-there": "second person, present tense: drop the viewer into the moment ('You are standing on...')",
        "myth-vs-fact": "state the popular myth, then flip it with the surprising truth",
        "one-number": "build the whole story around one shocking number",
        "timeline-twist": "tell it in order, then hit a twist nobody saw coming",
        "hidden-detail": "zoom in on a tiny overlooked detail that changes how we see the event",
        "unsung-hero": "the forgotten person who changed the outcome",
        "what-if": "the moment history almost went the other way, and what tipped it",
    },
    "loop": {
        "one-fact": "one jaw-dropping fact, phrased so the ending runs straight into the beginning",
        "time-gap": "two things you would never connect, separated by a surprising span of time",
        "scale": "a size, distance or number made physical and vivid",
    },
    "movie": {
        "documentary story": "chronological story with a cold open and rising stakes",
        "investigation": "a mystery worked through evidence, theories and the most likely answer",
        "rise and fall": "how an empire, city or person rose, peaked and collapsed, and why",
        "countdown": "six connected stories ranked from strange to strangest, one per chapter, each a complete mini-story",
    },
}
LENGTH = {"story": (55, 88, 5, 8), "loop": (12, 28, 2, 4)}  # words lo/hi, scenes lo/hi

# Cinematic AI-video formats: real moving shots with natural sound, not pictures.
CINE_FORMATS = {
    "pov": "first-person POV: the camera is the viewer's own eyes inside the moment, their hands visible doing "
           "period-accurate things; narration in second person, present tense ('You wake up to...'); never show their face",
    "trailer": "a movie-trailer micro-film: epic establishing shot, rising tension, one shocking reveal, a deep trailer voice",
    "timetraveler": "a modern time-traveller vlogs from inside the moment, talking to a handheld selfie camera in short, "
                    "excited lines; the same person in every shot",
}
CINE_LENGTH = {"story": (45, 80, 4, 6, 20, 32), "loop": (12, 24, 1, 2, 6, 10)}  # words, shots, seconds
# the free video engine makes about 3 clips a day of up to 8 s: fewer, longer shots
FREE_LENGTH = {"story": (40, 58, 3, 3, 18, 24), "loop": (12, 20, 1, 1, 6, 8)}


def cinematic_mode():
    return os.environ.get("CINEMATIC", "auto").lower() not in ("off", "0", "no")


def formats_for(kind):
    if kind == "story" and cinematic_mode():
        allowed = [f.strip() for f in os.environ.get("CINE_FORMATS", "pov,trailer").split(",") if f.strip() in CINE_FORMATS]
        return {f: CINE_FORMATS[f] for f in allowed or ["pov"]}
    return FORMATS[kind]


# ------------------------------------------------------------------ helpers

def plan():
    return data("plan.json")


def series_of(name, p=None):
    p = p or plan()
    for s in p["series"]:
        if s["name"].lower() == str(name or "").lower():
            return s
    fallback = p.get("default_series", "")
    return next((s for s in p["series"] if s["name"] == fallback), p["series"][0])


def _clean_scenes(scenes, topic):
    out = []
    for sc in scenes or []:
        if not isinstance(sc, dict):
            continue
        nar = re.sub(r"\s+", " ", str(sc.get("narration", ""))).strip()
        if not nar:
            continue
        vis = str(sc.get("visual", "ai")).lower()
        out.append({"narration": nar,
                    "image_prompt": str(sc.get("image_prompt") or nar).strip(),
                    "archive_query": str(sc.get("archive_query") or topic).strip()[:80],
                    "visual": "archive" if vis.startswith("arch") else "ai",
                    "chapter": sc.get("chapter")})
    if not out:
        raise RuntimeError("the script came back without scenes")
    return out


def _cut(text, n):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0].rstrip(",;:-")
    return cut or text[:n]


def _recent_lines(recent):
    if not recent:
        return "(none yet)"
    return "\n".join(f"- [{r.get('kind')}] {r.get('title')} | series: {r.get('series')} | format: {r.get('format')}"
                     for r in recent[:12])


def _trend_lines(trends, n=10):
    if not trends:
        return "(trend data unavailable today)"
    return "\n".join(f"- {t['title']} | {t['views_per_day']:,} views/day | {t['outlier']}x the channel's size | "
                     f"{t['age_days']} days old" for t in trends[:n])


# ------------------------------------------------------------------ what to make next

def candidates(kind, p=None):
    """Ideas waiting for this kind of video, best first."""
    p = p or plan()
    used = {n for n, _ in items("used")}
    day = today()
    stale = (now().date() - dt.timedelta(days=2)).isoformat()
    out = []
    for n, it in items("inbox"):
        if it.get("kind", "story") == kind:
            out.append(dict(it, id="inbox-" + n, _file=("inbox", n), source="you"))
    for n, it in items("followups"):
        if it.get("kind", "story") == kind:
            out.append(dict(it, id="followup-" + n, _file=("followups", n), source="follow-up"))
    due, later = [], []
    for it in p.get("ideas", []):
        if it.get("kind") != kind or it["id"] in used:
            continue
        d = it.get("date")
        if it.get("timely") and d and (d < stale or d > day):
            continue  # anniversaries only on (or just after) their day
        (due if d and d <= day else later).append(dict(it, source="plan"))
    due.sort(key=lambda x: (not x.get("timely"), x.get("date", "")))
    later.sort(key=lambda x: x.get("date") or "9999")
    for n, it in items("fresh"):
        if it.get("kind", "story") == kind:
            later.append(dict(it, id="fresh-" + n, _file=("fresh", n), source="trend idea"))
    return out + due + later


def fresh_ideas(kind, trends, recent, p=None, n=6):
    """When the plan runs dry: new ideas from this week's trends, saved for the next days."""
    p = p or plan()
    j = gemini.text_json(f"""{PLAYBOOK}

TASK: new_ideas
Propose {n} new {kind} ideas for History with Me that fit our series and ride what is trending now
(borrow the topic interest only, never a title or script).
SERIES:
{chr(10).join(f"- {s['name']}: {s['about']}" for s in p['series'])}
TRENDING NOW:
{_trend_lines(trends, 15)}
OUR RECENT VIDEOS:
{_recent_lines(recent)}
Return JSON: {{"ideas": [{{"topic": "...", "angle": "the specific surprising take", "series": "exact series name",
"wiki": ["best English Wikipedia article title"]}}]}}""", temperature=0.9)
    out = []
    for k, it in enumerate((j or {}).get("ideas", [])[:n]):
        if it.get("topic"):
            rec = {"kind": kind, "topic": it["topic"], "angle": it.get("angle", ""), "series": it.get("series", ""),
                   "wiki": it.get("wiki") or [it["topic"]], "added": now().isoformat()}
            put("fresh", f"{stamp()}-{k}-{slug(it['topic'], 30)}", rec)
            out.append(rec)
    log(f"strategist: {len(out)} fresh {kind} ideas saved")
    return out


def choose(kind, topic=None, trends=None, recent=None):
    """Pick today's idea and decide angle, series, format and why it should work now."""
    p = plan()
    if topic:
        cands = [{"id": "ask-" + slug(topic, 40), "kind": kind, "topic": topic, "source": "you"}]
    else:
        cands = candidates(kind, p)
        if not cands:
            fresh_ideas(kind, trends, recent, p)
            cands = candidates(kind, p)
        if not cands:
            raise RuntimeError(f"no {kind} ideas left and none could be generated")
    first = cands[0]
    fixed = first["source"] in ("you", "follow-up") or bool(first.get("timely") and first.get("date", "9") <= today())
    pool = cands[:1] if fixed else cands[:4]
    recent_formats = [r.get("format") for r in (recent or []) if r.get("kind") == kind][:3]
    listing = "\n".join(f"{i}. {c['topic']} | angle: {c.get('angle', '-')} | series: {c.get('series', '-')}"
                        f"{' | date: ' + c['date'] if c.get('date') else ''}" for i, c in enumerate(pool))
    j = {}
    try:
        j = gemini.text_json(f"""{PLAYBOOK}

TASK: choose_topic
Choose today's {kind} for History with Me.
{"THE TOPIC IS FIXED (the channel owner asked for it): keep candidate 0 and choose the best angle, series and format."
 if fixed else "Prefer a plan candidate. Switch to a new topic only if a trend below is clearly hot, fits a series, and we can tell it accurately and differently."}
CANDIDATES:
{listing}
TRENDING HISTORY {"VIDEOS" if kind == "movie" else "SHORTS"} (topic interest only, never copy):
{_trend_lines(trends)}
OUR RECENT VIDEOS (avoid repeating topics, openings and formats):
{_recent_lines(recent)}
SERIES:
{chr(10).join(f"- {s['name']}: {s['about']}" for s in p['series'])}
FORMATS (pick one not used in the last 3 {kind}s: {", ".join(f for f in recent_formats if f) or "none"}):
{chr(10).join(f"- {k}: {v}" for k, v in formats_for(kind).items())}
Return JSON: {{"choice": candidate number or -1 for a new trend-led topic, "topic": "...", "angle": "the specific surprising take",
"series": "exact series name", "format": "exact format name", "wiki": ["best English Wikipedia article title", "optional second"],
"why": "one line: why this will perform now", "trend_ref": "title of the trend that inspired it, or empty"}}""",
            temperature=0.7)
    except gemini.Fatal:
        raise
    except Exception as e:
        log("topic choice fell back to the plan order:", e)
    c = j.get("choice", 0) if isinstance(j, dict) else 0
    base = dict(pool[c]) if isinstance(c, int) and 0 <= c < len(pool) else {"id": "trend-" + slug(j.get("topic", "x"), 40),
                                                                           "source": "trend"}
    idea = dict(base)
    if not (idea.get("topic") or j.get("topic")):
        idea = dict(pool[0])
    idea["kind"] = kind
    for k in ("topic", "angle", "series", "format", "why", "trend_ref"):
        if j.get(k) and not (k == "topic" and fixed):
            idea[k] = j[k]
    if j.get("wiki"):
        idea["wiki"] = [w for w in j["wiki"] if w][:3] or idea.get("wiki")
    idea.setdefault("angle", "")
    idea["series"] = series_of(idea.get("series"), p)["name"]
    fm = formats_for(kind)
    if idea.get("format") not in fm:
        idea["format"] = next((f for f in fm if f not in recent_formats), next(iter(fm)))
    idea.setdefault("wiki", [idea["topic"]])
    if isinstance(idea["wiki"], str):
        idea["wiki"] = [idea["wiki"]]
    log(f"strategist: {kind} -> {idea['topic']} ({idea['series']}, {idea['format']}) from {idea.get('source')}")
    return idea


def mark_used(idea, rec_id):
    put("used", slug(idea["id"], 80), {"date": today(), "video": rec_id, "topic": idea["topic"]})
    f = idea.get("_file")
    if f:
        drop(*f)


def research(idea, kind):
    """Source text from Wikipedia for the writer and the fact-checker."""
    limit = 24000 if kind == "movie" else 9000
    titles = (idea.get("wiki") or [idea["topic"]])[:3 if kind == "movie" else 2]
    parts, srcs = [], []
    for t in titles:
        f = sources.wiki_facts(t, limit=limit // len(titles))
        if f["text"] and f["url"] not in [s["url"] for s in srcs]:
            parts.append(f"## {f['title']}\n{f['text']}")
            srcs.append({"title": f["title"], "url": f["url"]})
    if not parts:
        log("research: no Wikipedia text found; writing from well-established facts only")
    return {"text": "\n\n".join(parts)[:limit], "sources": srcs}


# ------------------------------------------------------------------ writing

def _source_block(facts):
    if facts["text"]:
        return f'SOURCE TEXT:\n"""\n{facts["text"]}\n"""'
    return "SOURCE TEXT: (none available - use only well-established, uncontested facts and hedge anything else)"


def fact_check(script, facts, label="script"):
    """A strict second pass against the sources; fixes or hedges any claim it can't support."""
    try:
        j = gemini.text_json(f"""TASK: fact_check
You are a strict history fact-checker for a YouTube channel. Check every factual claim in the SCRIPT against
the SOURCE TEXT and well-established history. Fix wrong claims, hedge disputed ones ("historians believe",
"legend says"), remove what cannot be supported. Keep the hook strong, keep the same number of scenes and
keep each scene's length within 15% of the original. Update an image description only if its scene changed.
{_source_block(facts)}
SCRIPT:
{json.dumps({"title": script.get("title", ""), "scenes": [{k: s[k] for k in ("narration", "image_prompt", "archive_query", "visual")} for s in script["scenes"]]}, ensure_ascii=False)}
Return JSON: {{"title": "same or corrected title (never misleading)", "scenes": [{{"narration": "...", "image_prompt": "...",
"archive_query": "...", "visual": "archive or ai"}}], "changes": ["what you changed and why"], "confidence": "high, medium or low"}}""",
            temperature=0.2)
    except gemini.Fatal:
        raise
    except Exception as e:
        log(f"fact check skipped for {label}:", e)
        script.setdefault("fact_check", {"changes": [], "confidence": "unchecked"})
        return script
    try:
        new = _clean_scenes(j.get("scenes"), script.get("topic", ""))
    except RuntimeError:
        new = []
    before = sum(words(x["narration"]) for x in script["scenes"])
    if new and sum(words(x["narration"]) for x in new) >= 0.7 * before:
        olds = script["scenes"]
        for i, sc in enumerate(new):
            sc["chapter"] = olds[min(i, len(olds) - 1)].get("chapter")
        script["scenes"] = new
    else:
        log(f"fact check ({label}) returned an unusable script; keeping the original")
    if j.get("title") and script.get("title") and len(j["title"]) <= 100:
        script["title"] = j["title"]
    prev = script.get("fact_check", {"changes": [], "confidence": "high"})
    order = ["high", "medium", "low", "unchecked"]
    conf = j.get("confidence", "medium")
    script["fact_check"] = {"changes": prev["changes"] + list(j.get("changes", []))[:8],
                            "confidence": max(prev["confidence"], conf if conf in order else "medium", key=order.index)}
    log(f"fact check ({label}): {len(j.get('changes', []))} changes, confidence {conf}")
    return script


def write_short(kind, idea, facts, recent):
    lo, hi, slo, shi = LENGTH[kind]
    secs = "20-35" if kind == "story" else "5-12"
    if kind == "loop":
        ending = ("The last scene's final words must run straight back into the first scene's opening words, so the video "
                  "loops seamlessly (the first scene may begin mid-thought). No call to action.")
    else:
        ending = ("The last scene pays off the hook with a twist or a striking final fact. No 'like and subscribe'; "
                  "you may end with a short line that makes people want the full story.")
    prompt = f"""{PLAYBOOK}

TASK: short_{kind}
Write one YouTube Short ({'story' if kind == 'story' else 'loop'}).
TOPIC: {idea['topic']}
ANGLE: {idea.get('angle') or 'find the most surprising true angle'}
SERIES: {idea['series']} - {series_of(idea['series'])['about']}
FORMAT: {idea['format']} - {FORMATS[kind][idea['format']]}
WHY NOW: {idea.get('why', '')}
OUR RECENT VIDEOS (do not repeat their openings):
{_recent_lines(recent)}
{_source_block(facts)}

Length: {lo}-{hi} spoken words in total (about {secs} seconds) in {slo}-{shi} scenes. Scene 1 is the hook, at most 12 words.
{ending}
Return JSON: {{"title": "max 60 characters, the main keyword early, curiosity without lying",
"hook_text": "2-5 words shown big on screen during the first 2 seconds",
"scenes": [{{"narration": "...", "image_prompt": "...", "archive_query": "2-5 words to find a real public-domain photo, painting or artifact of this scene on Wikimedia Commons",
"visual": "archive if a real photo, painting or artifact of exactly this exists, otherwise ai"}}],
"description": "2-3 sentences that add one fact not in the video",
"tags": ["10-15 search tags, most specific first"],
"hashtags": ["#history", "#shorts", "one or two topic hashtags"],
"pinned_comment": "one question that invites viewers to answer or guess"}}"""
    j = gemini.text_json(prompt, temperature=0.85)
    script = dict(j, topic=idea["topic"])
    script["scenes"] = _clean_scenes(j.get("scenes"), idea["topic"])
    n = sum(words(s["narration"]) for s in script["scenes"])
    if n < lo * 0.75 or n > hi * 1.25:
        log(f"script has {n} words (target {lo}-{hi}); asking for a rewrite")
        j2 = gemini.text_json(prompt + f"\n\nYour previous draft had {n} words. Rewrite it to {lo}-{hi} words. "
                              f"Previous draft:\n{json.dumps(script['scenes'], ensure_ascii=False)}", temperature=0.6)
        try:
            sc = _clean_scenes(j2.get("scenes"), idea["topic"])
            if abs(sum(words(s["narration"]) for s in sc) - (lo + hi) / 2) < abs(n - (lo + hi) / 2):
                script.update({k: v for k, v in j2.items() if k != "scenes"})
                script["scenes"] = sc
        except RuntimeError:
            pass
    script["title"] = _cut(script.get("title") or idea["topic"], 70)
    script = fact_check(script, facts, f"{kind} short")
    script["title"] = _cut(script["title"], 70)
    return script


def write_movie(idea, facts, recent, trends):
    p = plan()
    total = int(os.environ.get("MOVIE_WORDS", p.get("movie_words", 2250)))
    outline = gemini.text_json(f"""{PLAYBOOK}

TASK: movie_outline
Plan a 15-minute narrated history documentary (a "history movie") for YouTube, about {total} spoken words.
TOPIC: {idea['topic']}
ANGLE: {idea.get('angle') or 'the most gripping true angle'}
FORMAT: {idea['format']} - {FORMATS['movie'][idea['format']]}
SERIES: {idea['series']}
TRENDING LONG VIDEOS (topic interest only, never copy):
{_trend_lines(trends, 8)}
OUR RECENT VIDEOS:
{_recent_lines(recent)}
{_source_block(facts)}

Structure that keeps people watching:
- Chapter 1 opens inside the most dramatic moment (cold open), then within 30 seconds promises what the viewer will learn.
- Exactly 6 chapters. Each ends on an open question or reveal that pulls into the next.
- Stakes rise; the biggest revelation lands in chapter 5; chapter 6 resolves everything and leaves one haunting thought.
Return JSON: {{"title": "max 70 characters, main search keyword within the first 40 characters, strong curiosity",
"title_options": ["4 other titles"],
"thumbnail_text": "2-4 words, huge on the thumbnail, must not repeat the title",
"thumbnail_prompt": "one striking picture: a single clear subject, strong emotion or tension, high contrast, empty space on the left",
"promise": "one sentence: what the viewer gets",
"cast": [{{"name": "...", "look": "consistent visual description to reuse in pictures"}}],
"chapters": [{{"title": "2-5 words", "beats": ["5-8 story beats with specific facts"]}}],
"description": "two short keyword-rich paragraphs for the YouTube description, no hashtags",
"tags": ["15-25 search tags"],
"hashtags": ["#history", "#documentary", "one topic hashtag"],
"pinned_comment": "a question that sparks discussion"}}""", temperature=0.8, max_tokens=16000)
    chapters = [c for c in outline.get("chapters", []) if c.get("title")][:6]
    if len(chapters) < 4:
        raise RuntimeError("the movie outline came back with too few chapters")
    per = total // len(chapters)
    cast = "\n".join(f"- {c.get('name')}: {c.get('look')}" for c in outline.get("cast", [])[:8]) or "(none)"
    plan_text = "\n".join(f"{i + 1}. {c['title']}: " + "; ".join(c.get("beats", [])) for i, c in enumerate(chapters))
    scenes, last = [], ""
    for i, ch in enumerate(chapters):
        first, final = i == 0, i == len(chapters) - 1
        rule = ("Open in the middle of the most dramatic moment, then state the promise: "
                f"{outline.get('promise', '')}" if first else f"Continue naturally from: \"{last}\"")
        end = ("End by resolving the story and leaving one haunting thought, then one sentence inviting viewers to the "
               "next history movie." if final else "End on an open question or reveal that pulls into the next chapter.")
        prompt = f"""{PLAYBOOK}

TASK: movie_chapter
Write chapter {i + 1} of {len(chapters)} of the documentary "{outline.get('title', idea['topic'])}".
FULL OUTLINE:
{plan_text}
THIS CHAPTER: {ch['title']} - beats: {"; ".join(ch.get("beats", []))}
CAST (reuse these looks whenever they appear in a picture):
{cast}
{_source_block(facts)}
{rule}
Write {int(per * 0.9)}-{int(per * 1.15)} spoken words as {max(per // 32, 8)}-{max(per // 22, 10)} scenes of 18-35 words each.
{end}
Return JSON: {{"scenes": [{{"narration": "...", "image_prompt": "16:9 cinematic picture for this scene",
"archive_query": "2-5 words for Wikimedia Commons", "visual": "archive or ai"}}]}}"""
        j = gemini.text_json(prompt, temperature=0.8)
        sc = _clean_scenes(j.get("scenes"), idea["topic"])
        n = sum(words(s["narration"]) for s in sc)
        if n < per * 0.6:
            log(f"chapter {i + 1} too short ({n} words); asking again")
            j = gemini.text_json(prompt + f"\n\nYour previous attempt had only {n} words. Write at least {int(per * 0.9)} words.",
                                 temperature=0.8)
            sc2 = _clean_scenes(j.get("scenes"), idea["topic"])
            if sum(words(s["narration"]) for s in sc2) > n:
                sc = sc2
        part = fact_check({"title": "", "topic": idea["topic"], "scenes": sc}, facts, f"chapter {i + 1}")
        for s in part["scenes"]:
            s["chapter"] = ch["title"]
        scenes += part["scenes"]
        last = " ".join(s["narration"] for s in part["scenes"][-2:])
        outline.setdefault("_checks", []).append(part.get("fact_check", {}))
    order = ["high", "medium", "low", "unchecked"]
    checks = outline.pop("_checks", [])
    script = dict(outline, topic=idea["topic"], scenes=scenes)
    script["title"] = _cut(outline.get("title") or idea["topic"], 90)
    script["fact_check"] = {"changes": [c for k in checks for c in k.get("changes", [])][:10],
                            "confidence": max((k.get("confidence", "medium") for k in checks), key=lambda c: order.index(c)
                                              if c in order else 1, default="unchecked")}
    log(f"movie script: {len(scenes)} scenes, {sum(words(s['narration']) for s in scenes)} words")
    return script


def write_cinematic(kind, idea, facts, recent, host_look="", engine="omni"):
    """A shot list for real AI video: each shot is a camera direction with natural sound, plus the voiceover.
    engine "free" plans fewer, longer shots for the free video engine (about 3 clips of up to 8 s a day)."""
    wlo, whi, slo, shi, tlo, thi = (FREE_LENGTH if engine == "free" else CINE_LENGTH)[kind]
    shot_len = "6-8" if engine == "free" else "3-10"
    fmt = idea["format"] if kind == "story" else "loop"
    desc = CINE_FORMATS.get(fmt, "one or two breathtaking shots that show the fact itself, with a voiceover that loops")
    talk = fmt == "timetraveler"
    ending = ("The final words must run straight back into the first words so the clip loops seamlessly." if kind == "loop"
              else "End on a twist or a haunting final fact that makes people rewatch or comment.")
    prompt = f"""{PLAYBOOK}

TASK: cine_{kind}
You are also the director. Write a cinematic AI-video YouTube Short, shot by shot, for a video model that generates
photorealistic {shot_len} second shots with natural sound.
TOPIC: {idea['topic']}
ANGLE: {idea.get('angle') or 'the most gripping true angle'}
SERIES: {idea['series']}
FORMAT: {fmt} - {desc}
OUR RECENT VIDEOS (vary the opening):
{_recent_lines(recent)}
{_source_block(facts)}

Rules
- {slo}-{shi} shots, {tlo}-{thi} seconds in total. Shot 1 is the most striking moment of the whole story (start in the
  middle of the action), readable in a split second.
- Each shot's "visual" is a camera direction: shot type and camera move (for example "first-person POV, handheld, looking
  down at my hands", "low-angle tracking shot", "slow push-in"), the subject and ONE clear action, period-accurate clothes,
  tools and architecture for the exact year and place, lighting, weather, mood, and the natural sounds heard
  (ambience, footsteps, crowd, fire, wind). No text, captions or logos in the picture.
- Describe the main character's look the same way in every shot so they stay the same person{(': ' + host_look) if talk and host_look else ''}.
{'- The vlogger speaks to the camera: put their words in "dialogue" (at most 12 words per shot) and leave "voiceover" empty.' if talk else '- Narration goes in "voiceover" (about 2.5 words per second of the shot); write "no dialogue" into every visual.'}
- {wlo}-{whi} spoken words in total. Never graphic: show danger and tragedy through faces, sound and aftermath.
- {ending}
Return JSON: {{"title": "max 60 characters, keyword early, curiosity without lying",
"hook_text": "on-screen text for the first 3 seconds, max 45 characters (e.g. POV: You're a Pompeii baker, 79 AD)",
"shots": [{{"seconds": 4, "visual": "...", "voiceover": "...", "dialogue": "", "archive_query": "2-5 words for a real photo if one exists"}}],
"description": "2-3 sentences adding one fact not in the video",
"tags": ["10-15 search tags"], "hashtags": ["#history", "#shorts", "one topic hashtag"],
"pinned_comment": "a question viewers want to answer"}}"""
    j = gemini.text_json(prompt, temperature=0.9)
    shots = []
    for sh in j.get("shots") or []:
        if not isinstance(sh, dict) or not str(sh.get("visual", "")).strip():
            continue
        shots.append({"seconds": min(max(float(sh.get("seconds") or 5), 3), 10),
                      "visual": re.sub(r"\s+", " ", str(sh["visual"])).strip(),
                      "voiceover": re.sub(r"\s+", " ", str(sh.get("voiceover") or "")).strip(),
                      "dialogue": re.sub(r"\s+", " ", str(sh.get("dialogue") or "")).strip(),
                      "archive_query": str(sh.get("archive_query") or idea["topic"])[:80]})
    if not shots:
        raise RuntimeError("the director returned no shots")
    # the same strict fact check as every other script, run on what is said
    said = [{"narration": x["voiceover"] or x["dialogue"] or "(no words)", "image_prompt": x["visual"],
             "archive_query": x["archive_query"], "visual": "ai"} for x in shots]
    checked = fact_check({"title": j.get("title", ""), "topic": idea["topic"], "scenes": said}, facts, f"cinematic {kind}")
    if len(checked["scenes"]) == len(shots):
        for x, c in zip(shots, checked["scenes"]):
            words_ = "" if c["narration"] == "(no words)" else c["narration"]
            if x["dialogue"] and not x["voiceover"]:
                x["dialogue"] = words_
            else:
                x["voiceover"] = words_
            x["visual"] = c["image_prompt"] or x["visual"]
    script = dict(j, topic=idea["topic"], shots=shots, format=fmt, fact_check=checked.get("fact_check", {}))
    script["title"] = _cut(checked.get("title") or j.get("title") or idea["topic"], 70)
    script["scenes"] = [{"narration": x["voiceover"] or x["dialogue"], "image_prompt": x["visual"],
                         "archive_query": x["archive_query"], "visual": "ai"} for x in shots]
    return script


def cine_spec(kind, script, idea, p=None, pictures=None, host=None):
    p = p or plan()
    s = series_of(idea["series"], p)
    return {"format": "short", "kind": kind, "shots": script["shots"], "hook": _cut(script.get("hook_text", ""), 48),
            "voice": s.get("voice") or p["channel"].get("voice", "Charon"), "style": s.get("style") or p["channel"]["style"],
            "pictures": pictures or os.environ.get("PICTURES", "auto") or "auto", "topic": idea["topic"],
            "series": s["name"], "voice_engine": os.environ.get("VOICE", "auto") or "auto", "aspect": "9:16",
            "host": host if script.get("format") == "timetraveler" else None}


def write(kind, idea, facts, recent, trends):
    return write_movie(idea, facts, recent, trends) if kind == "movie" else write_short(kind, idea, facts, recent)


# ------------------------------------------------------------------ render spec and YouTube text

def spec(kind, script, idea, p=None, pictures=None, motion=None):
    p = p or plan()
    s = series_of(idea["series"], p)
    ch = p["channel"]
    out = {"format": "movie" if kind == "movie" else "short", "scenes": script["scenes"],
           "hook": "" if kind != "story" else _cut(script.get("hook_text", ""), 40),
           "voice": s.get("voice") or ch.get("voice", "Charon"), "style": s.get("style") or ch["style"],
           "pictures": pictures or os.environ.get("PICTURES", "auto") or "auto",
           "motion": int(motion if motion is not None else os.environ.get("MOTION", "0") or 0),
           "topic": script["scenes"][0].get("archive_query") or idea["topic"], "series": s["name"],
           "tail": 0.05 if kind == "loop" else 0.4, "voice_engine": os.environ.get("VOICE", "auto") or "auto"}
    if kind == "movie":
        out["thumbnail"] = {"prompt": script.get("thumbnail_prompt", ""), "text": _cut(script.get("thumbnail_text", ""), 28)}
        out["outro"] = ["Thanks for watching History with Me",
                        "New history movies every Wednesday and Sunday",
                        "Subscribe so you never miss the next one"]
    return out


def _stamp_time(t):
    t = int(round(t))
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"


def metadata(kind, script, idea, facts, out, p=None):
    p = p or plan()
    s = series_of(idea["series"], p)
    ch = p["channel"]
    tags, seen = [], set()
    for t in list(script.get("tags", [])) + list(s.get("tags", [])) + ["history", "history with me"]:
        t = re.sub(r"[<>\"]", "", str(t)).strip()
        if t and t.lower() not in seen and sum(len(x) + 3 for x in tags) + len(t) < 450:
            seen.add(t.lower())
            tags.append(t)
    hashtags = []
    for h in list(script.get("hashtags", [])) + list(s.get("hashtags", [])):
        h = "#" + re.sub(r"[^A-Za-z0-9]", "", str(h))
        if len(h) > 1 and h.lower() not in [x.lower() for x in hashtags]:
            hashtags.append(h)
    if kind != "movie" and "#shorts" not in [h.lower() for h in hashtags]:
        hashtags.insert(1, "#shorts")
    hashtags = hashtags[:4] if kind != "movie" else hashtags[:3]
    lines = [str(script.get("description", "")).strip()]
    if kind == "movie":
        chaps = out.get("chapters") or []
        if len(chaps) >= 3:
            lines += ["", "Chapters"] + [f"{_stamp_time(c['start'])} {c['title']}" for c in chaps]
    else:
        lines += ["", ch.get("short_footer", "Full history movies every Wednesday and Sunday on History with Me.")]
    if s.get("app_line"):
        lines += ["", s["app_line"]]
    if facts.get("sources"):
        lines += ["", "Sources"] + [f"- {x['title']}: {x['url']}" for x in facts["sources"]]
    lines += ["", ch.get("ai_note", "Narration voice and pictures are AI-generated. The script is researched from the "
                                    "sources above and reviewed by the creator before publishing."), "", " ".join(hashtags)]
    return {"title": _cut(script["title"], 100), "description": "\n".join(lines).strip()[:4900], "tags": tags,
            "pinned_comment": str(script.get("pinned_comment", "")).strip()[:500]}


# ------------------------------------------------------------------ weekly review and chat

def weekly_review(rows, goals, recent_titles):
    """Find what worked, queue follow-ups for outliers, and give the creator three clear moves for the week."""
    shorts = [r for r in rows if r.get("kind") != "movie" and r.get("views") is not None]
    med = sorted(r["views"] for r in shorts)[len(shorts) // 2] if shorts else 0
    for r in rows:
        r["outlier"] = bool(med and r.get("kind") != "movie" and r.get("views", 0) >= 3 * med and r.get("views", 0) >= 1000)
    j = gemini.text_json(f"""{PLAYBOOK}

TASK: weekly_review
You review History with Me's last 28 days like a top YouTube strategist. Be specific and honest.
GOALS (YouTube Partner Program before February 1, 2027): {json.dumps(goals)}
VIDEOS (views, average % viewed, subscribers gained; outlier = at least 3x the median Short):
{json.dumps(rows, ensure_ascii=False)[:12000]}
Return JSON: {{"summary": "3 short sentences: what is working and what is not",
"double_down": [{{"kind": "story or loop", "topic": "...", "angle": "...", "series": "...", "based_on": "title of the outlier"}}],
"movie_idea": {{"topic": "...", "angle": "...", "series": "...", "based_on": "..."}} or null,
"moves": ["three concrete moves for this week"],
"title_lesson": "one sentence about titles/hooks that worked"}}""", temperature=0.5)
    for k, it in enumerate((j.get("double_down") or [])[:3]):
        if it.get("topic"):
            put("followups", f"{stamp()}-{k}-{slug(it['topic'], 30)}", dict(it, kind=it.get("kind", "story"),
                                                                              wiki=[it["topic"]], added=now().isoformat()))
    mi = j.get("movie_idea")
    if isinstance(mi, dict) and mi.get("topic"):
        put("followups", f"{stamp()}-m-{slug(mi['topic'], 30)}", dict(mi, kind="movie", wiki=[mi["topic"]],
                                                                       added=now().isoformat()))
    return j


def intent(text):
    """Understand a plain message from the creator."""
    return gemini.text_json(f"""TASK: intent
You are the History with Me YouTube agent's command reader. The creator wrote: "{text}"
Map it to one action: make (a story Short now), loop (a loop Short now), movie (a 15-minute movie now), idea (save a topic
for later; set kind story, loop or movie), status (channel progress), next (upcoming ideas), pending (videos waiting for a
decision), trends (what is trending in history now), pause, resume, help, or chat (anything else - answer briefly as a friendly YouTube history strategist).
Return JSON: {{"action": "...", "topic": "topic if any", "kind": "story, loop or movie", "reply": "short reply for chat"}}""",
                            temperature=0.2, max_tokens=4000)
