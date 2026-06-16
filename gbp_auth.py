"""
gbp_auth.py  --  ONE-TIME local setup helper
---------------------------------------------
Runs the Google OAuth2 flow on your own machine to obtain the refresh token
needed by the weekly GBP post automation. Run this ONCE, copy the token into
your GitHub repo secrets, and the cron handles everything for a year.

PREREQUISITES (see GBP_SETUP.md for the click-by-click version):
  1. A Google Cloud project with the My Business API enabled.
  2. An OAuth 2.0 "Desktop app" credential created in that project.
  3. Have your Client ID and Client Secret handy.

USAGE:
  Windows PowerShell:
    $env:GBP_CLIENT_ID="xxxx"; $env:GBP_CLIENT_SECRET="yyyy"; python gbp_auth.py
  macOS/Linux:
    GBP_CLIENT_ID=xxxx GBP_CLIENT_SECRET=yyyy python gbp_auth.py

  (If you don't set the env vars, the script will prompt you for them.)

A browser opens; sign in as the Google account that manages the GBP listing;
approve the permissions; control returns here and your tokens are printed.
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
REDIRECT_URI  = f"http://localhost:{REDIRECT_PORT}{REDIRECT_PATH}"
AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE     = "https://www.googleapis.com/auth/business.manage"
STATE     = "prolink_gbp_setup"

_captured = {"code": None, "error": None}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != REDIRECT_PATH:
            self.send_response(404)
            self.end_headers()
            return
        qs = urllib.parse.parse_qs(parsed.query)
        _captured["code"]  = qs.get("code",  [None])[0]
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
    cid    = os.environ.get("GBP_CLIENT_ID", "").strip()
    secret = os.environ.get("GBP_CLIENT_SECRET", "").strip()
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
        "grant_type":   "authorization_code",
        "code":         code,
        "redirect_uri": REDIRECT_URI,
        "client_id":    cid,
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
        "client_id":     cid,
        "redirect_uri":  REDIRECT_URI,
        "scope":         SCOPE,
        "state":         STATE,
        "access_type":   "offline",
        "prompt":        "consent",   # forces a refresh token even if already authorized
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
        qs   = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
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

    access  = tok.get("access_token")
    refresh = tok.get("refresh_token")
    exp     = tok.get("expires_in")

    print("\n" + "=" * 68)
    print("  SUCCESS - add these to your GitHub repo secrets")
    print("  (Repo > Settings > Secrets and variables > Actions > New secret)")
    print("=" * 68)
    print(f"\nGBP_ACCESS_TOKEN (optional fallback):\n{access}\n")
    if refresh:
        print(f"GBP_REFRESH_TOKEN (required — never expires unless revoked):\n{refresh}\n")
    else:
        print(
            "WARNING: No refresh token returned. Make sure you passed access_type=offline\n"
            "and prompt=consent. Re-run this script to try again.\n"
        )
    if exp:
        print(f"(access token expires in ~{int(exp)//3600} hours — use the refresh token)")
    print(
        "\nAlso make sure these secrets are set:\n"
        "  GBP_CLIENT_ID, GBP_CLIENT_SECRET, GBP_ACCOUNT_ID, GBP_LOCATION_ID\n"
        "\nSee GBP_SETUP.md for how to find your Account ID and Location ID.\n"
    )


if __name__ == "__main__":
    main()
