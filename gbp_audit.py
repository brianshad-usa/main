"""
gbp_audit.py  --  READ-ONLY Google Business Profile configuration dump.
=======================================================================
Pulls the CURRENT state of the Pro Link Systems GBP location so the audit
reflects REAL values, not assumptions. This script makes **GET requests
only** -- it NEVER writes, patches, or deletes anything on the profile,
so it cannot trigger re-verification or a suspension. Safe to run anytime.

It reads the same credentials the posting automation uses
(GBP_CLIENT_ID / GBP_CLIENT_SECRET / GBP_REFRESH_TOKEN), auto-loading them
from C:\\GoogleAds\\secrets.env if they are not already in the environment,
and reuses gbp_post._resolve_access_token() so the OAuth flow is identical.

What it retrieves
-----------------
  Business Information API v1 (the authoritative config surface):
    * primary category + additional categories
    * business name (title), full storefront address, service area cities
    * phone numbers (primary + additional)
    * website URI, opening date (openInfo), regular + special hours, more hours
    * business description (profile.description) + its length
    * labels, Ad-words extension phone, lat/lng, store code
    * serviceItems  (the GBP "Services" list)  -> whether populated
    * attributes    (online appointments, identifies-as, accessibility, ...)
  Google My Business API v4 (counts only):
    * review count + average star rating
    * media/photo count by category (PROFILE/COVER/LOGO/additional)
    * most recent local post date + count (is the weekly cadence live?)

Everything is wrapped so a partial failure (e.g. v4 quota) still yields a
usable dump. Output:
    * prints a human-readable summary + a MISSING/EMPTY field checklist
    * writes the full raw JSON to  gbp_audit_output.json  next to this file

Usage (PowerShell, from the repo's  main/  folder):
    python gbp_audit.py

If creds are NOT in secrets.env, set them first in the shell:
    $env:GBP_CLIENT_ID="..."; $env:GBP_CLIENT_SECRET="..."; $env:GBP_REFRESH_TOKEN="..."
    python gbp_audit.py
"""

import os
import sys
import json
import datetime
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Known identifiers for the Pro Link Systems location (override via env).
# ---------------------------------------------------------------------------
DEFAULT_ACCOUNT_ID  = "106570312922328987685"
DEFAULT_LOCATION_ID = "7712242499324845523"

SECRETS_ENV_PATH = r"C:\GoogleAds\secrets.env"

BI_API  = "https://mybusinessbusinessinformation.googleapis.com/v1"
V4_API  = "https://mybusinessgoogleapis.com/v4"   # overwritten below
V4_API  = "https://mybusiness.googleapis.com/v4"

# Comprehensive readMask for the Business Information API location resource.
READ_MASK = ",".join([
    "name", "title", "storeCode", "languageCode",
    "phoneNumbers", "categories", "storefrontAddress", "websiteUri",
    "regularHours", "specialHours", "moreHours",
    "serviceArea", "labels", "adWordsLocationExtensions",
    "latlng", "openInfo", "metadata", "profile", "serviceItems",
])


def _log(msg):
    print(f"[audit] {msg}", flush=True)


def _load_secrets_env(path=SECRETS_ENV_PATH):
    """Populate os.environ from a KEY=VALUE secrets file WITHOUT overwriting
    anything already set in the shell. Silent no-op if the file is absent."""
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.lower().startswith("export "):
                    line = line[7:]
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
        _log(f"Loaded credentials from {path} (values not shown).")
    except Exception as e:
        _log(f"Could not read {path}: {e}")


def _get(url, token, what):
    """GET + JSON. Returns (data, None) on success, (None, err_string) on
    failure. Never raises -- a partial dump is more useful than a crash."""
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        msg = f"HTTP {e.code}"
        try:
            err = json.loads(body).get("error", {})
            msg += f": {err.get('status')} - {err.get('message')}"
        except Exception:
            msg += f": {body[:300]}"
        _log(f"{what} FAILED ({msg})")
        return None, msg
    except Exception as e:
        _log(f"{what} FAILED ({e})")
        return None, str(e)


def _na(v):
    return v if (v or v == 0) else "— (missing/empty)"


def main():
    _load_secrets_env()

    account_id  = os.environ.get("GBP_ACCOUNT_ID",  "").strip() or DEFAULT_ACCOUNT_ID
    location_id = os.environ.get("GBP_LOCATION_ID", "").strip() or DEFAULT_LOCATION_ID

    try:
        import gbp_post
        token = gbp_post._resolve_access_token()
    except Exception as e:
        _log(f"FATAL: could not obtain an access token: {e}")
        _log("Set GBP_CLIENT_ID / GBP_CLIENT_SECRET / GBP_REFRESH_TOKEN "
             "(in C:\\GoogleAds\\secrets.env or the shell) and retry.")
        sys.exit(1)

    location_name = f"locations/{location_id}"
    dump = {"_pulled_at": datetime.datetime.utcnow().isoformat() + "Z",
            "_account_id": account_id, "_location_id": location_id}

    # 1) Core config -- Business Information API v1 -------------------------
    loc, err = _get(f"{BI_API}/{location_name}?readMask={READ_MASK}",
                    token, "Location config (Business Information API)")
    dump["location"] = loc or {"_error": err}

    # 2) Attributes --------------------------------------------------------
    attrs, aerr = _get(f"{BI_API}/{location_name}/attributes", token, "Attributes")
    dump["attributes"] = attrs or {"_error": aerr}

    # 3) Reviews (count + average) -- v4 -----------------------------------
    rev, rerr = _get(f"{V4_API}/accounts/{account_id}/{location_name}/reviews?pageSize=1",
                     token, "Reviews summary (v4)")
    dump["reviews"] = rev or {"_error": rerr}

    # 4) Media / photos -- v4 ----------------------------------------------
    media, merr = _get(f"{V4_API}/accounts/{account_id}/{location_name}/media?pageSize=100",
                       token, "Media / photos (v4)")
    dump["media"] = media or {"_error": merr}

    # 5) Local posts (cadence check) -- v4 ---------------------------------
    posts, perr = _get(f"{V4_API}/accounts/{account_id}/{location_name}/localPosts?pageSize=10",
                       token, "Local posts (v4)")
    dump["localPosts"] = posts or {"_error": perr}

    # ---- write raw JSON --------------------------------------------------
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "gbp_audit_output.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(dump, fh, indent=2, ensure_ascii=False)
    _log(f"Raw JSON written to {out_path}")

    # ---- human summary ---------------------------------------------------
    print("\n" + "=" * 68)
    print("PRO LINK SYSTEMS -- CURRENT GBP CONFIGURATION (read-only)")
    print("=" * 68)

    if loc:
        cats = loc.get("categories", {}) or {}
        primary = (cats.get("primaryCategory") or {})
        print("Business name     :", _na(loc.get("title")))
        print("Primary category  :", _na(primary.get("displayName")),
              f"[{primary.get('name', '')}]")
        add = cats.get("additionalCategories", []) or []
        if add:
            for c in add:
                print("  + additional    :", c.get("displayName"),
                      f"[{c.get('name', '')}]")
        else:
            print("  + additional    : — (none set)")

        addr = loc.get("storefrontAddress", {}) or {}
        print("Address           :",
              ", ".join(addr.get("addressLines", []))
              + f", {addr.get('locality', '')} {addr.get('administrativeArea', '')}"
              + f" {addr.get('postalCode', '')}".rstrip())

        sa = (loc.get("serviceArea", {}) or {}).get("places", {}) or {}
        places = sa.get("placeInfos", []) or []
        print(f"Service area      : {len(places)} place(s) listed"
              + (" — EMPTY" if not places else ""))
        for p in places:
            print("    -", p.get("placeName"))

        phones = loc.get("phoneNumbers", {}) or {}
        print("Primary phone     :", _na(phones.get("primaryPhone")))
        if phones.get("additionalPhones"):
            print("Additional phones :", ", ".join(phones["additionalPhones"]))
        print("Website           :", _na(loc.get("websiteUri")))

        openinfo = loc.get("openInfo", {}) or {}
        od = openinfo.get("openingDate")
        if od:
            print("Opening date      :",
                  f"{od.get('year')}-{od.get('month','?')}-{od.get('day','?')}")
        else:
            print("Opening date      : — (not set)")
        print("Open status       :", _na(openinfo.get("status")))

        reg = loc.get("regularHours")
        print("Regular hours     :", "set" if reg else "— (NOT set)")
        print("Special hours     :", "set" if loc.get("specialHours") else "— (none)")
        print("More hours        :", "set" if loc.get("moreHours") else "— (none)")

        desc = (loc.get("profile", {}) or {}).get("description", "") or ""
        print(f"Description       : {len(desc)} chars",
              "— EMPTY" if not desc else "")
        if desc:
            print("   >", desc[:180] + ("..." if len(desc) > 180 else ""))

        svc = loc.get("serviceItems", []) or []
        print(f"Services list     : {len(svc)} item(s)"
              + (" — EMPTY (big miss)" if not svc else ""))
        for s in svc[:30]:
            label = (s.get("structuredServiceItem", {}) or {}).get("displayName") \
                or (s.get("freeFormServiceItem", {}) or {}) \
                     .get("label", {}).get("displayName") \
                or "(unnamed)"
            print("    -", label)

        labels = loc.get("labels", []) or []
        print("Labels            :", ", ".join(labels) if labels else "— (none)")
    else:
        print("!! Could not read core location config:", err)

    # attributes
    if attrs and attrs.get("attributes"):
        on = []
        for a in attrs["attributes"]:
            vals = a.get("values", [])
            if vals and vals[0] in (True, "true"):
                on.append(a.get("name", "").split("/")[-1])
        print(f"Attributes ON     : {len(on)} ->",
              ", ".join(on) if on else "— (none enabled)")
    else:
        print("Attributes        : — (none returned / endpoint error)")

    # reviews
    if dump["reviews"] and "averageRating" in dump["reviews"]:
        print(f"Reviews           : {dump['reviews'].get('totalReviewCount', '?')} total,"
              f" avg {dump['reviews'].get('averageRating', '?')} stars")
    else:
        print("Reviews           : (v4 error or none)",
              dump["reviews"].get("_error", "") if isinstance(dump["reviews"], dict) else "")

    # media
    if media and "mediaItems" in media:
        print(f"Photos            : {len(media['mediaItems'])} item(s) returned "
              f"(total {media.get('totalMediaItemCount', '?')})")
    else:
        print("Photos            : (v4 error or none)")

    # posts
    if posts and posts.get("localPosts"):
        lp = posts["localPosts"]
        newest = lp[0].get("updateTime") or lp[0].get("createTime")
        print(f"Local posts       : {len(lp)} recent; newest {newest}")
    else:
        print("Local posts       : (v4 error or none returned)")

    print("=" * 68)
    print(f"Full raw JSON: {out_path}")
    print("This was READ-ONLY. Nothing on the profile was changed.")


if __name__ == "__main__":
    main()
