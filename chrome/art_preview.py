#!/usr/bin/env python3
"""
chrome/art_preview.py -- render illustration scenes to a PNG contact sheet for review (iteration 4).

    python chrome/art_preview.py --out C:/some/dir  [slug ...]        # no slugs = every registered scene
    python chrome/art_preview.py --out DIR --list FILE                # one slug per line

Uses headless Chrome or Edge (already installed). Writes sheet-01.png, sheet-02.png ... (12 scenes per sheet)
and, with one or two slugs, a large single render of each. Checks each scene: parses as XML, contains exactly
one amber focal idea (warning only), no text/image/script elements, and size under 12 KB.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import art_scenes    # noqa: E402
import insight_art   # noqa: E402

art_scenes.load()
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]


def check(slug, svg):
    warn = []
    try:
        ET.fromstring(svg)
    except ET.ParseError as e:
        return ["INVALID XML: %s" % e]
    if len(svg.encode()) > 12000:
        warn.append("%d bytes (aim < 12000)" % len(svg.encode()))
    for bad in ("<text", "<image", "<script", "<foreignObject", "href=", "url(", "filter"):
        if bad in svg:
            warn.append("contains %s" % bad)
    if svg.count("rgba(227,154,61") + svg.count("#e39a3d") == 0:
        warn.append("no amber focal element")
    return warn


def shoot(html_path, png_path, w, h):
    exe = next(b for b in BROWSERS if os.path.exists(b))
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
                        "--force-device-scale-factor=1", "--user-data-dir=" + prof,
                        "--screenshot=" + png_path, "--window-size=%d,%d" % (w, h), "file:///" + html_path.replace("\\", "/")],
                       check=False, timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--list")
    ap.add_argument("slugs", nargs="*")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    slugs = a.slugs or (open(a.list, encoding="utf-8").read().split() if a.list else sorted(art_scenes.SCENES))
    bad = 0
    svgs = []
    for s in slugs:
        if s not in art_scenes.SCENES:
            print("MISSING scene:", s)
            bad += 1
            continue
        svg = insight_art.scene_svg(s)
        w = check(s, svg)
        if w:
            print(s, "->", "; ".join(w))
            bad += any(x.startswith("INVALID") for x in w)
        svgs.append((s, svg))
    single = len(svgs) <= 2
    per = 2 if single else 12
    for k in range(0, len(svgs), per):
        chunk = svgs[k:k + per]
        cells = "".join('<div class="c"><div class="t">%s</div>%s</div>' % (re.sub(r"^\d{4}-\d\d-\d\d-", "", s)[:46], svg) for s, svg in chunk)
        html = ('<!doctype html><meta charset="utf-8"><style>body{margin:0;background:#223;font:11px sans-serif;color:#9ab}'
                '.g{display:grid;grid-template-columns:repeat(%d,1fr);gap:14px;padding:14px}.c svg{width:100%%;height:auto;display:block}'
                '.t{margin:0 0 4px}</style><div class="g">%s</div>' % (1 if single else 3, cells))
        hp = os.path.join(a.out, "sheet-%02d.html" % (k // per + 1))
        open(hp, "w", encoding="utf-8").write(html)
        rows = -(-len(chunk) // (1 if single else 3))
        shoot(hp, os.path.join(a.out, "sheet-%02d.png" % (k // per + 1)), 1180 if single else 1230, (rows * 690 + 20) if single else (rows * 320 + 20))
    print("rendered %d scene(s) to %s; %d problem(s)" % (len(svgs), a.out, bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
