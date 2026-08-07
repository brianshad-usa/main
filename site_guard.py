#!/usr/bin/env python3
"""
site_guard.py -- whole-site source validator for prolinksystems.com.

Enforces the checkable invariants in CONVENTIONS.md. Exits non-zero with a
file-by-file report on any violation, so CI (and the blog generator) refuse to
publish content that breaks a site-wide rule.

Usage:
  python site_guard.py                 # validate; exit 1 if any violation
  python site_guard.py --fix-report    # report only (advisory), always exit 0

Only dependency beyond the stdlib is beautifulsoup4.

Interpretations (documented so they can be calibrated, not silently changed):
  * Per-page checks 1-10 run on every .html EXCEPT 404.html and thank-you.html
    (the two utility pages named in the spec's per-page group). 404.html is
    covered by check 14; both are exempt from the sitemap presence check (11).
  * Meta-description and title length are measured on the RENDERED text
    (HTML entities decoded) -- i.e. what Google counts -- not the raw attribute.
"""
import sys
import os
import re
import json
import glob
import html as _html

from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.abspath(__file__))
APEX = "https://prolinksystems.com"
PER_PAGE_EXEMPT = {"404.html", "thank-you.html"}       # spec: per-page group
SITEMAP_EXEMPT = {"404.html", "thank-you.html"}        # spec: check 11

violations = []  # (check_num, path, detail)


def V(num, path, detail):
    violations.append((num, path, detail))


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def meta_desc(soup):
    m = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    return (m.get("content", "").strip() if m else "")


def is_noindex(soup):
    m = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    return bool(m and "noindex" in m.get("content", "").lower())


def canonical_href(soup):
    for l in soup.find_all("link"):
        rels = [r.lower() for r in (l.get("rel") or [])]
        if "canonical" in rels:
            return (l.get("href") or "").strip()
    return None


def url_to_file(u):
    """Map a sitemap <loc> to the repo-relative file it should serve."""
    path = u.strip()
    for pre in ("https://prolinksystems.com", "http://prolinksystems.com",
                "https://www.prolinksystems.com"):
        if path.startswith(pre):
            path = path[len(pre):]
            break
    path = path.split("?")[0].split("#")[0]
    if path in ("", "/"):
        return "index.html"
    path = path.lstrip("/").rstrip("/")
    return path if path.endswith(".html") else path + ".html"


def page_url(name):
    """The canonical URL a repo file is expected to appear as in the sitemap."""
    if name == "index.html":
        return APEX + "/"
    if name.startswith("blog/"):
        return f"{APEX}/{name}"          # blog canonicalizes WITH .html
    return f"{APEX}/{name[:-5]}"          # root pages use clean URLs


# --------------------------------------------------------------------------- #
# Parse every page once
# --------------------------------------------------------------------------- #
all_html = sorted(glob.glob(os.path.join(ROOT, "*.html"))) + \
           sorted(glob.glob(os.path.join(ROOT, "blog", "*.html")))
pages = {}  # name -> {src, soup, noindex, desc}
for p in all_html:
    src = read(p)
    soup = BeautifulSoup(src, "html.parser")
    pages[rel(p)] = {"src": src, "soup": soup,
                     "noindex": is_noindex(soup), "desc": meta_desc(soup)}

# --------------------------------------------------------------------------- #
# Per-page checks (1-10)
# --------------------------------------------------------------------------- #
desc_index = {}  # rendered desc -> [pages]  (check 16)
for name, pg in pages.items():
    base = os.path.basename(name)
    if base in PER_PAGE_EXEMPT:
        continue
    soup, src, noindex = pg["soup"], pg["src"], pg["noindex"]

    # 1: meta description present + <=160 rendered chars (skip noindexed)
    if not noindex:
        if not pg["desc"]:
            V(1, name, "meta description missing")
        else:
            dlen = len(_html.unescape(pg["desc"]))
            if dlen > 160:
                V(1, name, f"meta description {dlen} chars (>160)")
    if pg["desc"]:
        desc_index.setdefault(_html.unescape(pg["desc"]), []).append(name)

    # 2: title present + <=60 rendered chars
    t = soup.find("title")
    ttext = t.get_text() if t else ""
    if not ttext.strip():
        V(2, name, "title missing")
    else:
        tlen = len(_html.unescape(ttext))
        if tlen > 60:
            V(2, name, f"title {tlen} chars (>60): {ttext.strip()[:70]!r}")

    # 3: exactly one <h1>
    h1s = soup.find_all("h1")
    if len(h1s) != 1:
        V(3, name, f"{len(h1s)} <h1> tags (must be exactly 1)")

    # 4: heading levels never skip downward
    prev = None
    for h in soup.find_all(re.compile(r"^h[1-6]$")):
        lvl = int(h.name[1])
        if prev is not None and lvl > prev + 1:
            V(4, name, f"heading level skips H{prev} -> H{lvl}")
            break
        prev = lvl

    # 5: canonical present + apex (no www)   [404 already exempt above]
    can = canonical_href(soup)
    if not can:
        V(5, name, "canonical missing")
    elif not can.startswith(APEX):
        V(5, name, f"canonical not apex: {can}")
    elif "www.prolinksystems.com" in can:
        V(5, name, f"canonical uses www: {can}")

    # 6: no www.prolinksystems.com in any internal href
    seen_www = set()
    for tag in soup.find_all(href=True):
        h = tag["href"]
        if "www.prolinksystems.com" in h and h not in seen_www:
            seen_www.add(h)
            V(6, name, f"www in href: {h}")

    # 7: no malformed heading tags (raw source)
    for pat in (r"<hh", r"</hh", r"<h\d\d", r"</h\d\d"):
        if re.search(pat, src, re.I):
            V(7, name, f"malformed heading tag matching /{pat}/")

    # 8 + 9: JSON-LD valid + ServiceChannel.servicePhone is a ContactPoint
    for i, s in enumerate(soup.find_all("script",
                                        attrs={"type": "application/ld+json"})):
        raw = s.string if s.string is not None else s.get_text()
        try:
            data = json.loads(raw)
        except Exception as e:
            V(8, name, f"JSON-LD block #{i} invalid JSON: {e}")
            continue

        def walk(obj):
            if isinstance(obj, dict):
                if obj.get("@type") == "ServiceChannel":
                    sp = obj.get("servicePhone")
                    if not (isinstance(sp, dict) and sp.get("@type") == "ContactPoint"):
                        V(9, name, f"ServiceChannel.servicePhone is not a "
                                   f"ContactPoint object (got {type(sp).__name__})")
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)
        walk(data)

    # 10: every <img> has non-empty alt
    for img in soup.find_all("img"):
        if not (img.get("alt") and img.get("alt").strip()):
            V(10, name, f"<img> missing alt (src={img.get('src', '?')})")

# --------------------------------------------------------------------------- #
# Cross-file checks (11-16)
# --------------------------------------------------------------------------- #
# 11: sitemap integrity
sm_path = os.path.join(ROOT, "sitemap.xml")
if not os.path.exists(sm_path):
    V(11, "sitemap.xml", "missing")
else:
    locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", read(sm_path))
    sitemap_files = set()
    for u in locs:
        f = url_to_file(u)
        sitemap_files.add(f)
        if not os.path.exists(os.path.join(ROOT, f)):
            V(11, "sitemap.xml", f"URL maps to a missing file: {u} -> {f}")
        elif f in pages and pages[f]["noindex"]:
            V(11, "sitemap.xml", f"noindexed page present in sitemap: {u}")
    for name, pg in pages.items():
        if os.path.basename(name) in SITEMAP_EXEMPT or pg["noindex"]:
            continue
        if name not in sitemap_files:
            V(11, name, f"indexable page missing from sitemap (expected {page_url(name)})")

# 12: _redirects -- no hostname rules, >=40 path rules
rd_path = os.path.join(ROOT, "_redirects")
if not os.path.exists(rd_path):
    V(12, "_redirects", "missing")
else:
    lines = read(rd_path).splitlines()
    for l in lines:
        if l.strip().startswith("http"):
            V(12, "_redirects", f"hostname-based rule (starts with http): {l.strip()}")
    rules = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    if len(rules) < 40:
        V(12, "_redirects", f"only {len(rules)} path rules (<40 -- possible wipe)")

# 13: _headers exists + HSTS
hd_path = os.path.join(ROOT, "_headers")
if not os.path.exists(hd_path):
    V(13, "_headers", "missing")
elif "Strict-Transport-Security" not in read(hd_path):
    V(13, "_headers", "missing Strict-Transport-Security")

# 14: 404.html exists + noindex
f404 = os.path.join(ROOT, "404.html")
if not os.path.exists(f404):
    V(14, "404.html", "missing")
elif "noindex" not in read(f404).lower():
    V(14, "404.html", "missing noindex")

# 15: robots.txt disallows /cdn-cgi/
rob = os.path.join(ROOT, "robots.txt")
if not os.path.exists(rob):
    V(15, "robots.txt", "missing")
elif "Disallow: /cdn-cgi/" not in read(rob):
    V(15, "robots.txt", "missing 'Disallow: /cdn-cgi/'")

# 16: no two pages share an identical meta description
for desc, pgs in desc_index.items():
    if len(pgs) > 1:
        V(16, pgs[0], f"identical meta description shared with "
                      f"{', '.join(pgs[1:])}: {desc[:70]!r}")

# --------------------------------------------------------------------------- #
# 17: secrets scan (all text files)
# --------------------------------------------------------------------------- #
SECRET_PATS = [
    ("Google OAuth client secret", re.compile(r"GOCSPX-[A-Za-z0-9_-]{20,}")),
    ("Anthropic API key",          re.compile(r"sk-ant-[A-Za-z0-9-]{20,}")),
    ("Google refresh token",       re.compile(r"1//0[A-Za-z0-9_-]{30,}")),
]
ASSIGN = re.compile(
    r"(client_secret|AZURE_CLIENT_SECRET|ANTHROPIC_API_KEY)"
    r"['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9~._+/-]{30,})", re.I)
PLACEHOLDER = re.compile(
    r"(PASTE|YOUR[_-]|XXXX|EXAMPLE|CHANGE|REPLACE|_HERE|PLACEHOLDER|\$\{|<[^>]+>|"
    r"secrets\.|env\.|process\.env|os\.environ|getenv)", re.I)
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".svg", ".mp4",
            ".mov", ".woff", ".woff2", ".ttf", ".otf", ".eot", ".pyc", ".zip",
            ".pdf", ".lock"}
GUARD = os.path.basename(__file__)

for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
    for fn in filenames:
        if os.path.splitext(fn)[1].lower() in SKIP_EXT or fn == GUARD:
            continue
        fp = os.path.join(dirpath, fn)
        try:
            text = open(fp, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        r = rel(fp)
        for label, pat in SECRET_PATS:
            if pat.search(text):
                V(17, r, f"possible {label} (matched /{pat.pattern}/)")
        for m in ASSIGN.finditer(text):
            key, val = m.group(1), m.group(2)
            if not PLACEHOLDER.search(val):
                V(17, r, f"possible {key} literal (value starts {val[:6]}...)")

# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
advisory = "--fix-report" in sys.argv[1:]
violations.sort(key=lambda v: (v[0], v[1]))
for num, path, detail in violations:
    print(f"VIOLATION [{num}] {path}: {detail}")

n = len(violations)
if n:
    by = {}
    for num, _, _ in violations:
        by[num] = by.get(num, 0) + 1
    print(f"\n{n} violation(s) across {len({v[1] for v in violations})} file(s); "
          f"by check: " + ", ".join(f"[{k}]={by[k]}" for k in sorted(by)))
else:
    print(f"OK: {len(all_html)} HTML pages + cross-file checks passed, no violations.")

sys.exit(0 if advisory or n == 0 else 1)
