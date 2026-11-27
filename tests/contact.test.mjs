// Node tests for the lead-form Function (functions/api/contact.js).
// Run from the repo root: node --test tests/contact.test.mjs
// (Node 22.5+ for node:sqlite; no other dependencies. Mocks Turnstile siteverify, Microsoft Graph and the
// Cache API; the D1 database is a real SQLite database behind a D1-shaped adapter.)
// 2026-11-26 (Phase G security closeout): Turnstile hostname + action checks, per-IP limits, once-per-token
// processing, visitor-confirmation gates. 2026-11-27 (final security release): no [UNVERIFIED] fallback —
// nothing is sent unless Turnstile fully passes; D1 (CONTACT_DB) required; D1 outage modes; health check.
// And throughout: proof that real submissions still work.
import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { createHash } from "node:crypto";

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

// ---------------------------------------------------------------- D1: a real SQLite database, D1-shaped
// prepare(sql).bind(...).first()/run()/all(), and batch() = one transaction (as D1 runs it).
class FakeD1 {
  constructor() { this.db = new DatabaseSync(":memory:"); this.fail = false; this.hang = false; this.batches = 0; }
  async check() {
    if (this.hang) await new Promise(() => {});    // a D1 call that never answers
    if (this.fail) throw new Error("D1_ERROR: storage unavailable (simulated outage)");
  }
  prepare(sql) {
    const self = this;
    const stmt = (args) => ({
      bind: (...a) => stmt(a),
      exec() { return { success: true, results: self.db.prepare(sql).all(...args).map((r) => ({ ...r })) }; },
      async first() { await self.check(); const r = this.exec().results; return r.length ? r[0] : null; },
      async run() { await self.check(); this.exec(); return { success: true }; },
      async all() { await self.check(); return this.exec(); },
    });
    return stmt([]);
  }
  async batch(stmts) {
    await this.check();
    this.batches++;
    this.db.exec("BEGIN");
    try { const out = stmts.map((s) => s.exec()); this.db.exec("COMMIT"); return out; }
    catch (e) { this.db.exec("ROLLBACK"); throw e; }
  }
  rows(table) {
    try { return this.db.prepare(`SELECT * FROM ${table}`).all().map((r) => ({ ...r })); } catch (e) { return []; }
  }
}
const db = new FakeD1();

// ---------------------------------------------------------------- upstream mocks
let calls, world, logs;
function resetWorld() {
  calls = [];
  logs = [];
  world = {
    sv: { success: true, hostname: "prolinksystems.com", action: "contact", "error-codes": [] },
    byToken: {},                                   // token -> siteverify reply (overrides world.sv)
    used: new Set(),                               // like Cloudflare: a token passes once, then "timeout-or-duplicate"
    siteverifyThrows: false,
    siteverifyHtml: false,
    graphTokenStatus: 200,
    sendStatus: 202,
    graphGate: null,                               // a promise that holds the Microsoft login call
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
    if (world.siteverifyHtml) return new Response("<html>502 Bad Gateway</html>", { status: 502 });
    const token = new URLSearchParams(body).get("response");
    let reply = world.byToken[token] || world.sv;
    if (reply.success === true) {
      if (world.used.has(token)) reply = { success: false, "error-codes": ["timeout-or-duplicate"] };
      world.used.add(token);
    }
    return new Response(JSON.stringify(reply), { status: 200 });
  }
  if (url.startsWith("https://login.microsoftonline.com/")) {
    if (world.graphGate) await world.graphGate;
    return new Response(JSON.stringify({ access_token: "graph-token" }), { status: world.graphTokenStatus });
  }
  if (url.startsWith("https://graph.microsoft.com/v1.0/users/")) return new Response(null, { status: world.sendStatus });
  throw new Error("unexpected fetch " + url);
};

const FN = new URL("../functions/api/contact.js", import.meta.url).href;
const { onRequestPost, onRequest } = await import(FN);
// A second module instance = a second isolate: own memory, same D1, same (mocked) data-center cache.
const isolateB = await import(FN + "?isolate=b");

// ---------------------------------------------------------------- helpers
let seq = 0;
const uniq = () => (++seq).toString(36) + "-" + realNow().toString(36);
const newIp = () => { seq++; return `198.51.${Math.floor(seq / 250) % 250}.${(seq % 250) + 1}`; };
// Move the mock clock to just after the next multiple of `win` seconds, so a test's requests share one window.
const alignTo = (win) => { const t = Date.now() / 1000; clockOffset += win - (t % win) + 1; };
// The D1 key of a token, as the Function computes it.
const tokenKey = (t) => "tok-" + createHash("sha256").update("pls-contact:tok:" + t).digest("hex").slice(0, 24);

const ENV = {
  MS_TENANT_ID: "tenant", MS_CLIENT_ID: "client", MS_CLIENT_SECRET: "secret",
  SEND_FROM: "info@prolinksystems.com", TURNSTILE_SECRET_KEY: "ts-secret", CONTACT_DB: db,
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
const siteverifyCalls = () => calls.filter((c) => c.url.includes("siteverify")).length;
const lastLog = () => JSON.parse(logs.filter((l) => l.startsWith("{")).slice(-1)[0] || "{}");
const noMail = (r, label) => { assert.equal(graphCalls().length, 0, label || "no Microsoft call at all"); assert.notEqual(r.status, 200, label); };

beforeEach(() => { resetWorld(); cache.fail = false; db.fail = false; db.hang = false; });

// ---------------------------------------------------------------- legitimate submissions keep working
test("contact page submission: notification to info@ + visitor confirmation, reference returned, recorded in D1", async () => {
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
  assert.equal(lastLog().store, "d1");
  const row = db.rows("contact_token").find((x) => x.h === tokenKey(f["cf-turnstile-response"]));
  assert.equal(row.v, r.json.refNumber);
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

// ---------------------------------------------------------------- hostname and action: no email, no D1 write
test("a token solved on a preview / old deployment is refused on production: no email, nothing written to D1", async () => {
  world.sv = { success: true, hostname: "2b85327c.plsmain.pages.dev", action: "contact" };
  const f = fields();
  const r = await post(f);
  assert.equal(r.status, 400);
  assert.match(r.json.message, /Verification failed/);
  noMail(r);
  assert.equal(lastLog().reason, "hostname");
  assert.ok(!db.rows("contact_token").some((x) => x.h === tokenKey(f["cf-turnstile-response"])));
});

test("a token from another site, or with no hostname at all, is refused", async () => {
  world.sv = { success: true, hostname: "evil.example", action: "contact" };
  assert.equal((await post(fields())).status, 400);
  world.sv = { success: true, action: "contact" };
  const r = await post(fields());
  assert.equal(r.status, 400);
  noMail(r);
});

test("TURNSTILE_ALLOWED_HOSTNAMES (local testing with Cloudflare's dummy keys) accepts the listed hostname", async () => {
  world.sv = { success: true, hostname: "example.com", action: "contact" };
  const r = await post(fields(), { host: "localhost:8788", env: Object.assign({}, ENV, { TURNSTILE_ALLOWED_HOSTNAMES: "example.com" }) });
  assert.equal(r.status, 200);
});

test("a checkout token (action 'checkout') is refused on /api/contact", async () => {
  world.sv = { success: true, hostname: "prolinksystems.com", action: "checkout" };
  const r = await post(fields());
  assert.equal(r.status, 400);
  noMail(r);
  assert.equal(lastLog().reason, "action");
});

test("an unlabeled token (page opened before the release): NO email; the visitor is asked to reload the page", async () => {
  world.sv = { success: true, hostname: "prolinksystems.com", action: "" };
  const r = await post(fields());
  assert.equal(r.status, 400);
  assert.match(r.json.message, /reload it, then send your message again/);
  noMail(r);
  assert.equal(lastLog().reason, "unlabeled-widget");
});

// ---------------------------------------------------------------- every Turnstile failure: nothing sent
test("no token / forged token -> 400 'Verification failed', nothing sent", async () => {
  let r = await post(fields({ "cf-turnstile-response": "" }));
  assert.equal(r.status, 400);
  assert.match(r.json.message, /Verification failed/);
  world.sv = { success: false, "error-codes": ["invalid-input-response"] };
  r = await post(fields());
  assert.equal(r.status, 400);
  assert.match(r.json.message, /Verification failed/);
  noMail(r);
});

test("an expired or already-used token (timeout-or-duplicate): 400 'press Send again', nothing sent", async () => {
  world.sv = { success: false, "error-codes": ["timeout-or-duplicate"] };
  const r = await post(fields());
  assert.equal(r.status, 400);
  assert.match(r.json.message, /expired or was already used\. Please press Send again/);
  noMail(r);
  assert.equal(lastLog().reason, "expired-or-used");
});

test("a Turnstile secret Cloudflare rejects (invalid-input-secret, e.g. after a key rotation): 503, nothing sent", async () => {
  for (const codes of [["invalid-input-secret"], ["missing-input-secret"], ["invalid-input-secret", "timeout-or-duplicate"]]) {
    resetWorld();
    world.sv = { success: false, "error-codes": codes };
    const r = await post(fields());
    assert.equal(r.status, 503, codes.join(","));
    assert.match(r.json.message, /try again in a minute, or call 1-800-890-6133/);
    noMail(r, codes.join(","));
    assert.equal(lastLog().reason, "turnstile-unavailable");
  }
});

test("Cloudflare-side failure (internal-error, siteverify unreachable, a non-JSON reply): 503, nothing sent", async () => {
  world.sv = { success: false, "error-codes": ["internal-error"] };
  let r = await post(fields());
  assert.equal(r.status, 503);
  noMail(r);
  resetWorld();
  world.siteverifyThrows = true;
  r = await post(fields());
  assert.equal(r.status, 503);
  noMail(r);
  resetWorld();
  world.siteverifyHtml = true;
  r = await post(fields());
  assert.equal(r.status, 503);
  noMail(r);
});

test("any other failure (unknown codes, no codes, success not exactly true) -> 400, nothing sent", async () => {
  for (const sv of [{ success: false, "error-codes": ["bad-request"] }, { success: false }, { success: "true", hostname: "prolinksystems.com", action: "contact" }]) {
    resetWorld();
    world.sv = sv;
    const r = await post(fields());
    assert.equal(r.status, 400, JSON.stringify(sv));
    noMail(r, JSON.stringify(sv));
  }
});

test("a token longer than any real one (2048 characters) is refused without asking Cloudflare", async () => {
  const r = await post(fields({ "cf-turnstile-response": "x".repeat(2049) }));
  assert.equal(r.status, 400);
  assert.equal(siteverifyCalls(), 0);
  noMail(r);
  assert.equal((await post(fields({ "cf-turnstile-response": "y".repeat(2048) }))).status, 200);
});

test("the form is checked BEFORE the token is spent: a missing name or bad email doesn't use up the robot check", async () => {
  let r = await post(fields({ first_name: "" }));
  assert.equal(r.status, 400);
  assert.match(r.json.message, /enter your name and email/);
  r = await post(fields({ email: "not-an-email" }));
  assert.equal(r.status, 400);
  assert.match(r.json.message, /valid email/);
  assert.equal(siteverifyCalls(), 0);
  noMail(r);
});

test("honeypot -> 200 and nothing sent; invalid JSON / null / array body -> 400; GET -> 405", async () => {
  const h = await post(fields({ botcheck: "on" }));
  assert.equal(h.status, 200);
  assert.equal(calls.length, 0);
  assert.equal((await post("{not json")).status, 400);
  assert.equal((await post("null")).status, 400);
  assert.equal((await post("[]")).status, 400);
  const g = await onRequest({ request: new Request("https://prolinksystems.com/api/contact"), env: ENV });
  assert.equal(g.status, 405);
});

test("configuration is required, the D1 binding included: 500 'Server not configured.' and nothing sent", async () => {
  for (const k of ["MS_TENANT_ID", "MS_CLIENT_ID", "MS_CLIENT_SECRET", "SEND_FROM", "TURNSTILE_SECRET_KEY", "CONTACT_DB"]) {
    const env = Object.assign({}, ENV, { [k]: "" });
    const r = await post(fields(), { env });
    assert.equal(r.status, 500, k);
    assert.equal(r.json.message, "Server not configured.");
  }
  // A binding that isn't a D1 database (e.g. a KV namespace bound under the wrong name).
  const r = await post(fields(), { env: Object.assign({}, ENV, { CONTACT_DB: { get() {}, put() {} } }) });
  assert.equal(r.status, 500);
  assert.equal(calls.length, 0);
});

test("the release probe POST {} still answers 'Verification failed' when configured (and sends nothing)", async () => {
  const r = await post({});
  assert.equal(r.status, 400);
  assert.match(r.json.message, /Verification failed/);
  assert.equal(calls.length, 0);
});

// ---------------------------------------------------------------- health check
test("GET /api/contact?health=1: ok + version + d1 when configured; 503 without D1 or when D1 fails; never sends", async () => {
  const get = (env) => onRequest({ request: new Request("https://prolinksystems.com/api/contact?health=1"), env });
  let r = await get(ENV);
  assert.equal(r.status, 200);
  const j = await r.json();
  assert.equal(j.ok, true);
  assert.equal(j.store, "d1");
  assert.match(j.version, /^\d{4}-\d{2}-\d{2}$/);
  r = await get(Object.assign({}, ENV, { CONTACT_DB: undefined }));
  assert.equal(r.status, 503);
  assert.equal((await r.json()).reason, "not-configured");
  db.fail = true;
  r = await get(ENV);
  assert.equal(r.status, 503);
  assert.equal((await r.json()).reason, "store-unavailable");
  assert.equal(calls.length, 0);
});

// ---------------------------------------------------------------- once per token (D1, global)
test("the same token twice: the repeat gets the first reference and nothing is sent again", async () => {
  const f = fields();
  const a = await post(f);
  const b = await post(f);
  assert.equal(a.status, 200);
  assert.equal(b.status, 200);
  assert.equal(b.json.refNumber, a.json.refNumber);
  assert.equal(sends().length, 2);
  assert.equal(siteverifyCalls(), 1);
});

test("a token replayed on another isolate / data center: Cloudflare says 'used', D1 knows the lead -> same reference, nothing sent", async () => {
  const f = fields();
  const a = await post(f);
  cache.m.clear();                                  // another data center: nothing shared but D1
  const b = await post(f, { handler: isolateB.onRequestPost });
  assert.equal(b.status, 200);
  assert.equal(b.json.refNumber, a.json.refNumber);
  assert.equal(sends().length, 2);
  assert.equal(lastLog().outcome, "duplicate");
});

test("a processed token replayed hours later still sends nothing", async () => {
  const f = fields();
  const a = await post(f);
  clockOffset += 6 * 3600;
  const b = await post(f, { handler: isolateB.onRequestPost });
  assert.equal(b.status, 200);
  assert.equal(b.json.refNumber, a.json.refNumber);
  assert.equal(sends().length, 2);
});

test("while the first request for a token is still running, a repeat elsewhere gets 409 and sends nothing", { timeout: 5000 }, async () => {
  const f = fields();
  let release;
  world.graphGate = new Promise((r) => { release = r; });
  const timer = setTimeout(() => release(), 1000);  // never hang
  try {
    const first = post(f);
    await new Promise((r) => setTimeout(r, 30));
    const repeat = await post(f, { handler: isolateB.onRequestPost });
    assert.equal(repeat.status, 409);
    assert.match(repeat.json.message, /already being sent/);
    release();
    assert.equal((await first).status, 200);
  } finally {
    clearTimeout(timer);
    release();
  }
  assert.equal(sends().length, 2);
});

test("an abandoned claim (a crash mid-request) expires and does not block the token for good", async () => {
  const t = "tok-" + uniq();
  const now = Math.floor(Date.now() / 1000);
  await post(fields());                             // make sure the tables exist
  db.db.prepare("INSERT INTO contact_token (h, v, exp) VALUES (?, 'pending', ?)").run(tokenKey(t), now - 1);
  resetWorld();
  const r = await post(fields({ "cf-turnstile-response": t }));
  assert.equal(r.status, 200);
  assert.equal(sends().length, 2);
});

test("Graph down -> 502, nothing recorded; the same token can't be resent, a fresh robot check goes through", async () => {
  world.sendStatus = 503;
  const f = fields();
  assert.equal((await post(f)).status, 502);
  assert.ok(!db.rows("contact_token").some((x) => x.h === tokenKey(f["cf-turnstile-response"])));
  world.sendStatus = 202;
  const attempted = sends().length;                 // the failed notification attempt
  const again = await post(f);
  assert.equal(again.status, 400);                  // Cloudflare: used. The form resets its widget.
  assert.match(again.json.message, /press Send again/);
  assert.equal(sends().length, attempted);
  const fresh = await post(fields({ email: f.email }));
  assert.equal(fresh.status, 200);
});

// ---------------------------------------------------------------- rate limits
test("per-IP limit (D1, global): the 6th verified submission within 10 minutes gets 429; other IPs and later windows are fine", async () => {
  alignTo(600);
  const ip = newIp();
  for (let i = 0; i < 5; i++) assert.equal((await post(fields(), { ip })).status, 200, `submission ${i + 1}`);
  const blocked = await post(fields(), { ip });
  assert.equal(blocked.status, 429);
  assert.match(blocked.json.message, /Too many attempts/);
  assert.ok(Number(blocked.headers.get("Retry-After")) > 0);
  assert.equal(lastLog().reason, "rate-limit:sent");
  assert.equal(sends().length, 10);
  assert.equal((await post(fields(), { ip: newIp() })).status, 200);
  clockOffset += 601;                               // next 10-minute window
  assert.equal((await post(fields(), { ip })).status, 200);
});

test("the per-IP limit is global: 3 submissions in one data center + 3 in another -> the 6th is refused", async () => {
  alignTo(600);
  const ip = newIp();
  for (let i = 0; i < 3; i++) assert.equal((await post(fields(), { ip })).status, 200);
  cache.m.clear();                                  // another data center: nothing shared but D1
  for (let i = 0; i < 2; i++) assert.equal((await post(fields(), { ip, handler: isolateB.onRequestPost })).status, 200);
  assert.equal((await post(fields(), { ip, handler: isolateB.onRequestPost })).status, 429);
});

test("16 concurrent verified submissions from one IP over two isolates: exactly 5 accepted (atomic D1 counting)", async () => {
  alignTo(600);
  const ip = newIp();
  const rs = await Promise.all(Array.from({ length: 16 }, (_, i) => post(fields(), { ip, handler: i % 2 ? isolateB.onRequestPost : onRequestPost })));
  assert.equal(rs.filter((r) => r.status === 200).length, 5);
  assert.equal(rs.filter((r) => r.status === 429).length, 11);
  assert.equal(sends().length, 10);
});

test("daily cap: 20 verified submissions per IP per day", async () => {
  alignTo(86400);
  const ip = newIp();
  let ok = 0;
  for (let w = 0; w < 5 && ok < 21; w++) {
    for (let i = 0; i < 5; i++) { const r = await post(fields(), { ip }); if (r.status === 200) ok++; }
    clockOffset += 601;
  }
  assert.equal(ok, 20);
});

test("per-IP limit counts IPv6 clients by their /64", async () => {
  alignTo(600);
  const p = `2001:db8:${(seq % 9000) + 100}:1`;
  for (let i = 0; i < 5; i++) assert.equal((await post(fields(), { ip: `${p}::${i + 1}` })).status, 200);
  assert.equal((await post(fields(), { ip: `${p}:0:0:0:beef` })).status, 429);
});

test("junk traffic is throttled per IP before Cloudflare, and never writes to D1 (the D1 quota can't be burned)", async () => {
  alignTo(600);
  const ip = newIp();
  world.sv = { success: false, "error-codes": ["invalid-input-response"] };
  const before = db.rows("contact_counter").length + db.rows("contact_token").length;
  const statuses = [];
  for (let i = 0; i < 12; i++) statuses.push((await post(fields(), { ip })).status);
  assert.deepEqual(statuses, [400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 429, 429]);
  assert.equal(siteverifyCalls(), 10);
  assert.equal(db.rows("contact_counter").length + db.rows("contact_token").length, before);
  assert.equal(graphCalls().length, 0);
});

test("no client IP header (local development): not counted per IP", async () => {
  for (let i = 0; i < 7; i++) assert.equal((await post(fields(), { ip: "" })).status, 200);
});

// ---------------------------------------------------------------- visitor confirmation gates
test("confirmations to one address are capped at 2 per day, globally; the lead still reaches info@ and says why", async () => {
  alignTo(86400);
  const email = `repeat.${uniq()}@example.com`;
  assert.equal((await post(fields({ email }))).status, 200);
  assert.equal((await post(fields({ email }), { handler: isolateB.onRequestPost })).status, 200);
  assert.equal(sends().length, 4);
  const r = await post(fields({ email }));
  assert.equal(r.status, 200);
  assert.equal(sends().length, 5);                  // notification only
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
    assert.equal(r.json.confirmation, false);       // the page can say "we'll reply personally"
  }
  resetWorld();
  assert.equal((await post(fields())).json.confirmation, undefined);
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

// ---------------------------------------------------------------- D1 outage
test("D1 outage, default 'degrade': the verified lead reaches info@, NO confirmation goes to the typed address", async () => {
  db.fail = true;
  const f = fields();
  const r = await post(f);
  assert.equal(r.status, 200);
  assert.equal(sends().length, 1);
  assert.equal(sends()[0].toRecipients[0].emailAddress.address, "info@prolinksystems.com");
  assert.match(sends()[0].body.content, /rate-limit database was unavailable/);
  assert.equal(lastLog().store, "degraded");
  assert.equal(lastLog().confirmation, "skipped:store-unavailable");
  const again = await post(f);                      // once per token still holds (memory / data-center cache)
  assert.equal(again.json.refNumber, r.json.refNumber);
  assert.equal(sends().length, 1);
});

test("D1 outage, 'degrade': the per-IP limit falls back to this data center's counters", async () => {
  alignTo(600);
  db.fail = true;
  const ip = newIp();
  for (let i = 0; i < 5; i++) assert.equal((await post(fields(), { ip })).status, 200);
  assert.equal((await post(fields(), { ip })).status, 429);
  assert.equal(sends().length, 5);                  // notifications only
});

test("D1 outage, Turnstile failures still send nothing (no fallback of any kind)", async () => {
  db.fail = true;
  for (const sv of [{ success: false, "error-codes": ["internal-error"] }, { success: false, "error-codes": ["invalid-input-secret"] },
    { success: true, hostname: "prolinksystems.com", action: "" }, { success: false, "error-codes": ["timeout-or-duplicate"] }]) {
    resetWorld();
    world.sv = sv;
    const r = await post(fields());
    noMail(r, JSON.stringify(sv));
  }
});

test("D1 that hangs instead of failing: after the time limit it counts as an outage (no visitor left waiting)", { timeout: 5000 }, async () => {
  db.hang = true;
  const env = Object.assign({}, ENV, { CONTACT_DB_TIMEOUT_MS: "50" });
  const t0 = realNow();
  const r = await post(fields(), { env });
  assert.equal(r.status, 200);
  assert.equal(r.json.confirmation, false);
  assert.equal(sends().length, 1);                  // notification only
  assert.ok(realNow() - t0 < 1000, `took ${realNow() - t0} ms`);
  const h = await onRequest({ request: new Request("https://prolinksystems.com/api/contact?health=1"), env });
  assert.equal(h.status, 503);
  const refuse = await post(fields(), { env: Object.assign({}, env, { CONTACT_DB_OUTAGE_MODE: "refuse" }) });
  assert.equal(refuse.status, 503);
});

test("D1 outage with CONTACT_DB_OUTAGE_MODE=refuse: 503 'temporarily unavailable', nothing sent", async () => {
  db.fail = true;
  const env = Object.assign({}, ENV, { CONTACT_DB_OUTAGE_MODE: "refuse" });
  const r = await post(fields(), { env });
  assert.equal(r.status, 503);
  assert.match(r.json.message, /temporarily unavailable/);
  noMail(r);
  db.fail = false;                                  // D1 back: normal service, same settings
  resetWorld();
  assert.equal((await post(fields(), { env })).status, 200);
  assert.equal(sends().length, 2);
});

test("Cache API unavailable or failing: submissions still go through (D1 does the counting)", async () => {
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

// ---------------------------------------------------------------- privacy
test("logs never contain the client IP or the visitor's email address", async () => {
  const ip = newIp();
  const f = fields();
  await post(f, { ip });
  world.sv = { success: true, hostname: "evil.example", action: "contact" };
  await post(fields(), { ip });
  db.fail = true;
  resetWorld();
  await post(fields({ email: f.email }), { ip });
  const all = logs.join("\n");
  assert.ok(!all.includes(ip));
  assert.ok(!all.includes(f.email));
  const stored = JSON.stringify([db.rows("contact_counter"), db.rows("contact_token")]);
  assert.ok(!stored.includes(ip));
  assert.ok(!stored.includes(f.email));
});

test("no notification subject ever carries [UNVERIFIED]", async () => {
  await post(fields());
  for (const m of sends()) assert.doesNotMatch(m.subject, /UNVERIFIED/);
});

test.after(() => { console.log = realLog; Date.now = realNow; });
