/* /assets/apps/checkout.js -- shared script for Pro Link's self-service app pages.
 * Load with a ?v=YYYYMMDD cache-buster and bump it on every change (browsers keep JS 24 h + 7 d).
 *
 *  - Every app page: records the session's first touch (same sessionStorage key and format as
 *    /contact-form.js), so a paid order carries the landing page, UTMs and gclid.
 *  - Order page:  <form data-checkout-product="<slug>" data-value="2500" data-currency="USD"> with a
 *    Turnstile widget, [data-checkout-error] and optional [data-checkout-cancelled] / [data-counter-for].
 *    Submits to /api/checkout/start, then posts the returned token to Authorize.net's hosted page.
 *  - Thank-you page: <div data-checkout-thankyou data-value data-currency data-item-id data-item-name
 *    data-ads-send-to> with [data-state="checking|paid|pending|unknown|invalid"] panels and
 *    [data-order-id] slots. The purchase conversion fires ONLY after /api/checkout/status says the
 *    webhook verified the payment, once per order, and never for sandbox (test) orders.
 */
(function () {
  "use strict";

  var FT_KEY = "pls_first_touch";
  var ATTR = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "msclkid"];
  var ID_RE = /^[A-Z0-9]{2,8}-[0-9]{6}-[A-Z0-9]{4}$/;
  var PHONE = "1-800-890-6133";

  function firstTouch() {
    var ft = null;
    try { ft = JSON.parse(sessionStorage.getItem(FT_KEY) || "null"); } catch (e) {}
    if (!ft) {
      ft = { landing_page: location.pathname + location.search, first_referrer: document.referrer || "" };
      try {
        var q = new URLSearchParams(location.search);
        ATTR.forEach(function (k) { if (q.get(k)) ft[k] = q.get(k); });
      } catch (e) {}
      try { sessionStorage.setItem(FT_KEY, JSON.stringify(ft)); } catch (e) {}
    }
    return ft;
  }
  var ft = firstTouch();

  function ga() {
    if (typeof window.gtag === "function") { try { window.gtag.apply(window, arguments); } catch (e) {} }
  }
  function uet(name, data) {
    try { window.uetq = window.uetq || []; window.uetq.push("event", name, data || {}); } catch (e) {}
  }
  function each(list, fn) { Array.prototype.forEach.call(list, fn); }

  // "Talk to us first" / "Book a call" links (<a data-bookings-link="<slug>">) open the app's Bookings
  // page in a new tab; count the clicks in GA4 per app.
  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("[data-bookings-link]") : null;
    if (a) ga("event", "book_call_click", { product: a.getAttribute("data-bookings-link") || "" });
  });

  var form = document.querySelector("form[data-checkout-product]");
  if (form) orderForm(form);
  var ty = document.querySelector("[data-checkout-thankyou]");
  if (ty) thankYou(ty);

  // ------------------------------------------------------------------ order form
  function orderForm(form) {
    var product = form.getAttribute("data-checkout-product");
    var value = Number(form.getAttribute("data-value")) || 0;
    var currency = form.getAttribute("data-currency") || "USD";
    var errorBox = form.querySelector("[data-checkout-error]");
    var button = form.querySelector('button[type="submit"]');
    var buttonHtml = button ? button.innerHTML : "";
    var busy = false;

    var cancelled = document.querySelector("[data-checkout-cancelled]");
    try { if (cancelled && new URLSearchParams(location.search).get("cancelled")) cancelled.hidden = false; } catch (e) {}

    each(form.querySelectorAll("[data-counter-for]"), function (c) {
      var t = form.querySelector('[name="' + c.getAttribute("data-counter-for") + '"]');
      if (!t) return;
      var max = Number(t.getAttribute("maxlength")) || 0;
      var update = function () { c.textContent = t.value.length + " / " + max; };
      t.addEventListener("input", update);
      update();
    });

    // Back button from the payment page: re-enable the form and get a fresh Turnstile token.
    window.addEventListener("pageshow", function (e) { if (e.persisted) { setBusy(false); resetTurnstile(); } });

    form.addEventListener("input", function (e) {
      if (e.target && e.target.getAttribute("aria-invalid") === "true") e.target.removeAttribute("aria-invalid");
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (busy) return;
      showError("");
      if (!form.checkValidity()) { form.reportValidity(); return; }
      setBusy(true);
      waitForToken(8000).then(function (token) {
        if (!token) {
          setBusy(false);
          showError("Please complete the security check above, then continue.");
          ga("event", "checkout_error", { reason: "turnstile_missing", product: product });
          return null;
        }
        var data = collect();
        data.product = product;
        data["cf-turnstile-response"] = token;
        data.source = source();
        return fetch("/api/checkout/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data)
        }).then(function (r) {
          return r.json().catch(function () { return {}; }).then(function (j) { return { status: r.status, j: j || {} }; });
        }).then(function (res) {
          var j = res.j;
          if (j.ok && j.token && j.post_url) {
            ga("event", "begin_checkout", {
              currency: currency, value: value,
              items: [{ item_id: product, price: value, quantity: 1 }]
            });
            toPayment(j.post_url, j.token);
            return;
          }
          resetTurnstile();      // tokens are single-use; the next attempt needs a new one
          setBusy(false);
          showError(j.message || ("Something went wrong. Please try again, or call " + PHONE + "."));
          if (j.field) markField(j.field);
          ga("event", "checkout_error", { reason: j.field || ("server_" + res.status), product: product });
        });
      }).catch(function () {
        resetTurnstile();
        setBusy(false);
        showError("We couldn't reach our server. Check your connection and try again, or call " + PHONE + ".");
        ga("event", "checkout_error", { reason: "network", product: product });
      });
    });

    function collect() {
      var out = {};
      each(form.elements, function (el) {
        if (!el.name || el.disabled || el.name === "cf-turnstile-response") return;
        if (el.type === "checkbox") out[el.name] = el.checked;
        else if (el.type === "radio") { if (el.checked) out[el.name] = el.value; }
        else if (el.tagName !== "BUTTON") out[el.name] = el.value;
      });
      return out;
    }
    function source() {
      var s = {};
      if (ft && ft.landing_page) s.page = ft.landing_page;
      ["utm_source", "utm_medium", "utm_campaign", "gclid"].forEach(function (k) { if (ft && ft[k]) s[k] = ft[k]; });
      return s;
    }
    function toPayment(url, token) {
      var f = document.createElement("form");
      f.method = "POST";
      f.action = url;
      f.style.display = "none";
      var i = document.createElement("input");
      i.type = "hidden";
      i.name = "token";
      i.value = token;
      f.appendChild(i);
      document.body.appendChild(f);
      f.submit();
    }
    function waitForToken(ms) {
      return new Promise(function (resolve) {
        var t0 = Date.now();
        (function poll() {
          var el = form.querySelector('[name="cf-turnstile-response"]');
          if (el && el.value) return resolve(el.value);
          if (Date.now() - t0 > ms) return resolve("");
          setTimeout(poll, 250);
        })();
      });
    }
    function resetTurnstile() { try { if (window.turnstile) window.turnstile.reset(); } catch (e) {} }
    function setBusy(b) {
      busy = b;
      if (!button) return;
      button.disabled = b;
      button.innerHTML = b ? "Starting secure payment&hellip;" : buttonHtml;
    }
    function showError(msg) {
      if (!errorBox) return;
      errorBox.textContent = msg;
      errorBox.hidden = !msg;
      if (msg) { try { errorBox.scrollIntoView({ block: "center", behavior: "smooth" }); } catch (e) {} }
    }
    function markField(name) {
      var el = form.querySelector('[name="' + name + '"]');
      if (el) { el.setAttribute("aria-invalid", "true"); try { el.focus(); } catch (e) {} }
    }
  }

  // ------------------------------------------------------------------ thank-you page
  function thankYou(root) {
    var id = "";
    try { id = (new URLSearchParams(location.search).get("order") || "").trim().toUpperCase(); } catch (e) {}
    var value = Number(root.getAttribute("data-value")) || 0;
    var currency = root.getAttribute("data-currency") || "USD";
    each(root.querySelectorAll("[data-order-id]"), function (el) { el.textContent = id; });
    if (!ID_RE.test(id)) { show("invalid"); return; }
    show("checking");

    var tries = 0;
    var MAX = 20;            // ~60 s; Authorize.net's webhook usually lands within seconds
    (function poll() {
      fetch("/api/checkout/status?order=" + encodeURIComponent(id), { cache: "no-store" })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (j && j.status === "paid") { show("paid"); if (!j.test) conversion(); return; }
          if (++tries >= MAX) { show(j && j.status === "unknown" ? "unknown" : "pending"); return; }
          setTimeout(poll, 3000);
        })
        .catch(function () {
          if (++tries >= MAX) { show("pending"); return; }
          setTimeout(poll, 3000);
        });
    })();

    function show(state) {
      each(root.querySelectorAll("[data-state]"), function (el) { el.hidden = el.getAttribute("data-state") !== state; });
    }
    function conversion() {
      var key = "pls_purchase_" + id;
      try { if (localStorage.getItem(key)) return; localStorage.setItem(key, "1"); } catch (e) {}
      var item = { item_id: root.getAttribute("data-item-id"), item_name: root.getAttribute("data-item-name"), price: value, quantity: 1 };
      ga("event", "purchase", { transaction_id: id, value: value, currency: currency, items: [item] });
      var sendTo = root.getAttribute("data-ads-send-to");
      if (sendTo) ga("event", "conversion", { send_to: sendTo, value: value, currency: currency, transaction_id: id });
      uet("purchase", { revenue_value: value, currency: currency });
    }
  }
})();
