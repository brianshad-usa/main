/**
 * POST /api/checkout/start  --  Cloudflare Pages Function (all self-service apps)
 * -----------------------------------------------------------------------------
 * Body: the app's order form as JSON, plus { product: "<slug>", "cf-turnstile-response",
 * source: {page, utm_*, gclid} }. Verifies Turnstile (strict: never a stale or reused token and,
 * since 2026-11-27, only a token solved on this host by the checkout widget, action "checkout";
 * see core.js), validates the form with the app's intake(), stores the pending order in KV
 * (7 days), and returns an Authorize.net Accept Hosted token: { ok, order_id, token, post_url }.
 * The browser then posts the token to Authorize.net's hosted payment page; card data never
 * touches this site.
 * Setup and secrets: functions/_lib/checkout/core.js header.
 *
 * Every answer is JSON with a message the order page can show. Missing settings and anything
 * unexpected after the Turnstile check (a KV outage, a platform error) also email Pro Link the
 * cause (2026-11-23: a bare Cloudflare error page left the customer with "Something went wrong"
 * and Pro Link with no alert).
 */
import {
  json, log, nowIso, newOrderId, clientIp, verifyTurnstile, anetConfig, billingFromInput, cleanLine,
  hostedPaymentToken, getOrder, putOrder, sendAlert, kvReady, KV_TTL_PENDING, UNAVAILABLE,
} from "../../_lib/checkout/core.js";
import { productById } from "../../_lib/checkout/products.js";

const START_FAILED = "We couldn't start the secure payment. Please try again, or call 1-800-890-6133.";

/** Names (never values) of the settings the checkout needs and doesn't have. */
function missingSettings(env, anet) {
  const out = [];
  if (!anet) out.push('ANET_ENV ("production" or "sandbox")');
  if (!env.ANET_API_LOGIN_ID) out.push("ANET_API_LOGIN_ID");
  if (!env.ANET_TRANSACTION_KEY) out.push("ANET_TRANSACTION_KEY");
  if (!kvReady(env)) out.push(env.ORDERS ? "ORDERS (it is a plain variable; it must be a KV namespace binding)" : "ORDERS (KV namespace binding)");
  if (!env.TURNSTILE_SECRET_KEY) out.push("TURNSTILE_SECRET_KEY");
  return out;
}

export async function onRequestPost({ request, env }) {
  let input;
  try {
    input = await request.json();
  } catch (e) {
    return json(400, { ok: false, message: "Invalid request." });
  }
  if (!input || typeof input !== "object") return json(400, { ok: false, message: "Invalid request." });

  const product = productById(input.product);
  if (!product) return json(400, { ok: false, message: "Unknown product." });
  if (input.botcheck) {                       // hidden honeypot
    log({ outcome: "rejected", reason: "honeypot", product: product.id });
    return json(400, { ok: false, message: "Please try again." });
  }

  const anet = anetConfig(env);
  const missing = missingSettings(env, anet);
  if (missing.length) {
    log({ outcome: "unavailable", reason: "not-configured", missing, product: product.id });
    // Tell Pro Link, but only for a visitor who passed Turnstile on this host with the checkout widget:
    // a bare POST, or a token from a lead form or a preview, can't trigger email.
    if (env.TURNSTILE_SECRET_KEY && (await verifyTurnstile(env, request, input["cf-turnstile-response"])).ok) {
      await sendAlert(env, "start-not-configured", "Checkout is switched off: settings missing",
        [`Someone tried to order the ${product.name}, but these Cloudflare Pages settings are missing or invalid: ${missing.join("; ")}.`,
          "Customers see \"Online ordering isn't available right now\". Changed settings apply from the next deployment."]);
    }
    return json(503, { ok: false, message: UNAVAILABLE });
  }

  // Strict (core.js): Cloudflare must accept the token, and it must come from the checkout widget on
  // this host. A token solved on a preview / old deployment or by a lead form is refused here.
  const ts = await verifyTurnstile(env, request, input["cf-turnstile-response"]);
  if (!ts.ok) {
    log({ outcome: "rejected", reason: ts.reason, codes: ts.codes, host: ts.hostname, action: ts.action, product: product.id });
    return json(400, { ok: false, field: "turnstile", message: "Please complete the security check again, then continue." });
  }

  try {
    return await startOrder(request, env, input, product, anet);
  } catch (e) {
    const detail = cleanLine(e && e.name ? `${e.name}: ${e.message}` : String(e), 300);
    log({ outcome: "error", reason: "exception", detail: detail.slice(0, 160), product: product.id });
    await sendAlert(env, "start-exception", "Checkout failed before the payment page",
      [`The order form's request failed inside /api/checkout/start (mode: ${anet.mode}): ${detail}`,
        `Customers see "${START_FAILED}" Details: Cloudflare Pages > Functions > real-time logs.`]);
    return json(500, { ok: false, message: START_FAILED });
  }
}

async function startOrder(request, env, input, product, anet) {
  const now = nowIso();
  const ip = clientIp(request);
  let orderId = newOrderId(product.orderPrefix);
  if (await getOrder(env, orderId)) orderId = newOrderId(product.orderPrefix);   // 1-in-1.7M same-day clash

  const res = product.intake(input, { now, ip, orderId, sandbox: anet.sandbox });
  if (!res.ok) {
    log({ outcome: "rejected", reason: "validation", field: res.field, errors: res.errors, product: product.id });
    return json(400, { ok: false, field: res.field, message: res.message });
  }
  const bill = billingFromInput(input);           // every app: billing address for Authorize.net (not stored)
  if (!bill.ok) {
    log({ outcome: "rejected", reason: "validation", field: bill.field, product: product.id });
    return json(400, { ok: false, field: bill.field, message: bill.message });
  }

  // Two payment sessions for the same order: the embedded form (no Authorize.net receipt) and the
  // full-window fallback (with receipt). Paying twice is blocked by Authorize.net's duplicate window
  // and, beyond it, flagged by the webhook ("second payment").
  const origin = new URL(request.url).origin;
  const tokenArgs = { product, orderId, email: res.email, ip, origin, billTo: bill.billTo, company: cleanLine(input.company_name, 50) };
  let pay;
  let full;
  try {
    [pay, full] = await Promise.all([
      hostedPaymentToken(env, anet, Object.assign({ display: "embedded" }, tokenArgs)),
      hostedPaymentToken(env, anet, Object.assign({ display: "full" }, tokenArgs)),
    ]);
    if (pay.ok && !full.ok) pay = full;           // surface the refusal below
  } catch (e) {
    pay = { ok: false, codes: ["unreachable"] };
  }
  if (!pay.ok) {
    log({ outcome: "error", reason: "anet-token", codes: pay.codes, product: product.id, order: orderId });
    await sendAlert(env, `start-${(pay.codes || []).join("-") || "unknown"}`,
      "Checkout can't create payment pages",
      [`Authorize.net refused the hosted-payment request (codes: ${(pay.codes || []).join(", ") || "none"}; mode: ${anet.mode}).`,
        "Customers see \"we couldn't start the secure payment\". Check ANET_API_LOGIN_ID / ANET_TRANSACTION_KEY / ANET_ENV in Cloudflare Pages."]);
    return json(502, { ok: false, message: START_FAILED });
  }

  try {
    await putOrder(env, orderId, {
      v: 1, product: product.id, status: "pending", mode: anet.mode, created_at: now, record: res.record,
    }, KV_TTL_PENDING);
  } catch (e) {
    log({ outcome: "error", reason: "kv-put", product: product.id, order: orderId });
    return json(503, { ok: false, message: START_FAILED });
  }

  log({ outcome: "token", product: product.id, order: orderId, mode: anet.mode });
  return json(200, {
    ok: true, order_id: orderId, token: pay.token, full_token: full.token, post_url: anet.hosted,
    return_url: `${origin}${product.pages.thankYou}?order=${encodeURIComponent(orderId)}`,
  });
}

export async function onRequest(context) {
  if (context.request.method === "POST") return onRequestPost(context);
  return json(405, { ok: false, message: "Method not allowed." });
}
