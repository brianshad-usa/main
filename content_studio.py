"""
content_studio.py
-----------------
Step 1 of the social pipeline, upgraded (2026 Editorial Excellence directive).
Drop-in replacement for social_render.py in .github/workflows/social-3x-week.yml
- it writes the same pending.json manifest social_publish.py consumes, extended
with per-channel content and carousel slides.

Pipeline per run:
  1. editorial_engine selects the topic from social_backlog.json vs the ledger
  2. DRAFT     - Claude writes per-channel content under editorial/standards.md
  3. REVIEW    - a second pass critiques the draft from the 11 review-board
                 perspectives, revises it, and scores the 15-dimension
                 Content Excellence rubric honestly
  4. GATE      - overall < TARGET (95) triggers one more revision round;
                 still < FLOOR (90) fails the run RED. Quality over schedule:
                 no post is published rather than a weak one.
  5. RENDER    - Instagram carousel slides via carousel_graphic.py, plus the
                 1080x1080 fallback card via social_graphic.py for channels
                 that take a single image
  6. MANIFEST  - pending.json (extended), ledger updated

Env: ANTHROPIC_API_KEY
Usage:
    python content_studio.py                # full run
    python content_studio.py --offline     # skip the API; canned demo content
                                            (structure/render testing only)
    python content_studio.py --idea S031   # force a specific backlog idea
"""

import os
import re
import sys
import json
import datetime

import editorial_engine
import carousel_graphic
import social_graphic

HERE = os.path.dirname(os.path.abspath(__file__))
SOCIAL_DIR = os.path.join(HERE, "social")
MANIFEST = os.path.join(HERE, "pending.json")
STANDARDS = os.path.join(HERE, "editorial", "standards.md")
FACTS = os.path.join(HERE, "editorial", "verified_facts.json")

MODEL = os.environ.get("EDITORIAL_MODEL", "claude-opus-5")
TARGET = 95
FLOOR = 90

RUBRIC = ["topic_relevance", "timeliness", "originality", "hook_strength",
          "educational_value", "technical_accuracy", "executive_value",
          "writing_quality", "visual_sophistication", "platform_fit",
          "shareability", "saveability", "brand_authority", "trust",
          "strategic_value"]

BOARD = ["Chief Marketing Officer", "Creative Director", "Art Director",
         "Senior Technology Editor", "CIO", "Cybersecurity Expert",
         "AI Strategist", "Executive Audience Representative",
         "Social Growth Strategist", "Brand Director", "Copy Editor"]

BANNED_OPENINGS = ["did you know", "in today's digital world",
                   "cybersecurity is more important than ever",
                   "technology is constantly evolving", "businesses today face"]


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _log(msg):
    print(f"[studio] {msg}", flush=True)


def system_prompt():
    return (
        "You are the editorial engine of Pro Link Systems' marketing organization: "
        "a premium technology publication that happens to be produced by a Los Angeles "
        "managed IT and cybersecurity firm. The standards document below is your "
        "operating contract. Follow it exactly.\n\n"
        "=== EDITORIAL STANDARDS ===\n" + _read(STANDARDS) +
        "\n\n=== VERIFIED FACTS (the ONLY ProLink claims you may make) ===\n" +
        _read(FACTS) +
        "\n\nYou always respond with ONLY a JSON object - no markdown fences, no prose "
        "around it. Strings must be plain text (no markdown) unless the field "
        "description says otherwise."
    )


def draft_prompt(idea):
    return f"""Create today's cross-channel content package from this approved backlog concept:

CONCEPT {idea['id']} - {idea['title']}
Theme: {idea['theme']}  |  Format: {idea['format']}  |  Timeliness: {idea.get('timeliness')}
Editorial angle: {idea['angle']}

One core idea; the best native expression of it for each channel - never the same
text twice. The concept's angle is the assignment: sharpen it, don't dilute it.

Return JSON with exactly these keys:
{{
  "core_idea": "one sentence stating the single idea every channel expresses",
  "linkedin": "executive analysis post, 900-1600 chars, line breaks between short
               paragraphs, no hashtags, hook in the first line, perspective not summary",
  "facebook": "approachable business version, 400-900 chars, scenario-led,
               not a copy of linkedin",
  "gbp": "practical advisory for an LA business owner, 300-700 chars, plain text,
          no hashtags, ends with a natural next step (not a hard sell)",
  "x": ["1-6 posts, <=270 chars each; a single post unless progression genuinely adds value"],
  "instagram": {{
    "caption": "carousel caption, 300-800 chars, up to 3 hashtags at the very end",
    "slides": [
      {{"role": "hook|content|takeaway|cta", "kicker": "2-4 word label",
        "headline": "the slide's one idea, <=90 chars",
        "body": "supporting text <=280 chars; empty string on the hook slide",
        "footer": "optional attribution/source line or empty string"}}
    ]
  }},
  "card_headline": "4-8 word hook for the single-image fallback card, sentence case",
  "cta_label": "2-4 word button label",
  "cta_type": "LEARN_MORE|BOOK_APPOINTMENT|CALL",
  "cta_url": "the most relevant prolinksystems.com page",
  "claims_audit": ["every factual claim in any channel, each tagged FACT(id)/ANALYSIS/OPINION,
                   e.g. 'FACT(F003): average ticket first-response time 15 minutes'"]
}}

Slide count follows the story (typically 5-8). The hook slide earns the swipe with
minimal text. Number-free unless a number appears in the verified facts or is common
knowledge stated qualitatively."""


def review_prompt(idea, package):
    return f"""Review this draft package before publication. Concept: {idea['id']} - {idea['title']}.

DRAFT:
{json.dumps(package, ensure_ascii=False, indent=1)}

Act as the full internal review board - {', '.join(BOARD)}. Each perspective must
identify at least one concrete weakness (or state a specific reason it has none).
Then REVISE the package to address every finding that matters.

Then score the REVISED package honestly on the 15-dimension rubric, 0-100 each:
{', '.join(RUBRIC)}.
Scoring integrity: do not inflate. If a dimension is genuinely below 95, say so
and explain what would raise it. The overall score is your holistic judgment, not
an average - a single serious weakness caps it.

Also verify against the ultimate test: could any MSP have published this exact
post? If yes, the revision is not finished.

Return JSON:
{{
  "board_findings": [{{"role": "...", "finding": "..."}}],
  "revised": {{ ...same schema as the draft package... }},
  "scores": {{"topic_relevance": 0, ...all 15 keys...}},
  "overall": 0,
  "verdict": "publish|revise|reject",
  "weakest_dimension": "name + one sentence on what would raise it"
}}"""


def call_model(client, system, user, max_tokens=9000):
    msg = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    raw = msg.content[0].text.strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON in model output:\n{raw[:800]}")
    return json.loads(raw[start:end + 1])


def lint(package):
    """Deterministic guardrails independent of the model's self-review."""
    problems = []
    texts = {
        "linkedin": package.get("linkedin", ""),
        "facebook": package.get("facebook", ""),
        "gbp": package.get("gbp", ""),
    }
    for name, t in texts.items():
        low = t.lower().strip()
        for b in BANNED_OPENINGS:
            if low.startswith(b):
                problems.append(f"{name}: banned opening '{b}'")
    if "#" in texts["linkedin"]:
        problems.append("linkedin: hashtags are not permitted")
    ig = package.get("instagram", {})
    caption = ig.get("caption", "")
    if caption.count("#") > 3:
        problems.append("instagram: more than 3 hashtags")
    slides = ig.get("slides", [])
    if not (3 <= len(slides) <= 10):
        problems.append(f"instagram: {len(slides)} slides outside 3-10")
    for t in list(texts.values()) + [caption]:
        for ch in t:
            if ord(ch) >= 0x1F300:   # emoji / pictographs
                problems.append("emoji found in copy")
                break
    # duplicate-text check: channels must not share sentences
    def sentences(t):
        return {s.strip().lower() for s in re.split(r"[.!?]\s+", t) if len(s.strip()) > 60}
    seen = {}
    for name, t in texts.items():
        for s in sentences(t):
            if s in seen:
                problems.append(f"duplicate sentence across {seen[s]} and {name}")
            seen[s] = name
    return problems


def offline_package(idea):
    """Canned structure for --offline render/manifest testing. Never published:
    the manifest is stamped offline_test so social_publish refuses it."""
    return {
        "core_idea": f"[OFFLINE TEST] {idea['title']}",
        "linkedin": "[OFFLINE TEST] Structure check only.",
        "facebook": "[OFFLINE TEST] Structure check only.",
        "gbp": "[OFFLINE TEST] Structure check only.",
        "x": ["[OFFLINE TEST]"],
        "instagram": {
            "caption": "[OFFLINE TEST]",
            "slides": [
                {"role": "hook", "kicker": "Offline", "headline": idea["title"], "body": "", "footer": ""},
                {"role": "content", "kicker": "Test", "headline": "Render check",
                 "body": "This slide exists to validate the renderer and manifest wiring.", "footer": ""},
                {"role": "cta", "kicker": "Pro Link Systems", "headline": "Not for publication.",
                 "body": "", "footer": "offline test"},
            ],
        },
        "card_headline": "Offline structure test",
        "cta_label": "Learn more",
        "cta_type": "LEARN_MORE",
        "cta_url": "https://prolinksystems.com",
        "claims_audit": [],
    }


def main():
    offline = "--offline" in sys.argv
    forced = None
    if "--idea" in sys.argv:
        forced = sys.argv[sys.argv.index("--idea") + 1]

    if forced:
        backlog = editorial_engine.load_backlog()
        idea = next((i for i in backlog["ideas"] if i["id"] == forced), None)
        if not idea:
            raise SystemExit(f"Unknown idea id {forced}")
    else:
        idea, _ = editorial_engine.select()
    _log(f"selected {idea['id']} [{idea['theme']}/{idea['format']}] - {idea['title']}")

    review = None
    if offline:
        package = offline_package(idea)
        scores = {k: 0 for k in RUBRIC}
        overall = 0
    else:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        system = system_prompt()

        package = call_model(client, system, draft_prompt(idea))
        _log("draft complete; convening review board")

        review = call_model(client, system, review_prompt(idea, package))
        package = review["revised"]
        overall = int(review["overall"])
        scores = review["scores"]
        _log(f"review round 1: overall {overall} - weakest: {review.get('weakest_dimension')}")

        if overall < TARGET:
            _log(f"below target {TARGET}; running a second revision round")
            review = call_model(client, system, review_prompt(idea, package))
            package = review["revised"]
            overall = int(review["overall"])
            scores = review["scores"]
            _log(f"review round 2: overall {overall}")

        problems = lint(package)
        if problems:
            _log("lint failures: " + "; ".join(problems))
        if overall < FLOOR or problems:
            print(f"::error::Content quality gate failed (overall {overall}, "
                  f"lint: {problems or 'clean'}). Publishing nothing beats publishing filler.")
            sys.exit(1)

    # ── Render ───────────────────────────────────────────────────
    today = datetime.date.today().isoformat()
    stem = f"{today}-{idea['id'].lower()}"
    os.makedirs(SOCIAL_DIR, exist_ok=True)

    slides = package["instagram"]["slides"]
    rendered = carousel_graphic.render_carousel(slides, SOCIAL_DIR, stem)
    slide_pngs = [os.path.basename(p) for p, _ in rendered]
    slide_jpgs = [os.path.basename(j) for _, j in rendered]
    _log(f"rendered {len(rendered)} carousel slides")

    # Single-image fallback card (GBP photo, LinkedIn/Facebook image)
    card_png = f"{stem}-card.png"
    social_graphic.make_card(package["card_headline"],
                             idea["theme"].replace("_", " ").title(),
                             package["cta_label"],
                             os.path.join(SOCIAL_DIR, card_png))
    from PIL import Image
    card_jpg = card_png[:-4] + ".jpg"
    Image.open(os.path.join(SOCIAL_DIR, card_png)).convert("RGB").save(
        os.path.join(SOCIAL_DIR, card_jpg), "JPEG", quality=92)

    # ── Manifest (superset of the legacy pending.json contract) ──
    manifest = {
        "post": package["facebook"],            # legacy fallback field
        "headline": package["card_headline"],
        "cta_label": package["cta_label"],
        "cta_type": package["cta_type"],
        "cta_url": package["cta_url"],
        "image_file": card_png,
        "image_file_jpg": card_jpg,
        "theme": idea["theme"],
        "idea_id": idea["id"],
        "core_idea": package["core_idea"],
        "channels": {
            "linkedin": package["linkedin"],
            "facebook": package["facebook"],
            "gbp": package["gbp"],
            "x": package["x"],
            "instagram_caption": package["instagram"]["caption"],
        },
        "carousel": {"png": slide_pngs, "jpg": slide_jpgs},
        "excellence": {"overall": overall, "scores": scores},
        "claims_audit": package.get("claims_audit", []),
        "board_findings": (review or {}).get("board_findings", []),
        "offline_test": offline,
    }
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    if not offline:
        editorial_engine.record_publication(
            idea, excellence=overall,
            channels=["LinkedIn", "Facebook", "Instagram", "GBP"])

    _log(f"core idea: {package['core_idea']}")
    _log(f"excellence: {overall}/100")
    _log(f"manifest written: {MANIFEST}")


if __name__ == "__main__":
    main()
