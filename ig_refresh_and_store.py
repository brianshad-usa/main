"""
ig_refresh_and_store.py  --  CI auto-refresh (hands-off)
--------------------------------------------------------
Runs inside the scheduled GitHub Actions workflow
(.github/workflows/ig-token-refresh.yml). It:

  1. Extends the current long-lived IG token by ~60 days, using the flow that
     matches how the token was minted (auto-detected from IG_GRAPH_BASE):
       * FACEBOOK-login flow (graph.facebook.com, the ProLink Social setup):
         re-exchange the long-lived USER token via
         GET /oauth/access_token?grant_type=fb_exchange_token (needs
         IG_APP_ID + IG_APP_SECRET). This is what `instagram_auth.py` mints.
       * INSTAGRAM-login flow (graph.instagram.com): use
         instagram_post.refresh_long_lived_token() (ig_refresh_token).
     The refreshed token is held in memory and NEVER printed to the CI log.
  2. Writes the refreshed token back into the repo secret IG_ACCESS_TOKEN via
     the GitHub REST API: GET the repo public key, encrypt with libsodium
     (PyNaCl sealed box), then PUT the encrypted value -- so the token never
     lapses.

If the token is a non-expiring Facebook PAGE token, fb_exchange_token returns
the same class of token; the write-back is harmless. If anything fails it emits
a GitHub `::error::` annotation and exits non-zero so the run goes RED and Brian
is notified -- far better than a silent lapse.

NO SECRET VALUE IS EVER PRINTED. The PAT and tokens come from env/secrets only.

Environment (provided by the workflow from repo secrets / Actions):
  IG_ACCESS_TOKEN   - current long-lived token to extend (required)
  IG_GRAPH_BASE     - selects the flow; contains "graph.facebook.com" for the
                      Facebook-login flow, else the Instagram-login flow
  IG_APP_ID         - Meta App ID  (required for the Facebook-login refresh)
  IG_APP_SECRET     - Meta App Secret (required for the Facebook-login refresh)
  GH_PAT            - fine-grained PAT with "Secrets: Read and write" on this
                      repo (alternate name IG_REFRESH_PAT also accepted)
  GITHUB_REPOSITORY - "owner/repo" (auto-set by Actions); REPO env overrides it
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

GITHUB_API = "https://api.github.com"
SECRET_NAME = "IG_ACCESS_TOKEN"
FB_GRAPH = "https://graph.facebook.com/v21.0"


def _fail(msg):
    # GitHub Actions error annotation -> the run turns RED with this message.
    print(f"::error::{msg}", flush=True)
    sys.exit(1)


def _log(msg):
    print(f"[ig-refresh] {msg}", flush=True)


def _pat():
    pat = (os.environ.get("GH_PAT") or os.environ.get("IG_REFRESH_PAT") or "").strip()
    if not pat:
        _fail("No PAT provided. Set the GH_PAT (or IG_REFRESH_PAT) repo secret to "
              "a fine-grained PAT with 'Secrets: Read and write' on this repo.")
    return pat


def _repo():
    repo = (os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY") or "").strip()
    if "/" not in repo:
        _fail("Could not determine owner/repo (GITHUB_REPOSITORY not set).")
    return repo


def _api(method, path, pat, body=None):
    url = f"{GITHUB_API}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {pat}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, (json.loads(raw) if raw else {})


def _encrypt_secret(public_key_b64, secret_value):
    """Encrypt a UTF-8 secret with the repo public key using a libsodium sealed
    box, per GitHub's 'create or update a repository secret' flow."""
    from nacl import encoding, public

    pk = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed = public.SealedBox(pk).encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(sealed).decode("utf-8")


def _refresh_facebook_token():
    """Facebook-login flow: extend the long-lived USER token another ~60 days."""
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    cid = (os.environ.get("IG_APP_ID") or os.environ.get("IG_CLIENT_ID") or "").strip()
    secret = (os.environ.get("IG_APP_SECRET") or os.environ.get("IG_CLIENT_SECRET") or "").strip()
    if not token:
        _fail("IG_ACCESS_TOKEN is empty; nothing to refresh.")
    if not (cid and secret):
        _fail("Facebook-login refresh needs IG_APP_ID and IG_APP_SECRET secrets "
              "(the main Meta App ID/Secret). Add them and re-run.")
    q = urllib.parse.urlencode({
        "grant_type": "fb_exchange_token",
        "client_id": cid,
        "client_secret": secret,
        "fb_exchange_token": token,
    })
    with urllib.request.urlopen(f"{FB_GRAPH}/oauth/access_token?{q}", timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    new_token = data.get("access_token")
    if not new_token:
        raise RuntimeError(f"fb_exchange_token returned no access_token: {data}")
    days = round(int(data.get("expires_in", 0)) / 86400) if data.get("expires_in") else "many"
    _log(f"Refreshed Facebook long-lived token OK; valid ~{days} more days.")
    return new_token


def _refresh_token():
    graph = os.environ.get("IG_GRAPH_BASE", "").lower()
    if "graph.facebook.com" in graph:
        _log("Detected Facebook-login flow (IG_GRAPH_BASE=graph.facebook.com).")
        return _refresh_facebook_token()
    # Instagram-login flow.
    _log("Detected Instagram-login flow (graph.instagram.com).")
    from instagram_post import refresh_long_lived_token
    return refresh_long_lived_token()


def main():
    pat = _pat()
    repo = _repo()

    # 1) Extend the token (in-memory; never printed).
    try:
        new_token = _refresh_token()
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        _fail(f"Token refresh failed ({e.code}). The token may be EXPIRED (an "
              f"expired token cannot be extended -- re-mint with instagram_auth.py). "
              f"Detail: {detail[:300]}")
    except Exception as e:
        _fail(f"Token refresh failed: {e}")

    if not new_token:
        _fail("Refresh returned an empty token; aborting without touching the secret.")

    # 2) GET the repo public key.
    try:
        _, key = _api("GET", f"/repos/{repo}/actions/secrets/public-key", pat)
    except urllib.error.HTTPError as e:
        _fail(f"Could not fetch repo public key ({e.code}). Check the PAT has "
              f"'Secrets: Read and write' on {repo}.")
    except Exception as e:
        _fail(f"Could not fetch repo public key: {e}")

    key_id, public_key = key.get("key_id"), key.get("key")
    if not key_id or not public_key:
        _fail("Repo public-key response was missing key_id/key.")

    # 3) Encrypt + PUT the new secret value.
    try:
        encrypted_value = _encrypt_secret(public_key, new_token)
    except Exception as e:
        _fail(f"Failed to encrypt the token with PyNaCl: {e}")

    try:
        status, _ = _api(
            "PUT",
            f"/repos/{repo}/actions/secrets/{SECRET_NAME}",
            pat,
            {"encrypted_value": encrypted_value, "key_id": key_id},
        )
    except urllib.error.HTTPError as e:
        _fail(f"Failed to update the {SECRET_NAME} secret ({e.code}). Check the "
              f"PAT permissions/scope on {repo}.")
    except Exception as e:
        _fail(f"Failed to update the {SECRET_NAME} secret: {e}")

    # 200 = updated existing secret, 201 = created new one.
    _log(f"{SECRET_NAME} updated successfully (HTTP {status}). Token extended "
         f"~60 days. No secret value was logged.")


if __name__ == "__main__":
    main()
