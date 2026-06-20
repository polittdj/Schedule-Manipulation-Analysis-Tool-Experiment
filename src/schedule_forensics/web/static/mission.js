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
  var NEXT_IDS = ["nextScurve", "nextSnap", "nextDrift", "qualNext", "nextEvo"];
  // the overview line charts have no frames to step; instead their solid lines re-draw left-to-right
  // on each beat so they "progress" in lockstep with the steppers (curves + the trend lines)
  var DRAW_IDS = ["finishesChart", "dataDateChart", "slippageChart", "trendCharts"];
  var timer = null;

  function replayDraw() {
    DRAW_IDS.forEach(function (id) {
      var node = document.getElementById(id);
      var host = node && node.closest ? node.closest(".chart-host") : null;
      if (!host) return;
      host.classList.remove("sf-draw");
      void host.offsetWidth;  // force reflow so the CSS draw animation restarts from the start
      host.classList.add("sf-draw");
    });
  }

  function stepAll() {
    NEXT_IDS.forEach(function (id) {
      var b = document.getElementById(id);
      if (b) b.click();
    });
    replayDraw();
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

  // per-tile controls (event-delegated): the Data toggle reveals the chart's hidden .sr-only data
  // table; the Enlarge toggle grows the tile to the full wall width (and back) so the user can
  // size any visual as they please without leaving the wall.
  grid.addEventListener("click", function (e) {
    var t = e.target;
    var dataBtn = t && t.closest ? t.closest(".tile-data") : null;
    if (dataBtn) {
      var dtile = dataBtn.closest(".tile");
      if (!dtile) return;
      var on = dtile.classList.toggle("show-data");
      dataBtn.setAttribute("aria-pressed", on ? "true" : "false");
      dataBtn.textContent = on ? "▦ Hide data" : "▦ Data";
      return;
    }
    var bigBtn = t && t.closest ? t.closest(".tile-expand") : null;
    if (bigBtn) {
      var btile = bigBtn.closest(".tile");
      if (!btile) return;
      var big = btile.classList.toggle("tile-expanded");
      bigBtn.setAttribute("aria-pressed", big ? "true" : "false");
      bigBtn.textContent = big ? "⛶ Shrink" : "⛶ Enlarge";
      if (big) btile.scrollIntoView({ block: "nearest" });
    }
  });
})();
