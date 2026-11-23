/**
 * Shared checkout core for Pro Link's self-service apps (Cloudflare Pages Functions).
 * -----------------------------------------------------------------------------
 * NOT a route: this module exports no onRequest handler. The routes live in
 * functions/api/checkout/ (start, anet-webhook, status) and serve EVERY app; an
 * app registers itself in ./products.js (price, order-id prefix, form intake,
 * order builder, hand-off). First app: the Microsoft 365 Security Assessment.
 *
 * Flow: order form -> POST /api/checkout/start (Turnstile + validation, pending
 * order saved in Workers KV, Authorize.net Accept Hosted token) -> the order page
 * shows Authorize.net's hosted payment form in an iframe (token posted into it;
 * full-window fallback; the site never sees card data) -> Authorize.net webhook ->
 * POST /api/checkout/anet-webhook (HMAC check, transaction re-read with
 * getTransactionDetails, then the product's hand-off).
 *
 * Bindings and variables (Cloudflare Pages -> Settings; entered by Pro Link in
 * the dashboard, never committed, never pasted into chat or a briefing):
 *   ORDERS                KV namespace binding: pending + paid orders
 *   ANET_ENV              "production" | "sandbox" (anything else = checkout off)
 *   ANET_API_LOGIN_ID     Authorize.net API Login ID                 [encrypted]
 *   ANET_TRANSACTION_KEY  Authorize.net Transaction Key              [encrypted]
 *   ANET_SIGNATURE_KEY    Authorize.net Signature Key (webhook HMAC) [encrypted]
 *   TURNSTILE_SECRET_KEY  already set for the contact form           [encrypted]
 *   MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET, SEND_FROM   already set (contact
 *                         form); used here only for failure alerts to Pro Link
 *   CHECKOUT_ALERT_TO     optional; default LEAD_NOTIFY, then SEND_FROM
 * Per product: the hand-off credential named in its registry entry
 * (GITHUB_ORDERS_TOKEN for the M365 assessment).
 */

export const KV_TTL_PENDING = 7 * 24 * 3600;   // a pending order lives 7 days
export const KV_TTL_PAID = 45 * 24 * 3600;     // outlives Authorize.net's ~9-day webhook retry window
export const UNAVAILABLE =
  "Online ordering isn't available right now. Please call 1-800-890-6133 or email info@prolinksystems.com.";

export function json(status, obj) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

export function log(evt) {
  // Cloudflare Pages -> Functions -> real-time logs. Never customer details or secrets.
  try { console.log(JSON.stringify(Object.assign({ evt: "checkout" }, evt))); } catch (e) { /* ignore */ }
}

/** RFC 3339 UTC timestamp without milliseconds, e.g. 2026-11-19T20:15:00Z (the order-JSON format). */
export function nowIso(d) {
  return (d || new Date()).toISOString().replace(/\.\d{3}Z$/, "Z");
}

// --------------------------------------------------------------------------
// Order ids: PREFIX-YYMMDD-XXXX (UTC date, 4 chars from a crypto RNG). Used as the
// Authorize.net invoiceNumber (max 20 chars), so prefixes stay short.
// --------------------------------------------------------------------------
export const ANY_ORDER_ID_RE = /^([A-Z0-9]{2,8})-[0-9]{6}-[A-Z0-9]{4}$/;

export function newOrderId(prefix, d) {
  const now = d || new Date();
  const ymd = String(now.getUTCFullYear() % 100).padStart(2, "0") +
    String(now.getUTCMonth() + 1).padStart(2, "0") + String(now.getUTCDate()).padStart(2, "0");
  const alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  let tail = "";
  while (tail.length < 4) {
    const bytes = new Uint8Array(8);
    crypto.getRandomValues(bytes);
    for (const b of bytes) {
      if (b < 252 && tail.length < 4) tail += alpha[b % 36];   // 252 = 7 x 36: no modulo bias
    }
  }
  return `${prefix}-${ymd}-${tail}`;
}

// --------------------------------------------------------------------------
// Input cleaning
// --------------------------------------------------------------------------
/** One-line text: control characters removed, whitespace collapsed, trimmed, capped. */
export function cleanLine(v, max) {
  const s = String(v == null ? "" : v).replace(/[\u0000-\u001F\u007F]/g, " ").replace(/\s+/g, " ").trim();
  return Array.from(s).slice(0, max).join("");
}

/** Multi-line text: keeps line breaks, drops other control characters, trims. Not capped (callers check). */
export function cleanText(v) {
  return String(v == null ? "" : v).replace(/\r\n?/g, "\n").replace(/[\u0000-\u0008\u000B-\u001F\u007F]/g, "").trim();
}

/** Email: trimmed, domain part lower-cased. */
export function normEmail(v) {
  const s = String(v == null ? "" : v).trim();
  const at = s.lastIndexOf("@");
  return at > 0 ? s.slice(0, at) + "@" + s.slice(at + 1).toLowerCase() : s;
}

/** Email domain from what people type: "acme.com", "https://www.acme.com/", "dana@acme.com" -> "acme.com". */
export function normDomain(v) {
  let d = String(v == null ? "" : v).trim().toLowerCase();
  d = d.replace(/^[a-z][a-z0-9+.-]*:\/\//, "");
  if (d.includes("@")) d = d.slice(d.lastIndexOf("@") + 1);
  d = d.split(/[\/?#:\s]/)[0].replace(/^www\./, "").replace(/\.$/, "");
  return d;
}

/**
 * Billing name + address from the order form (bill_* fields, every app). Collected on OUR page so the
 * embedded Authorize.net form only has to ask for the card; sent to Authorize.net as billTo (AVS) and
 * not stored anywhere. US addresses (country "US").
 */
const BILL_ZIP_RE = /^[A-Za-z0-9][A-Za-z0-9 -]{1,9}$/;
export function billingFromInput(input) {
  const b = {
    firstName: cleanLine(input.bill_first_name, 50),
    lastName: cleanLine(input.bill_last_name, 50),
    address: cleanLine(input.bill_address, 60),
    city: cleanLine(input.bill_city, 40),
    state: cleanLine(input.bill_state, 40),
    zip: cleanLine(input.bill_zip, 20),
  };
  for (const [field, v, label] of [["bill_first_name", b.firstName, "first name"], ["bill_last_name", b.lastName, "last name"],
    ["bill_address", b.address, "street address"], ["bill_city", b.city, "city"], ["bill_state", b.state, "state"]]) {
    if (!v) return { ok: false, field, message: `Please enter the billing ${label}.` };
  }
  if (!BILL_ZIP_RE.test(b.zip)) return { ok: false, field: "bill_zip", message: "Please enter the billing ZIP code." };
  return { ok: true, billTo: b };
}

export function clientIp(request) {
  const ip = (request.headers.get("CF-Connecting-IP") || "").trim();
  return /^[0-9a-fA-F:.]{2,45}$/.test(ip) ? ip : "";
}

// --------------------------------------------------------------------------
// JSON Schema (the subset the order contracts use): type, const, enum, required,
// properties, additionalProperties:false, minLength, maxLength, pattern,
// format: date-time. Returns a list of "path: problem" strings (empty = valid).
// --------------------------------------------------------------------------
const DATE_TIME_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/i;

export function validate(schema, value, path, errors) {
  path = path || "$";
  errors = errors || [];
  if (Object.prototype.hasOwnProperty.call(schema, "const") && value !== schema.const) {
    errors.push(`${path}: must be ${JSON.stringify(schema.const)}`);
  }
  if (Array.isArray(schema.enum) && !schema.enum.includes(value)) errors.push(`${path}: not an allowed value`);
  const t = schema.type;
  if (t) {
    const ok = t === "object" ? value !== null && typeof value === "object" && !Array.isArray(value)
      : t === "string" ? typeof value === "string"
      : t === "boolean" ? typeof value === "boolean"
      : t === "integer" ? Number.isInteger(value)
      : t === "number" ? typeof value === "number" && Number.isFinite(value)
      : t === "array" ? Array.isArray(value)
      : true;
    if (!ok) { errors.push(`${path}: must be ${t}`); return errors; }
  }
  if (typeof value === "string") {
    const len = Array.from(value).length;     // JSON Schema counts code points
    if (schema.minLength != null && len < schema.minLength) errors.push(`${path}: too short`);
    if (schema.maxLength != null && len > schema.maxLength) errors.push(`${path}: too long`);
    if (schema.pattern && !new RegExp(schema.pattern).test(value)) errors.push(`${path}: invalid format`);
    if (schema.format === "date-time" && !(DATE_TIME_RE.test(value) && !Number.isNaN(Date.parse(value)))) {
      errors.push(`${path}: not a date-time`);
    }
  }
  if (t === "object") {
    const props = schema.properties || {};
    for (const k of schema.required || []) {
      if (!Object.prototype.hasOwnProperty.call(value, k)) errors.push(`${path}.${k}: required`);
    }
    for (const [k, v] of Object.entries(value)) {
      if (Object.prototype.hasOwnProperty.call(props, k)) validate(props[k], v, `${path}.${k}`, errors);
      else if (schema.additionalProperties === false) errors.push(`${path}.${k}: unknown field`);
    }
  }
  return errors;
}

// --------------------------------------------------------------------------
// Cloudflare Turnstile. STRICT here (unlike the lead forms): no token, a forged
// token, or a stale/reused one all fail -- accepting "timeout-or-duplicate" would
// let one solved challenge mint unlimited payment pages (card-testing risk). The
// page simply resets the widget and the visitor submits again.
// --------------------------------------------------------------------------
export async function verifyTurnstile(secret, token) {
  if (!token) return { ok: false, codes: ["no-token"] };
  try {
    const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ secret, response: String(token) }),   // no remoteip (see contact.js)
    });
    const data = await r.json().catch(() => ({ success: false, "error-codes": ["bad-json"] }));
    return { ok: data.success === true, codes: data["error-codes"] || [] };
  } catch (e) {
    return { ok: false, codes: ["siteverify-unreachable"] };
  }
}

// --------------------------------------------------------------------------
// Authorize.net (JSON API; element ORDER matters -- it is converted to XML)
// --------------------------------------------------------------------------
export function anetConfig(env) {
  const mode = String(env.ANET_ENV || "").trim().toLowerCase();
  if (mode !== "production" && mode !== "sandbox") return null;
  const sandbox = mode === "sandbox";
  return {
    mode,
    sandbox,
    api: sandbox ? "https://apitest.authorize.net/xml/v1/request.api" : "https://api.authorize.net/xml/v1/request.api",
    hosted: sandbox ? "https://test.authorize.net/payment/payment" : "https://accept.authorize.net/payment/payment",
  };
}

export function merchantAuth(env) {
  return { name: env.ANET_API_LOGIN_ID, transactionKey: env.ANET_TRANSACTION_KEY };
}

/** POST one API request. Throws only on network failure / unparseable reply. */
export async function anetRequest(anet, body) {
  const r = await fetch(anet.api, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = (await r.text()).replace(/^﻿/, "");       // replies can start with a BOM
  let data;
  try { data = JSON.parse(text); } catch (e) { throw new Error(`anet-bad-reply ${r.status}`); }
  const msgs = (data && data.messages) || {};
  return {
    ok: msgs.resultCode === "Ok",
    data,
    codes: (Array.isArray(msgs.message) ? msgs.message : []).map((m) => m && m.code).filter(Boolean),
  };
}

/** Same-origin relay page that passes Authorize.net's iframe messages (resize, cancel) to the order
 *  page (assets/apps/anet-communicator.html, served without ".html"). Never move it. */
export const IFRAME_COMMUNICATOR_PATH = "/assets/apps/anet-communicator";

/** Accept Hosted token for one order. settingValue entries are JSON strings (Authorize.net's format).
 *  display "embedded" (the order page's iframe): NO Authorize.net receipt (it would be clipped in the
 *  non-scrolling frame); the form reports the result through the relay page (transactResponse) and
 *  checkout.js moves on to our own thank-you page. display "full" (the full-window fallback): the
 *  receipt shows, and its "Continue" leads to the same thank-you page.
 *  The billing address comes from our own form (billTo), so the hosted form shows only the card
 *  fields and the Pay button: no billing block, no order summary, no Cancel button. */
export async function hostedPaymentToken(env, anet, { product, orderId, email, ip, origin, billTo, company, display = "embedded" }) {
  const embedded = display !== "full";
  const s = (settingName, value) => ({ settingName, settingValue: JSON.stringify(value) });
  const transactionRequest = {
    transactionType: "authCaptureTransaction",
    amount: product.amount,
    order: { invoiceNumber: orderId, description: product.name.slice(0, 255) },
    customer: { email },
  };
  if (billTo) {                                   // element order = Authorize.net's customerAddressType
    const b = { firstName: billTo.firstName, lastName: billTo.lastName };
    if (company) b.company = Array.from(String(company)).slice(0, 50).join("");
    Object.assign(b, { address: billTo.address, city: billTo.city, state: billTo.state, zip: billTo.zip, country: "US" });
    transactionRequest.billTo = b;
  }
  if (ip) transactionRequest.customerIP = ip;
  const body = {
    getHostedPaymentPageRequest: {
      merchantAuthentication: merchantAuth(env),
      refId: orderId,
      transactionRequest,
      hostedPaymentSettings: {
        setting: [
          s("hostedPaymentReturnOptions", {
            showReceipt: !embedded,
            url: `${origin}${product.pages.thankYou}?order=${encodeURIComponent(orderId)}`,
            urlText: "Continue",
          }),
          s("hostedPaymentButtonOptions", { text: `Pay $${Number(product.amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}` }),
          s("hostedPaymentStyleOptions", { bgColor: "#0b3d6b" }),
          s("hostedPaymentPaymentOptions", { cardCodeRequired: true, showCreditCard: true, showBankAccount: false }),
          s("hostedPaymentSecurityOptions", { captcha: true }),
          s("hostedPaymentShippingAddressOptions", { show: false, required: false }),
          s("hostedPaymentBillingAddressOptions", { show: false, required: false }),
          s("hostedPaymentCustomerOptions", { showEmail: false, requiredEmail: false, addPaymentProfile: false }),
          s("hostedPaymentOrderOptions", { show: false, merchantName: "Pro Link Systems" }),
        ],
      },
    },
  };
  if (embedded) {
    body.getHostedPaymentPageRequest.hostedPaymentSettings.setting.push(
      s("hostedPaymentIFrameCommunicatorUrl", { url: `${origin}${IFRAME_COMMUNICATOR_PATH}` }));
  }
  const res = await anetRequest(anet, body);
  return { ok: res.ok && typeof res.data.token === "string" && res.data.token.length > 0, token: res.data.token, codes: res.codes };
}

export async function transactionDetails(env, anet, transId) {
  return anetRequest(anet, { getTransactionDetailsRequest: { merchantAuthentication: merchantAuth(env), transId } });
}

/**
 * What a getTransactionDetails transaction means for an order, by its CURRENT status:
 *   "paid"       captured (incl. a payment approved after a fraud-filter review: responseCode
 *                stays 4, the status becomes capturedPendingSettlement)
 *   "held"       held by the Fraud Detection Suite, waiting for Pro Link to approve or decline
 *   "declined"   the card was declined
 *   "error"      processing error (e.g. a duplicate submission); the customer saw it on the form
 *   "unexpected" anything else (voided, refunded, ...): a person should look
 */
export function paymentState(tx) {
  const s = String((tx && tx.transactionStatus) || "");
  const rc = Number(tx && tx.responseCode);
  if (s === "capturedPendingSettlement" || s === "settledSuccessfully" || (!s && rc === 1)) return "paid";
  if (s === "FDSPendingReview" || s === "FDSAuthorizedPendingReview" || (!s && rc === 4)) return "held";
  if (s === "declined" || (!s && rc === 2)) return "declined";
  if (rc === 3 || s === "generalError" || s === "communicationError") return "error";
  return "unexpected";
}

// --------------------------------------------------------------------------
// Webhook signature: X-ANET-Signature = "sha512=<hex>", HMAC-SHA512 over the RAW
// body with the Signature Key. Authorize.net's docs don't say whether the key is
// used as text or hex-decoded, so both are tried; either way only the holder of
// the secret key can produce a match. Case-insensitive, constant-time compare.
// The transaction is re-read from the API afterwards in any case.
// --------------------------------------------------------------------------
function hexToBytes(hex) {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.substr(i * 2, 2), 16);
  return out;
}

async function hmacSha512Hex(keyBytes, dataBytes) {
  const key = await crypto.subtle.importKey("raw", keyBytes, { name: "HMAC", hash: "SHA-512" }, false, ["sign"]);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, dataBytes));
  return Array.from(sig, (b) => b.toString(16).padStart(2, "0")).join("");
}

function sameHex(a, b) {
  a = a.toLowerCase();
  b = b.toLowerCase();
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export async function verifyAnetSignature(signatureKey, rawBytes, header) {
  const m = /^(?:sha512=)?([0-9a-f]{128})$/i.exec(String(header || "").trim());
  if (!m || !signatureKey) return false;
  const keys = [new TextEncoder().encode(signatureKey)];
  if (/^[0-9a-f]+$/i.test(signatureKey) && signatureKey.length % 2 === 0) keys.push(hexToBytes(signatureKey));
  let ok = false;
  for (const k of keys) {
    if (sameHex(await hmacSha512Hex(k, rawBytes), m[1])) ok = true;   // no early exit
  }
  return ok;
}

// --------------------------------------------------------------------------
// Orders in KV ("order:<id>")
// --------------------------------------------------------------------------
/** True when ORDERS is a usable Workers KV binding: not missing, and not a plain-text variable that
 *  happens to be named ORDERS (which would pass a truthiness check and then crash on .get). */
export function kvReady(env) {
  const kv = env && env.ORDERS;
  return !!kv && typeof kv.get === "function" && typeof kv.put === "function";
}

export async function getOrder(env, id) {
  return env.ORDERS.get(`order:${id}`, "json");
}

export async function putOrder(env, id, rec, ttl) {
  await env.ORDERS.put(`order:${id}`, JSON.stringify(rec), { expirationTtl: ttl });
}

// --------------------------------------------------------------------------
// Failure alerts to Pro Link (Microsoft Graph, the contact form's app + mailbox).
// Best effort, never throws; one email per tag per 6 hours (KV-deduped) so
// Authorize.net's retries can't flood the inbox. If KV itself is the problem the
// alert still goes out, without de-duplication: every caller sits behind a solved
// Turnstile check or a verified Authorize.net signature, so it can't be flooded.
// --------------------------------------------------------------------------
function esc(s) {
  return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export async function sendAlert(env, tag, subject, lines) {
  try {
    if (kvReady(env)) {
      const k = `alert:${tag}`;
      try {
        if (await env.ORDERS.get(k)) return false;
        await env.ORDERS.put(k, "1", { expirationTtl: 6 * 3600 });
      } catch (e) { /* KV unavailable: send anyway (see above) */ }
    }
    const to = env.CHECKOUT_ALERT_TO || env.LEAD_NOTIFY || env.SEND_FROM;
    if (!to || !env.MS_TENANT_ID || !env.MS_CLIENT_ID || !env.MS_CLIENT_SECRET || !env.SEND_FROM) {
      log({ outcome: "alert-not-sent", reason: "mail-not-configured", tag });
      return false;
    }
    const tr = await fetch(`https://login.microsoftonline.com/${env.MS_TENANT_ID}/oauth2/v2.0/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "client_credentials",
        client_id: env.MS_CLIENT_ID,
        client_secret: env.MS_CLIENT_SECRET,
        scope: "https://graph.microsoft.com/.default",
      }),
    });
    if (!tr.ok) throw new Error(`token ${tr.status}`);
    const token = (await tr.json()).access_token;
    const html = `<div style="font-family:system-ui,Arial,sans-serif;font-size:14px;color:#111">` +
      `<h2 style="margin:0 0 10px">${esc(subject)}</h2>` +
      lines.map((l) => `<p style="margin:0 0 8px">${esc(l)}</p>`).join("") +
      `<p style="margin-top:14px;color:#666;font-size:12px">Sent by the prolinksystems.com checkout ` +
      `(functions/api/checkout). Details: Cloudflare Pages &rarr; Functions &rarr; real-time logs.</p></div>`;
    const r = await fetch(`https://graph.microsoft.com/v1.0/users/${encodeURIComponent(env.SEND_FROM)}/sendMail`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        message: {
          subject: `[Checkout] ${subject}`,
          body: { contentType: "HTML", content: html },
          toRecipients: [{ emailAddress: { address: to } }],
          from: { emailAddress: { address: env.SEND_FROM, name: "Pro Link Systems Website" } },
        },
        saveToSentItems: false,
      }),
    });
    if (r.status !== 202) throw new Error(`sendMail ${r.status}`);
    return true;
  } catch (e) {
    log({ outcome: "alert-failed", tag, error: String(e && e.message || e).slice(0, 120) });
    return false;
  }
}
