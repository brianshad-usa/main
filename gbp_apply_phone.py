"""
gbp_apply_phone.py -- declare (877) 470-2739 as an ADDITIONAL phone on the GBP
location, keeping (800) 890-6133 as primary. One PATCH, updateMask=phoneNumbers.
Reason: the 877 line is live and still appears on older directory listings;
declaring it on GBP turns a NAP "mismatch" into a known secondary number.

    python gbp_apply_phone.py            # dry run (validateOnly)
    python gbp_apply_phone.py --apply    # live (backs up first)
"""
import os, sys, json, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gbp_audit, gbp_post
from gbp_apply_batch1 import _patch

PRIMARY    = "(800) 890-6133"
ADDITIONAL = ["(877) 470-2739"]
LOCATION   = f"locations/{os.environ.get('GBP_LOCATION_ID','').strip() or gbp_audit.DEFAULT_LOCATION_ID}"
HERE       = os.path.dirname(os.path.abspath(__file__))

def main():
    gbp_audit._load_secrets_env()
    apply = "--apply" in sys.argv[1:]
    token = gbp_post._resolve_access_token()
    cur, err = gbp_audit._get(f"{gbp_audit.BI_API}/{LOCATION}?readMask=name,phoneNumbers", token, "Current phones GET")
    if not cur: sys.exit(1)
    ph = cur.get("phoneNumbers", {})
    print("current :", ph)
    if ph.get("primaryPhone") != PRIMARY:
        print(f"!! primary on GBP is {ph.get('primaryPhone')!r}, expected {PRIMARY!r} -- aborting, nothing changed."); sys.exit(1)
    extra = [p for p in (ph.get("additionalPhones") or []) if p not in ADDITIONAL]
    body = {"phoneNumbers": {"primaryPhone": PRIMARY, "additionalPhones": ADDITIONAL + extra}}
    print("proposed:", body["phoneNumbers"])
    if apply:
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bp = os.path.join(HERE, f"gbp_backup_{ts}_phones.json")
        json.dump(cur, open(bp, "w", encoding="utf-8"), indent=2); print("backup ->", bp)
    ok, _ = _patch(f"{gbp_audit.BI_API}/{LOCATION}?updateMask=phoneNumbers", token, body, "phoneNumbers (+877 additional)", apply)
    print("phones ", "OK" if ok else "FAILED", "" if apply else "(dry run -- add --apply)")

if __name__ == "__main__":
    main()
