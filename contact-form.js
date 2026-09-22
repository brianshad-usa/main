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
 */
(function () {
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

  function handle(form) {
    var btn = submitBtn(form);
    var data = Object.fromEntries(new FormData(form));

    var email = String(data.email || "").trim();
    var firstName = String(data.first_name || data.name || "").trim();
    if (!firstName || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || !String(data.phone || "").trim()) {
      setError("Please fill in your name, a valid email, and a phone number, then try again.");
      return;
    }
    if (!data["cf-turnstile-response"]) {
      setError('Please complete the "I\'m not a robot" check, then send again.');
      return;
    }

    if (btn) { btn.disabled = true; btn.classList.add("loading"); }

    fetch("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(data)
    })
      .then(function (res) { return res.json().then(function (j) { return { ok: res.ok, json: j }; }); })
      .then(function (r) {
        if (r.ok && r.json && r.json.success) {
          if (typeof gtag === "function") {
            gtag("event", "conversion", { send_to: "AW-1068497497/yYS5CNKQkbccENn0v_0D", value: 50.0, currency: "USD" });
          }
          showSuccess(form, r.json.refNumber, firstName.split(" ")[0]);
        } else {
          if (btn) { btn.disabled = false; btn.classList.remove("loading"); }
          if (window.turnstile) { try { turnstile.reset(); } catch (e) {} }
          setError((r.json && r.json.message) || "There was a problem sending your message. Please call 1-800-890-6133 or email info@prolinksystems.com.");
        }
      })
      .catch(function () {
        if (btn) { btn.disabled = false; btn.classList.remove("loading"); }
        if (window.turnstile) { try { turnstile.reset(); } catch (e) {} }
        setError("There was a problem sending your message. Please call 1-800-890-6133 or email info@prolinksystems.com.");
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
