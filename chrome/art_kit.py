#!/usr/bin/env python3
"""
chrome/art_kit.py -- the drawing vocabulary for Insights illustrations (redesign-2026, iteration 4).

One corporate line-art language: navy ground, white linework in four weights, ONE amber focal element per scene.
Everything is original vector geometry; there is no text inside an illustration. Scenes live in chrome/art_scenes/
and compose these parts into a subject-specific schematic (see the README docstring of chrome/art_scenes).

Canvas: 1200 x 675. Keep meaning inside x 120-1080, y 80-595 (cards crop the sides slightly).
Coordinates are top-left (x, y, w, h) for framed parts and centre (cx, cy) for round parts.
Every function returns an SVG string. Tones: "hi" "mid" "lo" "faint" "amber" (or any colour).
"""
import math

W, H = 1200, 675
BG = "#0b1a2b"
AMBER = "#e39a3d"
AMBER_WASH = "rgba(227,154,61,.12)"
PANEL = "rgba(255,255,255,.035)"
PANEL2 = "rgba(255,255,255,.07)"
TONES = {"hi": "rgba(255,255,255,.9)", "mid": "rgba(255,255,255,.56)", "lo": "rgba(255,255,255,.3)",
         "faint": "rgba(255,255,255,.14)", "amber": AMBER, "bg": BG}


def n(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def tone(t):
    return TONES.get(t, t)


# ---- basic marks ----------------------------------------------------------------------------------------------

def path(d, t="hi", w=1.6, fill="none", dash=None):
    return '<path d="%s" stroke="%s" stroke-width="%s" fill="%s"%s stroke-linecap="round" stroke-linejoin="round"/>' % (
        d, tone(t), n(w), fill if fill != "bg" else BG, ' stroke-dasharray="%s"' % dash if dash else "")


def line(x1, y1, x2, y2, t="hi", w=1.6, dash=None):
    return path("M%s %sL%s %s" % (n(x1), n(y1), n(x2), n(y2)), t, w, "none", dash)


def poly(pts, t="hi", w=1.6, fill="none", dash=None, close=False):
    return path("M" + "L".join("%s %s" % (n(a), n(b)) for a, b in pts) + ("Z" if close else ""), t, w, fill, dash)


def rect(x, y, w, h, t="hi", sw=1.6, fill="none", dash=None, r=2):
    return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" stroke="%s" stroke-width="%s" fill="%s"%s/>' % (
        n(x), n(y), n(w), n(h), n(r), tone(t), n(sw), fill if fill != "bg" else BG,
        ' stroke-dasharray="%s"' % dash if dash else "")


def solid(x, y, w, h, t="amber", r=0):
    return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"/>' % (n(x), n(y), n(w), n(h), n(r), tone(t))


def circ(cx, cy, r, t="hi", w=1.6, fill="none", dash=None):
    return '<circle cx="%s" cy="%s" r="%s" stroke="%s" stroke-width="%s" fill="%s"%s/>' % (
        n(cx), n(cy), n(r), tone(t), n(w), fill if fill != "bg" else BG,
        ' stroke-dasharray="%s"' % dash if dash else "")


def dot(cx, cy, r=5, t="hi"):
    return '<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (n(cx), n(cy), n(r), tone(t))


def node(cx, cy, kind="hollow", r=7):
    """Network node: hollow (white ring on navy), hi (filled white), amber (filled amber)."""
    if kind == "hollow":
        return circ(cx, cy, r, "hi", 1.6, "bg")
    if kind == "amber":
        return dot(cx, cy, r, "amber")
    return dot(cx, cy, r, "hi")


def ticks(x, y, w, h, t="lo", s=14):
    """Engineering-drawing corner ticks around a box."""
    return "".join(path(d, t, 1.2) for d in (
        "M%s %sh%sM%s %sv%s" % (n(x), n(y), n(s), n(x), n(y), n(s)),
        "M%s %sh-%sM%s %sv%s" % (n(x + w), n(y), n(s), n(x + w), n(y), n(s)),
        "M%s %sh%sM%s %sv-%s" % (n(x), n(y + h), n(s), n(x), n(y + h), n(s)),
        "M%s %sh-%sM%s %sv-%s" % (n(x + w), n(y + h), n(s), n(x + w), n(y + h), n(s))))


def dim(x1, y1, x2, y2, t="lo"):
    """Dimension line with end ticks."""
    a = math.atan2(y2 - y1, x2 - x1) + math.pi / 2
    dx, dy = 7 * math.cos(a), 7 * math.sin(a)
    return line(x1, y1, x2, y2, t, 1.2) + line(x1 - dx, y1 - dy, x1 + dx, y1 + dy, t, 1.2) + line(x2 - dx, y2 - dy, x2 + dx, y2 + dy, t, 1.2)


def arrow(x1, y1, x2, y2, t="hi", w=1.8, dash=None, head=11):
    a = math.atan2(y2 - y1, x2 - x1)
    h1 = (x2 - head * math.cos(a - .45), y2 - head * math.sin(a - .45))
    h2 = (x2 - head * math.cos(a + .45), y2 - head * math.sin(a + .45))
    return line(x1, y1, x2, y2, t, w, dash) + poly([h1, (x2, y2), h2], t, w)


def curve(x1, y1, c1x, c1y, c2x, c2y, x2, y2, t="hi", w=1.8, dash=None, head=0):
    d = "M%s %sC%s %s %s %s %s %s" % tuple(n(v) for v in (x1, y1, c1x, c1y, c2x, c2y, x2, y2))
    s = path(d, t, w, "none", dash)
    if head:
        a = math.atan2(y2 - c2y, x2 - c2x)
        s += poly([(x2 - head * math.cos(a - .45), y2 - head * math.sin(a - .45)), (x2, y2),
                   (x2 - head * math.cos(a + .45), y2 - head * math.sin(a + .45))], t, w)
    return s


def link(a, b, t="lo", w=1.2, dash=None):
    return line(a[0], a[1], b[0], b[1], t, w, dash)


def mesh(points, maxd, t="lo", w=1.1):
    """Connect every pair of points closer than maxd."""
    out = []
    for i, p in enumerate(points):
        for q in points[i + 1:]:
            if math.hypot(p[0] - q[0], p[1] - q[1]) < maxd:
                out.append(link(p, q, t, w))
    return "".join(out)


# ---- documents, screens, data ---------------------------------------------------------------------------------

_LEN = (.92, .74, .88, .56, .8, .64, .9, .7)


def doc(x, y, w, h, lines=6, hl=None, t="hi", fold=.18, sw=1.8):
    """A page with a folded corner and text rules. hl = index of an amber rule."""
    c = w * fold
    s = path("M%s %sH%sL%s %sV%sH%sZ" % (n(x), n(y), n(x + w - c), n(x + w), n(y + c), n(y + h), n(x)), t, sw, "bg")
    s += path("M%s %sV%sH%s" % (n(x + w - c), n(y), n(y + c), n(x + w)), t, 1.3)
    m = w * .13
    top = y + h * .22
    gap = (h * .68) / max(1, lines - 1) if lines > 1 else 0
    for i in range(lines):
        L = (w - 2 * m) * _LEN[i % len(_LEN)]
        hot = hl is not None and i == hl
        s += line(x + m, top + i * gap, x + m + L, top + i * gap, "amber" if hot else "lo", 3 if hot else 2.4)
    return s


def check_mark(x, y, s=8, t="hi", w=2.2):
    return path("M%s %sl%s %sl%s %s" % (n(x), n(y), n(s * .4), n(s * .5), n(s * .75), n(-s * 1.0)), t, w)


def cross_mark(cx, cy, s=7, t="amber", w=2.2):
    return line(cx - s, cy - s, cx + s, cy + s, t, w) + line(cx - s, cy + s, cx + s, cy - s, t, w)


def table(x, y, w, h, cols, rows, hl_row=None, hl_cell=None, t="hi", head=True):
    """A ruled ledger. hl_row = amber wash row; hl_cell = (row, col) amber outline."""
    ch = h / rows
    cw = w / cols
    s = rect(x, y, w, h, t, 1.7, "bg")
    for i in range(1, rows):
        s += line(x, y + i * ch, x + w, y + i * ch, "lo" if not (head and i == 1) else "mid", 1.2 if not (head and i == 1) else 1.7)
    for j in range(1, cols):
        s += line(x + j * cw, y, x + j * cw, y + h, "faint", 1.2)
    for i in range(rows):
        for j in range(cols):
            L = cw * (.62 if (i + j) % 3 else .42)
            s += line(x + j * cw + cw * .16, y + i * ch + ch * .5, x + j * cw + cw * .16 + L, y + i * ch + ch * .5,
                      "mid" if (head and i == 0) else "lo", 2.6 if (head and i == 0) else 2)
    if hl_row is not None:
        s += solid(x, y + hl_row * ch, w, ch, AMBER_WASH)
        s += line(x, y + hl_row * ch, x, y + (hl_row + 1) * ch, "amber", 4)
    if hl_cell is not None:
        s += rect(x + hl_cell[1] * cw, y + hl_cell[0] * ch, cw, ch, "amber", 2.4)
    return s


def window(x, y, w, h, t="hi", sw=1.8, bar=.14):
    """A browser or app frame with a title bar."""
    b = h * bar
    s = rect(x, y, w, h, t, sw, "bg", r=4)
    s += line(x, y + b, x + w, y + b, "mid", 1.3)
    for i in range(3):
        s += circ(x + b * .55 + i * b * .42, y + b * .5, b * .12, "mid", 1.2)
    return s


def rows_of_text(x, y, w, count, gap, t="lo", w_stroke=2.4, seed=0):
    return "".join(line(x, y + i * gap, x + w * _LEN[(i + seed) % len(_LEN)], y + i * gap, t, w_stroke) for i in range(count))


def terminal(x, y, w, h, t="hi", lines=5):
    return window(x, y, w, h, t) + "".join(
        line(x + w * .1, y + h * .3 + i * h * .12, x + w * .1 + w * (.5 + .28 * ((i * 7) % 3) / 2), y + h * .3 + i * h * .12,
             "amber" if i == 1 else "lo", 2.4) for i in range(lines))


def server(x, y, w, h, units=3, t="hi", hot=None):
    s = rect(x, y, w, h, t, 1.8, "bg", r=3)
    uh = h / units
    for i in range(units):
        if i:
            s += line(x, y + i * uh, x + w, y + i * uh, "mid", 1.2)
        lit = hot is not None and i == hot
        s += dot(x + w * .88, y + (i + .5) * uh, 3.5, "amber" if lit else "mid")
        s += line(x + w * .12, y + (i + .5) * uh, x + w * .55, y + (i + .5) * uh, "amber" if lit else "lo", 2.4)
    return s


def cylinder(x, y, w, h, bands=3, t="hi", hot=None):
    ry = w * .16
    s = path("M%s %sV%sA%s %s 0 0 0 %s %sV%s" % (n(x), n(y + ry), n(y + h - ry), n(w / 2), n(ry), n(x + w), n(y + h - ry), n(y + ry)), t, 1.8)
    s += '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" stroke="%s" stroke-width="1.8" fill="%s"/>' % (n(x + w / 2), n(y + ry), n(w / 2), n(ry), tone(t), BG)
    for i in range(1, bands):
        yy = y + ry + (h - 2 * ry) * i / bands
        c = "amber" if hot is not None and i == hot else "lo"
        s += path("M%s %sA%s %s 0 0 0 %s %s" % (n(x), n(yy), n(w / 2), n(ry), n(x + w), n(yy)), c, 1.5 if c == "lo" else 2.4)
    return s


def cloud(cx, cy, s, t="hi", w=1.8, fill="none"):
    k = s / 100.0
    P = lambda *a: " ".join(n(v * k) for v in a)
    d = ("M%s %s" % (n(cx - 78 * k), n(cy + 34 * k))
         + "a%s 0 0 1 %s" % (P(40, 40), P(12, -76))
         + "a%s 0 0 1 %s" % (P(62, 62), P(116, -18))
         + "a%s 0 0 1 %s" % (P(48, 48), P(28, 94)) + "z")
    return path(d, t, w, fill)


# ---- security, identity, access --------------------------------------------------------------------------------

def shield(cx, cy, s, t="hi", w=2, check=False, fill="none"):
    k = s / 100.0
    d = "M%s %sL%s %sV%sC%s %s %s %s %s %sC%s %s %s %s %s %sV%sZ" % tuple(n(v) for v in (
        cx, cy - 62 * k, cx + 48 * k, cy - 44 * k, cy - 4 * k, cx + 48 * k, cy + 34 * k, cx + 22 * k, cy + 56 * k, cx, cy + 68 * k,
        cx - 22 * k, cy + 56 * k, cx - 48 * k, cy + 34 * k, cx - 48 * k, cy - 4 * k, cy - 44 * k))
    d = d.replace("V%s" % n(cy - 44 * k), "V%s" % n(cy - 44 * k))
    s_ = path(d, t, w, fill)
    if check:
        s_ += path("M%s %sl%s %sl%s %s" % (n(cx - 20 * k), n(cy + 2 * k), n(14 * k), n(16 * k), n(28 * k), n(-34 * k)), "amber", 2.8)
    return s_


def lock(cx, cy, s, t="hi", open_=False, hot=True, w=2):
    k = s / 100.0
    s_ = rect(cx - 36 * k, cy - 6 * k, 72 * k, 60 * k, t, w, "bg", r=4)
    sh = "M%s %sV%sa%s %s 0 0 1 %s 0V%s" if not open_ else "M%s %sV%sa%s %s 0 0 1 %s 0v%s"
    s_ += path(sh % (n(cx - 22 * k), n(cy - 6 * k), n(cy - 26 * k), n(22 * k), n(22 * k), n(44 * k),
                     n(cy - 6 * k) if not open_ else n(8 * k)), t, w)
    s_ += circ(cx, cy + 18 * k, 8 * k, "amber" if hot else t, 2) + line(cx, cy + 24 * k, cx, cy + 40 * k, "amber" if hot else t, 2.4)
    return s_


def key(cx, cy, s, t="amber", w=2.4, ang=0):
    k = s / 100.0
    c, si = math.cos(math.radians(ang)), math.sin(math.radians(ang))

    def R(x, y):
        return cx + (x * c - y * si) * k, cy + (x * si + y * c) * k
    s_ = '<circle cx="%s" cy="%s" r="%s" stroke="%s" stroke-width="%s" fill="none"/>' % (*[n(v) for v in R(-40, 0)], n(22 * k), tone(t), n(w))
    pts = [R(-18, 0), R(60, 0)]
    s_ += line(*pts[0], *pts[1], t, w)
    for dx in (34, 50):
        a, b = R(dx, 0), R(dx, 16)
        s_ += line(*a, *b, t, w)
    return s_


def badge(x, y, w, h, t="hi"):
    """An identity card: portrait, two lines."""
    return (rect(x, y, w, h, t, 1.8, "bg", r=6) + circ(x + w * .25, y + h * .38, h * .13, "hi", 1.6)
            + path("M%s %sa%s %s 0 0 1 %s 0" % (n(x + w * .25 - h * .2), n(y + h * .74), n(h * .2), n(h * .24), n(h * .4)), "hi", 1.6)
            + line(x + w * .5, y + h * .34, x + w * .86, y + h * .34, "mid", 2.4) + line(x + w * .5, y + h * .52, x + w * .78, y + h * .52, "lo", 2.4)
            + line(x + w * .5, y + h * .68, x + w * .7, y + h * .68, "lo", 2.4))


def person(cx, cy, s, t="hi", w=1.8, hot=False):
    k = s / 100.0
    c = "amber" if hot else t
    return (circ(cx, cy - 34 * k, 18 * k, c, w)
            + path("M%s %sv%sa%s %s 0 0 1 %s 0v%s" % (n(cx - 40 * k), n(cy + 50 * k), n(-20 * k), n(40 * k), n(40 * k), n(80 * k), n(20 * k)), c, w))


def barrier(x, y, w, h, t="hi", hot=True):
    """A gate: two posts and a bar. hot = amber bar (closed to what matters)."""
    s = rect(x, y, w * .12, h, t, 1.8, "bg") + rect(x + w * .88, y, w * .12, h, t, 1.8, "bg")
    s += line(x + w * .12, y + h * .28, x + w * .88, y + h * .28, "amber" if hot else t, 5 if hot else 3)
    s += line(x + w * .12, y + h * .28, x + w * .88, y + h * .28, "amber" if hot else t, 3)
    return s


def chain(x, y, count=3, s=46, t="hi", broken=None):
    """Interlocking links along a horizontal line; broken = index of a link drawn open in amber."""
    out = []
    for i in range(count):
        cx = x + i * s * .82
        hot = broken is not None and i == broken
        out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" stroke="%s" stroke-width="2.4" fill="none"%s/>'
                   % (n(cx - s * .5), n(y - s * .27), n(s), n(s * .54), n(s * .27), tone("amber" if hot else t),
                      ' stroke-dasharray="5 6"' if hot else ""))
    return "".join(out)


# ---- people, places, objects -----------------------------------------------------------------------------------

def building(x, y, w, h, floors=6, cols=3, t="hi", hot=None, sw=1.8, fill="bg"):
    """An office elevation; hot = (floor, col) lit amber window."""
    s = rect(x, y, w, h, t, sw, fill, r=1)
    cw, ch = w / (cols * 1.0 + .6), h / (floors + .6)
    for i in range(floors):
        for j in range(cols):
            wx = x + cw * .42 + j * cw * 1.02
            wy = y + ch * .35 + i * ch
            lit = hot == (i, j)
            s += rect(wx, wy, cw * .5, ch * .5, "amber" if lit else "lo", 1.4 if not lit else 2, AMBER_WASH if lit else "none")
    return s


def skyline(x0, base, specs, hot=None):
    """Row of buildings: specs = [(dx, w, h)] relative; hot = index."""
    s = line(x0 - 20, base, x0 + sum(a[0] for a in specs) + 160, base, "mid", 1.6)
    x = x0
    for i, (dx, w, h) in enumerate(specs):
        x += dx
        s += building(x, base - h, w, h, max(2, int(h / 38)), max(1, int(w / 34)), "hi" if i == hot else "lo",
                      (0, 0) if i == hot else None, 1.4)
    return s


def window_grid(x, y, w, h, rows, cols, t="lo", hot=None):
    cw, ch = w / cols, h / rows
    return "".join(rect(x + j * cw + cw * .14, y + i * ch + ch * .14, cw * .72, ch * .72, "amber" if hot == (i, j) else t, 1.4, AMBER_WASH if hot == (i, j) else "none")
                   for i in range(rows) for j in range(cols))


def phone(x, y, w, h, t="hi", screen=None):
    s = rect(x, y, w, h, t, 2, "bg", r=w * .14) + rect(x + w * .08, y + h * .09, w * .84, h * .78, "lo", 1.2, "none", r=2)
    s += line(x + w * .38, y + h * .05, x + w * .62, y + h * .05, "mid", 2) + circ(x + w * .5, y + h * .935, w * .05, "mid", 1.2)
    return s


def laptop(x, y, w, h, t="hi"):
    return (rect(x + w * .1, y, w * .8, h * .8, t, 2, "bg", r=6) + rect(x + w * .15, y + h * .06, w * .7, h * .66, "lo", 1.2)
            + path("M%s %sH%sL%s %sH%sZ" % (n(x), n(y + h * .84), n(x + w), n(x + w * .93), n(y + h), n(x + w * .07)), t, 2))


def envelope(x, y, w, h, t="hi", hot=False):
    c = "amber" if hot else t
    return rect(x, y, w, h, c, 1.9, "bg", r=3) + poly([(x, y), (x + w / 2, y + h * .58), (x + w, y)], c, 1.9)


def wave(x, y, w, h, bars=14, seed=3, t="hi", hot=None):
    """An audio waveform. hot = fraction (0-1) after which bars turn amber (cloned voice)."""
    out = []
    for i in range(bars):
        a = abs(math.sin(i * 1.7 + seed) * .7 + math.sin(i * .9 + seed * 2) * .3)
        hh = max(6, h * a)
        xx = x + w * i / (bars - 1)
        c = "amber" if hot is not None and i / (bars - 1) >= hot else t
        out.append(line(xx, y + h / 2 - hh / 2, xx, y + h / 2 + hh / 2, c, 3.2))
    return "".join(out)


def clock(cx, cy, r, hour=10, minute=10, t="hi", hot=True):
    s = circ(cx, cy, r, t, 1.9, "bg")
    for i in range(12):
        a = i * math.pi / 6
        s += line(cx + (r - 6) * math.sin(a), cy - (r - 6) * math.cos(a), cx + (r - 14 if i % 3 == 0 else r - 10) * math.sin(a), cy - (r - 14 if i % 3 == 0 else r - 10) * math.cos(a), "mid", 1.5)
    ah, am = (hour % 12 + minute / 60) * math.pi / 6, minute * math.pi / 30
    s += line(cx, cy, cx + r * .5 * math.sin(ah), cy - r * .5 * math.cos(ah), t, 2.8)
    s += line(cx, cy, cx + r * .74 * math.sin(am), cy - r * .74 * math.cos(am), "amber" if hot else t, 2.4) + dot(cx, cy, 3.5, "hi")
    return s


def gauge(cx, cy, r, frac=.7, t="hi", hot=True):
    """Semicircular gauge; the arc up to frac and the needle mark the reading (amber when hot)."""
    a1 = math.pi * (1 - frac)
    end = (cx + r * math.cos(a1), cy - r * math.sin(a1))
    c = "amber" if hot else t
    s = path("M%s %sA%s %s 0 0 1 %s %s" % (n(cx - r), n(cy), n(r), n(r), n(cx + r), n(cy)), "lo", 2.4)
    s += path("M%s %sA%s %s 0 0 1 %s %s" % (n(cx - r), n(cy), n(r), n(r), n(end[0]), n(end[1])), c, 3)
    s += line(cx, cy, cx + r * .72 * math.cos(a1), cy - r * .72 * math.sin(a1), "hi", 2.4) + dot(cx, cy, 5, "hi")
    return s


def calendar(x, y, w, h, marks=(), t="hi", hot=None):
    s = rect(x, y, w, h, t, 1.9, "bg", r=4) + rect(x, y, w, h * .2, t, 1.4, "none", r=4)
    for k in (.28, .72):
        s += line(x + w * k, y - h * .06, x + w * k, y + h * .08, t, 2.2)
    cw, ch = w / 7, (h * .74) / 4
    for i in range(4):
        for j in range(7):
            idx = i * 7 + j
            cx, cy = x + (j + .5) * cw, y + h * .26 + (i + .5) * ch
            if hot == idx:
                s += circ(cx, cy, min(cw, ch) * .36, "amber", 2.4, AMBER_WASH)
            elif idx in marks:
                s += dot(cx, cy, 3.4, "hi")
            else:
                s += dot(cx, cy, 2, "lo")
    return s


def gear(cx, cy, r, teeth=10, t="hi"):
    pts = []
    for i in range(teeth * 2):
        a0 = math.pi * 2 * i / (teeth * 2)
        rr = r if i % 2 == 0 else r * .8
        for da in (-.11, .11):
            pts.append((cx + rr * math.cos(a0 + da * 2 * math.pi / (teeth * 2) * 1.2), cy + rr * math.sin(a0 + da * 2 * math.pi / (teeth * 2) * 1.2)))
    return poly(pts, t, 1.8, "bg", None, True) + circ(cx, cy, r * .34, t, 1.8)


def scale(cx, cy, s, tilt=0, t="hi"):
    k = s / 100.0
    a = math.radians(tilt)
    lx, ly = cx - 70 * k * math.cos(a), cy - 34 * k - 70 * k * math.sin(a)
    rx, ry = cx + 70 * k * math.cos(a), cy - 34 * k + 70 * k * math.sin(a)
    out = line(cx, cy - 34 * k, cx, cy + 60 * k, t, 2) + line(cx - 34 * k, cy + 60 * k, cx + 34 * k, cy + 60 * k, t, 2)
    out += line(lx, ly, rx, ry, t, 2) + circ(cx, cy - 34 * k, 4 * k, t, 2)
    for x_, y_, hot in ((lx, ly, False), (rx, ry, True)):
        c = "amber" if hot else t
        out += line(x_, y_, x_ - 22 * k, y_ + 34 * k, c, 1.5) + line(x_, y_, x_ + 22 * k, y_ + 34 * k, c, 1.5)
        out += path("M%s %sA%s %s 0 0 0 %s %sZ" % (n(x_ - 28 * k), n(y_ + 34 * k), n(28 * k), n(16 * k), n(x_ + 28 * k), n(y_ + 34 * k)), c, 1.8, AMBER_WASH if hot else "none")
    return out


def pin(cx, cy, s, t="amber"):
    k = s / 100.0
    return (path("M%s %sC%s %s %s %s %s %sC%s %s %s %s %s %sZ" % tuple(n(v) for v in (
        cx, cy + 44 * k, cx - 34 * k, cy + 4 * k, cx - 34 * k, cy - 34 * k, cx, cy - 34 * k,
        cx + 34 * k, cy - 34 * k, cx + 34 * k, cy + 4 * k, cx, cy + 44 * k)), t, 2.2, AMBER_WASH if t == "amber" else "none")
            + circ(cx, cy - 8 * k, 10 * k, t, 2))


def bars(x, y, w, h, vals, hot=None, t="lo"):
    bw = w / len(vals)
    return "".join(rect(x + i * bw + bw * .14, y + h - h * v, bw * .72, h * v, "amber" if hot == i else t, 1.8, AMBER_WASH if hot == i else PANEL)
                   for i, v in enumerate(vals)) + line(x, y + h, x + w, y + h, "mid", 1.6)


def linegraph(x, y, w, h, pts, t="hi", hot_from=None):
    P = [(x + w * i / (len(pts) - 1), y + h - h * v) for i, v in enumerate(pts)]
    s = line(x, y + h, x + w, y + h, "mid", 1.6) + line(x, y, x, y + h, "lo", 1.4)
    if hot_from is None:
        return s + poly(P, t, 2.2)
    k = hot_from
    return s + poly(P[:k + 1], t, 2.2) + poly(P[k:], "amber", 2.8)


def stairs(x, y, w, h, n_steps=5, t="hi", hot_to=None):
    """Ascending steps from bottom-left; hot_to = amber up to that step."""
    d, dh = [], []
    for i in range(n_steps):
        xa, xb = x + w * i / n_steps, x + w * (i + 1) / n_steps
        ya = y + h - h * (i + 1) / n_steps
        d.append((xa, ya))
        d.append((xb, ya))
    pts = [(x, y + h)] + d
    s = poly(pts, t, 2, "none")
    if hot_to:
        s += poly([(x, y + h)] + d[:hot_to * 2], "amber", 2.8)
    return s


def funnel(x, y, w, h, t="hi"):
    return poly([(x, y), (x + w, y), (x + w * .58, y + h * .55), (x + w * .58, y + h), (x + w * .42, y + h), (x + w * .42, y + h * .55)], t, 2, "bg", None, True)


def balloon(x, y, w, h, t="hi", tail="left"):
    s = rect(x, y, w, h, t, 1.9, "bg", r=12)
    tx = x + w * .22 if tail == "left" else x + w * .78
    return s + poly([(tx - 16, y + h), (tx - 24, y + h + 26), (tx + 8, y + h)], t, 1.9, "bg")


def bolt(cx, cy, s, t="amber", w=2.4):
    k = s / 100.0
    return poly([(cx + 10 * k, cy - 60 * k), (cx - 26 * k, cy + 8 * k), (cx - 2 * k, cy + 8 * k), (cx - 14 * k, cy + 60 * k), (cx + 28 * k, cy - 14 * k), (cx + 4 * k, cy - 14 * k)],
                t, w, AMBER_WASH if t == "amber" else "none", None, True)


def flame(cx, cy, s, t="amber", w=2.4):
    """A flame: an outer tongue with a smaller one inside."""
    k = s / 100.0
    P = lambda *a: " ".join(n(v) for v in a)
    outer = "M" + P(cx, cy - 70 * k) + "C" + P(cx + 16 * k, cy - 44 * k, cx + 46 * k, cy - 26 * k, cx + 42 * k, cy + 16 * k) \
        + "C" + P(cx + 40 * k, cy + 52 * k, cx - 40 * k, cy + 56 * k, cx - 40 * k, cy + 14 * k) \
        + "C" + P(cx - 40 * k, cy - 8 * k, cx - 22 * k, cy - 14 * k, cx - 16 * k, cy - 34 * k) \
        + "C" + P(cx - 10 * k, cy - 18 * k, cx - 4 * k, cy - 24 * k, cx, cy - 70 * k) + "Z"
    inner = "M" + P(cx + 2 * k, cy - 6 * k) + "C" + P(cx + 22 * k, cy + 4 * k, cx + 20 * k, cy + 36 * k, cx + 2 * k, cy + 40 * k) \
        + "C" + P(cx - 18 * k, cy + 36 * k, cx - 16 * k, cy + 8 * k, cx + 2 * k, cy - 6 * k) + "Z"
    return path(outer, t, w, AMBER_WASH if t == "amber" else "none") + path(inner, t, w * .7, "none")


def pole(x, y, h, t="mid"):
    """A utility pole with two crossarms and wires' insulators."""
    return (line(x, y, x, y + h, t, 2.4) + line(x - 34, y + h * .12, x + 34, y + h * .12, t, 2.2) + line(x - 26, y + h * .24, x + 26, y + h * .24, t, 2.2)
            + dot(x - 30, y + h * .12 - 5, 2.4, t) + dot(x + 30, y + h * .12 - 5, 2.4, t))


# ---- industry silhouettes --------------------------------------------------------------------------------------

def column(x, y, w, h, t="hi"):
    """A fluted classical column (law, finance, institutions)."""
    s = rect(x, y, w, h * .08, t, 1.8, "bg", r=1) + rect(x + w * .08, y + h * .08, w * .84, h * .04, t, 1.6, "bg")
    s += rect(x + w * .14, y + h * .12, w * .72, h * .74, t, 1.6, "bg")
    for k in range(1, 5):
        s += line(x + w * (.14 + .144 * k), y + h * .13, x + w * (.14 + .144 * k), y + h * .85, "lo", 1.3)
    return s + rect(x, y + h * .9, w, h * .1, t, 1.8, "bg", r=1) + rect(x + w * .08, y + h * .86, w * .84, h * .04, t, 1.6, "bg")


def pediment(x, y, w, h, t="hi"):
    return poly([(x, y + h), (x + w / 2, y), (x + w, y + h)], t, 2, "bg", None, True)


def tooth(cx, cy, s, t="hi"):
    k = s / 100.0
    R = [(0, -46, 18, -66, 50, -58, 48, -20), (46, 8, 34, 14, 30, 34), (26, 56, 22, 64, 14, 64), (4, 64, 8, 20, 0, 20)]
    d = "M%s %sC%s %s %s %s %s %s" % tuple(n(v) for v in (cx, cy - 46 * k, cx + 18 * k, cy - 66 * k, cx + 50 * k, cy - 58 * k, cx + 48 * k, cy - 20 * k))
    for a, b, c, e, f, g in R[1:]:
        d += "C%s %s %s %s %s %s" % tuple(n(v) for v in (cx + a * k, cy + b * k, cx + c * k, cy + e * k, cx + f * k, cy + g * k))
    for a, b, c, e, f, g in ((-8, 20, -4, 64, -14, 64), (-22, 64, -26, 56, -30, 34), (-34, 14, -46, 8, -48, -20)):
        d += "C%s %s %s %s %s %s" % tuple(n(v) for v in (cx + a * k, cy + b * k, cx + c * k, cy + e * k, cx + f * k, cy + g * k))
    d += "C%s %s %s %s %s %sZ" % tuple(n(v) for v in (cx - 50 * k, cy - 58 * k, cx - 18 * k, cy - 66 * k, cx, cy - 46 * k))
    return path(d, t, 2, "none")


def cross(cx, cy, s, t="hi", w=2):
    k = s / 100.0
    return path("M%s %sh%sv-%sh%sv%sh%sv%sh-%sv%sh-%sv-%sh-%sz" % (
        n(cx - 46 * k), n(cy - 16 * k), n(30 * k), n(30 * k), n(32 * k), n(30 * k), n(30 * k), n(32 * k), n(30 * k), n(30 * k), n(32 * k), n(30 * k), n(30 * k)), t, w)


def crane(x, y, h, t="hi", hot=True):
    """Tower crane silhouette."""
    s = line(x, y, x, y + h, t, 2.4) + poly([(x - 10, y + h), (x + 10, y + h)], t, 3)
    s += line(x - 40, y, x + 150, y, t, 2.4) + line(x, y - 34, x + 150, y, t, 1.6) + line(x, y - 34, x - 40, y, t, 1.6) + line(x, y - 34, x, y, t, 2)
    s += line(x + 110, y, x + 110, y + 70, "mid", 1.4) + rect(x + 96, y + 70, 28, 20, "amber" if hot else t, 2, AMBER_WASH if hot else "none")
    return s


def plate(cx, cy, r, t="hi"):
    """A place setting: plate, fork and knife."""
    s = circ(cx, cy, r, t, 2, "bg") + circ(cx, cy, r * .62, "lo", 1.4)
    fx, kx = cx - r - 46, cx + r + 46
    s += line(fx, cy - r * .9, fx, cy + r * .9, t, 2) + line(fx - 9, cy - r * .9, fx - 9, cy - r * .35, t, 1.8) + line(fx + 9, cy - r * .9, fx + 9, cy - r * .35, t, 1.8) + path("M%s %sq0 18 9 18" % (n(fx - 9), n(cy - r * .35)), t, 1.8)
    s += path("M%s %sV%s" % (n(kx), n(cy - r * .9), n(cy + r * .9)), t, 2) + path("M%s %sc18 8 22 46 8 %s" % (n(kx), n(cy - r * .9), n(r * .62)), t, 1.8)
    return s


def helix(x, y, w, h, turns=2, t="hi"):
    out = []
    steps = int(60 * turns)
    for phase, tn in ((0, t), (math.pi, "mid")):
        pts = [(x + w / 2 + w / 2 * math.sin(i / steps * turns * 2 * math.pi + phase), y + h * i / steps) for i in range(steps + 1)]
        out.append(poly(pts, tn, 2.2 if tn == t else 1.6))
    for i in range(0, steps + 1, 8):
        a = x + w / 2 + w / 2 * math.sin(i / steps * turns * 2 * math.pi)
        b = x + w / 2 + w / 2 * math.sin(i / steps * turns * 2 * math.pi + math.pi)
        out.append(line(a, y + h * i / steps, b, y + h * i / steps, "lo", 1.4))
    return "".join(out)


def truck(x, y, w, h, t="hi"):
    s = rect(x, y, w * .62, h * .72, t, 2, "bg") + path("M%s %sh%sl%s %sv%sh-%s" % (
        n(x + w * .62), n(y + h * .22), n(w * .2), n(w * .18), n(h * .24), n(h * .26), n(w * .38)), t, 2, "bg")
    for wx in (.2, .8):
        s += circ(x + w * wx, y + h * .8, h * .16, t, 2, "bg")
    return s


def plane(cx, cy, s, t="hi"):
    """An aircraft in plan view, nose to the right."""
    k = s / 100.0
    top = [(86, 0), (60, -8), (12, -8), (-22, -60), (-44, -60), (-30, -8), (-64, -8), (-80, -30), (-92, -30), (-84, 0)]
    pts = [(cx + a * k, cy + b * k) for a, b in top] + [(cx + a * k, cy - b * k) for a, b in reversed(top[1:-1])]
    return poly(pts, t, 2, "bg", None, True)


def paw(cx, cy, s, t="hi"):
    k = s / 100.0
    s_ = path("M%s %sC%s %s %s %s %s %sC%s %s %s %s %s %sC%s %s %s %s %s %sZ" % tuple(n(v) for v in (
        cx, cy + 10 * k, cx + 30 * k, cy + 6 * k, cx + 40 * k, cy + 46 * k, cx, cy + 46 * k,
        cx - 40 * k, cy + 46 * k, cx - 30 * k, cy + 6 * k, cx, cy + 10 * k, cx - 40 * k, cy + 46 * k, cx, cy + 46 * k, cx, cy + 10 * k)), t, 2, "bg")
    s_ = circ(cx, cy + 24 * k, 24 * k, t, 2, "bg")
    for dx, dy in ((-34, -8), (-13, -30), (13, -30), (34, -8)):
        s_ += '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" stroke="%s" stroke-width="2" fill="none" transform="rotate(%s %s %s)"/>' % (
            n(cx + dx * k), n(cy + dy * k), n(9 * k), n(13 * k), tone(t), n(dx * .5), n(cx + dx * k), n(cy + dy * k))
    return s_


def bookshelf(x, y, w, h, rows=3, t="mid"):
    s = rect(x, y, w, h, t, 1.8, "bg")
    rh = h / rows
    for i in range(1, rows):
        s += line(x, y + i * rh, x + w, y + i * rh, t, 1.6)
    for i in range(rows):
        bx = x + 10
        j = 0
        while bx < x + w - 18:
            bw = 13 + (j * 5 + i * 3) % 9
            bh = rh * (.5 + ((j * 7 + i * 11) % 5) / 12)
            s += rect(bx, y + (i + 1) * rh - bh, bw, bh, "lo", 1.3)
            bx += bw + 6 + (j + i) % 3
            j += 1
    return s


def sprout(cx, cy, s, t="hi"):
    """A young plant: a stem with an amber leaf."""
    k = s / 100.0
    P = lambda *a: tuple(n(v) for v in a)
    stem = line(cx, cy + 60 * k, cx, cy - 10 * k, t, 2.2)
    left = path("M%s %sQ%s %s %s %sQ%s %s %s %sZ" % P(cx, cy - 10 * k, cx - 62 * k, cy - 14 * k, cx - 50 * k, cy - 62 * k, cx - 4 * k, cy - 54 * k, cx, cy - 10 * k), "amber", 2.2, AMBER_WASH)
    right = path("M%s %sQ%s %s %s %sQ%s %s %s %sZ" % P(cx, cy + 10 * k, cx + 62 * k, cy + 6 * k, cx + 50 * k, cy - 42 * k, cx + 4 * k, cy - 34 * k, cx, cy + 10 * k), t, 2.2, "bg")
    return stem + left + right


# ---- more everyday parts -------------------------------------------------------------------------------------------

def magnifier(cx, cy, r, t="hi", w=2.2, ang=45):
    a = math.radians(ang)
    return circ(cx, cy, r, t, w, "rgba(255,255,255,.03)") + line(cx + r * math.cos(a), cy + r * math.sin(a), cx + r * 2.0 * math.cos(a), cy + r * 2.0 * math.sin(a), t, w + 2.2)


def folder(x, y, w, h, t="hi", tab=.36):
    return path("M%s %sV%sH%sL%s %sH%sV%sZ" % (n(x), n(y + h), n(y + h * .14), n(x + w * tab), n(x + w * (tab + .09)), n(y + h * .26), n(x + w), n(y + h)), t, 1.9, "bg")


def stack(x, y, w, h, count=3, gap=14, t="hi"):
    """Offset sheets behind a front sheet."""
    s = ""
    for k in reversed(range(1, count)):
        s += rect(x + k * gap, y - k * gap, w, h, "lo", 1.4, "bg", r=3)
    return s + rect(x, y, w, h, t, 1.9, "bg", r=3)


def toggle(x, y, w, on=True):
    h = w * .5
    s = rect(x, y, w, h, "amber" if on else "mid", 2, AMBER_WASH if on else "none", r=h / 2)
    return s + circ(x + (w - h * .5 if on else h * .5), y + h / 2, h * .3, "hi", 1.8, "bg")


def hourglass(cx, cy, s, t="hi", hot=True):
    k = s / 100.0
    o = line(cx - 46 * k, cy - 62 * k, cx + 46 * k, cy - 62 * k, t, 2.6) + line(cx - 46 * k, cy + 62 * k, cx + 46 * k, cy + 62 * k, t, 2.6)
    for sgn in (-1, 1):
        o += path("M%s %sC%s %s %s %s %s %sC%s %s %s %s %s %s" % tuple(n(v) for v in (
            cx + sgn * 38 * k, cy - 62 * k, cx + sgn * 38 * k, cy - 20 * k, cx + sgn * 6 * k, cy - 8 * k, cx + sgn * 6 * k, cy,
            cx + sgn * 6 * k, cy + 8 * k, cx + sgn * 38 * k, cy + 20 * k, cx + sgn * 38 * k, cy + 62 * k)), t, 2)
    if hot:
        o += path("M%s %sH%sL%s %sH%sZ" % (n(cx - 26 * k), n(cy + 62 * k), n(cx + 26 * k), n(cx + 4 * k), n(cy + 24 * k), n(cx - 4 * k)), "amber", 2, AMBER_WASH)
    return o


def bricks(x, y, w, h, rows=5, t="mid", gap=None):
    """A wall of bricks; gap = (row, index) left open."""
    rh = h / rows
    s = ""
    for i in range(rows):
        off = -w * .12 if i % 2 else 0
        bw = w / 4
        for j in range(-1, 5):
            bx = x + off + j * bw
            a, b = max(x, bx + 3), min(x + w, bx + bw - 3)
            if b - a < 14 or gap == (i, j):
                continue
            s += rect(a, y + i * rh + 3, b - a, rh - 6, t, 1.6, "bg", r=1)
    return s


def router(x, y, w, h, t="hi"):
    """A network edge device: chassis, ports, status lights, antennae."""
    s = rect(x, y, w, h, t, 2, "bg", r=6)
    for k in range(5):
        s += rect(x + w * .08 + k * w * .12, y + h * .56, w * .08, h * .2, "mid", 1.3)
    s += dot(x + w * .8, y + h * .64, 4, "mid") + dot(x + w * .87, y + h * .64, 4, "amber") + line(x + w * .08, y + h * .3, x + w * .6, y + h * .3, "lo", 2.6)
    return s + line(x + w * .18, y, x + w * .1, y - h * .9, t, 2) + line(x + w * .82, y, x + w * .9, y - h * .9, t, 2)


def globe(cx, cy, r, t="hi", w=1.8):
    s = circ(cx, cy, r, t, w, "bg") + line(cx - r, cy, cx + r, cy, "lo", 1.3)
    for k in (.45, .85):
        s += '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" stroke="%s" stroke-width="1.3" fill="none"/>' % (n(cx), n(cy), n(r * k), n(r), tone("lo"))
        s += '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" stroke="%s" stroke-width="1.3" fill="none"/>' % (n(cx), n(cy), n(r), n(r * (1 - k) * .9 + 2), tone("faint"))
    return s


def ecg(x, y, w, h, t="hi", beats=2, hot=None):
    """A heartbeat trace; hot = beat index drawn in amber."""
    seg = w / beats
    out = [line(x, y + h / 2, x + w, y + h / 2, "faint", 1.2)]
    for i in range(beats):
        b = x + i * seg
        pts = [(b, y + h / 2), (b + seg * .3, y + h / 2), (b + seg * .38, y + h * .32), (b + seg * .44, y + h * .7), (b + seg * .5, y + h * .05),
               (b + seg * .58, y + h * .95), (b + seg * .66, y + h / 2), (b + seg, y + h / 2)]
        out.append(poly(pts, "amber" if hot == i else t, 2.6 if hot == i else 2))
    return "".join(out)


def fingerprint(cx, cy, s, t="hi", hot=True):
    k = s / 100.0
    o = ""
    for i, r in enumerate((14, 26, 38, 50, 62)):
        c = "amber" if hot and i == 2 else t
        o += path("M%s %sA%s %s 0 0 1 %s %s" % (n(cx - r * k), n(cy + 18 * k), n(r * k), n(r * k * 1.15), n(cx + r * k), n(cy + 18 * k)), c, 2.4 if c == "amber" else 2)
    return o + line(cx - 14 * k, cy + 18 * k, cx - 14 * k, cy + 40 * k, t, 2) + line(cx + 14 * k, cy + 18 * k, cx + 14 * k, cy + 40 * k, t, 2)


def wifi(cx, cy, s, t="hi"):
    k = s / 100.0
    o = dot(cx, cy + 38 * k, 5 * k + 1, t)
    for r in (26, 48, 70):
        o += path("M%s %sA%s %s 0 0 1 %s %s" % (n(cx - r * k), n(cy + 26 * k), n(r * k), n(r * k), n(cx + r * k), n(cy + 26 * k)), t, 2.2)
    return o


def coin(cx, cy, r, t="hi", hot=False):
    c = "amber" if hot else t
    return circ(cx, cy, r, c, 2, AMBER_WASH if hot else "bg") + circ(cx, cy, r * .72, c, 1.3)


def briefcase(x, y, w, h, t="hi"):
    return (rect(x, y + h * .22, w, h * .78, t, 2, "bg", r=5) + path("M%s %sV%sh%sV%s" % (n(x + w * .34), n(y + h * .22), n(y + h * .06), n(w * .32), n(y + h * .22)), t, 2)
            + line(x, y + h * .56, x + w, y + h * .56, "mid", 1.4) + rect(x + w * .42, y + h * .5, w * .16, h * .14, t, 1.8, "bg"))


def contract(x, y, w, h, t="hi", hot=True):
    s = doc(x, y, w, h, 6, None, t)
    sy = y + h * .84
    s += line(x + w * .14, sy, x + w * .56, sy, "amber" if hot else "mid", 2.2) + path("M%s %sq10 -18 20 0t20 0t18 -4" % (n(x + w * .2), n(sy - 4)), "amber" if hot else "mid", 1.8)
    return s


def speedo(cx, cy, r, vals=5, t="hi", hot=None):
    """Radial dial with tick marks; hot = index of the amber tick."""
    s = ""
    for i in range(vals + 1):
        a = math.pi + math.pi * i / vals
        s += line(cx + (r - 14) * math.cos(a), cy + (r - 14) * math.sin(a), cx + r * math.cos(a), cy + r * math.sin(a), "amber" if hot == i else t, 2.4 if hot == i else 1.8)
    return s + path("M%s %sA%s %s 0 0 1 %s %s" % (n(cx - r - 10), n(cy), n(r + 10), n(r + 10), n(cx + r + 10), n(cy)), "lo", 1.6)
