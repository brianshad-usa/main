#!/usr/bin/env python3
"""
update_site_links.py -- idempotent site-wide sync after adding location pages.

  1. Footer "Areas We Serve" links -> canonical 30-city list (FOOTER_AREAS in
     gen_location_pages.py) in every root .html, every blog post, and the
     blog generator template (generate_blog.py) so new posts don't regress.
     Each file keeps its own <h3> text and href style (root = relative,
     blog/generator = "/"-prefixed).
  2. sitemap.xml  -> add any missing location page (priority 0.85, monthly).
  3. _redirects   -> add ".html -> clean URL" 301 for any location page that
     lacks one (appended directly after the last existing location rule;
     nothing else in the file is touched -- CONVENTIONS: never reorder/wipe).
  4. llms.txt     -> add missing cities under "## Locations Served".
  5. Nearby-areas sections on the Sep-2026 pages -> append new neighbours.

Safe to re-run; every step is a no-op when already in sync.
"""
import os, re, glob, datetime
from gen_location_pages import FOOTER_AREAS

HERE = os.path.dirname(os.path.abspath(__file__))
APEX = "https://prolinksystems.com"
TODAY = datetime.date.today().isoformat()

LOCATION_SLUGS = [s for s, _ in FOOTER_AREAS]
NEW = ["managed-it-services-tarzana", "managed-it-services-agoura-hills",
       "managed-it-services-studio-city", "managed-it-services-north-hollywood",
       "managed-it-services-santa-clarita", "managed-it-services-simi-valley",
       "managed-it-services-downtown-los-angeles", "managed-it-services-west-los-angeles"]

changed = {}


def rw(path, fn):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    out = fn(src)
    if out != src:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(out)
        changed[path] = changed.get(path, 0) + 1
        return True
    return False


# 1) footer areas ----------------------------------------------------------
LINKS_RE = re.compile(r'(<div class="footer-areas-links">\n)(.*?)(\n\s*</div>)', re.S)


def sync_footer(src):
    m = LINKS_RE.search(src)
    if not m:
        return src
    prefix = "/" if 'href="/managed-it-services-' in m.group(2) else ""
    indent = re.match(r"\s*", m.group(2)).group(0) or "      "
    links = "\n".join(f'{indent}<a href="{prefix}{s}">{n}</a>' for s, n in FOOTER_AREAS)
    return src[:m.start(2)] + links + src[m.end(2):]


targets = glob.glob(os.path.join(HERE, "*.html")) + glob.glob(os.path.join(HERE, "blog", "*.html"))
n_footer = sum(rw(p, sync_footer) for p in targets)
n_gen = rw(os.path.join(HERE, "generate_blog.py"), sync_footer)
print(f"[footer] updated {n_footer} html files; generate_blog.py template updated: {bool(n_gen)}")


# 2) sitemap ---------------------------------------------------------------
def sync_sitemap(src):
    missing = [s for s in LOCATION_SLUGS if f"<loc>{APEX}/{s}</loc>" not in src]
    if not missing:
        return src
    entries = "".join(
        f"  <url>\n    <loc>{APEX}/{s}</loc>\n    <lastmod>{TODAY}</lastmod>\n"
        f"    <changefreq>monthly</changefreq>\n    <priority>0.85</priority>\n  </url>\n" for s in missing)
    return src.replace("</urlset>", entries + "</urlset>")


rw(os.path.join(HERE, "sitemap.xml"), sync_sitemap)
print("[sitemap] synced")


# 3) _redirects ------------------------------------------------------------
def sync_redirects(src):
    lines = src.split("\n")
    present = set(re.findall(r"^/([a-z0-9-]+)\.html\s", src, flags=re.M))
    missing = [s for s in LOCATION_SLUGS if s not in present]
    if not missing:
        return src
    last = max(i for i, l in enumerate(lines)
               if re.match(r"^/(managed-it-services-[a-z-]+|it-support-burbank)\.html\s", l))
    width = len("/managed-it-services-downtown-los-angeles.html") + 2
    new = [f"/{s}.html".ljust(width) + f"/{s}".ljust(width - 3) + "301" for s in missing]
    return "\n".join(lines[: last + 1] + new + lines[last + 1:])


rw(os.path.join(HERE, "_redirects"), sync_redirects)
print("[_redirects] synced")


# 4) llms.txt --------------------------------------------------------------
def sync_llms(src):
    missing = [(s, n) for s, n in FOOTER_AREAS if f"({APEX}/{s})" not in src]
    if not missing:
        return src
    add = "".join(f"- [{n}]({APEX}/{s})\n" for s, n in missing)
    # insert at end of "## Locations Served" section (before next "## ")
    i = src.index("## Locations Served")
    j = src.index("\n## ", i + 1)
    return src[:j].rstrip("\n") + "\n" + add + src[j:]


rw(os.path.join(HERE, "llms.txt"), sync_llms)
print("[llms.txt] synced")


# 5) nearby sections on existing pages ------------------------------------
NEARBY_ADD = {
    "managed-it-services-woodland-hills.html": [("managed-it-services-tarzana", "Tarzana")],
    "managed-it-services-los-angeles.html": [("managed-it-services-downtown-los-angeles", "Downtown LA"),
                                             ("managed-it-services-west-los-angeles", "West Los Angeles")],
    "managed-it-services-santa-monica.html": [("managed-it-services-west-los-angeles", "West Los Angeles")],
    "managed-it-services-beverly-hills.html": [("managed-it-services-west-los-angeles", "West Los Angeles")],
    "managed-it-services-pasadena.html": [("managed-it-services-downtown-los-angeles", "Downtown LA")],
    "managed-it-services-glendale.html": [("managed-it-services-north-hollywood", "North Hollywood")],
    # batch 2 (2026-10-08)
    "managed-it-services-santa-monica.html": [("managed-it-services-west-los-angeles", "West Los Angeles"),
                                              ("managed-it-services-malibu", "Malibu"),
                                              ("managed-it-services-playa-vista", "Playa Vista")],
    "managed-it-services-beverly-hills.html": [("managed-it-services-west-los-angeles", "West Los Angeles"),
                                               ("managed-it-services-hollywood", "Hollywood")],
    "managed-it-services-los-angeles.html": [("managed-it-services-downtown-los-angeles", "Downtown LA"),
                                             ("managed-it-services-west-los-angeles", "West Los Angeles"),
                                             ("managed-it-services-hollywood", "Hollywood"),
                                             ("managed-it-services-koreatown", "Koreatown")],
    "managed-it-services-pasadena.html": [("managed-it-services-downtown-los-angeles", "Downtown LA"),
                                          ("managed-it-services-san-gabriel-valley", "San Gabriel Valley")],
    "managed-it-services-west-los-angeles.html": [("managed-it-services-playa-vista", "Playa Vista")],
    "managed-it-services-downtown-los-angeles.html": [("managed-it-services-koreatown", "Koreatown")],
    "managed-it-services-north-hollywood.html": [("managed-it-services-sun-valley", "Sun Valley")],
    "managed-it-services-agoura-hills.html": [("managed-it-services-malibu", "Malibu"), ("managed-it-services-camarillo", "Camarillo")],
    "managed-it-services-simi-valley.html": [("managed-it-services-camarillo", "Camarillo")],
}
NB_RE = re.compile(r'(<p style="font-size:1\.05rem;line-height:2\.1;font-weight:600;">\n)(.*?)(\n\s*</p>)', re.S)
for fname, adds in NEARBY_ADD.items():
    def fn(src, adds=adds):
        m = NB_RE.search(src)
        if not m:
            return src
        block = m.group(2)
        for s, n in adds:
            if s in block:
                continue
            block = block.rstrip() + f' &nbsp;&middot;&nbsp;\n      <a href="/{s}" style="color:#0b3d6b;">{n}</a>'
        return src[:m.start(2)] + block + src[m.end(2):]
    rw(os.path.join(HERE, fname), fn)
print("[nearby] synced")

print(f"\n{len(changed)} file(s) changed.")
