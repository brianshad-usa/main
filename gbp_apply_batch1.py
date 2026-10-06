"""
gbp_apply_batch1.py  --  Push the approved BATCH 1 GBP optimizations.
=====================================================================
Batch 1 = the zero-NAP-risk edits from GBP_Audit_ProLinkSystems.md §9(a):

  1. serviceItems  -> replace the 86 auto-suggested items with 15 clean services
  2. serviceArea   -> the 20 approved LA/SFV/Westside/South Bay places
  3. attributes    -> requires_appointments OFF; appointment + social URLs filled
  4. moreHours     -> "Online service hours" 24/7 (office hours untouched)
  5. websiteUri    -> homepage + UTM for attribution

NOT in this script (deliberately): primary category, additional categories
(Batch 2), business name, address, phone, description, regular hours.

SAFETY MODEL
------------
  * Default run is a DRY RUN: every PATCH is sent with  validateOnly=true,
    so Google validates the payload server-side and returns what it WOULD
    accept -- nothing is written. Read the output, then re-run with --apply.
  * Before any real write the script GETs the location and saves a full
    backup to  gbp_backup_<timestamp>.json  so every field can be restored.
  * Each field is its own PATCH with its own tight updateMask. One failing
    field never blocks the others, and nothing outside the mask is touched.
  * Service-area place IDs are resolved live via the Places API (Text
    Search). If GOOGLE_MAPS_API_KEY / PLACES_API_KEY is not in secrets.env,
    the service-area step is SKIPPED with instructions to do that one field
    in the dashboard -- the other 4 fields still apply.

Usage (PowerShell, from repo main/):
    python gbp_apply_batch1.py            # dry run  (validateOnly, no writes)
    python gbp_apply_batch1.py --apply    # real push (backs up first)
    python gbp_apply_batch1.py --only services,hours   # subset, comma list:
                                          #   services, area, attributes, hours, website
"""

import os
import sys
import json
import time
import datetime
import urllib.parse
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gbp_audit            # reuses _load_secrets_env / _get / constants
import gbp_post             # reuses _resolve_access_token

BI_API      = gbp_audit.BI_API
LOCATION_ID = os.environ.get("GBP_LOCATION_ID", "").strip() or gbp_audit.DEFAULT_LOCATION_ID
LOCATION    = f"locations/{LOCATION_ID}"
HERE        = os.path.dirname(os.path.abspath(__file__))

# Free-form service items must hang off a category that is ON the location.
# computer_support_and_services stays in every planned scenario (it is kept
# as additional in Batch 2, or promoted to primary via the fallback), so
# services attached to it survive the later category changes.
SERVICE_PARENT_CATEGORY = "categories/gcid:computer_support_and_services"

# ---------------------------------------------------------------------------
# 1) SERVICES  (15)
# ---------------------------------------------------------------------------
SERVICES = [
    ("Managed IT Services",
     "Fully managed, proactive IT for LA businesses - monitoring, maintenance, and flat-rate support that keeps systems running."),
    ("24/7 IT Help Desk & Support",
     "US-based engineers answer around the clock - no ticket queues, no offshore support."),
    ("Cybersecurity Services",
     "Layered protection - threat detection, response, and security assessments to cut breach and ransomware risk."),
    ("Network Security",
     "Firewalls, segmentation, and monitoring that keep your business network locked down."),
    ("Endpoint Security",
     "Managed EDR/antivirus protecting laptops, desktops, and servers from modern threats."),
    ("Email Security",
     "Anti-phishing, spam, and impersonation defense for Microsoft 365 and business email."),
    ("Identity & Access Management",
     "MFA, SSO, and least-privilege access so only the right people reach your systems."),
    ("Cloud Services & Migration",
     "Plan and run Azure, AWS, and hybrid cloud moves with ongoing cloud management."),
    ("Microsoft 365 Support",
     "Setup, migration, licensing, and day-to-day M365 administration."),
    ("Backup & Disaster Recovery",
     "Automated backups and tested recovery plans so you're back up fast after any outage."),
    ("Virtual CIO (vCIO) & IT Strategy",
     "Budgeting, roadmaps, and technology planning aligned to your business goals."),
    ("Governance, Risk & Compliance",
     "HIPAA, SOC 2, CMMC, and PCI readiness, documentation, and audit support."),
    ("Security Awareness Training",
     "Phishing simulations and staff training that make employees your first line of defense."),
    ("Network Support & Cabling",
     "Design, installation, and support for wired and wireless business networks."),
    ("AI Automation Services",
     "Practical AI and workflow automation that cut manual work and boost productivity."),
]

# ---------------------------------------------------------------------------
# 2) SERVICE AREA  (20) -- place IDs resolved at run time
# ---------------------------------------------------------------------------
SERVICE_AREA_QUERIES = [
    "Woodland Hills, Los Angeles, CA, USA",
    "Calabasas, CA, USA",
    "Sherman Oaks, Los Angeles, CA, USA",
    "Encino, Los Angeles, CA, USA",
    "Van Nuys, Los Angeles, CA, USA",
    "Northridge, Los Angeles, CA, USA",
    "West Hills, Los Angeles, CA, USA",
    "Chatsworth, Los Angeles, CA, USA",
    "Burbank, CA, USA",
    "Glendale, CA, USA",
    "Thousand Oaks, CA, USA",
    "Santa Monica, CA, USA",
    "Beverly Hills, CA, USA",
    "Culver City, CA, USA",
    "El Segundo, CA, USA",
    "Torrance, CA, USA",
    "Long Beach, CA, USA",
    "Pasadena, CA, USA",
    "Irvine, CA, USA",
    "Los Angeles County, CA, USA",
]
assert len(SERVICE_AREA_QUERIES) == 20, "GBP allows max 20 service-area places"

# ---------------------------------------------------------------------------
# 3) ATTRIBUTES
# ---------------------------------------------------------------------------
ATTRIBUTES = [
    {"name": "attributes/requires_appointments",
     "valueType": "BOOL", "values": [False]},
    {"name": "attributes/url_appointment",
     "valueType": "URL",
     "uriValues": [{"uri": "https://prolinksystems.com/contact.html"}]},
    {"name": "attributes/url_linkedin",
     "valueType": "URL",
     "uriValues": [{"uri": "https://www.linkedin.com/company/pro-link-systems"}]},
    {"name": "attributes/url_facebook",
     "valueType": "URL",
     "uriValues": [{"uri": "https://www.facebook.com/prolinksys"}]},
    {"name": "attributes/url_instagram",
     "valueType": "URL",
     "uriValues": [{"uri": "https://www.instagram.com/prolinksystems"}]},
]
# attributeMask entries use the FULL resource name ("attributes/<id>"),
# per locations.attributes.updateAttributes docs -- not the bare id.
ATTRIBUTE_MASK = ",".join(a["name"] for a in ATTRIBUTES)

# ---------------------------------------------------------------------------
# 4) MORE HOURS -- online service 24/7 (regular office hours NOT touched)
# ---------------------------------------------------------------------------
_DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
MORE_HOURS = [{
    "hoursTypeId": "ONLINE_SERVICE_HOURS",
    "periods": [
        {"openDay": d, "openTime": {"hours": 0},
         "closeDay": d, "closeTime": {"hours": 24}} for d in _DAYS
    ],
}]

# ---------------------------------------------------------------------------
# 5) WEBSITE with UTM
# ---------------------------------------------------------------------------
WEBSITE_URI = ("https://prolinksystems.com/"
               "?utm_source=google&utm_medium=organic&utm_campaign=gbp_profile")


def _log(msg):
    print(f"[batch1] {msg}", flush=True)


def _patch(url, token, body, what, apply):
    """PATCH with validateOnly unless --apply. Never raises."""
    sep = "&" if "?" in url else "?"
    if not apply:
        url = f"{url}{sep}validateOnly=true"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="PATCH",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
        _log(f"{'APPLIED' if apply else 'VALIDATED OK'}: {what}")
        return True, data
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode("utf-8", "replace")
        try:
            err = json.loads(body_txt).get("error", {})
            msg = f"HTTP {e.code} {err.get('status')}: {err.get('message')}"
            for d in err.get("details", []):
                for fv in d.get("fieldViolations", []) or []:
                    msg += f"\n      field={fv.get('field')} : {fv.get('description')}"
        except Exception:
            msg = f"HTTP {e.code}: {body_txt[:400]}"
        _log(f"FAILED: {what}\n      {msg}")
        return False, None
    except Exception as e:
        _log(f"FAILED: {what} ({e})")
        return False, None


def _resolve_place_ids(queries):
    """Places API (New) Text Search -> [{placeName, placeId}]. Returns None
    if no key is configured. Skips (and reports) any query that fails."""
    key = (os.environ.get("GOOGLE_MAPS_API_KEY") or
           os.environ.get("PLACES_API_KEY") or "").strip()
    if not key:
        return None
    out, failed = [], []
    for q in queries:
        req = urllib.request.Request(
            "https://places.googleapis.com/v1/places:searchText",
            data=json.dumps({"textQuery": q, "maxResultCount": 1}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json",
                     "X-Goog-Api-Key": key,
                     "X-Goog-FieldMask": "places.id,places.formattedAddress"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                places = json.loads(r.read().decode("utf-8")).get("places", [])
            if not places:
                failed.append(q); continue
            out.append({"placeName": places[0].get("formattedAddress", q),
                        "placeId": places[0]["id"]})
        except Exception as e:
            failed.append(f"{q} ({e})")
        time.sleep(0.15)
    if failed:
        _log("Place lookups that failed (fix or add in dashboard): "
             + "; ".join(failed))
    return out


def main():
    gbp_audit._load_secrets_env()
    args  = sys.argv[1:]
    apply = "--apply" in args
    only  = None
    if "--only" in args:
        only = set(args[args.index("--only") + 1].split(","))

    def want(step):
        return only is None or step in only

    token = gbp_post._resolve_access_token()
    mode  = "LIVE APPLY" if apply else "DRY RUN (validateOnly=true, no writes)"
    print("=" * 68); print(f"GBP BATCH 1  --  {mode}"); print("=" * 68)

    # ---- backup current state before any real write ---------------------
    cur, err = gbp_audit._get(f"{BI_API}/{LOCATION}?readMask={gbp_audit.READ_MASK}",
                              token, "Pre-change backup GET")
    if cur is None:
        _log("Cannot read the location -- aborting before any change."); sys.exit(1)
    if apply:
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bpath = os.path.join(HERE, f"gbp_backup_{ts}.json")
        with open(bpath, "w", encoding="utf-8") as fh:
            json.dump(cur, fh, indent=2, ensure_ascii=False)
        _log(f"Backup of current location saved -> {bpath}")

    # Guard: the parent category for services must be on the location.
    cats = cur.get("categories", {}) or {}
    on_loc = {(cats.get("primaryCategory") or {}).get("name")} | \
             {c.get("name") for c in cats.get("additionalCategories", []) or []}
    if SERVICE_PARENT_CATEGORY not in on_loc:
        _log(f"WARNING: {SERVICE_PARENT_CATEGORY} is not on the location; "
             "services step would fail. Skipping services.")
        skip_services = True
    else:
        skip_services = False

    results = {}
    base = f"{BI_API}/{LOCATION}"

    # 1) services ----------------------------------------------------------
    if want("services") and not skip_services:
        items = [{"freeFormServiceItem": {
                    "category": SERVICE_PARENT_CATEGORY,
                    "label": {"displayName": n, "description": d,
                              "languageCode": "en"}}}
                 for n, d in SERVICES]
        _log(f"services: replacing {len(cur.get('serviceItems', []) or [])} "
             f"current items with {len(items)}")
        results["services"] = _patch(f"{base}?updateMask=serviceItems", token,
                                     {"serviceItems": items},
                                     "serviceItems (15 services)", apply)[0]

    # 2) service area ------------------------------------------------------
    if want("area"):
        places = _resolve_place_ids(SERVICE_AREA_QUERIES)
        if places is None:
            _log("area: SKIPPED -- no GOOGLE_MAPS_API_KEY / PLACES_API_KEY in "
                 "secrets.env. Set the 20 cities in the GBP dashboard "
                 "(Edit profile > Location and areas), or add a Places API key "
                 "and re-run with --only area.")
            results["area"] = None
        else:
            _log(f"area: resolved {len(places)} of 20 places")
            for p in places:
                _log(f"    - {p['placeName']}  [{p['placeId']}]")
            if len(places) == 20:
                body = {"serviceArea": {"businessType": "CUSTOMER_LOCATION_ONLY",
                                        "places": {"placeInfos": places}}}
                results["area"] = _patch(f"{base}?updateMask=serviceArea", token,
                                         body, "serviceArea (20 places)", apply)[0]
            else:
                _log("area: not all 20 resolved -- NOT pushing a partial list. "
                     "Fix the failed lookups and re-run with --only area.")
                results["area"] = False

    # 3) attributes --------------------------------------------------------
    if want("attributes"):
        results["attributes"] = _patch(
            f"{base}/attributes?attributeMask={ATTRIBUTE_MASK}", token,
            {"attributes": ATTRIBUTES},
            "attributes (requires_appointments=false; appointment/LinkedIn/"
            "Facebook/Instagram URLs)", apply)[0]

    # 4) more hours --------------------------------------------------------
    if want("hours"):
        results["hours"] = _patch(f"{base}?updateMask=moreHours", token,
                                  {"moreHours": MORE_HOURS},
                                  "moreHours (ONLINE_SERVICE_HOURS 24/7)", apply)[0]

    # 5) website -----------------------------------------------------------
    if want("website"):
        results["website"] = _patch(f"{base}?updateMask=websiteUri", token,
                                    {"websiteUri": WEBSITE_URI},
                                    "websiteUri (+UTM)", apply)[0]

    # ---- summary ---------------------------------------------------------
    print("-" * 68)
    for k, v in results.items():
        status = {True: "OK", False: "FAILED", None: "SKIPPED"}[v]
        print(f"  {k:<11} {status}")
    print("-" * 68)
    if not apply:
        print("Dry run only -- nothing was written. Re-run with --apply to push.")
    else:
        print("Batch 1 applied. Re-run  python gbp_audit.py  to confirm, then wait a "
              "few days before Batch 2 (additional categories).")


if __name__ == "__main__":
    main()
