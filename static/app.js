/* Catalyst EB-5, site behavior. No dependencies. Same base as catalystcd.com. */
(function () {
  'use strict';

  /* ---- reveal on scroll ---- */
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var rv = document.querySelectorAll('.rv');
  if (reduce || !('IntersectionObserver' in window)) {
    rv.forEach(function (el) { el.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });
    rv.forEach(function (el) { io.observe(el); });
  }

  /* ---- header transparent over hero, solid after ---- */
  var hdr = document.getElementById('hdr');
  var heroEl = document.querySelector('.hero, .phero');
  // Pages without a photo hero (articles, thank-you, 404) start with a solid header.
  var trigger = heroEl ? heroEl.offsetHeight - 90 : -1;
  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      hdr.classList.toggle('solid', window.scrollY > trigger);
      ticking = false;
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', function () {
    trigger = heroEl ? heroEl.offsetHeight - 90 : -1;
    onScroll();
  }, { passive: true });
  onScroll();

  /* ---- mobile nav ---- */
  var burger = document.getElementById('burger');
  var mnav = document.getElementById('mnav');
  if (burger && mnav) {
    burger.addEventListener('click', function () {
      var open = mnav.classList.toggle('open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      burger.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      document.body.style.overflow = open ? 'hidden' : '';
    });
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape' && mnav.classList.contains('open')) burger.click();
    });
  }

  /* ---- graceful image fallback ---- */
  document.addEventListener('error', function (ev) {
    var el = ev.target;
    if (el.tagName !== 'IMG' || el.dataset.failed) return;
    el.dataset.failed = '1';
    var par = el.parentElement;
    el.style.visibility = 'hidden';
    if (!par || par.classList.contains('hero-media')) return;
    var d = document.createElement('div');
    d.className = 'ph';
    d.style.position = 'absolute';
    d.style.pointerEvents = 'none';
    d.innerHTML = '<svg viewBox="0 0 32 32"><circle cx="16" cy="16" r="13" fill="none" stroke="#B79A4F" stroke-width="2"/>'
      + '<circle cx="16" cy="16" r="7" fill="none" stroke="#B79A4F" stroke-width="2"/></svg>'
      + '<div class="pn">' + (el.alt || 'Catalyst') + '</div><div class="pl">Image unavailable</div>';
    if (getComputedStyle(par).position === 'static') par.style.position = 'relative';
    par.appendChild(d);
  }, true);

  /* ---- contact: ?type=proposal preselects the first engagement option ---- */
  var params = new URLSearchParams(location.search);
  if (params.get('type') === 'proposal') {
    var ms = document.getElementById('ms');
    if (ms && !ms.value) ms.placeholder = 'Tell us about the fund, the project and the loan you would like us to administer.';
  }

  /* ---- info center category filter (?category=slug) ---- */
  var chips = document.getElementById('chips');
  var grid = document.getElementById('igrid');
  if (chips && grid) {
    var cards = grid.querySelectorAll('.icard');
    var empty = document.getElementById('iempty');
    var apply = function (cat) {
      var shown = 0;
      cards.forEach(function (c) {
        var on = cat === 'all' || c.dataset.cat === cat;
        c.classList.toggle('hide', !on);
        if (on) { c.classList.add('in'); shown++; }
      });
      chips.querySelectorAll('.chip').forEach(function (ch) {
        ch.classList.toggle('on', ch.dataset.cat === cat);
        ch.setAttribute('aria-current', ch.dataset.cat === cat ? 'true' : 'false');
      });
      if (empty) empty.style.display = shown ? 'none' : 'block';
    };
    apply(params.get('category') || 'all');
    chips.addEventListener('click', function (ev) {
      var a = ev.target.closest('.chip');
      if (!a) return;
      ev.preventDefault();
      var cat = a.dataset.cat;
      var url = cat === 'all' ? location.pathname : location.pathname + '?category=' + cat;
      history.replaceState(null, '', url);
      apply(cat);
    });
  }
})();
