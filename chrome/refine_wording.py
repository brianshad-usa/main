#!/usr/bin/env python3
"""
chrome/refine_wording.py -- iteration 4 wording pass on service, city and guide pages. Idempotent.

    python chrome/refine_wording.py [--check]

- Removes emoji used as icons (they clash with the line-drawn style and are hidden anyway).
- Replaces neighborhood-style sales lines with corporate wording. City, county and industry names stay in place.
- Edits only the page body and JSON-LD (never <title>, meta descriptions, links or scripts), so FAQ answers and
  FAQPage structured data remain identical to each other.
"""
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMOJI = "\U0001F300-\U0001FAFF☀-⛿✀-➿⭐⬆✅❌️"
RULES = [
    # whole icon elements that hold nothing but an emoji
    (re.compile(r'[ \t]*<(div|span) class="[^"]*icon[^"]*">\s*[' + EMOJI + r']+\s*</\1>\r?\n?'), ""),
    (re.compile(r'(class="form-privacy"[^>]*>)\s*[' + EMOJI + r'‍]+\s*'), r"\1"),
    # neighborhood-style lines
    (re.compile(r"Talk to a local IT team about your ((?:[A-Z][A-Za-z]+)(?: [A-Z][A-Za-z]+){0,3}) office"), r"Discuss the technology behind your \1 office"),
    (re.compile(r"Talk to a local IT team about your"), "Discuss the technology behind your"),
    (re.compile(r"Talk to a local IT expert"), "Talk with our advisory team"),
    (re.compile(r"Local IT support across (the LA metro|the West Valley|[^<]{3,40})"), r"On-site and remote IT support across \1"),
    (re.compile(r"Your Local IT Neighbor in West Hills"), "Headquartered minutes from West Hills"),
    (re.compile(r"Your Neighbor on Ventura Blvd (?:&mdash;|—|-) Minutes from Encino"), "Based on Ventura Boulevard, minutes from Encino"),
    (re.compile(r"West Hills deserves an IT partner who(?:'|’|&rsquo;)s <em>already in the neighborhood</em>"), "West Hills deserves a technology partner that is <em>already nearby</em>"),
    (re.compile(r"Encino(?:'|’|&rsquo;)s professional corridor deserves an IT partner that(?:'|’|&rsquo;)s <em>already here</em>"), "Encino’s professional corridor deserves a technology partner that is <em>already here</em>"),
    (re.compile(r"we know what local businesses need from a neighbor they can trust"), "we know what organizations here need from a provider based nearby"),
    (re.compile(r"has a real stake in your (?:neighborhood|community)"), "is accountable to you over the long term"),
    (re.compile(r"replacing the cost and hassle of internal IT with a local, flat-rate team"), "replacing the cost of running IT internally with an accountable, flat-rate team"),
    (re.compile(r"create new IT headaches"), "create new problems to manage"),
    (re.compile(r"(?:the hours they were spending on|on) IT headaches"), lambda m: m.group(0).replace("IT headaches", "IT issues")),
    (re.compile(r"get the most out of Microsoft 365 without the headaches"), "get the most out of Microsoft 365 with clear ownership"),
    (re.compile(r"\bwithout the headaches\b"), "with clear ownership"),
    (re.compile(r"Los Angeles(?:'|’|&rsquo;)s top-tier business community"), "Los Angeles’s professional and financial community"),
    (re.compile(r"\bone call away\b"), "available by phone"),
    (re.compile(r"Ready to Stop Worrying About IT\?"), "Considering outsourced IT?"),
    # sales lines shared by the city pages (second pass, 2026-11-21)
    (re.compile(r"under one flat monthly rate\s*(?:&mdash;|—|-)\s*no (?:à|&agrave;) la carte surprises"), "under one flat monthly rate"),
    (re.compile(r"Everything your team needs\s*(?:&mdash;|—|-)\s*one flat monthly rate, no (?:à|&agrave;) la carte surprises"), "Everything your team needs, under one flat monthly rate"),
    (re.compile(r"on-site visits\s*(?:&mdash;|—|-)\s*no (?:à|&agrave;) la carte surprises on your invoice"), "on-site visits"),
    (re.compile(r"\s*(?:&mdash;|—)\s*(?:not|never) (?:an? |outsourced to an? )?(?:overseas |remote )?(?:script-read(?:er|ing)[^.<\"]*|call center script)(?=[.<\"])"), ""),
    (re.compile(r"Just an honest conversation about (?:your current setup|where your IT stands|your cloud)[^.<]*\."), "A conversation about your current environment and where it can improve."),
    (re.compile(r"we(?:'|’|&rsquo;)re minutes away, not hours\.(?: This is our home, and most of our clients are neighbors\.)?"), "our engineers are minutes away."),
    (re.compile(r"Real Engineers, No Call Centers"), "Answered by Our Own Engineers"),
    (re.compile(r"You(?:'|’|&rsquo;|&#39;)re in good hands\."), "Thank you for contacting us."),
    (re.compile(r"so technology stops being something you worry about"), "so that technology supports the business"),
]


def rewrite(seg):
    for rx, rep in RULES:
        seg = rx.sub(rep, seg)
    return seg


def process(t):
    a = t.find("<!-- /PL:HEADER -->")
    b = t.find("<!-- PL:FOOTER -->")
    if a < 0:                                # pages with their own layout (the Ads landing page)
        a = t.find("<body")
    if b < 0:
        b = len(t)
    out = t[:a] + rewrite(t[a:b]) + t[b:]
    return re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)',
                  lambda m: m.group(1) + rewrite(m.group(2)) + m.group(3), out, flags=re.S)


def main():
    check = "--check" in sys.argv
    files = sorted(glob.glob(os.path.join(ROOT, "*.html")) + glob.glob(os.path.join(ROOT, "m365-security-assessment", "*.html")))
    n = 0
    for f in files:
        raw = io.open(f, encoding="utf-8", newline="").read()
        new = process(raw)
        if new != raw:
            n += 1
            if not check:
                io.open(f, "w", encoding="utf-8", newline="").write(new)
    print("%s %d page(s)" % ("would change" if check else "changed", n))
    if check and n:
        sys.exit(1)


if __name__ == "__main__":
    main()
