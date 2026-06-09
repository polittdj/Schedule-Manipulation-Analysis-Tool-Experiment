/* Schedule Forensics — interactive Power-BI-style visuals (M14).
 *
 * Dependency-free, fully local: no CDN, no external fetch, no third-party library (the
 * strongest air-gap posture for a CUI tool). Renders charts, an interactive activity grid
 * with add/remove fields and click-to-drill-into-metadata, and a Gantt that highlights the
 * driving / secondary / tertiary path tiers to a chosen target UID. All data comes from the
 * local /api endpoints; every drilled value carries its citation (file + UID + task name).
 */
"use strict";

(function () {
  const viz = document.getElementById("viz");
  if (!viz) return;
  const name = viz.dataset.name;
  const enc = encodeURIComponent(name);

  const el = (tag, attrs, children) => {
    const node = document.createElement(tag);
    for (const k in attrs || {}) {
      if (k === "class") node.className = attrs[k];
      else if (k === "text") node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    }
    (children || []).forEach((c) => node.appendChild(c));
    return node;
  };

  function barChart(container, title, rows) {
    // rows: [{label, value, max, cls}]
    const box = el("div", { class: "chart" });
    box.appendChild(el("h3", { text: title }));
    const max = Math.max(1, ...rows.map((r) => r.max != null ? r.max : r.value));
    rows.forEach((r) => {
      const track = el("div", { class: "bar-track" });
      const pct = Math.max(0, Math.min(100, (r.value / max) * 100));
      track.appendChild(el("div", { class: "bar-fill " + (r.cls || "accent"), style: "width:" + pct + "%" }));
      const row = el("div", { class: "bar-row" }, [
        el("span", { text: r.label }),
        track,
        el("span", { text: String(r.display != null ? r.display : r.value) }),
      ]);
      box.appendChild(row);
    });
    container.appendChild(box);
  }

  function renderCharts(data) {
    const charts = document.getElementById("charts");
    charts.innerHTML = "";
    // DCMA pass/fail overview
    const dcmaRows = Object.keys(data.dcma).map((k) => {
      const c = data.dcma[k];
      return { label: k, value: c.status === "FAIL" ? 1 : 0, max: 1,
               cls: c.status === "FAIL" ? "bad" : "ok", display: c.status };
    });
    barChart(charts, "DCMA-14 checks (red = fail)", dcmaRows);
    // baseline compliance counts
    const bc = data.baseline_compliance;
    barChart(charts, "Baseline compliance (activities)", [
      { label: "Completed on time", value: bc.completed_on_time || 0, cls: "ok" },
      { label: "Completed late", value: bc.completed_late || 0, cls: "warn" },
      { label: "Not completed", value: bc.not_completed || 0, cls: "bad" },
      { label: "Started on time", value: bc.started_on_time || 0, cls: "ok" },
      { label: "Started late", value: bc.started_late || 0, cls: "warn" },
      { label: "Not started", value: bc.not_started || 0, cls: "bad" },
    ]);
  }

  // ---- interactive activity grid: add/remove fields + drill-into-metadata ----
  const ALL_FIELDS = [
    { key: "unique_id", label: "UID", on: true },
    { key: "name", label: "Name", on: true },
    { key: "start", label: "Start", on: true },
    { key: "finish", label: "Finish", on: true },
    { key: "total_float_days", label: "Total float (d)", on: true },
    { key: "free_float_days", label: "Free float (d)", on: false },
    { key: "percent_complete", label: "% complete", on: true },
    { key: "is_critical", label: "Critical", on: true },
    { key: "wbs", label: "WBS", on: false },
  ];
  let activities = [];
  let sortKey = "unique_id";
  let sortDesc = false;

  function renderToggles() {
    const box = document.getElementById("fieldToggles");
    box.innerHTML = "";
    box.className = "field-toggles";
    ALL_FIELDS.forEach((f) => {
      const cb = el("input", { type: "checkbox" });
      cb.checked = f.on;
      cb.addEventListener("change", () => { f.on = cb.checked; renderGrid(); });
      const lab = el("label", {}, [cb, document.createTextNode(" " + f.label)]);
      box.appendChild(lab);
    });
  }

  function fmt(v) {
    if (v === true) return "yes";
    if (v === false) return "no";
    return v == null ? "" : String(v);
  }

  function renderGrid() {
    const grid = document.getElementById("grid");
    const fields = ALL_FIELDS.filter((f) => f.on);
    const rows = activities.slice().sort((a, b) => {
      const x = a[sortKey], y = b[sortKey];
      const cmp = x < y ? -1 : x > y ? 1 : 0;
      return sortDesc ? -cmp : cmp;
    });
    const table = el("table");
    const head = el("tr");
    fields.forEach((f) => {
      const th = el("th", { text: f.label });
      if (f.key === sortKey) th.className = "sorted" + (sortDesc ? " desc" : "");
      th.addEventListener("click", () => {
        if (sortKey === f.key) sortDesc = !sortDesc; else { sortKey = f.key; sortDesc = false; }
        renderGrid();
      });
      head.appendChild(th);
    });
    table.appendChild(head);
    rows.forEach((act) => {
      const tr = el("tr");
      if (act.is_critical) tr.className = "crit";
      fields.forEach((f) => tr.appendChild(el("td", { text: fmt(act[f.key]) })));
      tr.addEventListener("click", () => drill(act));
      table.appendChild(tr);
    });
    grid.innerHTML = "";
    grid.appendChild(table);
  }

  function drill(act) {
    const panel = document.getElementById("drill");
    panel.innerHTML = "";
    panel.className = "drill show";
    panel.appendChild(el("h3", { text: "Activity " + act.unique_id + " — " + act.name }));
    const dl = el("dl");
    ALL_FIELDS.forEach((f) => {
      dl.appendChild(el("dt", { text: f.label }));
      dl.appendChild(el("dd", { text: fmt(act[f.key]) }));
    });
    dl.appendChild(el("dt", { text: "Citation" }));
    dl.appendChild(el("dd", { text: act.name + " (UID " + act.unique_id + ", " + (act.source_file || "schedule") + ")" }));
    panel.appendChild(dl);
  }

  function renderGantt(driving) {
    const box = document.getElementById("gantt");
    box.innerHTML = "";
    box.appendChild(el("h3", { text: "Driving path to UID " + driving.target_uid + " — " + (driving.target_name || "") }));
    const legend = el("div", { class: "legend" });
    ["DRIVING", "SECONDARY", "TERTIARY", "BEYOND"].forEach((t) =>
      legend.appendChild(el("span", { class: "tier-" + t, text: t.toLowerCase() })));
    box.appendChild(legend);
    const rows = driving.rows;
    if (!rows.length) { box.appendChild(el("p", { class: "muted", text: "No ancestors trace to that UID." })); return; }
    const times = rows.flatMap((r) => [r.start_ord, r.finish_ord]).filter((x) => x != null);
    const lo = Math.min(...times), hi = Math.max(...times), span = Math.max(1, hi - lo);
    rows.forEach((r) => {
      const track = el("div", { class: "gantt-track" });
      if (r.start_ord != null && r.finish_ord != null) {
        const left = ((r.start_ord - lo) / span) * 100;
        const width = Math.max(1, ((r.finish_ord - r.start_ord) / span) * 100);
        const bar = el("div", { class: "gantt-bar tier-" + r.tier, style: "left:" + left + "%;width:" + width + "%" });
        bar.title = r.name + " — driving slack " + r.driving_slack_days + "d (" + r.tier + ")";
        track.appendChild(bar);
      }
      box.appendChild(el("div", { class: "gantt-row" }, [
        el("span", { text: "UID " + r.unique_id + " " + r.name.slice(0, 22) }), track,
      ]));
    });
  }

  function loadGantt() {
    const target = document.getElementById("targetUid").value;
    if (!target) return;
    const sec = document.getElementById("secMax").value || 10;
    const ter = document.getElementById("terMax").value || 20;
    fetch("/api/driving/" + enc + "?target=" + target + "&secondary=" + sec + "&tertiary=" + ter)
      .then((r) => r.ok ? r.json() : Promise.reject(r.status))
      .then(renderGantt)
      .catch(() => { document.getElementById("gantt").textContent = "No driving path for that UID."; });
  }

  fetch("/api/analysis/" + enc)
    .then((r) => r.json())
    .then((data) => {
      activities = data.activities || [];
      renderCharts(data);
      renderToggles();
      renderGrid();
    })
    .catch(() => { document.getElementById("charts").textContent = "Failed to load analysis."; });

  document.getElementById("ganttBtn").addEventListener("click", loadGantt);
})();
