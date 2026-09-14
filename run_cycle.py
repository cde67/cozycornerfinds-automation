"""
One automation cycle for Cozy Corner Finds:
1. Pick a theme not posted recently (tracks state in posted_log.json).
2. Generate the branded graphic + caption.
3. Push the image to the public GitHub repo (so Instagram's API can fetch it
   via a raw.githubusercontent.com URL - Instagram requires a public URL, not
   a local file, same constraint as Pinterest's bulk uploader).
4. Publish it to Instagram via the Graph API.

Requires GITHUB_TOKEN (fine-grained PAT scoped to this repo, Contents: Read
and write) and IG_USER_ID + IG_ACCESS_TOKEN in .env.
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_post as gp
import publish_instagram as pi

GITHUB_REPO = "cde67/cozycornerfinds-automation"
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/posts"


def load_env():
    env = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k] = v
    return env


def posted_log_path(base):
    return os.path.join(base, "posted_log.json")


def load_posted(base):
    p = posted_log_path(base)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return {"posted_titles": []}


def save_posted(base, data):
    with open(posted_log_path(base), "w") as f:
        json.dump(data, f, indent=2)


def pick_theme(posted_titles):
    unposted = [t for t in gp.THEMES if t["title"] not in posted_titles]
    if not unposted:
        return None
    import random
    return random.choice(unposted)


def sync_to_github(base):
    env = load_env()
    token = env.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set - skipping GitHub sync (image won't be publicly hosted).")
        return False

    remote = f"https://x-access-token:{token}@github.com/{GITHUB_REPO}.git"

    def run(cmd, **kw):
        return subprocess.run(cmd, cwd=base, capture_output=True, text=True, **kw)

    if not os.path.isdir(os.path.join(base, ".git")):
        run(["git", "init"])
        run(["git", "config", "user.name", "Cozy Corner Automation"])
        run(["git", "config", "user.email", "automation@cozycornerfinds.local"])
        run(["git", "remote", "add", "origin", remote])
        fetch = run(["git", "fetch", "origin", "main"])
        if fetch.returncode == 0:
            run(["git", "update-ref", "refs/heads/main", "origin/main"])
            run(["git", "symbolic-ref", "HEAD", "refs/heads/main"])
            run(["git", "reset"])
        else:
            run(["git", "checkout", "-B", "main"])
    else:
        run(["git", "remote", "set-url", "origin", remote])
        run(["git", "fetch", "origin", "main"])
        run(["git", "merge", "origin/main", "--no-edit"])

    run(["git", "add", "posts"])
    commit = run(["git", "commit", "-m", "Automated cycle: new post image"])
    if commit.returncode != 0:
        print("Nothing new to commit.")
        return True
    push = run(["git", "push", "origin", "main"])
    if push.returncode != 0:
        print(f"GitHub push failed:\n{push.stderr}")
        return False
    return True


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    posted = load_posted(base)

    theme = pick_theme(posted["posted_titles"])
    if theme is None:
        print("All themes posted - add more to generate_post.THEMES before the next cycle.")
        return

    slug = theme["title"].lower().replace(" ", "_").replace("$", "").replace("-", "")
    img_path = os.path.join(base, "posts", f"{slug}.png")
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    gp.make_post(theme, img_path)
    caption = gp.caption_for(theme)
    print(f"Generated: {img_path}")

    if not sync_to_github(base):
        print("Could not host image publicly - stopping before Instagram publish.")
        return

    image_url = f"{RAW_BASE}/{slug}.png"
    time.sleep(3)  # let raw.githubusercontent.com catch up
    try:
        result = pi.publish_post(image_url, caption)
    except Exception as e:
        print(f"Instagram publish failed: {e}")
        return

    print(f"Published to Instagram: {result}")
    posted["posted_titles"].append(theme["title"])
    save_posted(base, posted)
    print(f"CYCLE COMPLETE: posted '{theme['title']}'. {len(gp.THEMES) - len(posted['posted_titles'])} themes remaining.")


if __name__ == "__main__":
    main()
