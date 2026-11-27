/**
 * POST /api/contact  —  Cloudflare Pages Function
 * -----------------------------------------------------------------------------
 * Server-side handler for the website contact/lead forms. Replaces the old
 * client-side EmailJS + Web3Forms path, whose public keys let anyone send mail
 * as info@ to any recipient (the abuse that filled Sent Items with 279
 * unsolicited "inquiry received" messages).
 *
 * Security model (2026-11-27, Phase G final security release; every rule is
 * tested in tests/contact.test.mjs):
 *   - NOTHING is emailed unless Cloudflare Turnstile fully passes: siteverify
 *     says success, the token was solved on this host (prolinksystems.com and
 *     www count as one; the site key also works on plsmain.pages.dev and every
 *     preview / old-deployment subdomain of it), and it came from a lead-form
 *     widget (data-action="contact", site_guard check 19). Any other outcome —
 *     no token, a forged / expired / already-used token, another host, another
 *     widget (the checkout's "checkout"), a page opened before the widgets were
 *     labeled, a Turnstile secret Cloudflare rejects, Cloudflare erroring or
 *     unreachable — sends nothing and tells the visitor how to retry. (The
 *     2026-11-09 [UNVERIFIED] fallback was removed 2026-11-27.) We do NOT send
 *     `remoteip`: an IP that differs between the widget and this POST (iCloud
 *     Private Relay, mobile and corporate networks) must never cost a real lead.
 *   - A D1 database bound as CONTACT_DB is REQUIRED; without the binding the
 *     endpoint answers "Server not configured." (fail closed). Each verified
 *     submission is recorded there in ONE atomic batch: its token (one token =
 *     at most one lead, worldwide), the count for its IP (IPv6 per /64) and the
 *     count of confirmations to its address. D1 runs every statement on a single
 *     primary, so these limits are exact across data centers and concurrent
 *     requests. Only Turnstile-verified submissions write to D1, so junk traffic
 *     can't exhaust the D1 quota; every POST is first throttled per IP in this
 *     data center (memory + Cache API, no D1).
 *   - D1 OUTAGE (binding present, queries failing) — CONTACT_DB_OUTAGE_MODE:
 *       "degrade" (default): the verified lead still reaches info@, the per-IP
 *         limit falls back to this data center's counters, and NO confirmation
 *         goes to the typed address (an outage can't be used to mail third
 *         parties); the notification says so.
 *       "refuse": nothing is sent; the visitor is asked to call or retry.
 *     Siteverify's own once-per-token rule applies in both modes.
 *   - Visitor confirmations are capped per address, skipped when an echoed field
 *     holds link-like text, and their echoed fields are clipped.
 *   - A hidden honeypot field ("botcheck") silently drops obvious bots.
 *   - Credentials live ONLY in Pages env vars (never in page source). Every
 *     user-supplied value is HTML-escaped before it goes into an email body.
 *   - GET /api/contact?health=1 answers {ok, version, store} and sends nothing
 *     (release checks: is this code live, is the configuration complete, does D1 answer).
 *
 * Mail is sent from info@ via Microsoft Graph (application permissions), the
 * same mailbox/app the review agent already uses — real DKIM/SPF/DMARC, no
 * third-party relay, no per-email quota.
 *
 * Required Pages configuration (Production):
 *   MS_TENANT_ID          Azure AD tenant id
 *   MS_CLIENT_ID          App registration (client) id  [needs Mail.Send app perm]
 *   MS_CLIENT_SECRET      App client secret              [mark as "Secret"/encrypted]
 *   SEND_FROM             Sending mailbox, e.g. info@prolinksystems.com
 *   TURNSTILE_SECRET_KEY  Cloudflare Turnstile secret    [mark as "Secret"/encrypted]
 *   CONTACT_DB            D1 database binding (Settings -> Bindings -> D1 database).
 *                         The two tables are created on first use.
 * Optional:
 *   LEAD_NOTIFY           Where internal lead notifications go (default: SEND_FROM)
 *   CONTACT_DB_OUTAGE_MODE  "degrade" (default) or "refuse" — see above.
 *   TURNSTILE_ALLOWED_HOSTNAMES  Extra token hostnames accepted on any host, comma-separated.
 *                         Local testing only (Turnstile's dummy keys report "example.com");
 *                         never set it in Production.
 */

const GRAPH = "https://graph.microsoft.com/v1.0";
const SITEVERIFY = "https://challenges.cloudflare.com/turnstile/v0/siteverify";
const VERSION = "2026-11-27";      // reported by GET /api/contact?health=1 (release checks)
// Core fields every form must carry AFTER alias normalization. Everything else
// (last name, phone, company, message) is optional: an email is enough to follow
// up, and every extra required field costs leads (phone was required until
// 2026-11-09).
const REQUIRED = ["first_name", "email"];
const ENV_REQUIRED = ["MS_TENANT_ID", "MS_CLIENT_ID", "MS_CLIENT_SECRET", "SEND_FROM", "TURNSTILE_SECRET_KEY"];
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
// Siteverify failures that are OUR side or Cloudflare's (a rejected / missing secret, Cloudflare erroring or
// unreachable), not the visitor's: nothing is sent and the visitor is asked to retry shortly or call (503).
// 2026-11-27: these used to fall back to an [UNVERIFIED] notification to info@; that path is gone.
const SERVER_SIDE = ["invalid-input-secret", "missing-input-secret", "internal-error", "siteverify-unreachable", "bad-json"];
// Attribution fields the form scripts add (contact-form.js / contact.html).
const ATTRIBUTION = ["source_page", "page_url", "referrer", "landing_page", "first_referrer",
  "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "gbraid", "wbraid", "msclkid"];

// Turnstile hostname + action (2026-11-26). The production pair counts as one host.
const PROD_HOSTS = new Set(["prolinksystems.com", "www.prolinksystems.com"]);
const ACTION = "contact";          // data-action on every lead-form widget (site_guard check 19)

// Rate limits. A real visitor sends 1–2 POSTs. win = seconds, max = allowed per window.
const LIMITS = {
  edge: [{ win: 600, max: 10 }],                             // every POST from one IP, this data center (no D1)
  sent: [{ win: 600, max: 5 }, { win: 86400, max: 20 }],    // verified submissions from one IP, global (D1)
  confirm: [{ win: 86400, max: 2 }],                         // visitor confirmations to one address, global (D1)
};
const TOKEN_TTL = 86400;           // seconds a used token's outcome is remembered (tokens live 300 s)
const PENDING_TTL = 120;           // seconds a token counts as "being processed"
const D1_TIMEOUT_MS = 5000;        // a D1 call slower than this counts as an outage (D1's own limit is 30 s)

// What the visitor reads (contact-form.js and contact.html show `message` and reset the robot check).
// "Server not configured." and "Verification failed" are also what the release probes look for.
const MSG = {
  invalid: "Invalid request.",
  config: "Server not configured.",
  verify: "Verification failed — please retry the challenge.",
  expired: "The robot check expired or was already used. Please press Send again.",
  reload: "This page has been updated. Please reload it, then send your message again.",
  unavailable: "We couldn't complete the robot check just now. Please try again in a minute, or call 1-800-890-6133.",
  storeDown: "Our contact form is temporarily unavailable. Please try again in a few minutes, or call 1-800-890-6133.",
  busy: "This form is already being sent. If no confirmation appears within a minute, please call 1-800-890-6133.",
  tooMany: "Too many attempts from your network. Please wait a few minutes and try again, or call 1-800-890-6133.",
  sendFail: "Could not send right now — please call 1-800-890-6133.",
  missing: "Please enter your name and email address.",
  email: "Please enter a valid email address.",
};
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
  // Returns { ok, codes, hostname, action }. hostname/action come from a successful siteverify only.
  // No remoteip — see header.
  try {
    const r = await fetch(SITEVERIFY, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ secret, response: token }),
    });
    const data = await r.json().catch(() => ({ success: false, "error-codes": ["bad-json"] }));
    const codes = Array.isArray(data["error-codes"]) ? data["error-codes"].map(String) : [];
    if (data.success === true) {
      return { ok: true, codes, hostname: String(data.hostname || ""), action: String(data.action || "") };
    }
    return { ok: false, codes: codes.length ? codes : ["unknown"] };
  } catch (e) {
    return { ok: false, codes: ["siteverify-unreachable"] };
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
// LOCAL counters (this isolate's memory, exact, plus this data center's cache,
// shared by its isolates): the per-IP throttle on every POST, and the fallback
// when D1 is unavailable ("degrade" mode). Every cache call is wrapped; a cache
// error never blocks a visitor. The GLOBAL limits live in D1 (below).
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

// Counts one event for `id` in every window of `rules`, locally (see above). Returns the first exceeded
// window as { win, retry } (seconds), or null while within all limits. Never throws.
async function localCount(origin, kind, id, rules) {
  const now = nowSec();
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

// ---------------------------------------------------------------------------
// GLOBAL store: the D1 database bound as CONTACT_DB (required). D1 runs every
// statement on one primary, and a batch is one transaction, so an UPSERT ...
// RETURNING count is exact across data centers and concurrent requests, and a
// token claim succeeds exactly once worldwide.
// ---------------------------------------------------------------------------
let schemaReady = null;            // per isolate: creates the two tables once

function d1(env) {
  const d = env && env.CONTACT_DB;
  return d && typeof d.prepare === "function" && typeof d.batch === "function" ? d : null;
}

function configured(env) {
  return !!env && ENV_REQUIRED.every((k) => env[k]) && !!d1(env);
}

// Rejects when `p` takes longer than the D1 time limit (CONTACT_DB_TIMEOUT_MS overrides it; tests only).
function inTime(p, env) {
  const ms = Number(env && env.CONTACT_DB_TIMEOUT_MS) || D1_TIMEOUT_MS;
  let t;
  return Promise.race([p, new Promise((_, reject) => { t = setTimeout(() => reject(new Error("D1 timeout")), ms); })])
    .finally(() => clearTimeout(t));
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

// Claims the token unless a live claim exists (an expired "pending" claim is taken over), atomically.
const SQL_CLAIM = "INSERT INTO contact_token (h, v, exp) VALUES (?1, 'pending', ?2) " +
  "ON CONFLICT(h) DO UPDATE SET v = 'pending', exp = excluded.exp WHERE contact_token.exp <= ?3 RETURNING v";
const SQL_COUNT = "INSERT INTO contact_counter (k, n, exp) VALUES (?1, 1, ?2) ON CONFLICT(k) DO UPDATE SET n = n + 1 RETURNING n";

// One atomic D1 batch for a Turnstile-verified submission: claim its token, count it for its IP and
// for its address. Returns { claimed, ipOver, addrOver }; throws if D1 is unavailable.
async function recordVerified(d, tokenKey, ipHash, addrHash) {
  await ready(d);
  const now = nowSec();
  const stmts = [d.prepare(SQL_CLAIM).bind(tokenKey, now + PENDING_TTL, now)];
  const windows = [];
  const count = (kind, id, rules) => {
    for (const r of rules) {
      const bucket = Math.floor(now / r.win);
      windows.push({ kind, r, retry: (bucket + 1) * r.win - now });
      stmts.push(d.prepare(SQL_COUNT).bind(`${kind}-${r.win}-${bucket}-${id}`, (bucket + 1) * r.win));
    }
  };
  if (ipHash) count("sent", ipHash, LIMITS.sent);
  count("confirm", addrHash, LIMITS.confirm);
  const res = await d.batch(stmts);
  const rows = (i) => (res && res[i] && Array.isArray(res[i].results) ? res[i].results : []);
  const out = { claimed: rows(0).length > 0, ipOver: null, addrOver: null };
  windows.forEach((w, i) => {
    const row = rows(i + 1)[0];
    if (!row || Number(row.n) <= w.r.max) return;
    const over = { win: w.r.win, retry: w.retry };
    if (w.kind === "sent" && !out.ipOver) out.ipOver = over;
    if (w.kind === "confirm" && !out.addrOver) out.addrOver = over;
  });
  return out;
}

// After the notification: a repeat of this token now gets this reference. Never throws.
// useD1 = false while D1 is out (degrade mode): don't wait on it again.
async function setToken(env, origin, tokenKey, value, useD1) {
  const d = useD1 ? d1(env) : null;
  if (d) {
    try { await inTime(d.prepare("UPDATE contact_token SET v = ?2, exp = ?3 WHERE h = ?1").bind(tokenKey, value, nowSec() + TOKEN_TTL).run(), env); } catch (e) {}
  }
  await cachePut(origin, tokenKey, value, TOKEN_TTL);
}

// Nothing was sent for this token: forget the claim. Never throws.
async function dropToken(env, origin, tokenKey, useD1) {
  const d = useD1 ? d1(env) : null;
  if (d) {
    try { await inTime(d.prepare("DELETE FROM contact_token WHERE h = ?1").bind(tokenKey).run(), env); } catch (e) {}
  }
  await cacheDelete(origin, tokenKey);
}

// What became of a token siteverify reports as already used: its reference, "pending", or "" (unknown).
async function priorOutcome(env, origin, tokenKey) {
  const d = d1(env);
  if (d) {
    try {
      const row = await inTime(d.prepare("SELECT v, exp FROM contact_token WHERE h = ?1").bind(tokenKey).first(), env);
      if (row && Number(row.exp) > nowSec()) return String(row.v);
    } catch (e) {}
  }
  return (await cacheGet(origin, tokenKey)) || "";
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

function notifyHtml(f, ref, page, attr, noConfirm) {
  const row = (k, v) => `<tr><td style="padding:4px 16px 4px 0;color:#666">${esc(k)}</td><td style="font-weight:600">${esc(v)}</td></tr>`;
  const a = attr || {};
  const utm = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"].filter((k) => a[k]).map((k) => k.slice(4) + "=" + a[k]).join(" · ");
  const banner = noConfirm
    ? `<div style="background:#fff7e6;border:1px solid #f5c26b;border-radius:6px;padding:10px 12px;margin:0 0 14px;color:#7a4b00">
<strong>No confirmation email was sent to this visitor</strong> (${esc(noConfirm)}), so reply personally.</div>`
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
  return new Response(JSON.stringify({ success: false, message: MSG.tooMany }), {
    status: 429,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store", "Retry-After": String(Math.max(1, retry || 60)) },
  });
}

// A token Turnstile says was already used: its lead was sent -> the same reference, nothing sent again;
// still being processed -> wait; anything else (expired, refused, never ours) -> press Send again.
function duplicateReply(prior, page) {
  if (/^PLS-/.test(prior)) {
    log({ outcome: "duplicate", page, ref: prior });
    return json(200, { success: true, refNumber: prior });
  }
  if (prior === "pending") {
    log({ outcome: "rejected", reason: "in-progress", page });
    return json(409, { success: false, message: MSG.busy });
  }
  log({ outcome: "rejected", reason: "expired-or-used", page });
  return json(400, { success: false, message: MSG.expired });
}

export async function onRequestPost(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const origin = url.origin;

  // Required configuration, the D1 binding included: fail closed.
  if (!configured(env)) return json(500, { success: false, message: MSG.config });

  // Every POST from one IP is throttled in this data center first (no D1, no siteverify).
  // No client IP (local dev) = not counted.
  const ipId = clientId(request);
  const ipHash = ipId ? await hashId("ip:" + ipId) : "";
  if (ipHash) {
    const over = await localCount(origin, "edge", ipHash, LIMITS.edge);
    if (over) {
      log({ outcome: "rejected", reason: "rate-limit:edge", window: over.win });
      return tooMany(over.retry);
    }
  }

  let f;
  try {
    f = await request.json();
  } catch {
    return json(400, { success: false, message: MSG.invalid });
  }
  if (!f || typeof f !== "object" || Array.isArray(f)) return json(400, { success: false, message: MSG.invalid });

  // Honeypot: silently accept-and-drop obvious bots. Only "botcheck" is a real
  // hidden honeypot; "challenge" is a VISIBLE "Primary IT Challenge" dropdown on
  // the industry pages, so it must NOT be treated as a bot signal.
  if (f.botcheck) return json(200, { success: true, refNumber: makeRef() });

  normalize(f);
  const page = String(f.source_page || "").slice(0, 80);

  // Turnstile token present and plausible (real tokens are at most 2048 characters).
  const token = f["cf-turnstile-response"] || f.turnstile_token;
  if (!token || typeof token !== "string" || token.length > 2048) {
    log({ outcome: "rejected", reason: token ? "bad-token" : "no-token", page });
    return json(400, { success: false, message: MSG.verify });
  }

  // Check the form BEFORE spending the token, so a typo doesn't cost the visitor a new robot check.
  const missing = REQUIRED.filter((k) => !String(f[k] || "").trim());
  if (missing.length) {
    log({ outcome: "rejected", reason: "missing:" + missing.join("+"), page });
    return json(400, { success: false, message: MSG.missing });
  }
  if (!EMAIL_RE.test(String(f.email))) {
    log({ outcome: "rejected", reason: "bad-email", page });
    return json(400, { success: false, message: MSG.email });
  }
  for (const k of ["first_name", "last_name", "email", "phone", "company", "interest", "message"]) {
    if (f[k]) f[k] = String(f[k]).slice(0, 5000);
  }

  // The same token again in this isolate (double click, retry): answer from memory, no siteverify call.
  const tokenKey = "tok-" + (await hashId("tok:" + token));
  const memKey = "t:" + tokenKey;
  const seen = mem.get(memKey);
  if (seen && seen.exp > nowSec()) return duplicateReply(seen.v, page);

  // Turnstile: only a full pass goes on. Every other outcome sends nothing.
  const v = await verifyTurnstile(env.TURNSTILE_SECRET_KEY, token);
  if (!v.ok) {
    if (v.codes.some((c) => SERVER_SIDE.includes(c))) {
      // A secret Cloudflare rejects (e.g. a deployment left with a rotated key), or Cloudflare erroring.
      log({ outcome: "error", reason: "turnstile-unavailable", codes: v.codes, page });
      return json(503, { success: false, message: MSG.unavailable });
    }
    if (v.codes.includes("timeout-or-duplicate")) return duplicateReply(await priorOutcome(env, origin, tokenKey), page);
    log({ outcome: "rejected", reason: "turnstile", codes: v.codes, page });
    return json(400, { success: false, message: MSG.verify });
  }
  // Solved on another host (a preview, an old deployment, another site)? On another widget (the checkout)?
  // On a page opened before the widgets were labeled? None of these is a lead-form pass on this site.
  if (!hostnameOk(v.hostname, url.hostname, env)) {
    log({ outcome: "rejected", reason: "hostname", host: v.hostname.slice(0, 80), page });
    return json(400, { success: false, message: MSG.verify });
  }
  if (!v.action) {
    log({ outcome: "rejected", reason: "unlabeled-widget", page });
    return json(400, { success: false, message: MSG.reload });
  }
  if (v.action !== ACTION) {
    log({ outcome: "rejected", reason: "action", action: v.action.slice(0, 40), page });
    return json(400, { success: false, message: MSG.verify });
  }

  // Verified. Record it in D1 (token, IP count, address count) in one atomic batch.
  mem.set(memKey, { n: 1, exp: nowSec() + PENDING_TTL, v: "pending" });
  const addrHash = await hashId("to:" + String(f.email).trim().toLowerCase());
  let store = "d1";
  let rec;
  try {
    rec = await inTime(recordVerified(d1(env), tokenKey, ipHash, addrHash), env);
    sweep(env, context);                              // only verified submissions ever write to D1
  } catch (e) {
    // D1 unavailable. See CONTACT_DB_OUTAGE_MODE in the header.
    if (String(env.CONTACT_DB_OUTAGE_MODE || "").trim().toLowerCase() === "refuse") {
      mem.delete(memKey);
      log({ outcome: "error", reason: "store-unavailable", mode: "refuse", page });
      return json(503, { success: false, message: MSG.storeDown });
    }
    store = "degraded";
    const shared = await cacheGet(origin, tokenKey);
    if (shared) {
      mem.set(memKey, { n: 1, exp: nowSec() + (shared === "pending" ? PENDING_TTL : TOKEN_TTL), v: shared });
      return duplicateReply(shared, page);
    }
    await cachePut(origin, tokenKey, "pending", PENDING_TTL);
    rec = { claimed: true, ipOver: ipHash ? await localCount(origin, "sent", ipHash, LIMITS.sent) : null, addrOver: null };
  }
  if (!rec.claimed) {
    // Another request holds this token (siteverify passes a token only once, so this is a race at most).
    mem.delete(memKey);
    return duplicateReply(await priorOutcome(env, origin, tokenKey), page);
  }
  const release = async () => { mem.delete(memKey); await dropToken(env, origin, tokenKey, store === "d1"); };
  if (rec.ipOver) {
    await release();
    log({ outcome: "rejected", reason: "rate-limit:sent", window: rec.ipOver.win, store, page });
    return tooMany(rec.ipOver.retry);
  }

  const ref = makeRef();
  const from = env.SEND_FROM;
  const notifyTo = env.LEAD_NOTIFY || env.SEND_FROM;
  const attr = attribution(f, request);

  // Visitor confirmation gates, decided now so the notification can say why none was sent.
  let noConfirm = null;
  if (store !== "d1") {
    noConfirm = { code: "store-unavailable", text: "the rate-limit database was unavailable, so no email went to the typed address" };
  } else if (["first_name", "last_name", "company", "phone", "interest"].some((k) => LINKISH.test(String(f[k] || "")))) {
    noConfirm = { code: "linkish", text: "a link or address in the name, company, phone or service field" };
  } else if (rec.addrOver) {
    noConfirm = { code: "address-cap", text: `this address already had ${LIMITS.confirm[0].max} confirmations today` };
  }

  let token2;
  try {
    token2 = await graphToken(env);
  } catch (e) {
    await release();
    log({ outcome: "error", reason: "graph-token", page, ref });
    return json(502, { success: false, message: MSG.sendFail });
  }

  // 1) Internal notification — this is lead capture; it must succeed.
  try {
    await sendMail(token2, from, {
      message: {
        subject: `New Contact Form Submission — Pro Link Systems Website [${ref}]`,
        body: { contentType: "HTML", content: notifyHtml(f, ref, page, attr, noConfirm && noConfirm.text) },
        toRecipients: [{ emailAddress: { address: notifyTo } }],
        from: { emailAddress: { address: from, name: "Pro Link Systems Website" } },
        replyTo: [{ emailAddress: { address: String(f.email) } }],
      },
      saveToSentItems: false,
    });
  } catch (e) {
    await release();
    log({ outcome: "error", reason: "notify-send", page, ref });
    return json(502, { success: false, message: MSG.sendFail });
  }

  // Lead captured: a repeat of this token now gets this reference and sends nothing.
  mem.set(memKey, { n: 1, exp: nowSec() + TOKEN_TTL, v: ref });
  await setToken(env, origin, tokenKey, ref, store === "d1");

  if (noConfirm) {
    log({ outcome: "accepted", confirmation: "skipped:" + noConfirm.code, store, page, ref, channel: attr.channel });
    return json(200, { success: true, refNumber: ref, confirmation: false });   // lets a page say "we'll reply personally"
  }
  log({ outcome: "accepted", store, page, ref, channel: attr.channel });

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

// GET /api/contact?health=1 — release checks. Sends nothing; says whether this code is live, the configuration
// is complete (the D1 binding included) and D1 answers.
async function health(env) {
  if (!configured(env)) return json(503, { ok: false, version: VERSION, reason: "not-configured" });
  try {
    const d = d1(env);
    await inTime(ready(d).then(() => d.prepare("SELECT 1 AS ok").first()), env);
    return json(200, { ok: true, version: VERSION, store: "d1" });
  } catch (e) {
    return json(503, { ok: false, version: VERSION, reason: "store-unavailable" });
  }
}

// Any other method (and the health check).
export async function onRequest(context) {
  const { request, env } = context;
  if (request.method === "POST") return onRequestPost(context);
  if (request.method === "GET" && new URL(request.url).searchParams.has("health")) return health(env);
  return json(405, { success: false, message: "Method not allowed." });
}
