#!/usr/bin/env python3
"""
chrome/company_name.py -- the company is always "Pro Link Systems" (Brian, iteration 4).

    python chrome/company_name.py            # rewrite
    python chrome/company_name.py --check    # list what is left, exit 1 if any

Rewrites the standalone shorthand "Pro Link" (never "Pro Link Systems" or the named "Pro Link Framework") to
"Pro Link Systems" in visible text, alt / aria-label / title / placeholder attributes, JSON-LD strings, and (only
where the length limits hold: title <= 60, meta description <= 160 rendered characters) the metadata. It never
touches verbatim quotations (blockquote, q, cite, and elements whose class says quote, review, testimonial, tst-),
links, file names, scripts, or the @ProLink_Systems handle. alternateName "ProLink" in structured data stays: it is
how the name is searched for. Titles that would pass 60 characters are left and listed.
"""
import glob
import html
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHORT = re.compile(r"\bPro Link\b(?! Systems| Framework)")
VISIBLE_QUOTES = re.compile(r"(?:quote|review|testimonial|tst-|persp-|\bgr-)", re.I)
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr", "path"}
POSS = re.compile(r"\bPro Link(?: Systems)?(&rsquo;|&#8217;|’|')s\b(?! Systems)")


def fix_text(s):
    s = POSS.sub(lambda m: "Pro Link Systems%s" % m.group(1), s)
    return SHORT.sub("Pro Link Systems", s)


def fix_attrs(tag):
    def one(m):
        return m.group(1) + m.group(2) + fix_text(m.group(3)) + m.group(2)
    return re.sub(r'(\b(?:alt|aria-label|title|placeholder)=)(")([^"]*)(?=")', lambda m: m.group(1) + m.group(2) + fix_text(m.group(3)), tag)


TOKEN = re.compile(r"(<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>|<[^>]+>)", re.S | re.I)


def body_text(segment):
    out, stack = [], []
    for part in TOKEN.split(segment):
        if not part:
            continue
        if part.startswith("<"):
            low = part.lower()
            if low.startswith(("<!--", "<style")):
                out.append(part)
                continue
            if low.startswith("<script"):
                out.append(re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)', lambda m: m.group(1) + fix_json(m.group(2)) + m.group(3), part, flags=re.S) if "ld+json" in low else part)
                continue
            m = re.match(r"<(/?)([a-zA-Z0-9]+)", part)
            if not m:
                out.append(part)
                continue
            closing, name = m.group(1), m.group(2).lower()
            if closing:
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i][0] == name:
                        del stack[i:]
                        break
                out.append(part)
                continue
            cls = re.search(r'class="([^"]*)"', part)
            quoted = name in ("blockquote", "q", "cite") or bool(cls and VISIBLE_QUOTES.search(cls.group(1)))
            in_quote = any(q for _, q in stack)
            out.append(part if (in_quote or quoted) else fix_attrs(part))
            if name not in VOID and not part.endswith("/>"):
                stack.append((name, quoted))
        else:
            out.append(part if any(q for _, q in stack) else fix_text(part))
    return "".join(out)


def fix_json(block):
    """JSON-LD string values; alternateName is kept as is."""
    lines = []
    for line in block.split("\n"):
        lines.append(line if "alternateName" in line else fix_text(line))
    return "\n".join(lines)


def meta_value(v, limit):
    new = fix_text(v)
    return new if len(html.unescape(new)) <= limit else v


def process(t):
    a, b = t.find("<head"), t.find("</head>")
    head, body = t[:b], t[b:]
    skipped = []

    def title(m):
        new = meta_value(m.group(2), 60)
        if new == m.group(2) and SHORT.search(m.group(2)):
            skipped.append("title kept (> 60): " + html.unescape(m.group(2)))
        return m.group(1) + new + m.group(3)
    head = re.sub(r"(<title>)(.*?)(</title>)", title, head, flags=re.S)
    head = re.sub(r'(<meta (?:name|property)="(?:og:title|twitter:title)" content=")([^"]*)(">)', lambda m: m.group(1) + meta_value(m.group(2), 60) + m.group(3), head)
    head = re.sub(r'(<meta (?:name|property)="(?:description|og:description|twitter:description)" content=")([^"]*)(">)', lambda m: m.group(1) + meta_value(m.group(2), 160) + m.group(3), head)
    head = re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)', lambda m: m.group(1) + fix_json(m.group(2)) + m.group(3), head, flags=re.S)
    return head + body_text(body), skipped


def targets():
    files = []
    for pat in ("*.html", "blog/*.html", "case-studies/*.html", "leadership/*.html", "m365-security-assessment/*.html"):
        files += glob.glob(os.path.join(ROOT, *pat.split("/")))
    files += [os.path.join(ROOT, "chrome", "header.html"), os.path.join(ROOT, "chrome", "footer.html")]
    return sorted(set(files))


def main():
    check = "--check" in sys.argv
    changed, left = 0, []
    for f in targets():
        raw = io.open(f, encoding="utf-8", newline="").read()
        crlf = "\r\n" in raw
        t = raw.replace("\r\n", "\n")
        if os.path.basename(f) in ("header.html", "footer.html"):
            new, skipped = body_text(t), []
        else:
            new, skipped = process(t)
        rel = os.path.relpath(f, ROOT)
        left += ["%s: %s" % (rel, s) for s in skipped]
        if new != t:
            changed += 1
            if not check:
                io.open(f, "w", encoding="utf-8", newline="").write(new.replace("\n", "\r\n") if crlf else new)
    print("%s %d file(s)" % ("would change" if check else "changed", changed))
    for l in left:
        print("  " + l)
    if check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
