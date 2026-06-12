/* Schedule Forensics — SSI-style path analysis workspace.
 *
 * Data grid on the left, a SCALABLE timeline on the right (zoom = pixels per day,
 * horizontal scroll) with month ticks and the gold data-date line. The driving /
 * secondary / tertiary tiers come from /api/driving with the user's own day-bands and
 * target UID; columns are add/removable, rows filterable (tier, substring, hide 100%
 * complete). The Ask-the-AI panel posts to /api/ask — answers are grounded in the
 * engine's cited facts (see ai/qa.py). Dependency-free; nothing leaves the machine.
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
    var tier = $("pathTier").value;
    var q = $("pathFilter").value.trim().toLowerCase();
    return data.rows.filter(function (r) {
      if (hideDone && r.percent_complete >= 100) return false;
      if (tier && r.tier !== tier) return false;
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
      var tr = el("tr", { class: r.percent_complete >= 100 ? "done" : "" });
      on.forEach(function (f) {
        var v = r[f.key];
        if (typeof v === "boolean") v = v ? "yes" : "—";
        tr.appendChild(el("td", { text: v === null || v === undefined ? "—" : String(v) }));
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
            class: "gantt-bar tier-" + r.tier + (r.percent_complete >= 100 ? " done" : ""),
            style: "left:" + left + "px;width:" + w + "px",
            title: r.name + " — " + r.tier + ", slack " + r.driving_slack_days + "d, " +
              r.start + " → " + r.finish + ", " + r.percent_complete + "%",
          });
          if (r.percent_complete > 0 && r.percent_complete < 100) {
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

  // --- ask the AI -------------------------------------------------------------------
  function ask() {
    var out = $("askOut");
    var q = $("askInput").value.trim();
    if (!q) return;
    out.textContent = "Thinking locally…";
    var body = new URLSearchParams();
    body.set("question", q);
    fetch("/api/ask/" + encodeURIComponent($("pathSchedule").value), { method: "POST", body: body })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        out.textContent = "";
        if (!res.ok) { out.textContent = res.j.error || "Could not answer."; return; }
        if (res.j.answer) {
          out.appendChild(el("p", { class: "ask-answer", text: res.j.answer }));
          out.appendChild(el("p", { class: "muted", text: "Model-generated from the cited facts below — verify against them." }));
        } else {
          out.appendChild(el("p", { class: "muted", text: "No local model is active (or its answer failed the no-invented-numbers gate) — these are the engine's cited facts that match your question:" }));
        }
        var ul = el("ul");
        (res.j.facts || []).forEach(function (f) {
          var cite = (f.citations || []).map(function (c) { return c.task + " (UID " + c.uid + ")"; }).join("; ");
          ul.appendChild(el("li", { text: f.text + (cite ? "  [" + cite + "]" : "") }));
        });
        out.appendChild(ul);
      })
      .catch(function () { out.textContent = "Could not answer."; });
  }

  renderToggles();
  $("pathRun").addEventListener("click", trace);
  ["pathHideDone", "pathTier"].forEach(function (id) { $(id).addEventListener("change", render); });
  ["pathFilter", "pathZoom"].forEach(function (id) { $(id).addEventListener("input", render); });
  $("askBtn").addEventListener("click", ask);
  $("askInput").addEventListener("keydown", function (e) { if (e.key === "Enter") ask(); });
  if ($("pathTarget").value) trace(); // a session-wide target traces immediately
})();
