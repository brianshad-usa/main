/**
 * functions/_middleware.js -- STAGING GUARD for the SEO program release (branch seo-growth-2026-11), copied from the
 * redesign-2026 guard (same behaviour; the redesign review panel is replaced by a "compare with the live page" link).
 * >>> DELETE THIS FILE BEFORE THIS BRANCH IS MERGED TO PRODUCTION (golive_check.py fails while it exists). <<<
 *
 * On prolinksystems.com / www.prolinksystems.com it does nothing (straight pass-through).
 * On every other host (the *.pages.dev staging/preview addresses) it:
 *   1. when REQUIRE_LOGIN is true: requires HTTP Basic auth, user "prolink", password = STAGING_PASSWORD
 *      (Cloudflare Pages > Settings > Variables and Secrets > Preview, set by Brian; never in code); no password
 *      configured = everything is refused (fail closed). 2026-11-21: Brian asked to remove the login, so
 *      REQUIRE_LOGIN is false and staging is viewable by anyone with the link (still never indexed).
 *   2. keeps search engines out: robots.txt disallows everything, every response gets one X-Robots-Tag: noindex,
 *      and every HTML page ends up with exactly one robots meta tag, set to noindex (the page's own tag is
 *      rewritten; one is added only when a page has none), so there are no conflicting directives.
 *   3. answers the lead form and the checkout APIs itself: no email to the inbox, no payment session, no order
 *      sent to the assessment agent.
 *   4. removes the analytics / advertising tags (Google tag: Ads + GA4, Microsoft UET, Hotjar, Clarity) from HTML
 *      and installs no-op stubs first, so page code that calls gtag()/uetq/clarity never errors and staging
 *      visits never reach production analytics or ad conversions. Adds a small "STAGING" label.
 */
const PROD_HOSTS = new Set(["prolinksystems.com", "www.prolinksystems.com"]);
const REQUIRE_LOGIN = false;   // 2026-11-21 Brian: no login on staging; set true to require the password again
const USER = "prolink";
const TRACKING_SRC = /googletagmanager\.com|google-analytics\.com|bat\.bing\.net|clarity\.ms|hotjar\.com/i;
const TRACKING_INLINE = /googletagmanager\.com|bat\.bing\.net|clarity\.ms|static\.hotjar\.com|hotjar|gtag\(\s*['"](?:js|config)['"]/i;
const NOINDEX = "noindex, nofollow";
const STUB = '<script>window.dataLayer=[];' +
  'window.gtag=function(){};window.uetq=[];window.clarity=function(){};window.hj=function(){};</script>';
const RIBBON = '<div aria-hidden="true" style="position:fixed;left:12px;bottom:12px;z-index:2147483647;' +
  'background:#9b1c1c;color:#fff;font:700 11px/1 system-ui,sans-serif;letter-spacing:.12em;padding:7px 9px;' +
  'pointer-events:none">STAGING</div>';

// Review aid (staging only, removed with this file): a link to the same path on the live site, for side-by-side review.
const REVIEW_PANEL = `
<a id="plr" href="https://prolinksystems.com/" target="_blank" rel="noopener" style="position:fixed;right:16px;bottom:16px;z-index:2147483646;background:#0b1a2b;color:#fff;padding:10px 14px;font:600 11px/1 system-ui,sans-serif;letter-spacing:.1em;text-transform:uppercase;text-decoration:none;box-shadow:0 8px 24px rgba(0,0,0,.28)">Compare with live page</a>
<script>
(function () { var a = document.getElementById('plr'); if (a) a.href = 'https://prolinksystems.com' + location.pathname + location.hash; })();
</script>`;

function plain(status, text, extra = {}) {
  return new Response(text, {
    status,
    headers: { "Content-Type": "text/plain; charset=utf-8", "X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store", ...extra },
  });
}
function json(status, obj) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", "X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store" },
  });
}
function sameString(a, b) {                       // constant-time compare
  const x = new TextEncoder().encode(a);
  const y = new TextEncoder().encode(b);
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) diff |= (x[i] || 0) ^ (y[i] || 0);
  return diff === 0;
}
function authorized(header, password) {
  const m = /^Basic\s+([A-Za-z0-9+/=]+)$/.exec(header || "");
  if (!m) return false;
  let decoded = "";
  try { decoded = atob(m[1]); } catch (e) { return false; }
  const i = decoded.indexOf(":");
  if (i < 0) return false;
  return sameString(decoded.slice(0, i), USER) & sameString(decoded.slice(i + 1), password) ? true : false;
}

class ScriptFilter {
  constructor() { this.buf = ""; this.inline = false; }
  element(el) {
    const src = el.getAttribute("src");
    const type = (el.getAttribute("type") || "").toLowerCase();
    this.buf = "";
    this.inline = !src && !type.includes("ld+json");
    if (src && TRACKING_SRC.test(src)) el.remove();
  }
  text(chunk) {
    if (!this.inline) return;
    this.buf += chunk.text;
    chunk.remove();                               // hold the script body until we have all of it
    if (chunk.lastInTextNode) {
      if (!TRACKING_INLINE.test(this.buf)) chunk.after(this.buf, { html: true });
      this.buf = "";
    }
  }
}

export async function onRequest(context) {
  const { request, env, next } = context;
  const url = new URL(request.url);
  if (PROD_HOSTS.has(url.hostname)) return next();

  if (REQUIRE_LOGIN) {
    const password = env.STAGING_PASSWORD;
    if (!password) return plain(503, "The Pro Link staging site is locked: no STAGING_PASSWORD is configured.");
    if (!authorized(request.headers.get("Authorization"), password)) {
      return plain(401, "Authentication required.", { "WWW-Authenticate": 'Basic realm="Pro Link staging", charset="UTF-8"' });
    }
  }

  if (url.pathname === "/robots.txt") return plain(200, "User-agent: *\nDisallow: /\n");
  if (url.pathname === "/api/contact") return json(200, { ok: true, staging: true, message: "Staging site: the form works, but nothing was sent." });
  if (url.pathname.startsWith("/api/checkout/start")) return json(503, { ok: false, message: "Ordering is turned off on the staging site." });
  if (url.pathname.startsWith("/api/checkout/anet-webhook")) return json(200, { ok: true, ignored: "staging" });

  const res = await next();
  const headers = new Headers(res.headers);
  headers.set("X-Robots-Tag", "noindex, nofollow");
  headers.set("Cache-Control", "no-store");
  const out = new Response(res.body, { status: res.status, statusText: res.statusText, headers });
  if (!(headers.get("Content-Type") || "").includes("text/html")) return out;
  const robots = { seen: false };
  return new HTMLRewriter()
    .on("script", new ScriptFilter())
    .on('meta[name="robots"]', { element(el) {
      if (robots.seen) { el.remove(); return; }        // never two robots tags
      robots.seen = true;
      el.setAttribute("content", NOINDEX);
    } })
    .on("head", { element(el) {
      el.prepend(STUB, { html: true });
      el.onEndTag((end) => { if (!robots.seen) end.before('<meta name="robots" content="' + NOINDEX + '">', { html: true }); });
    } })
    .on("body", { element(el) { el.append(RIBBON + REVIEW_PANEL, { html: true }); } })
    .transform(out);
}
