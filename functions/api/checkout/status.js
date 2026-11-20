/**
 * GET /api/checkout/status?order=<id>  --  for the apps' thank-you pages
 * -----------------------------------------------------------------------------
 * { status: "paid" | "pending" | "unknown", test?: true }. No customer details.
 * The thank-you page shows "confirmed" and fires the purchase conversion only once
 * the webhook has verified the payment ("paid"), so a visit to a thank-you URL can't
 * inflate conversions, and sandbox orders (test: true) never count.
 */
import { json, getOrder } from "../../_lib/checkout/core.js";
import { productByOrderId } from "../../_lib/checkout/products.js";

export async function onRequestGet({ request, env }) {
  const id = new URL(request.url).searchParams.get("order") || "";
  if (!productByOrderId(id) || !env.ORDERS) return json(200, { status: "unknown" });
  let rec = null;
  try { rec = await getOrder(env, id); } catch (e) { rec = null; }
  if (!rec) return json(200, { status: "unknown" });
  const out = { status: rec.status === "paid" ? "paid" : "pending" };
  if (rec.mode === "sandbox") out.test = true;
  return json(200, out);
}

export async function onRequest(context) {
  if (context.request.method === "GET") return onRequestGet(context);
  return json(405, { status: "unknown" });
}
