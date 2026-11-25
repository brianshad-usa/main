/*
 * lead-form-ux.js: inline validation and accessible messages for the Ads landing-page lead forms.
 * Opt-in: only forms marked data-ux="lead" (managed-it-services, co-managed-it-services). Every other page is untouched.
 *
 * Loaded BEFORE /contact-form.js. Both listen for "submit" on document in the capture phase, so this runs first:
 *   - name or email missing / invalid: shows each field's message, marks it aria-invalid, focuses the first problem
 *     and stops the submit (contact-form.js would otherwise show a browser alert). The same GA4 events contact-form.js
 *     sends for a failed attempt (form_submit_attempt, form_error) are sent here, so reporting does not change.
 *   - valid: does nothing; contact-form.js sends the form exactly as before (endpoint, Turnstile, attribution).
 * contact-form.js's remaining messages (verification check, server errors) are rendered inline through
 * window.plsFormError, and focus moves to the confirmation when it appears.
 */
(function () {
  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function isLead(form) { return form && form.getAttribute && form.getAttribute("data-ux") === "lead"; }
  function group(el) { return el && el.closest ? el.closest(".form-group") : null; }
  function page() { return location.pathname.replace(/^\//, "") || "home"; }
  function track(name, params) { try { if (typeof gtag === "function") gtag("event", name, params || {}); } catch (e) {} }

  function setInvalid(el, bad) {
    var g = group(el);
    if (!g) return;
    g.classList.toggle("has-error", !!bad);
    if (bad) el.setAttribute("aria-invalid", "true"); else el.removeAttribute("aria-invalid");
  }

  function nameField(form) { return form.querySelector('[name="name"], [name="first_name"]'); }
  function emailOk(el) { return EMAIL.test(String(el.value || "").trim()); }

  function check(form) {
    var bad = [];
    var n = nameField(form), e = form.querySelector('[name="email"]');
    if (n) { var nb = !String(n.value || "").trim(); setInvalid(n, nb); if (nb) bad.push(n); }
    if (e) { var eb = !emailOk(e); setInvalid(e, eb); if (eb) bad.push(e); }
    return bad;
  }

  function alertBox(form) {
    var card = (form.closest && form.closest(".pl-formcard, .form-card")) || form.parentNode;
    return card ? card.querySelector(".lf-alert") : null;
  }
  function showAlert(form, msg) {
    var box = alertBox(form);
    if (!box) return false;
    box.textContent = msg;
    box.hidden = false;
    box.setAttribute("tabindex", "-1");
    try { box.focus(); } catch (e) {}
    return true;
  }
  function hideAlert(form) {
    var box = alertBox(form);
    if (box) { box.hidden = true; box.textContent = ""; }
  }

  document.addEventListener("submit", function (ev) {
    var form = ev.target;
    if (!isLead(form)) return;
    hideAlert(form);
    var bad = check(form);
    if (!bad.length) return;                       // valid: contact-form.js takes it from here
    ev.preventDefault();
    ev.stopImmediatePropagation();
    track("form_submit_attempt", { form_page: page() });
    track("form_error", { form_page: page(), reason: "validation" });
    showAlert(form, bad.length > 1 ? "Please check the two highlighted fields." : "Please check the highlighted field.");
    bad[0].focus();
  }, true);

  // Once a field has shown an error, re-check it as the visitor types; check the email format when they leave it.
  document.addEventListener("input", function (ev) {
    var el = ev.target, g = group(el);
    if (!g || !g.classList.contains("has-error") || !isLead(el.form)) return;
    if (el.name === "email") setInvalid(el, !emailOk(el));
    else if (el.name === "name" || el.name === "first_name") setInvalid(el, !String(el.value || "").trim());
  });
  document.addEventListener("focusout", function (ev) {
    var el = ev.target;
    if (el && el.name === "email" && isLead(el.form) && String(el.value || "").trim()) setInvalid(el, !emailOk(el));
  });

  // Messages contact-form.js would show in a browser alert: verification check and server errors.
  window.plsFormError = function (msg) {
    var form = document.querySelector('form[data-ux="lead"]');
    return form ? showAlert(form, msg) : false;
  };

  // Move focus to the confirmation heading when contact-form.js reveals it.
  [].slice.call(document.querySelectorAll('form[data-ux="lead"]')).forEach(function (form) {
    var card = form.closest && form.closest(".pl-formcard, .form-card");
    var ok = card && card.querySelector(".form-success");
    if (!ok || !window.MutationObserver) return;
    new MutationObserver(function () {
      if (!ok.classList.contains("show")) return;
      var h = ok.querySelector("h3");
      if (h) { h.setAttribute("tabindex", "-1"); try { h.focus(); } catch (e) {} }
    }).observe(ok, { attributes: true, attributeFilter: ["class"] });
  });
})();
