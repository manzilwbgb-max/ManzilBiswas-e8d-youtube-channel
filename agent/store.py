"""Finished videos wait for your approval as files in a private draft release of this GitHub repo.
Nothing reaches YouTube until you tap Publish (or Best time / Private upload) on Telegram."""
import os

import requests

from .util import log

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
UPLOADS = os.environ.get("GITHUB_UPLOADS_URL", "https://uploads.github.com").rstrip("/")


def _h(extra=None):
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if not tok:
        raise RuntimeError("GITHUB_TOKEN is missing (it is provided automatically inside GitHub Actions)")
    h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    h.update(extra or {})
    return h


def _repo():
    r = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not r:
        raise RuntimeError("GITHUB_REPOSITORY is missing (it is provided automatically inside GitHub Actions)")
    return r


def keep(rec_id, files, note=""):
    """files: {name: path}. Returns {"id": release_id, "assets": {name: asset_id}}."""
    r = requests.post(f"{API}/repos/{_repo()}/releases", headers=_h(), timeout=60, json={
        "tag_name": f"pending-{rec_id}", "name": f"Waiting for approval: {rec_id}", "body": note[:2000],
        "draft": True, "prerelease": True})
    if r.status_code not in (200, 201):
        raise RuntimeError("could not store the video on GitHub: " + r.text[:300])
    rel = r.json()
    out = {"id": rel["id"], "assets": {}, "links": {}}
    for name, path in files.items():
        mime = "video/mp4" if name.endswith(".mp4") else "image/jpeg"
        for attempt in range(3):
            try:
                with open(path, "rb") as f:
                    a = requests.post(f"{UPLOADS}/repos/{_repo()}/releases/{rel['id']}/assets", params={"name": name},
                                      headers=_h({"Content-Type": mime}), data=f, timeout=(30, 1800))
                if a.status_code in (200, 201):
                    out["assets"][name] = a.json()["id"]
                    out["links"][name] = a.json().get("browser_download_url", "")
                    break
                log("store upload refused:", a.status_code, a.text[:200])
            except requests.RequestException as e:
                log("store upload interrupted:", e)
        else:
            raise RuntimeError(f"could not store {name} on GitHub")
    log(f"stored {len(files)} file(s) for approval (draft release {rel['id']})")
    return out


def fetch(asset_id, out_path):
    """GitHub answers with a short-lived download link; follow it WITHOUT sending the GitHub token there."""
    url, headers = f"{API}/repos/{_repo()}/releases/assets/{asset_id}", _h({"Accept": "application/octet-stream"})
    for _ in range(5):
        r = requests.get(url, headers=headers, stream=True, timeout=(30, 1800), allow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
            url, headers = r.headers["Location"], {"Accept": "application/octet-stream"}
            r.close()
            continue
        if r.status_code != 200:
            raise RuntimeError(f"could not fetch the stored video ({r.status_code}); it may have been deleted")
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        r.close()
        return out_path
    raise RuntimeError("could not fetch the stored video (too many redirects)")


def forget(release_id):
    try:
        requests.delete(f"{API}/repos/{_repo()}/releases/{release_id}", headers=_h(), timeout=60)
    except requests.RequestException as e:
        log("could not delete the stored files:", e)
