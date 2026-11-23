#!/usr/bin/env python3
"""
chrome/clients.py -- the client portfolio, from editorial/clients.json.

    python chrome/clients.py --write     # refresh the featured clients on index.html (the hub and the case study
                                         # pages are written by build_case_pages.py, which also calls this)
    python chrome/clients.py --check     # exit 1 when a page and the data disagree

Rules the check enforces (owner, 2026-11-22, iterations 5 and 6): the portfolio holds every organization in `order` once, in
that fixed order; the home page shows the `home` lineup in its own fixed order; every client has an industry, a short
summary, an industry group and a relationship label (Current client, Past engagement or Project engagement) when one is
known; a client with a case study links to it and the case study page carries the same company profile and links back.
Both lists are plain source order (no CSS reordering), so the sequence is the same on desktop and mobile. Counts shown on
the pages are computed from the entries actually rendered.
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

ORDER = ["lisi-aerospace", "cunico", "philip-morris-international", "m13", "fralock", "veev-spirits",
         "optical-zonu", "cochise-capital", "crr", "global-holdings", "otitopic", "fsc-lighting", "hallmark-lighting",
         "myx-fusions", "beverly-hills-plaza", "cookes-crating", "optimus-property-management", "global-garden",
         "waverly-school", "snitzer-law"]
HOME = ["lisi-aerospace", "cunico", "m13", "fralock", "veev-spirits", "optical-zonu", "cochise-capital", "fsc-lighting"]
STATUS = {"current": ("Current client", " is-current"), "past": ("Past engagement", ""), "project": ("Project engagement", "")}
WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
         "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen", "Twenty", "Twenty-one", "Twenty-two"]


def load():
    d = json.load(io.open(DATA, encoding="utf-8"))
    for slug, c in d["clients"].items():
        c["slug"] = slug
    return d


def included(d):
    return [d["clients"][s] for s in d["order"] if d["clients"][s].get("include", True)]


def home_clients(d):
    return [d["clients"][s] for s in d["home"] if d["clients"][s].get("include", True)]


def word(n):
    return WORDS[n] if n < len(WORDS) else str(n)


def case_name(c):
    return c.get("case_name") or c["name"]


def flag(ids):
    return '<span class="pl-flag">Review %s</span>' % E(" · ".join(ids)) if ids else ""


# Logos sit in identical boxes and are sized to the same visual weight: each keeps its own proportions (never
# stretched), is scaled to a common area, then fitted inside the box. Wide wordmarks come out shorter, compact marks
# taller, so the row reads evenly. (owner, 2026-11-23: smaller, all the same size)
LOGO_HOME = (128, 40, 2500)        # box width, box height, target area in px: home page lineup
LOGO_PLATE = (150, 50, 3600)       # portfolio name plates


def logo_html(c, box):
    g = c["logo"]
    bw, bh, area = box
    s = (area / float(g["width"] * g["height"])) ** 0.5
    w, h = g["width"] * s, g["height"] * s
    k = min(1.0, bw / w, bh / h)
    return ('<span class="pl-clogo"><img src="%s" alt="%s" width="%d" height="%d" loading="lazy" decoding="async"></span>'
            % (A(g["src"]), A(c["name"]), round(w * k), round(h * k)))


def plate(c):
    """Name plate: one size and one typeface for every client; an approved logo file replaces the name."""
    if c.get("logo"):
        inner = logo_html(c, LOGO_PLATE)
    else:
        inner = "<span>%s</span>" % E(c["name"])
    if c.get("plate_sub"):
        inner += "<small>%s</small>" % E(c["plate_sub"])
    return inner


def status_line(c):
    if not c.get("status"):
        return ""
    label, cls = STATUS[c["status"]]
    when = c.get("period") if c["status"] == "current" else c.get("years")
    return '<span class="pl-status%s">%s</span>%s' % (cls, label, (" " + E(when)) if when else "")


def short(c):
    """Short name for link text: 'LISI Aerospace case study'."""
    return c.get("short") or c.get("home_name") or case_name(c)


def profile_item(c):
    """One profile: what Pro Link Systems did first (relationship, outcome, case study), then a short company summary."""
    legacy = '<span class="pl-anchor" id="%s"></span>\n    ' % A(c["legacy_id"]) if c.get("legacy_id") else ""
    work = []
    if c.get("status"):
        work.append('<p class="pl-profile-status">%s</p>' % status_line(c))
    if c.get("engagement"):
        work.append('<p class="pl-profile-did">%s</p>' % E(c["engagement"]))
    if c.get("metric"):
        work.append('<p class="pl-profile-metric"><strong>%s</strong> <span>%s</span></p>' % (E(c["metric"][0]), E(c["metric"][1])))
    if c.get("case"):
        work.append('<p class="pl-profile-case"><a class="pl-arrow" href="/case-studies/%s">%s case study</a></p>' % (c["case"], E(short(c))))
    if c.get("review"):
        work.append('<p class="pl-profile-flag">%s</p>' % flag(c["review"]))
    owner = '\n      <p class="pl-profile-owner"><b>Ownership</b> %s</p>' % E(c["ownership"]) if c.get("ownership") else ""
    brief = "" if work else " is-brief"
    return ('  <li class="pl-profile%s" id="%s" data-group="%s">\n    %s<h3 class="pl-nameplate">%s</h3>\n'
            '    <div class="pl-profile-work">\n      <p class="pl-case-sector">%s</p>\n      %s\n    </div>\n'
            '    <div class="pl-profile-about">\n      <p>%s</p>%s\n    </div>\n  </li>'
            % (brief, c["slug"], A(c["group"]), legacy, plate(c), E(c["industry"]), "\n      ".join(work), E(c["summary"]), owner))


FILTER_JS = """<script>
/* Jump to an industry: shows only that group's profiles, in portfolio order. Without JavaScript every profile is visible. */
(function () {
  var nav = document.getElementById('pl-folio-jump');
  var list = document.querySelector('.pl-folio');
  var out = document.getElementById('pl-folio-count');
  if (!nav || !list || !out) return;
  var items = [].slice.call(list.querySelectorAll('.pl-profile'));
  var buttons = [].slice.call(nav.querySelectorAll('button'));
  nav.hidden = false;
  function show(group, label) {
    var n = 0;
    items.forEach(function (li) { var on = !group || li.getAttribute('data-group') === group; li.hidden = !on; if (on) n++; });
    buttons.forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-group') === group ? 'true' : 'false'); });
    out.textContent = group ? ('Showing ' + n + ' of ' + items.length + ' organizations: ' + label + '.') : ('Showing all ' + items.length + ' organizations.');
  }
  buttons.forEach(function (b) {
    b.addEventListener('click', function () {
      show(b.getAttribute('data-group'), b.getAttribute('data-label'));
    });
  });
})();
</script>"""


def portfolio_html(d):
    cs = included(d)
    intro = d["intro"]
    lead = " ".join(E(p) for p in intro["lead"])
    review = (" " + flag(d["portfolio_review"])) if d.get("portfolio_review") else ""
    groups = [(g["id"], g["label"], sum(1 for c in cs if c["group"] == g["id"])) for g in d["groups"]]
    chips = ['      <button type="button" data-group="" data-label="All" aria-pressed="true">All <span>%d</span></button>' % len(cs)]
    chips += ['      <button type="button" data-group="%s" data-label="%s" aria-pressed="false">%s <span>%d</span></button>' % (A(gid), A(label), E(label), n)
              for gid, label, n in groups if n]
    return ('<section class="pl-section" id="portfolio" aria-labelledby="portfolio-h">\n  <div class="pl-wrap">\n'
            '    <div class="pl-head">\n'
            '      <div><p class="pl-eyebrow">Client portfolio</p><h2 class="pl-h2" id="portfolio-h">%s</h2></div>\n'
            '      <p class="pl-lead">%s</p>\n'
            '    </div>\n    <p class="pl-folio-intro">%s%s</p>\n'
            '    <nav class="pl-folio-jump" id="pl-folio-jump" aria-label="Jump to an industry" hidden>\n'
            '      <p class="pl-folio-jump-label">Jump to an industry</p>\n%s\n    </nav>\n'
            '    <p class="pl-folio-count" id="pl-folio-count" aria-live="polite">Showing all %d organizations.</p>\n'
            '    <ol class="pl-folio">\n%s\n    </ol>\n'
            '    <p class="pl-folio-note">Our work is for the client named in each profile. Parent companies are identified for context and do not mean that Pro Link Systems managed the group&rsquo;s wider technology environment. Company names and marks belong to their owners and identify clients; they do not imply endorsement.</p>\n'
            '%s\n  </div>\n</section>'
            % (E(intro["title"]), lead, E(intro["note"]), review, "\n".join(chips), len(cs),
               "\n".join(profile_item(c) for c in cs), FILTER_JS))


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
        name = logo_html(c, LOGO_HOME) if c.get("logo") else E(c.get("home_name") or c["name"])
        sub = '<span class="pl-client-sub">%s</span>' % E(c["plate_sub"]) if c.get("plate_sub") else ""
        cells.append('      <li><a href="/case-studies#%s"><span class="pl-client-name">%s</span>%s<span class="pl-client-industry">%s</span>%s</a></li>'
                     % (c["slug"], name, sub, E(c["industry"]), home_status(c)))
    total = len(included(d))
    return ('<!-- PL:CLIENTS (python chrome/clients.py --write) -->\n'
            '<section class="pl-clients" aria-labelledby="clients-h">\n  <div class="pl-wrap">\n'
            '    <div class="pl-clients-head">\n'
            '      <div><p class="pl-eyebrow">Our clients</p><h2 class="pl-h2" id="clients-h">Selected Clients &amp; Engagements</h2>'
            '<p class="pl-clients-lead">Trusted by organizations of all sizes, from growing businesses to globally recognized enterprises.</p></div>\n'
            '      <a class="btn btn-primary" href="/case-studies#portfolio">View the complete client portfolio</a>\n'
            '    </div>\n    <ol class="pl-clients-grid">\n%s\n    </ol>\n'
            '    <p class="pl-clients-note">%s of the %d organizations in our <a href="/case-studies#portfolio">client portfolio</a>.%s</p>\n'
            '  </div>\n</section>\n<!-- /PL:CLIENTS -->'
            % ("\n".join(cells), word(len(cs)), total, (" " + flag(d["portfolio_review"])) if d.get("portfolio_review") else ""))


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
        bad.append("editorial/clients.json: 'home' is not the owner's lineup")
    if len(set(ORDER)) != len(ORDER) or set(cl) != set(ORDER):
        bad.append("the portfolio must hold each organization in 'order' exactly once, and nothing else")
    names = [c["name"].casefold() for c in cl.values()]
    if len(set(names)) != len(names):
        bad.append("duplicate client name")
    groups = {g["id"] for g in d.get("groups", [])}
    for s, c in cl.items():
        if not c.get("industry") or len(c.get("description", "").split()) < 15 or len(c.get("summary", "").split()) < 8:
            bad.append("%s: industry, description or summary missing" % s)
        if c.get("group") not in groups:
            bad.append("%s: no industry group" % s)
        if c.get("status") not in (None, "current", "past", "project"):
            bad.append("%s: label must be Current client, Past engagement or Project engagement" % s)
        if c.get("logo") and not os.path.exists(os.path.join(ROOT, c["logo"]["src"].lstrip("/"))):
            bad.append("%s: logo file missing" % s)
    hub = io.open(os.path.join(ROOT, "case-studies.html"), encoding="utf-8").read()
    home = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    want = [c["slug"] for c in included(d)]
    got = re.findall(r'<li class="pl-profile(?: is-brief)?" id="([^"]+)"', hub)
    if got != want:
        bad.append("case-studies.html: profiles are missing or out of order (run build_case_pages.py)")
    if "Showing all %d organizations." % len(want) not in hub:
        bad.append("case-studies.html: the displayed count does not match the profiles shown")
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
    removed = [s for s in d.get("removed", [])]
    for s in removed:
        for path in ("case-studies.html", "index.html"):
            if 'id="%s"' % s in io.open(os.path.join(ROOT, path), encoding="utf-8").read():
                bad.append("%s still shows removed client %s" % (path, s))
    return bad


if __name__ == "__main__":
    if "--check" in sys.argv:
        problems = check()
        print("\n".join(problems) if problems else "client portfolio: %d profiles, %d on the home page, in order" % (len(included(load())), len(home_clients(load()))))
        sys.exit(1 if problems else 0)
    print("index.html " + ("updated" if write_home() else "already current"))
