"""
social_publish.py
-----------------
Step 3 of the 3x/week social pipeline. Reads pending.json (from social_render.py,
with its image already committed + pushed) and publishes the post + card to every
channel that has credentials configured. Each channel uses a safe maybe_post()
wrapper, so a missing/expired credential on one channel never blocks the others.

  - Google Business Profile : needs a public image URL (uses the pushed raw URL)
  - LinkedIn                : uploads the image binary from disk
  - Instagram               : needs a public image URL (dormant until creds added)
"""

import os
import json

import gbp_post
import linkedin_post
import instagram_post

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "pending.json")

# Public, immediately-available URL for the just-pushed card image.
# Repo brianshad-usa/main, default branch main, images under social/.
RAW_BASE = os.environ.get(
    "SOCIAL_IMG_BASE",
    "https://raw.githubusercontent.com/brianshad-usa/main/main/social/",
)


def main():
    with open(MANIFEST, encoding="utf-8") as f:
        m = json.load(f)

    post = m["post"]
    headline = m.get("headline", "Pro Link Systems")
    image_url = RAW_BASE + m["image_file"]
    local_image = os.path.join(HERE, "social", m["image_file"])

    print(f"[publish] image_url: {image_url}")
    print(f"[publish] local image exists: {os.path.exists(local_image)}")

    # Google Business Profile (public image URL)
    gbp_post.maybe_post(
        post,
        cta_type=m.get("cta_type", "LEARN_MORE"),
        cta_url=m.get("cta_url"),
        image_url=image_url,
    )

    # LinkedIn company page (binary upload)
    linkedin_post.maybe_post_image(post, local_image, alt_text=headline)

    # Instagram business account (public image URL)
    instagram_post.maybe_post(post, image_url)


if __name__ == "__main__":
    main()
