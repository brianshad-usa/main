"""
linkedin_post.py
----------------
Publishes a blog post to the Pro Link Systems company LinkedIn Page using the
LinkedIn Posts API (Community Management API).

Design goals:
  * NEVER break the blog pipeline. If anything goes wrong (missing secrets,
    expired token, LinkedIn outage), we log a clear warning and return None
    instead of raising. The blog post is already written + committed by then.
  * Refresh the access token on every run from a long-lived refresh token
    (refresh tokens last ~365 days), so a monthly cron keeps working for a
    year before you have to re-authorize.

Required environment variables (set as GitHub Actions secrets):
  LINKEDIN_CLIENT_ID        - from your LinkedIn developer app
  LINKEDIN_CLIENT_SECRET    - from your LinkedIn developer app
  LINKEDIN_ORG_ID           - numeric Company Page id, e.g. 12345678
  One of:
    LINKEDIN_REFRESH_TOKEN  - preferred; we exchange it for a fresh access token
    LINKEDIN_ACCESS_TOKEN   - fallback; used directly (expires in ~60 days)

Optional:
  LINKEDIN_API_VERSION      - LinkedIn-Version header, format YYYYMM
                              (defaults to 202506; bump if LinkedIn deprecates it)
"""

import os
import json
import urllib.parse
import urllib.request
import urllib.error

TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
POSTS_URL = "https://api.linkedin.com/rest/posts"
DEFAULT_API_VERSION = "202506"

# Characters the LinkedIn Posts API treats as reserved in the "commentary"
# (post text) field. They must be backslash-escaped to render literally.
# We deliberately leave '#' UNescaped so hashtags still work.
_RESERVED = set("\\<>~_*[]()|{}@")


def _log(msg):
    print(f"[linkedin] {msg}", flush=True)


def _escape_commentary(text):
    """Escape LinkedIn-reserved characters so prose renders literally.
    Hashtags ('#word') are preserved on purpose."""
    out = []
    for ch in text:
        if ch in _RESERVED:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def _http_post_form(url, fields):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _refresh_access_token(client_id, client_secret, refresh_token):
    """Exchange a refresh token for a fresh 60-day access token."""
    payload = _http_post_form(
        TOKEN_URL,
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    access = payload.get("access_token")
    if not access:
        raise RuntimeError(f"No access_token in refresh response: {payload}")

    # LinkedIn may return a rotated refresh token. We can't write it back to
    # GitHub secrets automatically, so surface it loudly if it changed.
    new_refresh = payload.get("refresh_token")
    if new_refresh and new_refresh != refresh_token:
        _log(
            "NOTE: LinkedIn returned a NEW refresh token. Update the "
            "LINKEDIN_REFRESH_TOKEN GitHub secret with the value below to "
            "avoid re-authorizing sooner than necessary:"
        )
        _log(new_refresh)

    rt_days = payload.get("refresh_token_expires_in")
    if rt_days:
        _log(f"Refresh token valid for ~{int(rt_days) // 86400} more days.")
    return access


def _resolve_access_token():
    """Get a usable access token: refresh-token flow preferred, else the
    stored access token as a fallback. Returns None if nothing is configured."""
    client_id = os.environ.get("LINKEDIN_CLIENT_ID", "").strip()
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("LINKEDIN_REFRESH_TOKEN", "").strip()
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()

    if client_id and client_secret and refresh_token:
        try:
            _log("Refreshing access token via refresh token...")
            return _refresh_access_token(client_id, client_secret, refresh_token)
        except Exception as e:
            _log(f"Refresh failed ({e}). Falling back to LINKEDIN_ACCESS_TOKEN if set.")

    if access_token:
        _log("Using stored LINKEDIN_ACCESS_TOKEN (expires ~60 days after issue).")
        return access_token

    return None


def _build_post_body(org_urn, commentary, url, title, description):
    return {
        "author": org_urn,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {
            "article": {
                "source": url,
                "title": title[:200],
                "description": (description or "")[:256],
            }
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }


def post_article(title, url, summary, caption):
    """Publish an article share to the company page. Returns the post URN on
    success. Raises on failure (caller decides how to handle)."""
    # Defaults to the Pro Link Systems Company Page id (3574099). Override with
    # the LINKEDIN_ORG_ID secret only if the page ever changes.
    org_id = os.environ.get("LINKEDIN_ORG_ID", "").strip() or "3574099"
    # Accept either a bare numeric id or a full URN.
    org_urn = org_id if org_id.startswith("urn:") else f"urn:li:organization:{org_id}"

    token = _resolve_access_token()
    if not token:
        raise RuntimeError(
            "No LinkedIn credentials found "
            "(need LINKEDIN_REFRESH_TOKEN or LINKEDIN_ACCESS_TOKEN)."
        )

    api_version = os.environ.get("LINKEDIN_API_VERSION", DEFAULT_API_VERSION).strip()

    commentary = _escape_commentary((caption or title).strip())[:2900]
    body = _build_post_body(org_urn, commentary, url, title, summary)

    req = urllib.request.Request(
        POSTS_URL,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": api_version,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            post_id = resp.headers.get("x-restli-id") or resp.headers.get("x-linkedin-id")
            _log(f"Published to LinkedIn. Post id: {post_id}")
            return post_id
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"LinkedIn API {e.code}: {detail}") from None


def maybe_post(title, url, summary, caption):
    """Safe wrapper for the blog pipeline. Never raises -- logs and returns
    None on any problem so the blog publish is never blocked."""
    has_creds = (
        os.environ.get("LINKEDIN_REFRESH_TOKEN", "").strip()
        or os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    )
    if not has_creds:
        _log("Skipping LinkedIn post (no LINKEDIN_REFRESH_TOKEN/ACCESS_TOKEN configured).")
        return None
    try:
        return post_article(title, url, summary, caption)
    except Exception as e:
        _log(f"WARNING: LinkedIn post failed, blog publish unaffected. Reason: {e}")
        return None


# ---------------------------------------------------------------------------
# Image posts (used by the social syndication pipeline — social_publish.py)
# ---------------------------------------------------------------------------
IMAGES_URL = "https://api.linkedin.com/rest/images"


def _upload_image(token, org_urn, image_path, api_version):
    """Register + upload an image to LinkedIn; return its 'urn:li:image:...' id."""
    init_req = urllib.request.Request(
        IMAGES_URL + "?action=initializeUpload",
        data=json.dumps({"initializeUploadRequest": {"owner": org_urn}}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": api_version,
        },
    )
    with urllib.request.urlopen(init_req, timeout=30) as resp:
        value = json.loads(resp.read().decode("utf-8"))["value"]
    upload_url = value["uploadUrl"]
    image_urn = value["image"]

    with open(image_path, "rb") as fh:
        img_bytes = fh.read()
    put_req = urllib.request.Request(
        upload_url, data=img_bytes, method="PUT",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "image/png"},
    )
    with urllib.request.urlopen(put_req, timeout=60) as resp:
        resp.read()
    return image_urn


def post_image(commentary, image_path, alt_text="Pro Link Systems"):
    """Publish an image post to the company page. Returns the post URN. Raises on failure."""
    org_id = os.environ.get("LINKEDIN_ORG_ID", "").strip() or "3574099"
    org_urn = org_id if org_id.startswith("urn:") else f"urn:li:organization:{org_id}"

    token = _resolve_access_token()
    if not token:
        raise RuntimeError("No LinkedIn credentials found.")

    api_version = os.environ.get("LINKEDIN_API_VERSION", DEFAULT_API_VERSION).strip()
    image_urn = _upload_image(token, org_urn, image_path, api_version)

    body = {
        "author": org_urn,
        "commentary": _escape_commentary((commentary or "").strip())[:2900],
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {"media": {"id": image_urn, "altText": (alt_text or "")[:300]}},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    req = urllib.request.Request(
        POSTS_URL,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": api_version,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            post_id = resp.headers.get("x-restli-id") or resp.headers.get("x-linkedin-id")
            _log(f"Published image post to LinkedIn. Post id: {post_id}")
            return post_id
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"LinkedIn API {e.code}: {detail}") from None


def maybe_post_image(commentary, image_path, alt_text="Pro Link Systems"):
    """Safe wrapper for the social pipeline. Never raises; returns None on any problem."""
    has_creds = (
        os.environ.get("LINKEDIN_REFRESH_TOKEN", "").strip()
        or os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    )
    if not has_creds:
        _log("Skipping LinkedIn image post (no LINKEDIN_REFRESH_TOKEN/ACCESS_TOKEN configured).")
        return None
    if not os.path.exists(image_path):
        _log(f"Skipping LinkedIn image post (image not found: {image_path}).")
        return None
    try:
        return post_image(commentary, image_path, alt_text)
    except Exception as e:
        _log(f"WARNING: LinkedIn image post failed. Reason: {e}")
        return None


if __name__ == "__main__":
    # Manual smoke test:
    #   python linkedin_post.py "Test Title" "https://prolinksystems.com/blog/x.html" "Summary" "Caption #ManagedIT"
    import sys

    args = sys.argv[1:]
    if len(args) < 3:
        print("usage: python linkedin_post.py TITLE URL SUMMARY [CAPTION]")
        sys.exit(1)
    t, u, s = args[0], args[1], args[2]
    c = args[3] if len(args) > 3 else None
    result = maybe_post(t, u, s, c)
    print("Result:", result)
