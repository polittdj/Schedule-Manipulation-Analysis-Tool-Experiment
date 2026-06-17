/* Schedule Forensics — SSI-style path analysis workspace.
 *
 * Data grid on the left, a SCALABLE timeline on the right (zoom = pixels per day,
 * horizontal scroll) with month ticks and the gold data-date line. The driving /
 * secondary / tertiary tiers come from /api/driving with the user's own day-bands and
 * target UID; columns are add/removable, rows filterable (tier, substring, hide 100%
 * complete). The Ask-the-AI panel is the page-shell one (ask.js). Dependency-free;
 * nothing leaves the machine.
 */
"use strict";

(function () {
  var view = document.getElementById("pathView");
  if (!view) return;

  var DAY_MS = 86400000;
  var FIELDS = [
    { key: "unique_id", label: "UID", on: true },
    { key: "name", label: "Name", on: true },
    { key: "wbs", label: "WBS", on: false },
    { key: "tier", label: "Tier", on: true },
    { key: "driving_slack_days", label: "Slack (d)", on: true },
    { key: "start", label: "Start", on: true },
    { key: "finish", label: "Finish", on: true },
    { key: "baseline_finish", label: "Baseline finish", on: false },
    { key: "duration_days", label: "Dur (d)", on: false },
    { key: "total_float_days", label: "TF (d)", on: false },
    { key: "percent_complete", label: "%", on: true },
    { key: "date_driven", label: "Date-driven", on: false },
    { key: "resource_names", label: "Resources", on: false },
  ];
  var data = null; // last /api/driving payload
  var pathTierSel = null; // checklist selection of tiers to show (null = all)

  function el(tag, attrs, kids) {
    var node = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "text") node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { node.appendChild(c); });
    return node;
  }
  function $(id) { return document.getElementById(id); }

  // --- field add/remove toggles ----------------------------------------------------
  function renderToggles() {
    var box = $("pathFields");
    box.textContent = "Columns: ";
    FIELDS.forEach(function (f) {
      var lab = el("label", { class: "field-toggle" });
      var cb = el("input", { type: "checkbox" });
      cb.checked = f.on;
      cb.addEventListener("change", function () { f.on = cb.checked; render(); });
      lab.appendChild(cb);
      lab.appendChild(document.createTextNode(" " + f.label + "  "));
      box.appendChild(lab);
    });
  }

  // --- filtering --------------------------------------------------------------------
  function visibleRows() {
    if (!data) return [];
    var hideDone = $("pathHideDone").checked;
    var q = $("pathFilter").value.trim().toLowerCase();
    return data.rows.filter(function (r) {
      if (hideDone && r.complete) return false;
      if (pathTierSel && !pathTierSel.has(r.tier)) return false; // empty Set hides every row
      if (q && (r.name + " " + r.unique_id).toLowerCase().indexOf(q) < 0) return false;
      return true;
    });
  }

  // --- the two-pane grid + scalable timeline ----------------------------------------
  function render() {
    view.textContent = "";
    if (!data) return;
    var rows = visibleRows();
    var status = $("pathStatus");
    status.textContent = data.note
      ? data.note
      : rows.length + " of " + data.rows.length + " path activities to UID " +
        data.target_uid + " (" + (data.target_name || "?") + ")" +
        (data.data_date ? " — data date " + data.data_date : "") +
        (data.coverage ? " — " + data.coverage : "");
    if (!rows.length) return;

    var px = Number($("pathZoom").value); // pixels per calendar day
    var t0 = null, t1 = null;
    rows.forEach(function (r) {
      if (r.start) t0 = Math.min(t0 === null ? Infinity : t0, Date.parse(r.start));
      if (r.finish) t1 = Math.max(t1 === null ? -Infinity : t1, Date.parse(r.finish));
    });
    if (data.data_date) t1 = Math.max(t1, Date.parse(data.data_date));
    if (t0 === null || t1 === null) return;
    t0 -= 2 * DAY_MS; t1 += 2 * DAY_MS;
    var width = Math.max(120, Math.round((t1 - t0) / DAY_MS) * px);
    var x = function (ms) { return Math.round(((ms - t0) / DAY_MS) * px); };

    var on = FIELDS.filter(function (f) { return f.on; });
    var table = el("table", { class: "gantt-grid path-grid" });
    var head = el("tr");
    on.forEach(function (f) { head.appendChild(el("th", { text: f.label })); });
    var thTime = el("th", { class: "g-head path-timeline-head" });
    var scale = el("div", { class: "path-scale", style: "width:" + width + "px" });
    var d = new Date(t0); d.setDate(1); // month ticks
    while (d.getTime() <= t1) {
      var tx = x(d.getTime());
      if (tx >= 0) {
        scale.appendChild(el("div", { class: "pv-tick", style: "left:" + tx + "px" }));
        scale.appendChild(el("div", {
          class: "pv-tick-label", style: "left:" + (tx + 3) + "px",
          text: (d.getMonth() + 1) + "/" + String(d.getFullYear()).slice(2),
        }));
      }
      d.setMonth(d.getMonth() + 1);
    }
    if (data.data_date) {
      scale.appendChild(el("div", {
        class: "pv-now", style: "left:" + x(Date.parse(data.data_date)) + "px",
        title: "data date " + data.data_date,
      }));
    }
    thTime.appendChild(scale);
    head.appendChild(thTime);
    table.appendChild(head);

    rows.forEach(function (r) {
      var tr = el("tr", { class: r.complete ? "done" : "" });
      on.forEach(function (f) {
        var v = r[f.key];
        if (typeof v === "boolean") v = v ? "yes" : "—";
        var text = v === null || v === undefined ? "—" : String(v);
        // the Name column wraps to its FULL text (no truncation); other columns stay nowrap
        tr.appendChild(el("td", f.key === "name" ? { class: "pv-name", text: text } : { text: text }));
      });
      var cell = el("td", { class: "path-timeline" });
      var track = el("div", { class: "path-track", style: "width:" + width + "px" });
      if (data.data_date) {
        track.appendChild(el("div", { class: "pv-now", style: "left:" + x(Date.parse(data.data_date)) + "px" }));
      }
      if (r.start && r.finish) {
        if (r.is_milestone) {
          track.appendChild(el("div", {
            class: "g-ms tier-" + r.tier, style: "left:" + x(Date.parse(r.finish)) + "px",
            title: r.name + " (milestone) — slack " + r.driving_slack_days + "d",
          }));
        } else {
          var left = x(Date.parse(r.start));
          var w = Math.max(2, x(Date.parse(r.finish)) - left);
          var bar = el("div", {
            class: "gantt-bar tier-" + r.tier + (r.complete ? " done" : ""),
            style: "left:" + left + "px;width:" + w + "px",
            title: r.name + " — " + r.tier + ", slack " + r.driving_slack_days + "d, " +
              r.start + " → " + r.finish + ", " + r.percent_complete + "%",
          });
          if (!r.complete && r.percent_complete > 0 && r.percent_complete < 100) {
            bar.appendChild(el("div", { class: "g-done", style: "width:" + r.percent_complete + "%" }));
          }
          track.appendChild(bar);
        }
      }
      cell.appendChild(track);
      tr.appendChild(cell);
      table.appendChild(tr);
    });
    view.appendChild(table);
  }

  // --- data loading -----------------------------------------------------------------
  function trace() {
    var sched = $("pathSchedule").value;
    var target = $("pathTarget").value;
    if (!target) { $("pathStatus").textContent = "Enter a target UniqueID, then Trace."; return; }
    var url = "/api/driving/" + encodeURIComponent(sched) +
      "?target=" + encodeURIComponent(target) +
      "&secondary=" + encodeURIComponent($("pathSec").value || "10") +
      "&tertiary=" + encodeURIComponent($("pathTer").value || "20");
    $("pathStatus").textContent = "Tracing…";
    fetch(url)
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { $("pathStatus").textContent = res.j.error || "Trace failed."; data = null; view.textContent = ""; return; }
        data = res.j;
        var q = "/" + encodeURIComponent(sched) + "?target=" + encodeURIComponent(target) +
          "&secondary=" + encodeURIComponent($("pathSec").value || "10") +
          "&tertiary=" + encodeURIComponent($("pathTer").value || "20");
        $("pathXlsx").href = "/export/xlsx/path" + q;
        $("pathDocx").href = "/export/docx/path" + q;
        $("pathExport").style.display = "";
        render();
      })
      .catch(function () { $("pathStatus").textContent = "Trace failed."; });
  }

  renderToggles();
  // the MS-Project-style tier checklist (select-all / clear which of the four tiers show)
  var pathTierMount = $("pathTier");
  if (pathTierMount && window.SFChecklist) {
    pathTierMount.appendChild(window.SFChecklist.filter({
      values: ["DRIVING", "SECONDARY", "TERTIARY", "BEYOND"],
      selected: null,
      label: "Tier",
      title: "Show driving-path tiers",
      onChange: function (s) { pathTierSel = s; render(); },
    }));
  }
  $("pathRun").addEventListener("click", trace);
  $("pathHideDone").addEventListener("change", render);
  ["pathFilter", "pathZoom"].forEach(function (id) { $(id).addEventListener("input", render); });
  if ($("pathTarget").value) trace(); // a session-wide target traces immediately
})();
