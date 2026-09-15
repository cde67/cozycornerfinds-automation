"""
Builds the Cozy Home Finds "link in bio" landing page (docs/index.html),
hosted for free via GitHub Pages on the same repo used for image hosting.

Every item shows a real photo (fetched/cached via fetch_images.py, same
source as the Instagram posts) next to its link, instead of a plain text
list, so the page matches the photo-forward look of the posts themselves.

Each item links to an Amazon search result tagged with the Associates
tracking ID (AMAZON_ASSOCIATE_TAG in .env). Until that's set to a real
approved tag, links use a clearly-marked placeholder so nothing is published
as if it were already earning commission.

Reads THEMES directly from generate_post.py so the page never drifts out of
sync with what's actually been posted - run this (or run_cycle.py, which
calls it automatically) any time THEMES changes.
"""
import json
import os
import shutil
import urllib.parse

import generate_post as gp
import fetch_images as fimg

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(SCRIPT_DIR, "docs")
OUT_PATH = os.path.join(DOCS_DIR, "index.html")
IMG_DIR = os.path.join(DOCS_DIR, "images")

PLACEHOLDER_TAG = "PLACEHOLDER-20"


def load_product_links():
    path = os.path.join(SCRIPT_DIR, "product_links.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


PRODUCT_LINKS = load_product_links()


def load_env():
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


def amazon_search_url(item, tag):
    """Direct product-page link when we've resolved a real ASIN for this
    item (see product_links.json) - falls back to a search link only for
    items not yet resolved."""
    link = PRODUCT_LINKS.get(item)
    if link:
        return f"{link['url']}?tag={tag}"
    q = urllib.parse.quote_plus(item)
    return f"https://www.amazon.com/s?k={q}&tag={tag}"


def build_html():
    env = load_env()
    tag = env.get("AMAZON_ASSOCIATE_TAG", "").strip() or PLACEHOLDER_TAG
    is_placeholder = tag == PLACEHOLDER_TAG

    os.makedirs(IMG_DIR, exist_ok=True)

    sections = []
    for theme in gp.THEMES:
        rows = []
        for item in theme["items"]:
            photo_path, _credit = fimg.get_item_image(item)
            img_html = ""
            if photo_path:
                fname = os.path.basename(photo_path)
                shutil.copyfile(photo_path, os.path.join(IMG_DIR, fname))
                img_html = f'<img src="images/{fname}" alt="{item}" loading="lazy">'
            else:
                img_html = '<div class="ph"></div>'
            rows.append(
                f'<li><a href="{amazon_search_url(item, tag)}" target="_blank" rel="noopener sponsored">'
                f'{img_html}<span>{item}</span></a></li>'
            )
        sections.append(f"""
        <section>
          <h2>{theme['title']}</h2>
          <ul>{"".join(rows)}</ul>
        </section>""")

    notice = ""
    if is_placeholder:
        notice = """
        <p class="notice">Affiliate links not yet active - Amazon Associates
        tag pending approval. Once approved, set AMAZON_ASSOCIATE_TAG in
        .env and re-run generate_bio_page.py to activate real tracking
        links across this page.</p>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cozy Home Finds - Shop Our Faves</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 640px; margin: 0 auto; padding: 24px 20px 60px; background: #faf5ee; color: #2d2826; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 4px; }}
  .tagline {{ color: #c48254; font-weight: 600; margin-top: 0; }}
  section {{ margin-top: 28px; }}
  h2 {{ font-size: 1.1rem; border-bottom: 2px solid #c48254; padding-bottom: 6px; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ border-bottom: 1px solid #e8ded2; }}
  li a {{ display: flex; align-items: center; gap: 14px; padding: 10px 0; color: #2d2826; text-decoration: none; }}
  li a:hover span {{ color: #c48254; }}
  li img, li .ph {{ width: 56px; height: 56px; border-radius: 10px; object-fit: cover; flex-shrink: 0; background: #eee6d9; }}
  li span {{ font-size: 0.98rem; }}
  .notice {{ background: #fff3e0; border: 1px solid #f0c896; padding: 12px 16px; border-radius: 8px; font-size: 0.9rem; margin-top: 24px; }}
  footer {{ margin-top: 40px; font-size: 0.8rem; color: #8a7f74; }}
</style>
</head>
<body>
<h1>Cozy Home Finds</h1>
<p class="tagline">Shop the look from every post</p>
{notice}
{"".join(sections)}
<footer>As an Amazon Associate we earn from qualifying purchases. Product photos via Pexels.</footer>
</body>
</html>
"""


def main():
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write(build_html())
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
