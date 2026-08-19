"""
social_graphic.py
-----------------
Generates a branded square (1080x1080) social card for Pro Link Systems:
navy gradient hero with the post headline + CTA pill, and a white footer
holding the REAL company logo (logo.png) and contact line.

Always composites the actual logo.png for brand consistency.

Fonts: bundled Inter variable font (assets/fonts/Inter.ttf) so local (Windows)
and CI (Linux) render identically. Falls back to Segoe UI / Liberation / DejaVu
if the bundled font is ever missing.

Used by social_syndicate.py. Pure Pillow, no external services.
"""

import os
import re
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

# ── Brand palette ────────────────────────────────────────────────
NAVY_DARK = (6, 20, 29)       # #06141d
NAVY      = (11, 61, 107)     # #0b3d6b
NAVY_MID  = (13, 77, 133)     # #0d4d85
GOLD      = (245, 166, 35)    # #f5a623
WHITE     = (255, 255, 255)
MUTED     = (90, 106, 128)    # #5a6a80

# ── Fonts ────────────────────────────────────────────────────────
INTER_VAR = os.environ.get("INTER_FONT", os.path.join(HERE, "assets", "fonts", "Inter.ttf"))
_WIN = r"C:\Windows\Fonts"
_FALLBACKS = {
    "head": [os.path.join(_WIN, "segoeuib.ttf"),
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "semi": [os.path.join(_WIN, "seguisb.ttf"),
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "reg":  [os.path.join(_WIN, "segoeui.ttf"),
             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}
_VARIATION = {"head": "Bold", "semi": "SemiBold", "reg": "Regular"}

LOGO_PATH = os.environ.get("LOGO_PATH", os.path.join(HERE, "logo.png"))

W = H = 1080
MARGIN = 84
FOOTER_H = 196


def _font(role, size):
    if os.path.exists(INTER_VAR):
        try:
            f = ImageFont.truetype(INTER_VAR, size)
            f.set_variation_by_name(_VARIATION[role])
            return f
        except Exception:
            pass
    for path in _FALLBACKS[role]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _gradient(draw, x0, y0, x1, y1, c1, c2):
    h = y1 - y0
    for i in range(h):
        t = i / max(h - 1, 1)
        col = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
        draw.line([(x0, y0 + i), (x1, y0 + i)], fill=col)


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit_headline(draw, text, max_w, max_h, start=96, min_size=46):
    size = start
    while size >= min_size:
        font = _font("head", size)
        lines = _wrap(draw, text, font, max_w)
        asc, desc = font.getmetrics()
        line_h = asc + desc + 8
        if len(lines) * line_h <= max_h and all(
                draw.textlength(l, font=font) <= max_w for l in lines):
            return font, lines, line_h
        size -= 4
    return font, lines, line_h


def _tracked(draw, xy, text, font, fill, tracking):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


# Visual-style treatments driven by social_variety.py. Every treatment keeps the
# brand DNA constant (navy ground, gold as the single accent, real logo + contact
# footer); only the hero composition changes so consecutive posts don't look alike.
STYLES = ("bold_type", "stat", "illustrative", "quote", "photo")


def _brand_footer(img, d, accent):
    """The fixed brand strip: accent border, real logo, contact block."""
    d.rectangle([0, H - FOOTER_H, W, H], fill=WHITE)
    d.rectangle([0, H - FOOTER_H, W, H - FOOTER_H + 5], fill=accent)
    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGBA")
        target_h = 86
        target_w = int(logo.width * (target_h / logo.height))
        logo = logo.resize((target_w, target_h), Image.LANCZOS)
        ly = H - FOOTER_H + (FOOTER_H - target_h) // 2
        img.paste(logo, (MARGIN, ly), logo)
    site_font = _font("semi", 32)
    tel_font = _font("reg", 28)
    right = W - MARGIN
    fy = H - FOOTER_H + 56
    d.text((right - d.textlength("prolinksystems.com", font=site_font), fy),
           "prolinksystems.com", font=site_font, fill=NAVY)
    d.text((right - d.textlength("1-800-890-6133", font=tel_font), fy + 44),
           "1-800-890-6133", font=tel_font, fill=MUTED)


def _kicker(d, kicker, accent, y=100, dot=True):
    kfont = _font("semi", 30)
    x = MARGIN
    if dot:
        d.ellipse([MARGIN, y + 4, MARGIN + 16, y + 20], fill=accent)
        x = MARGIN + 30
    _tracked(d, (x, y), kicker.upper(), kfont, accent, 2.5)


def _cta_pill(d, cta, accent=GOLD):
    cfont = _font("semi", 33)
    pad_x, pad_y = 34, 20
    tw = d.textlength(cta, font=cfont)
    asc, desc = cfont.getmetrics()
    pill_h = asc + desc + pad_y * 2
    pill_y = H - FOOTER_H - 56 - pill_h
    d.rounded_rectangle([MARGIN, pill_y, MARGIN + tw + pad_x * 2, pill_y + pill_h],
                        radius=pill_h // 2, fill=GOLD)
    d.text((MARGIN + pad_x, pill_y + pad_y - 2), cta, font=cfont, fill=NAVY)


def _navy_ground(gradient=True):
    img = Image.new("RGB", (W, H), NAVY_DARK)
    d = ImageDraw.Draw(img)
    if gradient:
        _gradient(d, 0, 0, W, H - FOOTER_H, NAVY_DARK, NAVY)
    return img, ImageDraw.Draw(img)


def _card_bold(headline, kicker, cta, accent):
    img, d = _navy_ground(gradient=True)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W - 420, -260, W + 220, 380], fill=(*NAVY_MID, 90))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)
    _kicker(d, kicker, accent)
    d.rectangle([MARGIN, 156, MARGIN + 76, 162], fill=accent)
    hfont, lines, line_h = _fit_headline(d, headline, W - 2 * MARGIN, 470)
    y = 212
    for ln in lines:
        d.text((MARGIN, y), ln, font=hfont, fill=WHITE)
        y += line_h
    _cta_pill(d, cta)
    return img, d


def _split_stat(headline):
    """Pull a leading figure out of the headline for the data_viz treatment."""
    m = re.match(r"^\s*([~<>]?\$?\d[\d,\.]*\s?%?(?:\s?(?:minutes|min|hours|hour|x))?)\b[\s:–-]*(.*)$",
                 headline, re.IGNORECASE)
    if m and m.group(1).strip():
        return m.group(1).strip(), (m.group(2).strip() or headline)
    return None, headline


def _card_stat(headline, kicker, cta, accent):
    """data_viz: one figure as the hero on a flat navy panel."""
    img, d = _navy_ground(gradient=False)
    _gradient(d, 0, 0, W, H - FOOTER_H, NAVY, NAVY_DARK)
    _kicker(d, kicker, accent)
    stat, rest = _split_stat(headline)
    y = 210
    if stat:
        sfont = _font("head", 300)
        # shrink to fit width
        while d.textlength(stat, font=sfont) > W - 2 * MARGIN and sfont.size > 120:
            sfont = _font("head", sfont.size - 12)
        d.text((MARGIN, y), stat, font=sfont, fill=GOLD)
        y += sfont.size + 24
        d.rectangle([MARGIN, y, MARGIN + 120, y + 6], fill=accent)
        y += 34
        rfont, lines, line_h = _fit_headline(d, rest, W - 2 * MARGIN, 320, start=64, min_size=40)
        for ln in lines:
            d.text((MARGIN, y), ln, font=rfont, fill=WHITE)
            y += line_h
    else:
        # no figure available: large centered claim, still distinct from bold_type
        hfont, lines, line_h = _fit_headline(d, headline, W - 2 * MARGIN, 470, start=88)
        for ln in lines:
            d.text((MARGIN, y), ln, font=hfont, fill=WHITE)
            y += line_h
    _cta_pill(d, cta)
    return img, d


def _card_illustrative(headline, kicker, cta, accent):
    """illustrative: abstract ProLink concentric-arc motif, no clip-art."""
    img, d = _navy_ground(gradient=True)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    cx, cy = W + 60, -60
    for i, r in enumerate(range(240, 1200, 150)):
        col = (*GOLD, 42) if i % 3 == 0 else (*NAVY_MID, 70)
        od.arc([cx - r, cy - r, cx + r, cy + r], start=90, end=200, fill=col, width=8)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)
    _kicker(d, kicker, accent)
    d.rectangle([MARGIN, 156, MARGIN + 76, 162], fill=accent)
    hfont, lines, line_h = _fit_headline(d, headline, W - 2 * MARGIN - 120, 470)
    y = 212
    for ln in lines:
        d.text((MARGIN, y), ln, font=hfont, fill=WHITE)
        y += line_h
    _cta_pill(d, cta)
    return img, d


def _card_quote(headline, kicker, cta, accent):
    """quote_minimal: one line, big negative space, quotation ornament."""
    img, d = _navy_ground(gradient=False)
    _gradient(d, 0, 0, W, H - FOOTER_H, NAVY_DARK, (9, 40, 70))
    # oversized quotation mark ornament
    qfont = _font("head", 340)
    d.text((MARGIN - 12, 70), "“", font=qfont, fill=GOLD)
    hfont, lines, line_h = _fit_headline(d, headline, W - 2 * MARGIN, 360, start=76, min_size=44)
    y = 360
    for ln in lines:
        d.text((MARGIN, y), ln, font=hfont, fill=WHITE)
        y += line_h
    y += 20
    d.rectangle([MARGIN, y, MARGIN + 90, y + 6], fill=accent)
    if kicker:
        _tracked(d, (MARGIN, y + 26), kicker.upper(), _font("semi", 26), accent, 2.5)
    _cta_pill(d, cta)
    return img, d


def _card_photo(headline, kicker, cta, accent, photo_path=None):
    """photographic: duotone photo ground. ASSET-GATED - only real photos.
    Falls back to a textured navy field if no verified photo is supplied, so the
    engine never fabricates imagery of people."""
    img, d = _navy_ground(gradient=True)
    if photo_path and os.path.exists(photo_path):
        photo = Image.open(photo_path).convert("L").resize((W, H - FOOTER_H))
        duo = Image.new("RGB", photo.size)
        px = photo.load()
        dp = duo.load()
        for yy in range(photo.height):
            for xx in range(photo.width):
                t = px[xx, yy] / 255
                dp[xx, yy] = tuple(int(NAVY_DARK[k] + (255 - NAVY_DARK[k]) * t * 0.65)
                                   for k in range(3))
        img.paste(duo, (0, 0))
        scrim = Image.new("RGBA", (W, H - FOOTER_H), (*NAVY_DARK, 120))
        img = Image.alpha_composite(img.convert("RGBA"),
                                    Image.new("RGBA", (W, H), (0, 0, 0, 0)))
        img.paste(Image.alpha_composite(Image.new("RGBA", scrim.size, (0, 0, 0, 0)), scrim),
                  (0, 0), scrim)
        img = img.convert("RGB")
        d = ImageDraw.Draw(img)
    _kicker(d, kicker, accent)
    hfont, lines, line_h = _fit_headline(d, headline, W - 2 * MARGIN, 320, start=80)
    y = H - FOOTER_H - 60 - len(lines) * line_h
    for ln in lines:
        d.text((MARGIN, y), ln, font=hfont, fill=WHITE)
        y += line_h
    return img, d


_CARD_BUILDERS = {
    "bold_type": _card_bold,
    "stat": _card_stat,
    "illustrative": _card_illustrative,
    "quote": _card_quote,
    "photo": _card_photo,
}


def make_card(headline, kicker, cta, out_path, accent=GOLD, style="bold_type",
              photo_path=None):
    """Render a 1080x1080 brand card in one of several visual styles.

    style: bold_type | stat | illustrative | quote | photo  (default preserves
    the legacy look, so existing callers are unaffected). Brand DNA (navy, gold
    accent, logo + contact footer) is constant across every style.
    """
    builder = _CARD_BUILDERS.get(style, _card_bold)
    if style == "photo":
        img, d = builder(headline, kicker, cta, accent, photo_path=photo_path)
    else:
        img, d = builder(headline, kicker, cta, accent)
    _brand_footer(img, d, accent)
    img.save(out_path, "PNG")
    return out_path


if __name__ == "__main__":
    headline = sys.argv[1] if len(sys.argv) > 1 else \
        "Is your LA business ready for a ransomware attack?"
    kicker = sys.argv[2] if len(sys.argv) > 2 else "Cybersecurity Alert"
    cta = sys.argv[3] if len(sys.argv) > 3 else "Book a free 30-min assessment"
    out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(HERE, "_card_preview.png")
    print(make_card(headline, kicker, cta, out))
