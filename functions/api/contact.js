/**
 * POST /api/contact  —  Cloudflare Pages Function
 * -----------------------------------------------------------------------------
 * Server-side handler for the website contact/lead forms. Replaces the old
 * client-side EmailJS + Web3Forms path, whose public keys let anyone send mail
 * as info@ to any recipient (the abuse that filled Sent Items with 279
 * unsolicited "inquiry received" messages).
 *
 * Security model:
 *   - Cloudflare Turnstile token is verified server-side on every submission.
 *     No token, or a malformed/forged one => no send. This is what kills the
 *     relay abuse. (We do NOT send `remoteip`: it is optional, and an IP that
 *     differs between the widget and this POST — iCloud Private Relay, mobile
 *     and corporate networks — must never cost us a real lead.)
 *   - Fail-safe for humans (added 2026-11-09, narrowed 2026-11-26): if Cloudflare
 *     itself errored ("internal-error" / siteverify unreachable), the internal
 *     notification still goes to info@ marked [UNVERIFIED] — but NO visitor
 *     confirmation is sent, so this path can never be used to relay mail to
 *     third parties. An expired or already-used token is rejected.
 *   - A hidden honeypot field ("botcheck") silently drops obvious bots.
 *   - All sending happens here with credentials that live ONLY in Pages env
 *     vars (never in page source). The recipient of the confirmation is the
 *     submitter, but the endpoint is un-spammable without a Turnstile token.
 *   - Every user-supplied value is HTML-escaped before being placed in email
 *     bodies, so form input can't inject markup/links into the messages.
 *   - 2026-11-26 (Phase G security closeout), all tested in tests/contact.test.mjs:
 *       * HOSTNAME: a token is only accepted on the host it was solved on
 *         (prolinksystems.com and www count as one). The site key also works on
 *         plsmain.pages.dev and every preview / old-deployment subdomain of it,
 *         so this stops a token solved there from being spent on production.
 *       * ACTION: the lead-form widgets carry data-action="contact". A token with
 *         any other action (the checkout's "checkout") is refused; an unlabeled
 *         token (a page opened before the widgets were labeled) takes the
 *         [UNVERIFIED] path, so no real lead is lost.
 *       * RATE LIMITS per IP (IPv6 per /64): every POST, and [UNVERIFIED]
 *         notifications. Each token is processed once (a repeat gets the first
 *         reference and sends nothing). Visitor confirmations are capped per
 *         address and skipped when an echoed field holds link-like text.
 *         Counters + token claims: with a D1 database bound as CONTACT_DB they
 *         are exact and global (D1 runs every statement on one primary,
 *         atomically). Without it — or if D1 errors — they use this data
 *         center's cache + an exact per-isolate count: approximate, per data
 *         center. Either way they FAIL OPEN (a store error never blocks a
 *         visitor). The WAF rate-limiting rule is the edge burst shield.
 *
 * Mail is sent from info@ via Microsoft Graph (application permissions), the
 * same mailbox/app the review agent already uses — real DKIM/SPF/DMARC, no
 * third-party relay, no per-email quota.
 *
 * Required Pages environment variables (Settings -> Environment variables):
 *   MS_TENANT_ID          Azure AD tenant id
 *   MS_CLIENT_ID          App registration (client) id  [needs Mail.Send app perm]
 *   MS_CLIENT_SECRET      App client secret              [mark as "Secret"/encrypted]
 *   SEND_FROM             Sending mailbox, e.g. info@prolinksystems.com
 *   TURNSTILE_SECRET_KEY  Cloudflare Turnstile secret    [mark as "Secret"/encrypted]
 * Optional:
 *   LEAD_NOTIFY           Where internal lead notifications go (default: SEND_FROM)
 *   TURNSTILE_ALLOWED_HOSTNAMES  Extra token hostnames accepted on any host, comma-separated.
 *                         Local testing only (Turnstile's dummy keys report "example.com");
 *                         never set it in Production.
 *   CONTACT_DB            D1 database binding (Settings -> Bindings -> D1). Makes the rate
 *                         limits and the once-per-token rule exact and global. The two
 *                         tables are created on first use; nothing else to set up.
 */

const GRAPH = "https://graph.microsoft.com/v1.0";
// Core fields every form must carry AFTER alias normalization. Everything else
// (last name, phone, company, message) is optional: an email is enough to follow
// up, and every extra required field costs leads (phone was required until
// 2026-11-09).
const REQUIRED = ["first_name", "email"];
// Siteverify outcomes that mean "Cloudflare hiccupped", not "this is a bot" — these fall back to an
// [UNVERIFIED] notification. 2026-11-26: an expired or already-used token ("timeout-or-duplicate")
// is REJECTED (the form resets its widget and the visitor presses Send again); it used to fall back
// too, which let one solved token be replayed into unlimited notifications. In the 11-09..11-26
// period the fallback never fired for a real lead (info@ holds no [UNVERIFIED] notification).
const SOFT_FAIL_CODES = ["internal-error"];
const EXPIRED = "The robot check expired or was already used. Please press Send again.";
// Attribution fields the form scripts add (contact-form.js / contact.html).
const ATTRIBUTION = ["source_page", "page_url", "referrer", "landing_page", "first_referrer",
  "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "gbraid", "wbraid", "msclkid"];

// Turnstile hostname + action (2026-11-26). The production pair counts as one host.
const PROD_HOSTS = new Set(["prolinksystems.com", "www.prolinksystems.com"]);
const ACTION = "contact";          // data-action on every lead-form widget (site_guard check 19)

// Rate limits (2026-11-26). A real visitor sends 1–2 POSTs. win = seconds, max = allowed per window.
const LIMITS = {
  post: [{ win: 600, max: 5 }, { win: 86400, max: 20 }],   // every POST from one IP
  unverified: [{ win: 3600, max: 2 }],                      // [UNVERIFIED] notifications from one IP
  confirm: [{ win: 86400, max: 2 }],                        // visitor confirmations to one address
};
const TOKEN_TTL = 86400;           // seconds a processed or refused token is remembered (tokens live 300 s)
const PENDING_TTL = 120;           // seconds a token counts as "being processed"
const REFUSED = "!refused";        // marker: solved on another host / for another widget; never accepted
const VERIFY_FAILED = "Verification failed — please retry the challenge.";
const TOO_MANY = "Too many attempts from your network. Please wait a few minutes and try again, or call 1-800-890-6133.";
// Text a mail client would turn into a link (or an address). Real names, companies, phones and the service
// dropdown practically never contain one; spam pushed through the visitor confirmation always does.
const LINKISH = /https?:\/\/|www\.|@|\b[a-z0-9-]{2,}\.(?:com|net|org|info|biz|io|co|ru|cn|xyz|top|site|online|link|click|live|shop|app|me|us|uk)\b/i;

// The pages use varied field names (name / firm_name / firm_size / firm_type,
// honeypot "botcheck" vs "challenge"). Map them to the canonical set the email
// templates expect so one endpoint serves every form.
function normalize(f) {
  if (!f.first_name && f.name) {
    const parts = String(f.name).trim().split(/\s+/);
    f.first_name = parts.shift() || "";
    if (!f.last_name) f.last_name = parts.join(" ");
  }
  f.last_name = f.last_name || "";
  f.company = f.company || f.firm_name || f.organization || "";
  f.interest = f.interest || f.firm_type || f.challenge || "";
  f.message = f.message || "";
  const extra = [];
  if (f.firm_size) extra.push("Firm size: " + f.firm_size);
  if (f.firm_type && f.firm_type !== f.interest) extra.push("Type: " + f.firm_type);
  // "challenge" is the VISIBLE "Primary IT Challenge" dropdown on 13 industry pages; when the same form
  // also has a firm-type dropdown, interest = firm_type and the challenge used to be dropped (fixed 2026-11-09).
  if (f.challenge && f.challenge !== f.interest) extra.push("IT challenge: " + f.challenge);
  if (extra.length) f.message = (f.message ? f.message + "\n\n" : "") + extra.join(" · ");
  return f;
}

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function json(status, obj) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

function makeRef() {
  const alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  const bytes = new Uint8Array(6);
  crypto.getRandomValues(bytes);
  let out = "";
  for (let i = 0; i < 6; i++) out += alpha[bytes[i] % alpha.length];
  return "PLS-" + out;
}

async function verifyTurnstile(secret, token) {
  // Returns { ok, soft, codes, hostname, action }: ok = verified; soft = only a
  // stale-token / Cloudflare-side failure (a human, not a bot). hostname/action
  // come from a successful siteverify only. No remoteip — see header.
  try {
    const body = new URLSearchParams({ secret, response: token || "" });
    const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    const data = await r.json().catch(() => ({ success: false, "error-codes": ["bad-json"] }));
    const codes = data["error-codes"] || [];
    if (data.success === true) {
      return { ok: true, soft: false, codes, hostname: String(data.hostname || ""), action: String(data.action || "") };
    }
    return { ok: false, soft: codes.length > 0 && codes.every((c) => SOFT_FAIL_CODES.includes(c)), codes };
  } catch (e) {
    // Network failure reaching Cloudflare: never the visitor's fault.
    return { ok: false, soft: true, codes: ["siteverify-unreachable"] };
  }
}

// A token may only be spent on the host it was solved on; prolinksystems.com and www are one site.
function hostnameOk(tokenHost, requestHost, env) {
  const t = String(tokenHost || "").toLowerCase();
  const r = String(requestHost || "").toLowerCase();
  if (!t) return false;
  const extra = String(env.TURNSTILE_ALLOWED_HOSTNAMES || "").toLowerCase().split(",").map((s) => s.trim()).filter(Boolean);
  if (extra.includes(t)) return true;
  if (PROD_HOSTS.has(t) && PROD_HOSTS.has(r)) return true;
  return t === r;
}

// ---------------------------------------------------------------------------
// Counters for the rate limits and the once-per-token rule. Each key lives in an
// exact in-memory map (this isolate) AND in this data center's cache, which every
// isolate here shares; an abusive client normally stays on one data center. Every
// cache call is wrapped: on any error the request simply goes ahead (fail open).
// ---------------------------------------------------------------------------
const mem = new Map();             // key -> { n, exp, v }

function nowSec() { return Math.floor(Date.now() / 1000); }

function prune(now) {
  if (mem.size < 2000) return;
  for (const [k, e] of mem) if (e.exp <= now) mem.delete(k);
  if (mem.size > 5000) for (const k of mem.keys()) { mem.delete(k); if (mem.size <= 4000) break; }   // oldest first
}

function sharedCache() {
  try { return typeof caches !== "undefined" && caches.default ? caches.default : null; } catch (e) { return null; }
}

function cacheKey(origin, key) { return origin + "/__contact-rl/" + key; }

async function cacheGet(origin, key) {
  const c = sharedCache();
  if (!c) return null;
  try {
    const hit = await c.match(cacheKey(origin, key));
    return hit ? await hit.text() : null;
  } catch (e) { return null; }
}

async function cachePut(origin, key, value, ttl) {
  const c = sharedCache();
  if (!c) return;
  try {
    await c.put(cacheKey(origin, key), new Response(String(value), {
      headers: { "Cache-Control": "max-age=" + Math.max(1, Math.floor(ttl)) },
    }));
  } catch (e) {}
}

async function cacheDelete(origin, key) {
  const c = sharedCache();
  if (!c) return;
  try { await c.delete(cacheKey(origin, key)); } catch (e) {}
}

async function hashId(s) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("pls-contact:" + s));
  return [...new Uint8Array(d)].slice(0, 12).map((b) => b.toString(16).padStart(2, "0")).join("");
}

// The client IP as counted: IPv4 as is, IPv6 by its /64 (a client can rotate addresses inside it).
function clientId(request) {
  const ip = String(request.headers.get("CF-Connecting-IP") || "").trim().toLowerCase();
  if (!ip || !ip.includes(":")) return ip;
  if (ip.includes(".")) return ip.slice(ip.lastIndexOf(":") + 1);   // IPv4-mapped IPv6 -> the IPv4
  const [head, tail = ""] = ip.split("::");
  const h = head ? head.split(":") : [];
  const t = tail ? tail.split(":") : [];
  const full = [...h, ...Array(Math.max(0, 8 - h.length - t.length)).fill("0"), ...t];
  return full.slice(0, 4).map((x) => x.padStart(4, "0")).join(":") + "::/64";
}

// ---------------------------------------------------------------------------
// Optional GLOBAL store: a D1 database bound as CONTACT_DB. D1 runs every statement
// on one primary, so an UPSERT ... RETURNING count is exact across data centers and
// concurrent requests, and a token claim (INSERT ... ON CONFLICT DO NOTHING) succeeds
// exactly once worldwide. Any D1 error falls back to cache + memory for that call.
// ---------------------------------------------------------------------------
let schemaReady = null;            // per isolate: creates the two tables once

function d1(env) {
  const d = env && env.CONTACT_DB;
  return d && typeof d.prepare === "function" && typeof d.batch === "function" ? d : null;
}

function ready(d) {
  if (!schemaReady) {
    schemaReady = d.batch([
      d.prepare("CREATE TABLE IF NOT EXISTS contact_counter (k TEXT PRIMARY KEY, n INTEGER NOT NULL, exp INTEGER NOT NULL)"),
      d.prepare("CREATE TABLE IF NOT EXISTS contact_token (h TEXT PRIMARY KEY, v TEXT NOT NULL, exp INTEGER NOT NULL)"),
    ]).catch((e) => { schemaReady = null; throw e; });
  }
  return schemaReady;
}

// Now and then (1 request in 50) drop expired rows, after the response.
function sweep(env, context) {
  const d = d1(env);
  if (!d || Math.random() > 0.02) return;
  const now = nowSec();
  const p = ready(d).then(() => d.batch([
    d.prepare("DELETE FROM contact_counter WHERE exp < ?1").bind(now),
    d.prepare("DELETE FROM contact_token WHERE exp < ?1").bind(now),
  ])).catch(() => {});
  if (context && typeof context.waitUntil === "function") context.waitUntil(p);
}

// Claims a token for processing. Returns { claimed: true }, or { claimed: false, prior }
// where prior is the reference already sent, "" while another request holds it, or REFUSED.
async function claimToken(env, origin, tokenKey) {
  const now = nowSec();
  const d = d1(env);
  if (d) {
    try {
      await ready(d);
      const ins = await d.prepare("INSERT INTO contact_token (h, v, exp) VALUES (?1, 'pending', ?2) ON CONFLICT(h) DO NOTHING RETURNING v")
        .bind(tokenKey, now + PENDING_TTL).first();
      if (ins) {
        await cachePut(origin, tokenKey, "pending", PENDING_TTL);
        return { claimed: true };
      }
      const row = await d.prepare("SELECT v, exp FROM contact_token WHERE h = ?1").bind(tokenKey).first();
      if (row && Number(row.exp) <= now) {             // a stale claim: take it over
        await d.prepare("UPDATE contact_token SET v = 'pending', exp = ?2 WHERE h = ?1").bind(tokenKey, now + PENDING_TTL).run();
        return { claimed: true };
      }
      return { claimed: false, prior: row && row.v !== "pending" ? String(row.v) : "" };
    } catch (e) { /* fall back to the data-center cache */ }
  }
  const shared = await cacheGet(origin, tokenKey);
  if (shared) return { claimed: false, prior: shared === "pending" ? "" : shared };
  await cachePut(origin, tokenKey, "pending", PENDING_TTL);
  return { claimed: true };
}

async function rememberToken(env, origin, tokenKey, value) {
  const d = d1(env);
  if (d) {
    try { await d.prepare("UPDATE contact_token SET v = ?2, exp = ?3 WHERE h = ?1").bind(tokenKey, value, nowSec() + TOKEN_TTL).run(); } catch (e) {}
  }
  await cachePut(origin, tokenKey, value, TOKEN_TTL);
}

async function releaseToken(env, origin, tokenKey) {
  const d = d1(env);
  if (d) {
    try { await d.prepare("DELETE FROM contact_token WHERE h = ?1").bind(tokenKey).run(); } catch (e) {}
  }
  await cacheDelete(origin, tokenKey);
}

// Counts one event for `id` in every window of `rules`. Returns the first exceeded
// window as { win, retry } (seconds), or null while within all limits.
async function overLimit(env, origin, kind, id, rules) {
  const now = nowSec();
  const d = d1(env);
  if (d) {
    try {
      await ready(d);
      const res = await d.batch(rules.map((r) => {
        const bucket = Math.floor(now / r.win);
        return d.prepare("INSERT INTO contact_counter (k, n, exp) VALUES (?1, 1, ?2) ON CONFLICT(k) DO UPDATE SET n = n + 1 RETURNING n")
          .bind(`${kind}-${r.win}-${bucket}-${id}`, (bucket + 1) * r.win);
      }));
      let over = null;
      rules.forEach((r, i) => {
        const row = res[i] && res[i].results && res[i].results[0];
        const exp = (Math.floor(now / r.win) + 1) * r.win;
        if (row && Number(row.n) > r.max && !over) over = { win: r.win, retry: exp - now };
      });
      return over;
    } catch (e) { /* fall back to the data-center cache + memory */ }
  }
  let over = null;
  for (const r of rules) {
    const bucket = Math.floor(now / r.win);
    const key = `${kind}-${r.win}-${bucket}-${id}`;
    const exp = (bucket + 1) * r.win;
    const m = mem.get(key);
    const local = (m && m.exp > now ? m.n : 0) + 1;      // set before any await: exact inside this isolate
    mem.set(key, { n: local, exp });
    const shared = parseInt((await cacheGet(origin, key)) || "0", 10) || 0;
    const n = Math.max(local, shared + 1);
    const cur = mem.get(key);
    if (cur && n > cur.n) cur.n = n;
    await cachePut(origin, key, n, exp - now);
    if (n > r.max && !over) over = { win: r.win, retry: exp - now };
  }
  prune(now);
  return over;
}

function log(evt) {
  // Visible in Cloudflare Pages -> Functions -> real-time logs. No message bodies.
  try { console.log(JSON.stringify(Object.assign({ evt: "contact" }, evt))); } catch (e) {}
}

function attribution(f, request) {
  const a = {};
  for (const k of ATTRIBUTION) if (f[k]) a[k] = String(f[k]).slice(0, 500);
  const cf = request.cf || {};
  if (cf.city || cf.region) a.location = [cf.city, cf.region, cf.country].filter(Boolean).join(", ");
  const ua = request.headers.get("User-Agent") || "";
  a.device = /iPhone|iPad|Android|Mobile/i.test(ua) ? "mobile" : "desktop";
  const ref = a.first_referrer || a.referrer || "";
  a.channel = a.gclid || a.gbraid || a.wbraid || (/google/i.test(a.utm_source || "") && /cpc|paid/i.test(a.utm_medium || "")) ? "Google Ads"
    : a.msclkid || (/bing|microsoft/i.test(a.utm_source || "") && /cpc|paid/i.test(a.utm_medium || "")) ? "Microsoft Ads"
    : /google\.|bing\.|duckduckgo\.|yahoo\./i.test(ref) ? "Organic search"
    : /chatgpt|openai|perplexity|claude\.ai|copilot|gemini/i.test(ref) ? "AI assistant"
    : ref && !/prolinksystems\.com/i.test(ref) ? "Referral"
    : "Direct / unknown";
  return a;
}

async function graphToken(env) {
  const body = new URLSearchParams({
    grant_type: "client_credentials",
    client_id: env.MS_CLIENT_ID,
    client_secret: env.MS_CLIENT_SECRET,
    scope: "https://graph.microsoft.com/.default",
  });
  const r = await fetch(
    `https://login.microsoftonline.com/${env.MS_TENANT_ID}/oauth2/v2.0/token`,
    { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body }
  );
  if (!r.ok) throw new Error("token " + r.status + " " + (await r.text()).slice(0, 200));
  return (await r.json()).access_token;
}

async function sendMail(token, from, message) {
  const r = await fetch(`${GRAPH}/users/${encodeURIComponent(from)}/sendMail`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(message),
  });
  if (r.status !== 202) throw new Error("sendMail " + r.status + " " + (await r.text()).slice(0, 200));
}

function clip(s, n) {
  s = String(s == null ? "" : s).trim();
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function confirmationHtml(f0, ref) {
  // Exact reproduction of the prior EmailJS confirmation design; every dynamic
  // value is HTML-escaped. No third-party "sent via" footer. The echoed fields
  // are clipped (2026-11-26) so the email can't carry a long block of someone
  // else's text to the address typed into the form.
  const f = { first_name: clip(f0.first_name, 40), last_name: clip(f0.last_name, 60), company: clip(f0.company, 100),
    phone: clip(f0.phone, 40), interest: clip(f0.interest, 100) };
  return `<table style="background:#f0f4f9;padding:40px 20px"><tbody><tr><td><table style="max-width:600px;width:100%"><tbody><tr><td style="background:#0b3d6b;border-radius:12px 12px 0 0;padding:36px 48px;text-align:center"><div style="font-size:22px;font-weight:800;color:#fff;letter-spacing:-0.5px">PRO LINK SYSTEMS</div><div style="font-size:11px;color:rgba(255,255,255,0.6);margin-top:5px;letter-spacing:1.5px;text-transform:uppercase">Managed IT  ·  Cybersecurity  ·  Cloud</div></td></tr><tr><td style="background:#fff;padding:48px 48px 40px;border:1px solid #dde5f0;border-top:none"><div style="text-align:center;margin-bottom:28px">✓  Inquiry Confirmed</div><h1 style="font-size:24px;font-weight:800;color:#0d1117;margin:0 0 14px;letter-spacing:-0.5px">You're in good hands, ${esc(f.first_name)}.</h1><p style="font-size:15px;color:#4a5568;line-height:1.7;margin:0 0 28px">Thank you for reaching out to Pro Link Systems. We've received your inquiry and a member of our team will contact you within <strong style="color:#0b3d6b">one business day</strong> to schedule your complimentary IT discovery call.</p><div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 24px;margin-bottom:32px;text-align:center"><div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Confirmation Reference</div><div style="font-size:20px;font-weight:700;color:#0b3d6b;font-family:'Courier New',monospace;letter-spacing:3px">${esc(ref)}</div></div><div style="background:#f8fafc;border-left:3px solid #0b3d6b;border-radius:0 8px 8px 0;padding:20px 24px;margin-bottom:32px"><div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#0b3d6b;margin-bottom:14px">Your Inquiry Summary</div><table><tbody><tr><td style="font-size:13px;color:#94a3b8;padding:3px 16px 3px 0;width:90px">Name</td><td style="font-size:13px;color:#2d3748;font-weight:600">${esc(f.first_name)} ${esc(f.last_name)}</td></tr><tr><td style="font-size:13px;color:#94a3b8;padding:3px 16px 3px 0">Company</td><td style="font-size:13px;color:#2d3748;font-weight:600">${esc(f.company)}</td></tr><tr><td style="font-size:13px;color:#94a3b8;padding:3px 16px 3px 0">Phone</td><td style="font-size:13px;color:#2d3748;font-weight:600">${esc(f.phone)}</td></tr><tr><td style="font-size:13px;color:#94a3b8;padding:3px 16px 3px 0">Service</td><td style="font-size:13px;color:#2d3748;font-weight:600">${esc(f.interest || "General inquiry")}</td></tr></tbody></table></div><div style="margin-bottom:36px"><div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#0d1117;margin-bottom:16px">What Happens Next</div><table><tbody><tr><td style="padding-bottom:14px"><table><tbody><tr><td style="vertical-align:top;padding-right:12px"><div style="width:26px;height:26px;background:rgba(11,61,107,0.08);border-radius:50%;text-align:center;line-height:26px;font-size:11px;font-weight:800;color:#0b3d6b">1</div></td><td style="font-size:13px;color:#4a5568;line-height:1.6;vertical-align:middle"><strong style="color:#1a202c">We review your inquiry.</strong> Your request is already with our team.</td></tr></tbody></table></td></tr><tr><td style="padding-bottom:14px"><table><tbody><tr><td style="vertical-align:top;padding-right:12px"><div style="width:26px;height:26px;background:rgba(11,61,107,0.08);border-radius:50%;text-align:center;line-height:26px;font-size:11px;font-weight:800;color:#0b3d6b">2</div></td><td style="font-size:13px;color:#4a5568;line-height:1.6;vertical-align:middle"><strong style="color:#1a202c">A specialist reaches out.</strong> Within 1 business day to schedule your free discovery call.</td></tr></tbody></table></td></tr><tr><td><table><tbody><tr><td style="vertical-align:top;padding-right:12px"><div style="width:26px;height:26px;background:rgba(11,61,107,0.08);border-radius:50%;text-align:center;line-height:26px;font-size:11px;font-weight:800;color:#0b3d6b">3</div></td><td style="font-size:13px;color:#4a5568;line-height:1.6;vertical-align:middle"><strong style="color:#1a202c">We assess your needs.</strong> No obligation — just an honest conversation about your IT environment.</td></tr></tbody></table></td></tr></tbody></table></div><div style="text-align:center;margin-bottom:36px"><a href="tel:18008906133" style="display:inline-block;background:#0b3d6b;color:#fff;text-decoration:none;padding:14px 36px;border-radius:8px;font-size:14px;font-weight:700">Need Help Now?  1-800-890-6133</a></div><div style="height:1px;background:#e5eaf2;margin-bottom:24px"></div><p style="font-size:12px;color:#94a3b8;line-height:1.6;margin:0;text-align:center">If you did not submit this form, please disregard this email.<br /><a href="mailto:info@prolinksystems.com" style="color:#0b3d6b;text-decoration:none;font-weight:600">info@prolinksystems.com</a>  ·  <a href="tel:18008906133" style="color:#0b3d6b;text-decoration:none;font-weight:600">1-800-890-6133</a></p></td></tr><tr><td style="background:#0b3d6b;border-radius:0 0 12px 12px;padding:24px 48px;text-align:center"><p style="font-size:11px;color:rgba(255,255,255,0.5);margin:0;line-height:1.7">© 2026 Pro Link Systems, Inc.  ·  21241 Ventura Blvd, Woodland Hills, CA 91364<br />Southern California's trusted managed IT partner since 1999.</p></td></tr></tbody></table></td></tr></tbody></table>`;
}

function notifyHtml(f, ref, page, attr, unverified, noConfirm) {
  const row = (k, v) => `<tr><td style="padding:4px 16px 4px 0;color:#666">${esc(k)}</td><td style="font-weight:600">${esc(v)}</td></tr>`;
  const a = attr || {};
  const utm = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"].filter((k) => a[k]).map((k) => k.slice(4) + "=" + a[k]).join(" · ");
  const box = (html) => `<div style="background:#fff7e6;border:1px solid #f5c26b;border-radius:6px;padding:10px 12px;margin:0 0 14px;color:#7a4b00">
${html}</div>`;
  const why = unverified === "unlabeled-widget"
    ? "the form page was opened before the latest site update"
    : `Cloudflare could not confirm the robot check (${esc(unverified)})`;
  const banner = unverified
    ? box(`<strong>Unverified:</strong> ${why}. Likely a real visitor &mdash; no confirmation email was sent to them, so reply personally.`)
    : noConfirm
      ? box(`<strong>No confirmation email was sent to this visitor</strong> (${esc(noConfirm)}), so reply personally.`)
      : "";
  return `<div style="font-family:system-ui,Arial,sans-serif;font-size:14px;color:#111">
<h2 style="margin:0 0 4px">New website inquiry — ${esc(f.first_name)} ${esc(f.last_name)}</h2>
<p style="color:#666;margin:0 0 14px">Ref ${esc(ref)}${page ? " · from " + esc(page) : ""}${a.channel ? " · " + esc(a.channel) : ""}</p>
${banner}<table>${row("Name", f.first_name + " " + f.last_name)}${row("Company", f.company)}${row("Work email", f.email)}${row("Phone", f.phone || "(not given)")}${row("Service", f.interest || "(not specified)")}</table>
<p style="margin:16px 0 4px;color:#666">Message</p>
<div style="white-space:pre-wrap;background:#f6f8fb;border:1px solid #e2e8f0;border-radius:6px;padding:12px 14px">${esc(f.message)}</div>
<p style="margin:16px 0 4px;color:#666">How they found us</p>
<table>${row("Channel", a.channel || "unknown")}${a.landing_page ? row("Landed on", a.landing_page) : ""}${a.first_referrer ? row("Came from", a.first_referrer) : ""}${row("Form page", a.page_url || page || "")}${utm ? row("Campaign", utm) : ""}${a.gclid ? row("Google click id (gclid)", a.gclid) : ""}${a.gbraid ? row("Google click id (gbraid)", a.gbraid) : ""}${a.wbraid ? row("Google click id (wbraid)", a.wbraid) : ""}${a.msclkid ? row("Microsoft click id (msclkid)", a.msclkid) : ""}${a.location ? row("Location (approx.)", a.location) : ""}${row("Device", a.device || "")}</table>
${(a.gclid || a.gbraid || a.wbraid) ? `<p style="margin-top:10px;color:#666;font-size:12px">Ads lead-quality loop: when this lead qualifies (or becomes a client), record it with this click id in the war room <em>ads/lead_ledger.csv</em> (or tell Claude) so Google Ads learns which clicks produce real business.</p>` : ""}
<p style="margin-top:16px;color:#666;font-size:12px">Reply directly to reach the sender (${esc(f.email)}).</p></div>`;
}

function tooMany(retry) {
  return new Response(JSON.stringify({ success: false, message: TOO_MANY }), {
    status: 429,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store", "Retry-After": String(Math.max(1, retry || 60)) },
  });
}

// A token seen before: once its lead was sent, the repeat gets the same reference and nothing is sent again;
// while the first request is still running, the repeat is told to wait; a refused token stays refused.
function duplicate(ref, page) {
  if (ref === REFUSED) {
    log({ outcome: "rejected", reason: "refused-token-again", page });
    return json(400, { success: false, message: VERIFY_FAILED });
  }
  log({ outcome: "duplicate", page, ref: ref || "" });
  if (ref) return json(200, { success: true, refNumber: ref });
  return json(409, { success: false, message: "This form is already being sent. If no confirmation appears within a minute, please call 1-800-890-6133." });
}

export async function onRequestPost(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const origin = url.origin;

  // Per-IP limit on every POST, before any other work. No client IP (local dev) = not counted.
  const ipId = clientId(request);
  const ipHash = ipId ? await hashId("ip:" + ipId) : "";
  sweep(env, context);
  if (ipHash) {
    const over = await overLimit(env, origin, "post", ipHash, LIMITS.post);
    if (over) {
      log({ outcome: "rejected", reason: "rate-limit:post", window: over.win });
      return tooMany(over.retry);
    }
  }

  let f;
  try {
    f = await request.json();
  } catch {
    return json(400, { success: false, message: "Invalid request." });
  }
  if (!f || typeof f !== "object" || Array.isArray(f)) return json(400, { success: false, message: "Invalid request." });

  // Honeypot: silently accept-and-drop obvious bots. Only "botcheck" is a real
  // hidden honeypot; "challenge" is a VISIBLE "Primary IT Challenge" dropdown on
  // the industry pages, so it must NOT be treated as a bot signal.
  if (f.botcheck) return json(200, { success: true, refNumber: makeRef() });

  // Required env — fail closed if misconfigured.
  for (const k of ["MS_TENANT_ID", "MS_CLIENT_ID", "MS_CLIENT_SECRET", "SEND_FROM", "TURNSTILE_SECRET_KEY"]) {
    if (!env[k]) return json(500, { success: false, message: "Server not configured." });
  }

  // Normalize varied field names first so logs and the fail-safe see clean fields.
  normalize(f);
  const page = String(f.source_page || "").slice(0, 80);

  // Turnstile — the gate that makes the endpoint un-spammable.
  const token = f["cf-turnstile-response"] || f.turnstile_token;
  if (!token) {
    log({ outcome: "rejected", reason: "no-token", page });
    return json(400, { success: false, message: "Verification failed — please retry the challenge." });
  }
  // Once per token: claim it (this isolate at once, then this data center) before
  // verifying, so a double submit or a replay can't produce a second email.
  const tokenStr = String(token).slice(0, 2048);    // Turnstile tokens are at most 2048 characters
  const memKey = "tok:" + tokenStr;
  const seen = mem.get(memKey);
  if (seen && seen.exp > nowSec()) return duplicate(seen.v, page);
  mem.set(memKey, { n: 1, exp: nowSec() + PENDING_TTL, v: "" });
  const tokenKey = "tok-" + (await hashId("tok:" + tokenStr));
  const claim = await claimToken(env, origin, tokenKey);
  if (!claim.claimed) {
    mem.set(memKey, { n: 1, exp: nowSec() + (claim.prior ? TOKEN_TTL : PENDING_TTL), v: claim.prior });
    return duplicate(claim.prior, page);
  }
  const remember = async (value) => {
    mem.set(memKey, { n: 1, exp: nowSec() + TOKEN_TTL, v: value });
    await rememberToken(env, origin, tokenKey, value);
  };
  const release = async () => { mem.delete(memKey); await releaseToken(env, origin, tokenKey); };
  // A token solved on another host, for another widget, or already used/expired is refused, and stays
  // refused: replaying it never reaches siteverify again or any other path.
  const refuse = async (reason, extra, message) => {
    await remember(REFUSED);
    log(Object.assign({ outcome: "rejected", reason, page }, extra || {}));
    return json(400, { success: false, message: message || VERIFY_FAILED });
  };

  const v = await verifyTurnstile(env.TURNSTILE_SECRET_KEY, tokenStr);
  let unverified = "";
  if (v.ok) {
    // Solved on another host (a preview or an old deployment)? Or another widget (the checkout)?
    if (!hostnameOk(v.hostname, url.hostname, env)) return refuse("hostname", { host: v.hostname.slice(0, 80) });
    if (v.action && v.action !== ACTION) return refuse("action", { action: v.action.slice(0, 40) });
    if (!v.action) unverified = "unlabeled-widget";    // a page opened before the widgets carried the action
  } else {
    if (v.codes.includes("timeout-or-duplicate")) return refuse("expired-or-used", { codes: v.codes }, EXPIRED);
    if (!v.soft) {
      await release();                                  // a forged token fails siteverify every time anyway
      log({ outcome: "rejected", reason: "turnstile", codes: v.codes, page });
      return json(400, { success: false, message: VERIFY_FAILED });
    }
    unverified = v.codes.join(",") || "unknown";
  }

  // [UNVERIFIED] notifications are capped per IP, so a Cloudflare outage can't be turned into a flood.
  if (unverified && ipHash) {
    const over = await overLimit(env, origin, "unverified", ipHash, LIMITS.unverified);
    if (over) {
      await release();
      log({ outcome: "rejected", reason: "rate-limit:unverified", why: unverified, page });
      return tooMany(over.retry);
    }
  }

  // Validate the relaxed core set.
  const missing = REQUIRED.filter((k) => !String(f[k] || "").trim());
  if (missing.length) {
    await release();
    log({ outcome: "rejected", reason: "missing:" + missing.join("+"), page });
    return json(400, { success: false, message: "Please enter your name and email address." });
  }
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(f.email))) {
    await release();
    log({ outcome: "rejected", reason: "bad-email", page });
    return json(400, { success: false, message: "Please enter a valid email address." });
  }
  // Trim overly long inputs (defensive).
  for (const k of ["first_name", "last_name", "email", "phone", "company", "interest", "message"]) {
    if (f[k]) f[k] = String(f[k]).slice(0, 5000);
  }

  const ref = makeRef();
  const from = env.SEND_FROM;
  const notifyTo = env.LEAD_NOTIFY || env.SEND_FROM;
  const attr = attribution(f, request);

  // Visitor confirmation gates, decided now so the notification can say why none was sent.
  let noConfirm = null;
  if (!unverified) {
    if (["first_name", "last_name", "company", "phone", "interest"].some((k) => LINKISH.test(String(f[k] || "")))) {
      noConfirm = { code: "linkish", text: "a link or address in the name, company, phone or service field" };
    } else {
      const over = await overLimit(env, origin, "confirm", await hashId("to:" + String(f.email).trim().toLowerCase()), LIMITS.confirm);
      if (over) noConfirm = { code: "address-cap", text: `this address already had ${LIMITS.confirm[0].max} confirmations today` };
    }
  }

  let token2;
  try {
    token2 = await graphToken(env);
  } catch (e) {
    await release();
    log({ outcome: "error", reason: "graph-token", page, ref });
    return json(502, { success: false, message: "Could not send right now — please call 1-800-890-6133." });
  }

  // 1) Internal notification — this is lead capture; it must succeed.
  try {
    await sendMail(token2, from, {
      message: {
        subject: `${unverified ? "[UNVERIFIED] " : ""}New Contact Form Submission — Pro Link Systems Website [${ref}]`,
        body: { contentType: "HTML", content: notifyHtml(f, ref, page, attr, unverified, noConfirm && noConfirm.text) },
        toRecipients: [{ emailAddress: { address: notifyTo } }],
        from: { emailAddress: { address: from, name: "Pro Link Systems Website" } },
        replyTo: [{ emailAddress: { address: String(f.email) } }],
      },
      saveToSentItems: false,
    });
  } catch (e) {
    await release();
    log({ outcome: "error", reason: "notify-send", page, ref });
    return json(502, { success: false, message: "Could not send right now — please call 1-800-890-6133." });
  }

  // Lead captured: a repeat of this token now gets this reference and sends nothing.
  await remember(ref);

  // Unverified path: the lead is captured for a human to follow up; no outbound
  // mail goes to the submitted address (keeps this path useless for relay abuse).
  if (unverified) {
    log({ outcome: "accepted-unverified", codes: v.codes, why: unverified, page, ref, channel: attr.channel });
    return json(200, { success: true, refNumber: ref });
  }
  if (noConfirm) {
    log({ outcome: "accepted", confirmation: "skipped:" + noConfirm.code, page, ref, channel: attr.channel });
    return json(200, { success: true, refNumber: ref });
  }
  log({ outcome: "accepted", page, ref, channel: attr.channel });

  // 2) Visitor confirmation — best-effort; the lead is already captured.
  try {
    await sendMail(token2, from, {
      message: {
        subject: `Your inquiry has been received — Pro Link Systems [Ref: ${ref}]`,
        body: { contentType: "HTML", content: confirmationHtml(f, ref) },
        toRecipients: [{ emailAddress: { address: String(f.email) } }],
        from: { emailAddress: { address: from, name: "Pro Link Systems" } },
      },
      saveToSentItems: true,
    });
  } catch (e) {
    // swallow — confirmation is non-critical
  }

  return json(200, { success: true, refNumber: ref });
}

// Any non-POST method.
export async function onRequest(context) {
  if (context.request.method === "POST") return onRequestPost(context);
  return json(405, { success: false, message: "Method not allowed." });
}
