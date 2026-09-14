"""
Publishes a post to Instagram via the Graph API's Content Publishing flow:
1. Create a media container pointing at a publicly-hosted image URL + caption.
2. Poll the container until Instagram finishes processing it.
3. Publish the container.

Requires IG_USER_ID and IG_ACCESS_TOKEN (a long-lived token for an Instagram
Business/Creator account you've added as an Instagram Tester on your own Meta
Developer App - see instagram_affiliate/SETUP.md for the one-time setup).
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://graph.facebook.com/v21.0"


def load_env():
    env = {}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")) as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k] = v
    return env


def api_post(path, fields):
    url = f"{API_BASE}{path}"
    body = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print("ERROR body:", e.read().decode())
        raise


def api_get(path, params):
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())


def publish_post(image_url, caption):
    env = load_env()
    ig_user_id = env["IG_USER_ID"]
    token = env["IG_ACCESS_TOKEN"]

    container = api_post(f"/{ig_user_id}/media", {
        "image_url": image_url,
        "caption": caption,
        "access_token": token,
    })
    if "id" not in container:
        raise RuntimeError(f"container creation failed: {container}")
    creation_id = container["id"]

    for _ in range(15):
        status = api_get(f"/{creation_id}", {"fields": "status_code", "access_token": token})
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") == "ERROR":
            raise RuntimeError(f"container processing failed: {status}")
        time.sleep(2)
    else:
        raise RuntimeError("container never finished processing")

    result = api_post(f"/{ig_user_id}/media_publish", {
        "creation_id": creation_id,
        "access_token": token,
    })
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python3 publish_instagram.py <image_url> <caption_file>")
        sys.exit(1)
    with open(sys.argv[2]) as f:
        caption = f.read()
    res = publish_post(sys.argv[1], caption)
    print(res)
