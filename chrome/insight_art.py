#!/usr/bin/env python3
"""
chrome/insight_art.py -- editorial illustrations for Insights articles (original vector artwork, no stock or AI
imagery). Each category has its own visual language; each article gets a deterministic variation seeded by its
slug, so the series is consistent without repeating. Palette: navy ground, white linework, one amber accent.

    from insight_art import art_svg            # art_svg(slug, category) -> SVG markup (1200 x 675)
    python chrome/insight_art.py SLUG "Category" > out.svg

Categories: Cybersecurity & Risk, Artificial Intelligence & Automation, Technology Leadership,
Cloud & Infrastructure, Governance & Compliance, Business Continuity, Industry Perspectives.
"""
import hashlib
import math
import random
import sys

W, H = 1200, 675
BG = "#0b1a2b"
LINE = "rgba(255,255,255,%s)"
AMBER = "#e39a3d"


def _rng(slug):
    return random.Random(int(hashlib.sha256(slug.encode("utf-8")).hexdigest()[:12], 16))


def _f(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def _grid(step=60, a=".055"):
    p = []
    for x in range(0, W + 1, step):
        p.append("M%d 0V%d" % (x, H))
    for y in range(0, H + 1, step):
        p.append("M0 %dH%d" % (y, W))
    return '<path d="%s" stroke="%s" stroke-width="1" fill="none"/>' % ("".join(p), LINE % a)


def _security(r):
    cx, cy = W * r.uniform(.55, .68), H * r.uniform(.45, .55)
    rings = r.randint(4, 6)
    out = []
    for i in range(rings):
        s = 92 + i * r.uniform(64, 76)
        gap = r.uniform(0, 360)
        pts = []
        for k in range(4):
            ang = math.radians(45 + 90 * k)
            pts.append((cx + s * math.cos(ang), cy + s * math.sin(ang)))
        d = "M%s %s" % (_f(pts[0][0]), _f(pts[0][1])) + "".join("L%s %s" % (_f(x), _f(y)) for x, y in pts[1:]) + "Z"
        dash = "%d %d" % (r.randint(40, 120), r.randint(8, 22)) if i % 2 else "none"
        out.append('<path d="%s" stroke="%s" stroke-width="%s" fill="none" stroke-dasharray="%s" transform="rotate(%s %s %s)"/>'
                   % (d, LINE % (".72" if i == 0 else ".4"), "1.6" if i == 0 else "1.3", dash, _f(gap % 6), _f(cx), _f(cy)))
    # an incoming path stopped at the inner perimeter
    ang = r.uniform(math.pi * .8, math.pi * 1.2)
    sx, sy = cx + 520 * math.cos(ang), cy + 520 * math.sin(ang)
    ex, ey = cx + 92 * math.cos(ang), cy + 92 * math.sin(ang)
    out.append('<path d="M%s %sL%s %s" stroke="%s" stroke-width="2" stroke-dasharray="6 8"/>' % (_f(sx), _f(sy), _f(ex), _f(ey), AMBER))
    out.append('<rect x="%s" y="%s" width="10" height="10" fill="%s"/>' % (_f(ex - 5), _f(ey - 5), AMBER))
    out.append('<rect x="%s" y="%s" width="14" height="14" fill="none" stroke="#fff" stroke-width="1.4"/>' % (_f(cx - 7), _f(cy - 7)))
    return out


def _ai(r):
    cols = r.randint(4, 5)
    x0, x1 = W * .22, W * .86
    layers = []
    for c in range(cols):
        n = r.randint(3, 6)
        x = x0 + (x1 - x0) * c / (cols - 1)
        ys = [H * .2 + (H * .6) * (i + .5) / n for i in range(n)]
        layers.append([(x, y) for y in ys])
    out, path = [], []
    for a, b in zip(layers, layers[1:]):
        for p in a:
            for q in b:
                if r.random() < .55:
                    out.append('<path d="M%s %sL%s %s" stroke="%s" stroke-width="1"/>' % (_f(p[0]), _f(p[1]), _f(q[0]), _f(q[1]), LINE % ".22"))
    for layer in layers:
        path.append(r.choice(layer))
        for (x, y) in layer:
            out.append('<circle cx="%s" cy="%s" r="7" fill="%s" stroke="#fff" stroke-width="1.6"/>' % (_f(x), _f(y), BG))
    out.append('<path d="M%s" stroke="%s" stroke-width="2.8" fill="none"/>' % (" L".join("%s %s" % (_f(x), _f(y)) for x, y in path), AMBER))
    for (x, y) in path:
        out.append('<circle cx="%s" cy="%s" r="8" fill="%s"/>' % (_f(x), _f(y), AMBER))
    return out


def _leadership(r):
    steps = r.randint(5, 7)
    x0, y0, x1, y1 = W * .14, H * .76, W * .88, H * .22
    out = ['<path d="M%s %sH%s" stroke="%s" stroke-width="1.2"/>' % (_f(x0), _f(y0 + 40), _f(x1), LINE % ".4")]
    pts = []
    for i in range(steps + 1):
        x = x0 + (x1 - x0) * i / steps
        y = y0 - (y0 - y1) * (i / steps) ** r.uniform(.8, 1.3)
        pts.append((x, y))
        out.append('<path d="M%s %sV%s" stroke="%s" stroke-width="1" stroke-dasharray="3 6"/>' % (_f(x), _f(y0 + 40), _f(y), LINE % ".2"))
        out.append('<path d="M%s %sv12" stroke="%s" stroke-width="1.2"/>' % (_f(x), _f(y0 + 34), LINE % ".55"))
    d = "M%s %s" % (_f(pts[0][0]), _f(pts[0][1]))
    for (a, b), (c, e) in zip(pts, pts[1:]):
        d += "H%sV%s" % (_f(c), _f(e))
    now = r.randint(2, steps - 1)
    out.append('<path d="%s" stroke="%s" stroke-width="1.6" fill="none"/>' % (d, LINE % ".7"))
    dn = "M%s %s" % (_f(pts[0][0]), _f(pts[0][1]))
    for (a, b), (c, e) in list(zip(pts, pts[1:]))[:now]:
        dn += "H%sV%s" % (_f(c), _f(e))
    out.append('<path d="%s" stroke="%s" stroke-width="2.4" fill="none"/>' % (dn, AMBER))
    for i, (x, y) in enumerate(pts):
        fill = AMBER if i == now else BG
        out.append('<rect x="%s" y="%s" width="12" height="12" fill="%s" stroke="%s" stroke-width="1.4"/>' % (_f(x - 6), _f(y - 6), fill, AMBER if i == now else "#fff"))
    return out


def _cloud(r):
    n, u = r.randint(5, 7), r.uniform(38, 42)
    c, s = math.cos(math.radians(30)) * u, math.sin(math.radians(30)) * u
    cx, cy, gap = W * r.uniform(.5, .6), H * .66, r.uniform(80, 92)
    layers = r.randint(3, 4)
    P = lambda x, y, k: (cx + (x - y) * c, cy + (x + y) * s - k * gap - n * s)
    out = []
    for k in range(layers):
        corners = [P(0, 0, k), P(n, 0, k), P(n, n, k), P(0, n, k)]
        out.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="1.2"/>'
                   % (" ".join("%s,%s" % (_f(a), _f(b)) for a, b in corners), LINE % (".06" if k == layers - 1 else ".03"), LINE % ".5"))
        g = []
        for i in range(1, n):
            a, b = P(i, 0, k), P(i, n, k)
            e, f = P(0, i, k), P(n, i, k)
            g.append("M%s %sL%s %sM%s %sL%s %s" % (_f(a[0]), _f(a[1]), _f(b[0]), _f(b[1]), _f(e[0]), _f(e[1]), _f(f[0]), _f(f[1])))
        out.append('<path d="%s" stroke="%s" stroke-width="1" fill="none"/>' % ("".join(g), LINE % ".12"))
    x, y = r.randint(1, n - 1), r.randint(1, n - 1)
    for k in range(layers - 1):
        a, b = P(x, y, k), P(x, y, k + 1)
        out.append('<path d="M%s %sL%s %s" stroke="%s" stroke-width="2" stroke-dasharray="4 6"/>' % (_f(a[0]), _f(a[1]), _f(b[0]), _f(b[1]), AMBER))
    for k in range(layers):
        a = P(x, y, k)
        out.append('<rect x="%s" y="%s" width="9" height="9" fill="%s"/>' % (_f(a[0] - 4.5), _f(a[1] - 4.5), AMBER))
    return out


def _governance(r):
    rows, cols = r.randint(6, 8), r.randint(5, 7)
    x0, y0, cw, rh = W * .3, H * .2, r.uniform(92, 110), r.uniform(48, 56)
    out = []
    for i in range(rows + 1):
        y = y0 + i * rh
        out.append('<path d="M%s %sH%s" stroke="%s" stroke-width="%s"/>' % (_f(x0), _f(y), _f(x0 + cols * cw), LINE % (".55" if i in (0, rows) else ".18"), "1.4" if i in (0, rows) else "1"))
    for j in range(cols + 1):
        x = x0 + j * cw
        out.append('<path d="M%s %sV%s" stroke="%s" stroke-width="1"/>' % (_f(x), _f(y0), _f(y0 + rows * rh), LINE % ".14"))
    for i in range(rows):
        for j in range(cols):
            v = r.random()
            if v < .45:
                w = cw * r.uniform(.3, .75)
                out.append('<rect x="%s" y="%s" width="%s" height="4" fill="%s"/>' % (_f(x0 + j * cw + 14), _f(y0 + i * rh + rh / 2 - 2), _f(w), LINE % ".35"))
    hi, hj = r.randint(1, rows - 2), r.randint(1, cols - 2)
    out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="2.2"/>' % (_f(x0 + hj * cw), _f(y0 + hi * rh), _f(cw), _f(rh), AMBER))
    out.append('<path d="M%s %sH%s" stroke="%s" stroke-width="2"/>' % (_f(x0 - 60), _f(y0 + hi * rh + rh / 2), _f(x0 + hj * cw), AMBER))
    return out


def _continuity(r):
    cx, cy = W * r.uniform(.56, .64), H * .5
    out = []
    for i in range(r.randint(4, 5)):
        rad = 92 + i * 52
        a0, a1 = r.uniform(0, 80), r.uniform(240, 320)
        p0 = (cx + rad * math.cos(math.radians(a0)), cy + rad * math.sin(math.radians(a0)))
        p1 = (cx + rad * math.cos(math.radians(a1)), cy + rad * math.sin(math.radians(a1)))
        big = 1 if (a1 - a0) % 360 > 180 else 0
        out.append('<path d="M%s %sA%d %d 0 %d 1 %s %s" stroke="%s" stroke-width="1.2" fill="none"/>'
                   % (_f(p0[0]), _f(p0[1]), rad, rad, big, _f(p1[0]), _f(p1[1]), LINE % ".58"))
    rad = 92 + 52 * 2
    a0, a1 = r.uniform(250, 300), r.uniform(370, 420)
    p0 = (cx + rad * math.cos(math.radians(a0)), cy + rad * math.sin(math.radians(a0)))
    p1 = (cx + rad * math.cos(math.radians(a1)), cy + rad * math.sin(math.radians(a1)))
    out.append('<path d="M%s %sA%d %d 0 0 1 %s %s" stroke="%s" stroke-width="3" fill="none"/>' % (_f(p0[0]), _f(p0[1]), rad, rad, _f(p1[0]), _f(p1[1]), AMBER))
    ang = math.radians(a1)
    tx, ty = -math.sin(ang), math.cos(ang)
    out.append('<path d="M%s %sl%s %sM%s %sl%s %s" stroke="%s" stroke-width="3"/>'
               % (_f(p1[0]), _f(p1[1]), _f(-tx * 14 - ty * 9), _f(-ty * 14 + tx * 9), _f(p1[0]), _f(p1[1]), _f(-tx * 14 + ty * 9), _f(-ty * 14 - tx * 9), AMBER))
    out.append('<rect x="%s" y="%s" width="16" height="16" fill="none" stroke="#fff" stroke-width="1.4"/>' % (_f(cx - 8), _f(cy - 8)))
    return out


def _industry(r):
    base = H * .8
    x, out, blocks = W * .16, [], []
    while x < W * .9:
        w = r.uniform(70, 150)
        h = r.uniform(140, 420)
        blocks.append((x, w, h))
        x += w + r.uniform(10, 26)
    hi = r.randrange(len(blocks))
    for i, (x, w, h) in enumerate(blocks):
        color = AMBER if i == hi else LINE % ".5"
        out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="%s" stroke-width="%s"/>'
                   % (_f(x), _f(base - h), _f(w), _f(h), "rgba(255,255,255,.03)", color, "2" if i == hi else "1.1"))
        rows = int(h // 34)
        cols = max(1, int(w // 30))
        for rr in range(1, rows):
            out.append('<path d="M%s %sH%s" stroke="%s" stroke-width="1"/>' % (_f(x + 8), _f(base - h + rr * 34), _f(x + w - 8), LINE % ".1"))
        for cc in range(1, cols):
            out.append('<path d="M%s %sV%s" stroke="%s" stroke-width="1"/>' % (_f(x + cc * w / cols), _f(base - h + 8), _f(base - 8), LINE % ".08"))
    out.append('<path d="M0 %sH%d" stroke="%s" stroke-width="1.4"/>' % (_f(base), W, LINE % ".6"))
    return out


def _leadership_lanes(r):
    """Roadmap lanes: workstreams as bars against a quarter scale, with an amber 'now' line."""
    lanes = r.randint(3, 4)
    x0, x1 = W * .12, W * .9
    lh = r.uniform(90, 104)
    y0 = (H - lanes * lh) / 2 + 24
    q = r.randint(6, 8)
    out = []
    for k in range(q + 1):
        x = x0 + (x1 - x0) * k / q
        out.append('<path d="M%s %sV%s" stroke="%s" stroke-width="1" stroke-dasharray="2 7"/>' % (_f(x), _f(y0 - 6), _f(y0 + lanes * lh), LINE % ".14"))
        out.append('<path d="M%s %sv10" stroke="%s" stroke-width="1.2"/>' % (_f(x), _f(y0 - 22), LINE % ".55"))
    for i in range(lanes + 1):
        y = y0 + i * lh
        edge = i in (0, lanes)
        out.append('<path d="M%s %sH%s" stroke="%s" stroke-width="%s"/>' % (_f(x0), _f(y), _f(x1), LINE % (".5" if edge else ".2"), "1.3" if edge else "1"))
    now = x0 + (x1 - x0) * r.uniform(.38, .62)
    hit = r.randrange(lanes)
    for i in range(lanes):
        cy = y0 + i * lh + lh / 2
        x = x0 + r.uniform(10, 60)
        while x < x1 - 90:
            w = min(r.uniform(90, 230), x1 - 20 - x)
            if i == hit and x < now < x + w:
                out.append('<rect x="%s" y="%s" width="%s" height="14" fill="%s"/>' % (_f(x), _f(cy - 7), _f(w), AMBER))
            elif x + w < now:
                out.append('<rect x="%s" y="%s" width="%s" height="14" fill="%s"/>' % (_f(x), _f(cy - 7), _f(w), LINE % ".42"))
            else:
                out.append('<rect x="%s" y="%s" width="%s" height="14" fill="none" stroke="%s" stroke-width="1.2"/>' % (_f(x), _f(cy - 7), _f(w), LINE % ".55"))
            x += w + r.uniform(24, 70)
    out.append('<path d="M%s %sV%s" stroke="%s" stroke-width="2"/>' % (_f(now), _f(y0 - 34), _f(y0 + lanes * lh + 14), AMBER))
    out.append('<rect x="%s" y="%s" width="12" height="12" fill="%s"/>' % (_f(now - 6), _f(y0 - 46), AMBER))
    return out


def _leadership_curve(r):
    """A growth curve with milestones; amber up to the current one."""
    x0, y0, x1, y1 = W * .12, H * .76, W * .88, H * .2
    k = r.uniform(.35, .65)
    c1 = (x0 + (x1 - x0) * k, y0)
    c2 = (x0 + (x1 - x0) * (1 - k * .5), y1 + (y0 - y1) * r.uniform(.05, .3))

    def bez(t):
        mt = 1 - t
        return (mt ** 3 * x0 + 3 * mt * mt * t * c1[0] + 3 * mt * t * t * c2[0] + t ** 3 * x1,
                mt ** 3 * y0 + 3 * mt * mt * t * c1[1] + 3 * mt * t * t * c2[1] + t ** 3 * y1)
    out = ['<path d="M%s %sH%s" stroke="%s" stroke-width="1.2"/>' % (_f(x0 - 20), _f(y0 + 36), _f(x1 + 20), LINE % ".4"),
           '<path d="M%s %sV%s" stroke="%s" stroke-width="1.2"/>' % (_f(x0 - 20), _f(y1 - 30), _f(y0 + 36), LINE % ".4"),
           '<path d="M%s %sC%s %s %s %s %s %s" stroke="%s" stroke-width="1.6" fill="none"/>'
           % (_f(x0), _f(y0), _f(c1[0]), _f(c1[1]), _f(c2[0]), _f(c2[1]), _f(x1), _f(y1), LINE % ".7")]
    n = r.randint(5, 7)
    now = r.randint(2, n - 2)
    tn = now / float(n)
    samples = [bez(tn * j / 40.0) for j in range(41)]
    out.append('<path d="M%s" stroke="%s" stroke-width="2.6" fill="none"/>' % (" L".join("%s %s" % (_f(x), _f(y)) for x, y in samples), AMBER))
    for i in range(n + 1):
        x, y = bez(i / float(n))
        out.append('<path d="M%s %sV%s" stroke="%s" stroke-width="1" stroke-dasharray="3 6"/>' % (_f(x), _f(y + 12), _f(y0 + 36), LINE % ".16"))
        if i == now:
            out.append('<circle cx="%s" cy="%s" r="9" fill="%s"/>' % (_f(x), _f(y), AMBER))
        else:
            out.append('<circle cx="%s" cy="%s" r="7" fill="%s" stroke="#fff" stroke-width="1.5"/>' % (_f(x), _f(y), BG))
    return out


def _security_zones(r):
    """Segmented network zones; an amber lateral path is stopped at the protected zone's boundary."""
    n = r.randint(3, 4)
    zones, x = [], W * .1
    for _ in range(n):
        w, h = r.uniform(170, 230), r.uniform(270, 400)
        zones.append([x, (H - h) / 2 + r.uniform(-36, 36), w, h])
        x += w + r.uniform(46, 76)
    span = zones[-1][0] + zones[-1][2] - W * .1
    if span > W * .8:
        s = W * .8 / span
        zones = [[W * .1 + (zx - W * .1) * s, zy, zw * s, zh] for zx, zy, zw, zh in zones]
    out, nodes = [], []
    for i, (zx, zy, zw, zh) in enumerate(zones):
        last = i == n - 1
        out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="rgba(255,255,255,.025)" stroke="%s" stroke-width="%s" stroke-dasharray="%s"/>'
                   % (_f(zx), _f(zy), _f(zw), _f(zh), LINE % (".7" if last else ".42"), "1.6" if last else "1.2", "none" if last else "8 6"))
        k = r.randint(3, 5)
        pts = [(zx + r.uniform(.22, .78) * zw, zy + (j + .5) * zh / k) for j in range(k)]
        nodes.append(pts)
        for a, b in zip(pts, pts[1:]):
            out.append('<path d="M%s %sL%s %s" stroke="%s" stroke-width="1"/>' % (_f(a[0]), _f(a[1]), _f(b[0]), _f(b[1]), LINE % ".24"))
    for i in range(n - 2):
        a, b = r.choice(nodes[i]), r.choice(nodes[i + 1])
        out.append('<path d="M%s %sL%s %s" stroke="%s" stroke-width="1.3"/>' % (_f(a[0]), _f(a[1]), _f(b[0]), _f(b[1]), LINE % ".45"))
    for pts in nodes:
        for (px, py) in pts:
            out.append('<circle cx="%s" cy="%s" r="6" fill="%s" stroke="#fff" stroke-width="1.4"/>' % (_f(px), _f(py), BG))
    a = r.choice(nodes[0])
    lz = zones[-1]
    sx, sy = lz[0] - 6, lz[1] + lz[3] * r.uniform(.3, .7)
    mx = (a[0] + sx) / 2
    out.append('<path d="M%s %sL%s %sL%s %s" stroke="%s" stroke-width="2" stroke-dasharray="6 7" fill="none"/>'
               % (_f(a[0]), _f(a[1]), _f(mx), _f(a[1] + (sy - a[1]) * .3), _f(sx), _f(sy), AMBER))
    out.append('<path d="M%s %sV%s" stroke="%s" stroke-width="3"/>' % (_f(lz[0]), _f(sy - 18), _f(sy + 18), AMBER))
    t = r.choice(nodes[-1])
    out.append('<rect x="%s" y="%s" width="16" height="16" fill="none" stroke="#fff" stroke-width="1.6"/>' % (_f(t[0] - 8), _f(t[1] - 8)))
    return out


def _ai_radial(r):
    """A radial model: rings of nodes converging on a core, with one amber inference path."""
    cx, cy = W * r.uniform(.5, .6), H * .5
    rings = [(104, r.randint(5, 7)), (180, r.randint(8, 11)), (256, r.randint(11, 15))]
    out, levels = [], []
    for rad, k in rings:
        out.append('<circle cx="%s" cy="%s" r="%d" fill="none" stroke="%s" stroke-width="1"/>' % (_f(cx), _f(cy), rad, LINE % ".1"))
        off = r.uniform(0, 2 * math.pi)
        levels.append([(cx + rad * math.cos(off + 2 * math.pi * j / k), cy + rad * math.sin(off + 2 * math.pi * j / k)) for j in range(k)])
    d2 = lambda p, q: (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
    inner = [[(cx, cy)]] + levels[:-1]
    for li, pts in enumerate(levels):
        for p in pts:
            for q in sorted(inner[li], key=lambda q: d2(p, q))[:r.randint(1, 2)]:
                out.append('<path d="M%s %sL%s %s" stroke="%s" stroke-width="1"/>' % (_f(p[0]), _f(p[1]), _f(q[0]), _f(q[1]), LINE % ".22"))
    for pts in levels:
        for (x, y) in pts:
            out.append('<circle cx="%s" cy="%s" r="6" fill="%s" stroke="#fff" stroke-width="1.4"/>' % (_f(x), _f(y), BG))
    p = r.choice(levels[2])
    path = [p]
    for li in (1, 0):
        p = min(levels[li], key=lambda q: d2(q, p))
        path.append(p)
    path.append((cx, cy))
    out.append('<path d="M%s" stroke="%s" stroke-width="2.6" fill="none"/>' % (" L".join("%s %s" % (_f(x), _f(y)) for x, y in path), AMBER))
    for (x, y) in path[:-1]:
        out.append('<circle cx="%s" cy="%s" r="7" fill="%s"/>' % (_f(x), _f(y), AMBER))
    out.append('<circle cx="%s" cy="%s" r="15" fill="%s" stroke="#fff" stroke-width="1.8"/>' % (_f(cx), _f(cy), BG))
    out.append('<circle cx="%s" cy="%s" r="5" fill="#fff"/>' % (_f(cx), _f(cy)))
    return out


def _governance_ledger(r):
    """A review ledger: checked rows, one open item highlighted, a sign-off line."""
    rows = r.randint(6, 8)
    x0, x1 = W * .2, W * .82
    rh = r.uniform(50, 58)
    y0 = (H - rows * rh) / 2 - 14
    hi = r.randint(1, rows - 2)
    out = ['<rect x="%s" y="%s" width="%s" height="%s" fill="rgba(227,154,61,.09)"/>' % (_f(x0), _f(y0 + hi * rh), _f(x1 - x0), _f(rh))]
    for i in range(rows + 1):
        edge = i in (0, rows)
        out.append('<path d="M%s %sH%s" stroke="%s" stroke-width="%s"/>' % (_f(x0), _f(y0 + i * rh), _f(x1), LINE % (".5" if edge else ".16"), "1.3" if edge else "1"))
    for xv in (x0 + 68, x1 - 150):
        out.append('<path d="M%s %sV%s" stroke="%s" stroke-width="1"/>' % (_f(xv), _f(y0), _f(y0 + rows * rh), LINE % ".14"))
    for i in range(rows):
        cy = y0 + i * rh + rh / 2
        box = AMBER if i == hi else LINE % ".6"
        out.append('<rect x="%s" y="%s" width="18" height="18" fill="none" stroke="%s" stroke-width="1.5"/>' % (_f(x0 + 25), _f(cy - 9), box))
        if i != hi and r.random() < .75:
            out.append('<path d="M%s %sl5 5l9 -10" stroke="#fff" stroke-width="1.8" fill="none"/>' % (_f(x0 + 29), _f(cy)))
        w = (x1 - x0 - 260) * r.uniform(.35, .85)
        out.append('<rect x="%s" y="%s" width="%s" height="4" fill="%s"/>' % (_f(x0 + 92), _f(cy - 6), _f(w), LINE % (".6" if i == hi else ".34")))
        out.append('<rect x="%s" y="%s" width="%s" height="3" fill="%s"/>' % (_f(x0 + 92), _f(cy + 5), _f(w * r.uniform(.4, .7)), LINE % ".16"))
        out.append('<rect x="%s" y="%s" width="%s" height="4" fill="%s"/>' % (_f(x1 - 128), _f(cy - 2), _f(r.uniform(50, 104)), LINE % ".28"))
    out.append('<path d="M%s %sH%s" stroke="%s" stroke-width="2"/>' % (_f(x0 - 70), _f(y0 + hi * rh + rh / 2), _f(x0), AMBER))
    sy = y0 + rows * rh + 52
    out.append('<path d="M%s %sH%s" stroke="%s" stroke-width="1.3"/>' % (_f(x1 - 280), _f(sy), _f(x1), LINE % ".55"))
    out.append('<rect x="%s" y="%s" width="10" height="10" fill="%s"/>' % (_f(x1 - 290), _f(sy - 5), AMBER))
    return out


def _continuity_timeline(r):
    """Service level over time: an outage, then an amber recovery back to baseline inside a target window."""
    x0, x1 = W * .1, W * .9
    base, floor = H * r.uniform(.34, .42), H * .7
    t_out = x0 + (x1 - x0) * r.uniform(.26, .36)
    t_low = t_out + r.uniform(60, 120)
    t_back = t_low + r.uniform(170, 280)
    axis = floor + 34
    out = []
    n = 12
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        out.append('<path d="M%s %sV%s" stroke="%s" stroke-width="1" stroke-dasharray="2 7"/>' % (_f(x), _f(base - 70), _f(axis), LINE % ".1"))
        out.append('<path d="M%s %sv10" stroke="%s" stroke-width="1.2"/>' % (_f(x), _f(axis), LINE % ".55"))
    out.append('<path d="M%s %sH%s" stroke="%s" stroke-width="1.3"/>' % (_f(x0), _f(axis), _f(x1), LINE % ".5"))
    out.append('<path d="M%s %sH%s" stroke="%s" stroke-width="1" stroke-dasharray="6 8"/>' % (_f(x0), _f(base), _f(x1), LINE % ".26"))
    out.append('<path d="M%s %sH%sL%s %sH%s" stroke="%s" stroke-width="1.8" fill="none"/>'
               % (_f(x0), _f(base), _f(t_out), _f(t_out + 16), _f(floor), _f(t_low), LINE % ".78"))
    mid = (t_low + t_back) / 2
    out.append('<path d="M%s %sC%s %s %s %s %s %s" stroke="%s" stroke-width="3" fill="none"/>'
               % (_f(t_low), _f(floor), _f(mid), _f(floor), _f(mid), _f(base), _f(t_back), _f(base), AMBER))
    out.append('<path d="M%s %sH%s" stroke="%s" stroke-width="1.8"/>' % (_f(t_back), _f(base), _f(x1), LINE % ".78"))
    rto = t_back - t_out + r.uniform(30, 90)
    out.append('<path d="M%s %sv-10H%sv10" stroke="%s" stroke-width="1.3" fill="none"/>' % (_f(t_out), _f(axis + 52), _f(t_out + rto), LINE % ".6"))
    out.append('<rect x="%s" y="%s" width="10" height="10" fill="%s"/>' % (_f(t_back - 5), _f(axis - 5), AMBER))
    return out


# Each category has two or three compositions; orientation-neutral ones may also be mirrored. Time and growth
# motifs (roadmaps, curves, timelines, ledgers) are never mirrored, so they always read left to right.
MOTIFS = {
    "Cybersecurity & Risk": [_security, _security_zones],
    "Artificial Intelligence & Automation": [_ai, _ai_radial],
    "Technology Leadership": [_leadership, _leadership_lanes, _leadership_curve],
    "Cloud & Infrastructure": [_cloud],
    "Governance & Compliance": [_governance, _governance_ledger],
    "Business Continuity": [_continuity, _continuity_timeline],
    "Industry Perspectives": [_industry],
}
MIRRORABLE = {_security, _security_zones, _ai, _ai_radial, _governance, _cloud, _continuity, _industry}


def art_svg(slug, category, label=None):
    r = _rng(slug)
    variants = MOTIFS.get(category, MOTIFS["Technology Leadership"])
    motif = variants[r.randrange(len(variants))]
    mirror = motif in MIRRORABLE and r.random() < .5
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" role="img" aria-label="%s">' % (W, H, (label or "Illustration for the article").replace('"', "'")),
             '<rect width="%d" height="%d" fill="%s"/>' % (W, H, BG), _grid()]
    for (x, y) in [(28, 28), (W - 28, 28), (28, H - 28), (W - 28, H - 28)]:
        parts.append('<path d="M%d %dh16M%d %dv16" stroke="%s" stroke-width="1"/>' % (x - 8, y, x, y - 8, LINE % ".3"))
    body = motif(r)
    if mirror:
        body = ['<g transform="translate(%d 0) scale(-1 1)">' % W] + body + ["</g>"]
    parts += body
    parts.append("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    sys.stdout.write(art_svg(sys.argv[1], sys.argv[2]))
