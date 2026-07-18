/* Schedule Forensics — client-side display translation (ADR-0099).
 *
 * When the session language is not English, translate the rendered page: fixed UI terms from the
 * embedded catalog (window.SF_I18N) are swapped instantly; text-node misses (imported activity
 * names, computed/AI prose) are batched to /api/translate, which uses the configured LOCAL model
 * and caches. A MutationObserver re-translates content added later (AJAX grids, charts, AI answers).
 *
 * NON-DESTRUCTIVE: every translated text node / attribute remembers its ORIGINAL English source and
 * we always translate FROM that source — never from already-translated text. So nodes are never
 * double-translated, the MutationObserver can't loop, and switching languages (back to English, or
 * between two non-English languages on a restored page) always re-renders correctly from source.
 *
 * Coverage includes user-facing ATTRIBUTES (placeholder/title/aria-label/alt) and <option> labels
 * via the catalog (catalog-only, so imported data values are left untouched). Numbers/dates/codes,
 * <input> values, scripts, and anything under data-no-i18n are left alone. Nothing leaves the
 * machine beyond the same local model the rest of the AI features already use.
 */
"use strict";

(function () {
  // ADR-0268: the boot payload rides a non-executable JSON block (the strict script-src CSP
  // forbids the old inline `window.SF_*=` script); parse it here, fail-soft to English.
  var boot = {};
  var bootEl = document.getElementById("sfI18nBoot");
  if (bootEl) { try { boot = JSON.parse(bootEl.textContent || "{}"); } catch (e) { boot = {}; } }
  var lang = boot.lang || "en";
  if (lang === "en") return; // English is the source language — nothing to translate or reset
  var dict = boot.catalog || {};

  // text nodes under these (or under data-no-i18n) are never translated
  var TEXT_SKIP = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, INPUT: 1, SELECT: 1, OPTION: 1, CODE: 1, PRE: 1 };
  // elements under these (or under data-no-i18n) get no attribute/option translation
  var ATTR_SKIP = { SCRIPT: 1, STYLE: 1, CODE: 1, PRE: 1, TEXTAREA: 1 };
  var ATTRS = ["placeholder", "title", "aria-label", "alt"];
  // purely numeric / date / code / punctuation text — never translated or sent to the model
  var NON_TEXT = /^[\s\d.,:;/%+\-()$£€#×—–·…»«|]*$/;
  var SRC = "__sfSrc";   // a text node's original English value (property on the node)
  var ASRC = "__sfAttr"; // an element's original English attribute values (object on the element)

  var memo = Object.create(null);  // source text -> model translation (fetched), this session
  var queue = {};                  // pending source text -> [text nodes] awaiting the server
  var timer = null;

  function underSkip(node, table) {
    for (var p = node.nodeType === 1 ? node : node.parentNode; p; p = p.parentNode) {
      if (p.nodeType === 1 && (table[p.tagName] || p.hasAttribute("data-no-i18n"))) return true;
    }
    return false;
  }

  // catalog-or-memo translation of a source string; null = unknown (caller may queue it)
  function lookup(src, catalogOnly) {
    var key = src.trim();
    if (!key || NON_TEXT.test(key)) return src;
    if (dict[key] != null) return src.replace(key, dict[key]);
    if (!catalogOnly && memo[key] != null) return src.replace(key, memo[key]);
    return null;
  }

  function setText(node, value) {
    if (node.nodeValue !== value) node.nodeValue = value;
  }

  // a text node: translate from its remembered English source (catalogOnly for <option> labels)
  function handleText(node, catalogOnly) {
    var src = SRC in node ? node[SRC] : node.nodeValue;
    if (src == null) return;
    if (lang === "en") { if (SRC in node) setText(node, src); return; }
    var out = lookup(src, catalogOnly);
    if (out != null) { node[SRC] = src; setText(node, out); return; }
    if (catalogOnly) return;            // unknown option label -> leave English
    node[SRC] = src;                    // unknown prose -> remember + queue for the model
    var key = src.trim();
    (queue[key] = queue[key] || []).push(node);
  }

  // an element's translatable attributes (catalog-only — short fixed UI strings, never data)
  function handleAttrs(el) {
    var store = null;
    for (var i = 0; i < ATTRS.length; i++) {
      var a = ATTRS[i];
      if (!el.hasAttribute(a) && !(el[ASRC] && a in el[ASRC])) continue;
      store = el[ASRC] || (el[ASRC] = {});
      var src = a in store ? store[a] : el.getAttribute(a);
      if (src == null) continue;
      if (lang === "en") { el.setAttribute(a, src); continue; }
      var out = lookup(src, true);
      if (out != null) { store[a] = src; el.setAttribute(a, out); }
    }
  }

  function handleOption(opt) {
    if (opt.firstChild && opt.firstChild.nodeType === 3) handleText(opt.firstChild, true);
  }

  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { if (!underSkip(root, TEXT_SKIP)) handleText(root); return; }
    if (root.nodeType !== 1) return;
    // text nodes
    var tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var n, texts = [];
    while ((n = tw.nextNode())) texts.push(n);
    texts.forEach(function (t) { if (!underSkip(t, TEXT_SKIP)) handleText(t); });
    // attributes + <option> labels, on root and every descendant element
    var els = [root];
    if (root.getElementsByTagName) {
      var all = root.getElementsByTagName("*");
      for (var i = 0; i < all.length; i++) els.push(all[i]);
    }
    els.forEach(function (e) {
      if (e.nodeType !== 1 || underSkip(e, ATTR_SKIP)) return;
      handleAttrs(e);
      if (e.tagName === "OPTION") handleOption(e);
    });
    schedule();
  }

  function schedule() {
    if (timer || lang === "en") return;
    timer = setTimeout(flush, 120);
  }

  function flush() {
    timer = null;
    var texts = Object.keys(queue);
    if (!texts.length) return;
    var sending = queue;
    queue = {};
    fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lang: lang, texts: texts }),
    })
      .then(function (r) { return r.ok ? r.json() : { translations: {} }; })
      .then(function (j) {
        var tr = (j && j.translations) || {};
        Object.keys(sending).forEach(function (key) {
          var es = tr[key];
          if (es == null) return; // no translation -> keep the source text
          memo[key] = es;
          sending[key].forEach(function (node) {
            var src = SRC in node ? node[SRC] : node.nodeValue;
            if (src != null) { node[SRC] = src; setText(node, src.replace(key, es)); }
          });
        });
      })
      .catch(function () { /* leave source text on failure */ });
  }

  function start() {
    walk(document.body);
    new MutationObserver(function (muts) {
      muts.forEach(function (m) {
        for (var i = 0; i < m.addedNodes.length; i++) walk(m.addedNodes[i]);
        if (m.type === "characterData") walk(m.target);
      });
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
    // a page restored from the back/forward cache may carry DOM translated to another language;
    // re-render from source so the language now in effect is what shows
    window.addEventListener("pageshow", function () { walk(document.body); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
