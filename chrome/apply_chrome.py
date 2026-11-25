#!/usr/bin/env python3
"""
chrome/apply_chrome.py -- put the shared 2026 header + footer on every page (redesign-2026).

The header and footer live in ONE place each: chrome/header.html and chrome/footer.html. This script writes
them into every page between markers, so a menu or footer change is: edit the partial, run this script.

    python chrome/apply_chrome.py            # apply to all pages (writes only files that change)
    python chrome/apply_chrome.py --check    # report what would change; exit 1 if anything is out of date

Per page it:
  1. replaces the header: the <!-- PL:HEADER --> block, or on first run the legacy
     <nav class="site-nav">...</nav> + <div class="mobile-menu" id="mobile-menu|mobileMenu">...</div> pair;
  2. replaces the footer: the <!-- PL:FOOTER --> block, or the legacy <footer class="site-footer">...</footer>
     (checkout pages keep their small checkout footer);
  3. marks the current menu section (Solutions / Industries / Client Success / Insights / About);
  4. makes old menu code null-safe: getElementById('hamburger'|'mobileMenu'|'mobile-menu') no longer throws
     once those elements are gone (industry pages wire their old hamburger in a script);
  5. preloads the two self-hosted fonts before _shared.css and drops Google Fonts preconnects;
  6. loads /assets/js/pl.js (menus, mobile drawer, reveal-on-scroll) before </body>.
Pages without the legacy header and without markers are skipped and listed (the Ads landing page
managed-it-services.html is skipped on purpose: it has its own conversion-focused layout).
Byte-safe: files are read and written as UTF-8 and keep their original newline style.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL_JS_VERSION = "20261122b"
FOOTER_ONLY = set()   # 2026-11-25: the Managed IT Ads landing page now uses the shared header too (Phase 2 brief §7)
SKIP_DIRS = {".git", ".github", "chrome", "editorial", "functions", "node_modules", "tools", "apps", "videos"}

SOLUTIONS = {
    "services", "managed-it-services", "co-managed-it-services", "it-help-desk", "cybersecurity-services", "cloud-services",
    "backup-disaster-recovery", "email-security-services", "endpoint-security-services",
    "governance-risk-compliance", "identity-access-management", "network-security-services",
    "security-awareness-training", "virtual-cio", "ai-automation-services", "microsoft-365-support-los-angeles",
    "network-support-los-angeles", "outsourced-it-services-los-angeles", "m365-security-assessment", "self-service",
}
INDUSTRIES = {
    "aerospace-defense-it-services", "education-it-services", "entertainment-it-services", "financial-services-it",
    "healthcare-it-services", "law-firm-it-services-los-angeles", "logistics-it-services",
    "manufacturing-it-services", "nonprofit-it-services", "professional-services-it", "real-estate-it-services",
    "technology-it-services", "waste-management-it-services",
}
INSIGHTS = {
    "how-to-choose-managed-it-provider-los-angeles", "managed-it-services-pricing-los-angeles",
    "vcio-vs-break-fix-vs-managed-it", "what-does-a-vcio-do", "when-your-business-needs-a-vcio",
    "la-business-cybersecurity-report-2026", "incident-response-playbook", "continuity-checklist",
    "pos-holiday-checklist", "technology-plan",
}
ABOUT = {"about", "why-pro-link-systems", "contact", "support", "it-support-burbank"}

FONT_PRELOAD = (
    '<link rel="preload" href="/assets/fonts/Manrope-normal-latin.woff2" as="font" type="font/woff2" crossorigin>\n'
    '  <link rel="preload" href="/assets/fonts/Inter-normal-latin.woff2" as="font" type="font/woff2" crossorigin>\n  '
)
PL_JS_TAG = '<script src="/assets/js/pl.js?v=%s" defer></script>' % PL_JS_VERSION
# Consent defaults (Phase 3, 2026-11-24): consent.js must run synchronously before the Google tag and Microsoft UET,
# so it goes immediately before whichever of the two comes first in <head>. Pages without either are left alone.
CONSENT_VERSION = "20261124"
CONSENT_TAG = ('<!-- PL:CONSENT --><script src="/assets/js/consent.js?v=%s"></script><!-- /PL:CONSENT -->' % CONSENT_VERSION)
RE_CONSENT = re.compile(r"<!-- PL:CONSENT -->.*?<!-- /PL:CONSENT -->", re.S)
RE_TAG_START = re.compile(r'<!-- Google tag \(gtag\.js\) -->|<script async src="https://www\.googletagmanager\.com/gtag/js\?id='
                          r'|<!-- Microsoft UET tag|bat\.bing\.(?:net|com)/bat\.js')

RE_HEADER_MARKED = re.compile(r"<!-- PL:HEADER -->.*?<!-- /PL:HEADER -->", re.S)
RE_FOOTER_MARKED = re.compile(r"<!-- PL:FOOTER -->.*?<!-- /PL:FOOTER -->", re.S)
RE_FOOTER_LEGACY = re.compile(r'<footer class="site-footer"[^>]*>.*?</footer>', re.S)
# (?!...) keeps the patch idempotent: an already-wrapped call is never wrapped again
RE_NULLSAFE = re.compile(r"""document\.getElementById\((['"])(hamburger|mobileMenu|mobile-menu)\1\)(?!\|\|document\.createElement)""")
RE_SHARED_CSS = re.compile(r'<link rel="stylesheet" href="/?_shared\.css[^"]*">')
RE_GFONTS_PRECONNECT = re.compile(r'[ \t]*<link rel="preconnect" href="https://fonts\.(?:googleapis|gstatic)\.com"[^>]*>\r?\n?')
RE_PL_JS = re.compile(r'<script src="/assets/js/pl\.js[^"]*" defer></script>')
# The main landmark: a page without its own <main> gets one, opened by the header block and closed by the footer block.
MAIN_ANCHOR = '<span id="pl-main" tabindex="-1"></span>'
MAIN_OPEN = '<main id="pl-main" tabindex="-1">'


def ensure_consent(t):
    """Insert (or refresh) the consent block before the first Google tag / UET snippet in <head>."""
    if RE_CONSENT.search(t):
        return RE_CONSENT.sub(lambda _m: CONSENT_TAG, t, count=1)
    head_end = t.find("</head>")
    m = RE_TAG_START.search(t)
    if not m:
        return t
    start = m.start()
    if head_end > 0 and start > head_end:
        # tags placed in <body> (legacy page): consent defaults still go in <head>, which runs first
        return t[:head_end] + "  " + CONSENT_TAG + "\n" + t[head_end:]
    if not t.startswith("<", start):
        # matched inside an inline UET <script>: back up to that <script> element
        start = t.rfind("<script", 0, start)
    line_start = t.rfind("\n", 0, start) + 1
    indent = t[line_start:start]
    if indent.strip():          # the tag shares a line with other markup: insert inline
        return t[:start] + CONSENT_TAG + t[start:]
    return t[:line_start] + indent + CONSENT_TAG + "\n" + t[line_start:]


def section_for(rel):
    base = os.path.splitext(os.path.basename(rel))[0]
    if rel.replace("\\", "/").startswith("blog/") or base in INSIGHTS:
        return "insights"
    if base == "case-studies" or rel.replace("\\", "/").startswith("case-studies/"):
        return "success"
    if base in INDUSTRIES:
        return "industries"
    if base in SOLUTIONS or rel.replace("\\", "/").startswith("m365-security-assessment/"):
        return "solutions"
    if base in ABOUT or rel.replace("\\", "/").startswith("leadership/") or (
            base.startswith("managed-it-services-") and base != "managed-it-services-pricing-los-angeles"):
        return "about"
    return None


def header_for(partial, section):
    h = partial
    if section == "success":
        h = h.replace('class="pl-nav-link" data-nav="success"', 'class="pl-nav-link" data-nav="success" aria-current="page"')
    elif section:
        h = h.replace('class="pl-nav-trigger" data-nav="%s"' % section,
                      'class="pl-nav-trigger is-current" data-nav="%s"' % section)
    return "<!-- PL:HEADER -->\n" + h.strip("\n") + "\n<!-- /PL:HEADER -->"


def find_legacy_header(text):
    """Return (start, end) of the legacy nav + mobile-menu pair, or None."""
    s = text.find('<nav class="site-nav"')
    if s < 0:
        return None
    e_nav = text.find("</nav>", s)
    if e_nav < 0:
        return None
    e_nav += len("</nav>")
    m = re.compile(r'\s*<div class="mobile-menu" id="(?:mobile-menu|mobileMenu)">').match(text, e_nav)
    if not m:
        return None
    e_menu = text.find("</div>", m.end())
    if e_menu < 0 or "<div" in text[m.end():e_menu]:
        return None
    return s, e_menu + len("</div>")


_PARTIALS = []


def partials():
    """(header, footer) partial text, read once."""
    if not _PARTIALS:
        for name in ("header.html", "footer.html"):
            with open(os.path.join(ROOT, "chrome", name), encoding="utf-8") as fh:
                _PARTIALS.append(fh.read().replace("\r\n", "\n"))
    return _PARTIALS[0], _PARTIALS[1]


def process_text(text, rel):
    """Chrome for a page held in memory (used by chrome/insights.py and generate_blog.py). Raises if the page
    has neither markers nor a legacy header."""
    header_partial, footer_partial = partials()
    new, notes = transform(text, rel, header_partial, footer_partial)
    if new is None:
        raise ValueError("apply_chrome: %s (%s)" % (rel, ", ".join(notes)))
    return new


def process(path, header_partial, footer_partial):
    rel = os.path.relpath(path, ROOT)
    with open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8")
    t, notes = transform(text, rel, header_partial, footer_partial)
    return (t if t is not None and t != text else None), notes


def transform(text, rel, header_partial, footer_partial):
    """Return (page text with current chrome, notes); the text is None when no header can be placed."""
    crlf = "\r\n" in text
    t = text.replace("\r\n", "\n")
    notes = []

    if rel.replace("\\", "/") in FOOTER_ONLY:
        footer = "<!-- PL:FOOTER -->\n" + footer_partial.strip("\n") + "\n<!-- /PL:FOOTER -->"
        t = RE_FOOTER_MARKED.sub(lambda _m: footer, t, count=1)
        t = ensure_consent(t)
        return (t.replace("\n", "\r\n") if crlf else t), notes

    header = header_for(header_partial, section_for(rel))
    if RE_HEADER_MARKED.search(t):
        t = RE_HEADER_MARKED.sub(lambda _m: header, t, count=1)
    else:
        span = find_legacy_header(t)
        if not span:
            return None, ["no header found"]
        t = t[:span[0]] + header + t[span[1]:]

    footer = "<!-- PL:FOOTER -->\n" + footer_partial.strip("\n") + "\n<!-- /PL:FOOTER -->"
    if RE_FOOTER_MARKED.search(t):
        t = RE_FOOTER_MARKED.sub(lambda _m: footer, t, count=1)
    elif RE_FOOTER_LEGACY.search(t):
        t = RE_FOOTER_LEGACY.sub(lambda _m: footer, t, count=1)
    else:
        notes.append("kept own footer")

    if footer in t:
        i, j = t.index(header) + len(header), t.index(footer)
        if i < j and "<main" not in t[i:j]:
            t = (t[:i - len(header)] + header.replace(MAIN_ANCHOR, MAIN_OPEN) + t[i:j]
                 + footer.replace("<!-- PL:FOOTER -->\n", "<!-- PL:FOOTER -->\n</main>\n", 1) + t[j + len(footer):])

    t = RE_NULLSAFE.sub(lambda m: "(document.getElementById('%s')||document.createElement('i'))" % m.group(2), t)

    if "/assets/fonts/Manrope-normal-latin.woff2" not in t:
        m = RE_SHARED_CSS.search(t)
        if m:
            t = t[:m.start()] + FONT_PRELOAD + t[m.start():]
    t = RE_GFONTS_PRECONNECT.sub("", t)

    if RE_PL_JS.search(t):
        t = RE_PL_JS.sub(PL_JS_TAG, t)
    else:
        i = t.rfind("</body>")
        if i < 0:
            return None, ["no </body>"]
        t = t[:i] + PL_JS_TAG + "\n" + t[i:]

    t = ensure_consent(t)

    if crlf:
        t = t.replace("\n", "\r\n")
    return t, notes


def main():
    check = "--check" in sys.argv
    with open(os.path.join(ROOT, "chrome", "header.html"), encoding="utf-8") as fh:
        header_partial = fh.read().replace("\r\n", "\n")
    with open(os.path.join(ROOT, "chrome", "footer.html"), encoding="utf-8") as fh:
        footer_partial = fh.read().replace("\r\n", "\n")

    changed, skipped, kept_footer = [], [], []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if not name.endswith(".html"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT)
            new, notes = process(path, header_partial, footer_partial)
            if "kept own footer" in notes:
                kept_footer.append(rel)
            if new is None:
                if notes and notes != ["kept own footer"]:
                    skipped.append("%s (%s)" % (rel, ", ".join(notes)))
                continue
            changed.append(rel)
            if not check:
                with open(path, "wb") as fh:
                    fh.write(new.encode("utf-8"))

    verb = "would change" if check else "changed"
    print("%s %d page(s)" % (verb, len(changed)))
    if kept_footer:
        print("kept their own footer: " + ", ".join(sorted(kept_footer)))
    if skipped:
        print("skipped:\n  " + "\n  ".join(sorted(skipped)))
    if check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
