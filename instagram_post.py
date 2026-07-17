"""
instagram_post.py
-----------------
Publishes an image + caption to the Pro Link Systems Instagram BUSINESS account
via the Instagram Graph API. Two steps: create a media container from a public
image URL, then publish it.

Same safety contract as gbp_post / linkedin_post: maybe_post() never raises, and
skips cleanly if credentials aren't configured yet (so it stays dormant until you
finish the Meta setup).

Requirements (Meta side, one-time):
  * The IG account must be a Professional (Business or Creator) account.
  * Default path = "Instagram API setup with Instagram login": generate the token
    by logging into the Instagram account directly in the app dashboard - no Graph
    API Explorer and no Facebook Page / developer-role wrangling.

Required GitHub secrets (set when ready):
  IG_USER_ID       - the Instagram account id (shown by the dashboard token
                     generator, or from GET graph.instagram.com/me?fields=user_id)
  IG_ACCESS_TOKEN  - the Instagram access token from the dashboard generator
  IG_GRAPH_BASE    - optional; defaults to https://graph.instagram.com/v21.0.
                     Set to https://graph.facebook.com/v21.0 only if you instead
                     use the older Facebook-login / Page-linked flow.

Note: Instagram fetches the image itself, so image_url MUST be publicly reachable
and a JPEG. Tokens last ~60 days; refresh before expiry.
"""

import os
import json
import time
import urllib.parse
import urllib.request
import urllib.error

GRAPH = os.environ.get("IG_GRAPH_BASE", "https://graph.instagram.com/v21.0")


def _log(msg):
    print(f"[instagram] {msg}", flush=True)


def _post(url, fields):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_image(caption, image_url):
    ig_id = os.environ["IG_USER_ID"].strip()
    token = os.environ["IG_ACCESS_TOKEN"].strip()

    container = _post(f"{GRAPH}/{ig_id}/media", {
        "image_url": image_url,
        "caption": caption[:2200],
        "access_token": token,
    })
    creation_id = container["id"]

    # Give Instagram a moment to fetch + process the image before publishing.
    time.sleep(5)

    published = _post(f"{GRAPH}/{ig_id}/media_publish", {
        "creation_id": creation_id,
        "access_token": token,
    })
    _log(f"Published to Instagram: {published.get('id')}")
    return published.get("id")


def maybe_post(caption, image_url):
    if not (os.environ.get("IG_USER_ID", "").strip()
            and os.environ.get("IG_ACCESS_TOKEN", "").strip()):
        _log("Skipping Instagram post (no IG_USER_ID/IG_ACCESS_TOKEN configured).")
        return None
    try:
        return post_image(caption, image_url)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        _log(f"WARNING: Instagram post failed: {e.code} {detail}")
        return None
    except Exception as e:
        _log(f"WARNING: Instagram post failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Reels (video) — used by the video syndication pipeline (video_publish.py)
# ---------------------------------------------------------------------------
def _get(url):
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_reel(caption, video_url):
    """Publish a Reel from a public video URL. Instagram fetches + transcodes it
    asynchronously, so we poll the container until it's FINISHED before publishing."""
    ig_id = os.environ["IG_USER_ID"].strip()
    token = os.environ["IG_ACCESS_TOKEN"].strip()

    container = _post(f"{GRAPH}/{ig_id}/media", {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption[:2200],
        "share_to_feed": "true",
        "access_token": token,
    })
    creation_id = container["id"]

    # Poll processing status: up to ~6 minutes (Reels transcode can be slow).
    finished = False
    for _ in range(45):
        time.sleep(8)
        status = _get(
            f"{GRAPH}/{creation_id}?fields=status_code,status&"
            + urllib.parse.urlencode({"access_token": token})
        )
        code = status.get("status_code")
        if code == "FINISHED":
            finished = True
            break
        if code == "ERROR":
            raise RuntimeError(f"Instagram failed to process the reel: {status.get('status', status)}")
        _log(f"reel processing... ({code})")
    if not finished:
        raise RuntimeError("Instagram reel processing timed out (still not FINISHED).")

    published = _post(f"{GRAPH}/{ig_id}/media_publish", {
        "creation_id": creation_id,
        "access_token": token,
    })
    _log(f"Published reel to Instagram: {published.get('id')}")
    return published.get("id")


def maybe_post_reel(caption, video_url):
    if not (os.environ.get("IG_USER_ID", "").strip()
            and os.environ.get("IG_ACCESS_TOKEN", "").strip()):
        _log("Skipping Instagram reel (no IG_USER_ID/IG_ACCESS_TOKEN configured).")
        return None
    try:
        return post_reel(caption, video_url)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        _log(f"WARNING: Instagram reel failed: {e.code} {detail}")
        return None
    except Exception as e:
        _log(f"WARNING: Instagram reel failed: {e}")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: python instagram_post.py CAPTION IMAGE_OR_VIDEO_URL [--reel]")
        sys.exit(1)
    if "--reel" in sys.argv:
        print("Result:", maybe_post_reel(sys.argv[1], sys.argv[2]))
    else:
        print("Result:", maybe_post(sys.argv[1], sys.argv[2]))
