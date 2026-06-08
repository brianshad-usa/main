"""
linkedin_auth.py  --  ONE-TIME local setup helper
--------------------------------------------------
Runs the LinkedIn OAuth flow on your own machine to obtain the initial
access token and (long-lived) refresh token. You run this ONCE, copy the
two tokens it prints into your GitHub repo secrets, and you're done for
about a year.

PREREQUISITES (see LINKEDIN_SETUP.md for the click-by-click version):
  1. A LinkedIn developer app linked to your Company Page.
  2. The app approved for the "Community Management API" product.
  3. In the app's Auth tab, add this exact Redirect URL:
        http://localhost:8000/callback
  4. Have your Client ID and Client Secret handy (Auth tab).

USAGE:
  Windows PowerShell:
    $env:LINKEDIN_CLIENT_ID="xxxx"; $env:LINKEDIN_CLIENT_SECRET="yyyy"; python linkedin_auth.py
  macOS/Linux:
    LINKEDIN_CLIENT_ID=xxxx LINKEDIN_CLIENT_SECRET=yyyy python linkedin_auth.py

  (If you don't set the env vars, the script will prompt you for them.)

A browser window opens; approve the permissions; control returns here and the
tokens are printed. If the browser can't reach localhost, the script falls
back to asking you to paste the redirected URL.
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
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
# Scopes needed to publish to a Company Page via the Community Management API.
SCOPES = "w_organization_social r_organization_social"
STATE = "prolink_linkedin_setup"

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
    cid = os.environ.get("LINKEDIN_CLIENT_ID", "").strip()
    secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "").strip()
    if not cid:
        cid = input("LinkedIn Client ID: ").strip()
    if not secret:
        secret = input("LinkedIn Client Secret: ").strip()
    if not cid or not secret:
        print("Client ID and Client Secret are required.")
        sys.exit(1)
    return cid, secret


def _exchange_code(cid, secret, code):
    data = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": cid,
            "client_secret": secret,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    cid, secret = _get_creds()

    auth_link = AUTH_URL + "?" + urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": cid,
            "redirect_uri": REDIRECT_URI,
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
        print(f"Waiting for the LinkedIn redirect on {REDIRECT_URI} ...")
        server.handle_request()  # serves exactly one request (the callback)
        if _captured["error"]:
            print(f"\nAuthorization error from LinkedIn: {_captured['error']}")
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
    rexp = tok.get("refresh_token_expires_in")

    print("\n" + "=" * 68)
    print("  SUCCESS - add these to your GitHub repo secrets")
    print("  (Repo > Settings > Secrets and variables > Actions > New secret)")
    print("=" * 68)
    print(f"\nLINKEDIN_ACCESS_TOKEN:\n{access}\n")
    if refresh:
        print(f"LINKEDIN_REFRESH_TOKEN:\n{refresh}\n")
    else:
        print(
            "NOTE: No refresh token was returned. Your app may not be enabled for\n"
            "refresh tokens (Community Management API apps normally are). Without a\n"
            "refresh token the access token expires in ~60 days and you'll re-run\n"
            "this script then.\n"
        )
    if exp:
        print(f"(access token expires in ~{int(exp)//86400} days)")
    if rexp:
        print(f"(refresh token expires in ~{int(rexp)//86400} days)")
    print(
        "\nAlso make sure these secrets are set:\n"
        "  LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_ORG_ID\n"
    )


if __name__ == "__main__":
    main()
