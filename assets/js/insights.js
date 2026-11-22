/* Insights index (/blog/): "Show more" in Latest, and search + topic filter in the Library. redesign-2026, iteration 4.
   Every article is a plain server-rendered link (the Library lists all of them by topic in <details> sections), so the
   page works fully without this script. Topics use the URL hash and search uses no URL: nothing new to index. */
(function () {
  'use strict';
  var root = document.documentElement;
  var library = document.getElementById('library');
  if (!library) return;
  root.classList.add('pl-ins-on');          // reveals the search, filter and "show more" controls

  /* ---- Latest: progressive loading ------------------------------------------------------------------------- */
  var grid = document.getElementById('pl-ins-list');
  var moreWrap = document.querySelector('.pl-ins-more');
  var more = moreWrap ? moreWrap.querySelector('button') : null;
  if (grid && more) {
    var cards = [].slice.call(grid.querySelectorAll('.pl-icard'));
    var step = parseInt(grid.getAttribute('data-page'), 10) || 12;
    var shown = step;
    var paint = function () {
      cards.forEach(function (c, i) { c.hidden = i >= shown; });
      moreWrap.hidden = shown >= cards.length;
    };
    more.addEventListener('click', function () {
      var first = cards[shown];
      shown += step;
      paint();
      var a = first && first.querySelector('a');
      if (a) a.focus();                      // keyboard and screen-reader users continue at the first new article
    });
    paint();
  }

  /* ---- Library: search + topic filter ------------------------------------------------------------------------ */
  var sections = [].slice.call(library.querySelectorAll('.pl-lib'));
  var chips = [].slice.call(library.querySelectorAll('.pl-ins-filter button'));
  var input = document.getElementById('pl-ins-q');
  var count = library.querySelector('.pl-ins-count');
  var empty = library.querySelector('.pl-ins-empty');
  var names = {};
  chips.forEach(function (b) { names[b.getAttribute('data-cat')] = b.textContent; });
  var rows = [];
  sections.forEach(function (s) {
    [].forEach.call(s.querySelectorAll('.pl-lib-row'), function (r) {
      rows.push({ el: r, section: s, cat: s.getAttribute('data-cat'), text: norm(r.getAttribute('data-text') || r.textContent) });
    });
  });
  var cat = '', query = '', timer = 0;

  function norm(s) {
    s = (s || '').toLowerCase();
    return s.normalize ? s.normalize('NFD').replace(/[̀-ͯ]/g, '') : s;
  }
  function plural(n) { return n + (n === 1 ? ' article' : ' articles'); }

  function render(openAll) {
    var terms = norm(query).split(/\s+/).filter(Boolean);
    var hits = 0, perSection = {};
    rows.forEach(function (r) {
      var ok = (!cat || r.cat === cat) && terms.every(function (t) { return r.text.indexOf(t) !== -1; });
      r.el.hidden = !ok;
      if (ok) { hits++; perSection[r.cat] = (perSection[r.cat] || 0) + 1; }
    });
    sections.forEach(function (s) {
      var n = perSection[s.getAttribute('data-cat')] || 0;
      s.hidden = n === 0;
      if (openAll) s.open = n > 0 && (!!terms.length || s.getAttribute('data-cat') === cat);
    });
    if (count) {
      count.textContent = hits ? (terms.length || cat ? 'Showing ' + plural(hits) : plural(hits)) +
        (cat ? ' in ' + names[cat] : '') + (terms.length ? ' matching “' + query + '”' : '') : '';
    }
    if (empty) empty.hidden = hits > 0;
  }

  function setCat(slug, push) {
    cat = Object.prototype.hasOwnProperty.call(names, slug) ? slug : '';
    chips.forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-cat') === cat)); });
    if (push) { try { history.replaceState(null, '', cat ? '#' + cat : location.pathname + location.search); } catch (e) { /* file:// */ } }
    render(true);
  }

  chips.forEach(function (b) {
    b.addEventListener('click', function () { setCat(b.getAttribute('data-cat'), true); });
  });

  if (input) {
    input.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(function () { query = input.value.trim(); render(!!query || !!cat); if (!query && !cat) sections.forEach(function (s) { s.open = false; }); }, 120);
    });
  }

  function open(slug) {
    if (slug === 'library') { setCat('', true); library.scrollIntoView({ block: 'start' }); return true; }
    if (!slug || !Object.prototype.hasOwnProperty.call(names, slug)) return false;
    setCat(slug, true);
    library.scrollIntoView({ block: 'start' });
    return true;
  }

  // Topic links in the page header open that topic in the Library (without JavaScript they jump to the section).
  document.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('.pl-topics a[href^="#"], .pl-ins-tools a[href="#library"]') : null;
    if (a && open(a.getAttribute('href').slice(1))) e.preventDefault();
  });
  window.addEventListener('hashchange', function () { open(location.hash.slice(1)); });

  var initial = location.hash.slice(1);
  if (initial && Object.prototype.hasOwnProperty.call(names, initial)) {
    setCat(initial, false);
    window.addEventListener('load', function () { library.scrollIntoView({ block: 'start' }); });
  } else {
    render(false);
  }
})();
