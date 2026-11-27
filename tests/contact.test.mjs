// Node tests for the lead-form Function (functions/api/contact.js).
// Run from the repo root: node --test tests/contact.test.mjs
// (Node 20+, no dependencies; mocks Turnstile siteverify, Microsoft Graph and the Cache API.)
// Added 2026-11-26 (Phase G security closeout): Turnstile hostname + action checks, per-IP rate limits,
// once-per-token processing and the visitor-confirmation gates -- and proof that real submissions still work.
import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";

// ---------------------------------------------------------------- clock + Cache API mocks
const realNow = Date.now;
let clockOffset = 0;                               // seconds; tests move time forward
Date.now = () => realNow() + clockOffset * 1000;

class MemCache {
  constructor() { this.m = new Map(); this.fail = false; }
  async match(url) {
    if (this.fail) throw new Error("cache down");
    const e = this.m.get(String(url));
    if (!e || e.exp <= Date.now()) return undefined;
    return new Response(e.body);
  }
  async put(url, res) {
    if (this.fail) throw new Error("cache down");
    const cc = res.headers.get("Cache-Control") || "";
    const age = Number((/max-age=(\d+)/.exec(cc) || [])[1] || 0);
    this.m.set(String(url), { body: await res.text(), exp: Date.now() + age * 1000 });
  }
  async delete(url) { if (this.fail) throw new Error("cache down"); return this.m.delete(String(url)); }
}
const cache = new MemCache();
globalThis.caches = { default: cache };

// ---------------------------------------------------------------- upstream mocks
let calls, world, logs;
function resetWorld() {
  calls = [];
  logs = [];
  world = {
    sv: { success: true, hostname: "prolinksystems.com", action: "contact", "error-codes": [] },
    byToken: {},                                   // token -> siteverify reply (overrides world.sv)
    siteverifyThrows: false,
    graphTokenStatus: 200,
    sendStatus: 202,
  };
}
const realLog = console.log;
console.log = (...a) => { logs.push(a.join(" ")); };

globalThis.fetch = async (url, init = {}) => {
  url = String(url);
  const body = init.body == null ? "" : String(init.body);
  calls.push({ url, method: init.method || "GET", body });
  if (url === "https://challenges.cloudflare.com/turnstile/v0/siteverify") {
    if (world.siteverifyThrows) throw new Error("network");
    const token = new URLSearchParams(body).get("response");
    return new Response(JSON.stringify(world.byToken[token] || world.sv), { status: 200 });
  }
  if (url.startsWith("https://login.microsoftonline.com/")) {
    return new Response(JSON.stringify({ access_token: "graph-token" }), { status: world.graphTokenStatus });
  }
  if (url.startsWith("https://graph.microsoft.com/v1.0/users/")) return new Response(null, { status: world.sendStatus });
  throw new Error("unexpected fetch " + url);
};

const FN = new URL("../functions/api/contact.js", import.meta.url).href;
const { onRequestPost, onRequest } = await import(FN);
// A second module instance = a second isolate in the same data center: own memory, same (mocked) cache.
const isolateB = await import(FN + "?isolate=b");

// ---------------------------------------------------------------- helpers
let seq = 0;
const uniq = () => (++seq).toString(36) + "-" + realNow().toString(36);
const newIp = () => { seq++; return `198.51.${Math.floor(seq / 250) % 250}.${(seq % 250) + 1}`; };
// Move the mock clock to just after the next multiple of `win` seconds, so a test's requests share one window.
const alignTo = (win) => { const t = Date.now() / 1000; clockOffset += win - (t % win) + 1; };

const ENV = {
  MS_TENANT_ID: "tenant", MS_CLIENT_ID: "client", MS_CLIENT_SECRET: "secret",
  SEND_FROM: "info@prolinksystems.com", TURNSTILE_SECRET_KEY: "ts-secret",
};

function fields(over = {}) {
  return Object.assign({
    first_name: "Dana", last_name: "Rivera", email: `dana.${uniq()}@example.com`, phone: "818-555-0100",
    company: "Rivera Dental Group", message: "We need help with Microsoft 365.", interest: "Managed IT Services",
    source_page: "Contact", page_url: "https://prolinksystems.com/contact",
    "cf-turnstile-response": "tok-" + uniq(),
  }, over);
}

async function post(body, { ip = newIp(), host = "prolinksystems.com", env = ENV, handler = onRequestPost } = {}) {
  const headers = { "Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0)" };
  if (ip) headers["CF-Connecting-IP"] = ip;
  const request = new Request(`https://${host}/api/contact`, {
    method: "POST", headers, body: typeof body === "string" ? body : JSON.stringify(body),
  });
  const res = await handler({ request, env, waitUntil() {} });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch (e) {}
  return { status: res.status, json, headers: res.headers };
}

const sends = () => calls.filter((c) => c.url.includes("/sendMail")).map((c) => JSON.parse(c.body).message);
const graphCalls = () => calls.filter((c) => c.url.startsWith("https://login.microsoftonline.com/") || c.url.includes("graph.microsoft.com"));
const lastLog = () => JSON.parse(logs.filter((l) => l.startsWith("{")).slice(-1)[0] || "{}");

beforeEach(() => { resetWorld(); cache.fail = false; });

// ---------------------------------------------------------------- legitimate submissions keep working
test("contact page submission: notification to info@ + visitor confirmation, reference returned", async () => {
  const f = fields();
  const r = await post(f);
  assert.equal(r.status, 200);
  assert.equal(r.json.success, true);
  assert.match(r.json.refNumber, /^PLS-[A-Z0-9]{6}$/);
  const [notify, confirm] = sends();
  assert.equal(sends().length, 2);
  assert.equal(notify.toRecipients[0].emailAddress.address, "info@prolinksystems.com");
  assert.doesNotMatch(notify.subject, /UNVERIFIED/);
  assert.match(notify.subject, new RegExp(r.json.refNumber));
  assert.equal(notify.replyTo[0].emailAddress.address, f.email);
  assert.equal(confirm.toRecipients[0].emailAddress.address, f.email);
  assert.match(confirm.subject, /Your inquiry has been received/);
  assert.match(confirm.body.content, /You're in good hands, Dana\./);
  assert.doesNotMatch(notify.body.content, /No confirmation email was sent/);
  assert.equal(lastLog().outcome, "accepted");
});

test("industry, city and Ads landing page field names are still accepted (name / firm_name / firm_size / challenge)", async () => {
  const r = await post({
    name: "Sam Lee", email: `sam.${uniq()}@example.com`, firm_name: "Lee & Park LLP", firm_size: "11-25",
    challenge: "Security and compliance", source_page: "Law firm IT", "cf-turnstile-response": "tok-" + uniq(),
  });
  assert.equal(r.status, 200);
  const [notify, confirm] = sends();
  assert.match(notify.body.content, /Lee &amp; Park LLP/);
  assert.match(notify.body.content, /Firm size: 11-25/);
  assert.match(confirm.body.content, /You're in good hands, Sam\./);
});

test("a token solved on www.prolinksystems.com is accepted on prolinksystems.com (one site)", async () => {
  world.sv = { success: true, hostname: "www.prolinksystems.com", action: "contact" };
  const r = await post(fields());
  assert.equal(r.status, 200);
  assert.equal(sends().length, 2);
});

test("one visitor sending two different forms from the same IP: both go through", async () => {
  const ip = newIp();
  const a = await post(fields(), { ip });
  const b = await post(fields(), { ip });
  assert.equal(a.status, 200);
  assert.equal(b.status, 200);
  assert.notEqual(a.json.refNumber, b.json.refNumber);
  assert.equal(sends().length, 4);
});

test("a branch preview accepts a token solved on that same preview (staging review keeps working)", async () => {
  const host = "seo-growth-2026-11.plsmain.pages.dev";
  world.sv = { success: true, hostname: host, action: "contact" };
  const r = await post(fields(), { host });
  assert.equal(r.status, 200);
});

// ---------------------------------------------------------------- hostname
test("a token solved on a preview / old deployment is refused on production, before any email", async () => {
  world.sv = { success: true, hostname: "2b85327c.plsmain.pages.dev", action: "contact" };
  const r = await post(fields());
  assert.equal(r.status, 400);
  assert.match(r.json.message, /Verification failed/);
  assert.equal(graphCalls().length, 0);
  assert.equal(lastLog().reason, "hostname");
});

test("a token from another site, or with no hostname at all, is refused", async () => {
  world.sv = { success: true, hostname: "evil.example", action: "contact" };
  assert.equal((await post(fields())).status, 400);
  world.sv = { success: true, action: "contact" };
  assert.equal((await post(fields())).status, 400);
  assert.equal(graphCalls().length, 0);
});

test("TURNSTILE_ALLOWED_HOSTNAMES (local testing with Cloudflare's dummy keys) accepts the listed hostname", async () => {
  world.sv = { success: true, hostname: "example.com", action: "contact" };
  const r = await post(fields(), { host: "localhost:8788", env: Object.assign({}, ENV, { TURNSTILE_ALLOWED_HOSTNAMES: "example.com" }) });
  assert.equal(r.status, 200);
});

// ---------------------------------------------------------------- action
test("a checkout token (action 'checkout') is refused on /api/contact", async () => {
  world.sv = { success: true, hostname: "prolinksystems.com", action: "checkout" };
  const r = await post(fields());
  assert.equal(r.status, 400);
  assert.equal(graphCalls().length, 0);
  assert.equal(lastLog().reason, "action");
});

test("an unlabeled token (page opened before the release) still delivers the lead, as [UNVERIFIED], no confirmation", async () => {
  world.sv = { success: true, hostname: "prolinksystems.com", action: "" };
  const r = await post(fields());
  assert.equal(r.status, 200);
  assert.equal(sends().length, 1);
  assert.match(sends()[0].subject, /^\[UNVERIFIED\] /);
  assert.match(sends()[0].body.content, /opened before the latest site update/);
  assert.equal(lastLog().why, "unlabeled-widget");
});

// ---------------------------------------------------------------- existing Turnstile behaviour is unchanged
test("no token / forged token -> 400 and nothing sent", async () => {
  assert.equal((await post(fields({ "cf-turnstile-response": "" }))).status, 400);
  world.sv = { success: false, "error-codes": ["invalid-input-response"] };
  assert.equal((await post(fields())).status, 400);
  assert.equal(graphCalls().length, 0);
});

test("an expired or already-used token (timeout-or-duplicate) is rejected, and a replay never reaches Cloudflare again", async () => {
  world.sv = { success: false, "error-codes": ["timeout-or-duplicate"] };
  const f = fields();
  const r = await post(f);
  assert.equal(r.status, 400);
  assert.match(r.json.message, /expired or was already used/);
  assert.equal(graphCalls().length, 0);
  assert.equal(lastLog().reason, "expired-or-used");
  const again = await post(f, { handler: isolateB.onRequestPost });
  assert.equal(again.status, 400);
  assert.equal(calls.filter((c) => c.url.includes("siteverify")).length, 1);
  assert.equal(graphCalls().length, 0);
});

test("Cloudflare-side failure (internal-error, or siteverify unreachable) -> [UNVERIFIED] notification only", async () => {
  world.sv = { success: false, "error-codes": ["internal-error"] };
  assert.equal((await post(fields())).status, 200);
  assert.equal(sends().length, 1);
  assert.match(sends()[0].subject, /^\[UNVERIFIED\] /);
  assert.match(sends()[0].body.content, /Cloudflare could not confirm the robot check/);
  resetWorld();
  world.siteverifyThrows = true;
  assert.equal((await post(fields())).status, 200);
  assert.equal(sends().length, 1);
  assert.match(sends()[0].subject, /^\[UNVERIFIED\] /);
});

test("honeypot -> 200 and nothing sent; invalid JSON / null body -> 400; GET -> 405; missing env -> 500", async () => {
  const h = await post(fields({ botcheck: "on" }));
  assert.equal(h.status, 200);
  assert.equal(calls.length, 0);
  assert.equal((await post("{not json")).status, 400);
  assert.equal((await post("null")).status, 400);
  const g = await onRequest({ request: new Request("https://prolinksystems.com/api/contact"), env: ENV });
  assert.equal(g.status, 405);
  const env = Object.assign({}, ENV, { TURNSTILE_SECRET_KEY: "" });
  assert.equal((await post(fields(), { env })).status, 500);
});

// ---------------------------------------------------------------- once per token
test("the same token twice: the repeat gets the first reference and nothing is sent again", async () => {
  const f = fields();
  const a = await post(f);
  const b = await post(f);
  assert.equal(a.status, 200);
  assert.equal(b.status, 200);
  assert.equal(b.json.refNumber, a.json.refNumber);
  assert.equal(sends().length, 2);                 // the first submission's two emails only
  assert.equal(calls.filter((c) => c.url.includes("siteverify")).length, 1);
});

test("a token refused for its hostname stays refused when replayed (no [UNVERIFIED] fallback)", async () => {
  const f = fields();
  world.sv = { success: true, hostname: "2b85327c.plsmain.pages.dev", action: "contact" };
  assert.equal((await post(f)).status, 400);
  world.sv = { success: false, "error-codes": ["timeout-or-duplicate"] };   // what Cloudflare says about a used token
  assert.equal((await post(f)).status, 400);
  assert.equal((await post(f, { handler: isolateB.onRequestPost })).status, 400);
  assert.equal(graphCalls().length, 0);
  assert.equal(lastLog().reason, "refused-token-again");
});

test("a processed token replayed hours later still sends nothing", async () => {
  const f = fields();
  const a = await post(f);
  clockOffset += 6 * 3600;
  world.sv = { success: false, "error-codes": ["timeout-or-duplicate"] };
  const b = await post(f, { handler: isolateB.onRequestPost });
  assert.equal(b.status, 200);
  assert.equal(b.json.refNumber, a.json.refNumber);
  assert.equal(sends().length, 2);
});

test("a replay that lands on another isolate in the same data center is caught through the cache", async () => {
  const f = fields();
  const a = await post(f);
  const b = await post(f, { handler: isolateB.onRequestPost });
  assert.equal(a.status, 200);
  assert.equal(b.status, 200);
  assert.equal(b.json.refNumber, a.json.refNumber);
  assert.equal(sends().length, 2);
});

test("while the first request for a token is still running, a repeat on another isolate gets 409 and sends nothing", { timeout: 5000 }, async () => {
  world.graphTokenStatus = 200;
  const f = fields();
  let release;
  const gate = new Promise((r) => { release = r; });
  const timer = setTimeout(() => release(), 500);       // never hang, even against code without the claim
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {             // hold the first request inside siteverify
    if (String(url).includes("siteverify")) await gate;
    return realFetch(url, init);
  };
  try {
    const first = post(f);
    await new Promise((r) => setTimeout(r, 20));
    const repeat = await post(f, { handler: isolateB.onRequestPost });
    assert.equal(repeat.status, 409);
    release();
    assert.equal((await first).status, 200);
  } finally {
    clearTimeout(timer);
    release();
    globalThis.fetch = realFetch;
  }
  assert.equal(sends().length, 2);
});

test("Graph down -> 502 and the token is released: a retry is checked by Cloudflare again, not answered as a duplicate", async () => {
  world.sendStatus = 503;
  const f = fields();
  assert.equal((await post(f)).status, 502);
  world.sendStatus = 202;
  world.sv = { success: false, "error-codes": ["timeout-or-duplicate"] };   // what Cloudflare says on a reused token
  const attempted = sends().length;                // the failed notification attempt
  const r = await post(f);
  assert.equal(r.status, 400);                     // the form resets its widget; the visitor sends again
  assert.equal(calls.filter((c) => c.url.includes("siteverify")).length, 2);
  assert.equal(sends().length, attempted);         // nothing new sent
});

// ---------------------------------------------------------------- rate limits
test("per-IP limit: the 6th POST within 10 minutes gets 429 + Retry-After; other IPs and later windows are fine", async () => {
  alignTo(600);
  const ip = newIp();
  for (let i = 0; i < 5; i++) assert.equal((await post(fields(), { ip })).status, 200, `POST ${i + 1}`);
  const blocked = await post(fields(), { ip });
  assert.equal(blocked.status, 429);
  assert.match(blocked.json.message, /Too many attempts/);
  assert.ok(Number(blocked.headers.get("Retry-After")) > 0);
  assert.equal(lastLog().reason, "rate-limit:post");
  assert.equal((await post(fields(), { ip: newIp() })).status, 200);
  clockOffset += 601;                              // next 10-minute window
  assert.equal((await post(fields(), { ip })).status, 200);
});

test("the per-IP limit holds across isolates sharing the data-center cache", async () => {
  alignTo(600);
  const ip = newIp();
  for (let i = 0; i < 3; i++) assert.equal((await post(fields(), { ip })).status, 200);
  for (let i = 0; i < 2; i++) assert.equal((await post(fields(), { ip, handler: isolateB.onRequestPost })).status, 200);
  assert.equal((await post(fields(), { ip, handler: isolateB.onRequestPost })).status, 429);
});

test("per-IP limit counts IPv6 clients by their /64", async () => {
  alignTo(600);
  const p = `2001:db8:${(seq % 9000) + 100}:1`;
  for (let i = 0; i < 5; i++) assert.equal((await post(fields(), { ip: `${p}::${i + 1}` })).status, 200);
  assert.equal((await post(fields(), { ip: `${p}:0:0:0:beef` })).status, 429);
});

test("[UNVERIFIED] notifications are capped at 2 per IP per hour", async () => {
  alignTo(3600);
  const ip = newIp();
  world.sv = { success: false, "error-codes": ["internal-error"] };
  assert.equal((await post(fields(), { ip })).status, 200);
  assert.equal((await post(fields(), { ip })).status, 200);
  const third = await post(fields(), { ip });
  assert.equal(third.status, 429);
  assert.equal(sends().length, 2);
  assert.equal(lastLog().reason, "rate-limit:unverified");
});

test("no client IP header (local development): not rate limited", async () => {
  for (let i = 0; i < 7; i++) assert.equal((await post(fields(), { ip: "" })).status, 200);
});

// ---------------------------------------------------------------- visitor confirmation gates
test("confirmations to one address are capped at 2 per day; the lead still reaches info@ and says why", async () => {
  alignTo(86400);
  const email = `repeat.${uniq()}@example.com`;
  for (let i = 0; i < 2; i++) assert.equal((await post(fields({ email }))).status, 200);
  assert.equal(sends().length, 4);
  const r = await post(fields({ email }));
  assert.equal(r.status, 200);
  assert.equal(sends().length, 5);                 // notification only
  assert.match(sends()[4].body.content, /No confirmation email was sent to this visitor/);
  assert.equal(lastLog().confirmation, "skipped:address-cap");
});

test("link-like text in an echoed field: lead captured, no confirmation to the typed address", async () => {
  for (const over of [{ first_name: "Visit www.cheap-meds.example" }, { company: "http://spam.example/win" },
    { last_name: "contact me at someone@else.example" }, { company: "bestdeals.ru" }]) {
    resetWorld();
    const r = await post(fields(over));
    assert.equal(r.status, 200);
    assert.equal(sends().length, 1, JSON.stringify(over));
    assert.equal(sends()[0].toRecipients[0].emailAddress.address, "info@prolinksystems.com");
    assert.equal(lastLog().confirmation, "skipped:linkish");
  }
});

test("ordinary punctuation is not mistaken for a link (St. John's, J.P. Morgan, 555.123.4567)", async () => {
  const r = await post(fields({ first_name: "J.P.", last_name: "O'Neil", company: "St. John's Health", phone: "555.123.4567" }));
  assert.equal(r.status, 200);
  assert.equal(sends().length, 2);
});

test("echoed fields are clipped in the confirmation; the notification keeps the full text", async () => {
  const longName = "A".repeat(300);
  await post(fields({ first_name: longName }));
  const [notify, confirm] = sends();
  assert.ok(notify.body.content.includes(longName));
  assert.ok(!confirm.body.content.includes("A".repeat(41)));
  assert.ok(confirm.body.content.includes("A".repeat(39) + "…"));
});

// ---------------------------------------------------------------- the counters fail open
test("Cache API unavailable or failing: submissions still go through (in-memory counting only)", async () => {
  cache.fail = true;
  assert.equal((await post(fields())).status, 200);
  const saved = globalThis.caches;
  delete globalThis.caches;
  try {
    assert.equal((await post(fields())).status, 200);
  } finally {
    globalThis.caches = saved;
  }
  assert.equal(sends().length, 4);
});

test("a D1 binding that errors (CONTACT_DB) falls back to the cache + memory counters; submissions still go through", async () => {
  const broken = { prepare() { throw new Error("D1 down"); }, batch: async () => { throw new Error("D1 down"); } };
  const env = Object.assign({}, ENV, { CONTACT_DB: broken });
  const ip = newIp();
  const f = fields();
  const a = await post(f, { ip, env });
  assert.equal(a.status, 200);
  assert.equal(sends().length, 2);
  const b = await post(f, { ip, env });             // the once-per-token rule still holds
  assert.equal(b.json.refNumber, a.json.refNumber);
  assert.equal(sends().length, 2);
});

test("logs never contain the client IP or the visitor's email address", async () => {
  const ip = newIp();
  const f = fields();
  await post(f, { ip });
  world.sv = { success: true, hostname: "evil.example", action: "contact" };
  await post(fields(), { ip });
  const all = logs.join("\n");
  assert.ok(!all.includes(ip));
  assert.ok(!all.includes(f.email));
});

test.after(() => { console.log = realLog; Date.now = realNow; });
