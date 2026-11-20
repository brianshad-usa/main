/* /assets/apps/checkout.js -- shared script for Pro Link's self-service app pages.
 * Load with a ?v=YYYYMMDD cache-buster and bump it on every change (browsers keep JS 24 h + 7 d).
 *
 *  - Every app page: records the session's first touch (same sessionStorage key and format as
 *    /contact-form.js), so a paid order carries the landing page, UTMs and gclid.
 *  - Order page:  <form data-checkout-product="<slug>" data-value="2500" data-currency="USD"> with a
 *    Turnstile widget, [data-checkout-error] and optional [data-checkout-cancelled] / [data-counter-for].
 *    Submits to /api/checkout/start, then shows Authorize.net's hosted payment form INSIDE the page:
 *    a payment step (built below the form) whose iframe the token is posted into. Authorize.net talks
 *    back (resize, cancel) through the same-origin relay page /assets/apps/anet-communicator. While
 *    the payment step is open the page polls /api/checkout/status and moves on to the thank-you page
 *    once the webhook has verified the payment. "Open it full-window" posts the same token to
 *    Authorize.net's page instead (fallback); data-checkout-display="redirect" on the form always does.
 *  - Thank-you page: <div data-checkout-thankyou data-value data-currency data-item-id data-item-name
 *    data-ads-send-to> with [data-state="checking|paid|pending|unknown|invalid"] panels and
 *    [data-order-id] slots. The purchase conversion fires ONLY after /api/checkout/status says the
 *    webhook verified the payment, once per order, and never for sandbox (test) orders.
 *  - One of our pages loaded INSIDE the payment iframe (the receipt's "Continue" or "Cancel") reloads
 *    itself in the top window.
 */
(function () {
  "use strict";

  if (window.top !== window.self) {
    try {
      if (window.top.location.origin === window.location.origin) {
        window.top.location.replace(window.location.href);
        return;
      }
    } catch (e) { /* framed by another site: carry on */ }
  }

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
  function postToken(url, token, target) {
    var f = document.createElement("form");
    f.method = "POST";
    f.action = url;
    if (target) f.target = target;
    f.style.display = "none";
    var i = document.createElement("input");
    i.type = "hidden";
    i.name = "token";
    i.value = token;
    f.appendChild(i);
    document.body.appendChild(f);
    f.submit();
    setTimeout(function () { if (f.parentNode) f.parentNode.removeChild(f); }, 1000);
  }

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
    var embed = form.getAttribute("data-checkout-display") !== "redirect";
    var errorBox = form.querySelector("[data-checkout-error]");
    var button = form.querySelector('button[type="submit"]');
    var buttonHtml = button ? button.innerHTML : "";
    var busy = false;
    var pay = null;                          // the open payment step: { id, returnUrl, token, postUrl, ... }
    var ui = embed ? paymentStep() : null;

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

    // Back button from Authorize.net's page or the thank-you page: back to a usable form.
    window.addEventListener("pageshow", function (e) {
      if (!e.persisted) return;
      if (pay || (ui && !ui.root.hidden)) closePayment(false);
      setBusy(false);
      resetTurnstile();
    });

    form.addEventListener("input", function (e) {
      if (e.target && e.target.getAttribute("aria-invalid") === "true") e.target.removeAttribute("aria-invalid");
    });

    // Billing name defaults to the contact's name (still editable).
    var contactName = form.querySelector('[name="contact_name"]');
    var billFirst = form.querySelector('[name="bill_first_name"]');
    var billLast = form.querySelector('[name="bill_last_name"]');
    if (contactName && billFirst && billLast) {
      contactName.addEventListener("change", function () {
        if (billFirst.value || billLast.value) return;
        var parts = contactName.value.trim().split(/\s+/);
        if (parts.length < 2) return;
        billLast.value = parts.pop();
        billFirst.value = parts.join(" ");
      });
    }

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
            if (ui) openPayment(j); else postToken(j.post_url, j.full_token || j.token);
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

    // ---- embedded payment step
    function paymentStep() {
      var root = document.createElement("section");
      root.className = "pay-step";
      root.hidden = true;
      root.setAttribute("aria-labelledby", "pay-step-title");
      root.innerHTML =
        '<div class="pay-step-head"><h2 id="pay-step-title" tabindex="-1">Payment</h2>' +
        '<p class="pay-step-lock"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>Secure payment by Authorize.net</p></div>' +
        '<p class="pay-step-note">Enter your card below. Card details go straight to Authorize.net; Pro Link never sees them.</p>' +
        '<div class="checkout-alert checkout-alert--info" data-pay-expired hidden>This payment session has timed out. If you already paid, your confirmation opens in a moment. Otherwise, <button type="button" class="pay-link pay-link--inline" data-pay-restart>start again</button>.</div>' +
        '<div class="pay-frame-wrap"><div class="pay-frame-loading" data-pay-loading><span class="app-spinner" aria-hidden="true"></span><span data-pay-loading-text>Loading the secure payment form&hellip;</span></div>' +
        '<iframe class="pay-frame" name="pls-anet-payment" title="Secure card payment form from Authorize.net" scrolling="no"></iframe></div>' +
        '<div class="pay-step-actions"><button type="button" class="pay-link" data-pay-back>&larr; Back to your details</button>' +
        '<button type="button" class="pay-link" data-pay-full>Payment form not loading? Open it full-window</button></div>';
      form.parentNode.insertBefore(root, form.nextSibling);
      var step = {
        root: root,
        title: root.querySelector("#pay-step-title"),
        frame: root.querySelector("iframe"),
        loading: root.querySelector("[data-pay-loading]"),
        loadingText: root.querySelector("[data-pay-loading-text]"),
        expired: root.querySelector("[data-pay-expired]"),
        posted: false
      };
      // The iframe never scrolls (scrolling="no", like Authorize.net's sample app): it takes the height
      // the form reports in resizeWindow messages. If none arrives within 6 s of the form loading, it
      // grows to a height the whole card form fits in, so nothing is ever cut off.
      // The empty iframe's own first "load" fires now, long before any token is posted.
      step.frame.addEventListener("load", function () {
        if (!step.posted) return;
        step.loading.hidden = true;
        var p = pay;
        if (p && !p.resized) {
          clearTimeout(p.noResize);
          p.noResize = setTimeout(function () {
            if (pay !== p || p.resized || p.done) return;
            step.frame.style.height = (window.innerWidth < 700 ? 1100 : 900) + "px";
            try { console.info("[checkout] no size message from the payment form; using the fallback height"); } catch (e) {}
            ga("event", "checkout_frame_noresize", { product: product });
          }, 6000);
        }
      });
      root.querySelector("[data-pay-back]").addEventListener("click", function () { closePayment(false); });
      root.querySelector("[data-pay-restart]").addEventListener("click", function () { closePayment(false); });
      root.querySelector("[data-pay-full]").addEventListener("click", fullWindow);

      // Messages from Authorize.net, relayed by /assets/apps/anet-communicator or (fallback) posted
      // straight to this page. UI hints only: the webhook + status poll decide whether an order is paid.
      window.addEventListener("message", function (e) {
        if (!e || !/^https:\/\/(accept|test)\.authorize\.net$/.test(e.origin)) return;
        if (typeof e.data === "string" && e.data.indexOf("action=") === 0) window.AuthorizeNetIFrame.onReceiveCommunication(e.data);
      });
      window.AuthorizeNetIFrame = {
        onReceiveCommunication: function (str) {
          if (!pay) return;
          var m = parseMsg(str);
          step.root.setAttribute("data-frame-messages", String((Number(step.root.getAttribute("data-frame-messages")) || 0) + 1));
          if (m.action === "resizeWindow") {
            var h = parseInt(m.height, 10);
            if (h > 0 && h < 5000) {
              pay.resized = true;
              clearTimeout(pay.noResize);
              step.frame.style.height = Math.max(h + 16, 300) + "px";        // a little room: no clipping
              try { console.info("[checkout] payment form size " + m.width + "x" + h); } catch (e) {}
            }
          } else if (m.action === "cancel") {
            ga("event", "checkout_cancel", { product: product });
            closePayment(true);
          } else if (m.action === "transactResponse") {
            // The embedded form shows no receipt: on success go straight to our thank-you page, which
            // waits for the webhook-verified status. Declines stay in the form (it shows the error).
            var r = null;
            var at = String(str).indexOf("response=");         // the JSON is the last parameter
            var raw = at >= 0 ? String(str).slice(at + 9) : "";
            try { raw = decodeURIComponent(raw); } catch (e) {}
            try { r = JSON.parse(raw || "null"); } catch (e) {}
            if (r && String(r.responseCode) === "1") goToThankYou(pay);
            else pollNow();
          }
        }
      };
      return step;
    }

    function openPayment(j) {
      pay = {
        id: j.order_id, returnUrl: j.return_url || "", token: j.token, fullToken: j.full_token || "", postUrl: j.post_url,
        started: Date.now(), timer: null, expiry: null, slow: null, noResize: null, resized: false, done: false
      };
      form.hidden = true;
      if (cancelled) cancelled.hidden = true;
      ui.expired.hidden = true;
      ui.root.removeAttribute("data-frame-messages");
      ui.loading.hidden = false;
      ui.loadingText.innerHTML = "Loading the secure payment form&hellip;";
      ui.frame.style.height = "";
      ui.root.hidden = false;
      setBusy(false);
      ui.posted = true;
      postToken(j.post_url, j.token, ui.frame.name);
      try { ui.root.scrollIntoView({ block: "start", behavior: "smooth" }); } catch (e) {}
      try { ui.title.focus({ preventScroll: true }); } catch (e) {}
      pay.slow = setTimeout(function () {
        if (!ui.loading.hidden) ui.loadingText.innerHTML = "Still loading&hellip; If nothing appears, use &ldquo;Open it full-window&rdquo; below.";
      }, 12000);
      pay.expiry = setTimeout(function () { if (pay && !pay.done) ui.expired.hidden = false; }, 15 * 60 * 1000);
      pay.timer = setTimeout(pollPaid, 5000);
    }

    function pollPaid() {
      var p = pay;
      if (!p || p.done) return;
      if (Date.now() - p.started > 20 * 60 * 1000) return;            // the token is long dead
      fetch("/api/checkout/status?order=" + encodeURIComponent(p.id), { cache: "no-store" })
        .then(function (r) { return r.json(); })
        .then(function (s) {
          if (pay !== p || p.done) return;
          if (s && s.status === "paid") { goToThankYou(p); return; }
          p.timer = setTimeout(pollPaid, 4000);
        })
        .catch(function () { if (pay === p && !p.done) p.timer = setTimeout(pollPaid, 6000); });
    }
    function goToThankYou(p) {
      if (!p || p.done) return;
      p.done = true;
      clearTimers(p);
      location.href = p.returnUrl || ("/" + product + "/thank-you?order=" + encodeURIComponent(p.id));
    }
    function pollNow() {
      if (!pay || pay.done) return;
      clearTimeout(pay.timer);
      pollPaid();
    }
    function clearTimers(p) { clearTimeout(p.timer); clearTimeout(p.expiry); clearTimeout(p.slow); clearTimeout(p.noResize); }

    function closePayment(showCancelled) {
      if (pay) { pay.done = true; clearTimers(pay); }
      pay = null;
      if (ui) {
        ui.posted = false;
        ui.root.hidden = true;
        try { ui.frame.src = "about:blank"; } catch (e) {}
      }
      form.hidden = false;
      if (cancelled && showCancelled) cancelled.hidden = false;
      setBusy(false);
      resetTurnstile();            // a new attempt needs a new token (and makes a new order)
      try { form.scrollIntoView({ block: "start", behavior: "smooth" }); } catch (e) {}
    }

    function fullWindow() {
      if (!pay) return;
      var p = pay;
      p.done = true;
      clearTimers(p);
      ga("event", "checkout_fullwindow", { product: product });
      postToken(p.postUrl, p.fullToken || p.token);            // the full-window session shows a receipt
    }

    function parseMsg(str) {
      var out = {};
      String(str || "").split("&").forEach(function (part) {
        var i = part.indexOf("=");
        if (i > 0) {
          var v = part.slice(i + 1);
          try { v = decodeURIComponent(v); } catch (e) {}
          out[part.slice(0, i)] = v;
        }
      });
      return out;
    }

    // ---- form helpers
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
