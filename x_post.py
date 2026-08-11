"""
x_post.py
---------
Posts to X (Twitter) as @Prolink_Systems via the v2 API with OAuth 1.0a user
context - the credential flavor that never expires, so there is no refresh
flow to break. Same contract as the other channel modules: maybe_post()
never raises; it returns a truthy id on success and None on any failure,
logging the reason, so social_publish.py's guardrail decides run state.

Required secrets (GitHub Actions + C:\\Googleads\\secrets.env):
  X_API_KEY        - app "API Key" (consumer key)
  X_API_SECRET     - app "API Key Secret" (consumer secret)
  X_ACCESS_TOKEN   - account access token   (generate AFTER the app has
  X_ACCESS_SECRET  - account access secret    Read+Write permissions)

Free API tier allows ~500 posts/month - our ~20/month is comfortably inside.
Text is trimmed to X's 280-char weighted limit (URLs count as 23).

CLI smoke test:  python x_post.py "Hello from the pipeline" [image.png]
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets as _secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
TWEET_URL = "https://api.twitter.com/2/tweets"
URL_RE = re.compile(r"https?://\S+")
TCO_LEN = 23
MAX_WEIGHTED = 280


def _log(msg):
    print(f"[x] {msg}", flush=True)


def _pct(s):
    return urllib.parse.quote(str(s), safe="~-._")


def _oauth_header(method, url, body_params=None):
    """RFC 5849 OAuth 1.0a Authorization header. body_params must be included
    for form-encoded bodies; pass None for JSON or multipart bodies."""
    oauth = {
        "oauth_consumer_key": os.environ["X_API_KEY"].strip(),
        "oauth_nonce": _secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": os.environ["X_ACCESS_TOKEN"].strip(),
        "oauth_version": "1.0",
    }
    sig_params = dict(oauth)
    if body_params:
        sig_params.update(body_params)
    param_str = "&".join(
        f"{_pct(k)}={_pct(v)}" for k, v in sorted(sig_params.items())
    )
    base = "&".join([method.upper(), _pct(url), _pct(param_str)])
    key = f"{_pct(os.environ['X_API_SECRET'].strip())}&{_pct(os.environ['X_ACCESS_SECRET'].strip())}"
    sig = base64.b64encode(
        hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()
    ).decode()
    oauth["oauth_signature"] = sig
    return "OAuth " + ", ".join(
        f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth.items())
    )


def _weighted_len(text):
    plain = URL_RE.sub("", text)
    return len(plain) + len(URL_RE.findall(text)) * TCO_LEN


def fit_280(text):
    """Trim to the 280 weighted limit at a word boundary, appending an ellipsis.
    URLs are never cut mid-way (they weigh 23 regardless of display length)."""
    text = (text or "").strip()
    if _weighted_len(text) <= MAX_WEIGHTED:
        return text
    words = text.split()
    out = []
    for w in words:
        candidate = " ".join(out + [w])
        if _weighted_len(candidate) > MAX_WEIGHTED - 2:  # room for the ellipsis
            break
        out.append(w)
    return (" ".join(out)).rstrip(",.;:") + " \u2026"


def _upload_media(image_path):
    """v1.1 media upload (multipart) -> media_id string."""
    with open(image_path, "rb") as f:
        blob = f.read()
    boundary = "----prolink" + _secrets.token_hex(12)
    ext = os.path.splitext(image_path)[1].lower().lstrip(".") or "png"
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="media"; filename="card.{ext}"\r\n'.encode(),
        b"Content-Type: application/octet-stream\r\n\r\n",
        blob,
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        UPLOAD_URL, data=body, method="POST",
        headers={
            "Authorization": _oauth_header("POST", UPLOAD_URL),  # multipart: sign oauth params only
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.loads(r.read())
    mid = out.get("media_id_string") or str(out.get("media_id", ""))
    if not mid:
        raise RuntimeError(f"media upload returned no id: {out}")
    return mid


def post(text, image_path=None):
    """Post a tweet (optionally with one image). Returns the tweet id. Raises."""
    payload = {"text": fit_280(text)}
    if image_path and os.path.exists(image_path):
        payload["media"] = {"media_ids": [_upload_media(image_path)]}
    elif image_path:
        _log(f"image not found, posting text-only: {image_path}")
    req = urllib.request.Request(
        TWEET_URL, data=json.dumps(payload).encode(), method="POST",
        headers={
            "Authorization": _oauth_header("POST", TWEET_URL),  # JSON body: oauth params only
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read())
    tid = (out.get("data") or {}).get("id")
    if not tid:
        raise RuntimeError(f"tweet create returned no id: {out}")
    _log(f"Posted to X: https://x.com/Prolink_Systems/status/{tid}")
    return tid


def maybe_post(text, image_path=None):
    """Safe wrapper. Never raises; returns None on any problem."""
    if not all(os.environ.get(n, "").strip() for n in
               ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")):
        _log("Skipping X (X_API_KEY/X_API_SECRET/X_ACCESS_TOKEN/X_ACCESS_SECRET not configured).")
        return None
    if not (text or "").strip():
        _log("Skipping X (empty text).")
        return None
    try:
        return post(text, image_path)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        _log(f"WARNING: X post failed: {e.code} {detail}")
        return None
    except Exception as e:
        _log(f"WARNING: X post failed: {e}")
        return None


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print('usage: python x_post.py "TEXT" [IMAGE_PATH]')
        sys.exit(1)
    print("Result:", maybe_post(args[0], args[1] if len(args) > 1 else None))
