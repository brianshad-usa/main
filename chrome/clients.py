#!/usr/bin/env python3
"""
chrome/clients.py -- the client portfolio, from editorial/clients.json.

    python chrome/clients.py --write     # refresh the featured clients on index.html (the hub and the case study
                                         # pages are written by build_case_pages.py, which also calls this)
    python chrome/clients.py --check     # exit 1 when a page and the data disagree

Rules the check enforces (owner, 2026-11-22): 21 organizations, no duplicates, in the fixed order below on the hub; exactly
eight, in their own fixed order, on the home page (enterprise and growing-business clients side by side); every client has an industry and an individual description; a
client with a case study links to it and the case study page carries the same company profile and links back.
Both lists are plain source order (no CSS reordering), so the sequence is the same on desktop and mobile.
"""
import html
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "editorial", "clients.json")
E = lambda s: html.escape(s, quote=False)
A = lambda s: html.escape(s, quote=True)

ORDER = ["lisi-aerospace", "cunico", "philip-morris-international", "m13", "fralock", "marriott-hotels", "veev-spirits",
         "optical-zonu", "cochise-capital", "crr", "global-holdings", "otitopic", "fsc-lighting", "hallmark-lighting",
         "myx-fusions", "beverly-hills-plaza", "cookes-crating", "optimus-property-management", "global-garden",
         "waverly-school", "snitzer-law"]
HOME = ["lisi-aerospace", "cunico", "m13", "fralock", "optical-zonu", "optimus-property-management", "cookes-crating", "waverly-school"]
STATUS = {"current": ("Current client", " is-current"), "past": ("Past engagement", ""), "historical": ("Historical client", ""),
          "project": ("Project engagement", "")}
WORDS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
         "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen", "Twenty", "Twenty-one"]


def load():
    d = json.load(io.open(DATA, encoding="utf-8"))
    for slug, c in d["clients"].items():
        c["slug"] = slug
    return d


def included(d):
    return [d["clients"][s] for s in d["order"] if d["clients"][s].get("include", True)]


def home_clients(d):
    return [d["clients"][s] for s in d["home"] if d["clients"][s].get("include", True)]


def case_name(c):
    return c.get("case_name") or c["name"]


def flag(ids):
    return '<span class="pl-flag">Review %s</span>' % E(" · ".join(ids)) if ids else ""


def plate(c):
    """Name plate: one size and one typeface for every client; a logo file replaces the name once it is approved."""
    if c.get("logo"):
        g = c["logo"]
        inner = '<img src="%s" alt="%s" width="%d" height="%d" loading="lazy" decoding="async">' % (A(g["src"]), A(c["name"]), g["width"], g["height"])
    else:
        inner = "<span>%s</span>" % E(c["name"])
    if c.get("plate_sub"):
        inner += "<small>%s</small>" % E(c["plate_sub"])
    return inner


def status_line(c):
    if not c.get("status"):
        return ""
    word, cls = STATUS[c["status"]]
    when = c.get("period") if c["status"] == "current" else c.get("years")
    return '<span class="pl-status%s">%s</span>%s' % (cls, word, (" " + E(when)) if when else "")


def profile_item(c):
    legacy = '<span class="pl-anchor" id="%s"></span>\n    ' % A(c["legacy_id"]) if c.get("legacy_id") else ""
    work = []
    if c.get("status"):
        work.append('<p class="pl-profile-status">%s</p>' % status_line(c))
    if c.get("metric"):
        work.append('<p class="pl-profile-metric"><strong>%s</strong> <span>%s</span></p>' % (E(c["metric"][0]), E(c["metric"][1])))
    if c.get("engagement"):
        work.append("<p>%s</p>" % E(c["engagement"]))
    if c.get("case"):
        work.append('<p class="pl-profile-case"><a class="pl-arrow" href="/case-studies/%s">%s case study</a></p>' % (c["case"], E(short(c))))
    if c.get("review"):
        work.append('<p class="pl-profile-flag">%s</p>' % flag(c["review"]))
    owner = '\n      <p class="pl-profile-owner"><b>Ownership</b> %s</p>' % E(c["ownership"]) if c.get("ownership") else ""
    brief = "" if c.get("status") or c.get("engagement") else " is-brief"
    return ('  <li class="pl-profile%s" id="%s">\n    %s<h3 class="pl-nameplate">%s</h3>\n'
            '    <div class="pl-profile-about">\n      <p class="pl-case-sector">%s</p>\n      <p>%s</p>%s\n    </div>\n'
            '    <div class="pl-profile-work">\n      %s\n    </div>\n  </li>'
            % (brief, c["slug"], legacy, plate(c), E(c["industry"]), E(c["description"]), owner, "\n      ".join(work)))


def short(c):
    """Short name for link text: 'LISI Aerospace case study'."""
    return c.get("short") or c.get("home_name") or case_name(c)


def portfolio_html(d):
    cs = included(d)
    intro = d["intro"]
    lead = " ".join(E(p) for p in intro["lead"])
    review = (" " + flag(d["portfolio_review"])) if d.get("portfolio_review") else ""
    return ('<section class="pl-section" id="portfolio" aria-labelledby="portfolio-h">\n  <div class="pl-wrap">\n'
            '    <div class="pl-head">\n'
            '      <div><p class="pl-eyebrow">Client portfolio</p><h2 class="pl-h2" id="portfolio-h">%s</h2></div>\n'
            '      <p class="pl-lead">%s</p>\n'
            '    </div>\n    <p class="pl-folio-intro">%s%s</p>\n    <ol class="pl-folio">\n%s\n    </ol>\n'
            '    <p class="pl-folio-note">Our work is for the client named in each profile. Parent companies are identified for context and do not mean that Pro Link Systems managed the group&rsquo;s wider technology environment. Company names and marks belong to their owners and identify clients; they do not imply endorsement.</p>\n'
            '  </div>\n</section>'
            % (E(intro["title"]), lead, E(intro["note"]), review, "\n".join(profile_item(c) for c in cs)))


def home_status(c):
    if not c.get("status"):
        return ""
    if c["status"] == "current":
        return '<span class="pl-client-status is-current">Current client</span>'
    if not c.get("years"):
        return '<span class="pl-client-status">%s</span>' % STATUS[c["status"]][0]
    return '<span class="pl-client-status">%s, <b>%s</b></span>' % (STATUS[c["status"]][0], E(c["years"]))


def home_html(d):
    cs = home_clients(d)
    cells = []
    for c in cs:
        name = '<img src="%s" alt="%s" width="%d" height="%d" loading="lazy" decoding="async">' % (
            A(c["logo"]["src"]), A(c["name"]), c["logo"]["width"], c["logo"]["height"]) if c.get("logo") else E(c.get("home_name") or c["name"])
        sub = '<span class="pl-client-sub">%s</span>' % E(c["plate_sub"]) if c.get("plate_sub") else ""
        cells.append('      <li><a href="/case-studies#%s"><span class="pl-client-name">%s</span>%s<span class="pl-client-industry">%s</span>%s</a></li>'
                     % (c["slug"], name, sub, E(c["industry"]), home_status(c)))
    total = len(included(d))
    return ('<!-- PL:CLIENTS (python chrome/clients.py --write) -->\n'
            '<section class="pl-clients" aria-labelledby="clients-h">\n  <div class="pl-wrap">\n'
            '    <div class="pl-clients-head">\n'
            '      <div><p class="pl-eyebrow">Our clients</p><h2 class="pl-h2" id="clients-h">Trusted by organizations of all sizes, from growing businesses to globally recognized enterprises.</h2></div>\n'
            '      <a class="btn btn-primary" href="/case-studies#portfolio">View the complete client portfolio</a>\n'
            '    </div>\n    <ol class="pl-clients-grid">\n%s\n    </ol>\n'
            '    <p class="pl-clients-note">Eight of the %d organizations profiled in our client portfolio.%s</p>\n'
            '  </div>\n</section>\n<!-- /PL:CLIENTS -->'
            % ("\n".join(cells), total, (" " + flag(d["portfolio_review"])) if d.get("portfolio_review") else ""))


HOME_RE = re.compile(r"<!-- PL:CLIENTS.*?<!-- /PL:CLIENTS -->", re.S)


def write_home(d=None):
    d = d or load()
    p = os.path.join(ROOT, "index.html")
    raw = io.open(p, encoding="utf-8", newline="").read()
    crlf = "\r\n" in raw
    t = raw.replace("\r\n", "\n")
    assert len(HOME_RE.findall(t)) == 1, "index.html needs one PL:CLIENTS block"
    t = HOME_RE.sub(lambda m: home_html(d), t)
    out = t.replace("\n", "\r\n") if crlf else t
    if out != raw:
        io.open(p, "w", encoding="utf-8", newline="").write(out)
    return out != raw


def check():
    d, bad = load(), []
    cl = d["clients"]
    if d["order"] != ORDER:
        bad.append("editorial/clients.json: 'order' is not the owner's order")
    if d["home"] != HOME:
        bad.append("editorial/clients.json: 'home' is not the owner's order of eight")
    if len(ORDER) != 21 or len(set(ORDER)) != 21 or set(cl) != set(ORDER):
        bad.append("the portfolio must hold 21 different organizations")
    names = [c["name"].casefold() for c in cl.values()]
    if len(set(names)) != len(names):
        bad.append("duplicate client name")
    for s, c in cl.items():
        if not c.get("industry") or len(c.get("description", "").split()) < 20:
            bad.append("%s: industry or individual description missing" % s)
        if c.get("status") not in (None, "current", "past", "historical", "project"):
            bad.append("%s: unknown status" % s)
        if c.get("logo") and not os.path.exists(os.path.join(ROOT, c["logo"]["src"].lstrip("/"))):
            bad.append("%s: logo file missing" % s)
    hub = io.open(os.path.join(ROOT, "case-studies.html"), encoding="utf-8").read()
    home = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    want = [c["slug"] for c in included(d)]
    got = re.findall(r'<li class="pl-profile(?: is-brief)?" id="([^"]+)"', hub)
    if got != want:
        bad.append("case-studies.html: profiles are missing or out of order (run build_case_pages.py)")
    block = HOME_RE.search(home)
    got = re.findall(r'<li><a href="/case-studies#([^"]+)">', block.group(0)) if block else []
    if got != [c["slug"] for c in home_clients(d)]:
        bad.append("index.html: featured clients are missing or out of order (run clients.py --write)")
    if not block or 'href="/case-studies#portfolio"' not in block.group(0) or 'id="portfolio"' not in hub:
        bad.append("index.html must link to the complete client portfolio")
    if block and block.group(0) != home_html(d):
        bad.append("index.html: featured clients differ from the data (run clients.py --write)")
    for c in included(d):
        if hub.count('id="%s"' % c["slug"]) != 1:
            bad.append("case-studies.html: id %s must appear once" % c["slug"])
        if c.get("legacy_id") and hub.count('id="%s"' % c["legacy_id"]) != 1:
            bad.append("case-studies.html: earlier anchor %s must appear once" % c["legacy_id"])
        if profile_item(c) not in hub.replace("\r\n", "\n"):
            bad.append("case-studies.html: %s differs from the data (run build_case_pages.py)" % c["slug"])
        if c.get("case"):
            p = os.path.join(ROOT, "case-studies", c["case"] + ".html")
            page = io.open(p, encoding="utf-8").read() if os.path.exists(p) else ""
            if E(c["description"]) not in page or 'href="/case-studies#%s"' % c["slug"] not in page or E(c["industry"]) not in page:
                bad.append("case-studies/%s.html: company profile missing or different (run build_case_pages.py)" % c["case"])
    return bad


if __name__ == "__main__":
    if "--check" in sys.argv:
        problems = check()
        print("\n".join(problems) if problems else "client portfolio: %d profiles, %d on the home page, in order" % (len(included(load())), len(home_clients(load()))))
        sys.exit(1 if problems else 0)
    print("index.html " + ("updated" if write_home() else "already current"))
