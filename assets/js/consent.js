/*
 * Pro Link Systems: consent defaults (Google Consent Mode v2 and Microsoft UET consent mode).
 *
 * Loaded synchronously in <head>, BEFORE the Google tag and the Microsoft UET tag, on every page that carries them
 * (inserted between <!-- PL:CONSENT --> markers by chrome/apply_chrome.py). Phase 3, 2026-11-24.
 *
 * What it decides, per visitor:
 *   - EEA, UK and Switzerland: everything denied until the visitor chooses (Google applies this by IP through the
 *     `region` default; this script also uses the browser time zone to show the choice banner and to hold back the
 *     non-Google tags it controls).
 *   - Everywhere else: analytics and advertising measurement on by default, with an opt-out ("Your Privacy Choices").
 *   - Global Privacy Control (navigator.globalPrivacyControl): treated as an opt-out of advertising data sharing.
 *   - ad_personalization is always denied: the site does not use remarketing or personalized-ad audiences.
 *   - A saved choice (localStorage "pls_consent_v1") overrides the defaults; GPC still wins for advertising.
 *
 * window.plsConsent: state(), analytics(), ads(), set({analytics, ads}, source), open().
 * The choice banner and dialog live in consent-ui.js, loaded only when needed.
 * Test hooks (never on prolinksystems.com): ?pls_region=eea|us and ?pls_gpc=1, kept for the browser session.
 */
(function (w, d) {
  "use strict";
  var KEY = "pls_consent_v1";
  var VERSION = 1;
  var UI_SRC = "/assets/js/consent-ui.js?v=20261124";
  var EEA = ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IS", "IE", "IT", "LV", "LI",
             "LT", "LU", "MT", "NL", "NO", "PL", "PT", "RO", "SK", "SI", "ES", "SE", "GB", "CH"];

  w.dataLayer = w.dataLayer || [];
  function gtag() { w.dataLayer.push(arguments); }
  w.uetq = w.uetq || [];

  function storage(kind) { try { return w[kind]; } catch (e) { return null; } }
  var ls = storage("localStorage"), ss = storage("sessionStorage");

  var host = (w.location && w.location.hostname) || "";
  var production = /(^|\.)prolinksystems\.com$/.test(host);
  var test = {};
  if (!production) {
    try {
      var q = new URLSearchParams(w.location.search);
      if (q.get("pls_region")) { ss && ss.setItem("pls_test_region", q.get("pls_region")); }
      if (q.get("pls_gpc")) { ss && ss.setItem("pls_test_gpc", q.get("pls_gpc")); }
      if (q.get("pls_reset") && ls) { ls.removeItem(KEY); }
      test.region = ss && ss.getItem("pls_test_region");
      test.gpc = ss && ss.getItem("pls_test_gpc") === "1";
    } catch (e) { /* no test hooks */ }
  }

  function tzRegion() {
    try {
      var tz = (Intl.DateTimeFormat().resolvedOptions().timeZone) || "";
      return (/^Europe\//.test(tz) || /^(Atlantic\/(Reykjavik|Canary|Madeira|Azores|Faroe)|Arctic\/Longyearbyen)$/.test(tz)) ? "eea" : "other";
    } catch (e) { return "other"; }
  }

  function read() {
    try {
      var v = ls && JSON.parse(ls.getItem(KEY) || "null");
      return (v && v.v === VERSION && typeof v.analytics === "boolean" && typeof v.ads === "boolean") ? v : null;
    } catch (e) { return null; }
  }

  var region = test.region === "eea" ? "eea" : (test.region === "us" ? "other" : tzRegion());
  var gpc = test.gpc === true || (typeof navigator !== "undefined" && navigator.globalPrivacyControl === true);
  var saved = read();
  var state = saved ? { analytics: saved.analytics, ads: saved.ads }
                    : (region === "eea" ? { analytics: false, ads: false } : { analytics: true, ads: true });
  if (gpc) { state.ads = false; }

  function signals(s) {
    return {
      ad_storage: s.ads ? "granted" : "denied",
      ad_user_data: s.ads ? "granted" : "denied",
      ad_personalization: "denied",
      analytics_storage: s.analytics ? "granted" : "denied"
    };
  }

  // 1) EEA, UK, Switzerland (by IP, applied by Google): denied until the visitor chooses.
  gtag("consent", "default", { ad_storage: "denied", ad_user_data: "denied", ad_personalization: "denied",
                               analytics_storage: "denied", region: EEA, wait_for_update: 500 });
  // 2) Everyone else: this visitor's state.
  gtag("consent", "default", signals(state));
  // 3) A saved choice also applies inside the EEA default.
  if (saved) { gtag("consent", "update", signals(state)); }
  // Advertising off: redact ad click identifiers and ask Google for restricted data processing.
  gtag("set", "ads_data_redaction", !state.ads);
  gtag("set", "restricted_data_processing", !state.ads);
  // Microsoft UET: default before the UET tag loads.
  w.uetq.push("consent", "default", { ad_storage: state.ads ? "granted" : "denied" });

  function emit() {
    try { w.dispatchEvent(new CustomEvent("pls:consent", { detail: api.state() })); } catch (e) { /* old browser */ }
  }

  var uiLoading = null;
  function loadUI(cb) {
    if (w.plsConsentUI) { cb && cb(); return; }
    if (uiLoading) { uiLoading.push(cb); return; }
    uiLoading = [cb];
    var s = d.createElement("script");
    s.src = UI_SRC;
    s.async = true;
    s.onload = function () { var q = uiLoading; uiLoading = null; q.forEach(function (f) { f && f(); }); };
    s.onerror = function () { uiLoading = null; w.location.href = "/privacy#your-choices"; };
    (d.head || d.documentElement).appendChild(s);
  }

  var api = {
    state: function () {
      return { analytics: state.analytics, ads: state.ads, gpc: gpc, region: region, saved: !!saved };
    },
    analytics: function () { return state.analytics; },
    ads: function () { return state.ads; },
    set: function (choice, source) {
      var before = state.analytics;
      state = { analytics: !!choice.analytics, ads: !!choice.ads && !gpc };
      saved = { v: VERSION, analytics: state.analytics, ads: state.ads, gpc: gpc, ts: new Date().toISOString(),
                src: source || "settings" };
      try { ls && ls.setItem(KEY, JSON.stringify(saved)); } catch (e) { /* choice applies to this page only */ }
      gtag("consent", "update", signals(state));
      gtag("set", "ads_data_redaction", !state.ads);
      gtag("set", "restricted_data_processing", !state.ads);
      w.uetq.push("consent", "update", { ad_storage: state.ads ? "granted" : "denied" });
      emit();
      // Session recorders cannot be unloaded mid-page: stop Clarity and reload so Hotjar stops too.
      if (before && !state.analytics && w.__plsRecorders) {
        try { if (typeof w.clarity === "function") { w.clarity("consent", false); } } catch (e) { /* ignore */ }
        setTimeout(function () { w.location.reload(); }, 300);
      }
    },
    open: function (opener) { loadUI(function () { w.plsConsentUI.open(opener); }); }
  };
  w.plsConsent = api;

  // "Your Privacy Choices" links: open the dialog (without JavaScript they go to the policy's choices section).
  d.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("[data-privacy-choices]") : null;
    if (!a) { return; }
    e.preventDefault();
    api.open(a);
  });

  // Banner only where consent is required and no choice is saved yet.
  if (region === "eea" && !saved) {
    var show = function () { loadUI(function () { w.plsConsentUI.banner(); }); };
    if (d.readyState === "loading") { d.addEventListener("DOMContentLoaded", show); } else { show(); }
  }
})(window, document);
