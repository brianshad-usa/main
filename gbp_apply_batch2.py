"""
gbp_apply_batch2.py  --  Push the approved BATCH 2 GBP optimization:
                         ADDITIONAL categories cleanup.
=====================================================================
From GBP_Audit_ProLinkSystems.md §3 / §9(a):

  DROP  Internet service provider   (gcid:internet_service_provider)  -- not an ISP
  DROP  Computer repair service     (gcid:computer_repair_service)    -- consumer intent
  DROP  Data recovery service       (gcid:data_recovery_service)      -- consumer intent
  KEEP  Computer support and services, Computer security service,
        Computer networking service
  ADD   Computer consultant          (demoted from primary, or kept if Brian
                                      already switched primary)
  ADD   Cloud computing service      (gcid resolved live via categories.list;
                                      skipped if Google has no such category)

The PRIMARY category is NEVER changed by this script. It is read live and
re-sent unchanged (the categories field must be patched as a whole). If the
primary is still "Computer consultant", it is simply not duplicated in the
additional list. Brian switches the primary himself in the dashboard.

SAFETY: dry run by default (validateOnly=true), backup JSON before --apply,
single PATCH with updateMask=categories only.

Usage (PowerShell, from repo main/):
    python gbp_apply_batch2.py            # dry run
    python gbp_apply_batch2.py --apply    # live
"""

import os
import sys
import json
import datetime
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gbp_audit
import gbp_post
from gbp_apply_batch1 import _patch, _log as _b1log

BI_API      = gbp_audit.BI_API
LOCATION_ID = os.environ.get("GBP_LOCATION_ID", "").strip() or gbp_audit.DEFAULT_LOCATION_ID
LOCATION    = f"locations/{LOCATION_ID}"
HERE        = os.path.dirname(os.path.abspath(__file__))

DROP = {
    "categories/gcid:internet_service_provider",
    "categories/gcid:computer_repair_service",
    "categories/gcid:data_recovery_service",
}
KEEP_OR_ADD = [
    "categories/gcid:computer_support_and_services",
    "categories/gcid:computer_security_service",
    "categories/gcid:computer_networking_center",   # displays "Computer networking service"
    "categories/gcid:computer_consultant",
]
CLOUD_SEARCH      = "cloud computing"
MANAGED_IT_SEARCH = "managed it"


def _log(msg):
    print(f"[batch2] {msg}", flush=True)


def _find_categories(token, text):
    """categories.list filtered by display name. Returns [(name, displayName)]."""
    q = urllib.parse.urlencode({
        "regionCode": "US", "languageCode": "en", "view": "BASIC",
        "filter": f"displayName={text}", "pageSize": 20})
    data, err = gbp_audit._get(f"{BI_API}/categories?{q}", token,
                               f"categories.list '{text}'")
    if not data:
        return []
    return [(c.get("name"), c.get("displayName")) for c in data.get("categories", [])]


def main():
    gbp_audit._load_secrets_env()
    apply = "--apply" in sys.argv[1:]
    token = gbp_post._resolve_access_token()
    mode  = "LIVE APPLY" if apply else "DRY RUN (validateOnly=true, no writes)"
    print("=" * 68); print(f"GBP BATCH 2 (additional categories)  --  {mode}"); print("=" * 68)

    cur, err = gbp_audit._get(f"{BI_API}/{LOCATION}?readMask=name,title,categories",
                              token, "Current categories GET")
    if not cur:
        _log("Cannot read location -- aborting."); sys.exit(1)

    cats     = cur.get("categories", {}) or {}
    primary  = cats.get("primaryCategory") or {}
    current_add = cats.get("additionalCategories", []) or []
    _log(f"Primary (unchanged): {primary.get('displayName')} [{primary.get('name')}]")
    _log("Current additional : " + ", ".join(c.get("displayName", "?") for c in current_add))

    # Resolve optional "Cloud computing service" gcid live.
    cloud = _find_categories(token, CLOUD_SEARCH)
    cloud_name = None
    for name, disp in cloud:
        if "cloud" in (disp or "").lower():
            cloud_name = name
            _log(f"Cloud category found: {disp} [{name}]")
            break
    if not cloud_name:
        _log("No 'cloud computing' category in Google's list -- proceeding with 4 additional.")

    # Bonus: tell Brian the exact name of the Managed IT category for his dashboard change.
    for name, disp in _find_categories(token, MANAGED_IT_SEARCH):
        _log(f"FYI for the PRIMARY switch (dashboard, Brian): '{disp}' [{name}]")

    wanted = list(KEEP_OR_ADD) + ([cloud_name] if cloud_name else [])
    new_add = [{"name": n} for n in wanted if n != primary.get("name")]

    dropped = [c.get("displayName") for c in current_add if c.get("name") in DROP]
    added   = [n for n in wanted
               if n not in {c.get("name") for c in current_add} and n != primary.get("name")]
    _log(f"Dropping : {', '.join(dropped) or '(none present)'}")
    _log(f"Adding   : {', '.join(added) or '(none)'}")
    _log(f"Resulting additional ({len(new_add)}): " + ", ".join(c['name'] for c in new_add))
    if len(new_add) > 9:
        _log("More than 9 additional categories -- GBP max is 9. Aborting."); sys.exit(1)

    if apply:
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bpath = os.path.join(HERE, f"gbp_backup_{ts}_categories.json")
        with open(bpath, "w", encoding="utf-8") as fh:
            json.dump(cur, fh, indent=2)
        _log(f"Backup saved -> {bpath}")

    body = {"categories": {"primaryCategory": {"name": primary.get("name")},
                           "additionalCategories": new_add}}
    ok, _ = _patch(f"{BI_API}/{LOCATION}?updateMask=categories", token, body,
                   "categories (primary unchanged + cleaned additional)", apply)

    print("-" * 68)
    print("  categories ", "OK" if ok else "FAILED")
    print("-" * 68)
    if not apply:
        print("Dry run only -- nothing written. Re-run with --apply to push.")
    else:
        print("Batch 2 applied. Re-run  python gbp_audit.py  to confirm.")
        print("Primary category switch to 'Managed IT Services' remains a manual,"
              " solo dashboard change for Brian.")


if __name__ == "__main__":
    main()
