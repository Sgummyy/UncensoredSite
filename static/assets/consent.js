/*!
 * Uncensored Runners – gestione consenso cookie (Vanilla JS, nessuna dipendenza)
 *
 * Blocco preventivo: nulla di terze parti viene caricato prima del consenso.
 * Per bloccare una risorsa basta marcarla così:
 *   <script type="text/plain" data-consent="statistiche" src="https://…"></script>
 *   <script type="text/plain" data-consent="statistiche"> …codice inline… </script>
 *   <iframe data-consent="media" data-src="https://…"></iframe>
 *   <img data-consent="media" data-src="https://…" alt="">
 * Quando l'utente acconsente alla categoria, la risorsa viene attivata.
 *
 * API: window.URConsent.has('media') · .grant('media') · .open() · .reset()
 * Evento: document 'ur:consent' con detail = { media: true, … }
 */
(function () {
  'use strict';

  /* ---------- configurazione ---------- */
  var VERSION = 1;                        // aumentalo se cambiano categorie o finalità: il banner verrà richiesto di nuovo
  var COOKIE = 'ur_consent';
  var MAX_AGE = 60 * 60 * 24 * 182;       // 6 mesi (Linee guida Garante Privacy, 10 giugno 2021)
  var POLICY_URL = '/cookie-policy/';
  var CATEGORIES = [
    { id: 'necessari', label: 'Necessari', locked: true,
      text: 'Servono al funzionamento del sito e a ricordare le tue scelte sui cookie. Non richiedono consenso.' },
    { id: 'media', label: 'Contenuti esterni (YouTube)',
      text: 'Permettono di vedere i video di YouTube direttamente nel sito. YouTube (Google) può impostare cookie e raccogliere dati di navigazione.' }
    /* Esempio per il futuro, se si aggiunge un sistema di statistiche:
    ,{ id: 'statistiche', label: 'Statistiche',
      text: 'Ci aiutano a capire in forma aggregata come viene usato il sito.' } */
  ];

  /* ---------- stato ---------- */
  function readCookie() {
    var m = document.cookie.match(new RegExp('(?:^|; )' + COOKIE + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : null;
  }
  function load() {
    var raw = readCookie();
    if (!raw) { try { raw = localStorage.getItem(COOKIE); } catch (e) {} }
    if (!raw) return null;
    try {
      var data = JSON.parse(raw);
      if (data.v !== VERSION) return null;
      if (Date.now() - data.t > MAX_AGE * 1000) return null;
      return data;
    } catch (e) { return null; }
  }
  function save(choices) {
    var data = { v: VERSION, t: Date.now(), c: choices };
    var raw = JSON.stringify(data);
    var secure = location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = COOKIE + '=' + encodeURIComponent(raw) + '; Max-Age=' + MAX_AGE + '; Path=/; SameSite=Lax' + secure;
    try { localStorage.setItem(COOKIE, raw); } catch (e) {}
    return data;
  }

  var state = load();
  var previous = state ? state.c : {};

  function has(cat) {
    if (cat === 'necessari') return true;
    return !!(state && state.c && state.c[cat]);
  }

  /* ---------- sblocco risorse ---------- */
  function activate() {
    var nodes = document.querySelectorAll('[data-consent]');
    Array.prototype.forEach.call(nodes, function (el) {
      var cat = el.getAttribute('data-consent');
      if (!has(cat) || el.getAttribute('data-consent-active')) return;
      el.setAttribute('data-consent-active', '1');
      if (el.tagName === 'SCRIPT' && el.type === 'text/plain') {
        var s = document.createElement('script');
        Array.prototype.forEach.call(el.attributes, function (a) {
          if (a.name !== 'type' && a.name !== 'data-consent') s.setAttribute(a.name, a.value);
        });
        if (!el.src) s.text = el.text;
        el.parentNode.replaceChild(s, el);
      } else if (el.hasAttribute('data-src')) {
        el.setAttribute('src', el.getAttribute('data-src'));
      }
    });
  }

  function apply(choices, fromUser) {
    // se l'utente revoca un consenso già dato, ricarichiamo la pagina per fermare gli script attivi
    var revoked = Object.keys(previous || {}).some(function (k) { return previous[k] && !choices[k]; });
    state = save(choices);
    previous = choices;
    activate();
    closeBanner();
    closePanel();
    try { document.dispatchEvent(new CustomEvent('ur:consent', { detail: choices })); } catch (e) {}
    if (revoked && fromUser) location.reload();
  }

  function all(value) {
    var c = {};
    CATEGORIES.forEach(function (cat) { if (!cat.locked) c[cat.id] = value; });
    return c;
  }

  /* ---------- interfaccia ---------- */
  var banner, panel, lastFocus;

  function el(tag, attrs, html) {
    var n = document.createElement(tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (html != null) n.innerHTML = html;
    return n;
  }

  function buildBanner() {
    banner = el('div', { class: 'cc-banner', role: 'region', 'aria-label': 'Preferenze cookie' },
      '<button class="cc-x" type="button" data-cc="reject" aria-label="Chiudi e rifiuta i cookie non necessari">' +
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M6 6l12 12M18 6L6 18"/></svg></button>' +
      '<p class="cc-title">Rispettiamo la tua privacy</p>' +
      '<p class="cc-text">Usiamo cookie tecnici necessari al funzionamento del sito. Con il tuo consenso attiviamo anche i video di YouTube, che possono usare cookie di terze parti. ' +
      'Puoi cambiare idea in qualsiasi momento da “Preferenze cookie” in fondo alla pagina. <a href="' + POLICY_URL + '">Cookie policy</a></p>' +
      '<div class="cc-actions">' +
        '<button type="button" class="cc-btn" data-cc="reject">Rifiuta</button>' +
        '<button type="button" class="cc-btn cc-link" data-cc="customize">Personalizza</button>' +
        '<button type="button" class="cc-btn" data-cc="accept">Accetta tutti</button>' +
      '</div>');
    document.body.appendChild(banner);
    document.documentElement.classList.add('cc-open');
  }

  function buildPanel() {
    var rows = CATEGORIES.map(function (cat) {
      var id = 'cc-' + cat.id;
      var checked = cat.locked || has(cat.id) ? ' checked' : '';
      var dis = cat.locked ? ' disabled' : '';
      return '<div class="cc-row"><div><label for="' + id + '"><b>' + cat.label + '</b>' + (cat.locked ? ' <small>Sempre attivi</small>' : '') + '</label>' +
        '<p>' + cat.text + '</p></div>' +
        '<span class="cc-switch"><input type="checkbox" id="' + id + '" data-cat="' + cat.id + '"' + checked + dis + '><span aria-hidden="true"></span></span></div>';
    }).join('');
    panel = el('div', { class: 'cc-overlay', role: 'presentation' },
      '<div class="cc-panel" role="dialog" aria-modal="true" aria-labelledby="cc-panel-title">' +
        '<div class="cc-head"><p class="cc-title" id="cc-panel-title">Preferenze cookie</p>' +
        '<button class="cc-x" type="button" data-cc="close" aria-label="Chiudi"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>' +
        '<p class="cc-text">Scegli quali categorie attivare. I dettagli sono nella <a href="' + POLICY_URL + '">cookie policy</a>.</p>' +
        rows +
        '<div class="cc-actions">' +
          '<button type="button" class="cc-btn" data-cc="reject">Rifiuta tutti</button>' +
          '<button type="button" class="cc-btn" data-cc="save">Salva le scelte</button>' +
          '<button type="button" class="cc-btn" data-cc="accept">Accetta tutti</button>' +
        '</div></div>');
    document.body.appendChild(panel);
    lastFocus = document.activeElement;
    var first = panel.querySelector('input:not([disabled])') || panel.querySelector('button');
    if (first) first.focus();
  }

  function closeBanner() {
    if (banner) { banner.remove(); banner = null; }
    document.documentElement.classList.remove('cc-open');
  }
  function closePanel() {
    if (panel) { panel.remove(); panel = null; if (lastFocus && lastFocus.focus) lastFocus.focus(); }
  }
  function open() { closePanel(); buildPanel(); }

  document.addEventListener('click', function (e) {
    var opener = e.target.closest('[data-consent-open]');
    if (opener) { e.preventDefault(); open(); return; }
    var b = e.target.closest('[data-cc]');
    if (!b) return;
    var act = b.getAttribute('data-cc');
    if (act === 'accept') apply(all(true), true);
    else if (act === 'reject') apply(all(false), true);
    else if (act === 'customize') open();
    else if (act === 'close') { closePanel(); }
    else if (act === 'save') {
      var c = {};
      Array.prototype.forEach.call(panel.querySelectorAll('input[data-cat]'), function (i) {
        if (!i.disabled) c[i.getAttribute('data-cat')] = i.checked;
      });
      apply(c, true);
    }
  });
  document.addEventListener('click', function (e) {
    if (panel && e.target === panel) closePanel();
  });
  document.addEventListener('keydown', function (e) {
    if (!panel) return;
    if (e.key === 'Escape') { closePanel(); return; }
    if (e.key === 'Tab') { // mantiene il focus dentro la finestra
      var f = panel.querySelectorAll('button, input:not([disabled]), a[href]');
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  window.URConsent = {
    has: has,
    grant: function (cat) { var c = {}; CATEGORIES.forEach(function (k) { if (!k.locked) c[k.id] = has(k.id); }); c[cat] = true; apply(c, false); },
    open: open,
    reset: function () { document.cookie = COOKIE + '=; Max-Age=0; Path=/'; try { localStorage.removeItem(COOKIE); } catch (e) {} location.reload(); }
  };

  function init() {
    activate();
    if (!state) buildBanner();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
