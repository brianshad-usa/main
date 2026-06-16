"""
gbp_post.py
-----------
Publishes a "What's New" update to the Pro Link Systems Google Business Profile
using the Google My Business API v4.

Design goals (same as linkedin_post.py):
  * NEVER break the generation pipeline. If anything goes wrong the caller
    gets None back, not an exception.
  * Refresh the short-lived Google access token on every run from the
    long-lived refresh token (Google refresh tokens don't expire unless
    the user revokes them or the app is idle for 6 months).

Required GitHub secrets:
  GBP_CLIENT_ID      - OAuth 2.0 "Desktop app" client ID from Google Cloud
  GBP_CLIENT_SECRET  - matching client secret
  GBP_REFRESH_TOKEN  - obtained once via gbp_auth.py
  GBP_ACCOUNT_ID     - numeric Google Business Profile account id (see GBP_SETUP.md)
  GBP_LOCATION_ID    - numeric location id (see GBP_SETUP.md)

Optional:
  GBP_ACCESS_TOKEN   - fallback if refresh fails (short-lived, ~1 hour)
"""

import os
import json
import urllib.parse
import urllib.request
import urllib.error

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GBP_API_BASE     = "https://mybusiness.googleapis.com/v4"

VALID_CTA_TYPES = {
    "BOOK_APPOINTMENT", "CALL", "LEARN_MORE",
    "ORDER", "SHOP", "SIGN_UP",
}


def _log(msg):
    print(f"[gbp] {msg}", flush=True)


def _refresh_access_token(client_id, client_secret, refresh_token):
    data = urllib.parse.urlencode({
        "grant_type":    "refresh_token",
        "refresh_token": refresh_token,
        "client_id":     client_id,
        "client_secret": client_secret,
    }).encode("utf-8")
    req = urllib.request.Request(
        GOOGLE_TOKEN_URL, data=data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    access = payload.get("access_token")
    if not access:
        raise RuntimeError(f"No access_token in Google response: {payload}")
    return access


def _resolve_access_token():
    client_id     = os.environ.get("GBP_CLIENT_ID",     "").strip()
    client_secret = os.environ.get("GBP_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("GBP_REFRESH_TOKEN", "").strip()
    access_token  = os.environ.get("GBP_ACCESS_TOKEN",  "").strip()

    if client_id and client_secret and refresh_token:
        try:
            _log("Refreshing Google access token...")
            return _refresh_access_token(client_id, client_secret, refresh_token)
        except Exception as e:
            _log(f"Refresh failed ({e}). Trying GBP_ACCESS_TOKEN fallback.")

    if access_token:
        _log("Using GBP_ACCESS_TOKEN directly (short-lived).")
        return access_token

    raise RuntimeError(
        "No GBP credentials configured. "
        "Set GBP_CLIENT_ID, GBP_CLIENT_SECRET, GBP_REFRESH_TOKEN."
    )


def post_update(summary, cta_type="LEARN_MORE", cta_url=None):
    """
    Publish a STANDARD (What's New) post to the GBP location.
    Returns the post resource name on success. Raises on failure.

    summary   : post text, max 1500 chars (we trim automatically)
    cta_type  : one of BOOK_APPOINTMENT, CALL, LEARN_MORE, ORDER, SHOP, SIGN_UP
    cta_url   : required when cta_type is not CALL
    """
    account_id  = os.environ.get("GBP_ACCOUNT_ID",  "").strip()
    location_id = os.environ.get("GBP_LOCATION_ID", "").strip()
    if not account_id or not location_id:
        raise RuntimeError(
            "GBP_ACCOUNT_ID and GBP_LOCATION_ID must be set as GitHub secrets."
        )

    token = _resolve_access_token()

    body = {
        "summary":      summary[:1500],
        "topicType":    "STANDARD",
        "languageCode": "en-US",
    }
    if cta_type in VALID_CTA_TYPES and (cta_url or cta_type == "CALL"):
        body["callToAction"] = {"actionType": cta_type}
        if cta_url:
            body["callToAction"]["url"] = cta_url

    endpoint = (
        f"{GBP_API_BASE}/accounts/{account_id}"
        f"/locations/{location_id}/localPosts"
    )
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result    = json.loads(resp.read().decode("utf-8"))
            post_name = result.get("name", "unknown")
            _log(f"Published GBP post: {post_name}")
            return post_name
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"GBP API {e.code}: {detail}") from None


def maybe_post(summary, cta_type="LEARN_MORE", cta_url=None):
    """
    Safe wrapper for the automation pipeline. Never raises.
    Returns the post name on success or None on any failure.
    """
    if not os.environ.get("GBP_REFRESH_TOKEN", "").strip():
        if not os.environ.get("GBP_ACCESS_TOKEN", "").strip():
            _log("Skipping GBP post (no GBP_REFRESH_TOKEN/ACCESS_TOKEN configured).")
            return None
    try:
        return post_update(summary, cta_type, cta_url)
    except Exception as e:
        _log(f"WARNING: GBP post failed, pipeline unaffected. Reason: {e}")
        return None


if __name__ == "__main__":
    # Manual smoke test:
    #   python gbp_post.py "Test post text" LEARN_MORE https://prolinksystems.com
    import sys
    args = sys.argv[1:]
    if len(args) < 1:
        print("usage: python gbp_post.py SUMMARY [CTA_TYPE] [CTA_URL]")
        sys.exit(1)
    summary  = args[0]
    cta_type = args[1] if len(args) > 1 else "LEARN_MORE"
    cta_url  = args[2] if len(args) > 2 else None
    result   = maybe_post(summary, cta_type, cta_url)
    print("Result:", result)
