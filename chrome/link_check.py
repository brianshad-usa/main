#!/usr/bin/env python3
"""
chrome/link_check.py -- internal links, fragments, assets and redirects across the whole site (staging QA).

    python chrome/link_check.py            # report; exit 1 when a link, fragment or asset does not resolve

Resolves extensionless URLs the way Cloudflare Pages does (/x -> x.html or x/index.html), follows _redirects, and
checks that "#fragment" ids exist in the target page. External links are not fetched here.
"""
import glob
import html
import os
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", ".github", "chrome", "editorial", "functions", "node_modules", "tools", "apps", "videos"}
PLATFORM = ("/api/", "/cdn-cgi/")


def pages():
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if f.endswith(".html"):
                yield os.path.relpath(os.path.join(dp, f), ROOT).replace("\\", "/")


def load_redirects():
    out = {}
    p = os.path.join(ROOT, "_redirects")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            parts = line.split("#")[0].split()
            if len(parts) >= 2 and parts[0].startswith("/"):
                out[parts[0]] = parts[1]
    return out


def main():
    allpages = sorted(pages())
    redirects = load_redirects()
    files = {os.path.relpath(p, ROOT).replace("\\", "/") for p in glob.glob(os.path.join(ROOT, "**", "*"), recursive=True) if os.path.isfile(p)}
    ids, cache = {}, {}

    def text(page):
        if page not in cache:
            cache[page] = open(os.path.join(ROOT, page), encoding="utf-8", errors="replace").read()
        return cache[page]

    def target(path):
        """Page or asset file for a site path, or None."""
        path = unquote(path)
        if path in ("", "/"):
            return "index.html"
        rel = path.strip("/")
        for cand in (rel, rel + ".html", rel + "/index.html", rel.rstrip("/") + ".html"):
            if cand in files:
                return cand
        return None

    broken, frag, redirected, checked = [], [], [], 0
    for page in allpages:
        t = text(page)
        found = set(re.findall(r'(?:href|src)="([^"#?][^"]*)"', t)) | set(re.findall(r'href="(#[^"]+)"', t))
        for raw in found:
            u = html.unescape(raw)
            if re.match(r"^(?:mailto:|tel:|sms:|javascript:|data:|#$)", u):
                continue
            sp = urlsplit(u)
            if sp.scheme in ("http", "https") and sp.netloc not in ("prolinksystems.com", "www.prolinksystems.com"):
                continue
            if sp.scheme in ("http", "https"):
                path = sp.path or "/"
            elif u.startswith("#"):
                path = "/" + page[:-5] if not page.endswith("index.html") else "/" + page[:-10]
            elif u.startswith("/"):
                path = sp.path
            else:
                path = "/" + os.path.normpath(os.path.join(os.path.dirname(page), sp.path)).replace("\\", "/")
            checked += 1
            if any(path.startswith(x) for x in PLATFORM):
                continue
            tg = page if u.startswith("#") else target(path)
            if tg is None:
                exact = path.rstrip("/") or "/"
                hop = redirects.get(exact) or redirects.get(exact + "/")
                star = next((v for k, v in redirects.items() if k.endswith("*") and path.startswith(k[:-1])), None)
                if hop or star:
                    redirected.append((page, u, hop or star))
                else:
                    broken.append((page, u))
                continue
            if sp.fragment and tg.endswith(".html"):
                if tg not in ids:
                    ids[tg] = set(re.findall(r'\bid="([^"]+)"', text(tg))) | set(re.findall(r'<a name="([^"]+)"', text(tg)))
                if sp.fragment not in ids[tg]:
                    frag.append((page, u))
    print("pages %d, internal references %d" % (len(allpages), checked))
    for label, items in (("broken", broken), ("missing fragment", frag), ("goes through a redirect", redirected)):
        print("%s: %d" % (label, len(items)))
        for it in items[:25]:
            print("   ", *it)
    if broken or frag:
        sys.exit(1)


if __name__ == "__main__":
    main()
