"""
instagram_auth.py  --  ONE-TIME local setup / re-mint helper
------------------------------------------------------------
Runs the Instagram OAuth flow ("Instagram API setup with Instagram login")
on your own machine to mint a fresh LONG-LIVED Instagram access token
(~60 days). You run this whenever you need a brand-new token -- e.g. the old
one already expired and can no longer be extended -- then paste the printed
value into the GitHub repo secret IG_ACCESS_TOKEN. Same spirit as
linkedin_auth.py / youtube_auth.py.

WHY THIS EXISTS: instagram_post.py --refresh can only EXTEND a still-valid
token. Once a token has fully lapsed it cannot be refreshed; you must mint a
new one from scratch. This script does that in one shot.

PREREQUISITES (Meta App Dashboard, one-time):
  1. A Meta app with the Instagram product added, using
     "Instagram API setup with Instagram login".
  2. The IG account must be a Professional (Business or Creator) account.
  3. In that Instagram setup panel, under "Business login settings" (OAuth
     redirect URIs), add this EXACT redirect URI:
        http://localhost:8000/callback
  4. Have your Instagram App ID and Instagram App Secret handy (same panel).
     (These are the Instagram app credentials, not the top-level Facebook
     App ID/Secret -- use the ones shown in the Instagram login setup box.)

USAGE:
  Windows PowerShell:
    $env:IG_APP_ID="xxxx"; $env:IG_APP_SECRET="yyyy"; python instagram_auth.py
  macOS/Linux:
    IG_APP_ID=xxxx IG_APP_SECRET=yyyy python instagram_auth.py

  (If you don't set the env vars, the script prompts for them. It also accepts
  the alternate names IG_CLIENT_ID / IG_CLIENT_SECRET.)

A browser window opens; approve the permissions; control returns here and the
new long-lived token is printed. If the browser can't reach localhost, the
script falls back to asking you to paste the redirected URL.
"""

import os
import sys
import json
import urllib.parse
import urllib.request
import urllib.error
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

REDIRECT_PORT = 8000
REDIRECT_PATH = "/callback"
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}{REDIRECT_PATH}"

# Instagram-login (graph.instagram.com) OAuth endpoints.
AUTH_URL = "https://www.instagram.com/oauth/authorize"
SHORT_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
LONG_TOKEN_URL = "https://graph.instagram.com/access_token"

# Scopes for the publishing pipeline. In the Instagram-login flow the scope
# list is COMMA-separated (unlike the Facebook-login flow).
SCOPES = "instagram_business_basic,instagram_business_content_publish"
STATE = "prolink_instagram_setup"

_captured = {"code": None, "error": None}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != REDIRECT_PATH:
            self.send_response(404)
            self.end_headers()
            return
        qs = urllib.parse.parse_qs(parsed.query)
        _captured["code"] = qs.get("code", [None])[0]
        _captured["error"] = qs.get("error_description", qs.get("error", [None]))[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if _captured["code"]:
            msg = "<h2>Success.</h2><p>You can close this tab and return to the terminal.</p>"
        else:
            msg = f"<h2>Authorization failed.</h2><p>{_captured['error']}</p>"
        self.wfile.write(f"<html><body style='font-family:sans-serif'>{msg}</body></html>".encode())

    def log_message(self, *args):
        pass  # silence default request logging


def _get_creds():
    cid = (os.environ.get("IG_APP_ID") or os.environ.get("IG_CLIENT_ID") or "").strip()
    secret = (os.environ.get("IG_APP_SECRET") or os.environ.get("IG_CLIENT_SECRET") or "").strip()
    if not cid:
        cid = input("Instagram App ID: ").strip()
    if not secret:
        secret = input("Instagram App Secret: ").strip()
    if not cid or not secret:
        print("Instagram App ID and App Secret are required.")
        sys.exit(1)
    return cid, secret


def _exchange_code_for_short_token(cid, secret, code):
    """Trade the authorization code for a SHORT-lived Instagram token."""
    data = urllib.parse.urlencode(
        {
            "client_id": cid,
            "client_secret": secret,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": code,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        SHORT_TOKEN_URL,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    # Instagram has returned this either flat or wrapped in a "data" list over
    # time -- handle both shapes.
    if isinstance(payload, dict) and payload.get("data"):
        payload = payload["data"][0]
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"No short-lived access_token in response: {payload}")
    return token


def _exchange_short_for_long(secret, short_token):
    """Trade the short-lived token for a LONG-lived (~60 day) token."""
    q = urllib.parse.urlencode(
        {
            "grant_type": "ig_exchange_token",
            "client_secret": secret,
            "access_token": short_token,
        }
    )
    with urllib.request.urlopen(f"{LONG_TOKEN_URL}?{q}", timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"No long-lived access_token in response: {payload}")
    return token, payload.get("expires_in")


def _read_body(e):
    if hasattr(e, "read"):
        try:
            return e.read().decode("utf-8", "replace")
        except Exception:
            return ""
    return ""


def main():
    cid, secret = _get_creds()

    auth_link = AUTH_URL + "?" + urllib.parse.urlencode(
        {
            "client_id": cid,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPES,
            "state": STATE,
        }
    )

    print("\nOpening your browser to authorize. If it doesn't open, paste this URL:\n")
    print(auth_link + "\n")
    try:
        webbrowser.open(auth_link)
    except Exception:
        pass

    code = None
    try:
        server = HTTPServer(("localhost", REDIRECT_PORT), _Handler)
        print(f"Waiting for the Instagram redirect on {REDIRECT_URI} ...")
        server.handle_request()  # serves exactly one request (the callback)
        if _captured["error"]:
            print(f"\nAuthorization error from Instagram: {_captured['error']}")
            sys.exit(1)
        code = _captured["code"]
    except OSError as e:
        print(f"\nCould not start local server on port {REDIRECT_PORT} ({e}).")
        pasted = input(
            "After approving in the browser you'll land on a localhost page that "
            "won't load.\nCopy that full URL from the address bar and paste it here:\n"
        ).strip()
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
        code = qs.get("code", [None])[0]

    if not code:
        print("No authorization code received. Aborting.")
        sys.exit(1)

    # Instagram appends a "#_" fragment to the code on the redirect; strip it.
    code = code.split("#")[0]

    print("\nExchanging authorization code for a short-lived token...")
    try:
        short_token = _exchange_code_for_short_token(cid, secret, code)
    except Exception as e:
        print(f"Short-lived token exchange failed: {e} {_read_body(e)}")
        sys.exit(1)

    print("Upgrading to a long-lived (~60 day) token...")
    try:
        long_token, expires_in = _exchange_short_for_long(secret, short_token)
    except Exception as e:
        print(f"Long-lived token exchange failed: {e} {_read_body(e)}")
        sys.exit(1)

    print("\n" + "=" * 68)
    print("  SUCCESS - update this GitHub repo secret")
    print("  (Repo > Settings > Secrets and variables > Actions > IG_ACCESS_TOKEN)")
    print("=" * 68)
    print(f"\nIG_ACCESS_TOKEN:\n{long_token}\n")
    if expires_in:
        print(f"(long-lived token valid ~{int(expires_in) // 86400} days)")
    print(
        "\nReminder: also confirm IG_USER_ID is set. Once the automated refresh\n"
        "workflow (.github/workflows/ig-token-refresh.yml) plus the GH_PAT secret\n"
        "are in place, this token will be extended on a schedule and you won't\n"
        "need to run this again.\n"
    )


if __name__ == "__main__":
    main()
