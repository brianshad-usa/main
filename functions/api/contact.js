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
 *   - Fail-safe for humans (added 2026-11-09): if siteverify reports only that
 *     a REAL token expired/was reused ("timeout-or-duplicate") or Cloudflare
 *     itself errored, the internal notification still goes to info@ marked
 *     [UNVERIFIED] — but NO visitor confirmation is sent, so this path can
 *     never be used to relay mail to third parties.
 *   - A hidden honeypot field ("botcheck") silently drops obvious bots.
 *   - All sending happens here with credentials that live ONLY in Pages env
 *     vars (never in page source). The recipient of the confirmation is the
 *     submitter, but the endpoint is un-spammable without a Turnstile token.
 *   - Every user-supplied value is HTML-escaped before being placed in email
 *     bodies, so form input can't inject markup/links into the messages.
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
 */

const GRAPH = "https://graph.microsoft.com/v1.0";
// Core fields every form must carry AFTER alias normalization. Everything else
// (last name, phone, company, message) is optional: an email is enough to follow
// up, and every extra required field costs leads (phone was required until
// 2026-11-09).
const REQUIRED = ["first_name", "email"];
// Siteverify outcomes that mean "a real token went stale / Cloudflare hiccupped",
// not "this is a bot" — these fall back to an [UNVERIFIED] notification.
const SOFT_FAIL_CODES = ["timeout-or-duplicate", "internal-error"];
// Attribution fields the form scripts add (contact-form.js / contact.html).
const ATTRIBUTION = ["source_page", "page_url", "referrer", "landing_page", "first_referrer",
  "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "msclkid"];

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
  // Returns { ok, soft, codes }: ok = verified; soft = only a stale-token /
  // Cloudflare-side failure (a human, not a bot). No remoteip — see header.
  try {
    const body = new URLSearchParams({ secret, response: token || "" });
    const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    const data = await r.json().catch(() => ({ success: false, "error-codes": ["bad-json"] }));
    const codes = data["error-codes"] || [];
    if (data.success) return { ok: true, soft: false, codes };
    return { ok: false, soft: codes.length > 0 && codes.every((c) => SOFT_FAIL_CODES.includes(c)), codes };
  } catch (e) {
    // Network failure reaching Cloudflare: never the visitor's fault.
    return { ok: false, soft: true, codes: ["siteverify-unreachable"] };
  }
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
  a.channel = a.gclid || (/google/i.test(a.utm_source || "") && /cpc|paid/i.test(a.utm_medium || "")) ? "Google Ads"
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

function confirmationHtml(f, ref) {
  // Exact reproduction of the prior EmailJS confirmation design; every dynamic
  // value is HTML-escaped. No third-party "sent via" footer.
  return `<table style="background:#f0f4f9;padding:40px 20px"><tbody><tr><td><table style="max-width:600px;width:100%"><tbody><tr><td style="background:#0b3d6b;border-radius:12px 12px 0 0;padding:36px 48px;text-align:center"><div style="font-size:22px;font-weight:800;color:#fff;letter-spacing:-0.5px">PRO LINK SYSTEMS</div><div style="font-size:11px;color:rgba(255,255,255,0.6);margin-top:5px;letter-spacing:1.5px;text-transform:uppercase">Managed IT  ·  Cybersecurity  ·  Cloud</div></td></tr><tr><td style="background:#fff;padding:48px 48px 40px;border:1px solid #dde5f0;border-top:none"><div style="text-align:center;margin-bottom:28px">✓  Inquiry Confirmed</div><h1 style="font-size:24px;font-weight:800;color:#0d1117;margin:0 0 14px;letter-spacing:-0.5px">You're in good hands, ${esc(f.first_name)}.</h1><p style="font-size:15px;color:#4a5568;line-height:1.7;margin:0 0 28px">Thank you for reaching out to Pro Link Systems. We've received your inquiry and a member of our team will contact you within <strong style="color:#0b3d6b">one business day</strong> to schedule your complimentary IT discovery call.</p><div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 24px;margin-bottom:32px;text-align:center"><div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Confirmation Reference</div><div style="font-size:20px;font-weight:700;color:#0b3d6b;font-family:'Courier New',monospace;letter-spacing:3px">${esc(ref)}</div></div><div style="background:#f8fafc;border-left:3px solid #0b3d6b;border-radius:0 8px 8px 0;padding:20px 24px;margin-bottom:32px"><div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#0b3d6b;margin-bottom:14px">Your Inquiry Summary</div><table><tbody><tr><td style="font-size:13px;color:#94a3b8;padding:3px 16px 3px 0;width:90px">Name</td><td style="font-size:13px;color:#2d3748;font-weight:600">${esc(f.first_name)} ${esc(f.last_name)}</td></tr><tr><td style="font-size:13px;color:#94a3b8;padding:3px 16px 3px 0">Company</td><td style="font-size:13px;color:#2d3748;font-weight:600">${esc(f.company)}</td></tr><tr><td style="font-size:13px;color:#94a3b8;padding:3px 16px 3px 0">Phone</td><td style="font-size:13px;color:#2d3748;font-weight:600">${esc(f.phone)}</td></tr><tr><td style="font-size:13px;color:#94a3b8;padding:3px 16px 3px 0">Service</td><td style="font-size:13px;color:#2d3748;font-weight:600">${esc(f.interest || "General inquiry")}</td></tr></tbody></table></div><div style="margin-bottom:36px"><div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#0d1117;margin-bottom:16px">What Happens Next</div><table><tbody><tr><td style="padding-bottom:14px"><table><tbody><tr><td style="vertical-align:top;padding-right:12px"><div style="width:26px;height:26px;background:rgba(11,61,107,0.08);border-radius:50%;text-align:center;line-height:26px;font-size:11px;font-weight:800;color:#0b3d6b">1</div></td><td style="font-size:13px;color:#4a5568;line-height:1.6;vertical-align:middle"><strong style="color:#1a202c">We review your inquiry.</strong> Your request is already with our team.</td></tr></tbody></table></td></tr><tr><td style="padding-bottom:14px"><table><tbody><tr><td style="vertical-align:top;padding-right:12px"><div style="width:26px;height:26px;background:rgba(11,61,107,0.08);border-radius:50%;text-align:center;line-height:26px;font-size:11px;font-weight:800;color:#0b3d6b">2</div></td><td style="font-size:13px;color:#4a5568;line-height:1.6;vertical-align:middle"><strong style="color:#1a202c">A specialist reaches out.</strong> Within 1 business day to schedule your free discovery call.</td></tr></tbody></table></td></tr><tr><td><table><tbody><tr><td style="vertical-align:top;padding-right:12px"><div style="width:26px;height:26px;background:rgba(11,61,107,0.08);border-radius:50%;text-align:center;line-height:26px;font-size:11px;font-weight:800;color:#0b3d6b">3</div></td><td style="font-size:13px;color:#4a5568;line-height:1.6;vertical-align:middle"><strong style="color:#1a202c">We assess your needs.</strong> No obligation — just an honest conversation about your IT environment.</td></tr></tbody></table></td></tr></tbody></table></div><div style="text-align:center;margin-bottom:36px"><a href="tel:18008906133" style="display:inline-block;background:#0b3d6b;color:#fff;text-decoration:none;padding:14px 36px;border-radius:8px;font-size:14px;font-weight:700">Need Help Now?  1-800-890-6133</a></div><div style="height:1px;background:#e5eaf2;margin-bottom:24px"></div><p style="font-size:12px;color:#94a3b8;line-height:1.6;margin:0;text-align:center">If you did not submit this form, please disregard this email.<br /><a href="mailto:info@prolinksystems.com" style="color:#0b3d6b;text-decoration:none;font-weight:600">info@prolinksystems.com</a>  ·  <a href="tel:18008906133" style="color:#0b3d6b;text-decoration:none;font-weight:600">1-800-890-6133</a></p></td></tr><tr><td style="background:#0b3d6b;border-radius:0 0 12px 12px;padding:24px 48px;text-align:center"><p style="font-size:11px;color:rgba(255,255,255,0.5);margin:0;line-height:1.7">© 2026 Pro Link Systems, Inc.  ·  21241 Ventura Blvd, Woodland Hills, CA 91364<br />Southern California's trusted managed IT partner since 1999.</p></td></tr></tbody></table></td></tr></tbody></table>`;
}

function notifyHtml(f, ref, page, attr, unverified) {
  const row = (k, v) => `<tr><td style="padding:4px 16px 4px 0;color:#666">${esc(k)}</td><td style="font-weight:600">${esc(v)}</td></tr>`;
  const a = attr || {};
  const utm = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"].filter((k) => a[k]).map((k) => k.slice(4) + "=" + a[k]).join(" · ");
  const banner = unverified
    ? `<div style="background:#fff7e6;border:1px solid #f5c26b;border-radius:6px;padding:10px 12px;margin:0 0 14px;color:#7a4b00">
<strong>Unverified:</strong> the robot check expired or Cloudflare could not confirm it (${esc(unverified)}). Likely a real visitor &mdash; no confirmation email was sent to them, so reply personally.</div>`
    : "";
  return `<div style="font-family:system-ui,Arial,sans-serif;font-size:14px;color:#111">
<h2 style="margin:0 0 4px">New website inquiry — ${esc(f.first_name)} ${esc(f.last_name)}</h2>
<p style="color:#666;margin:0 0 14px">Ref ${esc(ref)}${page ? " · from " + esc(page) : ""}${a.channel ? " · " + esc(a.channel) : ""}</p>
${banner}<table>${row("Name", f.first_name + " " + f.last_name)}${row("Company", f.company)}${row("Work email", f.email)}${row("Phone", f.phone || "(not given)")}${row("Service", f.interest || "(not specified)")}</table>
<p style="margin:16px 0 4px;color:#666">Message</p>
<div style="white-space:pre-wrap;background:#f6f8fb;border:1px solid #e2e8f0;border-radius:6px;padding:12px 14px">${esc(f.message)}</div>
<p style="margin:16px 0 4px;color:#666">How they found us</p>
<table>${row("Channel", a.channel || "unknown")}${a.landing_page ? row("Landed on", a.landing_page) : ""}${a.first_referrer ? row("Came from", a.first_referrer) : ""}${row("Form page", a.page_url || page || "")}${utm ? row("Campaign", utm) : ""}${a.gclid ? row("Google click id", "present") : ""}${a.location ? row("Location (approx.)", a.location) : ""}${row("Device", a.device || "")}</table>
<p style="margin-top:16px;color:#666;font-size:12px">Reply directly to reach the sender (${esc(f.email)}).</p></div>`;
}

export async function onRequestPost(context) {
  const { request, env } = context;

  let f;
  try {
    f = await request.json();
  } catch {
    return json(400, { success: false, message: "Invalid request." });
  }

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
  const v = await verifyTurnstile(env.TURNSTILE_SECRET_KEY, token);
  let unverified = "";
  if (!v.ok) {
    if (!v.soft) {
      log({ outcome: "rejected", reason: "turnstile", codes: v.codes, page });
      return json(400, { success: false, message: "Verification failed — please retry the challenge." });
    }
    unverified = v.codes.join(",") || "unknown";
  }

  // Validate the relaxed core set.
  const missing = REQUIRED.filter((k) => !String(f[k] || "").trim());
  if (missing.length) {
    log({ outcome: "rejected", reason: "missing:" + missing.join("+"), page });
    return json(400, { success: false, message: "Please enter your name and email address." });
  }
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(f.email))) {
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

  let token2;
  try {
    token2 = await graphToken(env);
  } catch (e) {
    log({ outcome: "error", reason: "graph-token", page, ref });
    return json(502, { success: false, message: "Could not send right now — please call 1-800-890-6133." });
  }

  // 1) Internal notification — this is lead capture; it must succeed.
  try {
    await sendMail(token2, from, {
      message: {
        subject: `${unverified ? "[UNVERIFIED] " : ""}New Contact Form Submission — Pro Link Systems Website [${ref}]`,
        body: { contentType: "HTML", content: notifyHtml(f, ref, page, attr, unverified) },
        toRecipients: [{ emailAddress: { address: notifyTo } }],
        from: { emailAddress: { address: from, name: "Pro Link Systems Website" } },
        replyTo: [{ emailAddress: { address: String(f.email) } }],
      },
      saveToSentItems: false,
    });
  } catch (e) {
    log({ outcome: "error", reason: "notify-send", page, ref });
    return json(502, { success: false, message: "Could not send right now — please call 1-800-890-6133." });
  }

  // Unverified path: the lead is captured for a human to follow up; no outbound
  // mail goes to the submitted address (keeps this path useless for relay abuse).
  if (unverified) {
    log({ outcome: "accepted-unverified", codes: v.codes, page, ref, channel: attr.channel });
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
