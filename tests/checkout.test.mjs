// Node tests for the self-service checkout Functions (functions/_lib/checkout + functions/api/checkout).
// Run from the repo root: node --test tests/checkout.test.mjs
// (Node 20+, no dependencies; mocks Turnstile, Authorize.net, GitHub, Graph and KV)
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";

const ROOT = new URL("../functions/", import.meta.url).href;
const core = await import(ROOT + "_lib/checkout/core.js");
const { productById, productByOrderId } = await import(ROOT + "_lib/checkout/products.js");
const start = await import(ROOT + "api/checkout/start.js");
const hook = await import(ROOT + "api/checkout/anet-webhook.js");
const status = await import(ROOT + "api/checkout/status.js");
const SCHEMA = (await import(ROOT + "_lib/checkout/schemas/m365-assessment-order-v1.js")).default;

// ---------------------------------------------------------------- mocks
class MemKV {
  constructor() { this.m = new Map(); }
  async get(k, type) { const v = this.m.get(k); if (v == null) return null; return type === "json" ? JSON.parse(v) : v; }
  async put(k, v) { this.m.set(k, v); }
  async delete(k) { this.m.delete(k); }
}

const SIG_KEY = "A1B2C3D4E5F60718293A4B5C6D7E8F90A1B2C3D4E5F60718293A4B5C6D7E8F90A1B2C3D4E5F60718293A4B5C6D7E8F90A1B2C3D4E5F60718293A4B5C6D7E8F90";

function makeEnv(over = {}) {
  return Object.assign({
    ORDERS: new MemKV(), ANET_ENV: "sandbox", ANET_API_LOGIN_ID: "login", ANET_TRANSACTION_KEY: "txkey",
    ANET_SIGNATURE_KEY: SIG_KEY, TURNSTILE_SECRET_KEY: "ts", GITHUB_ORDERS_TOKEN: "ghtoken",
    MS_TENANT_ID: "t", MS_CLIENT_ID: "c", MS_CLIENT_SECRET: "s", SEND_FROM: "info@prolinksystems.com",
  }, over);
}

// Fake upstreams; each test tweaks `world`.
let calls, world;
function resetWorld() {
  calls = [];
  world = {
    turnstileOk: true,
    anetTokenOk: true,
    tx: null,                          // transaction returned by getTransactionDetails
    detailsCodes: null,                // e.g. ["E00040"] to simulate an error
    repoPrivate: true,
    existingIssues: [],
    createStatus: 201,
  };
}
globalThis.fetch = async (url, init = {}) => {
  url = String(url);
  const body = init.body == null ? null : String(init.body);
  calls.push({ url, method: init.method || "GET", body, headers: init.headers || {} });
  const res = (status, obj, raw) => new Response(raw != null ? raw : JSON.stringify(obj), { status });
  if (url.startsWith("https://challenges.cloudflare.com/")) {
    return res(200, world.turnstileOk ? { success: true } : { success: false, "error-codes": ["invalid-input-response"] });
  }
  if (url.includes("authorize.net/xml/v1/request.api")) {
    const req = JSON.parse(body);
    if (req.getHostedPaymentPageRequest) {
      const ok = world.anetTokenOk;
      return res(200, null, "\uFEFF" + JSON.stringify(ok
        ? { token: "TOKEN123", messages: { resultCode: "Ok", message: [{ code: "I00001", text: "Successful." }] } }
        : { messages: { resultCode: "Error", message: [{ code: "E00007", text: "User authentication failed." }] } }));
    }
    if (req.getTransactionDetailsRequest) {
      if (world.detailsCodes) return res(200, null, "\uFEFF" + JSON.stringify({ messages: { resultCode: "Error", message: world.detailsCodes.map((code) => ({ code })) } }));
      return res(200, null, "\uFEFF" + JSON.stringify({ transaction: world.tx, messages: { resultCode: "Ok", message: [{ code: "I00001" }] } }));
    }
  }
  if (url === "https://api.github.com/repos/brianshad-usa/m365-security-agent") return res(200, { private: world.repoPrivate });
  if (url.startsWith("https://api.github.com/repos/brianshad-usa/m365-security-agent/issues?")) return res(200, world.existingIssues);
  if (url === "https://api.github.com/repos/brianshad-usa/m365-security-agent/issues" && init.method === "POST") {
    return world.createStatus === 201 ? res(201, { number: 42 }) : res(world.createStatus, { message: "nope" });
  }
  if (url.startsWith("https://login.microsoftonline.com/")) return res(200, { access_token: "graph" });
  if (url.startsWith("https://graph.microsoft.com/")) return new Response(null, { status: 202 });
  throw new Error("unexpected fetch " + url);
};

const formInput = (over = {}) => Object.assign({
  product: "m365-security-assessment",
  "cf-turnstile-response": "tok",
  company_name: "Northwind Dental Group",
  company_domain: "https://www.NorthwindDental.com/",
  employees: "26-50",
  contact_name: "Dana Rivera", contact_title: "Office Manager", contact_email: "dana@NorthwindDental.com", contact_phone: "+1 818 555 0101",
  tech_name: "Sam Lee", tech_email: "it@northwinddental.com",
  pre_call: false, notes: "",
  auth_accepted: true, auth_name: "Dana Rivera", auth_title: "Office Manager",
  source: { page: "/m365-security-assessment?utm_source=google", utm_source: "google", utm_medium: "cpc", gclid: "abc" },
}, over);

const startReq = (input, ip = "203.0.113.7") => new Request("https://prolinksystems.com/api/checkout/start", {
  method: "POST", headers: { "Content-Type": "application/json", "CF-Connecting-IP": ip }, body: JSON.stringify(input),
});

function webhookReq(payload, { key = SIG_KEY, hexKey = false, sig } = {}) {
  const raw = JSON.stringify(payload);
  const k = hexKey ? Buffer.from(key, "hex") : Buffer.from(key, "utf8");
  const mac = sig || "sha512=" + createHmac("sha512", k).update(raw).digest("hex").toUpperCase();
  return new Request("https://prolinksystems.com/api/checkout/anet-webhook", {
    method: "POST", headers: { "Content-Type": "application/json", "X-ANET-Signature": mac }, body: raw,
  });
}
const evt = (transId, eventType = "net.authorize.payment.authcapture.created") => ({ notificationId: "n1", eventType, eventDate: "2026-11-19T20:16:00Z", webhookId: "w1",
  payload: { responseCode: 1, authCode: "ABC", avsResponse: "Y", authAmount: 2500.0, entityName: "transaction", id: transId } });
const mails = () => calls.filter((c) => c.url.includes("/sendMail")).map((c) => JSON.parse(c.body).message);
const issuePosts = () => calls.filter((c) => c.method === "POST" && c.url.endsWith("/issues"));

async function placeOrder(env, input) {
  const r = await start.onRequestPost({ request: startReq(input || formInput()), env });
  return { status: r.status, body: await r.json() };
}

// ---------------------------------------------------------------- unit tests
test("spec example order validates; unknown / malformed fields fail", () => {
  const example = {
    schema: "prolink.m365-assessment-order/v1", order_id: "M365-261119-A7K2", placed_at: "2026-11-19T20:15:00Z", product: "m365-security-assessment",
    company: { name: "Northwind Dental Group", domain: "northwinddental.com", employees: "26-50", phone: "+1 818 555 0100" },
    contact: { name: "Dana Rivera", title: "Office Manager", email: "dana@northwinddental.com", phone: "+1 818 555 0101" },
    technical_contact: { name: "Sam Lee", email: "it@northwinddental.com" }, access_method: "prolink_app",
    payment: { processor: "authorize.net", transaction_id: "60212345678", amount: "2500.00", currency: "USD", status: "captured", verified_at: "2026-11-19T20:16:02Z", card_last4: "4242" },
    authorization: { accepted: true, terms_version: "2026-11", accepted_at: "2026-11-19T20:14:00Z", signer_name: "Dana Rivera", signer_title: "Office Manager", ip: "203.0.113.7" },
    pre_call_requested: false, notes: "", source: { page: "/m365-security-assessment", utm_source: "google", gclid: "..." },
  };
  assert.deepEqual(core.validate(SCHEMA, example), []);
  assert.ok(core.validate(SCHEMA, { ...example, extra: 1 }).some((e) => e.includes("unknown field")));
  assert.ok(core.validate(SCHEMA, { ...example, order_id: "M365-2611-A7K2" }).some((e) => e.includes("order_id")));
  assert.ok(core.validate(SCHEMA, { ...example, payment: { ...example.payment, status: "authorized" } }).length > 0);
  const { contact, ...noContact } = example;
  assert.ok(core.validate(SCHEMA, noContact).some((e) => e.includes("contact: required")));
  assert.ok(core.validate(SCHEMA, { ...example, placed_at: "yesterday" }).some((e) => e.includes("date-time")));
});

test("order ids: PREFIX-YYMMDD-XXXX, UTC date, random tail", () => {
  const id = core.newOrderId("M365", new Date("2026-11-19T23:59:00Z"));
  assert.match(id, /^M365-261119-[A-Z0-9]{4}$/);
  const set = new Set(Array.from({ length: 2000 }, () => core.newOrderId("M365")));
  assert.ok(set.size > 1990);
  assert.equal(productByOrderId(id).id, "m365-security-assessment");
  assert.equal(productByOrderId("INV-2026-0001"), null);
  assert.equal(productById("nope"), null);
  assert.equal(productById("__proto__"), null);
});

test("domain + email normalization", () => {
  assert.equal(core.normDomain("https://www.Acme.com/about"), "acme.com");
  assert.equal(core.normDomain("dana@acme.co.uk"), "acme.co.uk");
  assert.equal(core.normDomain(" acme.com. "), "acme.com");
  assert.equal(core.normEmail(" Dana@ACME.com "), "Dana@acme.com");
});

// ---------------------------------------------------------------- start
test("start: happy path (sandbox) stores a pending order and returns a hosted token", async () => {
  resetWorld();
  const env = makeEnv();
  const { status: s, body } = await placeOrder(env);
  assert.equal(s, 200, JSON.stringify(body));
  assert.equal(body.ok, true);
  assert.match(body.order_id, /^M365-\d{6}-[A-Z0-9]{4}$/);
  assert.equal(body.token, "TOKEN123");
  assert.equal(body.post_url, "https://test.authorize.net/payment/payment");

  const anetCall = calls.find((c) => c.url.includes("request.api"));
  assert.equal(anetCall.url, "https://apitest.authorize.net/xml/v1/request.api");
  const req = JSON.parse(anetCall.body).getHostedPaymentPageRequest;
  assert.deepEqual(Object.keys(req), ["merchantAuthentication", "refId", "transactionRequest", "hostedPaymentSettings"]);
  assert.deepEqual(Object.keys(req.transactionRequest), ["transactionType", "amount", "order", "customer", "customerIP"]);
  assert.equal(req.transactionRequest.amount, "2500.00");
  assert.equal(req.transactionRequest.order.invoiceNumber, body.order_id);
  assert.ok(body.order_id.length <= 20);
  assert.equal(req.transactionRequest.customer.email, "dana@northwinddental.com");
  const settings = Object.fromEntries(req.hostedPaymentSettings.setting.map((x) => [x.settingName, JSON.parse(x.settingValue)]));
  assert.equal(settings.hostedPaymentReturnOptions.url, `https://prolinksystems.com/m365-security-assessment/thank-you?order=${body.order_id}`);
  assert.equal(settings.hostedPaymentReturnOptions.cancelUrl, "https://prolinksystems.com/m365-security-assessment/order?cancelled=1");
  assert.equal(settings.hostedPaymentButtonOptions.text, "Pay $2,500.00");
  assert.equal(settings.hostedPaymentSecurityOptions.captcha, true);
  assert.equal(settings.hostedPaymentIFrameCommunicatorUrl.url, "https://prolinksystems.com/assets/apps/anet-communicator");
  assert.equal(body.return_url, `https://prolinksystems.com/m365-security-assessment/thank-you?order=${body.order_id}`);

  const rec = await env.ORDERS.get(`order:${body.order_id}`, "json");
  assert.equal(rec.status, "pending");
  assert.equal(rec.mode, "sandbox");
  assert.equal(rec.record.company.domain, "northwinddental.com");
  assert.equal(rec.record.contact.email, "dana@northwinddental.com");
  assert.equal(rec.record.authorization.ip, "203.0.113.7");
  assert.equal(rec.record.authorization.terms_version, "2026-11");
  assert.deepEqual(rec.record.source, { page: "/m365-security-assessment", utm_source: "google", utm_medium: "cpc", gclid: "abc" });
});

test("start: production mode uses the live endpoints", async () => {
  resetWorld();
  const env = makeEnv({ ANET_ENV: "production" });
  const { body } = await placeOrder(env);
  assert.equal(body.post_url, "https://accept.authorize.net/payment/payment");
  assert.ok(calls.some((c) => c.url === "https://api.authorize.net/xml/v1/request.api"));
});

test("start: rejects failed Turnstile before touching Authorize.net", async () => {
  resetWorld(); world.turnstileOk = false;
  const { status: s, body } = await placeOrder(makeEnv());
  assert.equal(s, 400); assert.equal(body.field, "turnstile");
  assert.ok(!calls.some((c) => c.url.includes("authorize.net")));
});

test("start: field validation", async () => {
  for (const [over, field] of [
    [{ company_domain: "not a domain" }, "company_domain"],
    [{ company_name: "x" }, "company_name"],
    [{ contact_email: "dana@" }, "contact_email"],
    [{ tech_email: "" }, "tech_email"],
    [{ tech_name: "", tech_email: "it@acme.com" }, "tech_name"],
    [{ auth_accepted: "true" }, "auth_accepted"],
    [{ auth_name: " " }, "auth_name"],
    [{ employees: "12" }, "employees"],
    [{ notes: "x".repeat(1001) }, "notes"],
  ]) {
    resetWorld();
    const { status: s, body } = await placeOrder(makeEnv(), formInput(over));
    assert.equal(s, 400, JSON.stringify(over));
    assert.equal(body.field, field, JSON.stringify(over));
    assert.ok(!calls.some((c) => c.url.includes("authorize.net")));
  }
  resetWorld();   // both admin fields blank is fine
  const ok = await placeOrder(makeEnv(), formInput({ tech_name: "", tech_email: "" }));
  assert.equal(ok.status, 200);
});

test("start: unknown product, honeypot, misconfiguration", async () => {
  resetWorld();
  assert.equal((await placeOrder(makeEnv(), formInput({ product: "other" }))).status, 400);
  assert.equal((await placeOrder(makeEnv(), formInput({ botcheck: "x" }))).status, 400);
  assert.equal((await placeOrder(makeEnv({ ANET_ENV: "live" }))).status, 503);
  assert.equal((await placeOrder(makeEnv({ ORDERS: undefined }))).status, 503);
});

test("start: Authorize.net refusal -> 502 and ONE alert per 6 hours", async () => {
  resetWorld(); world.anetTokenOk = false;
  const env = makeEnv();
  const a = await placeOrder(env);
  assert.equal(a.status, 502);
  assert.equal(calls.filter((c) => c.url.startsWith("https://graph.microsoft.com/")).length, 1);
  const b = await placeOrder(env);
  assert.equal(b.status, 502);
  assert.equal(calls.filter((c) => c.url.startsWith("https://graph.microsoft.com/")).length, 1, "deduped");
  assert.equal([...env.ORDERS.m.keys()].filter((k) => k.startsWith("order:")).length, 0, "no pending order stored");
});

// ---------------------------------------------------------------- webhook
async function paidScenario(envOver = {}, txOver = {}, inputOver = {}) {
  resetWorld();
  const env = makeEnv(envOver);
  const { body } = await placeOrder(env, formInput(inputOver));
  world.tx = Object.assign({
    transId: "60212345678", responseCode: 1, authAmount: 2500.0, settleAmount: 2500.0, transactionStatus: "capturedPendingSettlement",
    order: { invoiceNumber: body.order_id, description: "Microsoft 365 Security Assessment" },
    payment: { creditCard: { cardNumber: "XXXX4242", expirationDate: "XXXX", cardType: "Visa" } },
  }, txOver);
  calls = [];
  return { env, orderId: body.order_id };
}

function issueBodyOrder(call) {
  const { title, body } = JSON.parse(call.body);
  const m = /^Paid order from prolinksystems\.com\n\n<!-- prolink-order:v1 -->\n```json\n([\s\S]*)\n```\n$/.exec(body);
  assert.ok(m, "body format: " + body.slice(0, 120));
  return { title, order: JSON.parse(m[1]), body };
}

test("webhook: rejects a bad signature without calling anything", async () => {
  const { env } = await paidScenario();
  const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678"), { sig: "sha512=" + "0".repeat(128) }), env });
  assert.equal(r.status, 401);
  assert.equal(calls.length, 0);
  const r2 = await hook.onRequestPost({ request: webhookReq(evt("60212345678"), { key: "wrong-key" }), env });
  assert.equal(r2.status, 401);
});

test("webhook: verified payment -> one schema-valid [order] issue, order marked paid", async () => {
  const { env, orderId } = await paidScenario();
  const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
  assert.equal(r.status, 200, await r.clone().text());
  const posts = calls.filter((c) => c.method === "POST" && c.url.endsWith("/issues"));
  assert.equal(posts.length, 1);
  assert.equal(posts[0].headers.Authorization, "Bearer ghtoken");
  const { title, order } = issueBodyOrder(posts[0]);
  assert.equal(title, `[order] ${orderId} Northwind Dental Group`);
  assert.deepEqual(core.validate(SCHEMA, order), []);
  assert.equal(order.order_id, orderId);
  assert.equal(order.test, true, "sandbox => test:true");
  assert.equal(order.payment.transaction_id, "60212345678");
  assert.equal(order.payment.amount, "2500.00");
  assert.equal(order.payment.card_last4, "4242");
  assert.equal(order.access_method, "prolink_app");
  assert.deepEqual(order.technical_contact, { name: "Sam Lee", email: "it@northwinddental.com" });
  assert.deepEqual(Object.keys(order), ["schema", "order_id", "placed_at", "product", "company", "contact", "technical_contact",
    "access_method", "payment", "authorization", "test", "pre_call_requested", "notes", "source"]);
  const rec = await env.ORDERS.get(`order:${orderId}`, "json");
  assert.equal(rec.status, "paid");
  assert.equal(rec.handoff, "brianshad-usa/m365-security-agent#42");
  assert.equal(await env.ORDERS.get(`lock:${orderId}`), null, "lock released");

  // Retry of the same notification: idempotent, no second issue.
  calls = [];
  const again = await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
  assert.equal(again.status, 200);
  assert.equal((await again.json()).duplicate, true);
  assert.ok(!calls.some((c) => c.url.includes("github.com")));
});

test("webhook: production orders carry no test flag", async () => {
  const { env } = await paidScenario({ ANET_ENV: "production" });
  const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
  assert.equal(r.status, 200);
  const { order } = issueBodyOrder(calls.find((c) => c.method === "POST" && c.url.endsWith("/issues")));
  assert.equal("test" in order, false);
});

test("webhook: hex-decoded Signature Key variant is accepted too", async () => {
  const { env } = await paidScenario();
  const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678"), { hexKey: true }), env });
  assert.equal(r.status, 200);
});

test("webhook: transactions that aren't website orders are ignored", async () => {
  const { env } = await paidScenario({}, { order: { invoiceNumber: "INV-10443" } });
  const r = await hook.onRequestPost({ request: webhookReq(evt("60299999999")), env });
  assert.equal(r.status, 200);
  assert.equal((await r.json()).ignored, "not-a-website-order");
  assert.ok(!calls.some((c) => c.url.includes("github.com")));
});

test("webhook: Authorize.net 'record not found' (Test webhook button) -> 200 ignore", async () => {
  const { env } = await paidScenario();
  world.detailsCodes = ["E00040"];
  const r = await hook.onRequestPost({ request: webhookReq(evt("1")), env });
  assert.equal(r.status, 200);
  assert.equal((await r.json()).ignored, "transaction-not-found");
});

test("paymentState: Authorize.net statuses -> paid / held / declined / error / unexpected", () => {
  const ps = core.paymentState;
  assert.equal(ps({ responseCode: 1, transactionStatus: "capturedPendingSettlement" }), "paid");
  assert.equal(ps({ responseCode: 1, transactionStatus: "settledSuccessfully" }), "paid");
  assert.equal(ps({ responseCode: 4, transactionStatus: "capturedPendingSettlement" }), "paid", "approved after review");
  assert.equal(ps({ responseCode: 4, transactionStatus: "FDSPendingReview" }), "held");
  assert.equal(ps({ responseCode: 4, transactionStatus: "FDSAuthorizedPendingReview" }), "held");
  assert.equal(ps({ responseCode: 2, transactionStatus: "declined" }), "declined");
  assert.equal(ps({ responseCode: 3, transactionStatus: "generalError" }), "error");
  assert.equal(ps({ responseCode: 1, transactionStatus: "voided" }), "unexpected");
  assert.equal(ps({ responseCode: 1 }), "paid");
  assert.equal(ps({}), "unexpected");
});

test("webhook: wrong amount or unexpected status -> no hand-off, 'needs a look' alert", async () => {
  for (const txOver of [{ authAmount: 25.0 }, { transactionStatus: "voided" }]) {
    const { env, orderId } = await paidScenario({}, txOver);
    const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
    assert.equal(r.status, 200);
    assert.equal(issuePosts().length, 0);
    assert.ok(mails().some((m) => m.subject.includes("needs a look")), JSON.stringify(txOver));
    assert.equal((await env.ORDERS.get(`order:${orderId}`, "json")).status, "pending");
  }
});

test("webhook: declined card -> plain 'card declined' note naming the customer, no hand-off", async () => {
  const { env, orderId } = await paidScenario({}, { responseCode: 2, transactionStatus: "declined", responseReasonDescription: "This transaction has been declined." });
  const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
  assert.equal(r.status, 200);
  assert.equal((await r.json()).ignored, "declined");
  assert.equal(issuePosts().length, 0);
  const m = mails();
  assert.equal(m.length, 1);
  assert.match(m[0].subject, new RegExp(`Card declined for order ${orderId} \\(test\\)`));
  assert.ok(!m[0].subject.includes("needs a look"));
  assert.ok(m[0].body.content.includes("dana@northwinddental.com"), "contact included for follow-up");
  assert.equal((await env.ORDERS.get(`order:${orderId}`, "json")).status, "pending");
});

test("webhook: processing error (e.g. duplicate submission) -> logged only", async () => {
  const { env } = await paidScenario({}, { responseCode: 3, transactionStatus: "generalError" });
  const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
  assert.equal(r.status, 200);
  assert.equal((await r.json()).ignored, "payment-error");
  assert.equal(mails().length, 0);
  assert.equal(issuePosts().length, 0);
});

test("webhook: held for review -> alert; once approved (fraud.approved) the order is handed off", async () => {
  const { env, orderId } = await paidScenario({}, { responseCode: 4, transactionStatus: "FDSPendingReview" });
  const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
  assert.equal(r.status, 200);
  assert.equal((await r.json()).ignored, "held");
  assert.ok(mails().some((m) => m.subject.includes("held for review")));
  assert.equal(issuePosts().length, 0);
  assert.equal((await env.ORDERS.get(`order:${orderId}`, "json")).status, "pending");

  world.tx = Object.assign({}, world.tx, { transactionStatus: "capturedPendingSettlement" });   // Pro Link approved it
  calls = [];
  const r2 = await hook.onRequestPost({ request: webhookReq(evt("60212345678", "net.authorize.payment.fraud.approved")), env });
  assert.equal(r2.status, 200, await r2.clone().text());
  assert.equal(issuePosts().length, 1);
  assert.equal((await env.ORDERS.get(`order:${orderId}`, "json")).status, "paid");
});

test("webhook: a second, different payment for a paid order -> refund alert, no second issue", async () => {
  const { env } = await paidScenario();
  assert.equal((await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env })).status, 200);
  world.tx = Object.assign({}, world.tx, { transId: "60299990000" });
  calls = [];
  const r = await hook.onRequestPost({ request: webhookReq(evt("60299990000")), env });
  assert.equal(r.status, 200);
  assert.equal((await r.json()).ignored, "second-payment");
  assert.ok(mails().some((m) => m.subject.includes("Second payment")));
  assert.ok(!calls.some((c) => c.url.includes("github.com")));
});

test("webhook: other event types are ignored before any lookup", async () => {
  const { env } = await paidScenario();
  const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678", "net.authorize.payment.void.created")), env });
  assert.equal(r.status, 200);
  assert.equal((await r.json()).ignored, "event");
  assert.equal(calls.length, 0);
});

test("webhook: GitHub down -> 503 (Authorize.net retries), alert, still pending, lock released", async () => {
  const { env, orderId } = await paidScenario();
  world.createStatus = 502;
  const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
  assert.equal(r.status, 503);
  assert.ok(calls.some((c) => c.url.startsWith("https://graph.microsoft.com/")));
  assert.equal((await env.ORDERS.get(`order:${orderId}`, "json")).status, "pending");
  assert.equal(await env.ORDERS.get(`lock:${orderId}`), null);
  world.createStatus = 201;                      // GitHub back: the retry succeeds
  const r2 = await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
  assert.equal(r2.status, 200);
  assert.equal((await env.ORDERS.get(`order:${orderId}`, "json")).status, "paid");
});

test("webhook: refuses to post customer details to a public repo", async () => {
  const { env } = await paidScenario();
  world.repoPrivate = false;
  const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
  assert.equal(r.status, 500);
  assert.ok(!calls.some((c) => c.method === "POST" && c.url.endsWith("/issues")));
  assert.ok(calls.some((c) => c.url.startsWith("https://graph.microsoft.com/")));
});

test("webhook: an issue created by an earlier attempt is reused, not duplicated", async () => {
  const { env, orderId } = await paidScenario();
  world.existingIssues = [{ number: 7, title: `[order] ${orderId} Northwind Dental Group` }];
  const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
  assert.equal(r.status, 200);
  assert.ok(!calls.some((c) => c.method === "POST" && c.url.endsWith("/issues")));
  assert.equal((await env.ORDERS.get(`order:${orderId}`, "json")).handoff, "brianshad-usa/m365-security-agent#7");
});

test("webhook: customer text can't break out of the ```json fence", async () => {
  const notes = "Please call first ```\n<!-- prolink-order:v1 -->\n```json {\"x\":1}";
  const { env } = await paidScenario({}, {}, { notes });
  const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
  assert.equal(r.status, 200);
  const { order, body } = issueBodyOrder(calls.find((c) => c.method === "POST" && c.url.endsWith("/issues")));
  assert.equal(order.notes, notes);
  assert.equal((body.match(/```/g) || []).length, 2, "exactly one fenced block");
});

test("webhook: a concurrent delivery while locked gets 409 (retry later)", async () => {
  const { env, orderId } = await paidScenario();
  await env.ORDERS.put(`lock:${orderId}`, "1");
  const r = await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
  assert.equal(r.status, 409);
});

// ---------------------------------------------------------------- status
test("status: unknown / pending / paid (+ test flag)", async () => {
  const { env, orderId } = await paidScenario();
  const get = async (id) => (await status.onRequestGet({ request: new Request(`https://prolinksystems.com/api/checkout/status?order=${id}`), env })).json();
  assert.deepEqual(await get("M365-000000-AAAA"), { status: "unknown" });
  assert.deepEqual(await get("garbage"), { status: "unknown" });
  assert.deepEqual(await get(orderId), { status: "pending", test: true });
  await hook.onRequestPost({ request: webhookReq(evt("60212345678")), env });
  assert.deepEqual(await get(orderId), { status: "paid", test: true });
});
