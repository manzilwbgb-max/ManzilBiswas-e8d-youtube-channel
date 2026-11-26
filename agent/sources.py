"""Free sources: Wikipedia for facts, Wikimedia Commons for public-domain pictures."""
import io
import re

from PIL import Image, ImageOps

from .util import http, log

import os

PD = re.compile(r"public domain|^pd\b|^pd-|cc0", re.I)
WIKI_API = os.environ.get("WIKI_API", "https://en.wikipedia.org/w/api.php")
COMMONS_API = os.environ.get("COMMONS_API", "https://commons.wikimedia.org/w/api.php")


def wiki_facts(query, limit=12000):
    """Plain text of the best-matching English Wikipedia article."""
    try:
        r = http("GET", WIKI_API, params={
            "action": "query", "generator": "search", "gsrsearch": query, "gsrlimit": 1,
            "prop": "extracts|info", "explaintext": 1, "exsectionformat": "plain", "inprop": "url",
            "redirects": 1, "format": "json"})
        for p in ((r.json().get("query") or {}).get("pages") or {}).values():
            return {"title": p.get("title", query), "url": p.get("fullurl", ""), "text": (p.get("extract") or "")[:limit]}
    except Exception as e:
        log("wikipedia failed:", e)
    return {"title": query, "url": "", "text": ""}


def commons_search(query, n=12, min_side=800):
    """Public-domain or CC0 pictures from Wikimedia Commons (no credit line needed)."""
    out = []
    try:
        r = http("GET", COMMONS_API, params={
            "action": "query", "generator": "search", "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6,
            "gsrlimit": 40, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1800,
            "format": "json"})
        pages = sorted(((r.json().get("query") or {}).get("pages") or {}).values(), key=lambda p: p.get("index", 99))
        for p in pages:
            ii = (p.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata") or {}
            lic = re.sub(r"<[^>]+>", "", (meta.get("LicenseShortName") or {}).get("value", ""))
            if not PD.search(lic.strip()):
                continue
            if min(ii.get("width", 0), ii.get("height", 0)) < min_side:
                continue
            out.append({"url": ii.get("thumburl") or ii.get("url"), "title": p.get("title"), "license": lic,
                        "page": ii.get("descriptionurl")})
            if len(out) >= n:
                break
    except Exception as e:
        log("commons failed:", e)
    return out


def fingerprint(img):
    """64-bit average hash: near-identical photos get near-identical fingerprints."""
    g = ImageOps.grayscale(img).resize((8, 8), Image.LANCZOS)
    px = list(g.getdata())
    avg = sum(px) / 64.0
    return sum(1 << i for i, v in enumerate(px) if v > avg)


def commons_picture(query, out_path, w, h, avoid=(), hashes=None, lock=None):
    """Save the first public-domain picture for the query that isn't already used (by link or by look).
    Returns its info or None."""
    for item in commons_search(query):
        if item["url"] in avoid:
            continue
        try:
            r = http("GET", item["url"], timeout=60)
            if r.status_code != 200:
                continue
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            if hashes is not None:
                fp = fingerprint(img)
                if any(bin(fp ^ x).count("1") <= 6 for x in hashes):
                    continue  # same photo as one already in this video
                if lock:
                    with lock:
                        hashes.append(fp)
                else:
                    hashes.append(fp)
            ImageOps.fit(img, (w, h), Image.LANCZOS, centering=(0.5, 0.4)).save(out_path, "JPEG", quality=92)
            return item
        except Exception as e:
            log("commons download failed:", e)
    return None
