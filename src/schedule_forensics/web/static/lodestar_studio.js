// lodestar_studio.js — LODESTAR 2.0's studio controller (ADR-0543, the "Console" design handoff).
//
// The studio page is server-rendered and works with scripting off: every control is a plain form
// that posts to a v1 route and redirects. This script turns those same forms into live calls —
// it intercepts each submit, posts its fields as JSON to /api/<action> (an upload: the file, with
// Accept: application/json), and repaints from the answer: the server's state for the page,
// carrying the MAIN and RAIL regions as HTML (one renderer, in Python) and the slide's layout as
// data, which lodestar_slide.js paints. Nothing here decides a rule, a sentence or a coordinate.
//
// What lives only here is the interaction the design adds on top: picking two items on the slide
// (and dragging one onto the other), the data-date scrubber (fed by /api/preview while dragged),
// undo / redo on the keyboard, the ⌘K command palette, the full-screen slide, the guided tour,
// the Show-me demos (each run on /api/preview — a demo never changes the session or its log),
// the toasts, the client-side page tabs, and Print.
//
// Strict CSP (script-src 'self'): no inline script, no inline handlers — every listener is
// attached here, most of them delegated on the document so they survive a region swap.
(function () {
  "use strict";
  var D = document;
  function $(id) { return D.getElementById(id); }
  function readJson(id) {
    var n = $(id);
    if (!n) return null;
    try { return JSON.parse(n.textContent || "null"); } catch (e) { return null; }
  }
  var CFG = readJson("lsConfig"), S = readJson("lsState");
  if (!CFG || !S) return;

  var view = {
    page: S.page, slide: null, full: null,
    pick: { from: "", to: "", kind: "FS" }, hover: "", drag: null,
    dataOpen: false, historyOpen: false, tour: null, demo: null, timers: [],
    scrubbing: false, previewSeq: 0, autoTourDone: false, busy: false,
  };
  try { view.autoTourDone = sessionStorage.getItem("lodestar-tour-seen") === "1"; } catch (e) { /* none */ }

  // ── talking to the server ──────────────────────────────────────────────────────────────────
  function post(url, body) {
    return fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body || {}),
    }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, data: j }; }); });
  }
  function act(action, fields) {
    if (view.busy && action !== "preview") return Promise.resolve(null);
    view.busy = true;
    var body = Object.assign({ page: view.page }, fields || {});
    return post("/api/" + action, body).then(function (res) {
      view.busy = false;
      if (!res.ok) { toast(res.data && res.data.error ? res.data.error : "LODESTAR refused that.", "warn"); return null; }
      apply(res.data);
      return res.data;
    }, function () { view.busy = false; toast("LODESTAR is not answering — is its window still open?", "fail"); return null; });
  }
  function upload(form, file) {
    var fd = new FormData(form);
    if (file) fd.set("file", file, file.name);
    form.classList.add("is-busy");
    return fetch(form.getAttribute("action"), {
      method: "POST", credentials: "same-origin", headers: { Accept: "application/json" }, body: fd,
    }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, data: j }; }); })
      .then(function (res) {
        form.classList.remove("is-busy");
        if (!res.ok) { toast(res.data && res.data.error ? res.data.error : "The list was not loaded.", "warn"); return; }
        apply(res.data);
        maybeAutoTour(res.data);
      }, function () { form.classList.remove("is-busy"); toast("The upload did not reach LODESTAR.", "fail"); });
  }
  function loadPage(page, push) {
    return fetch("/api/state?page=" + encodeURIComponent(page), { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (r) { return r.json(); })
      .then(function (st) {
        stopDemo();
        view.pick = { from: "", to: "", kind: view.pick.kind };
        apply(st);
        if (push) try { history.pushState({ page: page }, "", st.path); } catch (e) { /* file: */ }
      });
  }

  // ── applying a state: swap the regions, repaint the slide, refresh the frame ───────────────
  function swap(id, html) {
    var host = $(id);
    if (!host || typeof html !== "string") return;
    var active = D.activeElement, keep = active && host.contains(active) && active.id ? active.id : "";
    var scroll = host.scrollTop;
    host.innerHTML = html;
    host.scrollTop = scroll;
    if (keep) { var again = $(keep); if (again && again.focus) try { again.focus({ preventScroll: true }); } catch (e) { again.focus(); } }
  }
  function apply(st) {
    if (!st) return;
    S = st;
    view.page = st.page;
    if (st.regions) { swap("lsMain", st.regions.main); swap("lsRail", st.regions.rail); }
    D.body.setAttribute("data-page", st.page);
    D.title = (CFG.pages[st.page] ? CFG.pages[st.page].label : "Timeline") + " — LODESTAR";
    frame(st);
    restoreRail();
    paintSlide(st.reveal);
    if (st.toast) toast(st.toast.text, st.toast.status);
    // the inline banner is the page's one-shot message; the toast says the same — keep one
    if (st.toast && st.banner && st.toast.text === st.banner.text) { var b = $("lsBanner"); if (b) b.parentNode.removeChild(b); }
    if (view.tour) placeTour();
  }
  function frame(st) {
    // the page tabs
    Array.prototype.forEach.call(D.querySelectorAll("[data-ls-tab]"), function (a) {
      var on = a.getAttribute("data-ls-tab") === st.page;
      a.classList.toggle("aismat-tab--active", on);
      a.setAttribute("aria-selected", on ? "true" : "false");
      if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    Array.prototype.forEach.call(D.querySelectorAll("[data-ls-next]"), function (i) { i.value = st.path; });
    // undo / redo
    var u = $("lsUndo"), r = $("lsRedo");
    if (u) { u.disabled = !st.canUndo; u.title = st.canUndo ? "Undo — " + st.undoLabel : "Nothing to undo"; u.setAttribute("aria-label", u.title); }
    if (r) { r.disabled = !st.canRedo; r.title = st.canRedo ? "Redo — " + st.redoLabel : "Nothing to redo"; r.setAttribute("aria-label", r.title); }
    // the marking: both bars, the print bars, the switch
    var m = st.marking;
    Array.prototype.forEach.call(D.querySelectorAll("[data-ls-mark]"), function (bar) {
      bar.textContent = m.text;
      bar.style.background = m.bg;
      bar.style.color = m.fg;
    });
    var mb = $("lsMarking");
    if (mb) { var sp = mb.querySelector("span"); if (sp) sp.textContent = m.flipLabel; }
    Array.prototype.forEach.call(D.querySelectorAll("[data-ls-flip]"), function (i) { i.value = m.flip; });
    // the change history (the header's history button)
    var hp = $("lsHistory");
    if (hp) hp.hidden = !view.historyOpen;
    var hb = D.querySelector("[data-ls-history]");
    if (hb) { hb.classList.toggle("aismat-iconbtn--active", view.historyOpen); hb.setAttribute("aria-pressed", view.historyOpen ? "true" : "false"); }
  }
  function restoreRail() {
    // the DATA drawer and the link type survive a swap
    var data = $("lsData"), db = D.querySelector("[data-ls-data]");
    if (data) data.hidden = !view.dataOpen;
    if (db) { db.classList.toggle("aismat-iconbtn--active", view.dataOpen); db.setAttribute("aria-pressed", view.dataOpen ? "true" : "false"); }
    var radios = D.querySelectorAll("#lsKind input[name=kind]");
    Array.prototype.forEach.call(radios, function (r) { r.checked = r.value === view.pick.kind; });
    markKind();
    // a pick survives a swap when both its items are still linkable
    var ok = {};
    (S.linkable || []).forEach(function (x) { ok[x.key] = true; });
    if (view.pick.from && !ok[view.pick.from]) view.pick.from = "";
    if (view.pick.to && !ok[view.pick.to]) view.pick.to = "";
    syncPick();
  }

  // ── the slide ──────────────────────────────────────────────────────────────────────────────
  function linkableSet() {
    var m = {};
    (S.linkable || []).forEach(function (x) { m[x.key] = x.label; });
    return m;
  }
  function paintSlide(reveal, layout) {
    var host = $("lsSlide");
    var L = layout || S.layout;
    if (!host || !L || !window.LSSlide) { view.slide = null; return; }
    var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    view.slide = LSSlide.paint(host, L, { reveal: !!reveal && !reduced, linkable: linkableSet() });
    rings();
    paintMarks();
    if (!$("lsFull").hidden) openFull();
  }
  function rings() {
    if (!view.slide) return;
    var d = view.demo;
    LSSlide.setRings(view.slide, {
      from: view.pick.from, to: view.pick.to, hover: view.hover,
      demo: d && d.keys ? d.keys : [], demoTag: d && d.tag ? d.tag : null,
    });
    LSSlide.setLead(view.slide, view.drag && view.drag.moved ? view.drag : (d && d.drag ? d.drag : null));
  }
  function paintMarks() {
    var m = S.marking;
    Array.prototype.forEach.call(D.querySelectorAll(".ls-print-mark"), function (bar) {
      bar.textContent = m.text; bar.style.background = m.bg; bar.style.color = m.fg;
    });
  }

  // ── picking two items, and dragging one onto the other ─────────────────────────────────────
  function labelOf(key) { var m = linkableSet(); return m[key] || ""; }
  function syncPick() {
    var f = $("lsFrom"), t = $("lsTo"), add = $("lsAddLink");
    if (f) f.value = view.pick.from;
    if (t) t.value = view.pick.to;
    if (add) add.disabled = !(view.pick.from && view.pick.to);
    var hint = $("lsHintText");
    if (hint) {
      if (view.pick.from && view.pick.to) hint.textContent = "From " + labelOf(view.pick.from) + " to " + labelOf(view.pick.to) + " — choose the type and press Add logic link.";
      else if (view.pick.from) hint.textContent = "From " + labelOf(view.pick.from) + " — now pick the successor on the slide or in the list.";
      else hint.textContent = CFG.hintNone;
    }
    rings();
  }
  function markKind() {
    Array.prototype.forEach.call(D.querySelectorAll("#lsKind label"), function (lab) {
      var r = lab.querySelector("input");
      lab.classList.toggle("aismat-tab--active", !!(r && r.checked));
    });
    var nm = $("lsKindName");
    if (nm) nm.textContent = CFG.linkNames[view.pick.kind] || view.pick.kind;
  }
  function pickItem(key) {
    var p = view.pick;
    if (!linkableSet()[key]) return;
    if (key === p.from && !p.to) p.from = "";
    else if (!p.from || p.to) { p.from = key; p.to = ""; }
    else p.to = key;
    syncPick();
  }
  function itemKey(target) {
    var g = target && target.closest ? target.closest("[data-key]") : null;
    var k = g ? g.getAttribute("data-key") : "";
    return k && linkableSet()[k] ? k : "";
  }
  function addLink(pred, succ, kind) {
    return act("links", { action: "add", pred: pred, succ: succ, kind: kind || view.pick.kind }).then(function (st) {
      if (st && st.label) view.pick = { from: "", to: "", kind: view.pick.kind };
      syncPick();
    });
  }
  D.addEventListener("pointerdown", function (ev) {
    if (view.demo || ev.button !== 0) return;
    var svg = ev.target.closest ? ev.target.closest("#lsSlide svg") : null;
    if (!svg) return;
    var key = itemKey(ev.target);
    if (!key) return;
    var pt = LSSlide.point(svg, ev);
    view.drag = { from: key, sx: pt ? pt.x : 0, sy: pt ? pt.y : 0, x: null, y: null, moved: false, over: false, kind: view.pick.kind };
    ev.preventDefault();
  });
  D.addEventListener("pointermove", function (ev) {
    var svg = D.querySelector("#lsSlide svg");
    if (view.drag && svg) {
      var pt = LSSlide.point(svg, ev);
      if (!pt) return;
      if (!view.drag.moved && Math.hypot(pt.x - view.drag.sx, pt.y - view.drag.sy) <= 3) return;
      var under = D.elementFromPoint(ev.clientX, ev.clientY), over = itemKey(under);
      view.drag.moved = true; view.drag.x = pt.x; view.drag.y = pt.y;
      view.drag.over = !!over && over !== view.drag.from;
      view.drag.target = view.drag.over ? over : "";
      view.hover = view.drag.target;
      rings();
      return;
    }
    if (!svg || view.demo) return;
    var k = ev.target.closest && ev.target.closest("#lsSlide svg") ? itemKey(ev.target) : "";
    if (k !== view.hover) { view.hover = k; rings(); }
  });
  D.addEventListener("pointerup", function (ev) {
    var d = view.drag;
    if (!d) return;
    view.drag = null;
    if (d.moved) {
      view.hover = "";
      if (d.over && d.target) addLink(d.from, d.target, view.pick.kind).then(function () {
        if (S && S.toast === null) return;
      });
      rings();
      return;
    }
    var key = itemKey(ev.target);
    if (key === d.from) pickItem(key);
    rings();
  });
  D.addEventListener("pointercancel", function () { view.drag = null; rings(); });

  // ── forms: every submit becomes a live call (scripting off, they post as they are) ──────────
  var API = { title: 1, window: 1, today: 1, clear: 1, links: 1, swap: 1, example: 1 };
  D.addEventListener("submit", function (ev) {
    var form = ev.target, url = form.getAttribute("action") || "";
    if (url === "/quit") { stopDemo(); return; } // the stopped page is a real navigation
    var path = url.split("#")[0], seg = path.split("/").pop();
    var fd = new FormData(form);
    if (ev.submitter && ev.submitter.name) fd.set(ev.submitter.name, ev.submitter.value);
    var fields = {};
    fd.forEach(function (v, k) { if (typeof v === "string" && k !== "next") fields[k] = v; });
    if (seg === "upload") {
      ev.preventDefault();
      var input = form.querySelector("input[type=file]");
      if (input && input.files && input.files.length) upload(form);
      else if (input) input.click();
      return;
    }
    if (path === "/marking") { ev.preventDefault(); act("marking", fields); return; }
    if (path === "/undo" || path === "/redo") { ev.preventDefault(); act(seg, {}); return; }
    if (!API[seg]) return;
    ev.preventDefault();
    fields.page = path.indexOf("/onepager-compare") === 0 ? "compare" : "timeline";
    if (seg === "links" && fields.action === "add") {
      fields.pred = fields.pred || view.pick.from; fields.succ = fields.succ || view.pick.to;
      addLink(fields.pred, fields.succ, fields.kind || view.pick.kind);
      return;
    }
    act(seg, fields).then(function (st) { if (seg === "example") maybeAutoTour(st); });
  });
  // the title commits on blur / Enter; a date input commits when it changes
  D.addEventListener("change", function (ev) {
    var t = ev.target;
    if (t.id === "lsTitle" && t.form) { t.form.requestSubmit(); return; }
    if (t.id === "lsToday" && t.form && t.value) { t.form.requestSubmit(); return; }
    if (t.id === "lsFrom") { view.pick.from = t.value; syncPick(); return; }
    if (t.id === "lsTo") { view.pick.to = t.value; syncPick(); return; }
    if (t.name === "kind" && t.closest && t.closest("#lsKind")) { view.pick.kind = t.value; markKind(); rings(); return; }
    if (t.type === "file" && t.form && t.files && t.files.length) { upload(t.form); return; }
  });
  D.addEventListener("keydown", function (ev) {
    if (ev.key === "Enter" && ev.target && ev.target.id === "lsTitle") { ev.preventDefault(); ev.target.blur(); }
  });

  // ── drop zones ─────────────────────────────────────────────────────────────────────────────
  function zoneOf(target) { return target && target.closest ? target.closest("[data-ls-drop]") : null; }
  ["dragenter", "dragover"].forEach(function (name) {
    D.addEventListener(name, function (ev) {
      ev.preventDefault();
      var z = zoneOf(ev.target);
      Array.prototype.forEach.call(D.querySelectorAll("[data-ls-drop]"), function (n) { n.classList.toggle("is-over", n === z); });
    });
  });
  D.addEventListener("dragleave", function (ev) {
    var z = zoneOf(ev.target);
    if (z && !z.contains(ev.relatedTarget)) z.classList.remove("is-over");
  });
  D.addEventListener("drop", function (ev) {
    ev.preventDefault();
    Array.prototype.forEach.call(D.querySelectorAll("[data-ls-drop]"), function (n) { n.classList.remove("is-over"); });
    var files = ev.dataTransfer && ev.dataTransfer.files;
    if (!files || !files.length) return;
    var z = zoneOf(ev.target);
    if (!z && view.page === "timeline") z = $("lsDrop"); // the Timeline takes a drop anywhere
    if (!z) {
      var hint = $("lsDropHint");
      var msg = "Drop the workbook onto the PRIOR or the CURRENT slot — the page never guesses which list is which.";
      if (hint) { hint.textContent = msg; hint.hidden = false; }
      toast(msg, "warn");
      return;
    }
    upload(z, files[0]);
  });
  D.addEventListener("click", function (ev) {
    var t = ev.target.closest ? ev.target : null;
    if (!t) return;
    var pick = t.closest("[data-ls-pick]");
    if (pick) {
      var which = pick.getAttribute("data-ls-pick");
      var input = $(which === "prior" ? "lsFilePrior" : which === "current" ? "lsFileCurrent" : "lsFile");
      if (input) input.click();
      return;
    }
    if (t.closest("[data-ls-dismiss]")) { var tst = t.closest(".aismat-toast"); if (tst) (tst.closest(".ls-banner") || tst).remove(); return; }
    if (t.closest("[data-ls-data]")) { view.dataOpen = !view.dataOpen; restoreRail(); return; }
    if (t.closest("[data-ls-history]")) { view.historyOpen = !view.historyOpen; frame(S); return; }
    if (t.closest("[data-ls-full]")) { openFull(); return; }
    if (t.closest("[data-ls-print]")) { printSlide(); return; }
    if (t.closest("[data-ls-palette]")) { togglePalette(); return; }
    if (t.closest("[data-ls-tour]")) { startTour(0); return; }
    if (t.closest("[data-ls-tour-end]")) { endTour(); return; }
    if (t.closest("[data-ls-tour-next]")) { nextTour(1); return; }
    if (t.closest("[data-ls-tour-back]")) { nextTour(-1); return; }
    if (t.closest("[data-ls-demo-stop]")) { stopDemo(); return; }
    var dm = t.closest("[data-ls-demo]");
    if (dm) { runDemo(dm.getAttribute("data-ls-demo")); return; }
    if (t.closest("[data-ls-explain]")) { runDemo(view.page === "compare" ? "compare" : "links"); return; }
    var tab = t.closest("[data-ls-tab]");
    if (tab && !ev.metaKey && !ev.ctrlKey && !ev.shiftKey) {
      ev.preventDefault();
      var page = tab.getAttribute("data-ls-tab");
      if (page !== view.page) loadPage(page, true);
      return;
    }
    if (t.id === "lsFull" ) closeFull();
    var pal = $("lsPalette");
    if (pal && !pal.hidden && t === pal) closePalette();
    var item = t.closest(".ls-palette-item");
    if (item) { runCommand(+item.getAttribute("data-i")); return; }
  });
  window.addEventListener("popstate", function (ev) {
    var page = ev.state && ev.state.page ? ev.state.page : (location.pathname.indexOf("/onepager-compare") === 0 ? "compare" : "timeline");
    if (page !== view.page) loadPage(page, false);
  });

  // ── the data-date scrubber ─────────────────────────────────────────────────────────────────
  function addDays(iso, n) {
    var p = iso.split("-"), d = new Date(Date.UTC(+p[0], +p[1] - 1, +p[2] + n));
    return d.toISOString().slice(0, 10);
  }
  var previewTimer = null;
  function previewToday(iso) {
    var seq = ++view.previewSeq;
    clearTimeout(previewTimer);
    previewTimer = setTimeout(function () {
      post("/api/preview", { page: view.page, today: iso }).then(function (res) {
        if (!res.ok || seq !== view.previewSeq || !view.scrubbing) return;
        if (res.data.layout) paintSlide(false, res.data.layout);
      });
    }, 90);
  }
  D.addEventListener("input", function (ev) {
    var t = ev.target;
    if (t.id === "lsPaletteQ") { renderPalette(); return; }
    if (t.id !== "lsScrubRange") return;
    view.scrubbing = true;
    var iso = addDays(t.getAttribute("data-first"), +t.value), box = $("lsToday");
    if (box) box.value = iso;
    if (view.slide) LSSlide.moveDataDate(view.slide, iso);
    previewToday(iso);
  });
  function commitScrub(ev) {
    var t = ev.target;
    if (!t || t.id !== "lsScrubRange" || !view.scrubbing) return;
    view.scrubbing = false;
    view.previewSeq++;
    var iso = addDays(t.getAttribute("data-first"), +t.value);
    act("today", { today: iso, action: "apply" });
  }
  D.addEventListener("change", commitScrub);

  // ── keyboard ───────────────────────────────────────────────────────────────────────────────
  D.addEventListener("keydown", function (ev) {
    if (ev.defaultPrevented) return;
    var tag = (ev.target && ev.target.tagName || "").toLowerCase();
    var typing = tag === "input" || tag === "select" || tag === "textarea";
    var mod = ev.metaKey || ev.ctrlKey;
    if (ev.key === "Escape") {
      if (!$("lsPalette").hidden) { closePalette(); return; }
      if (view.tour) { endTour(); return; }
      if (!$("lsFull").hidden) { closeFull(); return; }
      if (view.demo) { stopDemo(); return; }
      if (view.pick.from || view.pick.to) { view.pick.from = view.pick.to = ""; syncPick(); }
      return;
    }
    if (mod && ev.key.toLowerCase() === "k") { ev.preventDefault(); togglePalette(); return; }
    if (!$("lsPalette").hidden) { paletteKeys(ev); return; }
    if (typing) return;
    if (mod && ev.key.toLowerCase() === "z") { ev.preventDefault(); act(ev.shiftKey ? "redo" : "undo", {}); return; }
    if (mod && ev.key.toLowerCase() === "y") { ev.preventDefault(); act("redo", {}); }
  });

  // ── toasts ─────────────────────────────────────────────────────────────────────────────────
  var ICON = { pass: "circle-check", warn: "triangle-alert", fail: "circle-alert", info: "info" };
  function svgIcon(name, size) {
    return '<svg class="aismat-icon" width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><use href="#i-' + name + '"/></svg>';
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function toast(text, status) {
    if (!text) return;
    var box = $("lsToasts");
    if (!box) return;
    status = ICON[status] ? status : "info";
    var n = D.createElement("div");
    n.className = "aismat-toast aismat-toast--" + status;
    n.setAttribute("role", status === "warn" || status === "fail" ? "alert" : "status");
    n.innerHTML = '<span class="aismat-toast__icon">' + svgIcon(ICON[status], 16) + '</span><div class="aismat-toast__body"><div class="aismat-toast__msg">' + esc(text) +
      '</div></div><button type="button" class="aismat-iconbtn aismat-iconbtn--sm" aria-label="Dismiss" title="Dismiss" data-ls-dismiss>' + svgIcon("x", 15) + "</button>";
    box.appendChild(n);
    while (box.children.length > 3) box.removeChild(box.firstChild);
    setTimeout(function () { if (n.parentNode) n.parentNode.removeChild(n); }, 4200);
  }

  // ── print: the slide alone, landscape, on a white ground ───────────────────────────────────
  function printSlide() {
    if (!view.slide) { toast("There is no slide to print yet — load a list first.", "warn"); return; }
    paintMarks();
    try { window.print(); } catch (e) { /* the browser has no print */ }
  }

  // ── full-screen slide ──────────────────────────────────────────────────────────────────────
  function openFull() {
    var L = S.layout, box = $("lsFullBox"), f = $("lsFull");
    if (!L || !box) return;
    LSSlide.paint(box, L, { linkable: {} });
    f.hidden = false;
  }
  function closeFull() { var f = $("lsFull"); if (f) f.hidden = true; }
  $("lsFull").addEventListener("click", function (ev) { if (ev.target === $("lsFull")) closeFull(); });

  // ── the command palette ────────────────────────────────────────────────────────────────────
  var paletteSel = 0, paletteList = [];
  function exportLink(id) { var a = $(id); if (a) a.click(); else toast("Load a list first — there is nothing to export yet.", "warn"); }
  function commands() {
    var c = [
      { label: S.loaded.timeline ? "Replace the list" : "Load a list", hint: "Timeline", run: function () { goThen("timeline", function () { var i = $("lsFile"); if (i) i.click(); }); } },
      { label: "Load the PRIOR list", hint: "Compare", run: function () { goThen("compare", function () { var i = $("lsFilePrior"); if (i) i.click(); }); } },
      { label: "Load the CURRENT list", hint: "Compare", run: function () { goThen("compare", function () { var i = $("lsFileCurrent"); if (i) i.click(); }); } },
      { label: "Load the example list", hint: "Timeline", run: function () { goThen("timeline", function () { act("example", { page: "timeline" }).then(maybeAutoTour); }); } },
      { label: "Load the example pair (PRIOR and CURRENT)", hint: "Compare", run: function () { goThen("compare", function () { act("example", { page: "compare" }); }); } },
      { label: "Go to Timeline", hint: "page", run: function () { if (view.page !== "timeline") loadPage("timeline", true); } },
      { label: "Go to Compare", hint: "page", run: function () { if (view.page !== "compare") loadPage("compare", true); } },
      { label: "Export PowerPoint", hint: "⤓ .pptx", run: function () { exportLink("lsPptx"); } },
      { label: "Export Excel", hint: "⤓ .xlsx", run: function () { exportLink("lsXlsx"); } },
      { label: "Print the slide as PDF", hint: "print", run: printSlide },
      { label: "Show all dates", hint: "window", run: function () { act("window", { action: "clear" }); } },
      { label: "Use the computer's date", hint: "data date", run: function () { act("today", { action: "clear" }); } },
      { label: "Remove all logic links", hint: "links", run: function () { act("links", { action: "clear" }); } },
      { label: S.marking.flipLabel, hint: "marking", run: function () { act("marking", { marking: S.marking.flip }); } },
      { label: "Start the guided tour", hint: "help", run: function () { startTour(0); } },
      { label: "Undo — " + (S.canUndo ? S.undoLabel : "nothing to undo"), hint: "⌘Z", run: function () { act("undo", {}); } },
      { label: "Redo — " + (S.canRedo ? S.redoLabel : "nothing to redo"), hint: "⇧⌘Z", run: function () { act("redo", {}); } },
      { label: "Quit LODESTAR", hint: "stops the program", run: function () { var q = D.querySelector('form[action="/quit"]'); if (q) q.requestSubmit(); } },
    ];
    CFG.views.forEach(function (v) { c.push({ label: "View: " + v.label, hint: "appearance", run: function () { if (window.LSView) LSView.set(v.value); } }); });
    CFG.demos.forEach(function (d) { c.push({ label: "Show me: " + d.label, hint: "demo", run: function () { runDemo(d.id); } }); });
    return c;
  }
  function goThen(page, fn) {
    closePalette();
    if (page === view.page) { fn(); return; }
    loadPage(page, true).then(function () { setTimeout(fn, 30); });
  }
  function renderPalette() {
    var q = ($("lsPaletteQ").value || "").toLowerCase(), list = $("lsPaletteList");
    paletteList = commands().filter(function (c) { return !q || (c.label + " " + c.hint).toLowerCase().indexOf(q) >= 0; }).slice(0, 12);
    if (paletteSel >= paletteList.length) paletteSel = 0;
    list.innerHTML = paletteList.length ? paletteList.map(function (c, i) {
      return '<li role="option" aria-selected="' + (i === paletteSel) + '"><button type="button" class="ls-palette-item' + (i === paletteSel ? " is-sel" : "") + '" data-i="' + i + '"><span>' + esc(c.label) + '</span><span class="ls-palette-hint">' + esc(c.hint) + "</span></button></li>";
    }).join("") : '<li class="ls-palette-none">No command matches.</li>';
  }
  function togglePalette() { if ($("lsPalette").hidden) openPalette(); else closePalette(); }
  function openPalette() {
    var p = $("lsPalette"), q = $("lsPaletteQ");
    p.hidden = false; q.value = ""; paletteSel = 0; renderPalette();
    setTimeout(function () { q.focus(); }, 0);
  }
  function closePalette() { $("lsPalette").hidden = true; }
  function runCommand(i) { var c = paletteList[i]; if (!c) return; closePalette(); c.run(); }
  function paletteKeys(ev) {
    if (ev.key === "ArrowDown") { ev.preventDefault(); paletteSel = Math.min(paletteList.length - 1, paletteSel + 1); renderPalette(); }
    else if (ev.key === "ArrowUp") { ev.preventDefault(); paletteSel = Math.max(0, paletteSel - 1); renderPalette(); }
    else if (ev.key === "Enter") { ev.preventDefault(); runCommand(paletteSel); }
  }
  $("lsPalette").addEventListener("click", function (ev) { if (ev.target === $("lsPalette")) closePalette(); });

  // ── the guided tour ────────────────────────────────────────────────────────────────────────
  function startTour(step) {
    stopDemo();
    closePalette();
    view.tour = { step: step || 0 };
    try { sessionStorage.setItem("lodestar-tour-seen", "1"); } catch (e) { /* none */ }
    view.autoTourDone = true;
    $("lsTour").hidden = false;
    placeTour();
  }
  function endTour() { view.tour = null; $("lsTour").hidden = true; }
  function nextTour(d) {
    if (!view.tour) return;
    var n = view.tour.step + d;
    if (n < 0) return;
    if (n >= CFG.tour.length) { endTour(); return; }
    view.tour.step = n;
    placeTour();
  }
  function placeTour() {
    if (!view.tour) return;
    var step = CFG.tour[view.tour.step], root = $("lsRoot"), tour = $("lsTour");
    var target = D.querySelector('[data-tour="' + step.target + '"]');
    if (target && target.scrollIntoView) target.scrollIntoView({ block: "nearest" });
    var rr = root.getBoundingClientRect(), spot = $("lsTourSpot"), card = $("lsTourCard");
    var missing = !target || !target.getClientRects().length;
    tour.classList.toggle("is-missing", missing);
    var cardW = 320, cardH = card.offsetHeight || 170, x, y;
    if (missing) {
      x = rr.width / 2 - cardW / 2; y = rr.height / 2 - cardH / 2;
    } else {
      var tr = target.getBoundingClientRect();
      var r = { x: tr.left - rr.left, y: tr.top - rr.top, w: tr.width, h: tr.height };
      spot.style.left = (r.x - 6) + "px"; spot.style.top = (r.y - 6) + "px";
      spot.style.width = (r.w + 12) + "px"; spot.style.height = (r.h + 12) + "px";
      x = Math.max(12, Math.min(rr.width - cardW - 12, r.x + r.w / 2 - cardW / 2));
      var below = r.y + r.h + 14;
      y = below + cardH < rr.height ? below : Math.max(12, r.y - cardH - 14);
    }
    card.style.left = x + "px"; card.style.top = y + "px";
    $("lsTourStep").textContent = "STEP " + (view.tour.step + 1) + " OF " + CFG.tour.length;
    $("lsTourTitle").textContent = step.title;
    $("lsTourBody").textContent = step.body;
    $("lsTourNext").textContent = view.tour.step === CFG.tour.length - 1 ? "Finish" : "Next";
    var back = D.querySelector("[data-ls-tour-back]");
    if (back) back.disabled = view.tour.step === 0;
    var dots = $("lsTourDots");
    Array.prototype.forEach.call(dots.querySelectorAll(".ls-tour-dot"), function (n) { n.parentNode.removeChild(n); });
    CFG.tour.forEach(function (_t, i) {
      var dot = D.createElement("span");
      dot.className = "ls-tour-dot" + (i === view.tour.step ? " is-active" : i < view.tour.step ? " is-done" : "");
      dots.insertBefore(dot, dots.firstChild ? dots.querySelector(".ls-spacer") : null);
    });
  }
  window.addEventListener("resize", function () { if (view.tour) placeTour(); });
  function maybeAutoTour(st) {
    // the tour starts by itself after the FIRST list load of a session, from step 2
    if (!st || !st.label || view.autoTourDone || st.page !== "timeline") return;
    setTimeout(function () { startTour(1); }, 650);
  }

  // ── the Show-me demos: each runs on /api/preview, so nothing is committed or logged ────────
  function later(ms, fn) { view.timers.push(setTimeout(fn, ms)); }
  function say(text) {
    var n = $("lsDemoNote"), t = $("lsDemoText");
    if (!n || !t) return;
    t.textContent = text; n.hidden = !text;
  }
  function stopDemo() {
    view.timers.forEach(clearTimeout);
    view.timers = [];
    if (!view.demo) return;
    view.demo = null;
    say("");
    D.querySelectorAll("[data-ls-demo]").forEach(function (b) { b.classList.remove("is-active"); });
    var box = $("lsDemoBox");
    if (box && !S.layout) { box.hidden = true; var anim = D.querySelector(".ls-empty-anim"); if (anim) anim.hidden = false; }
    paintSlide(false);
  }
  function preview(body) {
    return post("/api/preview", Object.assign({ page: view.page }, body)).then(function (res) { return res.ok ? res.data.layout : null; });
  }
  function keysOf(L) { return L ? L.items.filter(function (p) { return p.key && p.x0 !== null; }).map(function (p) { return p.key; }) : []; }
  function longDate(iso) {
    var M = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], p = iso.split("-");
    return M[+p[1] - 1] + " " + (+p[2]) + ", " + p[0];
  }
  function monthYear(iso) { var M = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], p = iso.split("-"); return M[+p[1] - 1] + " " + p[0]; }
  function runDemo(id) {
    stopDemo();
    endTour();
    var btn = D.querySelector('[data-ls-demo="' + id + '"]');
    if (id === "compare" && view.page !== "compare") { loadPage("compare", true).then(function () { runDemo("compare"); }); return; }
    if (id !== "compare" && view.page !== "timeline") { loadPage("timeline", true).then(function () { runDemo(id); }); return; }
    view.demo = { id: id, keys: [] };
    if (btn) btn.classList.add("is-active");
    // an empty page runs the demo on the example list (or pair) — shown, never loaded
    var base = S.layout ? Promise.resolve(S.layout) : preview({ example: true });
    base.then(function (L) {
      if (!view.demo || view.demo.id !== id) return;
      if (!L) { stopDemo(); toast("There is nothing to demonstrate on yet.", "warn"); return; }
      // the empty studio shows the example slide in its demo box, in place of the animation
      var box = $("lsDemoBox");
      if (!S.layout && box) { box.hidden = false; var anim = D.querySelector(".ls-empty-anim"); if (anim) anim.hidden = true; }
      if (!$("lsSlide")) { stopDemo(); return; }
      paintSlide(false, L);
      var example = !S.layout;
      demoScripts[id](L, example);
    });
  }
  function demoPaint(L) { paintSlide(false, L); }
  var demoScripts = {
    links: function (L, example) {
      var k = keysOf(L), pred = k[1] || k[0], succ = k[3] || k[2] || k[0];
      if (!pred || !succ || pred === succ) { stopDemo(); toast("The slide needs two items to link.", "info"); return; }
      later(100, function () { view.demo.keys = [pred]; view.demo.tag = "FROM"; rings(); say("1 · Click the predecessor — the item the logic starts from."); });
      later(1400, function () { view.demo.keys = [succ]; view.demo.tag = "TO"; view.pick = { from: pred, to: "", kind: view.pick.kind }; rings(); say("2 · Click the successor. Both are ringed and tagged FROM and TO."); });
      later(2600, function () { view.demo.keys = []; view.pick.to = succ; rings(); say("3 · Choose the type (Finish-to-Start by default) and press Add logic link."); });
      later(3900, function () {
        preview({ pred: pred, succ: succ, kind: view.pick.kind, example: example }).then(function (L2) {
          if (!view.demo) return;
          view.pick = { from: "", to: "", kind: view.pick.kind };
          if (L2) demoPaint(L2);
          say("4 · The arrow is routed on the slide and carried into PowerPoint. Only the links you add are drawn.");
        });
      });
      later(6900, stopDemo);
    },
    drag: function (L, example) {
      var k = keysOf(L), pred = k[1] || k[0], succ = k[3] || k[2] || k[0];
      var P = L.items.filter(function (p) { return p.key === pred; })[0], Q = L.items.filter(function (p) { return p.key === succ; })[0];
      if (!P || !Q || pred === succ) { stopDemo(); toast("The slide needs two items to link.", "info"); return; }
      later(100, function () { view.demo.keys = [pred]; view.demo.tag = null; rings(); say("1 · Press on the predecessor and start dragging."); });
      var steps = 18, x0 = P.milestone ? P.x0 + (P.ms || L.ms) / 2 : P.x1, x1 = Q.milestone ? Q.x0 - (Q.ms || L.ms) / 2 : Q.x0;
      for (var i = 0; i <= steps; i++) (function (i) {
        later(900 + i * 60, function () {
          var t = i / steps;
          view.demo.drag = { from: pred, x: x0 + (x1 - x0) * t, y: P.y + (Q.y - P.y) * t, over: t > 0.9, kind: view.pick.kind };
          rings(); say("2 · A dashed lead follows the pointer — drop it on the successor.");
        });
      })(i);
      later(2300, function () {
        preview({ pred: pred, succ: succ, kind: view.pick.kind, example: example }).then(function (L2) {
          if (!view.demo) return;
          view.demo.drag = null; view.demo.keys = [];
          if (L2) demoPaint(L2);
          say("3 · Released on the successor: the link is added with the type in the selector — undo it with ⌘Z.");
        });
      });
      later(5300, stopDemo);
    },
    datadate: function (L, example) {
      var total = LSSlide.days(L.t0, L.t1), dates = [];
      for (var i = 1; i <= 5; i++) dates.push(addDays(L.t0, Math.round(total * i / 6)));
      later(100, function () { say("The data date is the computer's date until you set one. Watch the red line, its caption and the legend move together."); });
      dates.forEach(function (iso, i) {
        later(900 + i * 700, function () {
          preview({ today: iso, example: example }).then(function (L2) {
            if (!view.demo) return;
            if (L2) demoPaint(L2);
            say("Data date " + longDate(iso) + " — one setting for both pages and every PowerPoint.");
          });
        });
      });
      later(900 + dates.length * 700 + 700, stopDemo);
    },
    window: function (L, example) {
      var total = LSSlide.days(L.t0, L.t1);
      var a0 = addDays(L.t0, Math.round(total * 0.15)), a1 = addDays(L.t0, Math.round(total * 0.6));
      var b0 = addDays(L.t0, Math.round(total * 0.3)), b1 = addDays(b0, 90);
      later(100, function () { say("Two dates scope the slide. Items wholly outside the window are named below the slide, never dropped silently."); });
      later(1200, function () {
        preview({ window: [a0, a1], example: example }).then(function (L2) {
          if (!view.demo) return;
          if (L2) demoPaint(L2);
          say("Window " + monthYear(a0) + " – " + monthYear(a1) + ": the slide re-scales to fill the page; every item left off is named below it.");
        });
      });
      later(3600, function () {
        preview({ window: [b0, b1], example: example }).then(function (L2) {
          if (!view.demo) return;
          if (L2) demoPaint(L2);
          say("Window " + longDate(b0) + " – " + longDate(b1) + ": three months fill the slide — every label grows to use the room.");
        });
      });
      later(6000, function () { if (!view.demo) return; demoPaint(S.layout || L); say("Show all dates restores the whole list."); });
      later(7200, stopDemo);
    },
    compare: function (L) {
      later(100, function () { say("Compare takes a PRIOR and a CURRENT list. Solid is current; a ghost is where a moved item was; the arrow is the finish's move in calendar days."); });
      var steps = [["slipped", "Red arrows point right: these finishes slipped, +N calendar days."], ["pulled in", "A green arrow pointing left is a pull-in."], ["new", "NEW is tagged by name — the sheet has no id to follow."], ["removed", "A ghost with no solid shape is REMOVED."]];
      var t = 1800;
      steps.forEach(function (s) {
        var keys = L.items.filter(function (p) { return p.status === s[0]; }).map(function (p) { return p.key || ""; }).filter(Boolean);
        var removed = s[0] === "removed" ? L.items.filter(function (p) { return p.status === "removed"; }) : [];
        if (!keys.length && !removed.length) return;
        later(t, function () {
          if (!view.demo) return;
          view.demo.keys = keys; view.demo.tag = null; rings();
          if (removed.length && view.slide) removed.forEach(function (p) { ringRemoved(p); });
          say(s[1]);
        });
        t += 1500;
      });
      later(t + 400, stopDemo);
    },
  };
  function ringRemoved(p) {
    // a REMOVED row has no key (it cannot be linked) — ring its ghost directly
    var L = view.slide.L, h = (p.ghost_milestone ? (p.ghost_ms || L.ms) : L.bar_h) / 2;
    var x0 = p.ghost_milestone ? p.ghost_x0 - h : p.ghost_x0, x1 = p.ghost_milestone ? p.ghost_x0 + h : p.ghost_x1;
    var r = D.createElementNS("http://www.w3.org/2000/svg", "rect");
    r.setAttribute("x", x0 - 1.8); r.setAttribute("y", p.y - Math.max(L.bar_h, L.ms) / 2 - 1.8);
    r.setAttribute("width", x1 - x0 + 3.6); r.setAttribute("height", Math.max(L.bar_h, L.ms) + 3.6);
    r.setAttribute("rx", 1.5); r.setAttribute("class", "lss-ring is-demo");
    view.slide.rings.appendChild(r);
  }

  // ── boot ───────────────────────────────────────────────────────────────────────────────────
  try { history.replaceState({ page: S.page }, "", location.pathname + location.hash); } catch (e) { /* file: */ }
  frame(S);
  restoreRail();
  paintSlide(false);
  window.LSStudio = { state: function () { return S; }, view: view, act: act, runDemo: runDemo, startTour: startTour };
})();
