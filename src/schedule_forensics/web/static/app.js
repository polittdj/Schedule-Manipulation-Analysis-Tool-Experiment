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

  // ---- interactive activity grid + Gantt: add/remove fields + drill-into-metadata ----
  const ALL_FIELDS = [
    { key: "unique_id", label: "UID", on: true },
    { key: "name", label: "Name", on: true },
    { key: "duration_days", label: "Duration (d)", on: false },
    { key: "start", label: "Start", on: true },
    { key: "finish", label: "Finish", on: true },
    { key: "baseline_start", label: "Baseline start", on: false },
    { key: "baseline_finish", label: "Baseline finish", on: false },
    { key: "total_float_days", label: "Total float (d)", on: true },
    { key: "free_float_days", label: "Free float (d)", on: false },
    { key: "percent_complete", label: "% complete", on: true },
    { key: "is_critical", label: "Critical", on: false },
    { key: "resource_names", label: "Resources", on: false },
    { key: "wbs", label: "WBS", on: false },
  ];
  let activities = [];
  let statusDate = null; // ISO date from the schedule's data date (vertical marker)
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

  // ---- timeline helpers (the MS-Project-style Gantt column) ----
  const DAY_MS = 86400000;

  function timeRange(rows) {
    const dates = rows
      .flatMap((r) => [r.start, r.finish])
      .filter(Boolean)
      .map((d) => Date.parse(d));
    if (!dates.length) return null;
    const lo = Math.min(...dates), hi = Math.max(...dates);
    return { lo, span: Math.max(DAY_MS, hi - lo) };
  }

  function pct(range, t) {
    return Math.max(0, Math.min(100, ((t - range.lo) / range.span) * 100));
  }

  function monthTicks(range) {
    // first-of-month markers across the range, for the timeline header
    const ticks = [];
    const d = new Date(range.lo);
    d.setUTCDate(1);
    for (;;) {
      d.setUTCMonth(d.getUTCMonth() + 1);
      const t = d.getTime();
      if (t >= range.lo + range.span) break;
      ticks.push({ left: pct(range, t), label: (d.getUTCMonth() + 1) + "/" + (d.getUTCFullYear() % 100) });
    }
    // thin out so labels never overlap (cap ~12 labels)
    const step = Math.ceil(ticks.length / 12);
    return ticks.filter((_, i) => i % step === 0);
  }

  function timelineCell(act, range) {
    const cell = el("td", { class: "g-cell" });
    const track = el("div", { class: "g-track" });
    if (statusDate) {
      const sd = Date.parse(statusDate);
      if (sd >= range.lo && sd <= range.lo + range.span) {
        track.appendChild(el("div", { class: "g-status", style: "left:" + pct(range, sd) + "%" }));
      }
    }
    const s = act.start ? Date.parse(act.start) : null;
    const f = act.finish ? Date.parse(act.finish) : null;
    if (act.is_milestone && s != null) {
      const ms = el("div", { class: "g-ms", style: "left:" + pct(range, s) + "%" });
      ms.title = act.name + " (milestone) " + act.start;
      track.appendChild(ms);
    } else if (s != null && f != null) {
      const left = pct(range, s);
      const width = Math.max(0.6, pct(range, f) - left);
      const cls = act.is_summary ? "g-bar g-sum" : act.is_critical ? "g-bar g-crit" : "g-bar";
      const bar = el("div", { class: cls, style: "left:" + left + "%;width:" + width + "%" });
      bar.title = act.name + "  " + act.start + " → " + act.finish +
        (act.is_summary ? " (summary)" : "  " + (act.percent_complete || 0) + "%");
      if (!act.is_summary && act.percent_complete > 0) {
        bar.appendChild(el("div", { class: "g-done", style: "width:" + Math.min(100, act.percent_complete) + "%" }));
      }
      track.appendChild(bar);
    }
    cell.appendChild(track);
    return cell;
  }

  const filters = {}; // field key -> filter text (MS-Project-style per-column filter)

  function rowMatches(act, fields) {
    return fields.every((f) => {
      const needle = (filters[f.key] || "").trim();
      if (!needle) return true;
      const raw = act[f.key];
      // numeric comparators: >5, <10, =3 (work on the raw value when it is a number)
      const m = needle.match(/^(>=|<=|>|<|=)\s*(-?\d+(?:\.\d+)?)$/);
      if (m && typeof raw === "number") {
        const n = parseFloat(m[2]);
        if (m[1] === ">") return raw > n;
        if (m[1] === "<") return raw < n;
        if (m[1] === ">=") return raw >= n;
        if (m[1] === "<=") return raw <= n;
        return raw === n;
      }
      return fmt(raw).toLowerCase().includes(needle.toLowerCase());
    });
  }

  function renderBody(tbody, fields, range) {
    const rows = activities
      .filter((act) => rowMatches(act, fields))
      .sort((a, b) => {
        const x = a[sortKey], y = b[sortKey];
        const cmp = x < y ? -1 : x > y ? 1 : 0;
        return sortDesc ? -cmp : cmp;
      });
    tbody.innerHTML = "";
    rows.forEach((act) => {
      const tr = el("tr");
      if (act.is_critical) tr.className = "crit";
      if (act.is_summary) tr.className = (tr.className + " sum").trim();
      fields.forEach((f) => tr.appendChild(el("td", { text: fmt(act[f.key]) })));
      if (range) tr.appendChild(timelineCell(act, range));
      tr.addEventListener("click", () => drill(act));
      tbody.appendChild(tr);
    });
    if (!rows.length) {
      const tr = el("tr");
      tr.appendChild(el("td", { class: "muted", text: "No activities match the filters." }));
      tbody.appendChild(tr);
    }
  }

  function renderGrid() {
    const grid = document.getElementById("grid");
    const fields = ALL_FIELDS.filter((f) => f.on);
    const range = timeRange(activities);
    const table = el("table", { class: "gantt-grid" });
    const thead = el("thead");
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
    if (range) {
      const th = el("th", { class: "g-head", text: "Timeline" });
      monthTicks(range).forEach((tick) => {
        th.appendChild(el("span", { class: "g-tick", style: "left:" + tick.left + "%", text: tick.label }));
      });
      head.appendChild(th);
    }
    thead.appendChild(head);
    // per-column filter row (type to filter; numbers also take >n, <n, >=n, <=n, =n)
    const filterRow = el("tr", { class: "filter-row" });
    const tbody = el("tbody");
    fields.forEach((f) => {
      const td = el("td");
      const input = el("input", { type: "text", placeholder: "filter…", value: filters[f.key] || "" });
      input.addEventListener("input", () => { filters[f.key] = input.value; renderBody(tbody, fields, range); });
      input.addEventListener("click", (ev) => ev.stopPropagation());
      td.appendChild(input);
      filterRow.appendChild(td);
    });
    if (range) filterRow.appendChild(el("td", { class: "muted" }));
    thead.appendChild(filterRow);
    table.appendChild(thead);
    table.appendChild(tbody);
    renderBody(tbody, fields, range);
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

  let lastDriving = null; // re-render the trace when "show completed" toggles

  function renderGantt(driving) {
    lastDriving = driving;
    const box = document.getElementById("gantt");
    box.innerHTML = "";
    box.appendChild(el("h3", { text: "Driving path to UID " + driving.target_uid + " — " + (driving.target_name || "") + " (waterfall: earliest finish first)" }));
    const legend = el("div", { class: "legend" });
    ["DRIVING", "SECONDARY", "TERTIARY", "BEYOND"].forEach((t) =>
      legend.appendChild(el("span", { class: "tier-" + t, text: t.toLowerCase() })));
    box.appendChild(legend);
    const showDone = document.getElementById("showDone");
    const includeDone = !showDone || showDone.checked;
    // waterfall: earliest finish -> latest finish (the server pre-sorts; keep it stable here)
    const rows = driving.rows
      .filter((r) => includeDone || (r.percent_complete || 0) < 100)
      .slice()
      .sort((a, b) => (a.finish_ord ?? Infinity) - (b.finish_ord ?? Infinity));
    if (!rows.length) { box.appendChild(el("p", { class: "muted", text: "No activities to show (try enabling completed tasks)." })); return; }
    const times = rows.flatMap((r) => [r.start_ord, r.finish_ord]).filter((x) => x != null);
    const lo = Math.min(...times), hi = Math.max(...times), span = Math.max(1, hi - lo);
    rows.forEach((r) => {
      const track = el("div", { class: "gantt-track" });
      const done = (r.percent_complete || 0) >= 100;
      if (r.is_milestone && r.start_ord != null) {
        // milestones render as diamonds at their date, tinted by tier
        const ms = el("div", { class: "g-ms tier-" + r.tier, style: "left:" + ((r.start_ord - lo) / span) * 100 + "%" });
        ms.title = r.name + " (milestone) — driving slack " + r.driving_slack_days + "d (" + r.tier + ")";
        track.appendChild(ms);
      } else if (r.start_ord != null && r.finish_ord != null) {
        const left = ((r.start_ord - lo) / span) * 100;
        const width = Math.max(1, ((r.finish_ord - r.start_ord) / span) * 100);
        const bar = el("div", { class: "gantt-bar tier-" + r.tier + (done ? " done" : ""), style: "left:" + left + "%;width:" + width + "%" });
        bar.title = r.name + " — driving slack " + r.driving_slack_days + "d (" + r.tier + ")" + (done ? " — complete" : "");
        track.appendChild(bar);
      }
      box.appendChild(el("div", { class: "gantt-row" + (done ? " done" : "") }, [
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
      statusDate = data.status_date || null;
      renderCharts(data);
      renderToggles();
      renderGrid();
    })
    .catch(() => { document.getElementById("charts").textContent = "Failed to load analysis."; });

  document.getElementById("ganttBtn").addEventListener("click", loadGantt);
  const showDone = document.getElementById("showDone");
  if (showDone) showDone.addEventListener("change", () => { if (lastDriving) renderGantt(lastDriving); });
})();
