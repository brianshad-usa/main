"""
gbp_reviews.py  --  List unreplied Google reviews, then post approved replies.
==============================================================================
Two-step so no reply goes public unread:

  Step 1  python gbp_reviews.py --fetch
          Reads ALL reviews (paginated, read-only), prints the ones with NO
          owner reply, and writes them to  gbp_reviews_pending.json  with an
          empty "reply" slot for each.

  Step 2  (replies are drafted into that file -- one per review)
          python gbp_reviews.py --post            # dry run: shows what would post
          python gbp_reviews.py --post --apply    # posts replies

Posting uses My Business API v4:
    PUT accounts/{a}/locations/{l}/reviews/{reviewId}/reply  {"comment": "..."}
Before posting each reply the script re-checks live that the review still has
no owner reply, so nothing is ever double-posted. Entries with an empty
"reply" are skipped. Review comments are capped at 4096 chars by Google.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gbp_audit
import gbp_post

V4   = gbp_audit.V4_API
HERE = os.path.dirname(os.path.abspath(__file__))
PENDING = os.path.join(HERE, "gbp_reviews_pending.json")

STARS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}


def _log(m):
    print(f"[reviews] {m}", flush=True)


def _ids():
    a = os.environ.get("GBP_ACCOUNT_ID", "").strip() or gbp_audit.DEFAULT_ACCOUNT_ID
    l = os.environ.get("GBP_LOCATION_ID", "").strip() or gbp_audit.DEFAULT_LOCATION_ID
    return a, l


def _all_reviews(token):
    a, l = _ids()
    out, page = [], None
    while True:
        url = f"{V4}/accounts/{a}/locations/{l}/reviews?pageSize=50"
        if page:
            url += f"&pageToken={page}"
        data, err = gbp_audit._get(url, token, "Reviews page")
        if not data:
            break
        out.extend(data.get("reviews", []))
        page = data.get("nextPageToken")
        if not page:
            break
    return out


def fetch(token):
    reviews = _all_reviews(token)
    unreplied = [r for r in reviews if not r.get("reviewReply")]
    _log(f"{len(reviews)} reviews total; {len(unreplied)} with NO owner reply")
    pending = []
    print("=" * 68)
    for r in sorted(unreplied, key=lambda x: x.get("createTime", ""), reverse=True):
        rid   = r.get("reviewId") or r.get("name", "").split("/")[-1]
        who   = (r.get("reviewer") or {}).get("displayName", "Anonymous")
        stars = STARS.get(r.get("starRating"), "?")
        when  = (r.get("createTime") or "")[:10]
        text  = (r.get("comment") or "").strip()
        print(f"[{rid}]  {stars}★  {when}  {who}")
        print(f"    {text if text else '(no text -- star rating only)'}")
        print()
        pending.append({"reviewId": rid, "reviewer": who, "stars": stars,
                        "date": when, "comment": text, "reply": ""})
    with open(PENDING, "w", encoding="utf-8") as fh:
        json.dump(pending, fh, indent=2, ensure_ascii=False)
    _log(f"Wrote {len(pending)} pending review(s) -> {PENDING}")
    _log("Paste the block above; replies get drafted into that file's \"reply\" slots.")


def post(token, apply):
    if not os.path.exists(PENDING):
        _log("No gbp_reviews_pending.json -- run --fetch first."); return
    with open(PENDING, encoding="utf-8") as fh:
        pending = json.load(fh)
    live = {(r.get("reviewId") or r.get("name", "").split("/")[-1]): r
            for r in _all_reviews(token)}
    a, l = _ids()
    posted = skipped = failed = 0
    for p in pending:
        rid, reply = p["reviewId"], (p.get("reply") or "").strip()
        if not reply:
            _log(f"skip {rid} ({p['reviewer']}): empty reply"); skipped += 1; continue
        if rid not in live:
            _log(f"skip {rid}: review no longer found"); skipped += 1; continue
        if live[rid].get("reviewReply"):
            _log(f"skip {rid} ({p['reviewer']}): already has an owner reply"); skipped += 1; continue
        print("-" * 68)
        print(f"{p['stars']}★ {p['date']} {p['reviewer']}: {p['comment'][:140]}")
        print(f"  REPLY -> {reply}")
        if not apply:
            continue
        req = urllib.request.Request(
            f"{V4}/accounts/{a}/locations/{l}/reviews/{rid}/reply",
            data=json.dumps({"comment": reply[:4096]}).encode("utf-8"),
            method="PUT",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
            _log(f"POSTED reply to {rid} ({p['reviewer']})"); posted += 1
        except urllib.error.HTTPError as e:
            _log(f"FAILED {rid}: HTTP {e.code} {e.read().decode('utf-8','replace')[:300]}")
            failed += 1
        time.sleep(0.5)
    print("-" * 68)
    if apply:
        _log(f"posted={posted} skipped={skipped} failed={failed}")
    else:
        _log("Dry run -- nothing posted. Add --apply to post the replies above.")


def main():
    gbp_audit._load_secrets_env()
    args = sys.argv[1:]
    token = gbp_post._resolve_access_token()
    if "--fetch" in args:
        fetch(token)
    elif "--post" in args:
        post(token, apply="--apply" in args)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
