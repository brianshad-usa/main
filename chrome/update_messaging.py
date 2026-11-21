#!/usr/bin/env python3
"""
chrome/update_messaging.py -- replace legacy sales calls to action on internal pages with the 2026 corporate
consultation language (Brian, iteration 3). Idempotent.

    python chrome/update_messaging.py [--check]

- Scope: root pages and m365-security-assessment/ pages, EXCEPT the pages rebuilt by hand (home, about,
  services, contact, case studies, support), legal/privacy/404, and the Google Ads landing page
  managed-it-services.html (its wording matches the live ads). Blog posts are handled by the article template.
- Only the page body (between the PL:HEADER and PL:FOOTER markers) and JSON-LD blocks are edited, so visible
  FAQ answers and FAQPage JSON-LD stay identical. <title> and meta tags are never touched.
- Also fixes the naming rule: "assessment" is only the paid Microsoft 365 product, never the free offer.
- --check lists what would change and any "no pressure / no obligation" left for a manual edit.
"""
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {"index.html", "about.html", "services.html", "contact.html", "case-studies.html", "support.html",
        "404.html", "legal.html", "privacy.html", "managed-it-services.html",
        "m365-security-assessment.html"}   # paid product page: wording approved by Brian 2026-11-20

PHRASES = [  # (exact text, replacement) applied in order
    ("Schedule a Free Discovery Call", "Schedule a Technology Consultation"),
    ("Book a Free Discovery Call", "Schedule a Technology Consultation"),
    ("Start with a Free Discovery Call", "Schedule a Technology Consultation"),
    ("Request My Free Discovery Call", "Request a Consultation"),
    ("Request My Free IT Consultation", "Request a Consultation"),
    ("Request My Free Consultation", "Request a Consultation"),
    ("Get a Free IT Consultation", "Schedule a Technology Consultation"),
    ("Get a Free Security Consultation", "Schedule a Security Consultation"),
    ("Get a Free Cloud Consultation", "Schedule a Cloud Consultation"),
    ("Get a Free Consultation", "Schedule a Consultation"),
    ("Request Free Consultation", "Request a Consultation"),
    ("Schedule Free Consultation", "Schedule a Consultation"),
    ("Book your free consultation", "Schedule a consultation"),
    ("Get a Free BDR Assessment", "Schedule a Continuity Consultation"),
    ("Get a free backup &amp; disaster recovery assessment", "Discuss your continuity plan"),
    ("Get a free backup & disaster recovery assessment", "Discuss your continuity plan"),
    ("Get a Free Email Security Assessment", "Schedule an Email Security Consultation"),
    ("Schedule a Free Email Security Review", "Schedule an Email Security Review"),
    ("Get a Free Endpoint Assessment", "Schedule an Endpoint Security Consultation"),
    ("Schedule a Free Endpoint Assessment", "Schedule an Endpoint Security Consultation"),
    ("Get a Free School IT Assessment", "Schedule a School IT Consultation"),
    ("Get a free school IT assessment", "Schedule a school IT consultation"),
    ("Get a Free Legal IT Assessment", "Schedule a Legal IT Consultation"),
    ("Book your free 15-minute review", "Schedule a 15-minute review"),
    ("Get a free 15-minute review", "Schedule a 15-minute review"),
    ("Start with a free AI readiness conversation", "Start with an AI readiness conversation"),
    ("Request a free IT consultation", "Schedule a technology consultation"),
    ("Request a free discovery call", "Schedule a technology consultation"),
    ("Get a free security consultation", "Discuss your security strategy"),
    ("Get a free cloud consultation", "Discuss your cloud strategy"),
    ("Ready to talk to a real IT engineer?", "Discuss your technology strategy"),
    ("Call Now: 1-800-890-6133", "Call 1-800-890-6133"),
]
REGEXES = [
    (re.compile(r"(?:Get a free|Free) IT consultation for your (.{2,60}?) business", re.I), r"Discuss the technology strategy for your \1 business"),
    (re.compile(r"Get a [Ff]ree ([A-Za-z][A-Za-z&;\- ]{1,30}?) IT [Aa]ssessment"), lambda m: "Schedule a %s IT consultation" % m.group(1).lower()),
    (re.compile(r"Schedule a Free IT Consultation"), "Schedule a Technology Consultation"),
    (re.compile(r"your free co-managed IT discovery call"), "your co-managed IT consultation"),
    (re.compile(r"(?:Free IT Consultation|Free Discovery Call)\s*&middot;\s*No Obligation"), "Technology Consultation"),
    (re.compile(r'(<span class="section-label">)\s*(?:Free IT Consultation|Free Discovery Call)\s*(</span>)'), r"\1Technology Consultation\2"),
    (re.compile(r"No pressure, no obligation, and no replacing"), "No replacing"),
    (re.compile(r"No pressure,? no obligation\s*(?:&mdash;|—)\s*just", re.I), "Just"),
    (re.compile(r"\s*(?:&mdash;|&ndash;|[—–-])\s*(?:with )?no obligation(?:,? (?:and )?no (?:hard sell|sales pressure|sales script|pressure))?(?=[.<])", re.I), ""),
    (re.compile(r"\s*with no obligation and no pressure(?=[.<])", re.I), ""),
    (re.compile(r"\s*Free consultation, no obligation\.", re.I), ""),
    (re.compile(r"Free Consultation, No Pressure"), "Scoped After a Consultation"),
    (re.compile(r"Charging for the assessment or discovery call\."), "Charging for the initial consultation."),
    (re.compile(r"no charge for the initial discovery call or assessment"), "no charge for the initial consultation"),
    (re.compile(r"does not charge for the initial assessment or discovery call"), "does not charge for the initial consultation"),
    (re.compile(r"No pressure[.,]? [Nn]o commitment\s*(?:&mdash;|—)\s*just", re.I), "Just"),
    (re.compile(r"\s*No pressure[.,]? [Nn]o commitment\.", re.I), ""),
    (re.compile(r"\s*(?:&mdash;|&ndash;|[—–-])\s*no pressure,? no commitment\.?", re.I), "."),
    (re.compile(r"\s*(?:&mdash;|&ndash;|[—–-])\s*at no cost and no obligation", re.I), ""),
    (re.compile(r"\s*(?:&mdash;|&ndash;|[—–-])\s*no obligation(?=[.<])", re.I), ""),
    (re.compile(r"\bFree IT consultation\b"), "Technology consultation"),
    (re.compile(r"Get a free IT consultation"), "Schedule a technology consultation"),
    (re.compile(r"\s*[—–-]\s*no pressure,? (?:and )?no obligation(?:,? no scripts)?\.?", re.I), ""),
    (re.compile(r"\s*(?:&mdash;|&ndash;)\s*no pressure,? (?:and )?no obligation(?:,? no scripts)?\.?", re.I), ""),
    (re.compile(r"\s*No pressure,? (?:and )?no obligation(?:,? no scripts)?\.", re.I), ""),
    (re.compile(r"\b[Aa] free,? no[- ]obligation (consultation|call|review)"), r"a \1"),
    (re.compile(r"\bfree,? no[- ]obligation (consultation|call|review)"), r"\1"),
    (re.compile(r"\b[Aa] free discovery call"), "a technology consultation"),
    (re.compile(r"\bfree discovery call"), "technology consultation"),
    (re.compile(r"\b[Aa] free IT consultation"), "a technology consultation"),
    (re.compile(r"\bfree IT consultation"), "technology consultation"),
]


def rewrite(segment):
    for old, new in PHRASES:
        segment = segment.replace(old, new)
    for rx, rep in REGEXES:
        segment = rx.sub(rep, segment)
    return segment


def process(text):
    a = text.find("<!-- /PL:HEADER -->")
    b = text.find("<!-- PL:FOOTER -->")
    if a < 0:
        return text
    if b < 0:                                   # checkout pages keep their own footer
        b = text.find("<footer")
        b = b if b > a else len(text)
    out = text[:a] + rewrite(text[a:b]) + text[b:]
    return re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)',
                  lambda m: m.group(1) + rewrite(m.group(2)) + m.group(3), out, flags=re.S)


def main():
    check = "--check" in sys.argv
    files = [f for f in glob.glob(os.path.join(ROOT, "*.html")) if os.path.basename(f) not in SKIP]
    files += glob.glob(os.path.join(ROOT, "m365-security-assessment", "*.html"))
    changed, leftovers = [], []
    for f in sorted(files):
        raw = io.open(f, encoding="utf-8", newline="").read()
        new = process(raw)
        rel = os.path.relpath(f, ROOT)
        if new != raw:
            changed.append(rel)
            if not check:
                io.open(f, "w", encoding="utf-8", newline="").write(new)
        body = new[new.find("<!-- /PL:HEADER -->"):]
        for m in re.finditer(r"(?i)no pressure|no obligation|discovery call|free IT consultation", body):
            leftovers.append("%s: ...%s..." % (rel, re.sub(r"\s+", " ", body[max(0, m.start() - 50):m.end() + 30])))
    print("%s %d page(s)" % ("would change" if check else "changed", len(changed)))
    if leftovers:
        print("left for a manual edit (%d):" % len(leftovers))
        for l in leftovers[:40]:
            print("  " + l)


if __name__ == "__main__":
    main()
