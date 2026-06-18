"""
social_render.py
----------------
Step 1 of the 3x/week social pipeline (see .github/workflows/social-3x-week.yml).

Picks the day's theme, asks Claude for the post text + a short graphic headline +
a CTA button label, renders the branded card to social/<date>-<theme>.png, and
writes pending.json for social_publish.py to consume.

Reuses the rotating THEMES from generate_gbp_post.py so GBP keeps the same voice.

Env: ANTHROPIC_API_KEY
Usage: python social_render.py [theme_index 0-7]   (blank arg = auto-rotate by day)
"""

import os
import sys
import json
import datetime

import anthropic
import social_graphic
from generate_gbp_post import THEMES

HERE = os.path.dirname(os.path.abspath(__file__))
SOCIAL_DIR = os.path.join(HERE, "social")
MANIFEST = os.path.join(HERE, "pending.json")

DEFAULT_CTA_LABEL = {
    "BOOK_APPOINTMENT": "Book a free assessment",
    "CALL": "Call us today",
    "LEARN_MORE": "Learn more",
    "SIGN_UP": "Get started",
    "SHOP": "Learn more",
    "ORDER": "Learn more",
}


def pick_theme():
    idx = datetime.date.today().timetuple().tm_yday % len(THEMES)
    if len(sys.argv) > 1 and sys.argv[1].strip():
        try:
            idx = int(sys.argv[1]) % len(THEMES)
        except ValueError:
            pass
    return THEMES[idx]


def generate(theme):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    instructions = theme["prompt"] + """

After writing the post, return your answer as ONLY a JSON object (no markdown,
no code fences) with exactly these keys:
  "post":      the full post text exactly per the guidelines above, including hashtags
  "headline":  a punchy 4-8 word hook for a graphic card - no hashtags, no quotation
               marks, sentence case (e.g. "Is your LA business ransomware-ready?")
  "cta_label": a short 2-4 word call-to-action button label (e.g. "Book a free assessment")
"""
    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=900,
        messages=[{"role": "user", "content": instructions}],
    )
    raw = msg.content[0].text.strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON found in model output:\n{raw}")
    return json.loads(raw[start:end + 1])


def main():
    theme = pick_theme()
    os.makedirs(SOCIAL_DIR, exist_ok=True)

    print(f"[render] theme: {theme['label']} (key: {theme['key']})")
    data = generate(theme)

    post = data["post"].strip()
    headline = (data.get("headline") or "").strip() or theme["label"]
    cta_label = (data.get("cta_label") or "").strip() or \
        DEFAULT_CTA_LABEL.get(theme["cta_type"], "Learn more")

    today = datetime.date.today().isoformat()
    image_file = f"{today}-{theme['key']}.png"
    image_path = os.path.join(SOCIAL_DIR, image_file)
    social_graphic.make_card(headline, theme["label"], cta_label, image_path)

    manifest = {
        "post": post,
        "headline": headline,
        "cta_label": cta_label,
        "cta_type": theme["cta_type"],
        "cta_url": theme.get("cta_url"),
        "image_file": image_file,
        "theme": theme["key"],
    }
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[render] headline: {headline!r}")
    print(f"[render] cta: {cta_label!r}  image: {image_file}")
    print(f"[render] post ({len(post)} chars):\n{post}")


if __name__ == "__main__":
    main()
