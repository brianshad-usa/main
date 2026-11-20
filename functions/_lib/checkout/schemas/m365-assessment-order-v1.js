// Order contract (website -> assessment agent): copied VERBATIM from brianshad-usa/m365-security-agent,
// config/order-schema.json. Keep it in sync -- when the agent's schema changes, replace the object below
// with that file's contents (unknown fields make the agent reject an order). The checkout validates every
// order against it before the hand-off. A JS module rather than a .json import so the same file loads in
// Cloudflare's Functions bundler and in Node tests.
export default {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://prolinksystems.com/schemas/m365-assessment-order/v1",
  "title": "Pro Link M365 Security Assessment order (website -> agent)",
  "description": "Sent by the prolinksystems.com checkout ONLY after Authorize.net confirmed the payment. Shared contract: the website validates against this file before creating the order issue; the agent validates again on intake. Never include card data, passwords or tokens.",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema", "order_id", "placed_at", "product", "company", "contact", "access_method", "payment", "authorization"],
  "properties": {
    "schema": {"const": "prolink.m365-assessment-order/v1"},
    "order_id": {"type": "string", "pattern": "^M365-[0-9]{6}-[A-Z0-9]{4}$", "description": "M365-YYMMDD-XXXX; also used as the Authorize.net invoiceNumber (max 20 chars)"},
    "placed_at": {"type": "string", "format": "date-time"},
    "product": {"const": "m365-security-assessment"},
    "company": {
      "type": "object",
      "additionalProperties": false,
      "required": ["name", "domain"],
      "properties": {
        "name": {"type": "string", "minLength": 2, "maxLength": 120},
        "domain": {"type": "string", "pattern": "^(?=.{4,253}$)([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\\.)+[A-Za-z]{2,63}$", "description": "The company's Microsoft 365 email domain, e.g. acme.com"},
        "employees": {"type": "string", "enum": ["1-10", "11-25", "26-50", "51-100", "101-250", "251-500", "500+"]},
        "phone": {"type": "string", "maxLength": 40}
      }
    },
    "contact": {
      "type": "object",
      "additionalProperties": false,
      "required": ["name", "email"],
      "description": "The purchaser; receives the order confirmation and the report.",
      "properties": {
        "name": {"type": "string", "minLength": 2, "maxLength": 120},
        "title": {"type": "string", "maxLength": 120},
        "email": {"type": "string", "maxLength": 254, "pattern": "^[^@\\s<>\"']+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,63}$"},
        "phone": {"type": "string", "maxLength": 40}
      }
    },
    "technical_contact": {
      "type": "object",
      "additionalProperties": false,
      "required": ["name", "email"],
      "description": "Optional: the Microsoft 365 Global Administrator who will approve read-only access (gets the setup email; the purchaser is copied).",
      "properties": {
        "name": {"type": "string", "minLength": 2, "maxLength": 120},
        "email": {"type": "string", "maxLength": 254, "pattern": "^[^@\\s<>\"']+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,63}$"}
      }
    },
    "access_method": {"const": "prolink_app", "description": "Access is always app consent: website orders use Pro Link's read-only app (fully automated). Pro Link never asks for a user account or password."},
    "payment": {
      "type": "object",
      "additionalProperties": false,
      "required": ["processor", "transaction_id", "amount", "currency", "status"],
      "properties": {
        "processor": {"const": "authorize.net"},
        "transaction_id": {"type": "string", "pattern": "^[0-9]{1,20}$"},
        "amount": {"type": "string", "pattern": "^[0-9]+\\.[0-9]{2}$"},
        "currency": {"const": "USD"},
        "status": {"const": "captured"},
        "verified_at": {"type": "string", "format": "date-time"},
        "card_last4": {"type": "string", "pattern": "^[0-9]{4}$"}
      }
    },
    "authorization": {
      "type": "object",
      "additionalProperties": false,
      "required": ["accepted", "terms_version", "accepted_at", "signer_name"],
      "description": "The client's authorization for Pro Link to perform a read-only assessment of their tenant.",
      "properties": {
        "accepted": {"const": true},
        "terms_version": {"type": "string", "maxLength": 40},
        "accepted_at": {"type": "string", "format": "date-time"},
        "signer_name": {"type": "string", "minLength": 2, "maxLength": 120},
        "signer_title": {"type": "string", "maxLength": 120},
        "ip": {"type": "string", "maxLength": 45}
      }
    },
    "test": {"type": "boolean", "description": "true for Authorize.net SANDBOX orders: the agent validates the order and replies on the issue, but registers nothing and emails no one"},
    "pre_call_requested": {"type": "boolean"},
    "notes": {"type": "string", "maxLength": 1000},
    "source": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "page": {"type": "string", "maxLength": 200},
        "utm_source": {"type": "string", "maxLength": 100},
        "utm_medium": {"type": "string", "maxLength": 100},
        "utm_campaign": {"type": "string", "maxLength": 100},
        "gclid": {"type": "string", "maxLength": 200}
      }
    }
  }
};
