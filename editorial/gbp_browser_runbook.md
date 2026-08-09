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
5. In Chrome (Claude in Chrome; Brian's profile is signed into the Google
   account that manages the Pro Link Systems profile):
   - Go to `https://business.google.com/` and open the Pro Link Systems
     location (it may redirect to the profile manager embedded in Google
     Search — both work).
   - Choose **Add update** (a.k.a. "What's New" post).
   - Paste the post text. Attach the card image from
     `C:\Users\brian.shad\prolink-landing-page\main\social\<image_file>`.
   - Add the CTA button mapped from `cta_type`, with `cta_url`.
   - **Post it.** Then verify it appears in the profile's Updates list.
6. Append to `editorial/gbp_posted.json` `posts`:
   `{"stem": "<date>-<idea>", "posted": "<ISO timestamp>", "method": "browser",
     "cta": "<cta_type>"}`
   (The auto-commit watcher pushes this within a minute — no git commands needed.)
7. Report: posted/skipped/failed + the post text. If Chrome or the Google
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
