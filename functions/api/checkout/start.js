/**
 * POST /api/checkout/start  --  Cloudflare Pages Function (all self-service apps)
 * -----------------------------------------------------------------------------
 * Body: the app's order form as JSON, plus { product: "<slug>", "cf-turnstile-response",
 * source: {page, utm_*, gclid} }. Verifies Turnstile (strict), validates the form with the
 * app's intake(), stores the pending order in KV (7 days), and returns an Authorize.net
 * Accept Hosted token: { ok, order_id, token, post_url }. The browser then posts the token
 * to Authorize.net's hosted payment page; card data never touches this site.
 * Setup and secrets: functions/_lib/checkout/core.js header.
 */
import {
  json, log, nowIso, newOrderId, clientIp, verifyTurnstile, anetConfig, billingFromInput, cleanLine,
  hostedPaymentToken, getOrder, putOrder, sendAlert, KV_TTL_PENDING, UNAVAILABLE,
} from "../../_lib/checkout/core.js";
import { productById } from "../../_lib/checkout/products.js";

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
  if (!anet || !env.ANET_API_LOGIN_ID || !env.ANET_TRANSACTION_KEY || !env.ORDERS || !env.TURNSTILE_SECRET_KEY) {
    log({ outcome: "unavailable", reason: "not-configured", product: product.id });
    return json(503, { ok: false, message: UNAVAILABLE });
  }

  const ts = await verifyTurnstile(env.TURNSTILE_SECRET_KEY, input["cf-turnstile-response"]);
  if (!ts.ok) {
    log({ outcome: "rejected", reason: "turnstile", codes: ts.codes, product: product.id });
    return json(400, { ok: false, field: "turnstile", message: "Please complete the security check again, then continue." });
  }

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
    return json(502, { ok: false, message: "We couldn't start the secure payment. Please try again, or call 1-800-890-6133." });
  }

  try {
    await putOrder(env, orderId, {
      v: 1, product: product.id, status: "pending", mode: anet.mode, created_at: now, record: res.record,
    }, KV_TTL_PENDING);
  } catch (e) {
    log({ outcome: "error", reason: "kv-put", product: product.id, order: orderId });
    return json(503, { ok: false, message: "We couldn't start the secure payment. Please try again, or call 1-800-890-6133." });
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
