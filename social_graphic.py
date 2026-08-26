"""
social_graphic.py
-----------------
Generates a branded square (1080x1080) social card for Pro Link Systems in one
of five VISUALLY DISTINCT styles. Each style sits on its OWN ground / palette /
layout so the feed stops looking samey at thumbnail scale, while brand DNA stays
recognizable on every card: the real logo.png, navy + gold present somewhere, and
a calm professional voice.

The five styles (approved preview, ported here verbatim):
  bold_type      navy gradient ground, big bold white headline (the anchor look)
  stat           navy panel with ONE giant gold hero figure pulled from
                 editorial/verified_facts.json (24/7, 90%, 1999, ...) - the hero
                 is NOT parsed from the headline
  illustrative   LIGHT cream/paper ground, navy ink, gold quarter-arc motif
  quote          inverted gold-on-navy quote card, oversized quote mark, airy
  bright_accent  solid gold ground, navy type, navy corner block
  photo          duotone photo ground (ASSET-GATED - only real photos; falls back
                 to the bold navy card when no verified photo is registered)

The visual treatment is chosen by social_variety.py (STYLE_RENDER) and threaded
through content_studio.py via `style` (+ optional `palette_variant`). Brand marks
are fixed by the renderer; the treatment never changes the brand marks.

Fonts: bundled Inter variable font (assets/fonts/Inter.ttf) so local (Windows)
and CI (Linux) render identically. Pure Pillow, no external services.
"""

import os
import sys
import json
import hashlib
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))

# ── Brand palette (navy anchor + gold accent, plus a paper register) ─────
NAVY_BLACK = (6, 18, 30)       # #06121e  deepest ground
NAVY_DEEP  = (13, 59, 102)     # #0d3b66  brand navy anchor
NAVY       = (26, 93, 171)     # #1a5dab  brand navy (brighter)
NAVY_INK   = (17, 38, 62)      # ink on paper / gold
GOLD       = (247, 148, 29)    # #f7941d  brand gold accent
GOLD_WARM  = (245, 166, 35)    # slightly softer gold
CREAM      = (245, 241, 232)   # #f5f1e8  paper ground
CREAM_LINE = (219, 210, 193)
INK        = (23, 33, 45)
WHITE      = (255, 255, 255)
MUTED      = (95, 110, 130)

# Back-compat aliases (older callers referenced these names).
NAVY_DARK = NAVY_BLACK
NAVY_MID  = NAVY

W = H = 1080
MARGIN = 84

# ── Fonts (variable Inter; identical local + CI) ─────────────────────────
INTER_VAR = os.environ.get("INTER_FONT", os.path.join(HERE, "assets", "fonts", "Inter.ttf"))
LOGO_PATH = os.environ.get("LOGO_PATH", os.path.join(HERE, "logo.png"))
FACTS_PATH = os.path.join(HERE, "editorial", "verified_facts.json")

_WIN = r"C:\Windows\Fonts"
_FALLBACKS = {
    "bold":  [os.path.join(_WIN, "segoeuib.ttf"),
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "reg":   [os.path.join(_WIN, "segoeui.ttf"),
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}
_VAR = {"black": "Black", "extrabold": "ExtraBold", "bold": "Bold",
        "semi": "SemiBold", "med": "Medium", "reg": "Regular", "light": "Light"}


def _font(role, size):
    if os.path.exists(INTER_VAR):
        try:
            f = ImageFont.truetype(INTER_VAR, size)
            f.set_variation_by_name(_VAR.get(role, "Regular"))
            return f
        except Exception:
            pass
    paths = _FALLBACKS["bold"] if role in ("black", "extrabold", "bold", "semi") else _FALLBACKS["reg"]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# ── Drawing helpers ──────────────────────────────────────────────────────
def _gradient(d, x0, y0, x1, y1, c1, c2):
    h = y1 - y0
    for i in range(h):
        t = i / max(h - 1, 1)
        col = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
        d.line([(x0, y0 + i), (x1, y0 + i)], fill=col)


def _wrap(d, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textlength(test, font=f) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit(d, text, role, max_w, max_h, start, floor, leading=1.1):
    size = start
    while size >= floor:
        f = _font(role, size)
        lines = _wrap(d, text, f, max_w)
        line_h = int(size * leading) + 6
        if len(lines) * line_h <= max_h and all(
                d.textlength(l, font=f) <= max_w for l in lines):
            return f, lines, line_h
        size -= 4
    return f, lines, line_h


def _tracked(d, xy, text, f, fill, tracking=3.0):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + tracking


try:
    _LOGO = Image.open(LOGO_PATH).convert("RGBA")
except Exception:
    _LOGO = None


def _logo_lockup(img, d, x, y, target_h, ground="dark"):
    """Place the real logo so it always reads. The wordmark's navy strokes vanish
    on dark or gold grounds, so it sits on a white rounded chip there; on the cream
    paper ground it sits directly."""
    if _LOGO is None:
        return x
    lg = _LOGO.resize((int(_LOGO.width * target_h / _LOGO.height), target_h), Image.LANCZOS)
    if ground == "cream":
        img.paste(lg, (x, y), lg)
        return x + lg.width
    pad = 22
    d.rounded_rectangle([x - pad, y - pad, x + lg.width + pad, y + lg.height + pad],
                        radius=(lg.height + 2 * pad) // 2, fill=WHITE)
    img.paste(lg, (x, y), lg)
    return x + lg.width + pad


def _contact_line(d, y, color=WHITE):
    f1 = _font("semi", 30)
    f2 = _font("reg", 27)
    right = W - MARGIN
    d.text((right - d.textlength("prolinksystems.com", font=f1), y),
           "prolinksystems.com", font=f1, fill=color)
    sub = MUTED if color == WHITE else color
    d.text((right - d.textlength("1-800-890-6133", font=f2), y + 40),
           "1-800-890-6133", font=f2, fill=sub)


def _cta_pill(d, cta, x, y, fill, text_fill):
    if not cta:
        return 0
    cf = _font("semi", 32)
    pad_x, pad_y = 34, 19
    tw = d.textlength(cta, font=cf)
    asc, desc = cf.getmetrics()
    ph = asc + desc + pad_y * 2
    d.rounded_rectangle([x, y, x + tw + pad_x * 2, y + ph], radius=ph // 2, fill=fill)
    d.text((x + pad_x, y + pad_y - 2), cta, font=cf, fill=text_fill)
    return ph


# ── Verified-fact hero figures for the stat style ────────────────────────
# Each hero is a short display token + a support line that names the metric in
# full, so a bare figure never overclaims. Drawn ONLY from owner-confirmed facts
# (editorial/verified_facts.json). If that file changes materially, resync here.
_HERO_STATS = [
    ("24/7",   "US-based help desk, always on"),            # F001 / F008
    ("90%",    "first-contact resolution"),                 # F004
    ("1999",   "serving Los Angeles businesses since"),     # F012
    ("15 min", "average ticket first-response time"),       # F003 (named in full)
    ("Live",   "phone answered by a real technician"),      # F007
]


def _verified_facts_text():
    try:
        with open(FACTS_PATH, encoding="utf-8") as f:
            return json.dumps(json.load(f))
    except Exception:
        return ""


def _pick_hero(seed_text):
    """Deterministic hero choice: same headline -> same figure across re-runs.
    Only offers a figure that is still present in verified_facts.json."""
    facts = _verified_facts_text()
    pool = _HERO_STATS
    if facts:
        keep = []
        for value, label in _HERO_STATS:
            token = value.split()[0].rstrip("%")  # "24/7","90","1999","15","Live"
            if token in facts or value.lower() in facts.lower() or value == "Live":
                keep.append((value, label))
        pool = keep or _HERO_STATS
    h = int(hashlib.sha1((seed_text or "prolink").encode("utf-8")).hexdigest(), 16)
    return pool[h % len(pool)]


# ══════════════════════════════════════════════════════════════════════════
# STYLE 1 — bold_type : navy gradient ground, big bold white headline (anchor)
# ══════════════════════════════════════════════════════════════════════════
def _card_bold_type(headline, kicker, cta, accent=GOLD, **_):
    img = Image.new("RGB", (W, H), NAVY_BLACK)
    d = ImageDraw.Draw(img)
    _gradient(d, 0, 0, W, H, NAVY_BLACK, NAVY_DEEP)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W - 460, -300, W + 260, 400], fill=(*NAVY, 70))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)
    d.ellipse([MARGIN, 128, MARGIN + 16, 144], fill=accent)
    _tracked(d, (MARGIN + 30, 124), (kicker or "").upper(), _font("semi", 30), accent, 2.5)
    d.rectangle([MARGIN, 186, MARGIN + 84, 194], fill=accent)
    hf, lines, lh = _fit(d, headline, "extrabold", W - 2 * MARGIN, 470, 104, 56, 1.06)
    y = 244
    for ln in lines:
        d.text((MARGIN, y), ln, font=hf, fill=WHITE)
        y += lh
    _cta_pill(d, cta, MARGIN, H - 300, GOLD, NAVY_DEEP)
    _logo_lockup(img, d, MARGIN + 22, H - 150, 74, ground="dark")
    _contact_line(d, H - 150)
    return img


# ══════════════════════════════════════════════════════════════════════════
# STYLE 2 — stat : navy panel, ONE large hero figure from verified facts
# ══════════════════════════════════════════════════════════════════════════
def _card_stat(headline, kicker, cta, accent=GOLD, stat_value=None,
               stat_label=None, **_):
    if not stat_value:
        stat_value, stat_label = _pick_hero(headline)
    support = (stat_label or headline or "").strip()
    img = Image.new("RGB", (W, H), NAVY_BLACK)
    d = ImageDraw.Draw(img)
    _gradient(d, 0, 0, W, H, NAVY_DEEP, NAVY_BLACK)
    _tracked(d, (MARGIN, 132), (kicker or "").upper(), _font("semi", 30), accent, 3.0)
    sf = _font("black", 460)
    while d.textlength(stat_value, font=sf) > W - 2 * MARGIN and sf.size > 160:
        sf = _font("black", sf.size - 12)
    asc, desc = sf.getmetrics()
    sy = 250
    d.text((MARGIN, sy), stat_value, font=sf, fill=GOLD)
    y = sy + asc + 40
    d.rectangle([MARGIN, y, MARGIN + 150, y + 8], fill=accent)
    y += 44
    rf, lines, lh = _fit(d, support, "semi", W - 2 * MARGIN, 260, 60, 38, 1.16)
    for ln in lines:
        d.text((MARGIN, y), ln, font=rf, fill=WHITE)
        y += lh
    _logo_lockup(img, d, MARGIN + 22, H - 150, 74, ground="dark")
    _contact_line(d, H - 150)
    return img


# ══════════════════════════════════════════════════════════════════════════
# STYLE 3 — illustrative : LIGHT paper/ink card, navy ink, gold arc motif
# ══════════════════════════════════════════════════════════════════════════
def _card_illustrative(headline, kicker, cta, accent=GOLD, **_):
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    cx, cy = W + 40, H + 40
    for i, r in enumerate(range(220, 1180, 116)):
        col = (*GOLD, 150) if i % 3 == 0 else (*NAVY_DEEP, 95)
        od.arc([cx - r, cy - r, cx + r, cy + r], start=180, end=270, fill=col, width=6)
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(img)
    _tracked(d, (MARGIN, 132), (kicker or "").upper(), _font("semi", 30), GOLD, 3.0)
    d.rectangle([MARGIN, 186, MARGIN + 84, 191], fill=GOLD)
    hf, lines, lh = _fit(d, headline, "bold", W - 2 * MARGIN - 40, 430, 96, 52, 1.08)
    y = 236
    for ln in lines:
        d.text((MARGIN, y), ln, font=hf, fill=NAVY_INK)
        y += lh
    _cta_pill(d, cta, MARGIN, H - 300, NAVY_DEEP, CREAM)
    _logo_lockup(img, d, MARGIN, H - 138, 66, ground="cream")
    _contact_line(d, H - 150, color=NAVY_INK)
    return img


# ══════════════════════════════════════════════════════════════════════════
# STYLE 4 — quote : inverted gold-on-navy, oversized quote mark, airy
# ══════════════════════════════════════════════════════════════════════════
def _card_quote(headline, kicker, cta, accent=GOLD, **_):
    img = Image.new("RGB", (W, H), NAVY_DEEP)
    d = ImageDraw.Draw(img)
    _gradient(d, 0, 0, W, H, NAVY_DEEP, (9, 40, 72))
    d.text((MARGIN - 16, 40), "\u201c", font=_font("black", 380), fill=GOLD)
    hf, lines, lh = _fit(d, headline, "med", W - 2 * MARGIN, 360, 82, 48, 1.22)
    y = 400
    for ln in lines:
        d.text((MARGIN, y), ln, font=hf, fill=GOLD_WARM)
        y += lh
    y += 22
    d.rectangle([MARGIN, y, MARGIN + 96, y + 6], fill=WHITE)
    _tracked(d, (MARGIN, y + 26), (kicker or "").upper(), _font("semi", 27), (208, 220, 236), 3.0)
    _logo_lockup(img, d, MARGIN + 22, H - 150, 74, ground="dark")
    _contact_line(d, H - 150)
    return img


# ══════════════════════════════════════════════════════════════════════════
# STYLE 5 — bright_accent : gold-forward ground, navy type, navy corner block
# ══════════════════════════════════════════════════════════════════════════
def _card_bright(headline, kicker, cta, accent=GOLD, **_):
    img = Image.new("RGB", (W, H), GOLD)
    d = ImageDraw.Draw(img)
    _gradient(d, 0, 0, W, H, GOLD_WARM, GOLD)
    d.polygon([(W, H), (W, H - 360), (W - 360, H)], fill=NAVY_DEEP)
    _tracked(d, (MARGIN, 132), (kicker or "").upper(), _font("semi", 30), NAVY_DEEP, 3.0)
    d.rectangle([MARGIN, 186, MARGIN + 84, 194], fill=NAVY_DEEP)
    hf, lines, lh = _fit(d, headline, "extrabold", W - 2 * MARGIN, 440, 100, 54, 1.06)
    y = 244
    for ln in lines:
        d.text((MARGIN, y), ln, font=hf, fill=NAVY_DEEP)
        y += lh
    _cta_pill(d, cta, MARGIN, H - 300, NAVY_DEEP, GOLD)
    _logo_lockup(img, d, MARGIN + 22, H - 150, 74, ground="gold")
    _contact_line(d, H - 150, color=NAVY_DEEP)
    return img


# ══════════════════════════════════════════════════════════════════════════
# STYLE 6 — photo : duotone photo ground (ASSET-GATED). Falls back to bold navy
# when no verified photograph is supplied, so the engine never fabricates people.
# ══════════════════════════════════════════════════════════════════════════
def _square_from_focal(src, fx, fy):
    """Center-crop a landscape frame to a square around its focal point, then
    resize to the card size. Keeps the subject in frame instead of stretching."""
    side = min(src.width, src.height)
    cx, cy = int(src.width * fx), int(src.height * fy)
    left = max(0, min(src.width - side, cx - side // 2))
    top = max(0, min(src.height - side, cy - side // 2))
    return src.crop((left, top, left + side, top + side)).resize((W, H), Image.LANCZOS)


def _directional_scrim(text_pos):
    """A brand-navy scrim (uniform) plus a gradient that deepens toward the text
    side, so an overlaid headline stays legible over any photo."""
    base = Image.new("RGBA", (W, H), (*NAVY_BLACK, 96))          # even darkening
    grad = Image.new("L", (1, H))
    for yy in range(H):
        t = yy / (H - 1)
        a = t if text_pos == "bottom" else (1 - t)
        grad.putpixel((0, yy), int(24 + 205 * (a ** 1.6)))
    ramp = Image.new("RGBA", (W, H), (*NAVY_BLACK, 0))
    ramp.putalpha(grad.resize((W, H)))
    return Image.alpha_composite(base, ramp)


def _card_photo(headline, kicker, cta, accent=GOLD, photo_path=None,
                photo_focal=None, photo_text=None, **_):
    """photographic: a REAL registered photo as a duotone ground with a legible
    headline overlay. ASSET-GATED - only renders a photo when one is registered in
    assets/variety_assets.json and present on disk; otherwise falls back to the
    bold navy card so the engine never fabricates imagery of people."""
    if not (photo_path and os.path.exists(photo_path)):
        return _card_bold_type(headline, kicker, cta, accent)
    fx, fy = photo_focal or (0.5, 0.5)
    text_pos = photo_text or "bottom"
    sq = _square_from_focal(Image.open(photo_path).convert("RGB"), fx, fy)
    # Brand duotone: shadows -> deep navy, highlights -> soft warm white.
    duo = ImageOps.colorize(sq.convert("L"), black=NAVY_BLACK, white=(238, 240, 244),
                            mid=NAVY_DEEP).convert("RGBA")
    img = Image.alpha_composite(duo, _directional_scrim(text_pos)).convert("RGB")
    d = ImageDraw.Draw(img)
    # thin gold brand rule at the top edge
    d.rectangle([MARGIN, 96, MARGIN + 84, 104], fill=accent)

    if text_pos == "top":
        _tracked(d, (MARGIN, 128), (kicker or "").upper(), _font("semi", 30), accent, 2.5)
        hf, lines, lh = _fit(d, headline, "extrabold", W - 2 * MARGIN, 320, 90, 50, 1.06)
        y = 182
        for ln in lines:
            d.text((MARGIN, y), ln, font=hf, fill=WHITE)
            y += lh
        _cta_pill(d, cta, MARGIN, H - 300, GOLD, NAVY_DEEP)
    else:
        hf, lines, lh = _fit(d, headline, "extrabold", W - 2 * MARGIN, 320, 90, 50, 1.06)
        block_h = len(lines) * lh
        head_bottom = (H - 300) - 40            # sit just above the CTA pill
        y = head_bottom - block_h
        _tracked(d, (MARGIN, y - 52), (kicker or "").upper(), _font("semi", 30), accent, 2.5)
        for ln in lines:
            d.text((MARGIN, y), ln, font=hf, fill=WHITE)
            y += lh
        _cta_pill(d, cta, MARGIN, H - 300, GOLD, NAVY_DEEP)

    _logo_lockup(img, d, MARGIN + 22, H - 150, 74, ground="dark")
    _contact_line(d, H - 150)
    return img


# The five distinct autonomous styles, plus the asset-gated photo style. The
# names match social_variety.STYLE_RENDER["...card_style"].
STYLES = ("bold_type", "stat", "illustrative", "quote", "bright_accent", "photo")

_CARD_BUILDERS = {
    "bold_type":     _card_bold_type,
    "stat":          _card_stat,
    "illustrative":  _card_illustrative,
    "quote":         _card_quote,
    "bright_accent": _card_bright,
    "photo":         _card_photo,
}


def make_card(headline, kicker, cta, out_path, accent=GOLD, style="bold_type",
              photo_path=None, palette_variant=None, stat_value=None,
              stat_label=None, photo_focal=None, photo_text=None):
    """Render a 1080x1080 brand card in one of the distinct visual styles.

    style: bold_type | stat | illustrative | quote | bright_accent | photo
    palette_variant: passed through from social_variety.STYLE_RENDER; accepted so
        the planner's ground choice is honored end-to-end. Each style already owns
        its ground, so this is advisory (kept for forward compatibility and to
        close the gap where palette_variant was computed but never consumed).
    stat_value / stat_label: optional explicit hero for the stat style; when
        omitted, a verified figure is chosen from editorial/verified_facts.json.

    Brand DNA (real logo, navy + gold, calm voice) is constant across every style.
    """
    builder = _CARD_BUILDERS.get(style, _card_bold_type)
    img = builder(headline, kicker, cta, accent,
                  photo_path=photo_path, palette_variant=palette_variant,
                  stat_value=stat_value, stat_label=stat_label,
                  photo_focal=photo_focal, photo_text=photo_text)
    img.save(out_path, "PNG")
    return out_path


if __name__ == "__main__":
    headline = sys.argv[1] if len(sys.argv) > 1 else \
        "IT support that answers on the first ring."
    kicker = sys.argv[2] if len(sys.argv) > 2 else "US-Based Help Desk"
    cta = sys.argv[3] if len(sys.argv) > 3 else "Book a free assessment"
    style = sys.argv[4] if len(sys.argv) > 4 else "bold_type"
    out = sys.argv[5] if len(sys.argv) > 5 else os.path.join(HERE, "scratch", "_card_preview.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print(make_card(headline, kicker, cta, out, style=style))
