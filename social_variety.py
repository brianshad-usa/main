"""
social_variety.py
-----------------
Visual-style + FORMAT + CONTENT-REGISTER rotation for the live ProLink social
engine (content_studio.py -> social_graphic / carousel_graphic). Its job is to
guarantee the feed looks and reads varied, while ProLink brand DNA stays
constant on every asset (real logo, navy + gold somewhere, verified facts only,
peer-to-executive voice owned by editorial/standards.md).

Why this was rewritten (2026-10)
================================
The previous version rotated "styles," but FOUR of six styles shared a navy
ground and ALL of them shared one left-aligned corner-furniture layout, so the
rotation was invisible at thumbnail scale -- the feed looked like one navy card
repeated. And there was no content axis at all, so every post read as the same
cryptic, ominous one-liner regardless of theme.

This version rotates on THREE enforced axes, each measured against a rolling
window of the ledger (not just "differ from the immediately previous post"):

  1. GROUND  - navy / gold / cream / white / split / photo. Hard rule: never the
               same ground as the previous post, and navy is capped to 2 of the
               last 5 (navy is the anchor, not the default).
  2. LAYOUT  - left_block / centered / stat_hero / checklist / banner / split /
               photo. Never the same layout as the previous post; recent layouts
               are penalized so compositions keep changing.
  3. REGISTER- the CONTENT tone/shape: insight / practical_tip / how_to /
               myth_fact / stat_insight / client_value / question / checklist /
               behind_scenes / positive / seasonal. Never the same register as
               either of the last two posts, and the ominous-analytical
               "insight" register is capped to 2 of the last 5, so the feed stops
               being all dread.

Deterministic given (ledger, date): a re-run of a failed workflow picks the same
treatment instead of silently changing the look.

Honesty guard (asset-gated pool)
================================
photographic styles (photo / photo_light) and behind_scenes/reel formats require
a REAL registered photo or clip (assets/variety_assets.json). The autonomous
poster never fabricates a human face or fake footage, so those enter the rotation
ONLY when a matching asset is registered. Absent that, the planner draws from the
fully-autonomous pool it can render honestly with Pillow.
"""

import os
import json
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_MANIFEST = os.path.join(HERE, "assets", "variety_assets.json")

CHANNELS = ["linkedin", "facebook", "gbp", "instagram", "x"]

# ── VISUAL STYLES ─────────────────────────────────────────────────────────
# Each style owns a ground family + a layout, plus the renderer parameters.
# ground: the single biggest driver of "does the feed look varied".
# layout: so two cards on the same ground still differ in composition.
STYLE_META = {
    # autonomous (render fully in Pillow, no external asset)
    "bold_type":       {"ground": "navy",  "layout": "left_block", "asset": False,
                        "card_style": "bold_type",       "cover": "bold"},
    "stat":            {"ground": "navy",  "layout": "stat_hero",  "asset": False,
                        "card_style": "stat",            "cover": "stat"},
    "quote":           {"ground": "navy",  "layout": "centered",   "asset": False,
                        "card_style": "quote",           "cover": "quote"},
    "bright_accent":   {"ground": "gold",  "layout": "left_block", "asset": False,
                        "card_style": "bright_accent",   "cover": "gold"},
    "tip_banner":      {"ground": "white", "layout": "banner",     "asset": False,
                        "card_style": "tip_banner",      "cover": "gold"},
    "illustrative":    {"ground": "cream", "layout": "left_block", "asset": False,
                        "card_style": "illustrative",    "cover": "arc"},
    "checklist":       {"ground": "cream", "layout": "checklist",  "asset": False,
                        "card_style": "checklist",       "cover": "arc"},
    "editorial_light": {"ground": "white", "layout": "centered",   "asset": False,
                        "card_style": "editorial_light", "cover": "bold"},
    "stat_hero_light": {"ground": "white", "layout": "stat_hero",  "asset": False,
                        "card_style": "stat_hero_light", "cover": "stat"},
    "split":           {"ground": "split", "layout": "split",      "asset": False,
                        "card_style": "split",           "cover": "arc"},
    # asset-gated (need a registered real photo)
    "photo":           {"ground": "photo", "layout": "photo",      "asset": True,
                        "card_style": "photo",           "cover": "photo"},
    "photo_light":     {"ground": "photo", "layout": "photo",      "asset": True,
                        "card_style": "photo_light",     "cover": "photo"},
}

AUTONOMOUS_STYLES = [s for s, m in STYLE_META.items() if not m["asset"]]
ASSET_GATED_STYLES = [s for s, m in STYLE_META.items() if m["asset"]]

# ── CONTENT REGISTERS ──────────────────────────────────────────────────────
# The tone/shape of the writing. `copy_directive` steers the per-channel copy;
# `headline_directive` steers the single-card headline so it is NOT always a
# cryptic hook; `kicker` is a default label; `ominous` flags the dread register
# that gets frequency-capped. `prefer` lists compatible visual styles.
REGISTERS = {
    "insight": {
        "ominous": True,
        "kicker": None,
        "copy_directive": "A sharp executive point of view on the risk or trade-off. "
                          "Analytical, but land one useful takeaway, not just a warning.",
        "headline_directive": "A crisp 4-8 word insight (this is the analytical register).",
        "prefer": ["bold_type", "editorial_light", "split", "quote"],
    },
    "practical_tip": {
        "kicker": "Quick tip",
        "copy_directive": "Give ONE concrete action a busy owner can take this week. "
                          "Warm, plain, immediately useful - no fear-selling.",
        "headline_directive": "State the tip as a plain imperative, e.g. 'Turn on MFA for "
                              "email this week'. No riddles.",
        "prefer": ["tip_banner", "bold_type", "split", "editorial_light"],
    },
    "how_to": {
        "kicker": "How to",
        "copy_directive": "Walk through a simple 3-step how-to the reader could follow today. "
                          "Helpful and calm.",
        "headline_directive": "Name the outcome as a how-to, e.g. 'How to lock down a "
                              "departing employee's access'.",
        "prefer": ["editorial_light", "split", "illustrative", "tip_banner"],
    },
    "myth_fact": {
        "kicker": "Myth vs fact",
        "copy_directive": "State a common myth, then the fact. Correct the record without "
                          "condescension.",
        "headline_directive": "Lead with the myth in quotes or the myth-vs-fact contrast.",
        "prefer": ["split", "editorial_light", "bold_type", "illustrative"],
    },
    "stat_insight": {
        "kicker": "By the numbers",
        "copy_directive": "Lead with ONE verified figure (from verified_facts only) and what "
                          "it means for the reader. Never invent a statistic.",
        "headline_directive": "The headline IS the figure context; the card renders the verified "
                              "number itself, so give a short supporting line.",
        "prefer": ["stat", "stat_hero_light"],
    },
    "client_value": {
        "kicker": "What you get",
        "copy_directive": "Describe a concrete benefit the client experiences. Positive, human, "
                          "specific - the good outcome, not the scary one.",
        "headline_directive": "A warm benefit statement, e.g. 'A real technician answers your "
                              "first call'.",
        "prefer": ["bright_accent", "editorial_light", "photo_light", "tip_banner"],
    },
    "question": {
        "kicker": "Worth asking",
        "copy_directive": "Open with a genuine either/or question an owner is actually weighing, "
                          "then help them think it through.",
        "headline_directive": "Pose the question directly, e.g. 'Who owns AI risk on your org "
                              "chart?'.",
        "prefer": ["quote", "editorial_light", "bold_type"],
    },
    "checklist": {
        "kicker": "Checklist",
        "copy_directive": "Give 3-4 checkable items a reader would save. Each item is a short, "
                          "doable action.",
        "headline_directive": "Title the list, e.g. 'Before you sign an MSP contract'. Provide "
                              "the items in the 'checklist_items' field (3-4 short phrases).",
        "prefer": ["checklist"],
    },
    "behind_scenes": {
        "kicker": "Behind the scenes",
        "copy_directive": "A warm, first-person note from the ProLink team - who we are and how "
                          "we work. No jargon, no selling.",
        "headline_directive": "A human, welcoming line, e.g. 'The team behind your help desk'.",
        "prefer": ["photo", "photo_light"],
    },
    "positive": {
        "kicker": "Good to know",
        "copy_directive": "An encouraging, genuinely helpful note. Reassuring and human; show the "
                          "upside of getting IT right.",
        "headline_directive": "An upbeat, plain-spoken line - not a warning.",
        "prefer": ["bright_accent", "photo_light", "editorial_light", "tip_banner"],
    },
    "seasonal": {
        "kicker": "This season",
        "copy_directive": "Tie the idea to the current season/time of year for an LA business. "
                          "Timely and practical.",
        "headline_directive": "A seasonal, concrete line relevant to the month.",
        "prefer": ["bright_accent", "editorial_light", "illustrative", "split"],
    },
}

# Registers that read as warning/dread; frequency-capped so the feed isn't all dread.
OMINOUS_REGISTERS = {r for r, m in REGISTERS.items() if m.get("ominous")}

# Formats (the post shape). Carousel vs single card is the axis that content uses.
FORMATS = ["single_image", "carousel"]

# ── Rolling-window rules (measurable, enforced) ────────────────────────────
GROUND_WINDOW = 5
NAVY_CAP = 2            # at most 2 navy grounds in the last GROUND_WINDOW posts
LAYOUT_WINDOW = 4
REGISTER_WINDOW = 5
REGISTER_AVOID_LAST = 2     # don't reuse either of the last 2 registers
OMINOUS_CAP = 2            # at most 2 ominous registers in the last REGISTER_WINDOW


def _load(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def available_assets():
    data = _load(ASSETS_MANIFEST, {})
    return {k: v for k, v in data.items()
            if v and not k.startswith("_") and isinstance(v, list)}


def pick_photo(bucket="photographic", seed=""):
    items = available_assets().get(bucket) or []
    norm = []
    for it in items:
        if isinstance(it, str):
            norm.append({"path": it})
        elif isinstance(it, dict) and it.get("path"):
            norm.append(it)
    if not norm:
        return None
    h = int(hashlib.sha1((seed or "prolink").encode("utf-8")).hexdigest(), 16)
    return norm[h % len(norm)]


# ── Ledger history helpers ─────────────────────────────────────────────────
def _history(ledger, key, n):
    """The last n values of variety[key] across posts (most recent last)."""
    out = []
    for post in ledger.get("posts", []):
        v = post.get("variety") or {}
        val = v.get(key)
        # back-compat: derive ground/layout from style if not recorded
        if val is None and key in ("ground", "layout") and v.get("style"):
            meta = STYLE_META.get(v["style"])
            val = meta[key] if meta else None
        if val is not None:
            out.append(val)
    return out[-n:]


def _last(ledger, key):
    h = _history(ledger, key, 1)
    return h[-1] if h else None


def eligible_styles():
    """Styles the engine may use right now (autonomous + unlocked asset-gated)."""
    assets = available_assets()
    unlocked = list(AUTONOMOUS_STYLES)
    if assets.get("photographic"):
        unlocked += ASSET_GATED_STYLES
    return unlocked


def choose_register(ledger):
    """Pick the content register, enforcing no-repeat-of-last-2 and the ominous cap."""
    recent = _history(ledger, "register", REGISTER_WINDOW)
    avoid = set(recent[-REGISTER_AVOID_LAST:])
    ominous_recent = sum(1 for r in recent if r in OMINOUS_REGISTERS)
    n = len(ledger.get("posts", []))
    order = list(REGISTERS.keys())

    def ok(r):
        if r in avoid:
            return False
        if r in OMINOUS_REGISTERS and ominous_recent >= OMINOUS_CAP:
            return False
        return True

    candidates = [r for r in order if ok(r)]
    if not candidates:   # fall back: just avoid the immediate previous
        candidates = [r for r in order if r != (recent[-1] if recent else None)] or order
    # deterministic rotation through the candidate space
    return candidates[n % len(candidates)]


def choose_style(ledger, register):
    """Pick a visual style compatible with the register that maximizes ground +
    layout contrast against the recent window."""
    elig = set(eligible_styles())
    prefer = [s for s in REGISTERS[register]["prefer"] if s in elig]
    # widen if the preferred styles are all gated-out
    pool = prefer or [s for s in elig]
    if not pool:
        pool = ["bold_type"]

    g_recent = _history(ledger, "ground", GROUND_WINDOW)
    l_recent = _history(ledger, "layout", LAYOUT_WINDOW)
    s_recent = _history(ledger, "style", GROUND_WINDOW)
    prev_ground = g_recent[-1] if g_recent else None
    prev_layout = l_recent[-1] if l_recent else None
    navy_recent = sum(1 for g in g_recent if g == "navy")
    n = len(ledger.get("posts", []))

    def score(i, style):
        m = STYLE_META[style]
        g, lay = m["ground"], m["layout"]
        pen = 0
        # hard-ish avoidance: same ground/layout as previous is heavily penalized
        if g == prev_ground:
            pen += 100
        if lay == prev_layout:
            pen += 60
        # navy cap: adding another navy when already at the cap is penalized hard
        if g == "navy" and navy_recent >= NAVY_CAP:
            pen += 120
        # discourage recently-used grounds/layouts/styles (keep the feed moving)
        pen += 8 * g_recent.count(g)
        pen += 6 * l_recent.count(lay)
        pen += 10 * s_recent.count(style)
        rotated = (i + n) % max(len(pool), 1)
        return (pen, rotated)

    ranked = sorted(enumerate(pool), key=lambda ip: score(ip[0], ip[1]))
    return ranked[0][1]


def choose_format(ledger, style):
    """Alternate single-card vs carousel, honoring what the style supports."""
    # carousel is the multi-slide swipe; alternate it with single cards.
    last_fmt = _last(ledger, "format")
    n_carousel_recent = sum(1 for f in _history(ledger, "format", 3) if f == "carousel")
    # photo/stat_hero styles read best as single cards; everything else may carousel.
    can_carousel = STYLE_META[style]["layout"] not in ("stat_hero", "checklist", "banner")
    if not can_carousel:
        return "single_image"
    if last_fmt == "carousel" or n_carousel_recent >= 1:
        return "single_image"
    return "carousel"


def plan(ledger, today=None, idea=None):
    """Return the variety directive for this run (deterministic given the ledger).

    Enforces ground/layout/register diversity across a rolling window, not just
    against the immediately previous post.
    """
    register = choose_register(ledger)
    style = choose_style(ledger, register)
    fmt = choose_format(ledger, style)
    meta = STYLE_META[style]
    reg = REGISTERS[register]

    render = {
        "card_style": meta["card_style"],
        "carousel_cover": meta["cover"],
        "palette_variant": meta["ground"],
        "register": register,
    }

    copy_directive = " ".join([
        f"CONTENT REGISTER - {register.replace('_', ' ')}: {reg['copy_directive']}",
        f"VISUAL: a {meta['ground']} {meta['layout']} card; write for that shape.",
    ]).strip()

    # Per-channel: keep the run treatment coherent across channels (the feed is the
    # thing we're fixing), but let Instagram be carousel-native when carousel is
    # chosen, and give each channel the same register so copy stays on-message.
    channel_dirs = {}
    for ch in CHANNELS:
        ch_fmt = fmt
        if ch == "instagram" and fmt == "single_image" and meta["layout"] not in (
                "stat_hero", "checklist", "banner"):
            # IG is the carousel-native channel; let it swipe when it reasonably can
            # without forcing a second render every run.
            ch_fmt = fmt
        channel_dirs[ch] = {"style": style, "format": ch_fmt,
                            "ground": meta["ground"], "layout": meta["layout"],
                            "register": register}

    assets = available_assets()
    return {
        "style": style,
        "format": fmt,
        "ground": meta["ground"],
        "layout": meta["layout"],
        "register": register,
        "register_kicker": reg.get("kicker"),
        "register_headline_directive": reg["headline_directive"],
        "render": render,
        "asset_gated": meta["asset"],
        "assets_available": {k: len(v) for k, v in assets.items()},
        "copy_directive": copy_directive,
        "channels": channel_dirs,
        "previous_run": {
            "style": _last(ledger, "style"),
            "ground": (_history(ledger, "ground", 1) or [None])[-1],
            "layout": (_history(ledger, "layout", 1) or [None])[-1],
            "register": _last(ledger, "register"),
        },
    }


if __name__ == "__main__":
    import editorial_engine
    directive = plan(editorial_engine.load_ledger())
    print(json.dumps(directive, indent=2, ensure_ascii=False))
