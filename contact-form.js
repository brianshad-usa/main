/*
 * contact-form.js — shared handler for every Pro Link Systems lead form.
 * -----------------------------------------------------------------------------
 * Loaded on all form pages except contact.html (which has its own inline
 * handler). It replaces the retired EmailJS + Web3Forms client path.
 *
 * How it overrides each page's old inline handler without editing it:
 *   - It listens for "submit" on `document` in the CAPTURE phase, so it runs
 *     BEFORE the form's own (bubble-phase) listener, then calls
 *     preventDefault() + stopImmediatePropagation() to stop the old handler.
 *   - It only acts on forms that contain a `.cf-turnstile` widget, so other
 *     forms on the page are untouched.
 *
 * Fields are posted as-is; the /api/contact Function normalizes the varied
 * per-page names (name / firm_name / firm_size, honeypot botcheck|challenge).
 *
 * 2026-11-09 (lead-drop fixes): only name + email are required (phone was
 * required); waits up to 8 s for the Turnstile token instead of alerting a
 * fast typist; attaches first-touch attribution (landing page, referrer, UTMs,
 * gclid/msclkid) so every lead email says how the visitor found us; reports
 * every attempt/failure to GA4 (form_submit_attempt / form_error) so a silent
 * drop in leads is visible within days.
 */
(function () {
  var FT_KEY = "pls_first_touch";
  var ATTR = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "msclkid"];

  // First touch for this browser session: the page they landed on and where from.
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
  firstTouch();

  function track(name, params) {
    try { if (typeof gtag === "function") gtag("event", name, params || {}); } catch (e) {}
  }

  function isOurForm(form) {
    return form && form.tagName === "FORM" && form.querySelector && form.querySelector(".cf-turnstile");
  }

  function submitBtn(form) {
    return form.querySelector('button[type="submit"], input[type="submit"], button:not([type])');
  }

  function setError(msg) { window.alert(msg); }

  function showSuccess(form, ref, firstName) {
    var body = document.querySelector(".form-body");
    var ok = document.querySelector(".form-success");
    var nameEl = document.querySelector("#success-name, #successName, [data-success-name]");
    var refEl = document.querySelector("#success-ref, #successRef, [data-success-ref]");
    if (nameEl && firstName) nameEl.textContent = firstName;
    if (refEl && ref) refEl.textContent = ref;
    if (body) body.classList.add("hide");
    if (ok) { ok.classList.add("show"); try { ok.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (e) {} }
    if (!body && !ok) { form.reset(); setError("Thank you — your inquiry has been received (Ref " + ref + "). We'll be in touch within one business day."); }
  }

  // The Turnstile widget may still be working when a fast visitor presses Send.
  function waitForToken(form, cb) {
    var waited = 0;
    (function poll() {
      var el = form.querySelector('[name="cf-turnstile-response"]');
      var tok = el && el.value;
      if (tok || waited >= 8000) return cb(tok || "");
      waited += 250; setTimeout(poll, 250);
    })();
  }

  function handle(form) {
    var btn = submitBtn(form);
    var page = (form.querySelector('[name="source_page"]') || {}).value || location.pathname.replace(/^\//, "") || "home";
    var data = Object.fromEntries(new FormData(form));

    var email = String(data.email || "").trim();
    var firstName = String(data.first_name || data.name || "").trim();
    track("form_submit_attempt", { form_page: page });
    if (!firstName || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      track("form_error", { form_page: page, reason: "validation" });
      setError("Please enter your name and a valid email address, then try again.");
      return;
    }

    if (btn) { btn.disabled = true; btn.classList.add("loading"); }

    waitForToken(form, function (token) {
      if (!token) {
        if (btn) { btn.disabled = false; btn.classList.remove("loading"); }
        track("form_error", { form_page: page, reason: "turnstile_missing" });
        setError('Please complete the "I\'m not a robot" check, then send again. (If it won\'t load, call 1-800-890-6133 or email info@prolinksystems.com.)');
        return;
      }
      data["cf-turnstile-response"] = token;

      // Attribution (first touch this session + this form's page).
      var ft = firstTouch();
      Object.keys(ft).forEach(function (k) { if (!data[k]) data[k] = ft[k]; });
      data.source_page = data.source_page || page;
      data.page_url = location.origin + location.pathname;
      data.referrer = document.referrer || "";

      fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify(data)
      })
        .then(function (res) { return res.json().then(function (j) { return { ok: res.ok, status: res.status, json: j }; }); })
        .then(function (r) {
          if (r.ok && r.json && r.json.success) {
            if (typeof gtag === "function") {
              // Enhanced Conversions: supply first-party lead data (gtag hashes it
              // client-side before sending) so Google can match cookieless conversions.
              var ph = String(data.phone || "").replace(/[^0-9]/g, "");
              if (ph.length === 10) ph = "1" + ph;
              gtag("set", "user_data", {
                email: email.toLowerCase(),
                phone_number: ph ? ("+" + ph) : undefined,
                address: {
                  first_name: firstName,
                  last_name: String(data.last_name || "").trim()
                }
              });
              gtag("event", "conversion", { send_to: "AW-1068497497/yYS5CNKQkbccENn0v_0D", value: 50.0, currency: "USD" });
            }
            window.uetq = window.uetq || [];
            window.uetq.push('event', 'submit_lead_form', {});
            if (typeof gtag === "function") { gtag("event", "generate_lead", { method: "contact_form", form_page: page }); }
            showSuccess(form, r.json.refNumber, firstName.split(" ")[0]);
          } else {
            if (btn) { btn.disabled = false; btn.classList.remove("loading"); }
            if (window.turnstile) { try { turnstile.reset(); } catch (e) {} }
            track("form_error", { form_page: page, reason: "server_" + (r.status || "x") });
            setError((r.json && r.json.message) || "There was a problem sending your message. Please call 1-800-890-6133 or email info@prolinksystems.com.");
          }
        })
        .catch(function () {
          if (btn) { btn.disabled = false; btn.classList.remove("loading"); }
          if (window.turnstile) { try { turnstile.reset(); } catch (e) {} }
          track("form_error", { form_page: page, reason: "network" });
          setError("There was a problem sending your message. Please call 1-800-890-6133 or email info@prolinksystems.com.");
        });
    });
  }

  // Capture-phase, at document: runs before the form's own submit listener and
  // stops it, so the retired inline EmailJS/Web3Forms handler never executes.
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!isOurForm(form)) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    handle(form);
  }, true);
})();
