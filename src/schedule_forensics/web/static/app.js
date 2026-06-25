/* Schedule Forensics — interactive Power-BI-style visuals (M14).
 *
 * Dependency-free, fully local: no CDN, no external fetch, no third-party library (the
 * strongest air-gap posture for a CUI tool). Renders charts, an interactive activity grid
 * with add/remove fields and click-to-drill-into-metadata, and a Gantt that highlights the
 * driving / secondary / tertiary path tiers to a chosen target UID. All data comes from the
 * local /api endpoints; every drilled value carries its citation (file + UID + task name).
 *
 * Both Gantts (the always-on activity grid timeline and the driving-path trace) use the
 * SAME scalable model as the /path workspace: a user-adjustable zoom in PIXELS PER DAY and
 * horizontal scroll, instead of squeezing the whole span into a fixed-width column. Bars
 * therefore keep a true, legible time scale on long programs and the operator can zoom in.
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

  // DCMA overview: a stoplight (green/amber/red) + the measured value per check, instead of a
  // bar. Each row carries a hover/focus tooltip (what it is, why it matters, the threshold, and a
  // pass + a fail example). A plain-text title= keeps the same detail with no CSS/JS (a11y).
  // Place a floating tooltip (appended to <body>, position:fixed) just under its row, flipping
  // above when there's no room below and clamping to the viewport. Fixed positioning on <body>
  // lets the tip ESCAPE the chart frame's overflow clip — the old in-flow absolute tooltip was
  // cut off behind the Gantt (operator bug report).
  function placeFloatTip(tip, row) {
    tip.style.display = "block"; // must be visible to measure its size
    const pad = 6;
    const r = row.getBoundingClientRect();
    const t = tip.getBoundingClientRect();
    let left = r.left;
    if (left + t.width > window.innerWidth - pad) left = window.innerWidth - pad - t.width;
    let top = r.bottom + 4;
    if (top + t.height > window.innerHeight - pad) {
      const above = r.top - 4 - t.height;
      top = above >= pad ? above : Math.max(pad, window.innerHeight - pad - t.height);
    }
    tip.style.left = Math.max(pad, left) + "px";
    tip.style.top = Math.max(pad, top) + "px";
  }

  function dcmaPanel(container, dcma) {
    // a prior render's floating tips live on <body>; clear them before rebuilding
    Array.prototype.forEach.call(document.querySelectorAll(".dcma-tip-float"), (n) => n.remove());
    const box = el("div", { class: "chart dcma-overview" });
    box.appendChild(el("h3", { text: "DCMA-14 checks" }));
    Object.keys(dcma).forEach((k) => {
      const d = dcma[k];
      const st = d.status === "PASS" ? "ok" : d.status === "FAIL" ? "bad" : "warn";
      const heading = d.label + " — " + d.name;
      // the rich tooltip is parented to <body> (position:fixed) so the chart frame's overflow
      // can never clip it; app.js shows/positions it on hover & keyboard focus
      const tip = el("div", { class: "dcma-tip dcma-tip-float", role: "tooltip" });
      tip.appendChild(el("b", { text: heading }));
      const para = (label, val) => {
        if (!val) return;
        const node = el("p", {});
        if (label) node.appendChild(el("b", { text: label + " " }));
        node.appendChild(document.createTextNode(val));
        tip.appendChild(node);
      };
      para("", d.definition);
      para("Why it matters:", d.why);
      para("Threshold:", d.threshold);
      para("Pass example:", d.example_ok);
      para("Fail example:", d.example_fail);
      document.body.appendChild(tip);
      const row = el(
        "div",
        {
          class: "dcma-ov-row sl-" + st,
          tabindex: "0",
          "aria-label": heading + ": " + d.status + ", " + d.measure,
        },
        [
          el("span", { class: "sl-dot sl-" + st, "aria-hidden": "true" }),
          el("span", { class: "dcma-ov-name", text: heading }),
          el("span", { class: "dcma-ov-measure", text: d.measure }),
          el("span", { class: "dcma-info", "aria-hidden": "true", text: "ⓘ" }),
        ]
      );
      const show = () => placeFloatTip(tip, row);
      const hide = () => { tip.style.display = "none"; };
      row.addEventListener("mouseenter", show);
      row.addEventListener("mouseleave", hide);
      row.addEventListener("focus", show);
      row.addEventListener("blur", hide);
      box.appendChild(row);
    });
    container.appendChild(box);
  }

  function renderCharts(data) {
    const charts = document.getElementById("charts");
    charts.innerHTML = "";
    dcmaPanel(charts, data.dcma);
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
  let sortKey = "order"; // default = file/outline order (parents above children, MS-Project)
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

  // Read a column value off an activity. Standard fields are top-level; .mpp custom/extended fields
  // (added to ALL_FIELDS from data.custom_field_labels) live under act.custom[label]. Looking there
  // only when the key is not a top-level property keeps sorting/filtering working for both.
  function valueOf(act, key) {
    if (act == null) return null;
    if (Object.prototype.hasOwnProperty.call(act, key)) return act[key];
    return act.custom ? act.custom[key] : null;
  }

  // ---- timeline helpers: a SCALABLE px-per-day axis (matches the /path workspace) ----
  const DAY_MS = 86400000;

  let forcedPx = null; // set by the "Fit" button (whole project on screen); cleared by the slider
  function pxPerDay() {
    if (forcedPx && forcedPx > 0) return forcedPx;
    const z = document.getElementById("vizZoom");
    const v = z ? Number(z.value) : 8;
    return v > 0 ? v : 8; // pixels per calendar day
  }
  // Fit the ENTIRE project span into the visible width (no horizontal scroll). avail = the grid's
  // own client width minus an estimate of the data columns; the Scale slider then fine-tunes.
  function fitToWidth() {
    let t0 = null, t1 = null;
    activities.forEach((a) => {
      if (a.start) { const s = Date.parse(a.start); if (!isNaN(s)) t0 = t0 === null ? s : Math.min(t0, s); }
      if (a.finish) { const f = Date.parse(a.finish); if (!isNaN(f)) t1 = t1 === null ? f : Math.max(t1, f); }
    });
    if (t0 === null || t1 === null) return;
    const days = Math.max(1, (t1 - t0) / DAY_MS) + 4;
    const host = document.getElementById("grid");
    const avail = Math.max(240, (host ? host.clientWidth : 960) - 360);
    forcedPx = Math.max(0.05, avail / days);
    renderGrid();
    if (lastDriving) renderGantt(lastDriving);
  }

  // Build a horizontal time axis from rows carrying ISO `start`/`finish`, padded two days
  // each side and stretched to include an anchor date (the data date). Returns null when
  // nothing is dated. `x(ms)` maps a millisecond timestamp to a pixel offset; `width` is the
  // full px span the track/scale must occupy so the container scrolls instead of squeezing.
  function buildAxis(items, anchorDate) {
    const px = pxPerDay();
    let t0 = null, t1 = null;
    items.forEach((it) => {
      if (it.start) { const s = Date.parse(it.start); if (!isNaN(s)) t0 = t0 === null ? s : Math.min(t0, s); }
      if (it.finish) { const f = Date.parse(it.finish); if (!isNaN(f)) t1 = t1 === null ? f : Math.max(t1, f); }
    });
    const anchor = anchorDate || statusDate;
    if (anchor) {
      const a = Date.parse(anchor);
      if (!isNaN(a) && t0 !== null && t1 !== null) { t0 = Math.min(t0, a); t1 = Math.max(t1, a); }
    }
    if (t0 === null || t1 === null) return null;
    t0 -= 2 * DAY_MS; t1 += 2 * DAY_MS;
    const width = Math.max(120, Math.round((t1 - t0) / DAY_MS) * px);
    return { t0, t1, width, x: (ms) => Math.round(((ms - t0) / DAY_MS) * px) };
  }

  // The Microsoft-Project-style timeline (stacked Year/Quarter/Month header + month/quarter/year
  // gridlines) is shared with every other Gantt on the site via window.SFGantt (static/gantt.js).
  const buildTierScale = SFGantt.buildTierScale;
  const gridLines = SFGantt.gridLines;

  function timelineCell(act, axis, grid) {
    const cell = el("td", { class: "g-cell" });
    const track = el("div", { class: "g-track", style: "width:" + axis.width + "px" });
    (grid || []).forEach((g) => track.appendChild(el("div", { class: g.cls, style: "left:" + g.left + "px" })));
    if (statusDate) {
      const sd = Date.parse(statusDate);
      if (!isNaN(sd)) track.appendChild(el("div", { class: "g-status", style: "left:" + axis.x(sd) + "px" }));
    }
    const s = act.start ? Date.parse(act.start) : null;
    const f = act.finish ? Date.parse(act.finish) : null;
    if (act.is_milestone && s != null) {
      const ms = el("div", { class: "g-ms", style: "left:" + axis.x(s) + "px" });
      ms.title = act.name + " (milestone) " + act.start;
      track.appendChild(ms);
    } else if (s != null && f != null) {
      const left = axis.x(s);
      const width = Math.max(2, axis.x(f) - left);
      const cls = act.is_summary ? "g-bar g-sum" : act.is_critical ? "g-bar g-crit" : "g-bar";
      const bar = el("div", { class: cls, style: "left:" + left + "px;width:" + width + "px" });
      bar.title = act.name + "  " + act.start + " → " + act.finish +
        (act.is_summary ? " (summary)" : "  " + (act.percent_complete || 0) + "%");
      if (!act.is_summary && (act.complete || act.percent_complete > 0)) {
        var pctDone = act.complete ? 100 : Math.min(100, act.percent_complete);
        bar.appendChild(el("div", { class: "g-done", style: "width:" + pctDone + "%" }));
      }
      track.appendChild(bar);
    }
    cell.appendChild(track);
    return cell;
  }

  // field key -> selected-value Set (MS-Project-style checklist filter); absent/null = all
  const filters = {};

  function rowMatches(act, fields) {
    return fields.every((f) => {
      const sel = filters[f.key];
      if (!sel) return true; // unfiltered (all values selected)
      return sel.has(fmt(valueOf(act, f.key))); // an empty Set hides every row
    });
  }

  // distinct, sorted (numeric-aware) formatted values of a column — the checklist contents
  function distinctValues(key) {
    const seen = new Set();
    activities.forEach((a) => seen.add(fmt(valueOf(a, key))));
    const iso = /^\d{4}-\d\d-\d\d/;
    return Array.from(seen).sort((a, b) => {
      if (iso.test(a) && iso.test(b)) return a < b ? -1 : a > b ? 1 : 0; // ISO dates sort lexically
      const na = parseFloat(a), nb = parseFloat(b);
      const bothNum = !isNaN(na) && !isNaN(nb) && /^-?\d/.test(a) && /^-?\d/.test(b);
      return bothNum ? na - nb : a < b ? -1 : a > b ? 1 : 0;
    });
  }

  function renderBody(tbody, fields, axis, grid) {
    const rows = activities
      .filter((act) => rowMatches(act, fields))
      .sort((a, b) => {
        const x = valueOf(a, sortKey), y = valueOf(b, sortKey);
        const cmp = x < y ? -1 : x > y ? 1 : 0;
        return sortDesc ? -cmp : cmp;
      });
    tbody.innerHTML = "";
    rows.forEach((act) => {
      const tr = el("tr");
      if (act.is_critical) tr.className = "crit";
      if (act.is_summary) tr.className = (tr.className + " sum").trim();
      fields.forEach((f) => {
        const td = el("td", { text: fmt(valueOf(act, f.key)) });
        if (f.key === "name") {
          // MS-Project WBS indentation: each outline level indents the task name (any depth)
          td.className = "name-cell";
          td.style.paddingLeft = 6 + (act.outline_level || 0) * 14 + "px";
        }
        tr.appendChild(td);
      });
      if (axis) tr.appendChild(timelineCell(act, axis, grid));
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
    if (window.SFChecklist) SFChecklist.close(); // rebuilding the row discards any open popup
    const grid = document.getElementById("grid");
    const fields = ALL_FIELDS.filter((f) => f.on);
    // the axis spans ALL activities so the scale stays stable as filters/columns change
    const axis = buildAxis(activities);
    const gridLns = axis ? gridLines(axis) : null; // vertical month/quarter/year gridlines
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
    if (axis) {
      const th = el("th", { class: "g-head" });
      th.appendChild(buildTierScale(axis, "g-scale", statusDate)); // Year/Quarter/Month (MS Project)
      head.appendChild(th);
    }
    thead.appendChild(head);
    // per-column filter row: MS-Project-style checklist dropdowns (select-all / clear / search
    // the distinct values), replacing the old substring inputs
    const filterRow = el("tr", { class: "filter-row" });
    const tbody = el("tbody");
    fields.forEach((f) => {
      const td = el("td");
      if (window.SFChecklist) {
        td.appendChild(SFChecklist.filter({
          values: distinctValues(f.key),
          selected: filters[f.key] || null,
          label: "Filter",
          title: "Filter " + f.label,
          onChange: (selSet) => { filters[f.key] = selSet; renderBody(tbody, fields, axis, gridLns); },
        }));
      }
      td.addEventListener("click", (ev) => ev.stopPropagation());
      filterRow.appendChild(td);
    });
    if (axis) filterRow.appendChild(el("td", { class: "muted" }));
    thead.appendChild(filterRow);
    table.appendChild(thead);
    table.appendChild(tbody);
    renderBody(tbody, fields, axis, gridLns);
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
      dl.appendChild(el("dd", { text: fmt(valueOf(act, f.key)) }));
    });
    dl.appendChild(el("dt", { text: "Citation" }));
    dl.appendChild(el("dd", { text: act.name + " (UID " + act.unique_id + ", " + (act.source_file || "schedule") + ")" }));
    panel.appendChild(dl);
  }

  let lastDriving = null; // re-render the trace when "show completed" / tier / zoom changes
  let ganttTierSel = null; // checklist selection of tiers to show in the trace (null = all)

  function renderGantt(driving) {
    lastDriving = driving;
    const box = document.getElementById("gantt");
    box.innerHTML = "";
    if (driving.note && !(driving.rows || []).length) {
      box.appendChild(el("p", { class: "muted", text: driving.note }));
      return;
    }
    box.appendChild(el("h3", { text: "Driving path to UID " + driving.target_uid + " — " + (driving.target_name || "") + " (waterfall: earliest finish first)" }));
    const legend = el("div", { class: "legend" });
    ["DRIVING", "SECONDARY", "TERTIARY", "BEYOND"].forEach((t) =>
      legend.appendChild(el("span", { class: "tier-" + t, text: t.toLowerCase() })));
    box.appendChild(legend);
    const showDone = document.getElementById("showDone");
    const includeDone = !showDone || showDone.checked;
    // waterfall: earliest finish -> latest finish (the server pre-sorts; keep it stable here)
    const rows = driving.rows
      .filter((r) => includeDone || !r.complete)
      .filter((r) => !ganttTierSel || ganttTierSel.has(r.tier))
      .slice()
      .sort((a, b) => (a.finish_ord ?? Infinity) - (b.finish_ord ?? Infinity));
    if (!rows.length) {
      box.appendChild(el("p", { class: "muted", text: "No activities to show (adjust the tier filter or enable completed tasks)." }));
      return;
    }
    const axis = buildAxis(rows, driving.data_date);
    if (!axis) { box.appendChild(el("p", { class: "muted", text: "No dated activities to plot." })); return; }
    const scroll = el("div", { class: "gantt-scroll" });
    // Dur / Start / Finish / Driving-slack columns (operator request) between the name and the bar.
    function traceCols(r) {
      const c = el("div", { class: "gantt-cols" });
      const h = !r;
      c.appendChild(el("div", { class: "gantt-col c-dur", text: h ? "Dur d" : (r.duration_days != null ? String(r.duration_days) : "") }));
      c.appendChild(el("div", { class: "gantt-col c-date", text: h ? "Start" : (r.start || "") }));
      c.appendChild(el("div", { class: "gantt-col c-date", text: h ? "Finish" : (r.finish || "") }));
      c.appendChild(el("div", { class: "gantt-col c-slack", text: h ? "Driv slack" : (r.driving_slack_days != null ? r.driving_slack_days + "d" : "") }));
      return c;
    }
    // header row: name spacer + the Dur/Start/Finish/Slack headers + the Y/Q/M scale (MS Project)
    const headRow = el("div", { class: "gantt-row gantt-head" });
    headRow.appendChild(el("span", { class: "gantt-name" }));
    headRow.appendChild(traceCols(null));
    headRow.appendChild(buildTierScale(axis, "gantt-scale", driving.data_date));
    scroll.appendChild(headRow);
    const gridLns = gridLines(axis); // MS-Project vertical month/quarter/year gridlines
    rows.forEach((r) => {
      const done = !!r.complete;
      const track = el("div", { class: "gantt-track", style: "width:" + axis.width + "px" });
      gridLns.forEach((g) => track.appendChild(el("div", { class: g.cls, style: "left:" + g.left + "px" })));
      if (driving.data_date) {
        const dd = Date.parse(driving.data_date);
        if (!isNaN(dd)) track.appendChild(el("div", { class: "g-status", style: "left:" + axis.x(dd) + "px" }));
      }
      const s = r.start ? Date.parse(r.start) : null;
      const f = r.finish ? Date.parse(r.finish) : null;
      if (r.is_milestone && s != null) {
        // milestones render as diamonds at their date, tinted by tier
        const ms = el("div", { class: "g-ms tier-" + r.tier, style: "left:" + axis.x(s) + "px" });
        ms.title = r.name + " (milestone) — driving slack " + r.driving_slack_days + "d (" + r.tier + ")";
        track.appendChild(ms);
      } else if (s != null && f != null) {
        const left = axis.x(s);
        const width = Math.max(2, axis.x(f) - left);
        const bar = el("div", { class: "gantt-bar tier-" + r.tier + (done ? " done" : ""), style: "left:" + left + "px;width:" + width + "px" });
        bar.title = r.name + " — driving slack " + r.driving_slack_days + "d (" + r.tier + ")" + (done ? " — complete" : "");
        track.appendChild(bar);
      }
      const row = el("div", { class: "gantt-row" + (done ? " done" : "") });
      row.appendChild(el("span", { class: "gantt-name", text: "UID " + r.unique_id + " " + r.name }));
      row.appendChild(traceCols(r));
      row.appendChild(track);
      scroll.appendChild(row);
    });
    box.appendChild(scroll);
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
      // every .mpp custom/extended field becomes an optional, toggleable column (default off)
      (data.custom_field_labels || []).forEach((lbl) => {
        if (!ALL_FIELDS.some((f) => f.key === lbl)) {
          ALL_FIELDS.push({ key: lbl, label: lbl, on: false, custom: true });
        }
      });
      renderCharts(data);
      renderToggles();
      renderGrid();
      // a session-wide target pre-fills the trace box — run the trace right away
      if (document.getElementById("targetUid").value) loadGantt();
    })
    .catch(() => { document.getElementById("charts").textContent = "Failed to load analysis."; });

  document.getElementById("ganttBtn").addEventListener("click", loadGantt);
  const showDone = document.getElementById("showDone");
  if (showDone) showDone.addEventListener("change", () => { if (lastDriving) renderGantt(lastDriving); });
  const ganttTierMount = document.getElementById("ganttTier");
  if (ganttTierMount && window.SFChecklist) {
    ganttTierMount.appendChild(SFChecklist.filter({
      values: ["DRIVING", "SECONDARY", "TERTIARY", "BEYOND"],
      selected: null,
      label: "Tier",
      title: "Show driving-path tiers",
      onChange: (s) => { ganttTierSel = s; if (lastDriving) renderGantt(lastDriving); },
    }));
  }
  // one page-level "pixels per day" zoom rescales BOTH the activity grid timeline and the trace
  const vizZoom = document.getElementById("vizZoom");
  if (vizZoom) vizZoom.addEventListener("input", () => {
    forcedPx = null; // a manual zoom returns from "Fit" to the slider value
    renderGrid();
    if (lastDriving) renderGantt(lastDriving);
  });
  const fitBtn = document.getElementById("fitBtn");
  if (fitBtn) fitBtn.addEventListener("click", fitToWidth);
})();
