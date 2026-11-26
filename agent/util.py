"""Small shared helpers: time in India, logging, state files, HTTP with retries."""
import datetime as dt
import json
import os
import random
import re
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state")
DATA = os.path.join(ROOT, "data")
WORK = os.environ.get("WORK_DIR", os.path.join(ROOT, "work"))
UA = "HistoryWithMeAgent/1.0 (YouTube channel History with Me)"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
DRY = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")


def now():
    return dt.datetime.now(IST)


def today():
    return now().date().isoformat()


def log(*a):
    print(now().strftime("%H:%M:%S"), *a, flush=True)


def load(name, default):
    try:
        with open(os.path.join(STATE, name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(name, data):
    os.makedirs(STATE, exist_ok=True)
    with open(os.path.join(STATE, name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def data(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def http(method, url, tries=4, **kw):
    """requests with retries on network errors, 429 and 5xx."""
    kw.setdefault("timeout", 60)
    headers = dict(kw.pop("headers", None) or {})
    headers.setdefault("User-Agent", UA)
    delay, r = 3.0, None
    for i in range(tries):
        try:
            r = requests.request(method, url, headers=headers, **kw)
            if r.status_code < 500 and r.status_code != 429:
                return r
        except requests.RequestException:
            if i == tries - 1:
                raise
        time.sleep(delay + random.random())
        delay *= 2
    return r


def parse_json(text):
    """Read a JSON value from a model reply, tolerating code fences or a sentence around it."""
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except ValueError:
        a = min([i for i in (t.find("{"), t.find("[")) if i >= 0], default=-1)
        b = max(t.rfind("}"), t.rfind("]"))
        if a >= 0 and b > a:
            return json.loads(t[a:b + 1])
        raise


def slug(s, n=60):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:n] or "video"


def stamp():
    return now().strftime("%Y%m%d-%H%M%S")


# State lives in small files (one per video / idea) so two jobs never fight over one file.

def items(sub):
    """All records in state/<sub>/ as [(name, obj)], oldest first."""
    d = os.path.join(STATE, sub)
    out = []
    if os.path.isdir(d):
        for n in sorted(os.listdir(d)):
            if n.endswith(".json"):
                try:
                    with open(os.path.join(d, n), encoding="utf-8") as f:
                        out.append((n[:-5], json.load(f)))
                except (OSError, ValueError):
                    pass
    return out


def get_item(sub, name, default=None):
    try:
        with open(os.path.join(STATE, sub, name + ".json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def put(sub, name, obj):
    d = os.path.join(STATE, sub)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def drop(sub, name):
    try:
        os.remove(os.path.join(STATE, sub, name + ".json"))
    except OSError:
        pass


def words(text):
    return len(re.findall(r"[A-Za-z0-9']+", text or ""))
