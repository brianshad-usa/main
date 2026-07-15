"""
facebook_post.py
----------------
Publishes an image + caption to the Pro Link Systems Facebook PAGE via the
Graph API (POST /{page-id}/photos).

Same safety contract as the other publishers: maybe_post() never raises and
skips cleanly when credentials aren't configured yet (stays dormant until you
finish the Facebook setup).

Required GitHub secrets (set when ready):
  FB_PAGE_ID            - the Facebook Page's numeric id (from GET me/accounts)
  FB_PAGE_ACCESS_TOKEN  - a long-lived PAGE access token with pages_manage_posts
                          (a Page token derived from a long-lived user token does
                           not expire unless revoked)

Notes:
  * Facebook fetches the image itself, so image_url must be publicly reachable.
  * Uses the "Pro Link Social" Meta app you already created for Instagram --
    just add the pages_manage_posts + pages_read_engagement permissions.
"""

import os
import json
import urllib.parse
import urllib.request
import urllib.error

GRAPH = os.environ.get("FB_GRAPH_BASE", "https://graph.facebook.com/v21.0")


def _log(msg):
    print(f"[facebook] {msg}", flush=True)


def _post(url, fields):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_image(caption, image_url):
    page_id = os.environ["FB_PAGE_ID"].strip()
    token = os.environ["FB_PAGE_ACCESS_TOKEN"].strip()
    res = _post(f"{GRAPH}/{page_id}/photos", {
        "url": image_url,
        "caption": caption[:5000],
        "access_token": token,
    })
    post_id = res.get("post_id") or res.get("id")
    _log(f"Published to Facebook: {post_id}")
    return post_id


def maybe_post(caption, image_url):
    if not (os.environ.get("FB_PAGE_ID", "").strip()
            and os.environ.get("FB_PAGE_ACCESS_TOKEN", "").strip()):
        _log("Skipping Facebook post (no FB_PAGE_ID/FB_PAGE_ACCESS_TOKEN configured).")
        return None
    try:
        return post_image(caption, image_url)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        _log(f"WARNING: Facebook post failed: {e.code} {detail}")
        return None
    except Exception as e:
        _log(f"WARNING: Facebook post failed: {e}")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: python facebook_post.py CAPTION IMAGE_URL")
        sys.exit(1)
    print("Result:", maybe_post(sys.argv[1], sys.argv[2]))
