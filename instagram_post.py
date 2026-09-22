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

# Empty-safe: the workflows inject IG_GRAPH_BASE from a secret that may be
# unset, which passes "" -- `or` falls back to the graph.instagram.com default
# for both the missing AND empty-string cases.
GRAPH = os.environ.get("IG_GRAPH_BASE") or "https://graph.instagram.com/v21.0"


def _log(msg):
    print(f"[instagram] {msg}", flush=True)


# Meta/Instagram signatures for a dead access token. When any of these show up in
# an HTTPError body the token has expired or been invalidated -- a credential
# problem no code retry can fix -- so we say so loudly instead of dumping a raw
# 400/401 that looks like a transient blip.
_TOKEN_DEAD_MARKERS = (
    '"code":190',            # OAuthException: access token problem
    '"error_subcode":463',   # token expired
    '"error_subcode":460',   # session invalidated (password change / logout)
    '"error_subcode":467',   # token invalid (session no longer valid)
    "session has expired",
    "error validating access token",
    "access token could not be decrypted",
    "cannot parse access token",
)

_TOKEN_FIX_HINT = (
    "Instagram ACCESS TOKEN is EXPIRED or INVALID (not a transient error). "
    "Long-lived IG tokens last ~60 days and must be renewed. FIX: regenerate a "
    "new long-lived token for the Pro Link Systems Instagram account and update "
    "the GitHub repo secret IG_ACCESS_TOKEN. Instagram-login flow: Meta App "
    "Dashboard > your app > Instagram > API setup with Instagram login > generate "
    "a new token for the account (scopes: instagram_business_basic, "
    "instagram_business_content_publish). Facebook-linked flow: Graph API / "
    "Business Suite, scopes instagram_basic, instagram_content_publish, "
    "pages_read_engagement, pages_manage_posts. Then run `python "
    "instagram_post.py --refresh` periodically to extend it before it lapses."
)


def _token_looks_dead(detail):
    d = (detail or "").lower().replace(" ", "")
    hay = (detail or "").lower()
    return any(
        (m.replace(" ", "") in d) if m.startswith('"') else (m in hay)
        for m in _TOKEN_DEAD_MARKERS
    )


def _report_http_error(what, code, detail):
    """Log an HTTPError from a publish attempt, upgrading a dead-token error to a
    clear, actionable message so an expired credential can't masquerade as noise."""
    _log(f"WARNING: {what} failed: {code} {detail}")
    if _token_looks_dead(detail):
        _log("ACTION REQUIRED: " + _TOKEN_FIX_HINT)
        # Surface it as a GitHub Actions error annotation too, so the RED run says
        # exactly why without anyone digging through the raw log.
        print("::error::Instagram token expired/invalid - regenerate and update "
              "the IG_ACCESS_TOKEN GitHub secret (see instagram_post.py).",
              flush=True)


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
        _report_http_error("Instagram post", e.code, detail)
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
        _report_http_error("Instagram reel", e.code, detail)
        return None
    except Exception as e:
        _log(f"WARNING: Instagram reel failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Carousels — used by the editorial pipeline (content_studio.py). Same three-
# step Graph flow as images: child containers -> CAROUSEL container -> publish.
# ---------------------------------------------------------------------------
def post_carousel(caption, image_urls):
    """Publish a carousel (2-10 images) from public JPEG URLs."""
    if not (2 <= len(image_urls) <= 10):
        raise ValueError(f"Instagram carousels take 2-10 images, got {len(image_urls)}")
    ig_id = os.environ["IG_USER_ID"].strip()
    token = os.environ["IG_ACCESS_TOKEN"].strip()

    children = []
    for url in image_urls:
        child = _post(f"{GRAPH}/{ig_id}/media", {
            "image_url": url,
            "is_carousel_item": "true",
            "access_token": token,
        })
        children.append(child["id"])
        time.sleep(2)  # let each child finish fetching before the next

    container = _post(f"{GRAPH}/{ig_id}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption[:2200],
        "access_token": token,
    })
    time.sleep(5)

    published = _post(f"{GRAPH}/{ig_id}/media_publish", {
        "creation_id": container["id"],
        "access_token": token,
    })
    _log(f"Published carousel ({len(children)} slides) to Instagram: {published.get('id')}")
    return published.get("id")


def maybe_post_carousel(caption, image_urls):
    if not (os.environ.get("IG_USER_ID", "").strip()
            and os.environ.get("IG_ACCESS_TOKEN", "").strip()):
        _log("Skipping Instagram carousel (no IG_USER_ID/IG_ACCESS_TOKEN configured).")
        return None
    try:
        return post_carousel(caption, image_urls)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        _report_http_error("Instagram carousel", e.code, detail)
        return None
    except Exception as e:
        _log(f"WARNING: Instagram carousel failed: {e}")
        return None


def refresh_long_lived_token():
    """Extend the long-lived IG token by ~60 more days (Instagram-login flow).

    Meant to be run MANUALLY (or on a schedule) BEFORE the current token expires --
    a live token can be extended, an already-expired one cannot (you must then
    regenerate from scratch). Returns the new token string. Prints when it is safe
    to (interactive/local run); never called from the publish path, so a token
    value never lands in a CI log.
    """
    token = os.environ["IG_ACCESS_TOKEN"].strip()
    # Only the graph.instagram.com (Instagram-login) flow supports ig_refresh_token.
    if "graph.instagram.com" not in GRAPH:
        raise RuntimeError(
            "Auto-refresh only supports the Instagram-login flow "
            "(IG_GRAPH_BASE=graph.instagram.com). For the Facebook-linked flow, "
            "extend the Page token via graph.facebook.com/oauth/access_token "
            "(grant_type=fb_exchange_token) using your app id/secret."
        )
    q = urllib.parse.urlencode({
        "grant_type": "ig_refresh_token",
        "access_token": token,
    })
    data = _get(f"https://graph.instagram.com/refresh_access_token?{q}")
    days = round(int(data.get("expires_in", 0)) / 86400)
    _log(f"Refreshed IG token OK; valid ~{days} more days.")
    return data.get("access_token")


if __name__ == "__main__":
    import sys
    if "--refresh" in sys.argv:
        # Local maintenance: extend the token, then paste the printed value into
        # the IG_ACCESS_TOKEN GitHub secret. Do NOT run this in a public CI log.
        new_token = refresh_long_lived_token()
        print("\nNEW IG_ACCESS_TOKEN (update the GitHub secret with this value):")
        print(new_token)
        sys.exit(0)
    if len(sys.argv) < 3:
        print("usage: python instagram_post.py CAPTION IMAGE_OR_VIDEO_URL [--reel]")
        print("       python instagram_post.py --refresh   # extend the long-lived token")
        sys.exit(1)
    if "--reel" in sys.argv:
        print("Result:", maybe_post_reel(sys.argv[1], sys.argv[2]))
    else:
        print("Result:", maybe_post(sys.argv[1], sys.argv[2]))
