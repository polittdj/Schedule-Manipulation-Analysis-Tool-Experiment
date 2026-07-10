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
  let maxOutline = 0; // MS-Project "show outline level N"; 0 = all levels
  let barDates = false; // MS-Project "dates on bars" — start/finish text at the bar ends
  // unlimited right scroll (ADR-0187): grown when a Gantt pane hits its right edge, so the
  // operator can keep scrolling into future time instead of stopping at the last bar
  let extraRightDays = 0;

  // MS-Project-style "add/remove columns" dropdown (the same checklist component as the filters)
  function renderToggles() {
    const box = document.getElementById("fieldToggles");
    box.innerHTML = "";
    box.className = "field-toggles";
    if (!window.SFChecklist) return;
    box.appendChild(
      SFChecklist.filter({
        values: ALL_FIELDS.map((f) => f.label),
        selected: new Set(ALL_FIELDS.filter((f) => f.on).map((f) => f.label)),
        label: "Columns",
        title: "Add or remove columns",
        onChange: (sel) => {
          ALL_FIELDS.forEach((f) => { f.on = sel ? sel.has(f.label) : true; });
          renderGrid();
        },
      })
    );
  }

  function fmt(v) {
    if (v === true) return "yes";
    if (v === false) return "no";
    if (v == null) return "";
    const s = String(v);
    // operator: every Gantt date reads MM/DD/YYYY, no time-of-day (SFGantt.fmtMDY returns ""
    // for non-dates, so every other value falls through untouched). Data stays ISO underneath.
    return SFGantt.fmtMDY(s) || s;
  }

  // Numeric/date-aware comparator for the checklist filter value lists: MM/DD/YYYY dates sort
  // chronologically (they read month-first but must not SORT month-first), raw ISO dates sort
  // lexically, numbers numerically, everything else lexically.
  function compareValues(a, b) {
    const mdy = /^(\d\d)\/(\d\d)\/(\d{4})$/;
    const ma = mdy.exec(a), mb = mdy.exec(b);
    if (ma && mb) {
      const ka = ma[3] + ma[1] + ma[2], kb = mb[3] + mb[1] + mb[2]; // yyyymmdd
      return ka < kb ? -1 : ka > kb ? 1 : 0;
    }
    const iso = /^\d{4}-\d\d-\d\d/;
    if (iso.test(a) && iso.test(b)) return a < b ? -1 : a > b ? 1 : 0;
    const na = parseFloat(a), nb = parseFloat(b);
    const bothNum = !isNaN(na) && !isNaN(nb) && /^-?\d/.test(a) && /^-?\d/.test(b);
    return bothNum ? na - nb : a < b ? -1 : a > b ? 1 : 0;
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
  let lastFrozenWidth = 0; // MEASURED frozen data-column width (SFGantt.freezeColumns return)
  // RAW pixels-per-day (slider value, or the Fit button's exact-fill px). The Timescale Size %
  // is applied SEPARATELY in buildAxis, AFTER the page-fill baseline, so Size scales the filled
  // timeline in both slider and Fit modes (earlier it was multiplied in here and then silently
  // undone by the fill-to-page step — operator: "Size ... nothing changes").
  function pxPerDay() {
    if (forcedPx && forcedPx > 0) return forcedPx; // "Fit" computed an exact fill — leave it be
    const z = document.getElementById("vizZoom");
    const v = z ? Number(z.value) : 8;
    return v > 0 ? v : 8; // pixels per calendar day
  }
  function sizeFactor() {
    const s = window.SFTimescale ? SFTimescale.sizeFactor() : 1;
    return s > 0 ? s : 1;
  }
  // "Fit project" (operator spec 2026-07-08): anchor the STATUS DATE near the left edge of the
  // visible timeline (FIT_LEAD in) and scale so the REMAINING project — status date to project
  // finish — fills the rest of the page. The completed past stays on the track and scrolls off
  // to the LEFT (scroll back to see it). avail = the grid's client width minus the REAL measured
  // frozen-column width (recorded each paint, like path.js). Falls back to whole-project fit
  // when the schedule carries no status date. The Scale slider then fine-tunes.
  const FIT_LEAD = 0.12; // fraction of the visible timeline kept ahead of the status date
  function fitToWidth() {
    let t0 = null, t1 = null;
    activities.forEach((a) => {
      if (a.start) { const s = Date.parse(a.start); if (!isNaN(s)) t0 = t0 === null ? s : Math.min(t0, s); }
      if (a.finish) { const f = Date.parse(a.finish); if (!isNaN(f)) t1 = t1 === null ? f : Math.max(t1, f); }
    });
    if (t0 === null || t1 === null) return;
    const host = document.getElementById("grid");
    const avail = Math.max(240, (host ? host.clientWidth : 960) - (lastFrozenWidth || 360) - 18);
    const sd = statusDate ? Date.parse(statusDate) : NaN;
    if (!isNaN(sd) && sd < t1) {
      // remaining span (status date -> finish + buildAxis's 2-day right pad) fills (1-FIT_LEAD)
      const remDays = Math.max(1, (t1 + 2 * DAY_MS - sd) / DAY_MS);
      forcedPx = Math.max(0.05, (avail * (1 - FIT_LEAD)) / remDays);
    } else {
      const days = Math.max(1, (t1 - t0) / DAY_MS) + 3; // + 1-day left / 2-day right pad
      forcedPx = Math.max(0.05, avail / days);
    }
    renderGrid();
    if (lastDriving) renderGantt(lastDriving);
    // scroll the past off to the left so the status date sits FIT_LEAD into the viewport
    if (!isNaN(sd) && host) {
      const trackX = ((sd - (t0 - 1 * DAY_MS)) / DAY_MS) * forcedPx; // buildAxis pads t0 by 1 day
      host.scrollLeft = Math.max(0, Math.round(trackX - FIT_LEAD * avail));
    }
  }

  // Build a horizontal time axis from rows carrying ISO `start`/`finish`, padded one day on the
  // left (the earliest bar hugs the frozen data columns) and two on the right, stretched to
  // include an anchor date (the data date). Returns null when nothing is dated. `x(ms)` maps a
  // millisecond timestamp to a pixel offset; `width` is the full px span the track/scale must
  // occupy so the container scrolls instead of squeezing.
  function buildAxis(items, anchorDate) {
    let px = pxPerDay(); // reassigned below for the page-fill baseline + Size % scaling
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
    // small left pad (bars start close to the data columns); the right pad grows via the
    // edge-extend scroll so the timeline is never a hard wall
    t0 -= 1 * DAY_MS; t1 += (2 + extraRightDays) * DAY_MS;
    let width = Math.max(120, Math.round((t1 - t0) / DAY_MS) * px);
    // operator 2026-07-08: at Size 100% the timeline uses ALL available page space — when the
    // project span is narrower than the page, extend the axis past the finish to fill it. This
    // establishes the FILL BASELINE (px), which the Timescale Size % then scales on top of.
    const host = document.getElementById("grid");
    const avail = host ? host.clientWidth - (lastFrozenWidth || 360) - 18 : 0;
    if (avail > width) {
      width = avail;
      px = width / ((t1 - t0) / DAY_MS); // fill px: the whole span now fills the page at 100%
    }
    // apply the Timescale dialog's Size %: <100 shrinks (leaves right-hand space), >100 overflows
    // and scrolls — a true zoom of the filled timeline (MS Project's Size behavior).
    const size = sizeFactor();
    px *= size;
    width = Math.max(120, Math.round(width * size));
    return { t0, t1, width, x: (ms) => Math.round(((ms - t0) / DAY_MS) * px) };
  }

  // The Microsoft-Project-style timeline (stacked Year/Quarter/Month header + month/quarter/year
  // gridlines) is shared with every other Gantt on the site via window.SFGantt (static/gantt.js).
  const buildTierScale = SFGantt.buildTierScale;
  const gridLines = SFGantt.gridLines;

  // MS-Project "dates on bars": an MM/DD/YYYY label beside a bar end / milestone diamond,
  // CLAMPED into the visible track so a label near x=0 or the right edge is no longer clipped
  // by the track's overflow:hidden (bug fix). `anchor` is the px the label should touch;
  // side "s" ends there (right-aligned, left of the bar), side "f" starts there.
  const LABEL_W = 64; // width estimate of "MM/DD/YYYY" at the 9px label font
  function barLabel(track, axis, anchor, side, iso) {
    let x = side === "s" ? anchor - LABEL_W : anchor;
    x = Math.max(0, Math.min(axis.width - LABEL_W, x));
    track.appendChild(el("div", {
      class: "g-barlabel g-barlabel-" + side,
      style: "left:" + x + "px;width:" + LABEL_W + "px",
      text: SFGantt.fmtMDY(iso),
    }));
  }

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
      // MS-Project "dates on bars": a milestone shows its finish date next to the diamond
      if (barDates && act.finish) barLabel(track, axis, axis.x(s) + 7, "f", act.finish);
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
      // MS-Project "dates on bars": start date left of the bar, finish date right of it
      if (barDates) {
        barLabel(track, axis, left - 3, "s", act.start);
        barLabel(track, axis, left + width + 3, "f", act.finish);
      }
    }
    cell.appendChild(track);
    SFGantt.paintNonwork(cell, axis); // continuous weekend/holiday shading over the full row
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

  // distinct, sorted (numeric/date-aware) formatted values of a column — the checklist contents
  function distinctValues(key) {
    const seen = new Set();
    activities.forEach((a) => seen.add(fmt(valueOf(a, key))));
    return Array.from(seen).sort(compareValues);
  }

  // "show completed tasks" (toolbar checkbox) applies to the WHOLE Activities grid + Gantt,
  // not just the driving-path trace: unchecked hides every 100%-complete row (a fully complete
  // summary is hidden too — everything beneath it is complete by definition).
  function includeCompleted() {
    const cb = document.getElementById("showDone");
    return !cb || cb.checked;
  }

  // Row visibility: the MS-Project "show outline level N" collapses deeper tasks, and summary
  // tasks are ALWAYS shown (they carry the WBS context) so the per-column filters only scope the
  // detail rows beneath them.
  function rowVisible(act, fields) {
    if (maxOutline > 0 && (act.outline_level || 0) > maxOutline) return false;
    if (!includeCompleted() && (act.complete || (act.percent_complete || 0) >= 100)) return false;
    return act.is_summary || rowMatches(act, fields);
  }

  function renderBody(tbody, fields, axis, grid) {
    const rows = activities
      .filter((act) => rowVisible(act, fields))
      .sort((a, b) => {
        const x = valueOf(a, sortKey), y = valueOf(b, sortKey);
        const cmp = x < y ? -1 : x > y ? 1 : 0;
        return sortDesc ? -cmp : cmp;
      });
    tbody.innerHTML = "";
    rows.forEach((act) => {
      const tr = el("tr");
      tr.setAttribute("data-uid", act.unique_id); // Find-a-UID jumps to tr[data-uid]
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
    // re-pin the frozen data columns once the new body rows exist (only when the table is already in
    // the DOM — the initial renderGrid freezes after it appends the table); record the measured
    // frozen width so fitToWidth can size the timeline to the REAL remaining page space
    const tbl = tbody.parentNode;
    if (tbl && tbl.isConnected && window.SFGantt && SFGantt.freezeColumns) {
      lastFrozenWidth = SFGantt.freezeColumns(tbl) || lastFrozenWidth;
    }
    // dependency link lines (operator 2026-07-10): drawn once the rows have laid out
    window.requestAnimationFrame(function () { drawLinks(tbody.parentNode); });
  }

  // MS-Project-style dependency link lines over the timeline: one SVG overlay inside the
  // scroll pane (so it scrolls with the chart), an elbow per relationship between VISIBLE
  // rows, arrowhead into the successor. The "links" toolbar checkbox shows/hides them.
  function linksOn() {
    const cb = document.getElementById("showLinks");
    return !cb || cb.checked;
  }
  function drawLinks(table) {
    const pane = document.getElementById("grid");
    if (!pane || !table || !table.isConnected) return;
    const old = pane.querySelector("svg.g-links");
    if (old) old.parentNode.removeChild(old);
    if (!linksOn()) return;
    if (getComputedStyle(pane).position === "static") pane.style.position = "relative";
    const anchors = {}; // uid -> {x1 (left), x2 (right), y (mid)} in pane content coords
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("class", "g-links");
    svg.setAttribute("width", table.scrollWidth);
    svg.setAttribute("height", table.offsetHeight);
    pane.appendChild(svg);
    const base = svg.getBoundingClientRect();
    table.querySelectorAll("tbody tr[data-uid]").forEach(function (tr) {
      const bar = tr.querySelector(".g-bar, .g-ms");
      if (!bar) return;
      const r = bar.getBoundingClientRect();
      anchors[tr.getAttribute("data-uid")] = {
        x1: r.left - base.left, x2: r.right - base.left, y: r.top - base.top + r.height / 2,
      };
    });
    const frag = document.createDocumentFragment();
    activities.forEach(function (act) {
      const to = anchors[act.unique_id];
      if (!to) return;
      (act.predecessors || []).forEach(function (pr) {
        const from = anchors[pr.uid];
        if (!from) return;
        // anchor points per dependency type (FS default): FS pred-right -> succ-left,
        // SS pred-left -> succ-left, FF pred-right -> succ-right, SF pred-left -> succ-right
        const tp = pr.type || "FS";
        const sx = tp === "SS" || tp === "SF" ? from.x1 : from.x2;
        const ex = tp === "FF" || tp === "SF" ? to.x2 + 4 : to.x1 - 4;
        const sy = from.y, ey = to.y;
        const stub = 7;
        let d;
        if (sx + stub <= ex) {
          d = "M" + sx + " " + sy + " H" + (sx + stub) + " V" + ey + " H" + ex;
        } else { // backward link: route around via a mid-row channel
          const ymid = sy < ey ? ey - 9 : ey + 9;
          d = "M" + sx + " " + sy + " H" + (sx + stub) + " V" + ymid + " H" + (ex - stub) + " V" + ey + " H" + ex;
        }
        const path = document.createElementNS(svgNS, "path");
        path.setAttribute("d", d);
        path.setAttribute("class", "g-link");
        frag.appendChild(path);
        const arrow = document.createElementNS(svgNS, "polygon");
        const dir = tp === "FF" || tp === "SF" ? -1 : 1; // arrow points INTO the successor bar
        arrow.setAttribute("points",
          ex + "," + ey + " " + (ex - 5 * dir) + "," + (ey - 3.2) + " " + (ex - 5 * dir) + "," + (ey + 3.2));
        arrow.setAttribute("class", "g-link-arrow");
        frag.appendChild(arrow);
      });
    });
    svg.appendChild(frag);
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
    // scrolling to the pane's right edge extends the axis (unlimited right scroll, ADR-0187)
    if (window.SFGantt && SFGantt.attachEdgeExtend) {
      SFGantt.attachEdgeExtend(grid, () => {
        extraRightDays += 60;
        renderGrid();
        if (lastDriving) renderGantt(lastDriving);
      });
    }
    if (window.SFColResize) SFColResize.attach(table, "analysis"); // MS-Project drag-to-resize columns
    // lock the data columns so they stay visible as the wide timeline scrolls left↔right, and
    // record their measured width — the fill space fitToWidth subtracts from the page
    if (window.SFGantt && SFGantt.freezeColumns) {
      lastFrozenWidth = SFGantt.freezeColumns(table) || lastFrozenWidth;
    }
  }

  // MS Project-style Task Information dialog (operator 2026-07-10, ADR-0183): click any
  // task / summary / milestone row and get the tabbed popup MS Project shows. The dialog
  // itself is the SHARED SFTaskInfo module (static/taskinfo.js, ADR-0186) so every Gantt
  // on the site opens the identical popup; this page's rows carry the full payload already.
  function drill(act) {
    if (window.SFTaskInfo) SFTaskInfo.open(act);
  }

  let lastDriving = null; // re-render the trace when "show completed" / tier / zoom changes
  let ganttTierSel = null; // checklist selection of tiers to show in the trace (null = all)

  // The driving-path trace columns (UID/Name + the operator's Dur/Start/Finish/Driving-slack).
  const TRACE_FIELDS = [
    { key: "unique_id", label: "UID" },
    { key: "name", label: "Name" },
    { key: "duration_days", label: "Dur d" },
    { key: "start", label: "Start" },
    { key: "finish", label: "Finish" },
    { key: "driving_slack_days", label: "Driv slack" },
  ];
  const traceFilters = {}; // trace field key -> selected-value Set (MS-Project checklist); null = all

  // one trace cell's display text: dates read MM/DD/YYYY, slack carries its unit
  function traceCellText(r, f) {
    const v = r[f.key];
    if (v == null) return "";
    if (f.key === "driving_slack_days") return v + "d";
    return fmt(v);
  }

  // distinct, sorted values of a trace column across the WHOLE trace — the checklist contents
  function traceDistinct(driving, f) {
    const seen = new Set();
    (driving.rows || []).forEach((r) => seen.add(traceCellText(r, f)));
    return Array.from(seen).sort(compareValues);
  }

  // the trace's timeline cell: tier-tinted bar / milestone diamond + gridlines + data date,
  // honoring the same "dates on bars" toggle as the activity grid below (bug fix)
  function traceTimelineCell(r, axis, gridLns, driving) {
    const cell = el("td", { class: "g-cell" });
    const track = el("div", { class: "g-track", style: "width:" + axis.width + "px" });
    gridLns.forEach((g) => track.appendChild(el("div", { class: g.cls, style: "left:" + g.left + "px" })));
    if (driving.data_date) {
      const dd = Date.parse(driving.data_date);
      if (!isNaN(dd)) track.appendChild(el("div", { class: "g-status", style: "left:" + axis.x(dd) + "px" }));
    }
    const done = !!r.complete;
    const s = r.start ? Date.parse(r.start) : null;
    const f = r.finish ? Date.parse(r.finish) : null;
    if (r.is_milestone && s != null) {
      // milestones render as diamonds at their date, tinted by tier
      const ms = el("div", { class: "g-ms tier-" + r.tier, style: "left:" + axis.x(s) + "px" });
      ms.title = r.name + " (milestone) — driving slack " + r.driving_slack_days + "d (" + r.tier + ")";
      track.appendChild(ms);
      if (barDates && r.finish) barLabel(track, axis, axis.x(s) + 7, "f", r.finish);
    } else if (s != null && f != null) {
      const left = axis.x(s);
      const width = Math.max(2, axis.x(f) - left);
      const bar = el("div", { class: "gantt-bar tier-" + r.tier + (done ? " done" : ""), style: "left:" + left + "px;width:" + width + "px" });
      bar.title = r.name + " — driving slack " + r.driving_slack_days + "d (" + r.tier + ")" + (done ? " — complete" : "");
      track.appendChild(bar);
      if (barDates) {
        barLabel(track, axis, left - 3, "s", r.start);
        barLabel(track, axis, left + width + 3, "f", r.finish);
      }
    }
    cell.appendChild(track);
    SFGantt.paintNonwork(cell, axis); // continuous weekend/holiday shading over the full row
    return cell;
  }

  // repaint only the trace body (per-column filter changes keep the open dropdown alive)
  function renderTraceRows(tbody, rows, axis, gridLns, driving) {
    const visible = rows.filter((r) =>
      TRACE_FIELDS.every((f) => {
        const sel = traceFilters[f.key];
        return !sel || sel.has(traceCellText(r, f)); // an empty Set hides every row
      })
    );
    tbody.innerHTML = "";
    visible.forEach((r) => {
      const tr = el("tr", { class: r.complete ? "done" : "" });
      TRACE_FIELDS.forEach((f) => {
        const td = el("td", { text: traceCellText(r, f) });
        if (f.key === "name") td.className = "name-cell";
        tr.appendChild(td);
      });
      tr.appendChild(traceTimelineCell(r, axis, gridLns, driving));
      tbody.appendChild(tr);
    });
    if (!visible.length) {
      const tr = el("tr");
      tr.appendChild(el("td", { class: "muted", text: "No activities match the filters." }));
      tbody.appendChild(tr);
    }
    // re-pin the frozen data columns once the new body rows exist (initial render freezes after
    // the table is appended)
    const tbl = tbody.parentNode;
    if (tbl && tbl.isConnected && window.SFGantt && SFGantt.freezeColumns) SFGantt.freezeColumns(tbl);
  }

  // The driving-path trace is the SAME table-based gantt-grid as every other grid on the site:
  // a sticky thead (column titles + the tiered Y/Q/M timescale + a per-column filter row),
  // SFGantt-frozen data columns, SFColResize drag-to-resize — replacing the old one-off
  // flex-div layout that had none of those.
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
    // the axis spans the tier/completed selection; column filters repaint the body only, so the
    // scale stays stable while the operator scopes rows (same policy as the activity grid)
    const axis = buildAxis(rows, driving.data_date);
    if (!axis) { box.appendChild(el("p", { class: "muted", text: "No dated activities to plot." })); return; }
    const gridLns = gridLines(axis); // MS-Project vertical month/quarter/year gridlines
    const scroll = el("div", { class: "gantt-scroll" });
    const table = el("table", { class: "gantt-grid trace-grid" });
    const thead = el("thead");
    const head = el("tr");
    TRACE_FIELDS.forEach((f) => head.appendChild(el("th", { text: f.label })));
    const thTime = el("th", { class: "g-head" });
    thTime.appendChild(buildTierScale(axis, "g-scale", driving.data_date)); // Year/Quarter/Month
    head.appendChild(thTime);
    thead.appendChild(head);
    // per-column MS-Project checklist filters (same component as the grids below)
    const filterRow = el("tr", { class: "filter-row" });
    const tbody = el("tbody");
    TRACE_FIELDS.forEach((f) => {
      const td = el("td");
      if (window.SFChecklist) {
        td.appendChild(SFChecklist.filter({
          values: traceDistinct(driving, f),
          selected: traceFilters[f.key] || null,
          label: "Filter",
          title: "Filter " + f.label,
          onChange: (sel) => { traceFilters[f.key] = sel; renderTraceRows(tbody, rows, axis, gridLns, driving); },
        }));
      }
      td.addEventListener("click", (ev) => ev.stopPropagation());
      filterRow.appendChild(td);
    });
    filterRow.appendChild(el("td", { class: "muted" }));
    thead.appendChild(filterRow);
    table.appendChild(thead);
    table.appendChild(tbody);
    renderTraceRows(tbody, rows, axis, gridLns, driving);
    scroll.appendChild(table);
    box.appendChild(scroll);
    if (window.SFGantt && SFGantt.attachEdgeExtend) {
      SFGantt.attachEdgeExtend(scroll, () => {
        extraRightDays += 60;
        renderGrid();
        if (lastDriving) renderGantt(lastDriving);
      });
    }
    if (window.SFColResize) SFColResize.attach(table, "trace"); // MS-Project drag-to-resize columns
    // lock the data columns so they stay visible as the wide timeline scrolls left↔right
    if (window.SFGantt && SFGantt.freezeColumns) SFGantt.freezeColumns(table);
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

  // MS-Project "find" — jump the grid to a UniqueID, scroll it into view and flash it.
  function findUid(uid) {
    const grid = document.getElementById("grid");
    const status = document.getElementById("gridFindStatus");
    if (!grid || !uid) return;
    const row = grid.querySelector('tr[data-uid="' + uid + '"]');
    if (!row) {
      if (status) status.textContent = "UID " + uid + " not in view";
      return;
    }
    if (status) status.textContent = "";
    row.scrollIntoView({ block: "center", behavior: "smooth" });
    grid.querySelectorAll("tr.row-found").forEach((r) => r.classList.remove("row-found"));
    row.classList.add("row-found");
  }

  // Fill the MS-Project "show outline level" picker from the actual depth of the loaded plan.
  function populateOutline() {
    const sel = document.getElementById("gridOutline");
    if (!sel) return;
    let max = 0;
    activities.forEach((a) => { if ((a.outline_level || 0) > max) max = a.outline_level || 0; });
    sel.innerHTML = "";
    sel.appendChild(el("option", { value: "0", text: "All levels" }));
    for (let i = 1; i <= max; i++) sel.appendChild(el("option", { value: String(i), text: "Level " + i }));
  }

  fetch("/api/analysis/" + enc)
    .then((r) => r.json())
    .then((data) => {
      activities = data.activities || [];
      statusDate = data.status_date || null;
      // the schedule's real calendars feed the Timescale dialog's Non-working-time tab
      if (window.SFTimescale) {
        const cals = [];
        if (data.calendar && data.calendar.name) cals.push(data.calendar);
        (data.calendars || []).forEach((c) => {
          if (!cals.some((x) => x.name === c.name)) cals.push(c);
        });
        SFTimescale.setCalendars(cals);
      }
      // every .mpp custom/extended field becomes an optional, toggleable column (default off)
      (data.custom_field_labels || []).forEach((lbl) => {
        if (!ALL_FIELDS.some((f) => f.key === lbl)) {
          ALL_FIELDS.push({ key: lbl, label: lbl, on: false, custom: true });
        }
      });
      renderCharts(data);
      renderToggles();
      populateOutline();
      renderGrid();
      // a session-wide target pre-fills the trace box — run the trace right away
      if (document.getElementById("targetUid").value) loadGantt();
    })
    .catch(() => { document.getElementById("charts").textContent = "Failed to load analysis."; });

  document.getElementById("ganttBtn").addEventListener("click", loadGantt);
  const showDone = document.getElementById("showDone");
  if (showDone) showDone.addEventListener("change", () => {
    renderGrid(); // the toggle scopes the WHOLE Activities grid + Gantt (operator 2026-07-10)…
    if (lastDriving) renderGantt(lastDriving); // …and still re-renders the trace
  });
  const showLinks = document.getElementById("showLinks");
  if (showLinks) showLinks.addEventListener("change", () => renderGrid());
  // persist header column moves (SFGantt grip) into the field model so re-renders keep the order
  document.addEventListener("sf-colmove", (ev) => {
    const grid = document.getElementById("grid");
    if (!grid || !grid.contains(ev.target)) return;
    const visible = ALL_FIELDS.filter((f) => f.on);
    const i = ev.detail.index, j = i + ev.detail.dir;
    if (i < 0 || i >= visible.length || j < 0 || j >= visible.length) return;
    ev.preventDefault(); // we re-render from the model instead of a raw DOM move
    const a = ALL_FIELDS.indexOf(visible[i]), b = ALL_FIELDS.indexOf(visible[j]);
    ALL_FIELDS[a] = visible[j]; ALL_FIELDS[b] = visible[i];
    renderGrid();
  });
  window.addEventListener("resize", () => {
    const tbl = document.querySelector("#grid table.gantt-grid");
    if (tbl) window.requestAnimationFrame(() => drawLinks(tbl));
  }, { passive: true });
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
  // the Timescale dialog's OK repaints both timelines with the new tiers/size/shading
  window.addEventListener("sf-timescale", () => {
    renderGrid();
    if (lastDriving) renderGantt(lastDriving);
  });
  // MS-Project Find: jump to a UniqueID; Outline level: collapse to a depth; Dates on bars toggle
  const gridFind = document.getElementById("gridFind");
  if (gridFind) {
    const go = () => findUid(parseInt(gridFind.value, 10));
    gridFind.addEventListener("change", go);
    gridFind.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); go(); } });
  }
  const gridOutline = document.getElementById("gridOutline");
  if (gridOutline) {
    gridOutline.addEventListener("change", () => {
      maxOutline = parseInt(gridOutline.value, 10) || 0;
      renderGrid();
    });
  }
  const gridBarDates = document.getElementById("gridBarDates");
  if (gridBarDates) {
    // "dates on bars" drives BOTH gantts: the activity grid AND the driving-path trace
    gridBarDates.addEventListener("change", () => {
      barDates = gridBarDates.checked;
      renderGrid();
      if (lastDriving) renderGantt(lastDriving);
    });
  }
})();
