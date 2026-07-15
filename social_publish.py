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


def main():
    with open(MANIFEST, encoding="utf-8") as f:
        m = json.load(f)

    post = m["post"]
    headline = m.get("headline", "Pro Link Systems")
    image_url = RAW_BASE + m["image_file"]
    ig_image_url = RAW_BASE + m.get("image_file_jpg", m["image_file"])
    local_image = os.path.join(HERE, "social", m["image_file"])

    # (name, is_configured, attempt) -- attempt() returns a truthy id on success, None on failure.
    channels = [
        (
            "LinkedIn",
            _has("LINKEDIN_REFRESH_TOKEN") or _has("LINKEDIN_ACCESS_TOKEN"),
            lambda: linkedin_post.maybe_post_image(post, local_image, alt_text=headline),
        ),
        (
            "GBP",
            (_has("GBP_REFRESH_TOKEN") or _has("GBP_ACCESS_TOKEN"))
            and _has("GBP_ACCOUNT_ID", "GBP_LOCATION_ID"),
            lambda: gbp_post.maybe_post(
                post, m.get("cta_type", "LEARN_MORE"), m.get("cta_url"), image_url=image_url
            ),
        ),
        (
            "Instagram",
            _has("IG_USER_ID", "IG_ACCESS_TOKEN"),
            lambda: instagram_post.maybe_post(post, ig_image_url),
        ),
        (
            "Facebook",
            _has("FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"),
            lambda: facebook_post.maybe_post(post, image_url),
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
