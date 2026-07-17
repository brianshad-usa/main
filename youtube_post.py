"""
youtube_post.py
---------------
Uploads a video to the Pro Link Systems YouTube channel via the YouTube Data
API v3 (resumable upload), using pure urllib -- no SDK, matching the rest of
the pipeline.

Same safety contract as the other publishers: maybe_post() never raises and
skips cleanly when credentials aren't configured yet.

Required GitHub secrets (set after running youtube_auth.py once):
  YT_CLIENT_ID       - Google OAuth client id (Desktop app)
  YT_CLIENT_SECRET   - Google OAuth client secret
  YT_REFRESH_TOKEN   - long-lived refresh token from youtube_auth.py
Optional:
  YT_ACCESS_TOKEN    - fallback access token (expires ~1h)
  YT_PRIVACY         - public | unlisted | private   (default: public)
  YT_CATEGORY_ID     - numeric category id            (default: 28 = Science & Technology)

Returns a dict {"id", "url", "privacy"} on success, None on any failure.
"""

import os
import json
import urllib.parse
import urllib.request
import urllib.error

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos"
    "?uploadType=resumable&part=snippet,status"
)


def _log(msg):
    print(f"[youtube] {msg}", flush=True)


def _resolve_access_token():
    """Refresh-token flow preferred; fall back to a stored access token."""
    cid = os.environ.get("YT_CLIENT_ID", "").strip()
    secret = os.environ.get("YT_CLIENT_SECRET", "").strip()
    refresh = os.environ.get("YT_REFRESH_TOKEN", "").strip()
    access = os.environ.get("YT_ACCESS_TOKEN", "").strip()

    if cid and secret and refresh:
        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "client_id": cid,
            "client_secret": secret,
        }).encode("utf-8")
        req = urllib.request.Request(
            TOKEN_URL, data=data, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            tok = payload.get("access_token")
            if tok:
                return tok
            _log(f"No access_token in refresh response: {payload}")
        except Exception as e:
            _log(f"Token refresh failed ({e}). Falling back to YT_ACCESS_TOKEN if set.")

    if access:
        _log("Using stored YT_ACCESS_TOKEN (expires ~1h after issue).")
        return access
    return None


def post_video(video_path, title, description, tags=None):
    """Upload a video. Returns {"id","url","privacy"}. Raises on failure."""
    token = _resolve_access_token()
    if not token:
        raise RuntimeError("No YouTube credentials found (need YT_REFRESH_TOKEN or YT_ACCESS_TOKEN).")

    privacy = (os.environ.get("YT_PRIVACY", "").strip() or "public").lower()
    category = os.environ.get("YT_CATEGORY_ID", "").strip() or "28"  # Science & Technology

    metadata = {
        "snippet": {
            "title": (title or "Pro Link Systems")[:100],
            "description": (description or "")[:5000],
            "tags": (tags or [])[:30],
            "categoryId": category,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    size = os.path.getsize(video_path)

    # 1) Open a resumable upload session -> the response Location is the upload URL.
    init = urllib.request.Request(
        UPLOAD_URL,
        data=json.dumps(metadata).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(size),
            "X-Upload-Content-Type": "video/*",
        },
    )
    try:
        with urllib.request.urlopen(init, timeout=60) as resp:
            session_url = resp.headers.get("Location")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"YouTube init {e.code}: {detail}") from None
    if not session_url:
        raise RuntimeError("YouTube did not return a resumable session URL.")

    # 2) Upload the bytes in a single PUT (fine for typical short-form videos).
    with open(video_path, "rb") as fh:
        body = fh.read()
    put = urllib.request.Request(
        session_url,
        data=body,
        method="PUT",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "video/*", "Content-Length": str(size)},
    )
    try:
        with urllib.request.urlopen(put, timeout=600) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"YouTube upload {e.code}: {detail}") from None

    vid = result.get("id")
    got_privacy = (result.get("status") or {}).get("privacyStatus", privacy)
    if not vid:
        raise RuntimeError(f"YouTube upload returned no id: {result}")
    if got_privacy != privacy:
        _log(
            f"NOTE: requested privacy '{privacy}' but YouTube set '{got_privacy}'. "
            "Unverified API projects can force uploads to private -- verify the "
            "Google Cloud project (or use YT_PRIVACY=unlisted) for public posts."
        )
    _log(f"Uploaded to YouTube: https://youtu.be/{vid} (privacy: {got_privacy})")
    return {"id": vid, "url": f"https://youtu.be/{vid}", "privacy": got_privacy}


def maybe_post(video_path, title, description, tags=None):
    """Safe wrapper. Never raises; returns None on any problem."""
    if not (os.environ.get("YT_CLIENT_ID", "").strip()
            and os.environ.get("YT_CLIENT_SECRET", "").strip()
            and os.environ.get("YT_REFRESH_TOKEN", "").strip()) \
            and not os.environ.get("YT_ACCESS_TOKEN", "").strip():
        _log("Skipping YouTube upload (no YT_CLIENT_ID/YT_CLIENT_SECRET/YT_REFRESH_TOKEN configured).")
        return None
    if not os.path.exists(video_path):
        _log(f"Skipping YouTube upload (video not found: {video_path}).")
        return None
    try:
        return post_video(video_path, title, description, tags)
    except Exception as e:
        _log(f"WARNING: YouTube upload failed. Reason: {e}")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: python youtube_post.py VIDEO_PATH TITLE [DESCRIPTION]")
        sys.exit(1)
    vp, t = sys.argv[1], sys.argv[2]
    d = sys.argv[3] if len(sys.argv) > 3 else ""
    print("Result:", maybe_post(vp, t, d, ["Managed IT", "Cybersecurity", "Los Angeles"]))
