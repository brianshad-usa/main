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


# Redesign 2026: the areas list lives once, in chrome/footer.html, and apply_chrome.py writes it into every page between
# the PL:HEADER / PL:FOOTER markers. Pages that still carry the old footer are synced below as before.
FOOT = os.path.join(HERE, "chrome", "footer.html")
PL_AREAS_RE = re.compile(r'(<nav class="pl-footer-areas-links"[^>]*>\n)(.*?)(\n\s*</nav>)', re.S)


def sync_pl_footer(src):
    m = PL_AREAS_RE.search(src)
    if not m:
        return src
    indent = re.match(r"\s*", m.group(2)).group(0) or "      "
    links = "\n".join(f'{indent}<a href="/{s}">{n}</a>' for s, n in FOOTER_AREAS)
    return src[:m.start(2)] + links + src[m.end(2):]


if os.path.exists(FOOT) and rw(FOOT, sync_pl_footer):
    import subprocess
    import sys
    subprocess.run([sys.executable, os.path.join(HERE, "chrome", "apply_chrome.py")], check=True)

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


# 6) footer "Services" column -> the self-service apps hub ------------------
#    (2026-11-19) Self-service apps (first: /m365-security-assessment) are all listed
#    on ONE hub page, /self-service, so every footer links to the hub once and a new
#    app never needs a site-wide edit. Appends the link as the last item of the
#    footer's Services column, in the file's own href style (relative or "/") and
#    layout (one link per line, or all on one line); files that already link the hub
#    are left alone. The column is the LAST "Services" heading in the footer up to
#    its own </div>; a footer without one (ai-automation-services, case-studies) or
#    with nested markup there is skipped and listed for a manual look.
HUB_SLUG, HUB_LABEL = "self-service", "Self-Service Assessments"
SERVICES_H_RE = re.compile(r'<h([23])>Services</h\1>')
LINK_RE = re.compile(r'<a href="(/?)[^"]*"[^>]*>[^<]*</a>')
hub_skipped = []


def sync_hub_link(src, name=""):
    start = src.find("<footer")
    end = src.find("</footer>", start) if start >= 0 else -1
    if start < 0 or end < 0:
        return src
    heads = list(SERVICES_H_RE.finditer(src, start, end))
    if not heads:
        hub_skipped.append(name)
        return src
    body_start = heads[-1].end()
    close = src.find("</div>", body_start, end)
    body = src[body_start:close] if close >= 0 else ""
    if re.search(r'href="/?' + HUB_SLUG + r'"', body):
        return src
    links = list(LINK_RE.finditer(body))
    if close < 0 or "<div" in body or "<h" in body or not links:
        hub_skipped.append(name)
        return src
    last = links[-1]
    nl = body.rfind("\n", 0, last.start())
    lead = body[nl + 1:last.start()] if nl >= 0 else None
    link = f'<a href="{last.group(1)}{HUB_SLUG}">{HUB_LABEL}</a>'
    ins = f"\n{lead}{link}" if lead is not None and lead.strip() == "" else link
    at = body_start + last.end()
    return src[:at] + ins + src[at:]


n_hub = sum(rw(p, lambda s, p=p: sync_hub_link(s, os.path.relpath(p, HERE))) for p in targets)
n_hub_gen = rw(os.path.join(HERE, "generate_blog.py"), lambda s: sync_hub_link(s, "generate_blog.py"))
print(f"[footer hub link] added to {n_hub} html files; generate_blog.py template updated: {bool(n_hub_gen)}"
      + (f"; skipped (check by hand): {', '.join(hub_skipped)}" if hub_skipped else ""))


# 7) top menu -> "Assessments" (the self-service apps hub) -------------------
#    (2026-11-20) Brian: put the self-service assessments in the main menu. One item,
#    "Assessments" -> /self-service (the hub; while it has a single app, _redirects
#    sends it straight to that app), right after "Services" in the desktop menu
#    (div.nav-links) and the mobile menu (#mobile-menu / #mobileMenu), in each file's
#    own href style and with the Services link's own attributes (onclick etc.). The
#    app pages themselves (hub + every app folder) mark "Assessments" as the active
#    item. case-studies.html's custom top bar gets the same link. Pages without a
#    menu (the Ads landing page managed-it-services.html, utility pages) are skipped.
NAV_LABEL = "Assessments"
NAV_BLOCK_RES = [
    re.compile(r'(<div class="nav-links">)(.*?)(</div>)', re.S),
    re.compile(r'(<div class="mobile-menu" id="(?:mobile-menu|mobileMenu)">)(.*?)(</div>)', re.S),
    re.compile(r'(<nav style="background:#003057[^"]*">)(.*?)(</nav>)', re.S),       # case-studies.html
]
SERVICES_A_RE = re.compile(r'<a href="(?P<pre>[^"]*?)services"(?P<attrs>[^>]*)>Services</a>')
app_dirs = {os.path.dirname(p) for p in glob.glob(os.path.join(HERE, "*", "order.html"))}
app_pages = {os.path.join(HERE, f"{HUB_SLUG}.html")} | {p for d in app_dirs for p in glob.glob(os.path.join(d, "*.html"))}
app_pages |= {os.path.join(HERE, os.path.basename(d) + ".html") for d in app_dirs}   # each app's product page


def add_nav_item(block, active):
    if re.search(r'href="[^"]*' + HUB_SLUG + r'"', block):
        return block
    m = SERVICES_A_RE.search(block)
    if not m:
        return block
    attrs = m.group("attrs").replace(' class="active"', "")
    services = m.group(0)
    if active:                                    # the app pages: Assessments is the current section
        services = services.replace(' class="active"', "")
        attrs = ' class="active"' + attrs
    nl = block.rfind("\n", 0, m.start())
    lead = block[nl + 1:m.start()] if nl >= 0 else ""
    sep = ("\n" + lead) if lead.strip() == "" else " "
    item = f'<a href="{m.group("pre")}{HUB_SLUG}"{attrs}>{NAV_LABEL}</a>'
    return block[:m.start()] + services + sep + item + block[m.end():]


def sync_nav_item(src, active=False):
    for rx in NAV_BLOCK_RES:
        src = rx.sub(lambda m: m.group(1) + add_nav_item(m.group(2), active) + m.group(3), src)
    return src


nav_targets = sorted(set(targets) | app_pages)
n_nav = sum(rw(p, lambda s, p=p: sync_nav_item(s, p in app_pages)) for p in nav_targets if os.path.exists(p))
n_nav_gen = rw(os.path.join(HERE, "generate_blog.py"), sync_nav_item)
print(f"[top menu] '{NAV_LABEL}' added to {n_nav} html files; generate_blog.py template updated: {bool(n_nav_gen)}")

print(f"\n{len(changed)} file(s) changed.")
