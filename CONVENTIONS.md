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
  question-phrased H2/H3s. The Key Takeaways box comes from the post's registry entry
  (`takeaways`, 3-5 bullets), not from the body (redesign-2026: see "Redesign 2026" below).
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
- **GBP blog backfill never posts blind (2026-11-16).** `gbp_backfill.py` lists the posts
  already live on the profile (`gbp_post.list_posts`) and skips any blog URL that is there,
  refusing to post at all if the profile can't be listed; its ledger lives on the
  `social-state` branch (the Actions bot can't push to main). From 10/15 to 11/15 a silently
  failed ledger commit made it re-post the same 5 articles daily (~140 duplicates, deleted
  11/16). Any job that writes state must save it somewhere it can push, and fail loudly
  when it can't.

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
- **City pages are paid landing pages too (2026-11-14).** Google Ads city keywords
  ("it support pasadena") now land on the matching city page instead of
  `/managed-it-services`. Keep each city page's `#talk-to-us` form, `contact-form.js` and
  Google tag intact, and never rename or delete a city page without updating the ad
  destinations first (the ads team keeps the keyword → page list): a 301 would still
  work but lowers the ads' landing-page score.

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
- **Phones always get a moving video or a play button (2026-11-16).** The poster + play button
  (`#vid-placeholder`, role=button) stay up until the video is actually PLAYING (`playing` or
  advancing `timeupdate`) and come back on any `pause` or refused `play()`; a paused video keeps
  its own frame, dimmed (`.frame-paused`). Never hide the poster on `canplay`/`canplaythrough`:
  that left phones with a still frame and no button whenever autoplay was refused (iPhone Low
  Power Mode, data saver) or slow on cellular. Every tap path (poster, "Tap for sound", list
  items, dots, arrows, "Watch our story") calls `play()` synchronously inside the tap — iOS
  refuses play/sound from a timer.
- **Contact page = form + phone only (2026-11-16).** The Calendly "book a discovery call" option
  was removed (0 client bookings in 5½ months; the subscription is cancelled) and `/thank-you`,
  which only existed as its booking redirect, 301s to `/contact`. Don't reintroduce a
  third-party booking widget without a reason; Microsoft Bookings comes with Microsoft 365.
- **Home reviews carousel = real, current Google reviews.** Rebuilt 2026-11-17 from the Google Business
  Profile API (newest 2026 reviews, 4-5 stars). Every card must match a review on the live profile (on
  11/17, 9 of the 15 old cards didn't). Quote the reviewer's own sentences only; mark cuts with an ellipsis;
  show month + year, never "2 years ago". Skip reviews whose specific claims we can't verify. Refresh
  tooling lives in the private war-room repo (`tools/google-reviews`), not here.
- **Real photos only.** People imagery comes from `assets/photos/` (the 2026 brand shoot,
  registered in `assets/variety_assets.json`) — never stock or AI images of "our team".
  Web copies go in `assets/photos/web/` as WebP with width/height set. `assets/gbp/` frames
  carry a logo watermark: fine for the Business Profile, avoid on the website. **Captions and
  alt text describe only what is visible** (a technician in a Pro Link polo helping someone) —
  never a location, team or role nobody has confirmed: some shoot frames (`lab_consult`,
  `tech_workbench`) were clearly taken in a client's lab, so "our help desk team, Woodland Hills"
  was replaced on 2026-11-12. In use: home why-us card (`techs-at-desks-{720,921}.webp`, since 2026-11-17). Brian rejected there: `team-dual-monitor`,
  the mid-sentence interview still `brian-shad-home-*`, and ANY portrait of himself on the home page, About story top-right
  (`office-woodland-hills-{720,1005}.webp` since 2026-11-17 — Brian didn't like the deskside shot there;
  `deskside-support-*.webp` is now unused).
  **2026-11-17 photo pass (Brian reviewed the folder; he is the man in the portraits and the
  light-blue-shirt video frames; Snitzer, Waverly and Optical Zonu OK'd stills; the Woodland Hills
  building is our office).** In-flow photos use `<figure class="page-photo">` (+ `--wide` in full
  containers, `--top` above the law/manufacturing stat cards); `managed-it-services.html` and
  `case-studies.html` don't load `_shared.css`, so they carry the same rules inline (`.cs-photo`).
  Placed: About (`brian-shad-cto`), help desk, backup & DR, why-us, vCIO, managed IT, law firm,
  manufacturing, education, nonprofit, contact (building) and three case studies. Blog bylines
  carry `post-avatar` = `brian-shad-byline-160.webp` (top square of portrait #4 so the whole face fits
  the circle; generate_blog.py writes it). Brand-video frames have a logo bug top-left —
  crop it; the old site ("one-stop shop") shows on some wall screens — blur or crop it. Never use
  the AI-generated group PNGs, frames with children, or anything showing client labels/IPs or
  security-camera feeds (those sit in the Dropbox `hold` subfolder). City pages: no photos yet.
- **Readable sizes:** body/card copy ≥ 16px (`.card p` 1rem), form inputs 16px (smaller makes
  iPhones zoom the page on tap), labels ≥ .8rem. Bump `?v=` on `lead-form.css` /
  `contact-form.js` when they change (CSS/JS cache 24 h + 7 d stale). **`_shared.css` is versioned
  too since 2026-11-12** — after changing it run `python bump_shared_css.py <yyyymmdd>` (rewrites the
  `?v=` on all ~165 pages + `generate_blog.py`, byte-exact). Cloudflare's edge kept serving a
  27-minute-old copy to the industry pages after a deploy (`cf-cache-status: HIT`); an
  unversioned CSS/JS change can take up to 24 h to reach visitors. The 16px input size is
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

## Self-service apps: online ordering + checkout (2026-11-19)

Brian: the Microsoft 365 Security Assessment ($2,500) is "our first app of a series of such apps
that I would like to host on our site similarly". Every app follows this one pattern:
- **Pages per app.** `/<slug>` = the product page: a ROOT `.html` file, indexed, in `sitemap.xml`,
  `llms.txt` and `_redirects` (`.html` -> clean), full site nav + footer, scanned by the guard.
  `/<slug>/order` and `/<slug>/thank-you` (plus app-specific pages) live in a `<slug>/` folder:
  `noindex`, not in the sitemap, slim checkout footer (no city list, so nothing drifts). The guard
  only scans root + `blog/`, so check sub-pages by hand to the same rules (one h1, apex canonical,
  valid JSON-LD, alt text, check-20 claims, inline JS parses). Check 19 (lead forms: only
  name/email required) does NOT apply to order forms: a purchase legitimately requires what its
  order contract requires.
- **Hub.** `/self-service` lists every app (a card + an `ItemList` entry). Site-wide links go to the
  hub, never to an individual app: the top menu item **"Assessments"** right after Services
  (`update_site_links.py` step 7: desktop + mobile menus of every page, the app pages mark it active,
  blog template too; `case-studies.html`'s custom bar included; the Ads landing page
  `managed-it-services.html` has no menu on purpose), the footer Services column (step 6;
  `ai-automation-services.html` and `case-studies.html` hand-edited) and the `services.html` "More
  services" grid. Adding an app = a hub card, never a site-wide edit.
- **One app = no hub (Brian 2026-11-20).** While there is a single app, `_redirects` sends
  `/self-service` to it with a **302** (temporary; never 301, browsers cache those for good), the hub
  page is `noindex` and out of `sitemap.xml` + `llms.txt`, and the app's BreadcrumbList uses Home ›
  Services. When app #2 launches: delete that `_redirects` line, set the hub back to `index, follow`,
  re-add it to the sitemap and `llms.txt`, and point the breadcrumbs at the hub again. Hub cards are
  fixed-width and centred (one card used to sit left of the centred heading).
- **Top menu fit.** With 8 items the desktop menu needs ~1,100px, so `_shared.css` tightens it below
  1200px, hides "Home" below 1040px (the logo is the home link) and shows the ☰ menu below 920px
  (measured on home, services, industry and blog pages: no overflow or wrapping at any width).
  Re-measure before adding another menu item; `bump_shared_css.py <date>` after any `_shared.css` change.
- **Where the M365 assessment is promoted (2026-11-20):** the home page band after the stats ("New ·
  Order online"), and the shared `.assess-callout` box (styles in `_shared.css`) above the CTA band
  on `cybersecurity-services`, `email-security-services` and `identity-access-management`, and above
  the CTA box in the Microsoft 365 / Copilot blog posts (t4 Microsoft 365 vs Google, t89 tenant prep,
  t90 Copilot data governance, t106 OAuth app grants, t49 Copilot safely). Every claim matches the
  product page (about 80 controls, 13 areas, read-only, findings by severity, review call, $2,500).
  **Naming rule (Brian 2026-11-20):** "assessment" means the PAID product only. The free discovery
  offer is the "Free IT Consultation" (or "free security/cloud/network consultation"): renamed from
  "free ... assessment" on 70 pages, the generators (gen_location_pages, generate_gbp_post,
  social_render, social_graphic, build_industries_1) and the Google Ads copy. Never reintroduce
  "free assessment" wording.
- **Shared front end.** `/assets/apps/apps.css` + `/assets/apps/checkout.js` (versioned `?v=`, bump
  on change). The order form is `<form data-checkout-product="<slug>" data-value data-currency>` with
  Turnstile; the thank-you page is `[data-checkout-thankyou]` with `[data-state]` panels. The script
  records first touch exactly like `contact-form.js` (`sessionStorage.pls_first_touch`).
- **Payment is embedded (2026-11-20, Brian: keep customers on our branded page).** After `start`,
  checkout.js hides the form and shows a "Payment" step below it: Authorize.net's hosted form in an
  iframe (token posted into it), the order summary stays beside it. Authorize.net only lets us set
  its accent color, button text and merchant name (no logo), hence the iframe. It talks back through
  the same-origin relay page `/assets/apps/anet-communicator` (URL sent in every token as
  `hostedPaymentIFrameCommunicatorUrl`; never move it): resize and cancel. Brian found the first
  version (Authorize.net's full form in a bordered 640 px frame) ugly, so the box is kept SMALL: the
  billing name/address is collected on OUR form (`bill_first_name`, `bill_last_name`, `bill_address`,
  `bill_city`, `bill_state`, `bill_zip`; required by `start` for every app; sent as `billTo`, never
  stored) and the hosted form shows only card number, expiry, code and Pay (billing block, order
  summary and Cancel button turned off); the iframe is borderless with `scrolling="no"` (as in
  Authorize.net's sample app) and takes exactly the height Authorize.net reports (6 s no-message
  fallback 900/1100 px). The embedded session has NO Authorize.net receipt (it was clipped in the
  frame): on `transactResponse` success the page goes straight to our thank-you page. `start`
  therefore returns two tokens per order: `token` (embedded, `showReceipt:false`, relay page) and
  `full_token` (full-window fallback / redirect mode, with receipt). The step polls
  `/api/checkout/status` and goes to the thank-you page once the webhook has verified the payment;
  the receipt's "Continue" (or "Cancel") page loaded inside the iframe lifts itself to the top window
  (top of checkout.js). Fallback link "Open it full-window" posts the same token to Authorize.net's
  page; `data-checkout-display="redirect"` on a form skips the iframe entirely. The site sends no
  X-Frame-Options/CSP, so no header changes were needed; if a CSP is ever added, allow
  `frame-src https://accept.authorize.net https://test.authorize.net` and let Authorize.net frame the
  relay page.
- **One checkout for every app.** Routes `functions/api/checkout/{start,anet-webhook,status}.js`;
  shared code (not routes) in `functions/_lib/checkout/`: `core.js`, `github.js`, `products.js`
  (registry), `products/<slug>.js`, `schemas/`. Payment = Authorize.net Accept Hosted: the site
  never sees card data. ONE webhook for all apps -> `https://prolinksystems.com/api/checkout/anet-webhook`,
  subscribed to TWO events: `net.authorize.payment.authcapture.created` and
  `net.authorize.payment.fraud.approved`; routed by order-id prefix (`PREFIX-YYMMDD-XXXX`, unique
  prefix per app). It fires for every transaction on the account and ignores anything that isn't a
  pending website order.
- **Secrets / bindings** live only in Cloudflare Pages (entered by Brian; never in source, chat or a
  briefing): `ORDERS` (KV binding), `ANET_ENV` (`production`|`sandbox`; anything else = checkout off),
  `ANET_API_LOGIN_ID`, `ANET_TRANSACTION_KEY`, `ANET_SIGNATURE_KEY`, and each app's hand-off
  credential (M365: `GITHUB_ORDERS_TOKEN`, fine-grained, `brianshad-usa/m365-security-agent` only,
  Issues read/write only). Reuses `TURNSTILE_SECRET_KEY` and the contact form's `MS_*`/`SEND_FROM`
  for failure alerts (one email per problem per 6 h). The webhook verifies every payment with
  getTransactionDetails: newer Authorize.net accounts have the Transaction Details API on with no
  setting (the 2026-11 sandbox shows none in either UI); if an account shows a "Transaction Details
  API" setting under Account > Settings, it must be enabled.
- **Authorize.net account settings that matter:** "Transaction Processing Mode" Enabled (the old
  Test Mode OFF), or payments get no transaction id and no webhook. Fraud Detection Suite >
  **Amount Filter** applies to every card payment on the account: it must not "decline" an app's
  price (and "hold for review" means each order waits for Pro Link's approval). The sandbox default
  is Upper Limit 1,000.00 + "process as normal and report" (an email per order). Sandbox test
  card 4111 1111 1111 1111; billing ZIP 46282 forces a decline; retrying the same card/amount/order
  within ~2 minutes = "duplicate transaction".
- **Rules that keep money and data safe:** Turnstile is strict on `start` (no stale-token pass);
  the price comes only from the product module; the webhook checks the HMAC, then re-reads the
  transaction (captured, exact amount, invoice = a pending order) before any hand-off. By the
  transaction's current status (`core.paymentState`): declined -> a plain "Card declined" email
  naming the customer (sales follow-up; no alarm); held by a fraud filter -> an email to approve or
  decline it in Authorize.net, and approving it (event `fraud.approved`) hands the order off
  automatically; processing error -> log only; anything else or a wrong amount -> "needs a look"
  email; a SECOND, different payment for an already-paid order -> "refund one" email. Hand-offs
  are idempotent (paid flag + KV lock + existing-issue check; the M365 agent also closes a second issue
  for an order_id it already has, and blocks concurrent duplicates, without registering or emailing
  anything; agent spec updated to these endpoints in commit ed90fac); the GitHub hand-off refuses to post
  customer details unless the repo is private; sandbox orders carry `"test": true` and never fire
  conversions; customer text is escaped so it can't break the issue's ```json block.
- **Tracking:** GA4 `begin_checkout` (order page) and `purchase` (thank-you; `transaction_id` = order
  id, value, currency) + UET `purchase` (`revenue_value`). The thank-you page fires them only after
  `/api/checkout/status` reports the webhook-verified payment, once per order. The Google Ads purchase
  conversion fires from `data-ads-send-to` on the thank-you page: M365 = conversion action "Purchase -
  M365 Security Assessment" (id 7911721395, Purchase, value from the tag, every conversion, deduped by
  transaction_id) = `AW-1068497497/ySHlCLOTzbwdENn0v_0D` (2026-11-20). A new app gets its own action.
- **Google Ads (2026-11-20, Brian):** campaign "ProLink M365 Security Assessment US 2026" (id
  24528974813): Search only, US presence, English, Manual CPC max $10, $10/day, 16 exact/phrase
  keywords, 40 negatives (the account's compliance list + DIY/jobs/training), one RSA with product-page
  facts only, suffix `utm_campaign=m365_assessment&utm_content=m365_assessment`. Google's planner:
  ~100 US searches/month, top-of-page bids $16.50-$50, so $10/day buys at most ~1 click/day.
- **App #1, M365 Security Assessment** (spec: private repo `brianshad-usa/m365-security-agent`,
  `docs/website-integration.md`). `/m365-security-assessment/access-granted` is the redirect URI of
  Pro Link's Microsoft Entra app: never move or rename it. The order JSON must satisfy the agent's
  schema, copied VERBATIM into `functions/_lib/checkout/schemas/m365-assessment-order-v1.js` (keep
  in sync; unknown fields make the agent reject an order). `terms_version` 2026-11 = the
  authorization wording on the order page, approved by Brian 2026-11-19; changing that text
  requires a new `terms_version` (so each order records the wording it accepted). Copy rules: the report lists findings by severity and
  has NO remediation steps; the review call is free with no prices given; remediation pricing never
  appears on the site; calls before ordering are welcome but optional (links marked
  `data-bookings-link="<slug>"`, opening Brian's private Bookings meeting type "Microsoft 365 Security
  Assessment: questions" in a new tab; write the URL's `@` as `%40` so Cloudflare Email Address Obfuscation
  can't rewrite it; clicks = GA4 `book_call_click`); Pro Link approves every engagement (full refund if declined); access is
  read-only by app consent only; never suggest giving us an account or a password. Numbers quoted
  from the sample report are labelled sample data.
- **Adding app #2+:** (1) `functions/_lib/checkout/products/<slug>.js` (id, name, amount,
  orderPrefix, pages, intake, buildOrder, schema, handoff) + register it in `products.js`;
  (2) `<slug>.html` + `<slug>/order.html` + `<slug>/thank-you.html` from the M365 pages; (3) a hub
  card + `ItemList` entry on `self-service.html`, and for the SECOND app undo "One app = no hub"
  above; (4) sitemap, `llms.txt`, `_redirects`; (5) extend
  `tests/checkout.test.mjs` (run `node --test tests/checkout.test.mjs`; 28 checks for app #1:
  validation, signatures, idempotency, payment states, privacy guard, alerts), `site_guard.py`, then
  an Authorize.net SANDBOX order end to end before production (Cloudflare Pages project `plsmain`:
  a pushed branch previews at `https://<branch>.plsmain.pages.dev` with the Preview variables; the
  sandbox webhook points there; the Turnstile widget allows `plsmain.pages.dev`).

## Redesign 2026 (branch `redesign-2026`, staging only until Brian approves go-live)

- **Staging:** `https://redesign-2026.plsmain.pages.dev` (Cloudflare Pages preview of this branch), guarded by
  `functions/_middleware.js`: disallow-all robots + noindex, the lead form and checkout APIs answered by the
  middleware (nothing sent, charged or ordered), tracking tags stripped behind no-op stubs. No login since
  2026-11-21 (Brian's request): `REQUIRE_LOGIN = false`; set it to `true` to require Basic auth again (user
  `prolink`, password = the Preview secret `STAGING_PASSWORD`, set by Brian, never in code; no password =
  everything refused). The middleware does nothing on `prolinksystems.com`. **Delete it before the merge.**
- **Rollback:** production `main` is untouched by this branch. Backups: local tag `pre-redesign-2026-11-20`
  (= `de7b063`, not pushed) and a zip of that commit outside the repo; Cloudflare keeps every production
  deployment for one-click rollback.
- **Design system:** `_shared.css` (sections 1-13). Fonts are self-hosted (`assets/fonts/*.woff2`, Inter for
  text, Manrope for headings; no Google Fonts). New components use the `pl-` prefix; the legacy class
  names are restyled in section 6 so unconverted pages still look consistent. Flat surfaces, square corners,
  thin rules; navy primary, amber only as a thin accent.
- **Header + footer = one place each:** `chrome/header.html` and `chrome/footer.html`. Every page carries them
  between `<!-- PL:HEADER -->` / `<!-- PL:FOOTER -->` markers, written by `python chrome/apply_chrome.py`
  (idempotent; `--check` reports drift). It also marks the current menu section, preloads the fonts, loads
  `/assets/js/pl.js` (menus, mobile drawer, reveal-on-scroll) and makes old `getElementById('hamburger' |
  'mobileMenu' | 'mobile-menu')` calls null-safe. The Ads landing page `managed-it-services.html` has
  the new look with its own short header (logo and phone, no menu on purpose); the script only refreshes its footer. After merging `main` into this branch, re-run the script.
- **Rebuilt pages so far:** home, `services` (Solutions), `about`, `case-studies` (Client Success),
  `contact` (the lead form markup, IDs, Turnstile and handler are unchanged), new `support` (Client Support,
  noindex). Their `<head>` metadata, canonicals, tracking and JSON-LD are kept; FAQ JSON-LD always matches
  the visible FAQ. `HOME_BLOG` markers stay on the home page (generate_blog.py rewrites the cards).
- **No URL changes.** Every existing URL, anchor (`services#helpdesk`, `#cybersecurity`, `#cloud`, `#dr`,
  `#consulting`, `#remote`, `#ai`, new `#managed-it`) and the 39 location links (footer + About `#areas`)
  are kept. A URL change needs a full 301 map and Brian's approval first.
- **`Review R#` markers** (`<span class="pl-flag">`) mark copy that waits for Brian's decision; the details
  are in his private review document, never in this public repo.
- **Iteration 2 (2026-11-21):** branch `redesign-2026-v1` (preview `https://redesign-2026-v1.plsmain.pages.dev`)
  freezes iteration 1 for comparison and revert. Typography options live side by side: A = serif display
  (default when `html` has no `data-type`), B = Manrope (`html[data-type="sans"]`); the staging-only "Design
  review" panel (injected by the middleware, so it never ships) switches typography, the homepage headline
  (4 options) and the hero visual (architecture illustration vs headquarters photo; both in `index.html` as
  `data-hero`). Case studies: `python chrome/build_case_pages.py` builds `/case-studies/<slug>` pages and the
  hub `<main>` from its CASES data and adds indexable pages to `sitemap.xml`; `case-studies/crr.html` is
  noindex and ships only with Brian's separate approval. Scroll motion never hides content (transform only).
- **Iteration 3 (2026-11-21):** branch `redesign-2026-v2` freezes iteration 2. Typography B (Manrope headings,
  Inter text) is the only option now. **Insights** is one system:
  - `editorial/blog_registry.json` is the single source of truth: the 7 categories, the practice each maps to,
    authors, the featured lead + 3-4 picks (chosen by hand, not by date), the CTA copy, and one entry per post
    (title, summary, dates, category, local/executive, author, `approved_by`, reviewers, takeaways, overrides).
  - `chrome/insights.py` renders every post, `/blog/` (featured, latest with topic filter + search +
    load-more via `assets/js/insights.js`, archive by topic) and the home cards (max 4), plus profile pages
    (`leadership/brian-shad`). `python chrome/insights.py --rebuild` re-renders everything after a template
    or registry change; `--check` validates the registry. Existing posts keep their head byte-for-byte except
    the BlogPosting author node, the breadcrumb label ("Insights") and the old inline blog `<style>`; the body
    between `<!-- PL:BODY -->` markers is never rewritten. Illustrations are generated SVGs
    (`chrome/insight_art.py` -> `assets/insights/<slug>.svg`); og:image stays `/logo.png` (GBP backfill posts
    og:image as a photo, so it must stay raster).
  - **Attribution rule (Brian):** a post shows Brian Shad as author only when its entry has `"author":
    "brian-shad"` AND `approved_by`; everything else is published under the organization. New posts default to
    the organization.
  - `generate_blog.py` asks the model for CATEGORY and TAKEAWAYS (falls back to `insights.guess_category`),
    adds the registry entry, renders the post with the shared chrome, and rebuilds `/blog/` and the home cards.
    The workflow commits `editorial/blog_registry.json` and `assets/insights/` too. Filters/search never create
    URLs; `/category/*` and `/author/*` still 301 to `/blog`.
- **Iteration 4 (2026-11-21):** branch `redesign-2026-v3` freezes iteration 3 (preview
  `https://redesign-2026-v3.plsmain.pages.dev`). What is permanent from it:
  - **Illustrations:** every article has its own line-art scene in `chrome/art_scenes/` (registered per slug with an alt
    text; style guide in that package's docstring), built from `chrome/art_kit.py`. `python chrome/art_preview.py --out DIR
    [slug ...]` renders contact sheets. New posts without a scene get a category motif until a scene is added.
  - **Insights page:** compact hero, one lead analysis + four picks (chosen in the registry), Latest (9 shown, up to 24) and
    a **Library** with every article by topic in `<details>` sections, keyword search and topic filter
    (`assets/js/insights.js`). No category URLs; everything is in the HTML without JavaScript.
  - **Article page:** headline beside a 3:2 illustration, contents list with reading position (`assets/js/article.js`),
    takeaways first, and components usable in any article body: `table.pl-compare`, `ul.pl-checklist`, `ol.pl-process`,
    `div.pl-framework`, `div.pl-callout`, `figure.pl-flow` and a `References` list (`h2.pl-refs-h` + `ul.pl-refs`).
  - **Editorial bar:** no sales copy in article bodies (the template adds the CTA), no statistic without a primary source
    that was opened, references to primary sources only, "Pro Link Systems" at most once per article, no
    compliance-service claims, stale years corrected. Original publication dates never change; a substantive revision sets
    `date_modified` in the registry, which shows "Updated ..." on the page and updates `dateModified` and the sitemap.
    `dek` (registry) is the standfirst shown on the page; the meta description tag is not edited by that.
  - **Name:** the company is always "Pro Link Systems" (`python chrome/company_name.py`); only titles that would pass 60
    characters keep the short brand. Verbatim reviews are never edited. **Business hours:** Mon-Fri 9 AM-5 PM PT
    (footer, contact page, structured data); the 24/7 help desk is for managed-service clients under contract.
  - **Landmarks:** `apply_chrome.py` gives every page without its own `<main>` one (opened at the end of the header block,
    closed at the start of the footer block). Do not add a second `<main>` to those pages.
  - **Ads landing page (`/managed-it-services`):** rebuilt on `_shared.css` (about 55 KB lighter, no Google Fonts). Unchanged:
    every head tag and tracking call, the form fields and ids (`lpForm`, `fi-*`, `formBody`, `formSuccess`, `successName`,
    `successRef`), Turnstile, `contact-form.js`, title, meta, H1 wording, FAQ and structured data. On phones the headline
    now comes before the form.
  - **Pages rebuilt on verified facts:** `why-pro-link-systems` (seven questions to ask any provider; no competitor claims),
    `ai-automation-services`, `la-business-cybersecurity-report-2026` (figures from Verizon's 2026 DBIR and the FBI's 2025
    IC3 report; update it from the primary PDFs each year). Section 15 of `_shared.css` carries the older templates
    (resource pages, vCIO guides, legal pages, `.cmp` / `.sev-table` tables, `.trust-panel`).
  - **Quotes:** only verbatim Google reviews, a client's own video, or text with written approval may be quoted. Reference
    claims on industry pages match the approved case-study notes.
  - **Authorship:** the three guide pages (report, how-to-choose, pricing) name the organization as author in their
    structured data until Brian records an approval (A1).
  - **Offer wording:** "assessment" means the paid Microsoft 365 product only, also in form confirmation messages.
  - **Site checks:** `chrome/link_check.py`, `form_labels.py`, `refine_wording.py`, `company_name.py --check` and
    `insights.py --check` are part of `golive_check.py`.
- **Before go-live (checklist):** `python chrome/golive_check.py` must pass: no `pl-flag` left, no
  `functions/_middleware.js`, a new `_shared.css?v=` (`bump_shared_css.py` now covers `case-studies/`,
  `leadership/` and `m365-security-assessment/`), and `gen_location_pages.py` / `update_site_links.py`
  emitting the new header/footer markers (`generate_blog.py` does). Merge `main` into this branch first, then
  run `python chrome/build_blog_registry.py <classification.json>` only for posts published since (or add their
  registry entries by hand) and `python chrome/insights.py --rebuild`, because Tuesday posts arrive in the old
  design. SEO engine (`C:\Googleads\seo`) prerequisites: `audit.py` must know subdirectory pages
  (`/case-studies/*`, `/leadership/*`) or it reverts change-sets for "broken" links; strip the new header from
  word counts; rename its breadcrumb label to "Insights". Ship the generator and the migration together, not on
  a Tuesday. Then a PR to `main`, merged only on Brian's explicit approval.
