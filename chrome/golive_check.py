#!/usr/bin/env python3
"""
chrome/golive_check.py -- run before the redesign-2026 branch is proposed for production (see CONVENTIONS
"Redesign 2026"). Exit 0 only when every check passes. It changes nothing.

  python chrome/golive_check.py

Checks:
  1. no staging review markers left (class="pl-flag") in any page;
  2. the staging guard functions/_middleware.js has been deleted;
  3. the header/footer partials are current on every page (apply_chrome.py --check);
  4. every page links _shared.css with one shared ?v= that differs from production main's;
  5. the page generators emit the new header/footer markers (generate_blog.py, gen_location_pages.py,
     update_site_links.py), so new posts and city pages are born in the new design.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", ".github", "chrome", "editorial", "functions", "node_modules", "tools", "apps", "videos"}
problems = []


def pages():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for n in filenames:
            if n.endswith(".html"):
                yield os.path.join(dirpath, n)


versions = set()
for p in pages():
    rel = os.path.relpath(p, ROOT)
    t = open(p, encoding="utf-8").read()
    if 'class="pl-flag"' in t:
        problems.append("1 review marker left: " + rel)
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
        prod = subprocess.run(["git", "-C", ROOT, "show", "origin/main:index.html"], capture_output=True, text=True, encoding="utf-8").stdout
        pv = re.findall(r'_shared\.css\?v=([^"]+)"', prod)
        if pv and pv[0] in versions:
            problems.append("4 _shared.css?v=%s is the same as production; run bump_shared_css.py" % pv[0])
    except Exception as e:  # no git / no origin: report, do not pass silently
        problems.append("4 could not compare with origin/main: %s" % e)

for gen in ("generate_blog.py", "gen_location_pages.py", "update_site_links.py"):
    path = os.path.join(ROOT, gen)
    if os.path.exists(path) and "PL:HEADER" not in open(path, encoding="utf-8").read():
        problems.append("5 %s does not emit the new header/footer markers yet" % gen)

if problems:
    print("NOT READY for go-live:\n  " + "\n  ".join(problems))
    sys.exit(1)
print("Ready: all go-live checks passed (still needs Brian's explicit approval to merge).")
