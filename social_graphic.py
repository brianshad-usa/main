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


def make_card(headline, kicker, cta, out_path, accent=GOLD):
    img = Image.new("RGB", (W, H), NAVY_DARK)
    d = ImageDraw.Draw(img)

    _gradient(d, 0, 0, W, H - FOOTER_H, NAVY_DARK, NAVY)

    # Soft accent glow, top-right
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W - 420, -260, W + 220, 380], fill=(*NAVY_MID, 90))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)

    # Kicker (accent, uppercase, tracked) with leading dot
    kfont = _font("semi", 30)
    d.ellipse([MARGIN, 104, MARGIN + 16, 120], fill=accent)
    _tracked(d, (MARGIN + 30, 100), kicker.upper(), kfont, accent, 2.5)

    # Accent divider
    d.rectangle([MARGIN, 156, MARGIN + 76, 162], fill=accent)

    # Headline (white, auto-fit, wrapped)
    hfont, lines, line_h = _fit_headline(d, headline, W - 2 * MARGIN, 470)
    y = 212
    for ln in lines:
        d.text((MARGIN, y), ln, font=hfont, fill=WHITE)
        y += line_h

    # CTA pill (gold, navy text)
    cfont = _font("semi", 33)
    pad_x, pad_y = 34, 20
    tw = d.textlength(cta, font=cfont)
    asc, desc = cfont.getmetrics()
    pill_h = asc + desc + pad_y * 2
    pill_y = H - FOOTER_H - 56 - pill_h
    d.rounded_rectangle([MARGIN, pill_y, MARGIN + tw + pad_x * 2, pill_y + pill_h],
                        radius=pill_h // 2, fill=GOLD)
    d.text((MARGIN + pad_x, pill_y + pad_y - 2), cta, font=cfont, fill=NAVY)

    # White footer strip with accent top border
    d.rectangle([0, H - FOOTER_H, W, H], fill=WHITE)
    d.rectangle([0, H - FOOTER_H, W, H - FOOTER_H + 5], fill=accent)

    # Real logo (left, vertically centered)
    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGBA")
        target_h = 86
        target_w = int(logo.width * (target_h / logo.height))
        logo = logo.resize((target_w, target_h), Image.LANCZOS)
        ly = H - FOOTER_H + (FOOTER_H - target_h) // 2
        img.paste(logo, (MARGIN, ly), logo)

    # Contact, right-aligned
    site_font = _font("semi", 32)
    tel_font = _font("reg", 28)
    right = W - MARGIN
    fy = H - FOOTER_H + 56
    d.text((right - d.textlength("prolinksystems.com", font=site_font), fy),
           "prolinksystems.com", font=site_font, fill=NAVY)
    d.text((right - d.textlength("1-800-890-6133", font=tel_font), fy + 44),
           "1-800-890-6133", font=tel_font, fill=MUTED)

    img.save(out_path, "PNG")
    return out_path


if __name__ == "__main__":
    headline = sys.argv[1] if len(sys.argv) > 1 else \
        "Is your LA business ready for a ransomware attack?"
    kicker = sys.argv[2] if len(sys.argv) > 2 else "Cybersecurity Alert"
    cta = sys.argv[3] if len(sys.argv) > 3 else "Book a free 30-min assessment"
    out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(HERE, "_card_preview.png")
    print(make_card(headline, kicker, cta, out))
