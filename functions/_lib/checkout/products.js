/**
 * Self-service app registry. Not a route.
 *
 * Adding an app (full checklist in CONVENTIONS.md, "Self-service apps"):
 *   1. A product module in ./products/<slug>.js exporting the shape below.
 *   2. Its pages: /<slug> (product, indexed), /<slug>/order, /<slug>/thank-you (noindex).
 *   3. A card on the hub page /self-service, plus sitemap.xml and llms.txt entries.
 *
 * Product module shape:
 *   id           product slug, also the page slug ("m365-security-assessment")
 *   name         shown on the payment page and receipts
 *   amount       "2500.00" (string, two decimals; the only price the checkout charges)
 *   orderPrefix  2-8 chars [A-Z0-9], unique per app; order ids are PREFIX-YYMMDD-XXXX
 *   pages        { product, order, thankYou } root-relative paths
 *   intake(input, ctx)          order-form POST -> { ok:true, record, email } | { ok:false, field, message }
 *   buildOrder(record, payment, ctx)  -> the hand-off payload once payment is verified
 *   schema       JSON Schema the payload must satisfy before the hand-off
 *   handoff      { type: "github-issue", repo, tokenEnv, titlePrefix, title(order), body(order) }
 */
import m365SecurityAssessment from "./products/m365-security-assessment.js";

const LIST = [m365SecurityAssessment];

export const PRODUCTS = Object.freeze(Object.fromEntries(LIST.map((p) => [p.id, p])));

export function productById(id) {
  return typeof id === "string" && Object.prototype.hasOwnProperty.call(PRODUCTS, id) ? PRODUCTS[id] : null;
}

export function productByOrderId(orderId) {
  const m = /^([A-Z0-9]{2,8})-[0-9]{6}-[A-Z0-9]{4}$/.exec(String(orderId || ""));
  return (m && LIST.find((p) => p.orderPrefix === m[1])) || null;
}
