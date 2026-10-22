#!/usr/bin/env python3
"""
announce_blog.py — Post a blog article to the company LinkedIn page ONLY after it
is actually live.

Why this exists: the generator used to post to LinkedIn the moment it created a
post — before the post was merged to main and deployed. On 2026-10-21 the post's
PR never got created, so LinkedIn announced a URL that 404'd. This script closes
that gap: it runs AFTER a post lands on main (via .github/workflows/announce-blog.yml),
confirms the URL returns HTTP 200 (Cloudflare has deployed it), and only then posts.

It announces exactly the post(s) ADDED by the push that triggered it (from the git
diff), so old queued posts are never re-announced. For manual recovery, pass a slug
(or set ANNOUNCE_SLUG) to announce one specific post.

LinkedIn posting goes through linkedin_post.maybe_post(), which never raises and
no-ops cleanly if the LinkedIn secrets are missing.
"""
import os
import sys
import json
import time
import subprocess
import urllib.request

PENDING_DIR = "editorial/pending_linkedin"


def _url_is_live(url, tries=18, delay=20):
    """Poll the URL until it returns HTTP 200 (Cloudflare deploy can lag a minute
    or two after merge). Returns True as soon as it's live, else False after ~6 min."""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, method="GET",
                                         headers={"User-Agent": "ProLink-Announce/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                if getattr(r, "status", r.getcode()) == 200:
                    print(f"[announce] live after {i*delay}s: {url}")
                    return True
        except Exception as e:
            print(f"[announce]   not live yet ({type(e).__name__}); attempt {i+1}/{tries}")
        if i < tries - 1:
            time.sleep(delay)
    return False


def _new_blog_slugs_from_push():
    before = (os.environ.get("GITHUB_EVENT_BEFORE") or "").strip()
    sha = (os.environ.get("GITHUB_SHA") or "").strip()
    slugs = []
    if before and sha and not before.startswith("0000000"):
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", "--diff-filter=A", before, sha], text=True)
            for line in out.splitlines():
                line = line.strip()
                if (line.startswith("blog/") and line.endswith(".html")
                        and line != "blog/index.html"):
                    slugs.append(os.path.basename(line)[:-5])
        except Exception as e:
            print(f"[announce] could not diff push ({e}); nothing to announce from diff.", file=sys.stderr)
    return slugs


def _load_pending(slug):
    p = os.path.join(PENDING_DIR, f"{slug}.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception as e:
            print(f"[announce] bad sidecar {p}: {e}", file=sys.stderr)
    return None


def announce(slug):
    data = _load_pending(slug)
    if not data:
        print(f"[announce] no pending sidecar for '{slug}'; skipping.", file=sys.stderr)
        return False
    url = data.get("url") or f"https://prolinksystems.com/blog/{slug}"
    print(f"[announce] verifying {url} is live before posting…")
    if not _url_is_live(url):
        print(f"[announce] {url} did not go live in time; NOT posting (safe — no dead link). "
              f"Re-run this workflow with slug='{slug}' once it deploys.", file=sys.stderr)
        return False
    import linkedin_post
    linkedin_post.maybe_post(title=data.get("title", ""), url=url,
                             summary=data.get("summary", ""), caption=data.get("caption", ""))
    print(f"[announce] posted '{slug}' to LinkedIn.")
    return True


def main():
    slug_arg = sys.argv[1].strip() if len(sys.argv) > 1 and sys.argv[1].strip() else ""
    slug_env = (os.environ.get("ANNOUNCE_SLUG") or "").strip()
    if slug_arg:
        targets = [slug_arg]
    elif slug_env:
        targets = [slug_env]
    else:
        targets = _new_blog_slugs_from_push()

    if not targets:
        print("[announce] no new blog posts in this push; nothing to announce.")
        return

    for slug in targets:
        try:
            announce(slug)
        except Exception as e:  # maybe_post shouldn't raise, but never let one post break another
            print(f"[announce] WARNING: announcing '{slug}' failed (non-fatal): {e!r}", file=sys.stderr)


if __name__ == "__main__":
    main()
