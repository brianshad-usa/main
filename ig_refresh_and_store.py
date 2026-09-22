"""
ig_refresh_and_store.py  --  CI auto-refresh (hands-off)
--------------------------------------------------------
Runs inside the scheduled GitHub Actions workflow
(.github/workflows/ig-token-refresh.yml). It:

  1. Extends the current long-lived IG token by ~60 days using the same
     Meta refresh endpoint that `python instagram_post.py --refresh` uses
     (we import refresh_long_lived_token() directly so the new token is held
     in memory and NEVER printed to the CI log).
  2. Writes the refreshed token back into the repo secret IG_ACCESS_TOKEN via
     the GitHub REST API: GET the repo public key, encrypt with libsodium
     (PyNaCl sealed box), then PUT the encrypted value. This closes the loop
     so the token never lapses.

If anything fails, it emits a GitHub `::error::` annotation and exits non-zero
so the run goes RED and Brian is notified -- far better than a silent lapse.

NO SECRET VALUE IS EVER PRINTED. The PAT and tokens come from env/secrets only.

Environment (all provided by the workflow from repo secrets / Actions):
  IG_ACCESS_TOKEN   - current long-lived token to extend (required)
  IG_GRAPH_BASE     - optional; must be graph.instagram.com for refresh to work
  GH_PAT            - fine-grained PAT with "Secrets: Read and write" on this
                      repo (alternate name IG_REFRESH_PAT also accepted)
  GITHUB_REPOSITORY - "owner/repo" (auto-set by GitHub Actions); REPO env
                      overrides it if you ever run this elsewhere
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request

from instagram_post import refresh_long_lived_token

GITHUB_API = "https://api.github.com"
SECRET_NAME = "IG_ACCESS_TOKEN"


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


def main():
    pat = _pat()
    repo = _repo()

    # 1) Extend the token (in-memory; never printed).
    try:
        new_token = refresh_long_lived_token()
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        _fail(f"Instagram token refresh failed ({e.code}). The token may be "
              f"EXPIRED (an expired token cannot be extended -- re-mint with "
              f"instagram_auth.py). Detail: {detail[:300]}")
    except Exception as e:
        _fail(f"Instagram token refresh failed: {e}")

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
