/**
 * functions/_middleware.js -- STAGING GUARD for the 2026 redesign (branch redesign-2026).
 * >>> DELETE THIS FILE BEFORE THE REDESIGN IS MERGED TO PRODUCTION (see CONVENTIONS "Redesign 2026"). <<<
 *
 * On prolinksystems.com / www.prolinksystems.com it does nothing (straight pass-through).
 * On every other host (the *.pages.dev staging/preview addresses) it:
 *   1. when REQUIRE_LOGIN is true: requires HTTP Basic auth, user "prolink", password = STAGING_PASSWORD
 *      (Cloudflare Pages > Settings > Variables and Secrets > Preview, set by Brian; never in code); no password
 *      configured = everything is refused (fail closed). 2026-11-21: Brian asked to remove the login, so
 *      REQUIRE_LOGIN is false and staging is viewable by anyone with the link (still never indexed).
 *   2. keeps search engines out: robots.txt disallows everything, every response gets X-Robots-Tag: noindex,
 *      and HTML pages get a robots noindex meta tag.
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
const STUB = '<meta name="robots" content="noindex, nofollow"><script>window.dataLayer=[];' +
  'window.gtag=function(){};window.uetq=[];window.clarity=function(){};window.hj=function(){};</script>';
const RIBBON = '<div aria-hidden="true" style="position:fixed;left:12px;bottom:12px;z-index:2147483647;' +
  'background:#9b1c1c;color:#fff;font:700 11px/1 system-ui,sans-serif;letter-spacing:.12em;padding:7px 9px;' +
  'pointer-events:none">STAGING</div>';

// Design review (staging only, removed with this file): picks typography option A/B before first paint, and a
// small panel switches typography, the homepage headline and the hero visual. Choices persist per browser.
const REVIEW_HEAD = '<script>(function(){var d=document.documentElement,t="sans";try{var q=new URLSearchParams(location.search);' +
  't=q.get("type")||localStorage.getItem("pl-type")||"sans";if(q.get("type"))localStorage.setItem("pl-type",t);}catch(e){}' +
  'd.setAttribute("data-type",t==="serif"?"serif":"sans");})();</script>';
const REVIEW_PANEL = `
<div id="plr" class="plr">
  <button type="button" class="plr-toggle" aria-expanded="false" aria-controls="plr-body">Design review</button>
  <div class="plr-body" id="plr-body" hidden>
    <p class="plr-h">Typography</p>
    <div class="plr-seg" data-key="type"><button type="button" data-val="serif">A &middot; Editorial serif</button><button type="button" data-val="sans">B &middot; Contemporary sans</button></div>
    <div class="plr-home" hidden>
      <p class="plr-h">Homepage headline</p>
      <div class="plr-seg plr-seg--4" data-key="headline"><button type="button" data-val="1">1</button><button type="button" data-val="2">2</button><button type="button" data-val="3">3</button><button type="button" data-val="4">4</button></div>
      <p class="plr-h">Hero visual</p>
      <div class="plr-seg" data-key="hero"><button type="button" data-val="architecture">Architecture</button><button type="button" data-val="headquarters">Headquarters</button></div>
    </div>
    <p class="plr-links"><a data-v1 href="https://redesign-2026-v1.plsmain.pages.dev/">Compare with version 1</a> &middot; <a href="https://claude.ai/artifact/2ZvGhFzcjrKx5M8gR2wMLN" target="_blank" rel="noopener">Review notes</a></p>
  </div>
</div>
<style>
.plr{position:fixed;right:16px;bottom:16px;z-index:2147483646;font:500 13px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;color:#0b1a2b}
.plr-toggle{display:block;margin-left:auto;background:#0b1a2b;color:#fff;border:1px solid rgba(255,255,255,.3);padding:10px 14px;font:600 11px/1 system-ui,sans-serif;letter-spacing:.1em;text-transform:uppercase;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.28)}
.plr-body{width:300px;max-width:calc(100vw - 32px);margin-top:8px;background:#fff;border:1px solid #dde3ea;box-shadow:0 18px 48px rgba(11,26,43,.22);padding:16px}
.plr-h{font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#4b6580;margin:14px 0 8px}
.plr-body>.plr-h:first-child{margin-top:0}
.plr-seg{display:grid;grid-template-columns:1fr 1fr;border:1px solid #c7d0db}
.plr-seg--4{grid-template-columns:repeat(4,1fr)}
.plr-seg button{background:#fff;border:0;border-left:1px solid #c7d0db;padding:9px 6px;font:600 12px/1.2 system-ui,sans-serif;color:#0b1a2b;cursor:pointer}
.plr-seg button:first-child{border-left:0}
.plr-seg button[aria-pressed="true"]{background:#0b3d6b;color:#fff}
.plr-links{margin-top:14px;padding-top:12px;border-top:1px solid #dde3ea;font-size:12px}
.plr-links a{color:#0b3d6b;text-decoration:underline}
</style>
<script>
(function () {
  var d = document, root = d.documentElement, box = d.getElementById('plr');
  if (!box) return;
  var HL = {
    "1": ["Technology leadership for an increasingly complex world.", "Enterprise-grade technology management, cybersecurity and digital transformation, delivered by one accountable team. Trusted by organizations since 1999."],
    "2": ["Engineering the technology complex organizations depend on.", "Managed technology, cybersecurity, cloud engineering and strategy for organizations that cannot afford downtime. Independent since 1999."],
    "3": ["Independent technology leadership, built on 27 years of engineering.", "One accountable partner to run, secure and modernize your technology, from day-to-day operations to the leadership roadmap."],
    "4": ["Strategy, security and engineering for organizations that run on technology.", "Managed and co-managed IT, cybersecurity, cloud and AI, delivered through one accountable framework. Independent since 1999."]
  };
  function get(k, def) { try { return localStorage.getItem('pl-' + k) || def; } catch (e) { return def; } }
  function set(k, v) { try { localStorage.setItem('pl-' + k, v); } catch (e) {} }
  var h1 = d.getElementById('home-h1'), lead = d.getElementById('home-lead');
  var heroes = [].slice.call(d.querySelectorAll('[data-hero]'));
  if (h1 || heroes.length) box.querySelector('.plr-home').hidden = false;
  function apply(key, val) {
    if (key === 'type') root.setAttribute('data-type', val === 'serif' ? 'serif' : 'sans');
    if (key === 'headline' && h1 && HL[val]) { h1.textContent = HL[val][0]; if (lead) lead.textContent = HL[val][1]; }
    if (key === 'hero') heroes.forEach(function (el) { el.hidden = el.getAttribute('data-hero') !== val; });
    [].slice.call(box.querySelectorAll('[data-key="' + key + '"] button')).forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-val') === val ? 'true' : 'false');
    });
  }
  apply('type', root.getAttribute('data-type') || 'sans');
  if (h1) apply('headline', get('headline', '1'));
  if (heroes.length) apply('hero', get('hero', 'architecture'));
  var v1 = box.querySelector('[data-v1]');
  if (v1) v1.href = 'https://redesign-2026-v1.plsmain.pages.dev' + location.pathname;
  var toggle = box.querySelector('.plr-toggle'), body = d.getElementById('plr-body');
  function open(on) { toggle.setAttribute('aria-expanded', on ? 'true' : 'false'); body.hidden = !on; set('panel', on ? '1' : '0'); }
  box.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('button') : null;
    if (!b) return;
    if (b === toggle) { open(toggle.getAttribute('aria-expanded') !== 'true'); return; }
    var seg = b.closest('[data-key]');
    if (!seg) return;
    var key = seg.getAttribute('data-key'), val = b.getAttribute('data-val');
    if (key === 'type') set('type', val); else set(key, val);
    apply(key, val);
  });
  open(get('panel', '1') === '1');
})();
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
  return new HTMLRewriter()
    .on("script", new ScriptFilter())
    .on("head", { element(el) { el.prepend(STUB + REVIEW_HEAD, { html: true }); } })
    .on("body", { element(el) { el.append(RIBBON + REVIEW_PANEL, { html: true }); } })
    .transform(out);
}
