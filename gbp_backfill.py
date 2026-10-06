"""
gbp_backfill.py
---------------
Paced backfill of already-published blog posts to the Pro Link Systems Google
Business Profile as "What's new" (STANDARD) local posts, each with a
"Learn more" button linking to the blog article.

WHY THIS IS PACED (do NOT bulk-post):
  Google flags a sudden burst of local posts as spam, and GBP posts age out
  after ~6 months anyway. So this script posts only a SMALL number per run
  (default 2) and is meant to be driven by a daily scheduled job, dripping the
  archive out over a few weeks. State is persisted so it always resumes cleanly
  and NEVER double-posts the same article.

SOURCE OF TRUTH:
  The published set is taken from sitemap.xml (the <loc> entries under /blog/).
  That is exactly what is publicly indexed, so superseded/unindexed duplicate
  files in blog/ are not posted. Each URL is mapped back to its blog/<slug>.html
  to pull the title, summary and representative image.

STATE / LEDGER:
  gbp_backfill_log.json in the repo root records every URL already posted, with
  the returned localPost resource name and a UTC timestamp. Resuming is just
  "skip anything already in the log".

USAGE:
  python gbp_backfill.py --check          # show progress, post nothing
  python gbp_backfill.py --dry-run        # build the next batch, post nothing
  python gbp_backfill.py                  # post the next batch (default 2)
  python gbp_backfill.py --max 1          # post the next 1
  GBP_BACKFILL_PER_RUN=3 python gbp_backfill.py   # pace via env var

Daily pacing is handled by .github/workflows/gbp-backfill.yml (cron), which runs
this with --max set to the agreed per-day count and commits the updated ledger.

Credentials are the SAME GBP GitHub secrets already used by social_publish.py
(GBP_CLIENT_ID / GBP_CLIENT_SECRET / GBP_REFRESH_TOKEN / GBP_ACCOUNT_ID /
GBP_LOCATION_ID). Nothing new to configure.
"""

import os
import re
import sys
import json
import html
import datetime

import gbp_post

HERE = os.path.dirname(os.path.abspath(__file__))
SITEMAP = os.path.join(HERE, "sitemap.xml")
BLOG_DIR = os.path.join(HERE, "blog")
LOG_PATH = os.path.join(HERE, "gbp_backfill_log.json")

SITE = "https://prolinksystems.com"
DEFAULT_PER_RUN = 2          # conservative, spam-safe default
HARD_CAP_PER_RUN = 5         # safety rail: never post more than this in one run
DEFAULT_IMAGE = f"{SITE}/logo.png"


def _log(msg):
    print(f"[gbp-backfill] {msg}", flush=True)


# --------------------------------------------------------------------------
# Inventory
# --------------------------------------------------------------------------
def blog_urls_from_sitemap():
    """Return published blog URLs (chronological, oldest first) from sitemap.xml."""
    with open(SITEMAP, "r", encoding="utf-8") as fh:
        xml = fh.read()
    urls = re.findall(r"<loc>\s*([^<]+?/blog/[^<]+?)\s*</loc>", xml)
    # Normalise + de-dupe, keep order by slug (slugs start with YYYY-MM-DD).
    seen, cleaned = set(), []
    for u in urls:
        u = html.unescape(u.strip()).rstrip("/")
        if u.endswith("/blog") or u.endswith("/blog/index"):
            continue
        if u not in seen:
            seen.add(u)
            cleaned.append(u)
    cleaned.sort(key=lambda u: u.rsplit("/blog/", 1)[-1])
    return cleaned


def _slug_of(url):
    return url.rsplit("/blog/", 1)[-1]


def _meta(content, prop_patterns):
    for pat in prop_patterns:
        m = re.search(pat, content, re.IGNORECASE)
        if m:
            return html.unescape(m.group(1)).strip()
    return ""


def post_meta(url):
    """Pull title, summary and image for a blog URL from its HTML file."""
    path = os.path.join(BLOG_DIR, _slug_of(url) + ".html")
    title = summary = image = ""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            c = fh.read()
        title = _meta(c, [r'<meta property="og:title" content="([^"]+)"',
                          r"<title>([^<]+)</title>"])
        summary = _meta(c, [r'<meta name="description" content="([^"]+)"',
                            r'<meta property="og:description" content="([^"]+)"'])
        image = _meta(c, [r'<meta property="og:image" content="([^"]+)"'])
    # Strip the site suffix from the title for a cleaner hook.
    title = re.sub(r"\s*\|\s*Pro Link Systems\s*$", "", title).strip()
    return {
        "title": title,
        "summary": summary,
        "image": image or DEFAULT_IMAGE,
    }


def build_summary(meta):
    """Compose a short, engaging GBP post body (kept well under 1500 chars)."""
    title = meta["title"]
    desc = meta["summary"]
    parts = []
    if title:
        parts.append(title)
    if desc and desc.lower() != title.lower():
        parts.append(desc)
    parts.append("Read the full article →")
    body = "\n\n".join(parts)
    # Stay comfortably short (engaging, not a wall of text).
    if len(body) > 1400:
        body = body[:1397].rstrip() + "..."
    return body


# --------------------------------------------------------------------------
# Ledger
# --------------------------------------------------------------------------
def load_log():
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            data = {}
    else:
        data = {}
    data.setdefault("posted", {})   # url -> {name, posted_at, title}
    return data


def save_log(data):
    with open(LOG_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------
def pick_per_run(cli_max):
    if cli_max is not None:
        n = cli_max
    else:
        try:
            n = int(os.environ.get("GBP_BACKFILL_PER_RUN", DEFAULT_PER_RUN))
        except ValueError:
            n = DEFAULT_PER_RUN
    return max(0, min(n, HARD_CAP_PER_RUN))


def remaining(log):
    done = set(log["posted"].keys())
    return [u for u in blog_urls_from_sitemap() if u not in done]


def cmd_check():
    log = load_log()
    all_urls = blog_urls_from_sitemap()
    todo = remaining(log)
    _log(f"published blog posts in sitemap : {len(all_urls)}")
    _log(f"already posted to GBP           : {len(log['posted'])}")
    _log(f"remaining to backfill           : {len(todo)}")
    if todo:
        _log(f"next up: {_slug_of(todo[0])}")
    return 0


def run(cli_max=None, dry_run=False):
    log = load_log()
    todo = remaining(log)
    per_run = pick_per_run(cli_max)
    batch = todo[:per_run]

    _log(f"remaining={len(todo)} per_run={per_run} dry_run={dry_run}")
    if not batch:
        _log("Nothing to do -- backfill complete or per_run=0.")
        return 0

    posted_now = 0
    for url in batch:
        meta = post_meta(url)
        summary = build_summary(meta)
        _log(f"-> {_slug_of(url)}  (img={meta['image']})")
        if dry_run:
            print("----- DRY RUN POST BODY -----")
            print(summary)
            print(f"[CTA] LEARN_MORE -> {url}")
            print("-----------------------------")
            continue
        try:
            name = gbp_post.post_update(
                summary,
                cta_type="LEARN_MORE",
                cta_url=url,
                image_url=meta["image"],
            )
        except Exception as e:
            _log(f"FAILED {url}: {e}")
            # Stop the batch on first failure so we don't hammer a bad token.
            break
        log["posted"][url] = {
            "name": name,
            "title": meta["title"],
            "posted_at": datetime.datetime.now(datetime.timezone.utc)
            .isoformat(timespec="seconds"),
        }
        save_log(log)          # persist after EACH post -> always resumable
        posted_now += 1
        _log(f"   posted: {name}")

    if not dry_run:
        _log(f"Done. Posted {posted_now} this run. "
             f"{len(remaining(log))} remaining.")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] in ("--check", "-c", "check"):
        sys.exit(cmd_check())
    dry = False
    cli_max = None
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--dry-run", "-n"):
            dry = True
        elif a in ("--max", "-m") and i + 1 < len(args):
            cli_max = int(args[i + 1]); i += 1
        i += 1
    sys.exit(run(cli_max=cli_max, dry_run=dry))
