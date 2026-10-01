// lodestar_launch.js — LODESTAR 2.0's launch page (ADR-0543, the "Console" design handoff).
//
// Loaded in <head>, synchronously, so the operator's opt-out ("go straight to the studio next
// time") redirects before anything paints — the same storage key v1 used (sf-boot-skip), so the
// choice survives the upgrade; ?replay=1 (the header's mark) shows the page anyway. Then, once the
// page is parsed: the hero cycles every 6.5 s while idle (a dot picks one), TAKE A STAR FIX walks
// the six stages 650 ms apart and opens the welcome panel, Escape skips to the studio.
//
// Strict CSP (script-src 'self'): no inline script; the copy arrives in #lsBoot (JSON, not code).
(function () {
  "use strict";
  var SKIP_KEY = "sf-boot-skip";
  function stored(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function persist(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* in-page only */ } }
  function boot() {
    var el = document.getElementById("lsBoot");
    try { return el ? JSON.parse(el.textContent || "{}") : {}; } catch (e) { return {}; }
  }
  var B = boot(), HOME = typeof B.home === "string" && B.home ? B.home : "/onepager";
  if (stored(SKIP_KEY) === "1" && !/[?&]replay=1/.test(location.search)) {
    location.replace(HOME);
    return;
  }

  function wire() {
    var heroes = B.heroes || [], stages = B.stages || [], hero = 0, running = false, ready = false;
    // prefers-reduced-motion: the hero holds still (a dot still picks one) and the transit steps
    // without its pauses — motion never delays the operator, and nothing moves on its own
    var reduced = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    var k = document.getElementById("lsHeroK"), h = document.getElementById("lsHeroH"), s = document.getElementById("lsHeroS");
    var box = document.getElementById("lsHero");
    function show(i) {
      if (!heroes.length) return;
      hero = (i + heroes.length) % heroes.length;
      k.textContent = heroes[hero].k; h.textContent = heroes[hero].h; s.textContent = heroes[hero].s;
      box.classList.remove("is-swap"); void box.offsetWidth; box.classList.add("is-swap");
      Array.prototype.forEach.call(document.querySelectorAll("[data-ls-hero]"), function (d) {
        d.setAttribute("aria-pressed", +d.getAttribute("data-ls-hero") === hero ? "true" : "false");
      });
    }
    var cycle = reduced ? null : setInterval(function () { if (!running && !ready) show(hero + 1); }, B.heroMs || 6500);
    document.addEventListener("click", function (ev) {
      var d = ev.target.closest ? ev.target.closest("[data-ls-hero]") : null;
      if (d) show(+d.getAttribute("data-ls-hero"));
    });
    function stage(i) {
      var seq = document.getElementById("lsSeq");
      if (seq) seq.textContent = stages[i] || "";
      Array.prototype.forEach.call(document.querySelectorAll("[data-ls-stage]"), function (n) {
        var j = +n.getAttribute("data-ls-stage");
        n.classList.toggle("is-done", j < i);
        n.classList.toggle("is-active", j === i);
      });
    }
    var fix = document.getElementById("lsStarFix");
    if (fix) fix.addEventListener("click", function () {
      if (running || ready) return;
      running = true; fix.disabled = true;
      stages.forEach(function (_s, i) {
        setTimeout(function () {
          var st = Math.min(i + 1, stages.length - 1);
          stage(st);
          if (st === stages.length - 1) {
            running = false; ready = true; if (cycle) clearInterval(cycle);
            document.getElementById("lsHero").hidden = true;
            document.getElementById("lsActions").hidden = true;
            document.getElementById("lsWelcome").hidden = false;
            var enter = document.getElementById("lsEnter");
            if (enter) enter.focus();
          }
        }, reduced ? 0 : (B.stageMs || 650) * (i + 1));
      });
    });
    var never = document.getElementById("lsNever");
    if (never) {
      never.checked = stored(SKIP_KEY) === "1";
      never.addEventListener("change", function () { persist(SKIP_KEY, never.checked ? "1" : "0"); });
    }
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") location.assign(HOME);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();
})();
