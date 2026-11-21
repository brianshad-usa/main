/* Insights index (/blog/): topic filter, keyword search and load-more. redesign-2026, iteration 3.
   Every article is a plain server-rendered link in the HTML; this script only hides and reveals cards, so the
   page works fully without it. Topic filters use the URL hash and search uses no URL at all: no new pages to index. */
(function () {
  'use strict';
  var list = document.getElementById('pl-ins-list');
  if (!list) return;
  document.documentElement.classList.add('pl-ins-on');   // reveals the filter, search and load-more controls
  var cards = Array.prototype.slice.call(list.querySelectorAll('.pl-icard'));
  var buttons = Array.prototype.slice.call(document.querySelectorAll('.pl-ins-filter button'));
  var input = document.getElementById('pl-ins-q');
  var moreWrap = document.querySelector('.pl-ins-more');
  var more = moreWrap ? moreWrap.querySelector('button') : null;
  var count = document.querySelector('.pl-ins-count');
  var empty = document.querySelector('.pl-ins-empty');
  var latest = document.getElementById('latest');
  var page = parseInt(list.getAttribute('data-page'), 10) || 12;
  var shown = page, cat = '', query = '', timer = 0;
  var names = {};
  buttons.forEach(function (b) { names[b.getAttribute('data-cat')] = b.textContent; });

  function norm(s) {
    s = (s || '').toLowerCase();
    return s.normalize ? s.normalize('NFD').replace(/[̀-ͯ]/g, '') : s;
  }
  cards.forEach(function (c) { c._text = norm(c.getAttribute('data-text') || c.textContent); });

  function matching() {
    var terms = norm(query).split(/\s+/).filter(Boolean);
    return cards.filter(function (c) {
      if (cat && c.getAttribute('data-cat') !== cat) return false;
      for (var i = 0; i < terms.length; i++) {
        if (c._text.indexOf(terms[i]) === -1) return false;
      }
      return true;
    });
  }

  function render() {
    var m = matching();
    cards.forEach(function (c) { c.hidden = true; });
    m.forEach(function (c, i) { c.hidden = i >= shown; });
    var visible = Math.min(shown, m.length);
    if (count) {
      count.textContent = m.length ? 'Showing ' + visible + ' of ' + m.length + (m.length === 1 ? ' article' : ' articles') +
        (cat ? ' in ' + names[cat] : '') + (query ? ' matching “' + query + '”' : '') : '';
    }
    if (empty) empty.hidden = m.length > 0;
    if (moreWrap) moreWrap.hidden = visible >= m.length;
    return m;
  }

  function toLatest(smooth) {
    if (latest) latest.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' });
  }

  function setCat(slug) {
    cat = Object.prototype.hasOwnProperty.call(names, slug) ? slug : '';
    shown = page;
    buttons.forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-cat') === cat)); });
    try { history.replaceState(null, '', cat ? '#' + cat : location.pathname + location.search); } catch (e) { /* file:// */ }
    render();
  }

  buttons.forEach(function (b) {
    b.addEventListener('click', function () { setCat(b.getAttribute('data-cat')); });
  });

  // Topic links in the page header filter the list instead of jumping to the archive (their no-JS target).
  document.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('.pl-topics a[href^="#"]') : null;
    if (!a) return;
    var slug = a.getAttribute('href').slice(1);
    if (slug === 'latest') slug = '';   // "All perspectives"
    else if (!slug || !Object.prototype.hasOwnProperty.call(names, slug)) return;
    e.preventDefault();
    setCat(slug);
    toLatest(true);
  });

  if (input) {
    input.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(function () { query = input.value.trim(); shown = page; render(); }, 120);
    });
  }

  if (more) {
    more.addEventListener('click', function () {
      var before = shown;
      shown += page;
      var next = render()[before];
      var link = next ? next.querySelector('a') : null;
      if (link) link.focus();   // keyboard and screen-reader users continue at the first newly shown article
    });
  }

  var initial = location.hash.slice(1);
  if (initial && Object.prototype.hasOwnProperty.call(names, initial)) {
    setCat(initial);
    toLatest(false);
    window.addEventListener('load', function () { toLatest(false); });
  } else {
    render();
  }
})();
