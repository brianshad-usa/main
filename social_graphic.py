"""
social_graphic.py
-----------------
Generates a branded square (1080x1080) social card for Pro Link Systems in one
of many VISUALLY DISTINCT styles. Each style sits on its OWN ground AND its OWN
layout skeleton, so the feed stops looking samey at thumbnail scale -- the
earlier failure mode was that every "style" shared one navy-ish ground and the
identical left-aligned corner-furniture layout, so the rotation was invisible.

Brand DNA stays recognizable on every card: the real logo.png, navy + gold
present somewhere, and a calm professional voice.

GROUND families (the single biggest driver of "does the feed look varied"):
  navy   deep navy gradient                 (anchor; capped in rotation)
  gold   solid brand-gold ground
  cream  warm paper ground
  white  clean white / near-white ground
  split  two-tone split panel (navy + light)
  photo  real registered photograph (ASSET-GATED)

LAYOUTS (so two cards on the same ground still differ in composition):
  left_block   kicker + big left headline (the classic)
  centered     centered headline, hairline rules above/below (magazine cover)
  stat_hero    one giant centered figure + support line
  split        text on one panel, brand mark on the other
  checklist     a titled, saveable list of 3-4 checked items
  banner       a colored top banner (badge) + roomy body below

The visual treatment is chosen by social_variety.py (STYLE_RENDER) and threaded
through content_studio.py via `style`. Brand marks are fixed by the renderer;
the treatment never changes the brand marks.

Fonts: bundled Inter variable font (assets/fonts/Inter.ttf) so local (Windows)
and CI (Linux) render identically. Pure Pillow, no external services.
"""

import os
import sys
import json
import hashlib
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))

# ── Brand palette (navy anchor + gold accent, plus paper/white registers) ──
NAVY_BLACK = (6, 18, 30)       # #06121e  deepest ground
NAVY_DEEP  = (13, 59, 102)     # #0d3b66  brand navy anchor
NAVY       = (26, 93, 171)     # #1a5dab  brand navy (brighter)
NAVY_INK   = (17, 38, 62)      # ink on paper / gold
GOLD       = (247, 148, 29)    # #f7941d  brand gold accent
GOLD_WARM  = (245, 166, 35)    # slightly softer gold
GOLD_DEEP  = (214, 122, 16)    # deeper gold for rules on light grounds
CREAM      = (245, 241, 232)   # #f5f1e8  paper ground
CREAM_LINE = (219, 210, 193)
PAPER_WHITE = (252, 252, 250)  # near-white editorial ground
WHITE_LINE = (224, 228, 234)
INK        = (23, 33, 45)
WHITE      = (255, 255, 255)
MUTED      = (95, 110, 130)
MUTED_LIGHT = (120, 134, 152)

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
    return x


def _tracked_w(d, text, f, tracking=3.0):
    """Width of a tracked string (for centering)."""
    if not text:
        return 0
    return sum(d.textlength(ch, font=f) + tracking for ch in text) - tracking


try:
    _LOGO = Image.open(LOGO_PATH).convert("RGBA")
except Exception:
    _LOGO = None


def _logo_lockup(img, d, x, y, target_h, ground="dark"):
    """Place the real logo so it always reads. The wordmark's navy strokes vanish
    on dark or gold grounds, so it sits on a white rounded chip there; on a light
    (cream/white) ground it sits directly."""
    if _LOGO is None:
        return x
    lg = _LOGO.resize((int(_LOGO.width * target_h / _LOGO.height), target_h), Image.LANCZOS)
    if ground in ("cream", "light", "white"):
        img.paste(lg, (x, y), lg)
        return x + lg.width
    pad = 22
    d.rounded_rectangle([x - pad, y - pad, x + lg.width + pad, y + lg.height + pad],
                        radius=(lg.height + 2 * pad) // 2, fill=WHITE)
    img.paste(lg, (x, y), lg)
    return x + lg.width + pad


def _logo_lockup_centered(img, d, cx, y, target_h, ground="dark"):
    if _LOGO is None:
        return
    lg = _LOGO.resize((int(_LOGO.width * target_h / _LOGO.height), target_h), Image.LANCZOS)
    x = int(cx - lg.width / 2)
    if ground in ("cream", "light", "white"):
        img.paste(lg, (x, y), lg)
        return
    pad = 20
    d.rounded_rectangle([x - pad, y - pad, x + lg.width + pad, y + lg.height + pad],
                        radius=(lg.height + 2 * pad) // 2, fill=WHITE)
    img.paste(lg, (x, y), lg)


def _contact_line(d, y, color=WHITE, right=None):
    f1 = _font("semi", 30)
    f2 = _font("reg", 27)
    right = (W - MARGIN) if right is None else right
    d.text((right - d.textlength("prolinksystems.com", font=f1), y),
           "prolinksystems.com", font=f1, fill=color)
    sub = MUTED if color == WHITE else color
    d.text((right - d.textlength("1-800-890-6133", font=f2), y + 40),
           "1-800-890-6133", font=f2, fill=sub)


def _contact_centered(d, cx, y, color):
    f1 = _font("semi", 28)
    t = "prolinksystems.com  ·  1-800-890-6133"
    d.text((cx - d.textlength(t, font=f1) / 2, y), t, font=f1, fill=color)


def _cta_caption(d, cta, x, y, fill, text_fill=None):
    """Draw the call-to-action as a plain, arrow-led CAPTION -- deliberately NOT a
    button (a feed image is not clickable; the real link lives in the post copy)."""
    if not cta:
        return 0
    cf = _font("semi", 32)
    label = f"\u2192 {cta}"
    d.text((x, y), label, font=cf, fill=fill)
    asc, desc = cf.getmetrics()
    return asc + desc


# Back-compat alias.
_cta_pill = _cta_caption


# ── Verified-fact hero figures for the stat styles ───────────────────────
_HERO_STATS = [
    ("24/7",   "US-based help desk, always on"),
    ("90%",    "first-contact resolution"),
    ("1999",   "serving Los Angeles businesses since"),
    ("15 min", "average ticket first-response time"),
    ("Live",   "phone answered by a real technician"),
]


def _verified_facts_text():
    try:
        with open(FACTS_PATH, encoding="utf-8") as f:
            return json.dumps(json.load(f))
    except Exception:
        return ""


def _pick_hero(seed_text):
    facts = _verified_facts_text()
    pool = _HERO_STATS
    if facts:
        keep = []
        for value, label in _HERO_STATS:
            token = value.split()[0].rstrip("%")
            if token in facts or value.lower() in facts.lower() or value == "Live":
                keep.append((value, label))
        pool = keep or _HERO_STATS
    h = int(hashlib.sha1((seed_text or "prolink").encode("utf-8")).hexdigest(), 16)
    return pool[h % len(pool)]


# ══════════════════════════════════════════════════════════════════════════
# NAVY family
# ══════════════════════════════════════════════════════════════════════════
def _card_bold_type(headline, kicker, cta, accent=GOLD, **_):
    """navy / left_block -- the anchor look."""
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
    _cta_caption(d, cta, MARGIN, H - 300, GOLD)
    _logo_lockup(img, d, MARGIN + 22, H - 150, 74, ground="dark")
    _contact_line(d, H - 150)
    return img


def _card_stat(headline, kicker, cta, accent=GOLD, stat_value=None,
               stat_label=None, **_):
    """navy / stat_hero -- one large verified figure, left aligned."""
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


def _card_quote(headline, kicker, cta, accent=GOLD, **_):
    """navy / centered -- inverted gold-on-navy quote, airy."""
    img = Image.new("RGB", (W, H), NAVY_DEEP)
    d = ImageDraw.Draw(img)
    _gradient(d, 0, 0, W, H, NAVY_DEEP, (9, 40, 72))
    # centered oversized quote mark
    qm = _font("black", 300)
    d.text((W / 2 - d.textlength("\u201c", font=qm) / 2, 70), "\u201c", font=qm, fill=GOLD)
    hf, lines, lh = _fit(d, headline, "med", W - 2 * MARGIN - 40, 360, 78, 46, 1.24)
    total = len(lines) * lh
    y = 430 - total // 2 + 120
    for ln in lines:
        d.text((W / 2 - d.textlength(ln, font=hf) / 2, y), ln, font=hf, fill=GOLD_WARM)
        y += lh
    y += 24
    d.rectangle([W / 2 - 48, y, W / 2 + 48, y + 6], fill=WHITE)
    kf = _font("semi", 27)
    _tracked(d, (W / 2 - _tracked_w(d, (kicker or "").upper(), kf, 3.0) / 2, y + 26),
             (kicker or "").upper(), kf, (208, 220, 236), 3.0)
    _logo_lockup_centered(img, d, W / 2, H - 150, 70, ground="dark")
    return img


# ══════════════════════════════════════════════════════════════════════════
# GOLD family
# ══════════════════════════════════════════════════════════════════════════
def _card_bright(headline, kicker, cta, accent=GOLD, **_):
    """gold / left_block -- gold ground, navy type, navy corner block."""
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
    _cta_caption(d, cta, MARGIN, H - 300, NAVY_DEEP)
    _logo_lockup(img, d, MARGIN + 22, H - 150, 74, ground="gold")
    _contact_line(d, H - 150, color=NAVY_DEEP)
    return img


def _card_tip_banner(headline, kicker, cta, accent=GOLD, **_):
    """gold+white / banner -- a gold top banner badge over a clean white body.
    Reads as a friendly, saveable tip, totally unlike the big-headline cards."""
    img = Image.new("RGB", (W, H), PAPER_WHITE)
    d = ImageDraw.Draw(img)
    band_h = 150
    _gradient(d, 0, 0, W, band_h, GOLD_WARM, GOLD)
    badge = (kicker or "Quick tip").upper()
    bf = _font("bold", 34)
    _tracked(d, (MARGIN, band_h // 2 - 22), badge, bf, NAVY_DEEP, 3.0)
    # small navy ticks motif on the right of the band
    for i in range(3):
        bx = W - MARGIN - 40 - i * 46
        d.line([(bx, band_h // 2 - 2), (bx + 12, band_h // 2 + 12),
                (bx + 34, band_h // 2 - 18)], fill=NAVY_DEEP, width=7, joint="curve")
    hf, lines, lh = _fit(d, headline, "extrabold", W - 2 * MARGIN, 430, 92, 50, 1.08)
    y = band_h + 90
    for ln in lines:
        d.text((MARGIN, y), ln, font=hf, fill=NAVY_INK)
        y += lh
    d.rectangle([MARGIN, y + 12, MARGIN + 110, y + 20], fill=GOLD)
    _cta_caption(d, cta, MARGIN, H - 300, GOLD_DEEP)
    _logo_lockup(img, d, MARGIN, H - 140, 66, ground="white")
    _contact_line(d, H - 150, color=NAVY_INK)
    return img


# ══════════════════════════════════════════════════════════════════════════
# CREAM family
# ══════════════════════════════════════════════════════════════════════════
def _card_illustrative(headline, kicker, cta, accent=GOLD, **_):
    """cream / left_block -- paper ground, navy ink, gold arc motif."""
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
    _tracked(d, (MARGIN, 132), (kicker or "").upper(), _font("semi", 30), GOLD_DEEP, 3.0)
    d.rectangle([MARGIN, 186, MARGIN + 84, 191], fill=GOLD)
    hf, lines, lh = _fit(d, headline, "bold", W - 2 * MARGIN - 40, 430, 96, 52, 1.08)
    y = 236
    for ln in lines:
        d.text((MARGIN, y), ln, font=hf, fill=NAVY_INK)
        y += lh
    _cta_caption(d, cta, MARGIN, H - 300, NAVY_DEEP)
    _logo_lockup(img, d, MARGIN, H - 138, 66, ground="cream")
    _contact_line(d, H - 150, color=NAVY_INK)
    return img


def _card_checklist(headline, kicker, cta, accent=GOLD, items=None, **_):
    """cream / checklist -- a titled, saveable list of checked items."""
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    # subtle top gold rule
    d.rectangle([MARGIN, 120, MARGIN + 84, 128], fill=GOLD)
    _tracked(d, (MARGIN, 140), (kicker or "Checklist").upper(), _font("semi", 28), GOLD_DEEP, 3.0)
    hf, lines, lh = _fit(d, headline, "extrabold", W - 2 * MARGIN, 220, 70, 42, 1.08)
    y = 196
    for ln in lines:
        d.text((MARGIN, y), ln, font=hf, fill=NAVY_INK)
        y += lh
    y += 24
    # Derive list items from headline if none supplied (preview/offline safety).
    if not items:
        items = ["Confirm it's covered", "Check who owns it", "Test it this quarter"]
    itf = _font("semi", 40)
    for it in items[:4]:
        cyc = y + 26
        d.ellipse([MARGIN, cyc - 22, MARGIN + 44, cyc + 22], outline=GOLD, width=5)
        d.line([(MARGIN + 11, cyc), (MARGIN + 20, cyc + 11), (MARGIN + 34, cyc - 12)],
               fill=GOLD_DEEP, width=6, joint="curve")
        tl = _wrap(d, it, itf, W - 2 * MARGIN - 72)
        ty = y
        for seg in tl[:2]:
            d.text((MARGIN + 72, ty), seg, font=itf, fill=NAVY_INK)
            ty += 52
        y = ty + 30
    _logo_lockup(img, d, MARGIN, H - 138, 62, ground="cream")
    _contact_line(d, H - 150, color=NAVY_INK)
    return img


# ══════════════════════════════════════════════════════════════════════════
# WHITE family
# ══════════════════════════════════════════════════════════════════════════
def _card_editorial_light(headline, kicker, cta, accent=GOLD, **_):
    """white / centered -- airy magazine-cover treatment, hairline rules."""
    img = Image.new("RGB", (W, H), PAPER_WHITE)
    d = ImageDraw.Draw(img)
    cx = W / 2
    # top centered kicker between two short gold rules
    kf = _font("semi", 28)
    kick = (kicker or "").upper()
    kw = _tracked_w(d, kick, kf, 3.0)
    ky = 250
    d.rectangle([cx - kw / 2 - 70, ky + 16, cx - kw / 2 - 26, ky + 20], fill=GOLD)
    d.rectangle([cx + kw / 2 + 26, ky + 16, cx + kw / 2 + 70, ky + 20], fill=GOLD)
    _tracked(d, (cx - kw / 2, ky), kick, kf, GOLD_DEEP, 3.0)
    hf, lines, lh = _fit(d, headline, "extrabold", W - 2 * MARGIN - 30, 340, 94, 52, 1.1)
    total = len(lines) * lh
    y = 430 - total // 2 + 90
    for ln in lines:
        d.text((cx - d.textlength(ln, font=hf) / 2, y), ln, font=hf, fill=NAVY_INK)
        y += lh
    if cta:
        cf = _font("semi", 32)
        lab = f"\u2192 {cta}"
        d.text((cx - d.textlength(lab, font=cf) / 2, y + 20), lab, font=cf, fill=GOLD_DEEP)
    _logo_lockup_centered(img, d, cx, H - 180, 64, ground="white")
    _contact_centered(d, cx, H - 92, NAVY_INK)
    return img


def _card_stat_hero_light(headline, kicker, cta, accent=GOLD, stat_value=None,
                          stat_label=None, **_):
    """white / stat_hero -- one giant navy figure centered on white."""
    if not stat_value:
        stat_value, stat_label = _pick_hero(headline)
    support = (stat_label or headline or "").strip()
    img = Image.new("RGB", (W, H), PAPER_WHITE)
    d = ImageDraw.Draw(img)
    cx = W / 2
    kf = _font("semi", 28)
    kick = (kicker or "By the numbers").upper()
    _tracked(d, (cx - _tracked_w(d, kick, kf, 3.0) / 2, 230), kick, kf, GOLD_DEEP, 3.0)
    sf = _font("black", 420)
    while d.textlength(stat_value, font=sf) > W - 2 * MARGIN and sf.size > 150:
        sf = _font("black", sf.size - 12)
    asc, desc = sf.getmetrics()
    sy = 300
    d.text((cx - d.textlength(stat_value, font=sf) / 2, sy), stat_value, font=sf, fill=NAVY_DEEP)
    y = sy + asc + 24
    d.rectangle([cx - 70, y, cx + 70, y + 8], fill=GOLD)
    y += 40
    rf, lines, lh = _fit(d, support, "semi", W - 2 * MARGIN, 180, 54, 36, 1.18)
    for ln in lines:
        d.text((cx - d.textlength(ln, font=rf) / 2, y), ln, font=rf, fill=NAVY_INK)
        y += lh
    _logo_lockup_centered(img, d, cx, H - 180, 64, ground="white")
    _contact_centered(d, cx, H - 92, NAVY_INK)
    return img


# ══════════════════════════════════════════════════════════════════════════
# SPLIT family -- two-tone panels (completely different composition)
# ══════════════════════════════════════════════════════════════════════════
def _card_split(headline, kicker, cta, accent=GOLD, **_):
    """split / split -- navy left panel (kicker + brand), light right panel (headline)."""
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    panel = 430
    _gradient(d, 0, 0, panel, H, NAVY_DEEP, NAVY_BLACK)
    d.rectangle([panel, 0, panel + 10, H], fill=GOLD)
    # left panel: kicker (rotated-feel vertical stack) + a gold tick + logo
    _tracked(d, (MARGIN, 150), (kicker or "").upper(), _font("semi", 30), GOLD, 2.5)
    d.rectangle([MARGIN, 210, MARGIN + 70, 218], fill=GOLD)
    # a simple brand motif on the navy panel
    for i, r in enumerate(range(120, 460, 90)):
        d.arc([MARGIN - 40, H - 360 - r, MARGIN - 40 + 2 * r, H - 360 + r],
              start=270, end=360, fill=(*GOLD, 255) if i % 2 == 0 else (*NAVY, 255), width=5)
    _logo_lockup(img, d, MARGIN, H - 150, 64, ground="dark")
    # right panel: big navy headline on cream
    rx = panel + 60
    hf, lines, lh = _fit(d, headline, "extrabold", W - rx - MARGIN, 460, 82, 46, 1.1)
    total = len(lines) * lh
    y = H // 2 - total // 2
    for ln in lines:
        d.text((rx, y), ln, font=hf, fill=NAVY_INK)
        y += lh
    _cta_caption(d, cta, rx, y + 20, GOLD_DEEP)
    _contact_line(d, H - 92, color=NAVY_INK)
    return img


# ══════════════════════════════════════════════════════════════════════════
# PHOTO family (ASSET-GATED)
# ══════════════════════════════════════════════════════════════════════════
def _square_from_focal(src, fx, fy):
    side = min(src.width, src.height)
    cx, cy = int(src.width * fx), int(src.height * fy)
    left = max(0, min(src.width - side, cx - side // 2))
    top = max(0, min(src.height - side, cy - side // 2))
    return src.crop((left, top, left + side, top + side)).resize((W, H), Image.LANCZOS)


def _directional_scrim(text_pos, base_alpha=96, deep=NAVY_BLACK):
    base = Image.new("RGBA", (W, H), (*deep, base_alpha))
    grad = Image.new("L", (1, H))
    for yy in range(H):
        t = yy / (H - 1)
        a = t if text_pos == "bottom" else (1 - t)
        grad.putpixel((0, yy), int(24 + 205 * (a ** 1.6)))
    ramp = Image.new("RGBA", (W, H), (*deep, 0))
    ramp.putalpha(grad.resize((W, H)))
    return Image.alpha_composite(base, ramp)


def _card_photo(headline, kicker, cta, accent=GOLD, photo_path=None,
                photo_focal=None, photo_text=None, light=False, **_):
    """photographic: a REAL registered photo as a duotone ground with a legible
    headline overlay. ASSET-GATED. `light=True` renders a warmer, brighter wash
    so photo posts don't all read as another navy card."""
    if not (photo_path and os.path.exists(photo_path)):
        return _card_bold_type(headline, kicker, cta, accent)
    fx, fy = photo_focal or (0.5, 0.5)
    text_pos = photo_text or "bottom"
    sq = _square_from_focal(Image.open(photo_path).convert("RGB"), fx, fy)
    if light:
        duo = ImageOps.colorize(sq.convert("L"), black=(40, 55, 78),
                                white=(250, 248, 243), mid=(150, 150, 150)).convert("RGBA")
        scrim = _directional_scrim(text_pos, base_alpha=40, deep=NAVY_BLACK)
    else:
        duo = ImageOps.colorize(sq.convert("L"), black=NAVY_BLACK, white=(238, 240, 244),
                                mid=NAVY_DEEP).convert("RGBA")
        scrim = _directional_scrim(text_pos, base_alpha=96)
    img = Image.alpha_composite(duo, scrim).convert("RGB")
    d = ImageDraw.Draw(img)
    text_fill = WHITE if not light else NAVY_INK
    kick_fill = accent
    d.rectangle([MARGIN, 96, MARGIN + 84, 104], fill=accent)
    if text_pos == "top":
        _tracked(d, (MARGIN, 128), (kicker or "").upper(), _font("semi", 30), kick_fill, 2.5)
        hf, lines, lh = _fit(d, headline, "extrabold", W - 2 * MARGIN, 320, 90, 50, 1.06)
        y = 182
        for ln in lines:
            d.text((MARGIN, y), ln, font=hf, fill=text_fill)
            y += lh
        _cta_caption(d, cta, MARGIN, H - 300, accent)
    else:
        hf, lines, lh = _fit(d, headline, "extrabold", W - 2 * MARGIN, 320, 90, 50, 1.06)
        block_h = len(lines) * lh
        head_bottom = (H - 300) - 40
        y = head_bottom - block_h
        _tracked(d, (MARGIN, y - 52), (kicker or "").upper(), _font("semi", 30), kick_fill, 2.5)
        for ln in lines:
            d.text((MARGIN, y), ln, font=hf, fill=text_fill)
            y += lh
        _cta_caption(d, cta, MARGIN, H - 300, accent)
    # logo chip always reads (white chip), contact line in a safe color
    _logo_lockup(img, d, MARGIN + 22, H - 150, 74, ground="dark")
    _contact_line(d, H - 150, color=WHITE if not light else NAVY_INK)
    return img


def _card_photo_light(headline, kicker, cta, accent=GOLD, **kw):
    return _card_photo(headline, kicker, cta, accent, light=True, **kw)


# ── Style registry ────────────────────────────────────────────────────────
# Each card_style name maps to a builder. ground/layout metadata lives in
# social_variety.py (STYLE_META) and drives rotation diversity.
STYLES = ("bold_type", "stat", "quote", "bright_accent", "tip_banner",
          "illustrative", "checklist", "editorial_light", "stat_hero_light",
          "split", "photo", "photo_light")

_CARD_BUILDERS = {
    "bold_type":        _card_bold_type,
    "stat":             _card_stat,
    "quote":            _card_quote,
    "bright_accent":    _card_bright,
    "tip_banner":       _card_tip_banner,
    "illustrative":     _card_illustrative,
    "checklist":        _card_checklist,
    "editorial_light":  _card_editorial_light,
    "stat_hero_light":  _card_stat_hero_light,
    "split":            _card_split,
    "photo":            _card_photo,
    "photo_light":      _card_photo_light,
}


def make_card(headline, kicker, cta, out_path, accent=GOLD, style="bold_type",
              photo_path=None, palette_variant=None, stat_value=None,
              stat_label=None, photo_focal=None, photo_text=None, items=None):
    """Render a 1080x1080 brand card in one of the distinct visual styles.

    style: one of social_graphic.STYLES. Each owns its own ground + layout.
    items: optional list for the checklist style.
    Brand DNA (real logo, navy + gold, calm voice) is constant across styles.
    """
    builder = _CARD_BUILDERS.get(style, _card_bold_type)
    img = builder(headline, kicker, cta, accent,
                  photo_path=photo_path, palette_variant=palette_variant,
                  stat_value=stat_value, stat_label=stat_label,
                  photo_focal=photo_focal, photo_text=photo_text, items=items)
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
