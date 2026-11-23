#!/usr/bin/env python3
"""
chrome/golive_check.py -- run before the redesign-2026 branch is proposed for production (see CONVENTIONS
"Redesign 2026"). Exit 0 only when every check passes. It changes nothing.

  python chrome/golive_check.py            # every check
  python chrome/golive_check.py --seo      # only the cutover SEO checks (11-14), usable on staging today

Checks:
  1. no staging review markers left (class="pl-flag") in any page;
  2. the staging guard functions/_middleware.js has been deleted;
  3. the header/footer partials are current on every page (apply_chrome.py --check);
  4. every page links _shared.css with one shared ?v= that differs from production main's;
  5. the page generators emit the new header/footer markers (generate_blog.py, gen_location_pages.py,
     update_site_links.py), so new posts and city pages are born in the new design;
  6-7. homepage and typography are settled (see the code);
  9. company name, Insights registry, internal links, form labels and wording checks pass;
  10. the client portfolio matches its data and carries the owner's final approval of names and logos;
  11. robots: exactly one robots meta tag per page; indexable pages carry a canonical equal to their own production
      URL (https://prolinksystems.com/<path>, no .html), and every canonical points to a page that exists;
  12. sitemap.xml lists only final production URLs: each exists without a redirect, is indexable and is its own
      canonical; indexable pages missing from the sitemap are listed too;
  13. every production URL (origin/main pages, sitemap and _redirects sources) still resolves on this branch,
      directly or through exactly one redirect (Cloudflare Pages rules: _redirects first, then .html and
      trailing-slash normalization, each a hop); and _redirects keeps every static rule above the first dynamic
      (splat/placeholder) rule, within Cloudflare's 2,000 static / 100 dynamic / 1,000-character limits (with
      dynamic rules mixed in higher up, Cloudflare silently ignored everything after rule 100);
  14. no staging labels in static files ("STAGING", the "Design review" panel, *.pages.dev preview links).
(8, the CR&R hold, was retired on 2026-11-22: Brian approved CR&R for the portfolio and its own case study.)
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://prolinksystems.com"
SKIP_DIRS = {".git", ".github", "chrome", "editorial", "functions", "node_modules", "tools", "apps", "videos"}
problems = []
SEO_ONLY = "--seo" in sys.argv


def pages():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for n in filenames:
            if n.endswith(".html"):
                yield os.path.join(dirpath, n)


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def read(p):
    return open(p, encoding="utf-8").read()


def url_of(relpath):
    """Production URL path of a page file (Cloudflare Pages pretty URLs)."""
    if relpath == "index.html":
        return "/"
    if relpath.endswith("/index.html"):
        return "/" + relpath[:-len("index.html")]
    return "/" + relpath[:-len(".html")]


def git_show(spec):
    r = subprocess.run(["git", "-C", ROOT, "show", spec], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("git show %s failed: %s" % (spec, r.stderr.strip()[:200]))
    return r.stdout


def redirect_rules(text):
    rules = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            rules.append((parts[0], parts[1], parts[2] if len(parts) > 2 else "302"))
    return rules


def rule_regex(src):
    out = ""
    for tok in re.split(r"(\*|:[A-Za-z]\w*)", src):
        if tok == "*":
            out += "(?P<splat>.*)"
        elif tok.startswith(":") and len(tok) > 1:
            out += "(?P<%s>[^/]+)" % tok[1:]
        else:
            out += re.escape(tok)
    return re.compile("^" + out + "/?$")


class Site:
    """Resolves a URL path on the working tree the way Cloudflare Pages would (static files + _redirects)."""
    def __init__(self, files, redirects_text):
        self.files = files
        self.rules = [(rule_regex(s), s, t, c) for s, t, c in redirect_rules(redirects_text)]

    def redirect(self, path):
        for rx, src, target, code in self.rules:
            m = rx.match(path)
            if m:
                for k, v in m.groupdict().items():
                    target = target.replace(":" + k, v or "")
                return target, code
        return None

    def static(self, path):
        """(served path, extra hops) for a static page, or None when nothing is served."""
        f = self.files
        if path == "/":
            return ("/", 0) if "index.html" in f else None
        p = path.lstrip("/")
        if p.endswith(".html"):
            clean = "/" + p[:-5]
            if clean.endswith("/index"):
                clean = clean[:-5]
            return (clean, 1) if p in f else None
        if p.endswith("/"):
            if p + "index.html" in f:
                return (path, 0)
            if p[:-1] + ".html" in f:
                return ("/" + p[:-1], 1)
            return None
        if p + ".html" in f:
            return (path, 0)
        if p + "/index.html" in f:
            return (path + "/", 1)
        if p in f:                       # non-HTML asset (xml, txt, pdf ...)
            return (path, 0)
        return None

    def resolve(self, path, budget=3):
        """Returns (final path or external URL, hops) or (None, hops) when it ends in a 404."""
        hops = 0
        for _ in range(budget):
            r = self.redirect(path)
            if r:
                target = r[0]
                hops += 1
                if target.startswith("http"):
                    if target.startswith(SITE):
                        path = target[len(SITE):] or "/"
                        continue
                    return target, hops
                path = target
                continue
            s = self.static(path)
            if s is None:
                return None, hops
            served, extra = s
            if extra:
                hops += extra
                path = served
                continue
            return served, hops
        return None, hops


def branch_files():
    out = set()
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules"}]
        for n in filenames:
            out.add(rel(os.path.join(dirpath, n)))
    return out


def robots_of(t):
    head = t[:t.find("</head>")] if "</head>" in t else t
    return re.findall(r'<meta\s+name="robots"\s+content="([^"]*)"', head, re.I)


def canonical_of(t):
    m = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', t, re.I)
    return m.group(1) if m else None


def indexable(t):
    r = robots_of(t)
    return not r or "noindex" not in r[0].replace(" ", "").lower()


# ---------------------------------------------------------------- 1-10: design, content and process checks
if not SEO_ONLY:
    versions = set()
    for p in pages():
        t = read(p)
        if 'class="pl-flag"' in t:
            problems.append("1 review marker left: " + rel(p))
        versions.update(re.findall(r'_shared\.css\?v=([^"]+)"', t))

    if os.path.exists(os.path.join(ROOT, "functions", "_middleware.js")):
        problems.append("2 functions/_middleware.js (staging guard) still present")

    r = subprocess.run([sys.executable, os.path.join(ROOT, "chrome", "apply_chrome.py"), "--check"], capture_output=True, text=True)
    if r.returncode != 0:
        problems.append("3 header/footer out of date: run python chrome/apply_chrome.py")

    if len(versions) != 1:
        problems.append("4 _shared.css is linked with %d different ?v= values: %s" % (len(versions), sorted(versions)))
    else:
        try:
            pv = re.findall(r'_shared\.css\?v=([^"]+)"', git_show("origin/main:index.html"))
            if pv and pv[0] in versions:
                problems.append("4 _shared.css?v=%s is the same as production; run bump_shared_css.py" % pv[0])
        except Exception as e:  # no git / no origin: report, do not pass silently
            problems.append("4 could not compare with origin/main: %s" % e)

    home = read(os.path.join(ROOT, "index.html"))
    if "data-hero=" in home:
        problems.append("6 homepage still carries both hero visuals (data-hero): keep the chosen one, delete the other")
    if '[data-type="sans"]' in read(os.path.join(ROOT, "_shared.css")):
        problems.append("7 _shared.css still has both typography options: make the chosen one the default, remove the other + its font")

    clients = json.load(open(os.path.join(ROOT, "editorial", "clients.json"), encoding="utf-8"))
    if not clients.get("approved"):
        problems.append("10 client portfolio: Brian's final approval of client names and logos is not recorded (editorial/clients.json: approved)")
    for script, what in (("company_name.py", "the company is always Pro Link Systems"), ("clients.py", "client portfolio order, profiles and case study links"),
                         ("insights.py", "Insights registry and assets"), ("link_check.py", "internal links and fragments"),
                         ("form_labels.py", "form labels"), ("refine_wording.py", "corporate wording")):
        args = [sys.executable, os.path.join(ROOT, "chrome", script)] + ([] if script in ("link_check.py",) else ["--check"])
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 and not (script == "company_name.py" and "would change 0 file" in (r.stdout or "")):
            problems.append("9 %s fails (%s)" % (script, what))
    for gen in ("generate_blog.py", "gen_location_pages.py", "update_site_links.py"):
        path = os.path.join(ROOT, gen)
        if os.path.exists(path) and "PL:HEADER" not in read(path):
            problems.append("5 %s does not emit the new header/footer markers yet" % gen)

# ---------------------------------------------------------------- 11-14: cutover SEO checks
files = branch_files()
site = Site(files, read(os.path.join(ROOT, "_redirects")) if os.path.exists(os.path.join(ROOT, "_redirects")) else "")
page_info = {}
for p in pages():
    rp = rel(p)
    t = read(p)
    rb = robots_of(t)
    can = canonical_of(t)
    page_info[url_of(rp)] = (rp, t, can)
    if len(rb) != 1:
        problems.append("11 %s has %d robots meta tags (want exactly 1)" % (rp, len(rb)))
    if rp == "404.html":
        continue
    if indexable(t):
        want = SITE + url_of(rp)
        if can != want:
            problems.append("11 %s is indexable but its canonical is %s (want %s)" % (rp, can, want))
    if can and indexable(t):                     # noindex pages (e.g. the temporarily redirected hub) are exempt
        if not can.startswith(SITE):
            problems.append("11 %s canonical is not a production URL: %s" % (rp, can))
        else:
            final, hops = site.resolve(can[len(SITE):] or "/")
            if final is None or hops:
                problems.append("11 %s canonical %s does not resolve directly (%s after %d hop(s))" % (rp, can, final, hops))

sm = read(os.path.join(ROOT, "sitemap.xml"))
locs = re.findall(r"<loc>([^<]+)</loc>", sm)
seen = set()
for loc in locs:
    if loc in seen:
        problems.append("12 sitemap lists %s twice" % loc)
    seen.add(loc)
    if not loc.startswith(SITE + "/"):
        problems.append("12 sitemap URL is not on %s: %s" % (SITE, loc))
        continue
    path = loc[len(SITE):]
    final, hops = site.resolve(path)
    if final is None or hops:
        problems.append("12 sitemap URL %s does not resolve directly (%s after %d hop(s))" % (loc, final, hops))
        continue
    info = page_info.get(path)
    if info:
        rp, t, can = info
        if not indexable(t):
            problems.append("12 sitemap URL %s is noindex" % loc)
        elif can != loc:
            problems.append("12 sitemap URL %s has canonical %s" % (loc, can))
for path, (rp, t, can) in sorted(page_info.items()):
    if rp != "404.html" and indexable(t) and can == SITE + path and SITE + path not in seen:
        problems.append("12 indexable page missing from sitemap.xml: %s" % (SITE + path))

seen_dynamic = None
n_static = n_dynamic = 0
for i, (src, target, code) in enumerate(redirect_rules(read(os.path.join(ROOT, "_redirects"))), 1):
    if "*" in src or re.search(r":[A-Za-z]", src):
        n_dynamic += 1
        seen_dynamic = seen_dynamic or (i, src)
    else:
        n_static += 1
        if seen_dynamic:
            problems.append("13 _redirects rule %d (%s) is static but comes after dynamic rule %d (%s): keep static rules first"
                            % (i, src, seen_dynamic[0], seen_dynamic[1]))
    if len("%s %s %s" % (src, target, code)) > 1000:
        problems.append("13 _redirects rule %d is longer than 1,000 characters" % i)
if n_static > 2000 or n_dynamic > 100:
    problems.append("13 _redirects has %d static and %d dynamic rules (Cloudflare limit: 2,000 and 100)" % (n_static, n_dynamic))

try:
    r = subprocess.run(["git", "-C", ROOT, "ls-tree", "-r", "--name-only", "origin/main"], capture_output=True, text=True, encoding="utf-8")
    prod_files = [f for f in r.stdout.splitlines() if f.endswith(".html")
                  and f.split("/")[0] not in SKIP_DIRS and not f.startswith(".")]
    inventory = {url_of(f): "page" for f in prod_files}
    for loc in re.findall(r"<loc>([^<]+)</loc>", git_show("origin/main:sitemap.xml")):
        if loc.startswith(SITE):
            inventory.setdefault(loc[len(SITE):] or "/", "sitemap")
    prod_rules = redirect_rules(git_show("origin/main:_redirects"))
    for src, target, code in prod_rules:
        if "*" not in src and ":" not in src:
            inventory.setdefault(src, "redirect source")
    branch_sources = {s for s, _, _ in redirect_rules(read(os.path.join(ROOT, "_redirects")))}
    for src, target, code in prod_rules:
        if ("*" in src or ":" in src) and src not in branch_sources:
            problems.append("13 production wildcard redirect %s -> %s is missing on this branch" % (src, target))
    for path, kind in sorted(inventory.items()):
        final, hops = site.resolve(path)
        if final is None:
            problems.append("13 production URL %s (%s) is a 404 on this branch" % (path, kind))
        elif hops > 1:
            problems.append("13 production URL %s (%s) takes %d hops (want at most 1), ends at %s" % (path, kind, hops, final))
except Exception as e:
    problems.append("13 could not read production main (git): %s" % e)

STAGING_TEXT = re.compile(r">\s*STAGING\s*<|Design review|class=\"plr|\.pages\.dev|redesign-2026")
for f in sorted(files):
    if f.split("/")[0] in SKIP_DIRS or f.startswith(".") or not f.endswith((".html", ".js", ".css", ".xml", ".txt")):
        continue
    src = read(os.path.join(ROOT, f))
    if f.endswith((".css", ".js")):              # code comments may name the branch; only shipped text counts
        src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        src = re.sub(r"(?m)^\s*//.*$", "", src)
    if STAGING_TEXT.search(src):
        problems.append("14 staging label or preview link in %s" % f)

if problems:
    print(("NOT READY for go-live (%d):\n  " % len(problems)) + "\n  ".join(problems))
    sys.exit(1)
print("Ready: all %s checks passed (still needs Brian's explicit approval to merge)." % ("cutover SEO" if SEO_ONLY else "go-live"))
