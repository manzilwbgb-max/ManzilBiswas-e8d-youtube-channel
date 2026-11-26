"""Telegram: previews, the Publish / Keep private buttons, and reading your taps."""
import html
import json
import os
import re

import requests


def _url(method):
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not tok:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    base = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org").rstrip("/")
    return f"{base}/bot{tok}/{method}"


def chat():
    return str(os.environ.get("TELEGRAM_CHAT_ID", "")).strip().strip("\"'` ").strip()


def chat_problem(value=None):
    """Why TELEGRAM_CHAT_ID can't work ('' when it looks right). Never echoes the value: the logs are public."""
    v = chat() if value is None else str(value).strip()
    if not v:
        return "it is not saved yet"
    if re.fullmatch(r"-?\d{3,20}", v):
        return ""
    low = v.lower()
    if "t.me" in low or "http" in low or "/" in v:
        return "it looks like a link, but it must be the number the bot sends you"
    if re.search(r"\d+:[\w-]{20,}", v):
        return "it looks like the bot token, but it must be the number the bot sends you"
    if re.search(r"[a-z]", low):
        return "it contains letters, but it must be the number the bot sends you"
    return "it must be only the number the bot sends you (digits, nothing else)"


def private_chat(update):
    """The private chat an update came from (None for groups and channels)."""
    cq = update.get("callback_query") or {}
    c = ((update.get("message") or cq.get("message") or {}).get("chat")) or {}
    return c.get("id") if c.get("type") == "private" and c.get("id") else None


def chat_id_note(cid):
    return (f"Your chat id is {cid}\n\nSave this number in GitHub: your repository → Settings → Secrets and variables → "
            "Actions → TELEGRAM_CHAT_ID (edit it, or New repository secret). Paste only the number: no link, no name.")


def reachable():
    """True when the bot can message the owner's chat (checked before spending money on a video)."""
    if chat_problem():
        return False
    try:
        call("getChat", chat_id=chat())
        return True
    except Exception:
        return False


def call(method, files=None, **data):
    if files:
        r = requests.post(_url(method), data={k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v))
                                              for k, v in data.items()}, files=files, timeout=600)
    else:
        r = requests.post(_url(method), json=data, timeout=60)
    j = r.json()
    if not j.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {j.get('description')}")
    return j["result"]


def esc(s):
    return html.escape(str(s or ""), quote=False)


def keyboard(rows):
    return {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in rows]}


def send(text, rows=None):
    kw = dict(chat_id=chat(), text=text[:4096], parse_mode="HTML", disable_web_page_preview=True)
    if rows:
        kw["reply_markup"] = keyboard(rows)
    return call("sendMessage", **kw)


def send_video(path, caption, rows=None, filename="preview.mp4"):
    data = dict(chat_id=chat(), caption=caption[:1024], parse_mode="HTML", supports_streaming="true")
    if rows:
        data["reply_markup"] = keyboard(rows)
    with open(path, "rb") as f:
        return call("sendVideo", files={"video": (filename, f, "video/mp4")}, **data)


def send_photo(path, caption):
    with open(path, "rb") as f:
        return call("sendPhoto", files={"photo": ("thumbnail.jpg", f, "image/jpeg")},
                    chat_id=chat(), caption=caption[:1024], parse_mode="HTML")


def updates(offset):
    return call("getUpdates", offset=offset, timeout=0, allowed_updates=["callback_query", "message"])


def answer(callback_id, text):
    try:
        call("answerCallbackQuery", callback_query_id=callback_id, text=text[:190])
    except Exception:
        pass


def clear_buttons(message_id):
    try:
        call("editMessageReplyMarkup", chat_id=chat(), message_id=message_id, reply_markup={"inline_keyboard": []})
    except Exception:
        pass


def send_document(path, caption, rows=None, filename=None, mime="application/octet-stream"):
    data = dict(chat_id=chat(), caption=caption[:1024], parse_mode="HTML")
    if rows:
        data["reply_markup"] = keyboard(rows)
    with open(path, "rb") as f:
        return call("sendDocument", files={"document": (filename or os.path.basename(path), f, mime)}, **data)


def edit_caption(message_id, caption, rows=None):
    """Rewrite a video/photo caption (and its buttons). Falls back to editing text for text messages."""
    kw = dict(chat_id=chat(), message_id=message_id, parse_mode="HTML",
              reply_markup=keyboard(rows) if rows else {"inline_keyboard": []})
    try:
        return call("editMessageCaption", caption=caption[:1024], **kw)
    except Exception:
        try:
            return call("editMessageText", text=caption[:4096], disable_web_page_preview=True, **kw)
        except Exception:
            return None


def from_owner(update):
    """True only for messages and taps from your own chat (everyone else is ignored)."""
    owner = chat()
    if not owner:
        return False
    cq = update.get("callback_query")
    msg = (cq or {}).get("message") if cq else update.get("message")
    sender = (cq or update.get("message") or {}).get("from") or {}
    if str(((msg or {}).get("chat") or {}).get("id", "")) != owner:
        return False
    return owner.startswith("-") or str(sender.get("id", "")) == owner
