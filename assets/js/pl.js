/* Pro Link Systems site script (2026 design system). Header menus, mobile drawer, reveal-on-scroll.
   No dependencies, no tracking. Loaded with `defer` on every page by chrome/apply_chrome.py. */
(function () {
  'use strict';
  var d = document, root = d.documentElement;
  var hoverCapable = window.matchMedia ? window.matchMedia('(hover: hover) and (pointer: fine)') : { matches: false };

  /* ---- mega menus ---------------------------------------------------------------------------- */
  var header = d.getElementById('pl-header');
  var triggers = header ? [].slice.call(header.querySelectorAll('.pl-nav-trigger')) : [];
  var openTrigger = null, timer = null;

  function panelOf(btn) { return d.getElementById(btn.getAttribute('aria-controls')); }
  function closeMenu(returnFocus) {
    if (!openTrigger) return;
    var p = panelOf(openTrigger);
    if (p) p.classList.remove('is-open');
    openTrigger.setAttribute('aria-expanded', 'false');
    if (returnFocus) openTrigger.focus();
    openTrigger = null;
  }
  function openMenu(btn) {
    if (openTrigger === btn) return;
    closeMenu(false);
    var p = panelOf(btn);
    if (!p) return;
    p.classList.add('is-open');
    btn.setAttribute('aria-expanded', 'true');
    openTrigger = btn;
  }
  triggers.forEach(function (btn) {
    btn.addEventListener('click', function () {
      clearTimeout(timer);
      if (openTrigger === btn) closeMenu(false); else openMenu(btn);
    });
    btn.addEventListener('mouseenter', function () {
      if (!hoverCapable.matches) return;
      clearTimeout(timer);
      timer = setTimeout(function () { openMenu(btn); }, openTrigger ? 0 : 110);
    });
  });
  /* keyboard: an open panel follows its trigger in the focus order (Tab or Down Arrow enters it, Tab leaves it) */
  function panelLinks(p) { return [].slice.call(p.querySelectorAll('a[href], button')); }
  triggers.forEach(function (btn) {
    var p = panelOf(btn);
    if (!p) return;
    btn.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown' || (e.key === 'Tab' && !e.shiftKey && openTrigger === btn)) {
        if (openTrigger !== btn) openMenu(btn);
        var first = panelLinks(p)[0];
        if (first) { e.preventDefault(); first.focus(); }
      }
    });
    p.addEventListener('keydown', function (e) {
      if (e.key !== 'Tab') return;
      var l = panelLinks(p), at = l.indexOf(d.activeElement);
      if (e.shiftKey && at === 0) { e.preventDefault(); btn.focus(); }
      if (!e.shiftKey && at === l.length - 1) {
        var items = [].slice.call(header.querySelectorAll('.pl-nav-trigger, .pl-nav-link, .pl-header-cta'));
        var next = items[items.indexOf(btn) + 1];
        if (next) { e.preventDefault(); closeMenu(false); next.focus(); }
      }
    });
  });
  if (header) {
    [].slice.call(header.querySelectorAll('.pl-nav-link, .pl-logo, .pl-header-cta')).forEach(function (el) {
      el.addEventListener('mouseenter', function () { if (hoverCapable.matches) { clearTimeout(timer); timer = setTimeout(function () { closeMenu(false); }, 150); } });
    });
    header.addEventListener('mouseleave', function () {
      if (!hoverCapable.matches) return;
      clearTimeout(timer);
      timer = setTimeout(function () { closeMenu(false); }, 220);
    });
    header.addEventListener('mouseenter', function () { if (openTrigger) clearTimeout(timer); });
    header.addEventListener('focusout', function (e) {
      if (openTrigger && e.relatedTarget && !header.contains(e.relatedTarget)) closeMenu(false);
    });
  }
  d.addEventListener('click', function (e) {
    if (openTrigger && header && !header.contains(e.target)) closeMenu(false);
  });

  /* ---- mobile drawer --------------------------------------------------------------------------- */
  var burger = d.querySelector('.pl-burger');
  var drawer = d.getElementById('pl-drawer');
  function setDrawer(on) {
    if (!burger || !drawer) return;
    drawer.classList.toggle('is-open', on);
    burger.setAttribute('aria-expanded', on ? 'true' : 'false');
    burger.setAttribute('aria-label', on ? 'Close menu' : 'Open menu');
    root.classList.toggle('pl-lock', on);
  }
  if (burger && drawer) {
    burger.addEventListener('click', function () { setDrawer(!drawer.classList.contains('is-open')); });
    drawer.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('a')) setDrawer(false); });
    window.addEventListener('resize', function () { if (window.innerWidth > 1024) setDrawer(false); });
  }

  d.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (openTrigger) closeMenu(true);
    if (drawer && drawer.classList.contains('is-open')) { setDrawer(false); if (burger) burger.focus(); }
  });

  /* ---- tabs (practice areas): plain stacked sections become tabs; without JS every panel shows ---- */
  [].slice.call(d.querySelectorAll('[data-tabs]')).forEach(function (box) {
    var tabs = [].slice.call(box.querySelectorAll('[role="tab"]'));
    var panels = tabs.map(function (t) { return d.getElementById(t.getAttribute('aria-controls')); });
    if (!tabs.length || panels.some(function (p) { return !p; })) return;
    function select(i, focus) {
      tabs.forEach(function (t, j) {
        var on = i === j;
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.tabIndex = on ? 0 : -1;
        panels[j].classList.toggle('is-active', on);
      });
      if (focus) tabs[i].focus();
    }
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { select(i, false); });
      t.addEventListener('keydown', function (e) {
        var n = tabs.length, k = e.key;
        var j = (k === 'ArrowDown' || k === 'ArrowRight') ? (i + 1) % n : (k === 'ArrowUp' || k === 'ArrowLeft') ? (i - 1 + n) % n : k === 'Home' ? 0 : k === 'End' ? n - 1 : -1;
        if (j >= 0) { e.preventDefault(); select(j, true); }
      });
    });
    box.classList.add('is-enhanced');
    select(0, false);
  });

  /* ---- accordions on older pages: keep aria-expanded in step with the open state ------------------ */
  function syncFaq() {
    [].slice.call(d.querySelectorAll('.faq-q, .faq-question')).forEach(function (b) {
      var item = b.closest('.faq-item') || b.parentElement;
      b.setAttribute('aria-expanded', b.classList.contains('open') || item.classList.contains('open') ? 'true' : 'false');
    });
  }
  if (d.querySelector('.faq-q, .faq-question')) {
    syncFaq();
    d.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('.faq-q, .faq-question')) setTimeout(syncFaq, 0); });
  }

  /* ---- reveal on scroll (content is never hidden; arriving blocks only rise a few pixels) -------- */
  var els = [].slice.call(d.querySelectorAll('.pl-reveal'));
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!els.length || reduce || !('IntersectionObserver' in window)) {
    els.forEach(function (el) { el.classList.add('is-in'); });
  } else {
    var vh = window.innerHeight || root.clientHeight;
    els.forEach(function (el) { if (el.getBoundingClientRect().top < vh) el.classList.add('is-in'); });
    root.classList.add('js');
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('is-in'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -6% 0px', threshold: 0.06 });
    els.forEach(function (el) { if (!el.classList.contains('is-in')) io.observe(el); });
  }
})();
