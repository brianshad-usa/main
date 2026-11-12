"""Bump the ?v= on every link to _shared.css (root pages, blog/ pages, generate_blog.py).

Run this whenever _shared.css changes:  python bump_shared_css.py 20261112
(any 8-digit date, optionally + one letter for a second bump the same day, e.g. 20261112b)

Why: CSS is served with Cache-Control max-age=86400 + stale-while-revalidate (see _headers),
and Cloudflare's edge keeps the copy it cached for up to a day. Without a new ?v= a stylesheet
change reaches visitors up to 24 h late (2026-11-12: the phone-layout and 16px-input rules
were invisible on the live industry pages until the link was versioned).
Files are rewritten byte-for-byte except the href, so CRLF/LF endings are preserved.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HREF = re.compile(r'href="(/?)_shared\.css(?:\?v=[^"]*)?"')


def main() -> int:
    if len(sys.argv) != 2 or not re.fullmatch(r"\d{8}[a-z]?", sys.argv[1]):
        print(__doc__)
        return 2
    version = sys.argv[1]
    targets = sorted(ROOT.glob("*.html")) + sorted(ROOT.glob("blog/*.html")) + [ROOT / "generate_blog.py"]
    changed = refs = 0
    for path in targets:
        text = path.read_bytes().decode("utf-8")
        new, n = HREF.subn(lambda m: f'href="{m.group(1)}_shared.css?v={version}"', text)
        refs += n
        if new != text:
            path.write_bytes(new.encode("utf-8"))
            changed += 1
    stale = [p.name for p in targets if re.search(r'href="/?_shared\.css"', p.read_bytes().decode("utf-8"))]
    print(f"{changed} files updated, {refs} links now _shared.css?v={version}; unversioned left: {stale or 'none'}")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
