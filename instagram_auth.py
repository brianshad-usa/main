"""
instagram_auth.py  --  ONE-TIME local setup / re-mint helper
------------------------------------------------------------
Mints a fresh LONG-LIVED token that instagram_post.py will accept, for the
"ProLink Social" Meta app -- which uses the FACEBOOK-LOGIN flow (Facebook Login
for Business + the "Manage messaging & content on Instagram" / "Manage
everything on your Page" use cases). In this flow Instagram publishing goes
through graph.facebook.com using a token tied to your Facebook Page and its
linked Instagram business account -- there is NO separate Instagram app
id/secret; you use the MAIN App ID + App Secret (App settings -> Basic).

  App ID     : App settings -> Basic -> "App ID"
  App Secret : App settings -> Basic -> "App Secret" (click Show)

What this script produces (paste into GitHub repo secrets):
  IG_ACCESS_TOKEN  - a LONG-LIVED (~60 day) user token with IG publish rights,
                     refreshable by the auto-refresh workflow.
  IG_USER_ID       - your Instagram BUSINESS ACCOUNT id (discovered from the
                     Page here; NOT your @handle).
  IG_GRAPH_BASE    - must be https://graph.facebook.com/v21.0 for this flow.

PREREQUISITES (Meta App Dashboard, one-time):
  1. App type supports Facebook Login for Business (yours does).
  2. Under Facebook Login for Business -> Settings, add this EXACT redirect URI
     to "Valid OAuth Redirect URIs":
        http://localhost:8000/callback
     (Keep the app in Development mode -- that's fine; see note below.)
  3. Your Facebook Page must have the Instagram business account linked
     (Page settings -> Linked accounts), and you must be an admin.

DEVELOPMENT MODE IS FINE: an unpublished app can fully use these permissions
for accounts with a role on the app (you, the admin/owner). You do NOT need App
Review or to publish the app for first-party posting to your own Page/IG. Just
make sure your Facebook user has a role on the app (Roles -> Roles), which the
owner always does.

USAGE:
  Windows PowerShell:
    $env:IG_APP_ID="1008983111864495"; $env:IG_APP_SECRET="yyyy"; python instagram_auth.py
  macOS/Linux:
    IG_APP_ID=1008983111864495 IG_APP_SECRET=yyyy python instagram_auth.py

  (If you don't set the env vars, the script prompts for them. It also accepts
  IG_CLIENT_ID / IG_CLIENT_SECRET. If your Facebook Login for Business setup
  requires a configuration id, set IG_LOGIN_CONFIG_ID and it will be used.)

A browser opens; approve for the Page + Instagram account; control returns here
and the long-lived token + IG_USER_ID are printed. If the browser can't reach
localhost, the script falls back to asking you to paste the redirected URL.
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

GRAPH_VER = "v21.0"
AUTH_URL = f"https://www.facebook.com/{GRAPH_VER}/dialog/oauth"
TOKEN_URL = f"https://graph.facebook.com/{GRAPH_VER}/oauth/access_token"
ACCOUNTS_URL = f"https://graph.facebook.com/{GRAPH_VER}/me/accounts"

# Facebook-login flow scopes for Instagram content publishing off a Page.
SCOPES = (
    "instagram_basic,instagram_content_publish,"
    "pages_show_list,pages_read_engagement,pages_manage_posts,business_management"
)
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
        cid = input("Meta App ID (App settings -> Basic): ").strip()
    if not secret:
        secret = input("Meta App Secret (App settings -> Basic): ").strip()
    if not cid or not secret:
        print("App ID and App Secret are required.")
        sys.exit(1)
    return cid, secret


def _get_json(url):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _read_body(e):
    if hasattr(e, "read"):
        try:
            return e.read().decode("utf-8", "replace")
        except Exception:
            return ""
    return ""


def _exchange_code_for_short_token(cid, secret, code):
    """Trade the authorization code for a SHORT-lived user token."""
    q = urllib.parse.urlencode({
        "client_id": cid,
        "client_secret": secret,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    })
    data = _get_json(f"{TOKEN_URL}?{q}")
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"No short-lived access_token in response: {data}")
    return token


def _exchange_short_for_long(cid, secret, short_token):
    """Trade the short-lived user token for a LONG-lived (~60 day) user token."""
    q = urllib.parse.urlencode({
        "grant_type": "fb_exchange_token",
        "client_id": cid,
        "client_secret": secret,
        "fb_exchange_token": short_token,
    })
    data = _get_json(f"{TOKEN_URL}?{q}")
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"No long-lived access_token in response: {data}")
    return token, data.get("expires_in")


def _discover_pages(long_user_token):
    """List the Pages this user manages, with each Page's token + linked IG
    business account, so we can print IG_USER_ID and the (non-expiring) Page
    token as an alternative."""
    q = urllib.parse.urlencode({
        "fields": "name,id,access_token,instagram_business_account{id,username}",
        "access_token": long_user_token,
    })
    data = _get_json(f"{ACCOUNTS_URL}?{q}")
    return data.get("data", [])


def main():
    cid, secret = _get_creds()

    params = {
        "client_id": cid,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": STATE,
    }
    # Facebook Login for Business may require a configuration id instead of a raw
    # scope list; support either.
    config_id = os.environ.get("IG_LOGIN_CONFIG_ID", "").strip()
    if config_id:
        params["config_id"] = config_id
    else:
        params["scope"] = SCOPES
    auth_link = AUTH_URL + "?" + urllib.parse.urlencode(params)

    print("\nOpening your browser to authorize. If it doesn't open, paste this URL:\n")
    print(auth_link + "\n")
    try:
        webbrowser.open(auth_link)
    except Exception:
        pass

    code = None
    try:
        server = HTTPServer(("localhost", REDIRECT_PORT), _Handler)
        print(f"Waiting for the Facebook redirect on {REDIRECT_URI} ...")
        server.handle_request()  # serves exactly one request (the callback)
        if _captured["error"]:
            print(f"\nAuthorization error from Facebook: {_captured['error']}")
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

    print("\nExchanging authorization code for a short-lived token...")
    try:
        short_token = _exchange_code_for_short_token(cid, secret, code)
    except Exception as e:
        print(f"Short-lived token exchange failed: {e} {_read_body(e)}")
        sys.exit(1)

    print("Upgrading to a long-lived (~60 day) user token...")
    try:
        long_token, expires_in = _exchange_short_for_long(cid, secret, short_token)
    except Exception as e:
        print(f"Long-lived token exchange failed: {e} {_read_body(e)}")
        sys.exit(1)

    print("Discovering your Page + linked Instagram business account...")
    ig_user_id = None
    page_token = None
    pages = []
    try:
        pages = _discover_pages(long_token)
    except Exception as e:
        print(f"(warning) Could not auto-list Pages: {e} {_read_body(e)}")

    linked = [p for p in pages if p.get("instagram_business_account")]
    if len(linked) == 1:
        ig_user_id = linked[0]["instagram_business_account"]["id"]
        page_token = linked[0].get("access_token")
    elif len(linked) > 1:
        print("\nMultiple Pages have a linked Instagram account:")
        for i, p in enumerate(linked):
            iba = p["instagram_business_account"]
            print(f"  [{i}] Page '{p.get('name')}' (id {p.get('id')}) -> "
                  f"IG @{iba.get('username')} (id {iba.get('id')})")
        try:
            choice = int(input("Pick the number for the ProLink Instagram: ").strip())
            ig_user_id = linked[choice]["instagram_business_account"]["id"]
            page_token = linked[choice].get("access_token")
        except Exception:
            print("(couldn't read a valid choice; set IG_USER_ID manually below)")

    print("\n" + "=" * 68)
    print("  SUCCESS - update these GitHub repo secrets")
    print("  (Repo > Settings > Secrets and variables > Actions)")
    print("=" * 68)
    print(f"\nIG_ACCESS_TOKEN  (long-lived user token, refreshable):\n{long_token}\n")
    if expires_in:
        print(f"(valid ~{int(expires_in) // 86400} days; the refresh workflow extends it)")
    if ig_user_id:
        print(f"\nIG_USER_ID  (Instagram business account id):\n{ig_user_id}\n")
    else:
        print("\nIG_USER_ID: could not auto-detect. Find it via Graph API Explorer:\n"
              "  GET /me/accounts?fields=instagram_business_account{id,username}\n")
    print("IG_GRAPH_BASE  (required for this flow):\n"
          "https://graph.facebook.com/v21.0\n")
    if page_token:
        print("-" * 68)
        print("ALTERNATIVE: a Page access token (does NOT expire) is also available.\n"
              "If IG publishing ever rejects the user token with a permissions\n"
              "error, use the Page token as IG_ACCESS_TOKEN instead -- it's\n"
              "set-and-forget (the refresh workflow then just no-ops safely):\n"
              f"{page_token}\n")
    print(
        "Reminder: keep the app in Development mode is fine for first-party\n"
        "posting to your own Page/IG. No App Review needed.\n"
    )


if __name__ == "__main__":
    main()
