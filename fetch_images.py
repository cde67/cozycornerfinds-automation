"""
Fetches a real photo for a given item description (e.g. "Chunky knit throw
blanket") via the Pexels API (pexels.com/api) - a free stock photo API. Free
tier, no cost, no attribution required for commercial use per the Pexels
License. Requires PEXELS_API_KEY in .env.

Results are cached locally (by item text) in images/cache/ so the same item
reuses the same photo across cycles instead of refetching.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

API_BASE = "https://api.pexels.com/v1/search"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(SCRIPT_DIR, "images", "cache")
MANIFEST_PATH = os.path.join(SCRIPT_DIR, "images", "manifest.json")
TILE_SIZE = 600


def _load_env():
    env = {}
    path = os.path.join(SCRIPT_DIR, ".env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k] = v
    return env


def _api_key():
    key = os.environ.get("PEXELS_API_KEY")
    if key:
        return key
    return _load_env().get("PEXELS_API_KEY")


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {}


def _save_manifest(m):
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(m, f, indent=2)


def _search(query, per_page=5):
    key = _api_key()
    if not key:
        raise RuntimeError("PEXELS_API_KEY not set in .env or environment")
    url = API_BASE + "?" + urllib.parse.urlencode({
        "query": query,
        "per_page": per_page,
        "orientation": "square",
    })
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": "CozyCornerFindsBot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode()).get("photos", [])
    except (urllib.error.URLError, urllib.error.HTTPError):
        return []


def _download_and_tile(url, out_path):
    req = urllib.request.Request(url, headers={"User-Agent": "CozyCornerFindsBot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return False

    tmp_path = out_path + ".src"
    with open(tmp_path, "wb") as f:
        f.write(data)
    try:
        img = Image.open(tmp_path).convert("RGB")
    except Exception:
        os.remove(tmp_path)
        return False
    w, h = img.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((TILE_SIZE, TILE_SIZE), Image.LANCZOS)
    img.save(out_path, "JPEG", quality=88)
    os.remove(tmp_path)
    return True


def fetch_candidates(item_text, out_dir, n=6):
    """Downloads up to n distinct candidate photos for item_text into out_dir
    (as 0.jpg, 1.jpg, ...) WITHOUT picking one automatically - unlike
    get_item_image, which silently takes the first search result. That
    'first result wins' shortcut is what caused real mismatches (e.g. a
    'Cable management box' search returning an open PC case) since Pexels'
    top hit for an ambiguous multi-word query is often a lifestyle/action
    photo or an unrelated object that merely shares a keyword, not an actual
    product shot of the named item. This instead gathers several candidates
    across a couple of query phrasings so a human (or an agent looking at
    the actual images) can pick the one that really shows the item, or
    reject all of them.

    Returns a list of {path, credit, url} dicts, most-relevant-query-first.
    """
    os.makedirs(out_dir, exist_ok=True)
    queries = [item_text, f"{item_text} product photo", " ".join(item_text.split()[-2:])]
    seen_urls = set()
    candidates = []
    for q in queries:
        if len(candidates) >= n:
            break
        for photo in _search(q, per_page=6):
            if len(candidates) >= n:
                break
            src = photo.get("src", {})
            img_url = src.get("large") or src.get("medium") or src.get("original")
            if not img_url or img_url in seen_urls:
                continue
            seen_urls.add(img_url)
            out_path = os.path.join(out_dir, f"{len(candidates)}.jpg")
            if _download_and_tile(img_url, out_path):
                credit = f"Photo by {photo.get('photographer', 'a Pexels contributor')} (Pexels)"
                candidates.append({"path": out_path, "credit": credit, "url": img_url})
    return candidates


def get_item_image(item_text):
    """Returns (local_path_or_None, credit_text_or_None) for an item. Cached
    by item_text so repeated items reuse the same photo across cycles. Pexels
    License requires no attribution, but we keep a light credit line handy."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    manifest = _load_manifest()

    if item_text in manifest:
        entry = manifest[item_text]
        path = entry.get("path")
        if path and os.path.exists(os.path.join(SCRIPT_DIR, path)):
            return os.path.join(SCRIPT_DIR, path), entry.get("credit")
        if entry.get("no_image"):
            return None, None

    slug = _slug(item_text)
    out_path = os.path.join(CACHE_DIR, f"{slug}.jpg")

    queries = [item_text, " ".join(item_text.split()[-2:])]
    chosen = None
    for q in queries:
        photos = _search(q)
        for photo in photos:
            src = photo.get("src", {})
            img_url = src.get("large") or src.get("medium") or src.get("original")
            if not img_url:
                continue
            if _download_and_tile(img_url, out_path):
                chosen = photo
                break
        if chosen:
            break

    if not chosen:
        manifest[item_text] = {"no_image": True}
        _save_manifest(manifest)
        return None, None

    credit = f"Photo by {chosen.get('photographer', 'a Pexels contributor')} (Pexels)"
    rel_path = os.path.relpath(out_path, SCRIPT_DIR)
    manifest[item_text] = {"path": rel_path, "credit": credit}
    _save_manifest(manifest)
    return out_path, credit


if __name__ == "__main__":
    import sys
    for item in sys.argv[1:] or ["chunky knit throw blanket", "ceramic aromatherapy diffuser"]:
        path, credit = get_item_image(item)
        print(item, "->", path, "|", credit)
