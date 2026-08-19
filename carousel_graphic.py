"""
carousel_graphic.py
-------------------
Renders the ProLink editorial carousel system: 1080x1350 (4:5) slides that
read as editorial design, not social clip-art.

Design language (deliberately distinct from the legacy social_graphic.py card):
  * type-led - a serif-weight display headline does the work; no icons,
    no padlocks, no shields, no imagery cliches
  * paper/ink slides alternating with navy accent slides for rhythm
  * generous margins, hard left rail, oversized slide numerals
  * thin gold rule as the only ornament
  * the wordmark small and low - the system should be recognizable
    before the logo is

Same dependency contract as social_graphic.py: pure Pillow + the bundled
Inter variable font, so local Windows and CI Linux render identically.

Slide spec (from content_studio.py):
    {"kicker": "...", "headline": "...", "body": "...", "footer": "..."}
role: "hook" | "content" | "takeaway" | "cta"
"""

import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

# ── Palette ──────────────────────────────────────────────────────
INK        = (17, 24, 32)       # near-black text on paper
PAPER      = (247, 245, 240)    # warm off-white ground
PAPER_DIM  = (110, 116, 124)    # secondary text on paper
NAVY_DEEP  = (7, 22, 38)        # accent-slide ground
NAVY_TEXT  = (214, 222, 232)    # body text on navy
GOLD       = (197, 152, 62)     # restrained brass, not bright gold
RULE_PAPER = (210, 205, 196)

W, H = 1080, 1350
MARGIN = 96

INTER_VAR = os.environ.get("INTER_FONT", os.path.join(HERE, "assets", "fonts", "Inter.ttf"))
_WIN = r"C:\Windows\Fonts"
_FALLBACKS = [
    os.path.join(_WIN, "segoeui.ttf"),
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
_BOLD_FALLBACKS = [
    os.path.join(_WIN, "segoeuib.ttf"),
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
_VARIATION = {"black": "Black", "bold": "Bold", "semi": "SemiBold",
              "med": "Medium", "reg": "Regular", "light": "Light"}


def _font(role, size):
    if os.path.exists(INTER_VAR):
        try:
            f = ImageFont.truetype(INTER_VAR, size)
            f.set_variation_by_name(_VARIATION.get(role, "Regular"))
            return f
        except Exception:
            pass
    paths = _BOLD_FALLBACKS if role in ("black", "bold", "semi") else _FALLBACKS
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


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


def _fit(draw, text, role, max_w, max_h, start, floor, leading=1.12):
    size = start
    while size >= floor:
        font = _font(role, size)
        lines = _wrap(draw, text, font, max_w)
        line_h = int(size * leading) + 6
        if len(lines) * line_h <= max_h:
            return font, lines, line_h
        size -= 4
    return font, lines, line_h


def _tracked(draw, xy, text, font, fill, tracking=3.0):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def _chrome(d, img, idx, total, dark):
    """Shared slide furniture: kicker rail, numeral, wordmark, progress."""
    ink = NAVY_TEXT if dark else INK
    dim = (150, 160, 172) if dark else PAPER_DIM

    # Oversized slide numeral, top-right, ghosted
    if total > 1:
        nfont = _font("black", 168)
        label = f"{idx:02d}"
        ghost = (26, 46, 68) if dark else (231, 227, 219)
        d.text((W - MARGIN - d.textlength(label, font=nfont), 44),
               label, font=nfont, fill=ghost)

    # Gold rule, top-left
    d.rectangle([MARGIN, 118, MARGIN + 64, 122], fill=GOLD)

    # Footer: wordmark left, progress dots right
    wfont = _font("semi", 26)
    _tracked(d, (MARGIN, H - 92), "PRO LINK SYSTEMS", wfont, ink, 4.0)
    d.text((MARGIN, H - 54), "prolinksystems.com", font=_font("reg", 22), fill=dim)
    if total > 1:
        r, gap = 5, 18
        x0 = W - MARGIN - (total - 1) * gap - 2 * r
        for i in range(total):
            cx = x0 + i * gap
            fill = GOLD if (i + 1) == idx else ((40, 62, 86) if dark else RULE_PAPER)
            d.ellipse([cx - r, H - 76 - r, cx + r, H - 76 + r], fill=fill)


def _cover_motif(d, img, variant):
    """A restrained motif on the hook slide so consecutive carousels differ at a
    glance. Brand DNA constant: navy ground, gold as the only accent."""
    if variant == "arc":
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        cx, cy = W + 40, -40
        for i, r in enumerate(range(220, 1100, 140)):
            col = (*GOLD, 46) if i % 3 == 0 else (34, 56, 82, 80)
            od.arc([cx - r, cy - r, cx + r, cy + r], start=95, end=205, fill=col, width=7)
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"), (0, 0))
    elif variant == "quote":
        d.text((MARGIN - 10, 60), "“", font=_font("black", 300), fill=GOLD)
    elif variant == "stat":
        d.rectangle([MARGIN, 176, MARGIN + 220, 184], fill=GOLD)
    # "bold" and "photo" leave the type-led cover as-is.


def render_slide(spec, idx, total, out_path, variant="bold"):
    role = spec.get("role", "content")
    dark = role in ("hook", "cta")
    bg = NAVY_DEEP if dark else PAPER
    ink = (236, 240, 245) if dark else INK
    body_ink = NAVY_TEXT if dark else (55, 62, 70)
    dim = (150, 160, 172) if dark else PAPER_DIM

    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    if role == "hook" and variant:
        _cover_motif(d, img, variant)
        d = ImageDraw.Draw(img)
    _chrome(d, img, idx, total, dark)

    y = 208

    kicker = (spec.get("kicker") or "").strip()
    if kicker:
        _tracked(d, (MARGIN, y), kicker.upper(), _font("semi", 27), GOLD, 3.5)
        y += 76

    headline = (spec.get("headline") or "").strip()
    body = (spec.get("body") or "").strip()

    if headline:
        # Hook slides carry almost nothing else, so the type gets enormous.
        start = 118 if (role == "hook" and not body) else 84
        h_budget = 620 if not body else 400
        hfont, lines, line_h = _fit(d, headline, "bold", W - 2 * MARGIN,
                                    h_budget, start, 44, leading=1.08)
        for ln in lines:
            d.text((MARGIN, y), ln, font=hfont, fill=ink)
            y += line_h
        y += 44

    if body:
        # Divider between headline and body
        d.rectangle([MARGIN, y - 10, MARGIN + 40, y - 7], fill=GOLD)
        y += 26
        bfont, blines, bline_h = _fit(d, body, "reg", W - 2 * MARGIN,
                                      H - 190 - y, 40, 28, leading=1.38)
        for ln in blines:
            d.text((MARGIN, y), ln, font=bfont, fill=body_ink)
            y += bline_h

    footer = (spec.get("footer") or "").strip()
    if footer:
        ffont = _font("med", 28)
        flines = _wrap(d, footer, ffont, W - 2 * MARGIN)
        fy = H - 170 - len(flines) * 40
        for ln in flines:
            d.text((MARGIN, fy), ln, font=ffont, fill=dim)
            fy += 40

    img.save(out_path, "PNG")
    return out_path


def render_carousel(slides, out_dir, stem, variant="bold"):
    """Render every slide; return list of (png_path, jpg_path).

    variant restyles the hook/cover slide (bold|arc|quote|stat|photo) so
    consecutive carousels don't open the same way. Body slides are unchanged."""
    os.makedirs(out_dir, exist_ok=True)
    outputs = []
    total = len(slides)
    for i, spec in enumerate(slides, start=1):
        png = os.path.join(out_dir, f"{stem}-{i:02d}.png")
        render_slide(spec, i, total, png, variant=variant)
        jpg = png[:-4] + ".jpg"
        Image.open(png).convert("RGB").save(jpg, "JPEG", quality=92)
        outputs.append((png, jpg))
    return outputs


if __name__ == "__main__":
    demo = [
        {"role": "hook", "kicker": "Shadow AI",
         "headline": "The AI your company didn't buy is already at work."},
        {"role": "content", "kicker": "The problem",
         "headline": "Nobody approved it. Everybody's using it.",
         "body": "Employees adopt AI tools the way they once adopted spreadsheets: quietly, because the tools work. Procurement finds out at renewal time. Security finds out later than that."},
        {"role": "content", "kicker": "Why it matters",
         "headline": "Every paste is a data decision.",
         "body": "A prompt window feels like a scratchpad. It is a transmission to a third party, governed by terms nobody in the building has read."},
        {"role": "takeaway", "kicker": "The takeaway",
         "headline": "You can't govern what you haven't listed.",
         "body": "Start with an inventory, not a policy. The policy will be wrong until you know what people actually use."},
        {"role": "cta", "kicker": "Pro Link Systems",
         "headline": "We help LA businesses put AI to work without losing control of their data.",
         "footer": "Since 1999 - Woodland Hills, Los Angeles"},
    ]
    outs = render_carousel(demo, os.path.join(HERE, "social"), "_carousel_preview")
    for png, jpg in outs:
        print(png)
