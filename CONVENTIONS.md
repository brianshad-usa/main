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
- `llms.txt` lists every indexable top-level (non-blog) page and no listed URL
  404s (guard check 18). Blog posts are covered by the single `/blog/` link and
  the homepage is the file header, so both are exempt. `update_site_links.py`
  only auto-syncs LOCATION pages into llms.txt — new service/guide/resource
  pages need a manual llms.txt entry (the guard now enforces this).
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

## Google Cloud project & API credentials (2026-08-19)

- All Google API OAuth lives in ONE Cloud project: **"ProLink - Sandbox"**
  (being renamed "ProLink Marketing APIs"), project number **6748977141**,
  owned by brianshad@gmail.com. It holds the "ProLink Ads client" OAuth client.
  **Never migrate this client to another project** — OAuth clients can't move,
  and re-minting would touch the working Ads pipeline. Enabled APIs there:
  Google Ads, Search Console, Places (classic).
- Search Console property is **URL-prefix `https://prolinksystems.com/`**
  (NOT sc-domain), owner brianshad@gmail.com.
- **Dual secret stores**: `C:\Googleads\secrets.env` (local scheduled tasks)
  AND GitHub Actions secrets on `brianshad-usa/prolink-warroom` (cloud
  workflows refresh.yml / cmo-weekly.yml). Any re-minted token or new key
  (esp. GSC_REFRESH_TOKEN, GOOGLE_PLACES_API_KEY) must be updated in BOTH,
  or local and cloud dashboards silently diverge.
- `dashboard/generate_gsc_token.py` pins login_hint=brianshad@gmail.com,
  supports `--no-browser` (paste URL into the right browser profile), and
  prefers GSC_CLIENT_ID/GSC_CLIENT_SECRET when set (falls back to Ads client).

## Review-request agent (2026-08-19)

- Template is approval-locked: gratitude-led opening named to the client's
  company (never "thank you for your business"), ONE Google link only, fixed
  subject "A quick favor, {first}?" (no emoji), two-minute friction line.
  Optional per-contact `relationship` field — ONLY verified tenure (Snitzer
  18yr, Waverly 23yr); never invent history.
- `reviewed.txt` (one email/line) = responders, permanently excluded from
  follow-ups. Check it AND the sent list in review_tracking.json before
  loading any new batch (Batch-4 load caught 2 duplicates).
- Sending runs via Scheduled Task "ProLink Review Requests" (weekdays 9am,
  5/day, self-stops on empty queue). New batches: append to CONTACTS and the
  schedule picks them up — do not create parallel senders.

## War-room coordination (2026-08-19)

- `C:\Googleads` is repo brianshad-usa/prolink-warroom (branch war-room) with
  its OWN auto-sync — assume anything you write there reaches GitHub within
  ~1 minute, and cloud workflows execute the repo's code.
- `dashboard/tasks.yaml`: claim task ids via the "NEXT FREE ID" header line,
  incremented IN THE SAME EDIT that adds tasks (T25/T26 were double-assigned
  by two sessions on 8/11; ads tasks were renumbered T31-T36).
- Every meaningful Google Ads change gets a row in the Change Ledger in
  `ADS_COMMAND_CENTER.md` (§3) with an evaluation date. Auction insights are
  API-gated — refresh the §4c snapshot monthly via the Ads UI.
- Local scheduled tasks on Brian's PC: "ProLink Weekly Conversions" (Mon 8am),
  "ProLink Marketing Dashboard" (Mon 8am, registered 8/18), "ProLink Review
  Requests" (weekdays 9am). Don't duplicate these in new automations.

## Location pages & GBP (2026-10-08)

- **Location-page template = `managed-it-services-glendale.html`** (Sep-2026
  deployment: LocalBusiness+GeoCoordinates, BreadcrumbList, 5-Q FAQPage,
  Organization, Speakable WebPage, "Nearby service areas" section). New city
  pages are built from it with `gen_location_pages.py` (content in CITIES;
  refuses to overwrite without `--force`). Don't hand-fork an older page.
- **Canonical footer city list lives in `gen_location_pages.FOOTER_AREAS`**
  (39 cities as of 10/8: batch 1 = Tarzana, Agoura Hills, Studio City, North
  Hollywood, Santa Clarita, Simi Valley, Downtown LA, West LA; batch 2 = Playa
  Vista, Hollywood, Koreatown, Hawthorne, Manhattan Beach, Sun Valley, San
  Gabriel Valley, Camarillo, Malibu). Meta descriptions must be <=160 chars --
  the guard enforces it; write them to the 120-155 target the first time.
- `site_guard.py` takes ~3 min on the mounted drive from a sandbox but ~2 s
  locally; run it locally or copy the tree to /tmp first. After adding a page, run `update_site_links.py` -- it syncs the
  footer in every root page, every blog post AND `generate_blog.py` (the blog
  template had drifted to a 16-city list, leaving newer pages under-linked),
  plus sitemap, `_redirects` (.html -> clean URL), and `llms.txt`. Idempotent.
- Every location page must have a `_redirects` rule; six pages shipped without
  one (chatsworth, culver-city, long-beach, northridge, van-nuys, west-hills)
  and were fixed 10/8. The sync script now catches this.
- GBP service area is capped at 20 places and is NOT the site's city list;
  site pages can exceed it. GBP read/apply scripts: `gbp_audit.py` (read-only),
  `gbp_apply_batch1.py` / `gbp_apply_batch2.py` (validate-first, backup JSON
  before any write), `gbp_reviews.py` (fetch unreplied -> draft -> post).
  Primary-category changes are made manually in the dashboard, solo.

## Microsoft UET tag / Bing Ads conversions (2026-10-12)

- **Microsoft UET base tag `ti=97275167`** is on every page, placed DIRECTLY AFTER
  the Google `gtag.js` block in `<head>` (incl. `generate_blog.py`'s post AND index
  templates, so new blog posts carry it). The tag id is public by design — no
  secret. Idempotency marker: `ti:"97275167"`. Deployed site-wide via a one-shot
  content-anchored script (anchor = the gtag include + its inline-config
  `</script>`), 162 pages.
- **Conversion events mirror the Google events and live where the gtag event
  actually fires now**, NOT where `UET_DEPLOYMENT_SPEC.md` (2026-10-12) assumed:
  - Form success `uetq.push('event','submit_lead_form')` → in **`contact-form.js`**
    (shared handler, 15 pages) beside the gtag form-conversion, and in
    **`contact.html`**'s inline success branch. The per-page inline
    `gtag_report_conversion()` snippets are **dead** (the capture-phase
    `contact-form.js` overrides submit and fires the conversion itself), so a UET
    push there would never run — do not add one.
  - Phone click `uetq.push('event','phone_call_click')` → beside the gtag
    `tel:` click-conversion (`AW-1068497497/LKCuCL275MkcENn0v_0D`) in the 108
    pages that carry the delegated tel: listener.
- Spec §2c (it-help-desk "UET event goes here" placeholder) was moot:
  `it-help-desk.html` has **no form** — it gets base + phone only, like any page.
- Turnstile blocks automated form submits, so the `submit_lead_form` beacon can't
  be self-tested from a headless browser — confirm it with a real human submit or
  the UET Tag Helper. Base-tag `bat.js` load IS verifiable on any page load.

## SEO / local-search push (2026-10-14)

- **City-page titles/H1s are dual-intent**: "Managed IT Services & IT Support {City} |
  Pro Link" / H1 "Managed IT Services & IT Support in {City}, CA". GSC + Ahrefs showed
  "it support {city}" and "it services {city}" OUT-volume "managed it services {city}"
  (Pasadena 600 vs 300/mo, Burbank 600, Irvine 700) while every title targeted only
  the latter. `gen_location_pages.py` was synced to the live pages on 2026-10-14
  (CITIES titles/metas = live values; `body()` H1 + the Nearby `/case-studies` proof
  link patched; render-tested), so new CITIES entries and `--force` regenerations
  inherit the formula — write new entries' title/meta in the same dual-intent form
  (<=60 / <=155 rendered chars). Sync method: copy live page values INTO CITIES
  (the live page is the source of truth), never the reverse.
- **Cannibalization split**: `/managed-it-services` (hub) owns "Managed IT Services
  Los Angeles"; `/managed-it-services-los-angeles` owns "IT Support Los Angeles". The
  hub was **"Crawled – currently not indexed"** (Google treated it as a duplicate of
  the LA page) despite 142 inbound links. Fixed by differentiating it (title/H1, a
  6-Q FAQ section with FAQPage + LocalBusiness + BreadcrumbList schema) and making it
  the FIRST footer "Services" link site-wide plus a homepage link. **Request
  Indexing must be done in the GSC UI** — the API's URL Inspection is read-only.
- Meta descriptions use only verifiable hooks: flat-rate, "no long-term contracts"
  (never "no contracts" — there is an MSA), since 1999, "Rated 4.9/5 on Google"
  (the live GBP rating). No aggregateRating markup: Google ignores self-serving
  review stars on LocalBusiness/Organization.
- Every city page now carries Speakable, office GeoCoordinates (34.1684, -118.5997
  = the HQ; never fake per-city coords), a "Nearby service areas" section and a
  `/case-studies` proof link. `update_site_links.py` NEARBY_ADD only appends to
  existing Nearby blocks; `apply_cs2`-style inserts are needed for pages without one.
- Local pack reality: Pro Link is ABSENT from the Woodland Hills local pack (its own
  city — TeamLogic IT / Intelligent IT / Heed hold it) and Places returns no IT
  category type for the listing. GBP primary/secondary categories are a manual,
  solo dashboard task (see GBP rule above) — the highest-impact lead lever outside
  the site. Pages at organic #3–7 earned ZERO clicks because the local pack + AI
  answers sit above them; measure clicks + position on money queries, not impressions.

## Autonomous SEO/GEO/AEO engine (2026-10-14)

- The engine lives in the PRIVATE war-room repo (`prolink-warroom/seo/`, workflow
  `seo-daily.yml`, 15:15 UTC daily + manual dispatch). It checks this repo out with
  the `SITE_REPO_PAT` secret and **only ever opens pull requests** — it never pushes
  to `main`, so the desktop auto-commit watcher and the engine cannot race.
  LOW-risk fixes → PR labelled `automerge`; MEDIUM → `needs-review`; HIGH/external
  → a rolling monthly GitHub issue. Reports, intelligence, ledger and state stay in
  the war room (this repo is public — never put reports or strategy here).
- `pr-checks.yml` runs `site_guard.py` on every pull request. Make it a REQUIRED
  status check in branch protection BEFORE flipping `seo/config.json →
  risk_policy.low_auto_pr` to true; GitHub auto-merge merges instantly when no
  checks are required.
- Engine commits are authored `prolink-seo-engine`. If the guard ever fails on
  `main` within 48h of an engine merge, the engine blocks further changes and names
  the commit to revert (rollback = revert PR).
- Daily audits run on the local checkout (complete, quota-free); `site_guard.py`
  remains the invariant gate and must not be weakened to make an engine fix pass.
