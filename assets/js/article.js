/* Insights article pages: the contents list (collapsed on phones, reading position on desktop). redesign-2026.
   Everything works without this script: the list is a plain <details> that starts open. */
(function () {
  'use strict';
  var nav = document.querySelector('.pl-toc');
  if (!nav) return;
  var box = nav.querySelector('details');
  var small = window.matchMedia('(max-width: 1024px)');
  if (box && small.matches) box.removeAttribute('open');
  var links = [].slice.call(nav.querySelectorAll('a[href^="#"]'));
  if (!links.length || !('IntersectionObserver' in window)) return;
  var byId = {};
  links.forEach(function (a) { byId[a.getAttribute('href').slice(1)] = a; });
  var heads = [].slice.call(document.querySelectorAll('.pl-art-body h2[id]')).filter(function (h) { return byId[h.id]; });
  var current = null;
  function mark(id) {
    if (current === id) return;
    current = id;
    links.forEach(function (a) {
      if (a === byId[id]) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
    });
  }
  var seen = {};
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { seen[e.target.id] = e.isIntersecting; });
    for (var i = 0; i < heads.length; i++) if (seen[heads[i].id]) { mark(heads[i].id); return; }
  }, { rootMargin: '-96px 0px -62% 0px' });
  heads.forEach(function (h) { io.observe(h); });
})();
