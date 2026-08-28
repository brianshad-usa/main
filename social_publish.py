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


# Site homepage: the always-live fallback destination when a theme carries no
# specific cta_url (e.g. the CALL theme). Verified 200.
HOME_URL = "https://prolinksystems.com/"


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

    # (name, is_configured, attempt) -- attempt() returns a truthy id on success, None on failure.
    channels = [
        (
            "LinkedIn",
            _has("LINKEDIN_REFRESH_TOKEN") or _has("LINKEDIN_ACCESS_TOKEN"),
            lambda: linkedin_post.maybe_post_image(li_text, local_image, alt_text=headline),
        ),
        (
            "GBP",
            (_has("GBP_REFRESH_TOKEN") or _has("GBP_ACCESS_TOKEN"))
            and _has("GBP_ACCOUNT_ID", "GBP_LOCATION_ID"),
            lambda: gbp_post.maybe_post(
                gbp_text, m.get("cta_type", "LEARN_MORE"), m.get("cta_url"), image_url=image_url
            ),
        ),
        (
            "Instagram",
            _has("IG_USER_ID", "IG_ACCESS_TOKEN"),
            do_instagram,
        ),
        (
            "Facebook",
            _has("FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"),
            lambda: facebook_post.maybe_post(fb_text, image_url),
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
        ),
    ]

    summary = []
    failures = []
    for name, configured, attempt in channels:
        if not configured:
            summary.append(f"  [skipped] {name} (not configured)")
            continue
        result = attempt()
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
