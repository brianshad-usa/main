"""
carousel_graphic.py
-------------------
Renders the ProLink editorial carousel system: 1080x1350 (4:5) slides that read
as editorial design, not social clip-art.

Design language (deliberately distinct from the legacy single card):
  * type-led - a display headline does the work; no icons, no padlocks, no shields
  * the GROUND CHANGES ACROSS THE SWIPE - a navy hook, cream/ink body slides, and
    a gold call-to-action - so the whole carousel differs slide-to-slide AND
    post-to-post, not just on the cover (this was the samey-feed gap)
  * generous margins, hard left rail, oversized slide numerals
  * thin gold rule as the only ornament
  * the wordmark small and low - the system is recognizable before the logo is

Brand DNA is constant on every slide: navy + gold present, the wordmark + URL,
the calm peer-to-executive voice, verified facts only.

Same dependency contract as social_graphic.py: pure Pillow + the bundled Inter
variable font, so local Windows and CI Linux render identically.

Slide spec (from content_studio.py):
    {"role": "hook|content|takeaway|cta", "kicker": "...", "headline": "...",
     "body": "...", "footer": "..."}
"""

import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

# ── Palette (matched to social_graphic.py so cards + carousels share DNA) ──
INK        = (23, 33, 45)
NAVY_INK   = (17, 38, 62)
PAPER      = (245, 241, 232)    # warm off-white ground  (#f5f1e8)
PAPER_DIM  = (110, 116, 124)
PAPER_RULE = (219, 210, 193)
NAVY_DEEP  = (13, 59, 102)      # brand navy anchor
NAVY_BLACK = (6, 18, 30)
NAVY_TEXT  = (214, 222, 232)
GOLD       = (247, 148, 29)     # brand gold accent
GOLD_WARM  = (245, 166, 35)

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
_VARIATION = {"black": "Black", "extrabold": "ExtraBold", "bold": "Bold",
              "semi": "SemiBold", "med": "Medium", "reg": "Regular", "light": "Light"}


def _font(role, size):
    if os.path.exists(INTER_VAR):
        try:
            f = ImageFont.truetype(INTER_VAR, size)
            f.set_variation_by_name(_VARIATION.get(role, "Regular"))
            return f
        except Exception:
            pass
    paths = _BOLD_FALLBACKS if role in ("black", "extrabold", "bold", "semi") else _FALLBACKS
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _gradient(d, x0, y0, x1, y1, c1, c2):
    h = y1 - y0
    for i in range(h):
        t = i / max(h - 1, 1)
        col = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
        d.line([(x0, y0 + i), (x1, y0 + i)], fill=col)


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


# ── Ground palettes: each slide sits on one of three grounds ─────────────
def _ground_colors(ground):
    if ground == "cream":
        return {"ink": NAVY_INK, "body": (55, 62, 70), "dim": PAPER_DIM,
                "kick": GOLD, "accent": GOLD, "ghost": (231, 224, 210),
                "dot_off": PAPER_RULE}
    if ground == "gold":
        return {"ink": NAVY_DEEP, "body": NAVY_INK, "dim": NAVY_INK,
                "kick": NAVY_DEEP, "accent": NAVY_DEEP, "ghost": (232, 150, 60),
                "dot_off": (255, 255, 255)}
    # navy
    return {"ink": (236, 240, 245), "body": (206, 216, 228), "dim": (150, 162, 176),
            "kick": GOLD, "accent": GOLD, "ghost": (24, 52, 82),
            "dot_off": (40, 62, 86)}


def _paint_ground(img, d, ground):
    if ground == "cream":
        d.rectangle([0, 0, W, H], fill=PAPER)
    elif ground == "gold":
        _gradient(d, 0, 0, W, H, GOLD_WARM, GOLD)
        d.polygon([(W, H), (W, H - 300), (W - 300, H)], fill=NAVY_DEEP)
    else:
        _gradient(d, 0, 0, W, H, NAVY_BLACK, NAVY_DEEP)


def _chrome(d, img, idx, total, ground):
    """Shared slide furniture: gold rule, ghosted numeral, wordmark, progress."""
    c = _ground_colors(ground)
    if total > 1:
        nfont = _font("black", 168)
        label = f"{idx:02d}"
        d.text((W - MARGIN - d.textlength(label, font=nfont), 44),
               label, font=nfont, fill=c["ghost"])
    d.rectangle([MARGIN, 118, MARGIN + 64, 122], fill=c["accent"])
    wfont = _font("semi", 26)
    _tracked(d, (MARGIN, H - 92), "PRO LINK SYSTEMS", wfont, c["ink"], 4.0)
    d.text((MARGIN, H - 54), "prolinksystems.com", font=_font("reg", 22), fill=c["dim"])
    if total > 1:
        r, gap = 5, 18
        x0 = W - MARGIN - (total - 1) * gap - 2 * r
        for i in range(total):
            cx = x0 + i * gap
            fill = c["accent"] if (i + 1) == idx else c["dot_off"]
            d.ellipse([cx - r, H - 76 - r, cx + r, H - 76 + r], fill=fill)


def _cover_motif(d, img, variant, ground):
    """A restrained motif on the hook slide so consecutive carousels differ at a
    glance. Returns the y-offset the body text should start at, so an oversized
    ornament never collides with the kicker/headline (the old quote-overlap bug)."""
    if variant == "arc":
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        cx, cy = W + 40, -40
        for i, r in enumerate(range(220, 1100, 140)):
            col = (*GOLD, 46) if i % 3 == 0 else (34, 56, 82, 80)
            od.arc([cx - r, cy - r, cx + r, cy + r], start=95, end=205, fill=col, width=7)
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"), (0, 0))
        return 0
    if variant == "quote":
        # Oversized quotation ornament at the top; push the text well below it so
        # the kicker and headline never sit under the glyph.
        d.text((MARGIN - 10, 54), "\u201c", font=_font("black", 300), fill=GOLD)
        return 250
    if variant == "stat":
        d.rectangle([MARGIN, 176, MARGIN + 220, 184], fill=GOLD)
        return 40
    if variant == "gold":
        # gold-accent corner flag on the navy hook (pairs with the bright_accent card)
        d.polygon([(W, 0), (W, 240), (W - 240, 0)], fill=GOLD)
        return 0
    return 0  # "bold" / "photo": type-led cover, no ornament offset


# ── Ground assignment across the swipe ───────────────────────────────────
def _assign_grounds(slides):
    """Give the swipe a changing ground: navy hook, cream/navy body slides, a
    gold call-to-action. No two adjacent slides share a ground."""
    grounds = []
    for i, spec in enumerate(slides):
        role = (spec.get("role") or "content").lower()
        if role == "hook":
            g = "navy"
        elif role == "cta":
            g = "gold"
        elif role == "takeaway":
            g = "navy"
        else:  # content: alternate paper and navy for rhythm
            g = "cream" if (i % 2 == 1) else "navy"
        if grounds and g == grounds[-1]:
            g = next(o for o in ("cream", "navy", "gold") if o != grounds[-1])
        grounds.append(g)
    # Guarantee the final slide reads as the CTA ground when it is the CTA.
    if slides and (slides[-1].get("role") or "").lower() == "cta":
        grounds[-1] = "gold" if (len(grounds) < 2 or grounds[-2] != "gold") else "navy"
    return grounds


def render_slide(spec, idx, total, out_path, variant="bold", ground=None):
    role = (spec.get("role") or "content").lower()
    if ground is None:
        ground = {"hook": "navy", "cta": "gold", "takeaway": "navy"}.get(role, "cream")
    c = _ground_colors(ground)

    img = Image.new("RGB", (W, H), PAPER if ground == "cream" else NAVY_DEEP)
    d = ImageDraw.Draw(img)
    _paint_ground(img, d, ground)
    d = ImageDraw.Draw(img)

    motif_offset = 0
    if role == "hook" and variant:
        motif_offset = _cover_motif(d, img, variant, ground)
        d = ImageDraw.Draw(img)
    _chrome(d, img, idx, total, ground)

    y = 208 + motif_offset

    kicker = (spec.get("kicker") or "").strip()
    if kicker:
        _tracked(d, (MARGIN, y), kicker.upper(), _font("semi", 27), c["kick"], 3.5)
        y += 76

    headline = (spec.get("headline") or "").strip()
    body = (spec.get("body") or "").strip()

    if headline:
        start = 118 if (role == "hook" and not body) else 84
        # Budget the headline against the remaining height so a lowered start
        # (e.g. the quote cover) can never overflow past the footer.
        h_budget = (H - 210 - y) if not body else min(400, H - 360 - y)
        hfont, lines, line_h = _fit(d, headline, "bold", W - 2 * MARGIN,
                                    max(h_budget, 140), start, 44, leading=1.08)
        for ln in lines:
            d.text((MARGIN, y), ln, font=hfont, fill=c["ink"])
            y += line_h
        y += 44

    if body:
        d.rectangle([MARGIN, y - 10, MARGIN + 40, y - 7], fill=c["accent"])
        y += 26
        bfont, blines, bline_h = _fit(d, body, "reg", W - 2 * MARGIN,
                                      H - 190 - y, 40, 28, leading=1.38)
        for ln in blines:
            d.text((MARGIN, y), ln, font=bfont, fill=c["body"])
            y += bline_h

    footer = (spec.get("footer") or "").strip()
    if footer:
        ffont = _font("med", 28)
        flines = _wrap(d, footer, ffont, W - 2 * MARGIN)
        fy = H - 170 - len(flines) * 40
        for ln in flines:
            d.text((MARGIN, fy), ln, font=ffont, fill=c["dim"])
            fy += 40

    img.save(out_path, "PNG")
    return out_path


def render_carousel(slides, out_dir, stem, variant="bold"):
    """Render every slide; return list of (png_path, jpg_path).

    The ground changes across the swipe (navy hook -> cream/navy body -> gold
    CTA), and `variant` restyles the hook cover (bold|arc|quote|stat|gold|photo)
    so consecutive carousels don't open the same way either."""
    os.makedirs(out_dir, exist_ok=True)
    outputs = []
    total = len(slides)
    grounds = _assign_grounds(slides)
    for i, spec in enumerate(slides, start=1):
        png = os.path.join(out_dir, f"{stem}-{i:02d}.png")
        render_slide(spec, i, total, png, variant=variant, ground=grounds[i - 1])
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
    outs = render_carousel(demo, os.path.join(HERE, "scratch"), "_carousel_preview", variant="arc")
    for png, jpg in outs:
        print(png)
