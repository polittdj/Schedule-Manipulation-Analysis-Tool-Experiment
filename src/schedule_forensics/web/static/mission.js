/* Schedule Forensics — Mission Control wall.
 *
 * Drives the tiled chart wall: a master "Play all" steps every animated chart in lockstep
 * (one timer clicking each chart's Next), and a per-tile "Data" toggle reveals that chart's
 * hidden .sr-only data table so you can dive into the underlying numbers and back. The charts
 * themselves are the dedicated-page scripts, loaded alongside this one; nothing leaves the box.
 */
"use strict";

(function () {
  var grid = document.getElementById("missionGrid");
  if (!grid) return;

  // each animated tile's "Next" control — the master timer clicks them together so every
  // visual advances at the same rate (true lockstep, no per-chart timer drift)
  var NEXT_IDS = ["nextScurve", "nextSnap", "nextDrift", "qualNext"];
  var timer = null;

  function stepAll() {
    NEXT_IDS.forEach(function (id) {
      var b = document.getElementById(id);
      if (b) b.click();
    });
  }
  function setLabel(text) {
    var pa = document.getElementById("missionPlay");
    if (pa) pa.textContent = text;
  }
  function start() {
    if (timer) return;
    stepAll();
    timer = setInterval(stepAll, 1600);
    setLabel("⏸ Pause all");
  }
  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
    setLabel("▶ Play all");
  }
  function toggle() {
    if (timer) { stop(); return; }
    // honor prefers-reduced-motion — advance one frame instead of running a timer
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      stepAll();
      return;
    }
    start();
  }

  var play = document.getElementById("missionPlay");
  if (play) play.addEventListener("click", toggle);
  var step = document.getElementById("missionStep");
  if (step) step.addEventListener("click", stepAll);

  // per-tile data toggle: reveal/hide the chart's visually-hidden .sr-only data table
  grid.addEventListener("click", function (e) {
    var btn = e.target && e.target.closest ? e.target.closest(".tile-data") : null;
    if (!btn) return;
    var tile = btn.closest(".tile");
    if (!tile) return;
    var on = tile.classList.toggle("show-data");
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    btn.textContent = on ? "▦ Hide data" : "▦ Data";
  });
})();
