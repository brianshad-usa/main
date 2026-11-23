/**
 * POST /api/checkout/anet-webhook  --  Authorize.net webhook (all self-service apps)
 * -----------------------------------------------------------------------------
 * Subscribe ONE webhook in the Authorize.net Merchant Interface, URL
 * https://prolinksystems.com/api/checkout/anet-webhook, to TWO events:
 *   net.authorize.payment.authcapture.created  every card payment (approved, declined or held)
 *   net.authorize.payment.fraud.approved       Pro Link approved a payment the Fraud Detection
 *                                              Suite had held for review
 * They fire for EVERY transaction on the account (including payments that have nothing to do
 * with the website), so only transactions whose invoice number is a pending self-service order
 * are acted on.
 *
 * 1. X-ANET-Signature must match HMAC-SHA512(Signature Key, raw body)        -> else 401
 * 2. getTransactionDetails(transId); invoiceNumber must be a pending order in KV. Then, by the
 *    transaction's CURRENT status (core.paymentState):
 *      paid, the app's exact amount -> step 3
 *      held for review              -> 200 + email Pro Link to approve or decline it (approving
 *                                      sends fraud.approved, which arrives here as "paid")
 *      declined                     -> 200 + a plain "card declined" note (who tried, for follow-up)
 *      processing error             -> 200, log only (the customer saw the error on the form)
 *      anything else / wrong amount -> 200 + "needs a look" email
 * 3. Idempotent: an order already marked paid -> 200 (a SECOND, different payment for it emails
 *    Pro Link to refund one); a short KV lock keeps Authorize.net's parallel retries from
 *    handing off twice
 * 4. Build the app's order, validate it against the app's schema, run its hand-off
 *    (GitHub issue for the M365 assessment), mark the order paid               -> 200
 * Transient hand-off failures answer 503 so Authorize.net retries (3 x 3 min, 3 x 8 h,
 * 4 x 48 h; after 10 failures it disables the webhook) and Pro Link gets an email.
 * Permanent problems answer 200 (retrying can't help) and email Pro Link.
 */
import {
  json, log, nowIso, anetConfig, transactionDetails, verifyAnetSignature, validate, paymentState,
  getOrder, putOrder, sendAlert, kvReady, KV_TTL_PAID,
} from "../../_lib/checkout/core.js";
import { productByOrderId } from "../../_lib/checkout/products.js";
import { githubIssueHandoff } from "../../_lib/checkout/github.js";

const HANDOFFS = { "github-issue": githubIssueHandoff };
const EVENTS = new Set(["net.authorize.payment.authcapture.created", "net.authorize.payment.fraud.approved"]);

/** Who placed the order, for Pro Link's own emails (never logged). */
function orderWho(rec) {
  const r = (rec && rec.record) || {};
  const c = r.company || {};
  const p = r.contact || {};
  const out = [];
  if (c.name || c.domain) out.push(`Company: ${[c.name, c.domain].filter(Boolean).join(", ")}`);
  if (p.name || p.email || p.phone) out.push(`Contact: ${[p.name, p.email, p.phone].filter(Boolean).join(", ")}`);
  return out;
}

export async function onRequestPost({ request, env }) {
  const raw = new Uint8Array(await request.arrayBuffer());

  if (!env.ANET_SIGNATURE_KEY) {
    log({ outcome: "error", reason: "no-signature-key" });
    return json(500, { ok: false });
  }
  if (!(await verifyAnetSignature(env.ANET_SIGNATURE_KEY, raw, request.headers.get("X-ANET-Signature")))) {
    log({ outcome: "rejected", reason: "bad-signature" });
    return json(401, { ok: false });
  }

  let evt;
  try {
    evt = JSON.parse(new TextDecoder().decode(raw));
  } catch (e) {
    return json(400, { ok: false });
  }
  if (!EVENTS.has(evt.eventType)) {
    return json(200, { ok: true, ignored: "event" });
  }
  const transId = String((evt.payload && evt.payload.id) || "");
  if (!/^[0-9]{1,20}$/.test(transId)) return json(200, { ok: true, ignored: "no-transaction-id" });

  const anet = anetConfig(env);
  if (!anet || !env.ANET_API_LOGIN_ID || !env.ANET_TRANSACTION_KEY || !kvReady(env)) {
    log({ outcome: "error", reason: "not-configured", trans: transId });
    await sendAlert(env, "webhook-not-configured", "Payment webhook is not configured",
      [`A payment notification arrived (transaction ${transId}) but ANET_ENV / ANET_API_LOGIN_ID / ANET_TRANSACTION_KEY or the ORDERS KV binding is missing in Cloudflare Pages (ORDERS must be a KV namespace binding, not a variable).`]);
    return json(500, { ok: false });
  }

  // 1) Ask Authorize.net what actually happened; never trust the notification body alone.
  let det;
  try {
    det = await transactionDetails(env, anet, transId);
  } catch (e) {
    log({ outcome: "retry", reason: "anet-unreachable", trans: transId });
    return json(503, { ok: false });
  }
  if (!det.ok) {
    if (det.codes.includes("E00040")) {           // record not found (e.g. the "Test webhook" button)
      log({ outcome: "ignored", reason: "transaction-not-found", trans: transId });
      return json(200, { ok: true, ignored: "transaction-not-found" });
    }
    log({ outcome: "error", reason: "anet-details", codes: det.codes, trans: transId });
    await sendAlert(env, `webhook-details-${det.codes.join("-") || "unknown"}`, "Can't verify payments with Authorize.net",
      [`getTransactionDetails failed for transaction ${transId} (codes: ${det.codes.join(", ") || "none"}; mode: ${anet.mode}).`,
        "Check ANET_API_LOGIN_ID / ANET_TRANSACTION_KEY / ANET_ENV in Cloudflare Pages. If the Authorize.net account shows a \"Transaction Details API\" setting (Account > Settings), it must be enabled; newer accounts have it on with no setting. Paid orders wait until this is fixed; Authorize.net keeps retrying."]);
    return json(500, { ok: false });
  }

  const tx = det.data.transaction || {};
  const invoice = String((tx.order && tx.order.invoiceNumber) || "");
  const product = productByOrderId(invoice);
  if (!product) return json(200, { ok: true, ignored: "not-a-website-order" });

  const rec = await getOrder(env, invoice);
  if (!rec || rec.product !== product.id) {
    log({ outcome: "error", reason: "order-not-found", order: invoice, trans: transId });
    await sendAlert(env, `webhook-missing-${invoice}`, `Paid order ${invoice} not found`,
      [`Authorize.net transaction ${transId} carries invoice ${invoice}, but no pending order with that number exists (expired after 7 days, or never stored).`,
        "Look the payment up in Authorize.net and contact the customer; the order was NOT handed off."]);
    return json(200, { ok: true, ignored: "order-not-found" });
  }

  const state = paymentState(tx);
  const who = orderWho(rec);
  const test = rec.mode === "sandbox" ? " (test)" : "";

  if (rec.status === "paid") {
    if (state === "paid" && rec.transaction_id && String(rec.transaction_id) !== transId) {
      log({ outcome: "error", reason: "second-payment", order: invoice, trans: transId, first: rec.transaction_id });
      await sendAlert(env, `second-payment-${transId}`, `Second payment for order ${invoice}${test}`,
        [`Order ${invoice} was already paid (transaction ${rec.transaction_id}), and another payment for it just went through (transaction ${transId}, ${tx.authAmount}).`,
          "The order was handed off once. Refund one of the two payments in Authorize.net.", ...who]);
      return json(200, { ok: true, ignored: "second-payment" });
    }
    return json(200, { ok: true, duplicate: true });
  }

  if (state === "declined") {
    log({ outcome: "declined", product: product.id, order: invoice, trans: transId });
    const why = tx.responseReasonDescription ? ` (Authorize.net: ${String(tx.responseReasonDescription).slice(0, 160)})` : "";
    await sendAlert(env, `declined-${invoice}`, `Card declined for order ${invoice}${test}`,
      [`Someone tried to pay for the ${product.name} and the card was declined${why}.`,
        "Nothing is broken and the order stays unpaid. They can try again with another card, or you may want to reach out:", ...who]);
    return json(200, { ok: true, ignored: "declined" });
  }
  if (state === "held") {
    log({ outcome: "held", product: product.id, order: invoice, trans: transId });
    await sendAlert(env, `held-${invoice}`, `Payment held for review: order ${invoice}${test}`,
      [`Authorize.net's Fraud Detection Suite held transaction ${transId} (${tx.authAmount}) for review, so the order has NOT moved on yet.`,
        "Approve or decline it in Authorize.net under Suspicious Transactions (new design: Payments > Manage Transactions > Suspicious Transactions; classic view: Tools > Fraud Detection Suite).",
        "Once you approve it, the order continues automatically (the webhook must include the \"Fraud approved\" event). If you decline it, the customer isn't charged.", ...who]);
    return json(200, { ok: true, ignored: "held" });
  }
  if (state === "error") {
    log({ outcome: "ignored", reason: "payment-error", order: invoice, trans: transId, code: tx.responseCode });
    return json(200, { ok: true, ignored: "payment-error" });
  }

  const amount = Number(tx.authAmount);
  if (state !== "paid" || !Number.isFinite(amount) || amount.toFixed(2) !== product.amount) {
    log({ outcome: "error", reason: "payment-mismatch", order: invoice, trans: transId, code: tx.responseCode, status: tx.transactionStatus, amount: tx.authAmount });
    await sendAlert(env, `webhook-mismatch-${invoice}`, `Payment for ${invoice} needs a look`,
      [`Transaction ${transId}: status ${tx.transactionStatus || "?"}, response code ${tx.responseCode}, amount ${tx.authAmount} (expected captured, ${product.amount}).`,
        "The order was NOT handed off. Check the transaction in Authorize.net.", ...who]);
    return json(200, { ok: true, ignored: "payment-mismatch" });
  }

  // 2) One hand-off at a time per order (Authorize.net may deliver retries in parallel).
  const lockKey = `lock:${invoice}`;
  if (await env.ORDERS.get(lockKey)) return json(409, { ok: false, retry: true });
  await env.ORDERS.put(lockKey, "1", { expirationTtl: 120 });

  try {
    const card = String((tx.payment && tx.payment.creditCard && tx.payment.creditCard.cardNumber) || "");
    const last4 = (/([0-9]{4})$/.exec(card) || [])[1];
    const verifiedAt = nowIso();
    const order = product.buildOrder(rec.record,
      { transactionId: transId, amount: product.amount, verifiedAt, last4 },
      { orderId: invoice, placedAt: rec.created_at, sandbox: anet.sandbox || rec.mode === "sandbox" });

    const errors = validate(product.schema, order);
    if (errors.length) {
      log({ outcome: "error", reason: "schema", order: invoice, errors: errors.slice(0, 10) });
      await sendAlert(env, `webhook-schema-${invoice}`, `Paid order ${invoice} failed validation`,
        [`The order built after payment (transaction ${transId}) does not match the agent's schema: ${errors.slice(0, 5).join("; ")}.`,
          "It was NOT handed off. This is a website bug; the payment is captured."]);
      return json(200, { ok: false, error: "schema" });
    }

    const run = HANDOFFS[product.handoff.type];
    const h = run ? await run(env, product.handoff, order) : { ok: false, transient: false, reason: "unknown hand-off type" };
    if (!h.ok) {
      log({ outcome: h.transient ? "retry" : "error", reason: "handoff", detail: h.reason, order: invoice });
      await sendAlert(env, `webhook-handoff-${invoice}`, `Paid order ${invoice} is waiting`,
        [`Payment verified (transaction ${transId}), but the hand-off failed: ${h.reason}.`,
          h.transient ? "Authorize.net will retry automatically." : "Fix the configuration; Authorize.net keeps retrying for about 9 days."]);
      return json(h.transient ? 503 : 500, { ok: false });
    }

    try {
      await putOrder(env, invoice, Object.assign({}, rec, {
        status: "paid", paid_at: verifiedAt, transaction_id: transId, handoff: h.ref,
      }), KV_TTL_PAID);
    } catch (e) {
      // The hand-off happened; don't make Authorize.net retry (the duplicate check would catch it anyway).
      log({ outcome: "warn", reason: "kv-mark-paid-failed", order: invoice });
    }
    log({ outcome: "paid", product: product.id, order: invoice, trans: transId, handoff: h.ref, existing: !!h.existing, mode: anet.mode, event: evt.eventType });
    return json(200, { ok: true });
  } finally {
    try { await env.ORDERS.delete(lockKey); } catch (e) { /* expires in 2 min anyway */ }
  }
}

export async function onRequest(context) {
  if (context.request.method === "POST") return onRequestPost(context);
  return json(405, { ok: false });
}
