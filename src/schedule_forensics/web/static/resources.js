/* Schedule Forensics — resource-loading histogram (ADR-0125, buckets + drill #74).
 *
 * Reads the server-computed loading payload embedded in #resData and draws the selected resource's
 * work-vs-capacity histogram at the chosen bucket (day / week / month): a bar per bucket (working
 * days of booked work), a capacity tick per bucket, and over-allocated buckets (load > capacity)
 * drawn red. Clicking a bar opens the over-allocation drill (#resDrill) listing the activities
 * driving that bucket's load. The drill has a Columns dropdown (operator 2026-07-10): any
 * standard or custom field can be ADDED to the table, the choice persists in localStorage and
 * applies to every subsequent bar click, and the exact selection + columns export to Excel
 * (/export/xlsx/resource-drill). Field data comes from the same-origin /api/analysis; the
 * bucket's own work figures stay from the embedded payload. Dependency-free SVG, air-gap safe.
 */
"use strict";

(function () {
  var dataEl = document.getElementById("resData");
  var pick = document.getElementById("resPick");
  var host = document.getElementById("resChart");
  var status = document.getElementById("resStatus");
  var drill = document.getElementById("resDrill");
  if (!dataEl || !pick || !host) return;

  var SVGNS = "http://www.w3.org/2000/svg";
  var payload;
  try {
    payload = JSON.parse(dataEl.textContent);
  } catch (e) {
    return;
  }
  var GRAN = payload.granularity || "month";
  var UNIT = GRAN === "day" ? "day" : GRAN === "week" ? "week" : "month";
  var byId = {};
  (payload.resources || []).forEach(function (r) { byId[String(r.id)] = r; });

  // ---- drill columns: standard fields + the file's custom fields, persisted set-once ----
  var COLS_KEY = "sf-res-drill-cols";
  var EXTRA_STANDARD = [
    { key: "duration_days", label: "Duration (d)" },
    { key: "percent_complete", label: "% complete" },
    { key: "start", label: "Start" },
    { key: "finish", label: "Finish" },
    { key: "total_float_days", label: "Total float (d)" },
    { key: "free_float_days", label: "Free float (d)" },
    { key: "is_critical", label: "Critical" },
    { key: "wbs", label: "WBS" },
    { key: "baseline_start", label: "Baseline start" },
    { key: "baseline_finish", label: "Baseline finish" },
  ];
  var byUid = null;      // uid -> activity row (from /api/analysis, fetched once)
  var customLabels = []; // custom-field labels available on this file
  var extraOn = (function () {
    try { return new Set(JSON.parse(localStorage.getItem(COLS_KEY) || "[]")); }
    catch (e) { return new Set(); }
  })();
  function saveCols() {
    try { localStorage.setItem(COLS_KEY, JSON.stringify(Array.from(extraOn))); } catch (e) { /* ok */ }
  }
  function fetchFields(cb) {
    if (byUid) { cb(); return; }
    fetch("/api/analysis/" + encodeURIComponent(payload.source_file || ""))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        byUid = {};
        (d.activities || []).forEach(function (a) { byUid[a.unique_id] = a; });
        var seen = new Set();
        (d.activities || []).forEach(function (a) {
          Object.keys(a.custom || {}).forEach(function (k) { seen.add(k); });
        });
        customLabels = Array.from(seen).sort();
        cb();
      })
      .catch(function () { byUid = {}; cb(); });
  }
  function extraCols() {
    var std = EXTRA_STANDARD.filter(function (f) { return extraOn.has(f.label); });
    var cus = customLabels.filter(function (k) { return extraOn.has(k); })
      .map(function (k) { return { key: k, label: k, custom: true }; });
    return std.concat(cus);
  }
  function cellValue(a, col) {
    if (!a) return "";
    var v = col.custom ? (a.custom || {})[col.key] : a[col.key];
    if (v === null || v === undefined) return "";
    if (v === true) return "yes";
    if (v === false) return "no";
    var mdy = window.SFGantt && SFGantt.fmtMDY ? SFGantt.fmtMDY(String(v)) : "";
    return mdy || String(v);
  }

  function showDrill(res, p) {
    if (!drill) return;
    fetchFields(function () { renderDrill(res, p); });
  }
  function renderDrill(res, p) {
    drill.innerHTML = "";
    var tasks = p.tasks || [];
    var head = document.createElement("h3");
    head.textContent = res.name + " — " + p.period + ": " + p.load + " d booked / " +
      p.cap + " d capacity" + (p.over ? " (OVER-ALLOCATED)" : "");
    drill.appendChild(head);
    var src = document.createElement("p");
    src.className = "muted";
    src.setAttribute("data-no-i18n", "");
    src.textContent = "Source file: " + (payload.source_file || "loaded schedule");
    drill.appendChild(src);
    if (!tasks.length) {
      drill.appendChild(document.createElement("p")).textContent =
        "No per-activity work recorded for this " + UNIT + ".";
      return;
    }
    // controls: Columns picker (persists across bar clicks + sessions) + Excel export
    var bar = document.createElement("div");
    bar.className = "viz-controls";
    if (window.SFChecklist) {
      var labels = EXTRA_STANDARD.map(function (f) { return f.label; }).concat(customLabels);
      bar.appendChild(SFChecklist.filter({
        values: labels,
        selected: new Set(labels.filter(function (l) { return extraOn.has(l); })),
        label: "Columns",
        title: "Add fields to the drill table (kept for every bar you click)",
        onChange: function (sel) {
          extraOn = sel ? new Set(Array.from(sel)) : new Set();
          saveCols();
          renderDrill(res, p);
        },
      }));
    }
    var cols = extraCols();
    var href = "/export/xlsx/resource-drill?resource=" + encodeURIComponent(res.id) +
      "&period=" + encodeURIComponent(p.period) + "&bucket=" + encodeURIComponent(GRAN) +
      (cols.length ? "&cols=" + encodeURIComponent(cols.map(function (c) { return c.key; }).join(",")) : "");
    var a = document.createElement("a");
    a.className = "btn-link";
    a.href = href;
    a.textContent = "⬇ Excel (this selection)";
    bar.appendChild(a);
    drill.appendChild(bar);

    var scroller = document.createElement("div");
    scroller.className = "hist-drill-scroll";
    var table = document.createElement("table");
    table.className = "hist-drill-table";
    var headHtml = "<thead><tr><th>UID</th><th>Activity</th><th>Work (days) this " + UNIT + "</th>";
    cols.forEach(function (c) { headHtml += "<th></th>"; });
    headHtml += "</tr></thead>";
    table.innerHTML = headHtml;
    // fill the extra header labels via textContent (never trust labels as HTML)
    var ths = table.querySelectorAll("th");
    cols.forEach(function (c, i) { ths[3 + i].textContent = c.label; });
    var tb = document.createElement("tbody");
    tasks.forEach(function (t) {
      var tr = document.createElement("tr");
      [t.uid, t.name, t.days].forEach(function (v) {
        var td = document.createElement("td");
        td.textContent = v;
        tr.appendChild(td);
      });
      var act = byUid ? byUid[t.uid] : null;
      cols.forEach(function (c) {
        var td = document.createElement("td");
        td.textContent = cellValue(act, c);
        tr.appendChild(td);
      });
      tb.appendChild(tr);
    });
    table.appendChild(tb);
    scroller.appendChild(table);
    drill.appendChild(scroller);
    drill.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function svg(tag, attrs) {
    var n = document.createElementNS(SVGNS, tag);
    for (var k in attrs || {}) n.setAttribute(k, attrs[k]);
    return n;
  }
  function txt(node, s) { node.textContent = s; return node; }
  function titled(node, s) {
    var t = svg("title");
    t.textContent = s;
    node.appendChild(t);
    return node;
  }

  function draw(res) {
    host.innerHTML = "";
    if (!res || !res.series || !res.series.length) {
      host.appendChild(document.createElement("p")).textContent = "No work recorded for this resource.";
      return;
    }
    var series = res.series;
    var W = 960, H = 300, ml = 38, mr = 12, mt = 14, mb = 54;
    var maxV = 0;
    series.forEach(function (p) { maxV = Math.max(maxV, p.load, p.cap); });
    if (maxV <= 0) maxV = 1;
    var s = svg("svg", { class: "res-svg", viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    var plotW = W - ml - mr, plotH = H - mt - mb;
    var x = function (i) { return ml + (plotW * (i + 0.5)) / series.length; };
    var bw = Math.max(2, (plotW / series.length) * 0.7);
    var y = function (v) { return mt + plotH * (1 - v / maxV); };

    // y gridlines + labels (working days)
    [0, 0.25, 0.5, 0.75, 1].forEach(function (f) {
      var gy = mt + plotH * (1 - f);
      s.appendChild(svg("line", { x1: ml, y1: gy, x2: W - mr, y2: gy, class: "res-grid" }));
      s.appendChild(txt(svg("text", { x: ml - 4, y: gy + 3, class: "res-yl" }), Math.round(maxV * f)));
    });
    s.appendChild(svg("line", { x1: ml, y1: H - mb, x2: W - mr, y2: H - mb, class: "res-ax" }));

    series.forEach(function (p, i) {
      var cx = x(i);
      // load bar
      var h = plotH * (p.load / maxV);
      var bar = svg("rect", {
        x: cx - bw / 2, y: y(p.load), width: bw, height: Math.max(0, h),
        class: p.over ? "res-bar res-bar-over" : "res-bar",
        "data-i": i, style: "cursor:pointer",
      });
      titled(bar, p.period + ": " + p.load + " d booked / " + p.cap + " d capacity" +
        (p.over ? " — OVER-ALLOCATED" : "") + " — click to drill");
      bar.addEventListener("click", function () { showDrill(res, p); });
      s.appendChild(bar);
      // capacity tick across the bar slot
      if (p.cap > 0) {
        s.appendChild(svg("line", {
          x1: cx - bw / 2 - 1, y1: y(p.cap), x2: cx + bw / 2 + 1, y2: y(p.cap), class: "res-cap",
        }));
      }
      // x labels: thin out when crowded (day/week granularity produces many buckets)
      var step = Math.max(1, Math.ceil(series.length / 16));
      if (i % step === 0) {
        var lab = txt(svg("text", { x: cx, y: H - mb + 14, class: "res-xl", transform: "rotate(40 " + cx + " " + (H - mb + 14) + ")" }), p.period);
        s.appendChild(lab);
      }
    });
    // capacity legend
    s.appendChild(txt(svg("text", { x: ml, y: H - 6, class: "res-xl" }),
      "bars = work booked (days); dash = per-" + UNIT + " capacity; red = over-allocated; click a bar to drill"));
    // Axis captions via the ONE shared helper (ADR-0298). The bucket width is chosen at runtime
    // (UNIT = day / week / month), so the X caption names the bucket actually rendered rather than
    // assuming one. The Y axis is work booked in WORKING DAYS — the gridline labels and every
    // tooltip say "d booked", so any other unit here would contradict the chart it labels.
    SFChartFrame.axisTitles(s, { L: ml, R: W - mr, T: mt, B: H - mb }, {
      xLabel: "Period (" + UNIT + " commencing)",
      yLabel: "Work booked (working days)",
    });
    // data-date marker via the ONE shared helper (ADR-0342). This is the spec's own
    // "distribution over months -> columns with DD marker" case: unlike a version axis, the
    // buckets here are EQUAL-length calendar periods, so the marker has a real position.
    // The bucket KEY is computed server-side by the engine's own bucket_key (ISO week
    // numbering is not worth a second implementation in the browser); we place the line on the
    // RIGHT edge of the data-date bucket — elapsed to the left, remaining to the right — which
    // is cei.js's long-standing placement. A data date outside the loaded work's span finds no
    // bucket and draws NOTHING, rather than clamping to an edge it does not occupy.
    if (payload.status_period) {
      var ddi = -1;
      series.forEach(function (p, i) { if (p.period === payload.status_period) ddi = i; });
      if (ddi >= 0) {
        SFGantt.dataDateLine(s, {
          x: ml + (plotW * (ddi + 1)) / series.length, top: mt, bottom: H - mb,
          iso: payload.status_date,
        });
      }
    }
    host.appendChild(s);
    // ADR-0319 — ADR-0303's "data label yields", MEASURED: the X caption owns its corner, and
    // the last 40°-rotated period labels were parked under it (36-40x2-4px in 8 of 12
    // theme x scale combos). The yield runs AFTER the append (live boxes need layout) against
    // the caption's REAL box, so apollo's wider mono glyphs are covered without guessing text
    // metrics; the caption itself never moves (the placement is frozen, standing req. 5).
    var xcap = null;
    s.querySelectorAll("text.ch-at").forEach(function (t) {
      if (t.getAttribute("text-anchor") === "end") xcap = t;
    });
    var capBox = xcap ? xcap.getBoundingClientRect() : null;
    if (capBox && capBox.width) { // unmeasurable (hidden) boxes must not shred the labels
      s.querySelectorAll("text.res-xl[transform]").forEach(function (t) {
        var b = t.getBoundingClientRect();
        var dx = Math.min(capBox.right, b.right) - Math.max(capBox.left, b.left);
        var dy = Math.min(capBox.bottom, b.bottom) - Math.max(capBox.top, b.top);
        if (dx > -2 && dy > -2) t.remove(); // yields with a 2px margin — the label, never the caption
      });
    }

    if (status) {
      status.textContent = res.total_days + " work-days total" +
        (res.over && res.over.length
          ? " · over-allocated in " + res.over.length + " " + UNIT + "(s)"
          : "");
    }
    if (window.SFChartFrame && window.SFChartFrame.scan) window.SFChartFrame.scan();
  }

  // ── Utilization by resource (operator 2026-08-20): EVERY resource on one chart ──────────
  // Peak booked load as a share of each resource's OWN capacity (its max units) in its busiest
  // bucket, worst first. Booked work against zero capacity is the most extreme over-allocation
  // there is and reads "over (no capacity)" — never divided, never hidden.
  function drawUtil() {
    var box = document.getElementById("resUtilChart");
    if (!box) return;
    box.innerHTML = "";
    var rows = (payload.resources || []).map(function (r) {
      var pct = 0, overNoCap = false;
      (r.series || []).forEach(function (p) {
        if (p.cap > 0) pct = Math.max(pct, (100 * p.load) / p.cap);
        else if (p.load > 0) overNoCap = true;
      });
      return { name: r.name, max_units: r.max_units, pct: pct, overNoCap: overNoCap,
        idle: !(r.series || []).length };
    });
    rows.sort(function (a, b) {
      if (a.overNoCap !== b.overNoCap) return a.overNoCap ? -1 : 1;
      if (b.pct !== a.pct) return b.pct - a.pct;
      return a.name < b.name ? -1 : 1;
    });
    var maxPct = 0;
    rows.forEach(function (r) { maxPct = Math.max(maxPct, r.pct); });
    var scaleMax = Math.max(120, Math.min(300, Math.ceil(maxPct / 10) * 10));
    var capLeft = (100 / scaleMax) * 100;
    rows.forEach(function (r) {
      var row = document.createElement("div");
      row.className = "util-row";
      var name = document.createElement("span");
      name.className = "util-name";
      name.textContent = r.name;
      name.title = r.name + " — max units " + (r.max_units == null ? "(assumed 1)" : r.max_units);
      var track = document.createElement("div");
      track.className = "util-track";
      var cap = document.createElement("div");
      cap.className = "util-cap";
      cap.style.left = capLeft + "%";
      cap.title = "100% of this resource's capacity";
      track.appendChild(cap);
      var fillPct = r.overNoCap ? 100 : Math.min(r.pct, scaleMax) / scaleMax * 100;
      if (fillPct > 0) {
        var fill = document.createElement("div");
        fill.className = "util-fill" + ((r.pct > 100 || r.overNoCap) ? " util-over" : "");
        fill.style.width = fillPct + "%";
        track.appendChild(fill);
      }
      var val = document.createElement("span");
      val.className = "util-val" + ((r.pct > 100 || r.overNoCap) ? " res-over" : "");
      val.textContent = r.overNoCap ? "over (no capacity)"
        : r.idle ? "no booked work"
          : Math.round(r.pct) + "% of capacity";
      row.appendChild(name);
      row.appendChild(track);
      row.appendChild(val);
      box.appendChild(row);
    });
  }

  function selected() { return byId[pick.value] || (payload.resources || [])[0]; }
  pick.addEventListener("change", function () {
    if (drill) drill.innerHTML = "";
    draw(selected());
  });
  draw(selected());
  drawUtil();
})();
