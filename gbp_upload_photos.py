"""
gbp_upload_photos.py -- push photos in assets/gbp/ to the Google Business Profile.
=================================================================================
GBP's media API pulls each photo from a PUBLIC URL, so the files must already be
deployed at https://prolinksystems.com/assets/gbp/<name>.jpg (the auto-commit
watcher + Cloudflare Pages do that within a few minutes of the files landing in
the repo). The script checks every URL returns 200 before posting anything.

Ledger: gbp_media_log.json (sha1 of file -> GBP media name). A photo whose
content hash is in the ledger is skipped, so re-runs never duplicate.

    python gbp_upload_photos.py              # dry run: shows what would post
    python gbp_upload_photos.py --apply      # upload
    python gbp_upload_photos.py --apply --only office-exterior,monitoring-displays

Category map below uses GBP's own buckets (EXTERIOR / TEAMS / AT_WORK / INTERIOR).
Anything not mapped goes to ADDITIONAL.
"""
import os, sys, json, glob, hashlib, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gbp_audit, gbp_post

HERE   = os.path.dirname(os.path.abspath(__file__))
SRC    = os.path.join(HERE, "assets", "gbp")
LEDGER = os.path.join(HERE, "gbp_media_log.json")
BASE   = "https://prolinksystems.com/assets/gbp/"
V4     = gbp_audit.V4_API

CATEGORY = {
    "office-exterior":          "EXTERIOR",
    "office-workstation":       "INTERIOR",
    "monitoring-displays":      "INTERIOR",
    "conference-room-meeting":  "INTERIOR",
    "front-desk-support":       "INTERIOR",
    "office-team-at-work":      "TEAMS",
    "leadership-interview":     "TEAMS",
    "headset-support":          "AT_WORK",
    "onsite-assistance":        "AT_WORK",
    "onsite-computer-support":  "AT_WORK",
    "server-rack-support":      "AT_WORK",
    "workstation-consultation": "AT_WORK",
    "client-consultation":      "AT_WORK",
    "technology-planning":      "AT_WORK",
}
DESCRIPTION = {
    "office-exterior":          "Pro Link Systems headquarters on Ventura Blvd, Woodland Hills",
    "office-team-at-work":      "The Pro Link Systems team at work in our Woodland Hills office",
    "leadership-interview":     "Pro Link Systems leadership",
    "monitoring-displays":      "24/7 monitoring at Pro Link Systems",
    "server-rack-support":      "On-site server and network support",
    "headset-support":          "Live help desk - a real engineer answers every call",
    "onsite-computer-support":  "On-site computer support for Los Angeles businesses",
    "client-consultation":      "Client IT consultation",
    "technology-planning":      "Technology planning session",
}


def _sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _head_ok(url):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    gbp_audit._load_secrets_env()
    args  = sys.argv[1:]
    apply = "--apply" in args
    only  = set(args[args.index("--only") + 1].split(",")) if "--only" in args else None
    a = os.environ.get("GBP_ACCOUNT_ID", "").strip() or gbp_audit.DEFAULT_ACCOUNT_ID
    l = os.environ.get("GBP_LOCATION_ID", "").strip() or gbp_audit.DEFAULT_LOCATION_ID
    ledger = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {"uploaded": {}}
    token = gbp_post._resolve_access_token()

    files = sorted(glob.glob(os.path.join(SRC, "*.jpg")))
    plan, skipped, notlive = [], [], []
    for p in files:
        name = os.path.splitext(os.path.basename(p))[0]
        if only and name not in only:
            continue
        h = _sha1(p)
        if h in ledger["uploaded"]:
            skipped.append(name); continue
        url = BASE + os.path.basename(p)
        if not _head_ok(url):
            notlive.append(name); continue
        plan.append((name, h, url, CATEGORY.get(name, "ADDITIONAL"), DESCRIPTION.get(name)))

    print(f"already on GBP (ledger): {len(skipped)}  | not yet live on site: {len(notlive)}  | to upload: {len(plan)}")
    for n in notlive: print("   not live yet:", n, "-> wait for deploy, re-run")
    for n, h, url, cat, desc in plan: print(f"   {cat:<10} {n}  ({desc or 'no caption'})")
    if not apply:
        print("\nDry run -- nothing uploaded. Add --apply to post."); return

    ok = fail = 0
    for n, h, url, cat, desc in plan:
        body = {"mediaFormat": "PHOTO", "sourceUrl": url,
                "locationAssociation": {"category": cat}}
        if desc: body["description"] = desc
        req = urllib.request.Request(
            f"{V4}/accounts/{a}/locations/{l}/media",
            data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.loads(r.read().decode("utf-8"))
            ledger["uploaded"][h] = {"file": n, "media": res.get("name"), "category": cat,
                                     "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            json.dump(ledger, open(LEDGER, "w"), indent=2)
            print("UPLOADED", n, "->", res.get("name")); ok += 1
        except urllib.error.HTTPError as e:
            print("FAILED  ", n, e.code, e.read().decode("utf-8", "replace")[:300]); fail += 1
        time.sleep(1.5)
    print(f"\nuploaded={ok} failed={fail}. Ledger: {LEDGER}")


if __name__ == "__main__":
    main()
