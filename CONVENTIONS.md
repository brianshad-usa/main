# CONVENTIONS.md — prolinksystems.com

**Every session (human or AI) must read this file before changing anything in this
repo or in `C:\Googleads`.** It records load-bearing decisions and their reasons.
Violating these breaks things that were deliberately fixed. If you make a new
material decision, append it here in the same format, same commit.

Automated enforcement: `site_guard.py` runs on every push (GitHub Actions) and
fails the build on violations of the checkable rules below. Do not weaken or
bypass the guard; fix the content instead.

---

## Secrets & credentials

- **No secret ever appears in a `.py`, `.html`, `.md`, `.yml`, or prompt/briefing.**
  All credentials live in `C:\Googleads\secrets.env`, loaded via `config.py`
  (`get()` / `get_google_ads_client()`). Reference secrets by location, never by value.
  History: three live credentials were leaked by pasting them into briefings; all
  were rotated and the codebase refactored (June 2026).
- `secrets.env` is never committed, synced, uploaded, or pasted anywhere.
- Google Ads scripts authenticate with the **client account (4318939692) as
  `login_customer_id`** — using the MCC there causes permission errors.
  Exception: `run_campaign_prolink.py`-style account-creation flows used the MCC;
  those scripts are deleted and must not be recreated casually.
- Azure/Microsoft credentials (review agent) are separate from Google credentials.
  Never mix the two; a Google client ID pasted into `MS_CLIENT_ID` broke the agent once.

## Domain & hosting

- **Apex domain only** (`https://prolinksystems.com`). Every canonical, sitemap URL,
  internal link, and schema URL uses apex. No `www.` anywhere in source.
- www → apex is a **301 Redirect Rule in the Cloudflare dashboard**, NOT in
  `_redirects` (Pages `_redirects` cannot match hostnames — a rule there is dead config).
- `_redirects` holds ~42 path rules (`.html` → clean URL canonicalization).
  **Preserve them exactly**; never wipe, reorder, or "clean up" this file.
- `_headers` carries `Strict-Transport-Security: max-age=31536000` — deliberately
  no `includeSubDomains`, no `preload`. Do not add them without explicit approval.
- `404.html` in repo root is the custom 404 (Pages serves it with real 404 status).
  It stays `noindex` and out of the sitemap.
- Cloudflare **Email Address Obfuscation is ON** by design; the resulting
  `/cdn-cgi/l/email-protection` "404s" in crawl reports are false alarms.
  `robots.txt` disallows `/cdn-cgi/` for this reason — keep that line.

## HTML / SEO invariants (guard-enforced)

- Meta descriptions ≤ 160 chars (target 120–155), unique per page.
- Titles ≤ 60 chars, primary keyword first.
- Exactly one `<h1>` per page; heading levels never skip (H2→H3, not H2→H4).
  The shared footer uses H3 **by design** (was H4; caused site-wide skips).
- Every page: canonical tag (apex), meta description, valid JSON-LD.
- JSON-LD must parse; `ServiceChannel.servicePhone` must be a ContactPoint object,
  not a string (failed validation once).
- Indexable pages appear in `sitemap.xml`; noindexed pages do not.
- Superseded/duplicate pages are noindexed + canonicaled to their replacement,
  never deleted (links may exist).

## Blog generator (`generate_blog.py` + GitHub Action)

- **Topic tracking (`used_topics.json`) is mandatory** — the generator once wrapped
  around its topic list and republished four posts as duplicates. Never bypass;
  on topic exhaustion it must fail loudly, not recycle.
- **Output validation is mandatory**: model-written HTML is untrusted. The
  sanitize (`normalize_heading_tags`) + `validate_post_html` gate stays; on
  failure the post is not written and the run exits non-zero. History: the model
  emitted `</hh2>`; a legacy footer template left stray `</div>`s in 9 posts.
- New posts are **answer-first**: direct 2–3 sentence answer in the first 40 words,
  Key Takeaways box, question-phrased H2/H3s.
- Topic queue focuses on **core managed IT services** (M365, cloud, migrations,
  cybersecurity, network, IT management for 10+ employee companies).
  CMMC/compliance is a secondary vertical, not the lead.

## Content & positioning

- Never claim Pro Link "certifies" CMMC compliance — certification is done only
  by independent C3PAOs. Pro Link prepares and manages environments.
- No fabricated statistics, clients, reviews, or testimonials, ever.
  Named testimonials require documented client permission.
- One CTA per page/post (free discovery/assessment call → /contact).

## Google Ads (`C:\Googleads` scripts)

- RSAs cannot be edited in place: create the new ad **first**, then remove the old,
  so an ad group is never empty.
- High-intent ad groups point to matched landing pages
  (`/managed-it-services`, `/helpdesk-it-support-los-angeles`), never the homepage.
- Permanent scripts: `config.py`, `check_status.py`, `campaign_report.py`,
  `quality_scores.py`, `weekly_optimization.py`, `generate_refresh_token.py`,
  `review_request_agent.py`. Seven one-time setup scripts were deleted July 2026
  (campaign builders, sitelink/negative one-offs) — re-running their logic creates
  duplicates; don't recreate them without checking current account state first.
- `weekly_optimization.py` edits its negatives/pause lists **before** each run;
  as-is it re-applies old changes.

## Review agent

- 5 emails/day max, one follow-up per contact after 10+ days, never a second.
- `reviewed.txt` (one email/line) permanently excludes responders — check it before
  any send-logic change.
- CAN-SPAM footer (physical address + opt-out) stays in every template.

## Infrastructure

- `auto-commit.ps1` + `auto-commit.log` live **outside the repo** deliberately
  (a self-committing log would loop the watcher). Registered as Scheduled Task
  "ProLink Auto-Commit Watcher" (logon trigger, 999 restarts). Uses
  `GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`, 120s kill-tree timeout —
  it once hung 7.5 hours on a credential prompt. Keep a backed-up copy when edited.
- PowerShell 5.1: `Start-Process -PassThru` ExitCode is unreliable; use
  `System.Diagnostics.Process` for exit codes.
- The GitHub Actions blog cadence is temporarily every-2-days; revert to monthly
  when content base is sufficient.

## Session workflow

- Prompts to implementation sessions are **bounded**: "don't touch anything beyond
  what's specified." Preserving existing material (e.g., the 42 redirects) beats
  literal spec compliance — flag conflicts instead of destroying data.
- Every session reports diffs + verification (curl checks, counts, hashes) back
  for cross-session review before the work is considered done.
- When counting things in reports, state the unit (lines vs rules vs files).

*Last updated: August 2026. Append new decisions below this line.*
