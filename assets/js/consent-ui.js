/*
 * Pro Link Systems: privacy choices banner and dialog (loaded on demand by consent.js).
 * The banner appears only where consent is required (EEA, UK, Switzerland) and no choice is saved; everyone can open
 * the dialog from "Your Privacy Choices". Accept and Reject have equal weight; nothing is pre-ticked where consent is
 * required. Phase 3, 2026-11-24.
 */
(function (w, d) {
  "use strict";
  if (w.plsConsentUI || !w.plsConsent) { return; }
  var C = w.plsConsent;

  var CSS = [
    ".plc-banner{position:fixed;left:16px;right:16px;bottom:16px;z-index:2147483000;max-width:760px;margin:0 auto;background:#fff;color:#14213d;",
    "border:1px solid #c9d3df;border-radius:10px;box-shadow:0 10px 30px rgba(10,30,60,.18);padding:18px 20px;font:15px/1.5 inherit}",
    ".plc-banner p{margin:0 0 12px}",
    ".plc-actions{display:flex;flex-wrap:wrap;gap:10px}",
    ".plc-btn{appearance:none;border:2px solid #0b3d6b;background:#fff;color:#0b3d6b;border-radius:6px;padding:9px 16px;",
    "font:600 14px/1.2 inherit;cursor:pointer;min-height:44px}",
    ".plc-btn:hover{background:#0b3d6b;color:#fff}",
    ".plc-btn:focus-visible,.plc-close:focus-visible,.plc-dialog input:focus-visible,.plc-banner a:focus-visible,.plc-dialog a:focus-visible",
    "{outline:3px solid #f2a900;outline-offset:2px}",
    ".plc-back{position:fixed;inset:0;z-index:2147483001;background:rgba(10,20,40,.55);display:flex;align-items:center;justify-content:center;padding:16px}",
    ".plc-back[hidden]{display:none}",
    ".plc-dialog{position:relative;background:#fff;color:#14213d;border-radius:12px;max-width:620px;width:100%;max-height:calc(100vh - 32px);",
    "overflow:auto;padding:26px 24px 22px;font:15px/1.55 inherit;box-shadow:0 20px 50px rgba(0,0,0,.3)}",
    ".plc-dialog h2{font-size:1.3rem;margin:0 36px 8px 0;color:#0b3d6b}",
    ".plc-dialog h3{font-size:1rem;margin:0 0 4px;color:#14213d}",
    ".plc-dialog p{margin:0 0 10px}",
    ".plc-row{display:flex;gap:16px;align-items:flex-start;justify-content:space-between;border-top:1px solid #e3e8ef;padding:14px 0}",
    ".plc-row p{font-size:.92rem;color:#3d4a5c;margin:0}",
    ".plc-toggle{display:flex;align-items:center;gap:8px;white-space:nowrap;font-weight:600;font-size:.9rem;min-height:44px}",
    ".plc-toggle input{width:22px;height:22px;accent-color:#0b3d6b}",
    ".plc-fixed{font-weight:600;font-size:.9rem;white-space:nowrap;color:#1f6b43;padding-top:2px}",
    ".plc-note{font-size:.88rem;background:#f3f6fa;border-left:3px solid #0b3d6b;padding:8px 10px}",
    ".plc-close{position:absolute;top:10px;right:10px;width:44px;height:44px;border:0;background:transparent;font-size:26px;line-height:1;cursor:pointer;color:#14213d}",
    ".plc-status{font-size:.88rem;color:#1f6b43;min-height:1.2em;margin-top:8px}",
    "@media (max-width:560px){.plc-row{flex-direction:column;gap:6px}.plc-actions .plc-btn{flex:1 1 auto}}"
  ].join("");

  function el(html) { var t = d.createElement("div"); t.innerHTML = html; return t.firstElementChild; }
  var style = d.createElement("style");
  style.textContent = CSS;
  d.head.appendChild(style);

  var banner = null, back = null, lastOpener = null;

  function closeBanner() { if (banner) { banner.remove(); banner = null; } }

  function choose(choice, source) {
    C.set(choice, source);
    closeBanner();
  }

  function showBanner() {
    if (banner || C.state().saved) { return; }
    banner = el(
      '<div class="plc-banner" role="region" aria-label="Cookie choices">' +
      '<p>We use cookies and similar technologies for website analytics and to measure our advertising. You can accept, ' +
      'reject or choose. <a href="/privacy#cookies">Privacy policy</a></p>' +
      '<div class="plc-actions">' +
      '<button type="button" class="plc-btn" data-plc="accept">Accept all</button>' +
      '<button type="button" class="plc-btn" data-plc="reject">Reject all</button>' +
      '<button type="button" class="plc-btn" data-plc="choices">Choose</button>' +
      '</div></div>');
    banner.addEventListener("click", function (e) {
      var b = e.target.closest("[data-plc]");
      if (!b) { return; }
      var a = b.getAttribute("data-plc");
      if (a === "accept") { choose({ analytics: true, ads: true }, "banner"); }
      else if (a === "reject") { choose({ analytics: false, ads: false }, "banner"); }
      else { open(b); }
    });
    d.body.appendChild(banner);
  }

  function build() {
    back = el(
      '<div class="plc-back" hidden>' +
      '<div class="plc-dialog" role="dialog" aria-modal="true" aria-labelledby="plc-title" aria-describedby="plc-desc">' +
      '<button type="button" class="plc-close" aria-label="Close privacy choices">&times;</button>' +
      '<h2 id="plc-title">Your privacy choices</h2>' +
      '<p id="plc-desc">Choose how this website may use cookies and similar technologies. Your choice is saved in this browser. ' +
      'Read the <a href="/privacy#cookies">privacy policy</a> for details.</p>' +
      '<div class="plc-row"><div><h3>Strictly necessary</h3><p>Security, spam protection for forms (Cloudflare Turnstile), ' +
      'payments and site delivery. Always on.</p></div><span class="plc-fixed">Always on</span></div>' +
      '<div class="plc-row"><div><h3>Analytics</h3><p>Google Analytics, Microsoft Clarity and Hotjar help us see how pages are ' +
      'used so we can improve them.</p></div><label class="plc-toggle"><input type="checkbox" id="plc-analytics" aria-label="Allow analytics"> Allow</label></div>' +
      '<div class="plc-row"><div><h3>Advertising measurement</h3><p>Google Ads and Microsoft Advertising measure which ads lead ' +
      'to inquiries. When you submit a form, a hashed (coded) copy of your name, email and phone may be sent to Google to match ' +
      'your inquiry to an ad click. Turning this off opts you out of the sale or sharing of your personal information for ' +
      'advertising. We do not use remarketing or personalized-ad audiences.</p></div>' +
      '<label class="plc-toggle"><input type="checkbox" id="plc-ads" aria-label="Allow advertising measurement"> Allow</label></div>' +
      '<p class="plc-note" id="plc-gpc" hidden>Your browser is sending a Global Privacy Control signal, so advertising ' +
      'measurement stays off for this browser.</p>' +
      '<div class="plc-actions">' +
      '<button type="button" class="plc-btn" data-plc="save">Save choices</button>' +
      '<button type="button" class="plc-btn" data-plc="accept">Accept all</button>' +
      '<button type="button" class="plc-btn" data-plc="reject">Reject all</button>' +
      '</div><p class="plc-status" role="status" aria-live="polite"></p></div></div>');
    d.body.appendChild(back);
    var dlg = back.querySelector(".plc-dialog");
    back.addEventListener("click", function (e) {
      if (e.target === back) { close(); return; }
      var b = e.target.closest("[data-plc]");
      if (e.target.closest(".plc-close")) { close(); return; }
      if (!b) { return; }
      var a = b.getAttribute("data-plc");
      var choice = a === "accept" ? { analytics: true, ads: true }
                 : a === "reject" ? { analytics: false, ads: false }
                 : { analytics: back.querySelector("#plc-analytics").checked, ads: back.querySelector("#plc-ads").checked };
      choose(choice, "settings");
      sync();
      back.querySelector(".plc-status").textContent = "Saved. Your choices apply now.";
      setTimeout(close, 900);
    });
    back.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { e.preventDefault(); close(); return; }
      if (e.key !== "Tab") { return; }
      var f = [].slice.call(dlg.querySelectorAll("button, a[href], input:not([disabled])")).filter(function (x) { return x.offsetParent !== null; });
      if (!f.length) { return; }
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && d.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && d.activeElement === last) { e.preventDefault(); first.focus(); }
    });
  }

  function sync() {
    var s = C.state();
    var an = back.querySelector("#plc-analytics"), ad = back.querySelector("#plc-ads");
    an.checked = s.analytics;
    ad.checked = s.ads;
    ad.disabled = s.gpc;
    back.querySelector("#plc-gpc").hidden = !s.gpc;
  }

  function open(opener) {
    if (!back) { build(); }
    lastOpener = opener || d.activeElement;
    sync();
    back.querySelector(".plc-status").textContent = "";
    back.hidden = false;
    d.documentElement.style.overflow = "hidden";
    back.querySelector("#plc-analytics").focus();
  }

  function close() {
    if (!back || back.hidden) { return; }
    back.hidden = true;
    d.documentElement.style.overflow = "";
    var target = lastOpener && d.body.contains(lastOpener) ? lastOpener : null;
    if (target && typeof target.focus === "function") { target.focus(); }
  }

  w.plsConsentUI = { banner: showBanner, open: open, close: close };
})(window, document);
