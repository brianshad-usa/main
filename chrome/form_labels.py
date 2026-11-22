#!/usr/bin/env python3
"""
chrome/form_labels.py -- connect every lead-form label to its field (WCAG 1.3.1 / 4.1.2). Idempotent.

    python chrome/form_labels.py [--check]

Adds for="lead-<name>" to a bare <label> that directly precedes an input, select or textarea, and id="lead-<name>" to a
field without an id. Field names, handlers, Turnstile and existing ids are never changed. Also removes the trailing dash
left in three form introductions.
"""
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAIR = re.compile(r"<label(?P<la>(?:(?! for=)[^>])*)>(?P<txt>(?:(?!</label>).)*)</label>(?P<sp>\s*)<(?P<tag>input|select|textarea)\b(?P<at>[^>]*)>", re.S)
FORM = re.compile(r"<form\b.*?</form>", re.S)


def fix_form(form, used):
    def one(m):
        at = m.group("at")
        if re.search(r'\btype="(?:hidden|checkbox|radio)"', at):
            return m.group(0)
        name = re.search(r'\bname="([^"]+)"', at)
        idm = re.search(r'\bid="([^"]+)"', at)
        if idm:
            fid = idm.group(1)
        elif name:
            base = "lead-" + re.sub(r"[^a-z0-9]+", "-", name.group(1).lower())
            fid, n = base, 2
            while fid in used:
                fid, n = "%s-%d" % (base, n), n + 1
            used.add(fid)
            at = " id=\"%s\"%s" % (fid, at)
        else:
            return m.group(0)
        return "<label for=\"%s\"%s>%s</label>%s<%s%s>" % (fid, m.group("la"), m.group("txt"), m.group("sp"), m.group("tag"), at)
    return PAIR.sub(one, form)


def process(t):
    used = set(re.findall(r'\bid="([^"]+)"', t))
    t = FORM.sub(lambda m: fix_form(m.group(0), used), t)
    return re.sub(r"\s*(?:&mdash;|—)\s*(?=</p>)", ".", t) if re.search(r"(?:production running|your firm needs|for your firm)\s*(?:&mdash;|—)\s*</p>", t) else t


def main():
    check = "--check" in sys.argv
    n = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
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
