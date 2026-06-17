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

    function applyZoom() {
      var svgs = host.querySelectorAll("svg");
      for (var i = 0; i < svgs.length; i++) svgs[i].style.width = Math.round(100 * scale) + "%";
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

    var fsBtn = button("⤢", "Full screen", function () {
      if (fsElement() === wrap) {
        exitFs();
      } else if (requestFs(wrap) === null) {
        // no Fullscreen API → fixed-position maximize fallback
        wrap.classList.toggle("cf-max");
        fsBtn.textContent = wrap.classList.contains("cf-max") ? "✕" : "⤢";
      }
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
    });

    // re-apply the current zoom to SVGs drawn later (async fetch, or stepper re-renders)
    var obs = new MutationObserver(function () { applyZoom(); });
    obs.observe(host, { childList: true, subtree: true });

    applyZoom();
  }

  function scan() {
    var hosts = document.querySelectorAll(".chart-host");
    for (var i = 0; i < hosts.length; i++) frame(hosts[i]);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scan);
  } else {
    scan();
  }
})();
