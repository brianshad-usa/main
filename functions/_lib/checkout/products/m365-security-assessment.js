/**
 * App #1: Microsoft 365 Security Assessment ($2,500, one-time, read-only). Not a route.
 *
 * The website sells, takes payment and hands over ONE verified order; the assessment
 * agent (private repo brianshad-usa/m365-security-agent, spec docs/website-integration.md)
 * does everything after: Pro Link's approval, the read-only assessment, Pro Link's review
 * of the report, and the client emails. The order JSON must satisfy the agent's schema
 * (copied in ../schemas/m365-assessment-order-v1.js): unknown fields make the agent
 * reject the order.
 */
import { cleanLine, cleanText, normDomain, normEmail, validate } from "../core.js";
import SCHEMA from "../schemas/m365-assessment-order-v1.js";

const AMOUNT = "2500.00";
const TERMS_VERSION = "2026-11";   // the authorization wording on /m365-security-assessment/order

// Field rules come straight from the schema so the form can't drift from the contract.
const P = SCHEMA.properties;
const DOMAIN_RE = new RegExp(P.company.properties.domain.pattern);
const EMAIL_RE = new RegExp(P.contact.properties.email.pattern);
const EMPLOYEES = P.company.properties.employees.enum;

const fail = (field, message) => ({ ok: false, field, message });
const len = (s) => Array.from(s).length;

function cleanSource(src) {
  if (!src || typeof src !== "object") return null;
  const out = {};
  const page = cleanLine(src.page, 400).split(/[?#]/)[0];
  if (page.startsWith("/")) out.page = page.slice(0, 200);
  for (const k of ["utm_source", "utm_medium", "utm_campaign"]) {
    const v = cleanLine(src[k], 100);
    if (v) out[k] = v;
  }
  const gclid = cleanLine(src.gclid, 200);
  if (gclid) out.gclid = gclid;
  return Object.keys(out).length ? out : null;
}

function buildOrder(record, payment, ctx) {
  const order = {
    schema: "prolink.m365-assessment-order/v1",
    order_id: ctx.orderId,
    placed_at: ctx.placedAt,
    product: "m365-security-assessment",
    company: record.company,
    contact: record.contact,
  };
  if (record.technical_contact) order.technical_contact = record.technical_contact;
  order.access_method = "prolink_app";      // always app consent; never an account or a password
  order.payment = {
    processor: "authorize.net",
    transaction_id: String(payment.transactionId),
    amount: payment.amount,
    currency: "USD",
    status: "captured",
    verified_at: payment.verifiedAt,
  };
  if (payment.last4) order.payment.card_last4 = payment.last4;
  order.authorization = record.authorization;
  if (ctx.sandbox) order.test = true;         // sandbox orders: the agent validates, replies, does nothing else
  order.pre_call_requested = record.pre_call_requested === true;
  order.notes = record.notes || "";
  if (record.source) order.source = record.source;
  return order;
}

function intake(input, ctx) {
  const company = { name: cleanLine(input.company_name, 120), domain: normDomain(input.company_domain) };
  if (len(company.name) < 2) return fail("company_name", "Please enter your company name.");
  if (!DOMAIN_RE.test(company.domain)) {
    return fail("company_domain", "Please enter the domain your company email uses, like acme.com.");
  }
  const employees = cleanLine(input.employees, 20);
  if (employees) {
    if (!EMPLOYEES.includes(employees)) return fail("employees", "Please choose your number of employees.");
    company.employees = employees;
  }

  const contact = { name: cleanLine(input.contact_name, 120), email: normEmail(input.contact_email) };
  if (len(contact.name) < 2) return fail("contact_name", "Please enter your name.");
  if (contact.email.length > 254 || !EMAIL_RE.test(contact.email)) {
    return fail("contact_email", "Please enter a valid email address.");
  }
  const title = cleanLine(input.contact_title, 120);
  if (title) contact.title = title;
  const phone = cleanLine(input.contact_phone, 40);
  if (phone) contact.phone = phone;

  let technical_contact = null;
  const techName = cleanLine(input.tech_name, 120);
  const techEmail = normEmail(input.tech_email);
  if (techName || techEmail) {
    if (len(techName) < 2) return fail("tech_name", "Enter your Global Administrator's name and email address, or leave both blank.");
    if (techEmail.length > 254 || !EMAIL_RE.test(techEmail)) {
      return fail("tech_email", "Enter your Global Administrator's name and email address, or leave both blank.");
    }
    technical_contact = { name: techName, email: techEmail };
  }

  if (input.auth_accepted !== true) return fail("auth_accepted", "Please check the authorization box to continue.");
  const signer = cleanLine(input.auth_name, 120);
  if (len(signer) < 2) return fail("auth_name", "Please type your full name to sign the authorization.");
  const authorization = { accepted: true, terms_version: TERMS_VERSION, accepted_at: ctx.now, signer_name: signer };
  const signerTitle = cleanLine(input.auth_title, 120);
  if (signerTitle) authorization.signer_title = signerTitle;
  if (ctx.ip) authorization.ip = ctx.ip;

  const notes = cleanText(input.notes);
  if (len(notes) > 1000) return fail("notes", "Notes can be up to 1,000 characters.");

  const record = { company, contact };
  if (technical_contact) record.technical_contact = technical_contact;
  record.authorization = authorization;
  record.pre_call_requested = input.pre_call === true;
  record.notes = notes;
  const source = cleanSource(input.source);
  if (source) record.source = source;

  // Prove now that the paid order will satisfy the agent's schema, so a payment can never
  // end in an order the agent rejects.
  const probe = buildOrder(record,
    { transactionId: "1", amount: AMOUNT, verifiedAt: ctx.now, last4: "0000" },
    { orderId: ctx.orderId, placedAt: ctx.now, sandbox: ctx.sandbox });
  const errors = validate(SCHEMA, probe);
  if (errors.length) return { ok: false, field: null, message: "Please check the form and try again.", errors };

  return { ok: true, record, email: contact.email };
}

export default {
  id: "m365-security-assessment",
  name: "Microsoft 365 Security Assessment",
  amount: AMOUNT,
  orderPrefix: "M365",
  pages: {
    product: "/m365-security-assessment",
    order: "/m365-security-assessment/order",
    thankYou: "/m365-security-assessment/thank-you",
  },
  intake,
  buildOrder,
  schema: SCHEMA,
  handoff: {
    type: "github-issue",
    repo: "brianshad-usa/m365-security-agent",
    tokenEnv: "GITHUB_ORDERS_TOKEN",
    titlePrefix: "[order]",
    title(order) {
      return `[order] ${order.order_id} ${cleanLine(order.company.name, 100)}`;
    },
    body(order) {
      // Backticks are escaped inside the JSON (` is the same character once parsed) so text a
      // customer typed can never close the ```json fence the agent reads.
      const payload = JSON.stringify(order, null, 2).replace(/`/g, "\\u0060");
      return "Paid order from prolinksystems.com\n\n<!-- prolink-order:v1 -->\n```json\n" + payload + "\n```\n";
    },
  },
};
