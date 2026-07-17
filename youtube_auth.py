"""
youtube_auth.py  --  ONE-TIME local setup helper
-------------------------------------------------
Runs the Google OAuth2 flow on your own machine to obtain the refresh token the
video pipeline uses to upload to your YouTube channel. Run this ONCE, copy the
token into your GitHub repo secrets, and the automation handles everything for a
year (refresh tokens last until revoked).

PREREQUISITES (one-time, in Google Cloud Console):
  1. A Google Cloud project with the "YouTube Data API v3" enabled.
  2. An OAuth 2.0 "Desktop app" credential in that project (Client ID + Secret).
  3. On the OAuth consent screen, add YOURSELF as a Test user (the Google
     account that owns / manages the Pro Link Systems YouTube channel).

USAGE:
  Windows PowerShell:
    $env:YT_CLIENT_ID="xxxx"; $env:YT_CLIENT_SECRET="yyyy"; python youtube_auth.py
  macOS/Linux:
    YT_CLIENT_ID=xxxx YT_CLIENT_SECRET=yyyy python youtube_auth.py

  (If you don't set the env vars, the script prompts for them.)

A browser opens; sign in as the channel's Google account; approve "Manage your
YouTube videos"; control returns here and your tokens are printed.

NOTE ON PUBLIC UPLOADS: while your Google Cloud project is still "Testing" /
unverified, videos uploaded through the API can be forced to PRIVATE. If your
first upload lands as private, either (a) set YT_PRIVACY=unlisted for now, or
(b) submit the project for verification to allow public API uploads. The
uploader logs the privacy status it received so you'll know.
"""

import os
import sys
import json
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

REDIRECT_PORT = 8000
REDIRECT_PATH = "/callback"
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}{REDIRECT_PATH}"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
# youtube.upload lets us insert videos; youtube.readonly is handy for sanity checks.
SCOPE = "https://www.googleapis.com/auth/youtube.upload"
STATE = "prolink_youtube_setup"

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
        _captured["error"] = qs.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if _captured["code"]:
            msg = "<h2>Success.</h2><p>You can close this tab and return to the terminal.</p>"
        else:
            msg = f"<h2>Authorization failed.</h2><p>{_captured['error']}</p>"
        self.wfile.write(f"<html><body style='font-family:sans-serif'>{msg}</body></html>".encode())

    def log_message(self, *args):
        pass


def _get_creds():
    cid = os.environ.get("YT_CLIENT_ID", "").strip()
    secret = os.environ.get("YT_CLIENT_SECRET", "").strip()
    if not cid:
        cid = input("Google OAuth Client ID: ").strip()
    if not secret:
        secret = input("Google OAuth Client Secret: ").strip()
    if not cid or not secret:
        print("Client ID and Client Secret are required.")
        sys.exit(1)
    return cid, secret


def _exchange_code(cid, secret, code):
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": cid,
        "client_secret": secret,
    }).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL, data=data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    cid, secret = _get_creds()

    auth_link = AUTH_URL + "?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": cid,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": STATE,
        "access_type": "offline",
        "prompt": "consent",  # forces a refresh token even if already authorized
    })

    print("\nOpening your browser to authorize. If it doesn't open, paste this URL:\n")
    print(auth_link + "\n")
    try:
        webbrowser.open(auth_link)
    except Exception:
        pass

    code = None
    try:
        server = HTTPServer(("localhost", REDIRECT_PORT), _Handler)
        print(f"Waiting for the Google redirect on {REDIRECT_URI} ...")
        server.handle_request()
        if _captured["error"]:
            print(f"\nAuthorization error from Google: {_captured['error']}")
            sys.exit(1)
        code = _captured["code"]
    except OSError as e:
        print(f"\nCould not start local server on port {REDIRECT_PORT} ({e}).")
        pasted = input(
            "After approving in the browser you'll land on a localhost page.\n"
            "Copy the full URL from the address bar and paste it here:\n"
        ).strip()
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
        code = qs.get("code", [None])[0]

    if not code:
        print("No authorization code received. Aborting.")
        sys.exit(1)

    print("\nExchanging authorization code for tokens...")
    try:
        tok = _exchange_code(cid, secret, code)
    except Exception as e:
        body = ""
        if hasattr(e, "read"):
            try:
                body = e.read().decode("utf-8", "replace")
            except Exception:
                pass
        print(f"Token exchange failed: {e} {body}")
        sys.exit(1)

    access = tok.get("access_token")
    refresh = tok.get("refresh_token")
    exp = tok.get("expires_in")

    print("\n" + "=" * 68)
    print("  SUCCESS - add these to your GitHub repo secrets")
    print("  (Repo > Settings > Secrets and variables > Actions > New secret)")
    print("=" * 68)
    if refresh:
        print(f"\nYT_REFRESH_TOKEN (required - lasts until revoked):\n{refresh}\n")
    else:
        print(
            "\nWARNING: No refresh token returned. Make sure you passed access_type=offline\n"
            "and prompt=consent, and that this is a Desktop-app credential. Re-run to retry.\n"
        )
    print(f"YT_ACCESS_TOKEN (optional fallback):\n{access}\n")
    if exp:
        print(f"(access token expires in ~{int(exp) // 3600} hours - use the refresh token)")
    print(
        "\nAlso set these secrets:\n"
        "  YT_CLIENT_ID, YT_CLIENT_SECRET\n"
        "Optional:\n"
        "  YT_PRIVACY  (public | unlisted | private; default public)\n"
    )


if __name__ == "__main__":
    main()
