/* Schedule Forensics — client-side display translation (ADR-0099).
 *
 * When the session language is not English, walk the rendered DOM's text nodes and translate them:
 * fixed UI terms from the embedded catalog (window.SF_I18N) are swapped instantly; everything else
 * (imported activity names, computed/AI prose) is batched to /api/translate, which uses the
 * configured local model and caches. A MutationObserver re-translates content added later (AJAX
 * grids, charts, AI answers). Numbers/dates/codes and inputs/scripts are left untouched. Falls back
 * to the source text for anything not translated — the page is never broken. Nothing leaves the
 * machine beyond the same local model the rest of the AI features already use.
 */
"use strict";

(function () {
  var lang = window.SF_LANG;
  if (!lang || lang === "en") return;
  var dict = window.SF_I18N || {};

  var SKIP_TAGS = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, INPUT: 1, SELECT: 1, OPTION: 1, CODE: 1, PRE: 1 };
  // text that is purely numeric / dates / codes / punctuation — never sent for translation
  var NON_TEXT = /^[\s\d.,:;/%+\-()$£€#×—–·…»«|]*$/;

  var memo = Object.create(null); // source text -> translation (catalog + fetched), this page
  var done = Object.create(null); // already-applied translation strings (don't re-translate them)
  var queue = {}; // pending source text -> [textNodes] awaiting the server
  var timer = null;

  function skip(node) {
    for (var p = node.parentNode; p; p = p.parentNode) {
      if (p.nodeType === 1 && (SKIP_TAGS[p.tagName] || p.hasAttribute("data-no-i18n"))) return true;
    }
    return false;
  }

  function apply(node, raw, translation) {
    done[translation] = 1; // so the resulting text is not itself re-translated by the observer
    var text = raw.replace(raw.trim(), translation);
    if (node.nodeValue !== text) node.nodeValue = text;
  }

  function handle(node) {
    var raw = node.nodeValue;
    if (!raw) return;
    var key = raw.trim();
    if (!key || NON_TEXT.test(key) || done[key]) return; // skip our own already-applied output
    if (dict[key] != null) { apply(node, raw, dict[key]); return; }
    if (memo[key] != null) { apply(node, raw, memo[key]); return; }
    (queue[key] = queue[key] || []).push(node);
  }

  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { if (!skip(root)) handle(root); return; }
    if (root.nodeType !== 1 || SKIP_TAGS[root.tagName] || root.hasAttribute("data-no-i18n")) return;
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var n, batch = [];
    while ((n = w.nextNode())) batch.push(n);
    batch.forEach(function (t) { if (!skip(t)) handle(t); });
    schedule();
  }

  function schedule() {
    if (timer) return;
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
            if (node.nodeValue) apply(node, node.nodeValue, es);
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
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
