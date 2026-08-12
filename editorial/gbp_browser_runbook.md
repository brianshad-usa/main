# GBP browser-posting runbook (interim, until Google approves API access)

Followed by the scheduled Claude task "ProLink GBP post" (Mon/Wed/Fri 10:20 AM
Pacific). Purpose: publish the GBP copy that the CI editorial run generated at
10:00 AM, using Brian's logged-in Chrome, exactly once per manifest.

**Retire this whole mechanism** the day the `GBP_*` secrets are set in the
`brianshad-usa/main` GitHub repo — then CI posts via the API and this task must
be deleted (double-posting risk otherwise).
Check first: if the latest CI "Social Posts" run log shows `[posted] GBP`,
the API path is live — delete the scheduled task, do not post.

## Steps

1. `git -C C:\Users\brian.shad\prolink-landing-page\main pull --rebase origin main`
2. Find the newest `editorial/manifests/<date>-<idea>.json`. Manifest dates are
   stamped in UTC by CI, so the newest may be dated one day ahead of Pacific
   time. Rule: post it only if its date is within the last 2 calendar days;
   older means the CI run failed or hasn't run — stop and report; do NOT post
   stale copy.
3. Read `editorial/gbp_posted.json`. If the newest manifest's stem is already
   recorded, stop (already posted) and report "nothing to do".
4. From the manifest take:
   - `channels.gbp` — the post text (plain text; verify: no hashtags, no
     markdown; if it somehow has either, strip them)
   - `cta_type` / `cta_url` — the button (LEARN_MORE → "Learn more" etc.)
   - `image_file` — the card PNG in `social/` (local path after the pull)
5. **ASSISTED MODE** (current mode — Claude's browser tools are policy-blocked
   on www.google.com, where Google now hosts the only post-compose UI; verified
   2026-08-09 with extension site access set to "all sites"):
   - Put the post text (`channels.gbp`) on the system clipboard
     (computer-use `write_clipboard`).
   - In Chrome, open `https://business.google.com/locations` and click
     **See your profile** on the row for the VERIFIED service-area business
     named "Pro Link Systems" (Irvine/Orange + 18 other areas). Every other
     row is permanently closed or unverified — never touch those. The click
     opens the profile manager in a google.com tab; Claude cannot see that
     tab, but Brian can.
   - Notify Brian: the post text is on the clipboard, ready to paste into
     **Add update**; name the card image to attach
     (`C:\Users\brian.shad\prolink-landing-page\main\social\<image_file>`)
     and the CTA button + URL to set. Include the full post text in the
     notification body as backup (clipboards get overwritten).
   - If google.com access is ever granted to the browser tools, revert to
     full-auto: compose, attach, set CTA, publish, and verify in the Updates
     list directly.
6. Append to `editorial/gbp_posted.json` `posts`:
   `{"stem": "<date>-<idea>", "staged": "<ISO timestamp>",
     "method": "assisted-clipboard", "cta": "<cta_type>"}`
   (The auto-commit watcher pushes this within a minute — no git commands
   needed.) A staged entry counts as handled — never re-stage a recorded stem;
   the notification is Brian's to act on.
7. Report: staged/skipped/failed + the post text. If Chrome or the Google
   session is unavailable, DO NOT retry blindly — report the blocker and leave
   the manifest unposted; the next scheduled run picks it up via the ledger gap.

## Guardrails

- Never post the same stem twice (the ledger is the source of truth).
- Never post copy that names a client or contains a statistic not in
  `editorial/verified_facts.json` — if found, stop and flag (the CI gate should
  make this impossible; treat an occurrence as a pipeline bug).
- Never post during an active local fire event if the copy is
  continuity/disaster-themed (standing campaign rule); skip and report instead.
- One post per scheduled run, ever. No catch-up batches: if two manifests are
  unposted, post only the newest and report the gap.
