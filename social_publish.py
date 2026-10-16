"""
social_publish.py
-----------------
Step 3 of the 3x/week social pipeline. Reads pending.json (from social_render.py,
with its image already committed + pushed) and publishes the post + card to every
channel that is CONFIGURED.

Guardrail: prints a clear per-channel summary and fails the run (exit 1) ONLY when
a channel that has its credentials configured fails to post -- so a silently dead
token/credential turns the run RED instead of hiding behind a green check. Channels
that aren't set up yet (no creds) are skipped and never fail the run.

  - LinkedIn                : needs a LinkedIn token
  - Google Business Profile : needs a token + GBP_ACCOUNT_ID + GBP_LOCATION_ID
  - Instagram               : needs IG_USER_ID + IG_ACCESS_TOKEN
"""

import os
import sys
import json
import time
import urllib.request

import gbp_post
import linkedin_post
import instagram_post
import facebook_post
import x_post

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "pending.json")

# Public, immediately-available URL for the just-pushed card image.
RAW_BASE = os.environ.get(
    "SOCIAL_IMG_BASE",
    "https://raw.githubusercontent.com/brianshad-usa/main/main/social/",
)


def _has(*names):
    """True only if every named env var is set and non-empty."""
    return all(os.environ.get(n, "").strip() for n in names)


def _url_live(url, tries=6, delay=5):
    """Confirm a public image URL actually serves (HTTP 200) before handing it to
    a channel that publishes by FETCHING the image by URL (GBP, Instagram,
    Facebook). A freshly pushed raw.githubusercontent.com asset can lag a few
    seconds behind the push, and if the push never landed at all the URL 404s
    forever -- either way, handing Meta/Google a dead URL produces a cryptic
    "media could not be fetched" failure. A short poll absorbs propagation lag;
    a persistent miss returns False so the caller can skip that channel with a
    clear reason instead of a confusing downstream error. LinkedIn is unaffected
    (it uploads the local file, not a URL)."""
    req = urllib.request.Request(url, method="HEAD")
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                if 200 <= getattr(r, "status", 200) < 300:
                    return True
        except Exception as e:
            print(f"[publish] image URL not live yet (try {i + 1}/{tries}): {e}")
        if i < tries - 1:
            time.sleep(delay)
    return False


# Site homepage: the always-live fallback destination when a theme carries no
# specific cta_url (e.g. the CALL theme). Verified 200.
HOME_URL = "https://prolinksystems.com/"

HERE = os.path.dirname(os.path.abspath(__file__))
_SITEMAP = os.path.join(HERE, "sitemap.xml")


def _live_paths():
    """Normalized set of real published page paths (from sitemap.xml + the repo's
    own .html pages). Used as a last-resort check so a stale/legacy manifest can
    never publish a link to a page that doesn't exist. content_studio.py already
    validates cta_url at generation; this is defense in depth at publish time."""
    import re
    paths = set()
    try:
        with open(_SITEMAP, encoding="utf-8") as f:
            for loc in re.findall(r"<loc>\s*(.*?)\s*</loc>", f.read()):
                paths.add(_norm_path(loc))
    except OSError:
        pass
    try:
        for fn in os.listdir(HERE):
            if fn.endswith(".html"):
                stem = fn[:-5]
                paths.add("/" if stem == "index" else _norm_path("/" + stem))
    except OSError:
        pass
    paths.add("/")
    return paths


def _norm_path(url):
    import re
    u = (url or "").strip()
    u = re.sub(r"^https?://[^/]+", "", u, flags=re.IGNORECASE)
    u = u.split("#", 1)[0].split("?", 1)[0]
    if not u.startswith("/"):
        u = "/" + u
    if u.lower().endswith(".html"):
        u = u[:-5]
    if len(u) > 1:
        u = u.rstrip("/")
    return u.lower() or "/"


def _ensure_live_url(cta_url):
    """Return cta_url if it points at a real page; else the homepage (always live).
    Prevents a post from ever shipping a 404 CTA."""
    if not (cta_url or "").strip():
        return HOME_URL
    if _norm_path(cta_url) in _live_paths():
        return cta_url
    print(f"[publish] CTA url '{cta_url}' is not a live page - falling back to {HOME_URL}")
    return HOME_URL


def _with_cta_link(text, cta_label, cta_url):
    """Return post copy with a REAL, clickable CTA + URL appended.

    A feed image is not clickable, so the card's on-image CTA is a caption only --
    the working link has to live in the post text. LinkedIn (and Facebook/X)
    auto-linkify a bare URL in the body, so appending 'Label: https://...' gives
    viewers an actual path to follow. No-ops if a link to that page is already in
    the copy, so editorial copy that already includes the URL isn't doubled up."""
    text = (text or "").strip()
    url = (cta_url or "").strip() or HOME_URL
    if url.rstrip("/").lower() in text.lower():
        return text
    label = (cta_label or "Learn more").strip().rstrip(".:→> ") or "Learn more"
    return f"{text}\n\n{label}: {url}"


def main():
    with open(MANIFEST, encoding="utf-8") as f:
        m = json.load(f)

    # Manifests produced by `content_studio.py --offline` are structure tests
    # and must never reach a channel, no matter how the workflow was invoked.
    if m.get("offline_test"):
        print("::error::pending.json is an offline test manifest - refusing to publish.")
        sys.exit(1)

    # Dead-link guard (last resort): never publish a CTA to a page that doesn't
    # exist. Applied once here so every channel - the appended LinkedIn link and
    # the GBP button URL alike - uses a validated destination.
    m["cta_url"] = _ensure_live_url(m.get("cta_url"))

    # Per-channel copy from the editorial pipeline; the legacy single-text
    # manifest (m["post"] only) still works unchanged as the fallback.
    per = m.get("channels", {})
    post = m["post"]
    # LinkedIn: the card's CTA is only a caption on the image (not tappable), so
    # put the real clickable CTA + destination URL in the post copy itself.
    li_text = _with_cta_link(
        per.get("linkedin") or post, m.get("cta_label"), m.get("cta_url")
    )
    fb_text = per.get("facebook") or post
    gbp_text = per.get("gbp") or post
    ig_caption = per.get("instagram_caption") or post
    # X copy: dedicated key if the editorial pipeline provides one, else the
    # shared post text; x_post.fit_280 handles the length limit either way.
    x_text = per.get("x") or per.get("twitter") or post

    headline = m.get("headline", "Pro Link Systems")
    image_url = RAW_BASE + m["image_file"]
    ig_image_url = RAW_BASE + m.get("image_file_jpg", m["image_file"])
    local_image = os.path.join(HERE, "social", m["image_file"])

    # Instagram: carousel when the manifest carries slides, single image otherwise.
    carousel_jpgs = (m.get("carousel") or {}).get("jpg") or []
    carousel_urls = [RAW_BASE + name for name in carousel_jpgs]

    def do_instagram():
        if len(carousel_urls) >= 2:
            return instagram_post.maybe_post_carousel(ig_caption, carousel_urls)
        return instagram_post.maybe_post(ig_caption, ig_image_url)

    # The image URL Instagram will try to fetch (first carousel slide, else the
    # single card jpg) -- used for the pre-flight liveness check below.
    ig_dep_url = carousel_urls[0] if len(carousel_urls) >= 2 else ig_image_url

    # (name, is_configured, attempt, dep_url) -- attempt() returns a truthy id on
    # success, None on failure. dep_url is the public image URL the channel must
    # fetch (None for channels that upload the local file, like LinkedIn); it is
    # pre-flighted for HTTP 200 before the attempt so a channel is never handed a
    # dead/not-yet-propagated URL.
    channels = [
        (
            "LinkedIn",
            _has("LINKEDIN_REFRESH_TOKEN") or _has("LINKEDIN_ACCESS_TOKEN"),
            lambda: linkedin_post.maybe_post_image(li_text, local_image, alt_text=headline),
            None,
        ),
        (
            "GBP",
            (_has("GBP_REFRESH_TOKEN") or _has("GBP_ACCESS_TOKEN"))
            and _has("GBP_ACCOUNT_ID", "GBP_LOCATION_ID"),
            lambda: gbp_post.maybe_post(
                gbp_text, m.get("cta_type", "LEARN_MORE"), m.get("cta_url"), image_url=image_url
            ),
            image_url,
        ),
        (
            "Instagram",
            _has("IG_USER_ID", "IG_ACCESS_TOKEN"),
            do_instagram,
            ig_dep_url,
        ),
        (
            "Facebook",
            _has("FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"),
            lambda: facebook_post.maybe_post(fb_text, image_url),
            image_url,
        ),
        (
            "X",
            # Deliberately OFF by default even with creds present: X API posting
            # is paywalled (402 credits-depleted, 2026-08) and posting is manual
            # for now. Arm by setting the repo Actions VARIABLE X_ENABLED=1 --
            # credentials alone must never turn this channel on.
            _has("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")
            and os.environ.get("X_ENABLED", "").strip() == "1",
            lambda: x_post.maybe_post(x_text, local_image),
            None,
        ),
    ]

    summary = []
    failures = []
    url_live_cache = {}

    def _dep_ok(url):
        """Memoized HTTP-200 pre-flight for a channel's image URL."""
        if url not in url_live_cache:
            url_live_cache[url] = _url_live(url)
        return url_live_cache[url]

    for name, configured, attempt, dep_url in channels:
        if not configured:
            summary.append(f"  [skipped] {name} (not configured)")
            continue
        # Pre-flight: never hand a URL-fetching channel an image that isn't live.
        if dep_url and not _dep_ok(dep_url):
            print(f"[{name.lower()}] image URL is not reachable (HTTP != 200): {dep_url} "
                  f"- skipping to avoid a 'media could not be fetched' failure.")
            summary.append(f"  [FAILED]  {name} (image URL not live: {dep_url})")
            failures.append(name)
            continue
        # Fault isolation: a channel that RAISES (rather than returning None) must
        # not abort the loop and take the other channels down with it -- the newly
        # added GBP channel especially must degrade, not nuke the run.
        try:
            result = attempt()
        except Exception as e:
            print(f"[{name.lower()}] ERROR (isolated, pipeline unaffected): {e}")
            result = None
        if result:
            summary.append(f"  [posted]  {name}")
        else:
            summary.append(f"  [FAILED]  {name} (see the log above for the reason)")
            failures.append(name)

    print("\n===== SOCIAL PUBLISH SUMMARY =====")
    for line in summary:
        print(line)
    print("==================================\n")

    if failures:
        # GitHub Actions annotation + non-zero exit => the run goes RED.
        print("::error::Social publish FAILED for configured channel(s): " + ", ".join(failures))
        sys.exit(1)


if __name__ == "__main__":
    main()
