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
  // Full screen REFORMATS instead of magnifying (operator 2026-07-08): an expanded chart may
  // render at most this multiple of its design (viewBox) size, so fonts/marks stay near their
  // intended 10-12px instead of blowing up with the container. Reflow-aware charts (the SRA
  // S-curve/tornados, progress S-curve) additionally redraw at 1:1 to the wider container via
  // the "sf-reflow" event, genuinely using the extra space for plot area rather than for scale.
  var FS_FONT_CAP = 1.25;

  // ── shared hover call-out ───────────────────────────────────────────────────────────────────
  // One styled tooltip, reused by every framed chart. Hovering any SVG shape that carries a direct
  // <title> child (the existing native-tooltip text used across the charts) — or an explicit
  // data-callout attribute for richer text — shows an instant, styled call-out at the cursor. This
  // upgrades EVERY chart's hover to a real call-out without touching each chart, and gives new
  // charts a hook (data-callout=…) for multi-line detail.
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
        var kids = node.childNodes;
        for (var j = 0; j < kids.length; j++) {
          var k = kids[j];
          if (k.nodeName && k.nodeName.toLowerCase() === "title" && k.textContent) {
            return k.textContent;
          }
        }
      }
      node = node.parentNode;
    }
    return null;
  }
  function wireCallouts(host) {
    host.addEventListener("mousemove", function (e) {
      var txt = calloutText(e.target, host);
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
    host.addEventListener("mouseleave", function () { if (tip) tip.style.display = "none"; });
  }

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

    function inFsMode() {
      return fsElement() === wrap || wrap.classList.contains("cf-max");
    }
    function applyZoom() {
      var svgs = host.querySelectorAll("svg");
      var fs = inFsMode();
      var avail = scroll.clientWidth || host.clientWidth || 0;
      for (var i = 0; i < svgs.length; i++) {
        var svg = svgs[i];
        var vb = svg.viewBox && svg.viewBox.baseVal ? svg.viewBox.baseVal.width : 0;
        if (fs && vb > 0 && avail > 0) {
          // expanded: pixel-capped width (no font blow-up), centered by CSS; the user's explicit
          // -/+ zoom still multiplies on top of the cap
          svg.style.width = Math.round(Math.min(avail, vb * FS_FONT_CAP) * scale) + "px";
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

    wireCallouts(host);  // styled hover call-outs for every chart in this frame
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
