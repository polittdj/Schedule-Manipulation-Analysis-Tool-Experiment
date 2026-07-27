/* Schedule Forensics — generic chart frame: full-screen + zoom on every chart.
 *
 * Dependency-free (no CDN — air-gap posture). Any element marked `class="chart-host"`
 * gets a small toolbar (⤢ full screen · − / ＋ zoom · reset). Zoom rescales the SVG(s)
 * inside the host and the host scrolls; full screen uses the Fullscreen API (with a fixed
 * "maximize" fallback) and Esc / the button returns to the original view.
 *
 * The toolbar lives OUTSIDE the host's content, so charts that re-render their innards
 * (the Bow-Wave / drift / evolution steppers clear and rebuild their SVG each frame) keep
 * their frame and zoom level — a MutationObserver re-applies the current zoom to any SVG
 * the chart draws later.
 */
"use strict";

(function () {
  var ZOOM_STEP = 1.25;
  var ZOOM_MIN = 0.5;
  var ZOOM_MAX = 6;
  // Full screen CONTAIN-FITS the chart to the viewport (operator 2026-07-10: an expanded chart
  // "looked tiny in a huge empty page — utilize the page space"): the SVG scales to the larger
  // of its design size and the biggest size that still fits BOTH the available width and height,
  // so it fills the page without overflowing it. The user's explicit −/＋ zoom multiplies on
  // top. Reflow-aware charts (SRA S-curve/tornados, progress S-curve) additionally redraw at
  // 1:1 to the wider container via the "sf-reflow" event, using the space for plot area.

  // ── shared hover call-out ───────────────────────────────────────────────────────────────────
  // One styled tooltip for the WHOLE app. Hovering any element that carries a direct SVG <title>
  // child, an HTML title= attribute, or an explicit data-callout attribute for richer text shows
  // an instant, styled call-out at the cursor — and the native browser tooltip is suppressed so
  // exactly ONE call-out is ever visible (ADR-0190). This upgrades every hover to a real call-out
  // without touching each chart, and gives new charts a hook (data-callout=…) for detail.
  var tip = null;
  function ensureTip() {
    if (tip) return tip;
    tip = document.createElement("div");
    tip.className = "cf-tip";
    tip.setAttribute("data-no-i18n", "");
    tip.setAttribute("role", "tooltip");
    tip.style.display = "none";
    document.body.appendChild(tip);
    return tip;
  }
  function calloutText(node, host) {
    while (node && node !== host) {
      if (node.getAttribute) {
        var dc = node.getAttribute("data-callout");
        if (dc) return dc;
        // an HTML title= attribute (the table-Gantt bars) gets the same instant call-out
        // as an SVG <title> child — the native tooltip is slow and unstyled (ADR-0187).
        // The text is MOVED to data-cf-title on first hover so the browser's own tooltip
        // can never pop up on top of the styled call-out (operator: "only one, not
        // multiple at the same time" — ADR-0190); re-renders that set title= afresh are
        // simply re-stripped on the next hover.
        var cached = node.getAttribute("data-cf-title");
        if (cached) return cached;
        var ta = node.getAttribute("title");
        if (ta) {
          node.setAttribute("data-cf-title", ta);
          node.removeAttribute("title");
          return ta;
        }
        var kids = node.childNodes;
        for (var j = 0; j < kids.length; j++) {
          var k = kids[j];
          if (k.nodeName && k.nodeName.toLowerCase() === "title" && k.textContent) {
            var tt = k.textContent;
            node.setAttribute("data-cf-title", tt);
            node.removeChild(k); // same de-duplication for SVG <title> native tooltips
            return tt;
          }
        }
      }
      node = node.parentNode;
    }
    return null;
  }
  function hideTip() {
    if (tip) tip.style.display = "none";
  }
  // ── ONE call-out for the whole app (ADR-0190) ──────────────────────────────────────────
  // A single document-level listener replaces the old per-framed-host wiring: ANY element
  // carrying a title= / SVG <title> / data-callout — framed chart or not, on every page —
  // gets the same styled cf-tip, and calloutText moves the text into data-cf-title so the
  // browser's native tooltip can never pop a second, overlapping box on top of it
  // (operator: "only the one in white, not both … applies to all callouts in the entire
  // tool. Only one. Not multiple at the same time").
  function wireCallouts() {
    document.addEventListener("mousemove", function (e) {
      var txt = calloutText(e.target, document);
      var t = ensureTip();
      if (!txt) { t.style.display = "none"; return; }
      t.textContent = txt;
      t.style.display = "block";
      var pad = 14, r = t.getBoundingClientRect();
      var x = e.clientX + pad, y = e.clientY + pad;
      if (x + r.width > window.innerWidth) x = e.clientX - pad - r.width;
      if (y + r.height > window.innerHeight) y = e.clientY - pad - r.height;
      t.style.left = Math.max(0, x) + "px";
      t.style.top = Math.max(0, y) + "px";
    });
    document.addEventListener("mouseleave", hideTip);
    document.addEventListener("scroll", hideTip, true); // don't let a stale tip float mid-scroll
  }
  wireCallouts();

  // ── "Play all" coordinator: manual chart control halts the master (ADR-0275) ────────────────
  // Animated charts carry a per-chart ‹ Prev / ▶ Play / Next › stepper AND a page-level master
  // "Play all" (mission.js on the wall, #sfPlayAll on Trends) that steps every chart in lockstep by
  // PROGRAMMATICALLY clicking their Next buttons on a timer. A per-chart Stop only cleared THAT
  // chart's own timer, so while the master ran it kept stepping the chart — the operator hit a
  // chart's Stop and it "continued to play" (most visible on an enlarged chart, where the master
  // control is out of view). Fix: masters register their stop() here, and any TRUSTED (real user)
  // click on a per-chart animation control stops every master first — touching a chart by hand
  // takes manual control and the auto-play-all halts, so Stop (and Prev/Next) behave as expected.
  // The master's OWN stepping uses element.click() (isTrusted === false), so it never stops itself.
  var playMasters = [];
  window.SFPlayAll = window.SFPlayAll || {
    register: function (stopFn) {
      if (typeof stopFn === "function" && playMasters.indexOf(stopFn) === -1) {
        playMasters.push(stopFn);
      }
    },
    stopAll: function () {
      for (var i = 0; i < playMasters.length; i++) {
        try { playMasters[i](); } catch (e) { /* one bad master must not block the rest */ }
      }
    },
  };
  // every per-chart animation control across the app (the sf-frame stepper shared by trend/margin/
  // curves, plus the dedicated play/step buttons of the bow-wave, S-curve, drift, path-evolution
  // and quality steppers). A new animated chart adds its control ids here to join the coordinator.
  var ANIM_CTL_SELECTOR =
    ".sf-frame-play,.sf-frame-next,.sf-frame-prev," +
    "#autoPlay,#scurvePlay,#driftPlay,#evoPlay,#qualPlay," +
    "#nextSnap,#prevSnap,#nextScurve,#prevScurve,#nextDrift,#prevDrift," +
    "#nextEvo,#prevEvo,#qualNext,#qualPrev";
  document.addEventListener(
    "click",
    function (e) {
      if (!e.isTrusted) return; // the master's own programmatic .click() must NOT stop the master
      var t = e.target;
      if (t && t.closest && t.closest(ANIM_CTL_SELECTOR)) window.SFPlayAll.stopAll();
    },
    true // capture phase: halt the master BEFORE the control's own handler advances/toggles
  );

  function requestFs(el) {
    var fn = el.requestFullscreen || el.webkitRequestFullscreen || el.msRequestFullscreen;
    return fn ? fn.call(el) : null;
  }
  function exitFs() {
    var fn = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen;
    if (fn) fn.call(document);
  }
  function fsElement() {
    return document.fullscreenElement || document.webkitFullscreenElement || null;
  }

  function frame(host) {
    if (host.__cfFramed) return;
    host.__cfFramed = true;
    var scale = 1;

    var wrap = document.createElement("div");
    wrap.className = "cf-frame";
    var scroll = document.createElement("div");
    scroll.className = "cf-scroll";

    // splice the wrapper in where the host was, then move the host inside the scroller
    host.parentNode.insertBefore(wrap, host);
    scroll.appendChild(host);

    var bar = document.createElement("div");
    bar.className = "cf-bar";
    wrap.appendChild(bar);
    wrap.appendChild(scroll);

    // ── title in EVERY view (operator 2026-07-10) ─────────────────────────────────────
    // Most chart titles are the panel h2/h3 that sits OUTSIDE the framed host, so the
    // expanded view used to show an untitled chart. Mirror the nearest preceding heading
    // into a .cf-title that CSS reveals in the expanded modes (the original heading still
    // shows in the normal view — no duplicate). The heading's explainer callout
    // (data-sf-hint, decorated later by vizhints.js) is mirrored on entry to fullscreen so
    // the what/how-to-use/example call-out is available in the expanded view too.
    function findTitleSource() {
      var inner = host.querySelector("h2, h3");
      if (inner) return inner; // the title lives inside the host — visible in all views
      var node = wrap;
      while (node && node !== document.body) {
        var sib = node.previousElementSibling;
        while (sib) {
          if (/^H[23]$/.test(sib.tagName)) return sib;
          var wrapped = sib.querySelector ? sib.querySelector("h2, h3") : null;
          if (wrapped) return wrapped;
          sib = sib.previousElementSibling;
        }
        node = node.parentNode;
        if (node && node.classList && node.classList.contains("panel")) {
          var h = node.querySelector("h2, h3");
          return h || null;
        }
      }
      return null;
    }
    var titleSrc = host.querySelector("h2, h3") ? null : findTitleSource();
    var cfTitle = null;
    if (titleSrc) {
      cfTitle = document.createElement("div");
      cfTitle.className = "cf-title";
      cfTitle.textContent = titleSrc.textContent;
      wrap.insertBefore(cfTitle, scroll);
    }
    function syncTitle() {
      if (!cfTitle || !titleSrc) return;
      cfTitle.textContent = titleSrc.textContent; // dynamic headings (steppers) stay current
      var hint = titleSrc.getAttribute("data-sf-hint");
      if (hint) {
        cfTitle.setAttribute("data-sf-hint", hint);
        cfTitle.classList.add("viz-hint");
        cfTitle.setAttribute("tabindex", "0");
      }
    }

    function inFsMode() {
      return fsElement() === wrap || wrap.classList.contains("cf-max");
    }
    function applyZoom() {
      var svgs = host.querySelectorAll("svg");
      var fs = inFsMode();
      var availW = scroll.clientWidth || host.clientWidth || 0;
      var availH = scroll.clientHeight || 0;
      for (var i = 0; i < svgs.length; i++) {
        var svg = svgs[i];
        var vbObj = svg.viewBox && svg.viewBox.baseVal ? svg.viewBox.baseVal : null;
        var vbW = vbObj ? vbObj.width : 0;
        var vbH = vbObj ? vbObj.height : 0;
        if (fs && vbW > 0 && availW > 0) {
          // expanded: contain-fit — as large as fits BOTH dimensions (fills the page,
          // never overflows it); the user's -/+ zoom multiplies on top
          var fitW = availW;
          if (vbH > 0 && availH > 0) fitW = Math.min(availW, (availH * vbW) / vbH);
          svg.style.width = Math.round(fitW * scale) + "px";
        } else {
          svg.style.width = Math.round(100 * scale) + "%";
        }
      }
      // Non-SVG visuals (e.g. the HTML 5x5 assessment matrix) opt in with class "cf-zoom-box":
      // CSS-transform-scale them and reserve the grown footprint via margin so the scroller can
      // pan a magnified copy. offsetWidth/Height stay the untransformed layout size at any zoom.
      var boxes = host.querySelectorAll(".cf-zoom-box");
      for (var b = 0; b < boxes.length; b++) {
        var box = boxes[b];
        var w = box.offsetWidth, h = box.offsetHeight;
        box.style.transformOrigin = "top left";
        box.style.transform = scale === 1 ? "" : "scale(" + scale + ")";
        box.style.marginRight = w * (scale - 1) + "px";
        box.style.marginBottom = h * (scale - 1) + "px";
      }
      zlabel.textContent = Math.round(scale * 100) + "%";
    }
    function setZoom(next) {
      scale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, next));
      applyZoom();
    }
    function button(txt, title, fn) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "cf-btn";
      b.textContent = txt;
      b.title = title;
      b.setAttribute("aria-label", title);
      b.addEventListener("click", fn);
      bar.appendChild(b);
      return b;
    }

    function reflowSoon() {
      // let the layout settle at the new size, then re-apply the width policy and tell the
      // reflow-aware charts to redraw to the resized container
      syncTitle();
      window.requestAnimationFrame(function () {
        applyZoom();
        try { window.dispatchEvent(new CustomEvent("sf-reflow")); } catch (e) { /* very old engine */ }
      });
    }

    var fsBtn = button("⤢", "Full screen", function () {
      if (fsElement() === wrap) { exitFs(); return; }
      var maximize = function () {
        // no/denied Fullscreen API → fixed-position maximize fallback
        wrap.classList.toggle("cf-max");
        fsBtn.textContent = wrap.classList.contains("cf-max") ? "✕" : "⤢";
        reflowSoon();
      };
      var req = requestFs(wrap);
      if (req === null) maximize();
      else if (req && typeof req.catch === "function") req.catch(maximize);
    });
    button("−", "Zoom out", function () { setZoom(scale / ZOOM_STEP); });
    var zlabel = document.createElement("span");
    zlabel.className = "cf-zoom";
    zlabel.textContent = "100%";
    bar.appendChild(zlabel);
    button("＋", "Zoom in", function () { setZoom(scale * ZOOM_STEP); });
    button("Reset", "Reset zoom", function () { setZoom(1); });

    document.addEventListener("fullscreenchange", function () {
      fsBtn.textContent = fsElement() === wrap ? "✕" : "⤢";
      reflowSoon();
    });

    // re-apply the current zoom to SVGs drawn later (async fetch, or stepper re-renders)
    var obs = new MutationObserver(function () { applyZoom(); });
    obs.observe(host, { childList: true, subtree: true });

    // hover call-outs are wired ONCE at document level (ADR-0190) — nothing per-frame
    applyZoom();
  }

  function scan() {
    var hosts = document.querySelectorAll(".chart-host");
    for (var i = 0; i < hosts.length; i++) frame(hosts[i]);
  }

  // Public hook so charts rendered AFTER page load (e.g. the SSI run fetches its S-curve / histogram /
  // assessment matrices on demand) can frame their freshly-built ".chart-host" wrappers: call
  // SFChartFrame.scan() once the new nodes are in the DOM. frame() is idempotent (guards __cfFramed).
  window.SFChartFrame = { frame: frame, scan: scan };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scan);
  } else {
    scan();
  }
})();
