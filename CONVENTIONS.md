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
- One CTA per page/post (free discovery/assessment call → /contact). Ad landing pages and
  industry pages may also embed the shared lead form (contact-form.js); buttons still go to /contact.

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

## Lead forms — rules after the Sep–Nov 2026 lead drop (2026-11-09)

Genuine form leads went 7 (Jul 27–Sep 17) → 0 for 7½ weeks with nobody noticing
(diagnosis: `C:\Googleads\LEAD_DROP_FINDINGS_2026-11-09.md`). The forms are now
fail-safe and measured; keep them that way:
- **Only name + email are required** — in `functions/api/contact.js` (`REQUIRED`),
  `contact-form.js` and `contact.html`'s inline `validate()`. Never re-add required
  fields; every one costs leads (the contact page had six). The **labels must match**:
  only name/first-name/email carry `<span class="req">*</span>`; no other field gets an
  asterisk or a `required` attribute (15 of 16 forms still showed phone/company/last-name
  asterisks until the 2026-11-09 sweep). **Enforced by `site_guard.py` check 19.**
- **Cache-buster:** pages load `/contact-form.js?v=YYYYMMDD`. Browsers keep the script
  for 24 h + 7 d stale (`_headers`), so **bump `?v=` on all 15 pages whenever
  `contact-form.js` changes** — an unversioned reference fails check 19.
- **Turnstile siteverify never sends `remoteip`** (an IP that differs between the
  widget and the POST — iCloud Private Relay, mobile, corporate proxies — must not
  cost a lead). No token / forged token (`invalid-input-response`) → rejected.
  Stale token (`timeout-or-duplicate`), `internal-error`, or Cloudflare unreachable
  → the lead still goes to info@ as **`[UNVERIFIED] New Contact Form Submission…`**
  with NO visitor confirmation (keeps the path useless for relay abuse).
- Every notification carries **"How they found us"** (channel, landing page, first
  referrer, UTMs, gclid/msclkid, approx. location, device) from the session's first
  touch (`sessionStorage.pls_first_touch`, written by both form scripts).
- GA4 events: `form_submit_attempt`, `form_error` (`reason`: validation /
  turnstile_missing / server_4xx|5xx / network), `generate_lead` (key event).
  The SEO-intel collector stores `ga4.form_funnel_7d`; the engine raises
  `LEADS-form-failing` when attempts ≥ 3 with 0 leads, or errors ≥ 3, in 7 days.
- Function logs one JSON line per submission (`evt: "contact"`, outcome, reason/codes,
  page, ref, channel) → Cloudflare Pages → Functions → real-time logs.
- Both form scripts **wait up to 8 s for the Turnstile token** before complaining.
- Any form/handler/Function change: test in a scratch copy, run `site_guard.py`,
  then a **human** submit on mobile (cellular) + desktop, and confirm the info@
  notification shows the attribution block.
- Ads landing page (`/managed-it-services`) + home: Hotjar + Clarity load on the
  first scroll/tap/key or after 6 s (main-thread time = Ads landing-page experience).
  Keep `/managed-it-services` LA-focused — it is the Google + Microsoft Ads landing
  page; the LA city page carries organic "managed IT services Los Angeles".
- **City pages carry the shared form (2026-11-11).** All 39 location pages
  (`managed-it-services-*.html` + `it-support-burbank.html`) have the standard lead form in
  a `#talk-to-us` section above the FAQ (styles in `/lead-form.css?v=…`, handler
  `/contact-form.js?v=…` + Turnstile), and their hero / CTA-band "free assessment" buttons
  scroll to it instead of sending people to /contact. `gen_location_pages.py` emits the same
  section and anchors. **Check 19 now fails any page with a Turnstile form that does not load
  `/contact-form.js?v=` and the Turnstile script** (contact.html excepted: it has its own
  inline handler): without them the form POSTs to the page itself and the lead is lost.

## Home page, video and visual standards (2026-11-12)

- **Hero = one message + one proof line + two actions + the form.** Eyebrow, H1, a one-sentence
  verified-facts subhead, "Call 1-800-890-6133" + "Watch our story", and a proof row (4.9 on
  Google · in-house US help desk · 90% first contact). No video, carousel or bullet grid in the
  hero — the old video-first hero showed visitors a blank dark box until the video loaded.
- **Videos live in `#see-us-work`** below the stats strip, every entry has a `poster`
  (`/assets/video/<name>-poster.webp`, 1280×720 frames chosen from the video), the `<video>`
  is `preload="none"`, and the first video only loads when the carousel is about to scroll into
  view (IntersectionObserver) — it used to pull a 19 MB file on every home-page visit. Clicking
  a list item or the poster starts that video with sound. New testimonial video: add an entry
  to `VIDEOS` with `src`, `poster`, `title` (plain characters — titles are set as text, entities
  show literally), `badge`, plus a button in `#see-us-list`.
- **Real photos only.** People imagery comes from `assets/photos/` (the 2026 brand shoot,
  registered in `assets/variety_assets.json`) — never stock or AI images of "our team".
  Web copies go in `assets/photos/web/` as WebP with width/height set. `assets/gbp/` frames
  carry a logo watermark: fine for the Business Profile, avoid on the website. **Captions and
  alt text describe only what is visible** (a technician in a Pro Link polo helping someone) —
  never a location, team or role nobody has confirmed: some shoot frames (`lab_consult`,
  `tech_workbench`) were clearly taken in a client's lab, so "our help desk team, Woodland Hills"
  was replaced on 2026-11-12. In use: home why-us card (`team-dual-monitor.webp`), About story
  (`deskside-support-{720,1100}.webp`, srcset).
- **Readable sizes:** body/card copy ≥ 16px (`.card p` 1rem), form inputs 16px (smaller makes
  iPhones zoom the page on tap), labels ≥ .8rem. Bump `?v=` on `lead-form.css` /
  `contact-form.js` when they change (CSS/JS cache 24 h + 7 d stale). The 16px input size is
  enforced site-wide by the last rule in `_shared.css` (`!important`, because many pages style
  their forms inline after it loads) — industry pages were 13px and contact 14.4px before it.
- **No sideways scroll on phones.** Every page must fit a 390px-wide screen. `_shared.css` stacks
  inline two-column grids written `grid-template-columns:1fr 1fr;gap:4x/5x/6x` (the industry pages'
  text + visual blocks) at ≤860px; it matches the inline style text, so write inline grids without
  spaces, or better, use a class with its own media query. Pages that don't load `_shared.css`
  carry their own rule (the Ads landing page: `.lp-section [style*=...]`; `case-studies.html`: a
  ≤700px block). Never put `white-space:nowrap` on a sentence-length link. Check on 2026-11-12:
  7 of 87 pages overflowed (case-studies 120px, manufacturing 157px, technology 101px,
  financial 54px, healthcare 43px, law 32px, home 19px) → 0.
- **Testimonial attribution:** a quote shown under a client's name must be traceable to that
  client (their Google review, their own words in their video, or a written approval). The Ads
  landing page video cards had "first ring… back up in under an hour" (Optical Zonu, "David R.")
  and "a real engineer answers the phone" (Waverly, "Michael T.") with invented initials, and
  Alan B. Snitzer's Google review under "LM" — fixed 2026-11-12 (captions for the videos, the
  Snitzer review credited to him). Check the reviews with the GBP v4 API before quoting anyone.
- **Check 21 (site_guard):** every classic inline `<script>` must parse (one Node process
  compiles them; skipped with a NOTE if Node is missing). Added after a `/* … */` note written
  inside an existing block comment broke the home page's whole script block for a day.

## No compliance advertising + verified claims only (2026-11-09)

Owner (Brian, 2026-11-09): **"I don't want to advertise any compliance work as we mostly
outsource it."** Applies to ads, landing pages, site copy, the Business Profile and every
generator (blog, GBP posts, social, SEO engine).
- **Never** claim a compliance status ("HIPAA-compliant/ready", "SOC 2 aligned", "HITECH
  compliant", "Full compliance") or sell compliance delivery ("BAA included", "CMMC
  documentation", "risk analysis", "we prepare you for audits/assessments", "compliance
  assistance"). Describe the IT side instead (encryption, access controls, MFA, patching,
  monitoring, documented environment, restore-tested backups). At most one honest line per
  page: "we work alongside your compliance advisor and handle the IT side". Informational
  explanations of a regulation (blog, the LA cyber report) are fine. **Pro Link signs BAAs
  with healthcare clients** (Brian, 2026-11-10; verified fact F015) — state it plainly as a
  contractual fact (the healthcare page does), never as a compliance service or in ads.
- **Claims come only from `editorial/verified_facts.json`** (master: war room
  `cmo/verified-facts.json`): F003 is always "average ticket first-response time: 15
  minutes" (never "under 15 minutes", "within 15 minutes", "&lt;15m"); no "500+", "99.9%
  uptime", "uptime SLA/guarantee", "guaranteed response", "Fortune 1000" (except the factual
  Cunico/BWX description), "month-to-month", "no contracts" (there is an MSA). Unsourced
  industry statistics are removed or given a named, dated source. **Confirmed 2026-11-10:**
  unlimited support on managed plans (F016) and same-day on-site support when needed (F017;
  say "when needed", not a promise for every request).
- **Testimonials:** the anonymous "Los Angeles ___ Client" quotes came from
  `build_industries_1.py` template data (fabricated) and were replaced on 2026-11-09 by a
  verified "How our help desk performs" proof block (15 min / 90% / &lt;1 hr / 1999 + link to
  /case-studies). Named real-client quotes are never edited — and a quote is only "real" if
  it can be traced: the quote the site attributed to Alan B. Snitzer ("over 21 years") was
  another client's 2018 Google review with the number changed; it was replaced on 2026-11-10
  with Snitzer's own review text. Snitzer = **18-year client** (F011). Cunico and CR&R
  mention permission granted by Brian 2026-11-10.
- **No `aggregateRating`** anywhere (removed from 10 pages on 2026-11-09).
- **Enforced by `site_guard.py` check 20** (compliance-status claims, response-time wording,
  500+, 99.9% uptime, "no contracts", aggregateRating; the BAA rule was dropped 2026-11-10). Do not
  weaken it to make a page pass — fix the copy. **Added 2026-11-11:** "no annual contracts" (say
  "no long-term contracts") and unconditional same-business-day on-site claims ("technicians are
  dispatched the same business day") — 20 city pages, the Ads landing page and the city
  generator said both; rewritten to F017 "same-day on-site support when needed". Also
  compliance-alignment wording ("SEC/FINRA and GLBA-aligned", "SOC 2 aligned"), and **check 20 now
  scans `llms.txt` too** (it still said "SEC/FINRA and GLBA-aligned IT" because only HTML was
  checked). `llms.txt` carries a "Key Facts" block built only from `verified_facts.json` (citable
  F001–F005, F007, F008, F012–F017) — keep it in sync when a fact changes. Self-test for the
  patterns: they must flag the 11/11 claims and must NOT flag "no long-term contracts",
  "same-day on-site support when needed" or "we work alongside your compliance advisor".
  Check 20 also **renders animated counters** (`data-target` + `data-suffix` + the label after them)
  before matching: the home and about pages counted up to "500+ CA Businesses Served" and "98% Ticket
  Resolution Rate" until 2026-11-11 because the numbers lived in attributes. Counters now show only
  verified facts and carry their final value in the HTML (crawlers and AI readers don't run the animation).
- Google Ads: compliance terms are campaign negatives; ads/callouts/sitelinks use verified
  facts only; campaign-level sitelinks only (ad-group sitelinks override the campaign set);
  each ad group sets `final_url_suffix` with its own `utm_content`.
- Generators: `generate_gbp_post.py` "Compliance Corner" → "Backup Reality Check";
  `editorial/standards.md` carries the rule; `generate_blog.py` compliance topics removed and
  the blog runs weekly (Tuesday 16:00 UTC); `llms.txt` service descriptions are claim-free;
  the SEO engine's content-gap list no longer includes CMMC / NIST / ITAR / GCC High.

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
  LOW-risk fixes → PR labelled `automerge`; MEDIUM → PR labelled `automerge` +
  `medium-risk` (auto-merged too since 2026-10-15 by owner decision — nothing waits
  on a human); HIGH/external → a rolling monthly GitHub issue, never automated.
  Reports, intelligence, ledger and state stay in the war room (this repo is public
  — never put reports or strategy here).
- `pr-checks.yml` runs `site_guard.py` on every pull request as the job `guard`. The
  ruleset `main-protection` REQUIRES the status check named exactly `guard` (GitHub
  Actions); that required check is the only thing standing between an engine PR and
  `main`, so never rename the job, never remove the requirement, and never flip
  `risk_policy.low_auto_pr` / `medium_auto_merge` on without it — GitHub auto-merge
  merges instantly when no checks are required.
- That same required check blocks DIRECT pushes to `main` (`GH013: Required status
  check "guard" is expected`) — the desktop watcher and the editorial engine push
  directly, so the ruleset must keep **Repository admin** on its bypass list
  (*Always allow*). The engine's reconcile step verifies the `guard` check-run on
  the PR head itself before merging, so the bypass never weakens the engine's gate.
- GitHub re-evaluates auto-merge only on events (a check finishing, a push, a
  review), not on a ruleset edit, so an armed PR can sit "clean" and unmerged. The
  engine's reconcile step (daily run + `seo-reconcile.yml` every 4 h) merges clean
  policy-allowed engine PRs through the API — GitHub still enforces `guard` there —
  updates branches behind `main` and closes conflicted ones. It only ever touches
  `seo/auto-*` branches; human PRs are left alone.
- Engine commits are authored `prolink-seo-engine`. If the guard ever fails on
  `main` within 48h of an engine merge, the engine blocks further changes and names
  the commit to revert (rollback = revert PR).
- Daily audits run on the local checkout (complete, quota-free); `site_guard.py`
  remains the invariant gate and must not be weakened to make an engine fix pass.
