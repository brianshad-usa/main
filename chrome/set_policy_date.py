#!/usr/bin/env python3
"""
chrome/set_policy_date.py -- stamp the privacy policy's effective date on release day.

The revised policy (approved by counsel, 2026-11-25) shows its effective date in two places, both marked
<time data-policy-effective ...>: the page header and the change-log entry. Until release they read "on publication".
Run this in the release commit, with the date the policy actually goes live (Pacific):

    python chrome/set_policy_date.py 2026-12-01      # writes "December 1, 2026" and datetime="2026-12-01"
    python chrome/set_policy_date.py --check         # exit 1 while the date is still unset (golive_check 15 does this too)

It changes nothing else in the approved wording.
"""
import datetime as dt
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "privacy.html")
RX = re.compile(r'<time data-policy-effective(?: datetime="([^"]*)")?>([^<]*)</time>')


def unset(text):
    tags = RX.findall(text)
    return not tags or any(not dtv for dtv, _ in tags)


def main():
    text = io.open(PAGE, encoding="utf-8", newline="").read()
    if "--check" in sys.argv:
        if unset(text):
            print("privacy.html: effective date not set (run python chrome/set_policy_date.py YYYY-MM-DD on release day)")
            sys.exit(1)
        print("privacy.html: effective date set: %s" % RX.search(text).group(1))
        return
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    day = dt.date.fromisoformat(sys.argv[1])
    label = "%s %d, %d" % (day.strftime("%B"), day.day, day.year)
    n = len(RX.findall(text))
    if n != 2:
        sys.exit("expected 2 <time data-policy-effective> tags in privacy.html, found %d" % n)
    text = RX.sub(lambda m: '<time data-policy-effective datetime="%s">%s</time>' % (day.isoformat(), label), text)
    io.open(PAGE, "w", encoding="utf-8", newline="").write(text)
    print("privacy.html effective date set to %s" % label)


if __name__ == "__main__":
    main()
