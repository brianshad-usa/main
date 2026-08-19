"""
social_variety.py
-----------------
Visual-style + format rotation for the live ProLink social engine
(content_studio.py -> social_render/graphic). Guarantees that consecutive
automated posts do NOT look or read the same, while ProLink brand DNA stays
constant on every asset:

  * navy anchor ground, gold used sparingly as the single accent
  * the real logo.png and the prolinksystems.com / 1-800-890-6133 contact line
  * the peer-to-executive editorial voice (owned by editorial/standards.md)
  * verified facts only (owned by editorial/verified_facts.json)
  * balanced casting standard for any human imagery (asset-gated, see below)

No war-room cmo/social_variety.py exists in this repo to port, so this is the
canonical implementation. It is deterministic given (ledger, date): a re-run of
a failed workflow picks the same treatment instead of silently changing the look.

Two axes
========
VISUAL STYLE  - how the asset looks:
    bold_type       oversized display headline, high-contrast navy card
    data_viz        a single figure/stat as the hero, chart-card treatment
    illustrative    geometric ProLink motif (arcs/grid), no stock clip-art
    quote_minimal   one line, enormous negative space, quotation ornament
    photographic    duotone photo ground  (ASSET-GATED - see below)

FORMAT        - the shape of the post:
    single_image        one square card
    carousel            multi-slide editorial swipe
    infographic         stat/structure card built for saves
    quote_stat_card     one claim, isolated
    question_poll       an opener written as a question (poll-ready)
    reel_clip           short video            (ASSET-GATED)
    behind_the_scenes   real team/office photo (ASSET-GATED)

Honesty guard (asset-gated pool)
================================
photographic / reel_clip / behind_the_scenes require a REAL photo or video of
real people or the real office. The autonomous daily poster must never fabricate
a human face or fake footage, so these enter the rotation ONLY when a matching
asset is registered in assets/variety_assets.json. Absent that, the planner
draws exclusively from the autonomous pool it can render honestly with Pillow.

Anti-repetition
===============
Per channel, this run's (style, format) pair must differ from that channel's
previous run. The planner also maximises contrast: it avoids repeating the
previous run's style OR format where a fuller-contrast option is available.
"""

import os
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_MANIFEST = os.path.join(HERE, "assets", "variety_assets.json")

# The channels the live engine syndicates to. Each keeps its own no-repeat memory.
CHANNELS = ["linkedin", "facebook", "gbp", "instagram", "x"]

STYLES = ["bold_type", "data_viz", "illustrative", "quote_minimal", "photographic"]
FORMATS = ["single_image", "carousel", "infographic", "quote_stat_card",
           "question_poll", "reel_clip", "behind_the_scenes"]

# Formats/styles the engine can render honestly with no external asset.
AUTONOMOUS_STYLES = ["bold_type", "data_viz", "illustrative", "quote_minimal"]
AUTONOMOUS_FORMATS = ["single_image", "carousel", "infographic",
                      "quote_stat_card", "question_poll"]
ASSET_GATED_STYLES = ["photographic"]
ASSET_GATED_FORMATS = ["reel_clip", "behind_the_scenes"]

# Which (style, format) pairs are coherent. Not every combination makes sense;
# e.g. quote_minimal belongs on a quote card, not a dense infographic.
STYLE_FORMAT_MATRIX = {
    "bold_type":     ["single_image", "carousel", "question_poll"],
    "data_viz":      ["single_image", "infographic", "quote_stat_card", "carousel"],
    "illustrative":  ["single_image", "carousel", "infographic"],
    "quote_minimal": ["single_image", "quote_stat_card", "question_poll"],
    "photographic":  ["single_image", "carousel", "behind_the_scenes", "reel_clip"],
}

# Render parameters per style. Brand DNA (navy + gold + logo + contact) is fixed
# in the renderers; these only choose the *treatment*, never the brand marks.
STYLE_RENDER = {
    "bold_type":     {"card_style": "bold_type",   "carousel_cover": "bold",
                      "palette_variant": "navy_gradient"},
    "data_viz":      {"card_style": "stat",        "carousel_cover": "stat",
                      "palette_variant": "navy_panel"},
    "illustrative":  {"card_style": "illustrative", "carousel_cover": "arc",
                      "palette_variant": "navy_arcs"},
    "quote_minimal": {"card_style": "quote",       "carousel_cover": "quote",
                      "palette_variant": "navy_flat"},
    "photographic":  {"card_style": "photo",       "carousel_cover": "photo",
                      "palette_variant": "duotone"},
}

# A short instruction appended to the draft prompt so the COPY matches the FORMAT.
FORMAT_COPY_DIRECTIVE = {
    "single_image":     "Lead with one sharp claim; the card carries a 4-8 word hook.",
    "carousel":         "Build a 5-8 slide argument that earns each swipe.",
    "infographic":      "Structure the idea as 3-4 labelled parts a reader would save.",
    "quote_stat_card":  "Isolate a single verified figure or one-line claim as the hero; "
                        "if no verified number applies, use a one-sentence assertion, never an invented stat.",
    "question_poll":    "Open with a genuine either/or question an executive is actually weighing.",
    "reel_clip":        "Write a 15-25s spoken script with an on-screen caption track.",
    "behind_the_scenes": "Write a warm, first-person note from the ProLink team; no jargon.",
}

STYLE_COPY_DIRECTIVE = {
    "bold_type":     "The visual is a bold typographic card; the headline must stand alone.",
    "data_viz":      "The visual foregrounds one figure; make that figure unmissable in the copy.",
    "illustrative":  "The visual is an abstract ProLink motif; the words do the explaining.",
    "quote_minimal": "The visual is a spare quote card; give it one quotable line.",
    "photographic":  "The visual is a real photograph; the caption complements, not repeats, it.",
}


def _load(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def available_assets():
    """Registered real photos/clips that unlock the asset-gated pool.

    Shape: {"photographic": [..paths..], "behind_the_scenes": [...], "reel_clip": [...]}
    Only non-empty buckets unlock their style/format.
    """
    data = _load(ASSETS_MANIFEST, {})
    return {k: v for k, v in data.items() if v}


def _last_pair_for(ledger, channel):
    """The (style, format) the given channel received on the most recent run."""
    for post in reversed(ledger.get("posts", [])):
        v = post.get("variety")
        if not v:
            continue
        ch = v.get("channels", {}).get(channel)
        if ch:
            return (ch.get("style"), ch.get("format"))
        # Older single-directive entries: fall back to the run-level pair.
        if v.get("style"):
            return (v.get("style"), v.get("format"))
    return (None, None)


def _last_run_pair(ledger):
    for post in reversed(ledger.get("posts", [])):
        v = post.get("variety")
        if v and v.get("style"):
            return (v.get("style"), v.get("format"))
    return (None, None)


def _eligible_pairs(assets):
    """All coherent (style, format) pairs the engine may use right now."""
    pairs = []
    unlocked_styles = set(AUTONOMOUS_STYLES) | {
        s for s in ASSET_GATED_STYLES if assets.get(s)}
    unlocked_formats = set(AUTONOMOUS_FORMATS) | {
        f for f in ASSET_GATED_FORMATS if assets.get(f)}
    for style in STYLES:
        if style not in unlocked_styles:
            continue
        for fmt in STYLE_FORMAT_MATRIX.get(style, []):
            if fmt not in unlocked_formats:
                continue
            pairs.append((style, fmt))
    return pairs


def plan(ledger, today=None, idea=None):
    """Return the variety directive for this run.

    Deterministic given the ledger. Picks a run-level (style, format) that
    differs from the last run, then assigns each channel a pair that differs
    from that channel's own previous run.
    """
    assets = available_assets()
    pairs = _eligible_pairs(assets)
    if not pairs:  # should never happen: autonomous pool is always non-empty
        pairs = [("bold_type", "single_image")]

    prev_run = _last_run_pair(ledger)
    n_posts = len(ledger.get("posts", []))

    # Rank eligible pairs by contrast with the previous run; rotate the tie-break
    # by post count so the engine cycles through the space over successive runs.
    def rank_key(i_pair):
        i, pair = i_pair
        style, fmt = pair
        ps, pf = prev_run
        contrast = (style != ps) + (fmt != pf)
        rotated = (i + n_posts) % len(pairs)
        return (-contrast, rotated)

    ranked = sorted(enumerate(pairs), key=rank_key)
    run_style, run_format = ranked[0][1]
    # Never repeat the exact previous run pair if any alternative exists.
    if (run_style, run_format) == prev_run and len(pairs) > 1:
        run_style, run_format = ranked[1][1]

    # Per-channel assignment: each channel avoids its own last pair. Instagram
    # is the carousel-native channel; keep carousel with it when chosen, else it
    # shares the run treatment.
    channel_dirs = {}
    for ci, channel in enumerate(CHANNELS):
        last = _last_pair_for(ledger, channel)
        # candidate order: run pair first, then the ranked alternatives
        candidates = [(run_style, run_format)] + [p for _, p in ranked]
        chosen = None
        for cand in candidates:
            if cand != last:
                chosen = cand
                break
        chosen = chosen or (run_style, run_format)
        channel_dirs[channel] = {"style": chosen[0], "format": chosen[1]}

    render = dict(STYLE_RENDER[run_style])
    copy_directive = " ".join([
        STYLE_COPY_DIRECTIVE[run_style],
        FORMAT_COPY_DIRECTIVE.get(run_format, ""),
    ]).strip()

    return {
        "style": run_style,
        "format": run_format,
        "render": render,
        "asset_gated": run_style in ASSET_GATED_STYLES or run_format in ASSET_GATED_FORMATS,
        "assets_available": {k: len(v) for k, v in assets.items()},
        "copy_directive": copy_directive,
        "channels": channel_dirs,
        "previous_run": {"style": prev_run[0], "format": prev_run[1]},
    }


if __name__ == "__main__":
    import editorial_engine
    directive = plan(editorial_engine.load_ledger())
    print(json.dumps(directive, indent=2, ensure_ascii=False))
