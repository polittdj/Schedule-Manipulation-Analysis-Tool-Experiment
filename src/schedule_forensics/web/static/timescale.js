/* Schedule Forensics — the Microsoft-Project "Timescale" dialog (operator 2026-07-08).
 *
 * Operator: "Provide the user the option to select to modify the timescale and have this popup
 * show … make sure each of the options is reflected and works. For the units you can stop at
 * hours." This module owns the timescale CONFIGURATION (persisted per browser in localStorage)
 * and the popup itself; static/gantt.js consumes the config when it draws every tiered header,
 * gridline set and non-working-time shading. Dependency-free, air-gap-safe. window.SFTimescale.
 *
 * Faithful to the MS Project dialog: Top/Middle/Bottom tier tabs (Units, Label, Count, Align,
 * Use fiscal year, Tick lines), the shared Timescale options (Show one/two/three tiers, Size %,
 * Scale separator), and the Non-working time tab (Draw behind / in front / not at all, Color,
 * Pattern, Calendar) with a live preview strip. Units run Years → Hours (no Minutes, per the
 * operator). "Use fiscal year" numbers year-bearing labels by the fiscal year that ENDS in the
 * period (US-Government convention; the FY start month select defaults to October) and, for
 * Years / Half Years / Quarters, aligns the band boundaries to the fiscal grid.
 */
"use strict";

window.SFTimescale = (function () {
  var DAY_MS = 86400000;
  var STORE_KEY = "sf.timescale.v1";
  var MONTHS_S = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var MONTHS_L = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];
  var DOW_S = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var DOW_1 = ["S", "M", "T", "W", "T", "F", "S"];
  var MAX_BANDS = 4000; // per tier — beyond this the tier shows a "too fine" notice instead

  function el(tag, attrs) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === "text") node.textContent = attrs[k];
        else if (k === "class") node.className = attrs[k];
        else node.setAttribute(k, attrs[k]);
      });
    }
    return node;
  }

  // ---------------------------------------------------------------- configuration
  // Defaults reproduce the pre-dialog look exactly: three tiers of Years / Quarters / Months,
  // 100% size, separator on, weekends shaded softly behind the bars from the project calendar.
  function tierDefaults(units, label) {
    return { units: units, label: label, count: 1, align: "center", fiscal: false, ticks: true };
  }
  function defaults() {
    return {
      show: 3,          // 1 = Middle only, 2 = Middle + Bottom, 3 = Top + Middle + Bottom
      size: 100,        // % zoom applied to every page's pixels-per-day
      separator: true,  // horizontal rule between tier rows
      fyStartMonth: 9,  // 0-based month the fiscal year STARTS (9 = October, US Gov)
      top: tierDefaults("years", "y_full"),
      middle: tierDefaults("quarters", "q_longyear"),
      bottom: tierDefaults("months", "m_short"),
      nonworking: { draw: "behind", color: "", pattern: "solid", calendar: "" },
    };
  }
  var CFG = defaults();
  try {
    var raw = window.localStorage ? localStorage.getItem(STORE_KEY) : null;
    if (raw) {
      var saved = JSON.parse(raw);
      ["show", "size", "separator", "fyStartMonth"].forEach(function (k) {
        if (saved[k] != null) CFG[k] = saved[k];
      });
      ["top", "middle", "bottom"].forEach(function (t) {
        if (saved[t]) Object.keys(CFG[t]).forEach(function (k) {
          if (saved[t][k] != null) CFG[t][k] = saved[t][k];
        });
      });
      if (saved.nonworking) Object.keys(CFG.nonworking).forEach(function (k) {
        if (saved.nonworking[k] != null) CFG.nonworking[k] = saved.nonworking[k];
      });
    }
  } catch (e) { CFG = defaults(); }

  function save() {
    try { if (window.localStorage) localStorage.setItem(STORE_KEY, JSON.stringify(CFG)); }
    catch (e) { /* private mode — config just lives for the page */ }
  }

  // ---------------------------------------------------------------- calendars (non-working days)
  // Pages register the schedule's real calendars (name + working weekdays, Mon=0..Sun=6 python
  // convention + ISO holidays). The dropdown always offers the standard 5-day week as a fallback.
  var CALS = [];
  var STANDARD = { name: "Standard (Mon–Fri)", work_weekdays: [0, 1, 2, 3, 4], holidays: [] };
  function setCalendars(list) {
    CALS = (list || []).filter(function (c) { return c && c.name && c.work_weekdays; });
  }
  function calendarByName(name) {
    for (var i = 0; i < CALS.length; i++) if (CALS[i].name === name) return CALS[i];
    return CALS[0] || STANDARD;
  }
  // python date.weekday() (Mon=0..Sun=6) -> JS getUTCDay() (Sun=0..Sat=6) non-working set
  function jsOffDays(cal) {
    var working = {};
    (cal.work_weekdays || []).forEach(function (py) { working[(py + 1) % 7] = true; });
    var off = [];
    for (var d = 0; d < 7; d++) if (!working[d]) off.push(d);
    return off;
  }

  // ---------------------------------------------------------------- fiscal helpers
  function fiscalYear(d, fyStart) {
    // FY numbered by the calendar year it ENDS in: Oct 2023 (fyStart=9) belongs to FY2024.
    return d.getUTCFullYear() + (fyStart > 0 && d.getUTCMonth() >= fyStart ? 1 : 0);
  }
  function periodNum(d, phase, size) { // 1-based quarter/half number within the (fiscal) year
    return Math.floor(((d.getUTCMonth() - phase + 12) % 12) / size) + 1;
  }

  // ---------------------------------------------------------------- units
  // Every unit is a walker: snap(d, phaseMonths) aligns a date DOWN to a unit boundary and
  // advance(d, n) moves n units forward. Month-grid units honor the fiscal phase.
  function snapMonthGrid(d, phase, size) {
    var m = d.getUTCFullYear() * 12 + d.getUTCMonth();
    var k = Math.floor((m - phase) / size) * size + phase;
    d.setUTCFullYear(Math.floor(k / 12), ((k % 12) + 12) % 12, 1);
    d.setUTCHours(0, 0, 0, 0);
  }
  var UNITS = {
    years: {
      name: "Years", approxMs: 365 * DAY_MS, fiscalGrid: true,
      snap: function (d, ph) { snapMonthGrid(d, ph, 12); },
      advance: function (d, n) { d.setUTCMonth(d.getUTCMonth() + 12 * n); },
    },
    halfyears: {
      name: "Half Years", approxMs: 182 * DAY_MS, fiscalGrid: true,
      snap: function (d, ph) { snapMonthGrid(d, ph % 6, 6); },
      advance: function (d, n) { d.setUTCMonth(d.getUTCMonth() + 6 * n); },
    },
    quarters: {
      name: "Quarters", approxMs: 91 * DAY_MS, fiscalGrid: true,
      snap: function (d, ph) { snapMonthGrid(d, ph % 3, 3); },
      advance: function (d, n) { d.setUTCMonth(d.getUTCMonth() + 3 * n); },
    },
    months: {
      name: "Months", approxMs: 30 * DAY_MS,
      snap: function (d) { snapMonthGrid(d, 0, 1); },
      advance: function (d, n) { d.setUTCMonth(d.getUTCMonth() + n); },
    },
    thirds: {
      name: "Thirds of Months", approxMs: 10 * DAY_MS,
      snap: function (d) {
        var day = d.getUTCDate();
        d.setUTCDate(day >= 21 ? 21 : day >= 11 ? 11 : 1);
        d.setUTCHours(0, 0, 0, 0);
      },
      advance: function (d, n) {
        for (var i = 0; i < n; i++) {
          var day = d.getUTCDate();
          if (day < 11) d.setUTCDate(11);
          else if (day < 21) d.setUTCDate(21);
          else { d.setUTCMonth(d.getUTCMonth() + 1, 1); }
        }
      },
    },
    weeks: {
      name: "Weeks", approxMs: 7 * DAY_MS,
      snap: function (d) { // MS Project US default: weeks start Sunday
        d.setUTCDate(d.getUTCDate() - d.getUTCDay());
        d.setUTCHours(0, 0, 0, 0);
      },
      advance: function (d, n) { d.setUTCDate(d.getUTCDate() + 7 * n); },
    },
    days: {
      name: "Days", approxMs: DAY_MS,
      snap: function (d) { d.setUTCHours(0, 0, 0, 0); },
      advance: function (d, n) { d.setUTCDate(d.getUTCDate() + n); },
    },
    hours: {
      name: "Hours", approxMs: 3600000,
      snap: function (d) { d.setUTCMinutes(0, 0, 0); },
      advance: function (d, n) { d.setUTCHours(d.getUTCHours() + n); },
    },
  };
  var UNIT_ORDER = ["years", "halfyears", "quarters", "months", "thirds", "weeks", "days", "hours"];

  // ---------------------------------------------------------------- label formats
  // Per unit: [{id, name (dropdown text), fn(d, ctx) -> label, narrow?, minPx?}]. ctx carries
  // {fy: fiscal start month or -1 when the tier is calendar-based, phase: month-grid phase}.
  function yr(d, ctx) { return ctx.fy >= 0 ? fiscalYear(d, ctx.fy) : d.getUTCFullYear(); }
  function yy(n) { return ("0" + (n % 100)).slice(-2); }
  function weekOfYear(d) {
    var jan1 = Date.UTC(d.getUTCFullYear(), 0, 1);
    return Math.floor((d.getTime() - jan1) / DAY_MS / 7) + 1;
  }
  function hour12(h) { return (h % 12 === 0 ? 12 : h % 12) + (h < 12 ? " AM" : " PM"); }
  var LABELS = {
    years: [
      { id: "y_full", name: "2009, 2010, ... (FY-aware)",
        fn: function (d, c) { var y = yr(d, c); return (c.fy >= 0 ? "FY" : "") + y; },
        narrow: function (d, c) { return "'" + yy(yr(d, c)); }, minPx: 34 },
      { id: "y_abbr", name: "'09, '10, ...",
        fn: function (d, c) { return "'" + yy(yr(d, c)); } },
    ],
    halfyears: [
      { id: "h_num", name: "H1, H2, ...",
        fn: function (d, c) { return "H" + periodNum(d, c.phase, 6); } },
      { id: "h_word", name: "1st Half, 2nd Half, ...",
        fn: function (d, c) { return periodNum(d, c.phase, 6) === 1 ? "1st Half" : "2nd Half"; },
        narrow: function (d, c) { return "H" + periodNum(d, c.phase, 6); }, minPx: 52 },
      { id: "h_numyy", name: "H1 '09, ...",
        fn: function (d, c) { return "H" + periodNum(d, c.phase, 6) + " '" + yy(yr(d, c)); },
        narrow: function (d, c) { return "H" + periodNum(d, c.phase, 6); }, minPx: 44 },
    ],
    quarters: [
      { id: "q_longyear", name: "Qtr 1 2009, ... (FY-aware)",
        fn: function (d, c) {
          return "Qtr " + periodNum(d, c.phase, 3) + " " + (c.fy >= 0 ? "FY" : "") + yr(d, c);
        },
        narrow: function (d, c) { return "Q" + periodNum(d, c.phase, 3); }, minPx: 64 },
      { id: "q_long", name: "Qtr 1, Qtr 2, ...",
        fn: function (d, c) { return "Qtr " + periodNum(d, c.phase, 3); },
        narrow: function (d, c) { return "Q" + periodNum(d, c.phase, 3); }, minPx: 34 },
      { id: "q_short", name: "Q1, Q2, ...",
        fn: function (d, c) { return "Q" + periodNum(d, c.phase, 3); } },
      { id: "q_num", name: "1, 2, ...",
        fn: function (d, c) { return String(periodNum(d, c.phase, 3)); } },
    ],
    months: [
      { id: "m_full", name: "January, February, ...",
        fn: function (d) { return MONTHS_L[d.getUTCMonth()]; },
        narrow: function (d) { return MONTHS_S[d.getUTCMonth()]; }, minPx: 58 },
      { id: "m_short", name: "Jan, Feb, ...",
        fn: function (d) { return MONTHS_S[d.getUTCMonth()]; },
        narrow: function (d) { return MONTHS_S[d.getUTCMonth()][0]; }, minPx: 22 },
      { id: "m_shortyy", name: "Jan '09, ...",
        fn: function (d) { return MONTHS_S[d.getUTCMonth()] + " '" + yy(d.getUTCFullYear()); },
        narrow: function (d) { return MONTHS_S[d.getUTCMonth()]; }, minPx: 42 },
      { id: "m_letter", name: "J, F, M, ...",
        fn: function (d) { return MONTHS_S[d.getUTCMonth()][0]; } },
      { id: "m_num", name: "1, 2, ... 12",
        fn: function (d) { return String(d.getUTCMonth() + 1); } },
    ],
    thirds: [
      { id: "t_bme", name: "B, M, E (beginning / middle / end)",
        fn: function (d) { var day = d.getUTCDate(); return day >= 21 ? "E" : day >= 11 ? "M" : "B"; } },
      { id: "t_day", name: "1, 11, 21",
        fn: function (d) { return String(d.getUTCDate()); } },
    ],
    weeks: [
      { id: "w_mmmd", name: "Jan 27, Feb 3, ...",
        fn: function (d) { return MONTHS_S[d.getUTCMonth()] + " " + d.getUTCDate(); },
        narrow: function (d) { return String(d.getUTCDate()); }, minPx: 38 },
      { id: "w_mdy", name: "01/27/09, ...",
        fn: function (d) {
          return ("0" + (d.getUTCMonth() + 1)).slice(-2) + "/" + ("0" + d.getUTCDate()).slice(-2) +
            "/" + yy(d.getUTCFullYear());
        },
        narrow: function (d) { return String(d.getUTCDate()); }, minPx: 54 },
      { id: "w_num", name: "W1, W2, ... (week of year)",
        fn: function (d) { return "W" + weekOfYear(d); } },
      { id: "w_day", name: "27, 3, ... (start day)",
        fn: function (d) { return String(d.getUTCDate()); } },
    ],
    days: [
      { id: "d_dowmmmd", name: "Mon Jan 27, ...",
        fn: function (d) { return DOW_S[d.getUTCDay()] + " " + MONTHS_S[d.getUTCMonth()] + " " + d.getUTCDate(); },
        narrow: function (d) { return String(d.getUTCDate()); }, minPx: 68 },
      { id: "d_mmmd", name: "Jan 27, ...",
        fn: function (d) { return MONTHS_S[d.getUTCMonth()] + " " + d.getUTCDate(); },
        narrow: function (d) { return String(d.getUTCDate()); }, minPx: 38 },
      { id: "d_dow", name: "Mon, Tue, ...",
        fn: function (d) { return DOW_S[d.getUTCDay()]; },
        narrow: function (d) { return DOW_1[d.getUTCDay()]; }, minPx: 26 },
      { id: "d_letter", name: "M, T, W, ...",
        fn: function (d) { return DOW_1[d.getUTCDay()]; } },
      { id: "d_num", name: "1, 2, ... 31",
        fn: function (d) { return String(d.getUTCDate()); } },
    ],
    hours: [
      { id: "hr_ampm", name: "8 AM, 9 AM, ...",
        fn: function (d) { return hour12(d.getUTCHours()); },
        narrow: function (d) { return String(d.getUTCHours()); }, minPx: 34 },
      { id: "hr_24", name: "08, 09, ... 23",
        fn: function (d) { return ("0" + d.getUTCHours()).slice(-2); } },
      { id: "hr_colon", name: "8:00, 9:00, ...",
        fn: function (d) { return d.getUTCHours() + ":00"; },
        narrow: function (d) { return String(d.getUTCHours()); }, minPx: 30 },
    ],
  };
  function labelDef(units, id) {
    var defs = LABELS[units] || [];
    for (var i = 0; i < defs.length; i++) if (defs[i].id === id) return defs[i];
    return defs[0];
  }

  // ---------------------------------------------------------------- band generation
  // The bands of one tier across an axis: [{left, width, label, align, warn?}]. A tier whose
  // unit is too fine for the span (> MAX_BANDS bands) yields a single explanatory band instead
  // (MS Project raises "the timescale range is too long for the units" — same idea, softer).
  function tierBands(axis, tier, fyStartMonth) {
    var unit = UNITS[tier.units] || UNITS.months;
    var count = Math.max(1, Math.min(999, Math.floor(tier.count) || 1));
    var expected = (axis.t1 - axis.t0) / (unit.approxMs * count);
    if (expected > MAX_BANDS) {
      return [{ left: 0, width: axis.width, align: "center", warn: true,
        label: unit.name + " are too fine for this date range — raise Count, pick a larger unit, or zoom in" }];
    }
    var fiscal = !!tier.fiscal && unit.fiscalGrid;
    var phase = fiscal ? fyStartMonth : 0;
    var def = labelDef(tier.units, tier.label);
    var ctx = { fy: fiscal ? fyStartMonth : -1, phase: phase };
    var out = [];
    var cur = new Date(axis.t0);
    unit.snap(cur, phase);
    var guard = 0;
    while (cur.getTime() <= axis.t1 && guard++ < MAX_BANDS + 2) {
      var next = new Date(cur);
      unit.advance(next, count);
      var left = axis.x(cur.getTime());
      var right = axis.x(next.getTime());
      if (right > 0 && left < axis.width) {
        var w = Math.max(1, right - left);
        var label = def.fn(cur, ctx);
        if (def.narrow && def.minPx && w < def.minPx) label = def.narrow(cur, ctx);
        if (w < 9) label = "";
        out.push({ left: Math.max(0, left), width: w, label: label, align: tier.align || "center" });
      }
      cur.setTime(next.getTime());
    }
    return out;
  }

  // Which configured tiers are visible, top -> bottom (MS Project "Show" semantics).
  function visibleTiers() {
    if (CFG.show === 1) return [CFG.middle];
    if (CFG.show === 2) return [CFG.middle, CFG.bottom];
    return [CFG.top, CFG.middle, CFG.bottom];
  }

  // The full tier stack for gantt.js: [{bands, ticks}] + the separator flag.
  function tiers(axis) {
    return {
      separator: !!CFG.separator,
      rows: visibleTiers().map(function (t) {
        return { bands: tierBands(axis, t, CFG.fyStartMonth), ticks: !!t.ticks };
      }),
    };
  }

  // Gridline boundaries for gantt.js: light lines on the BOTTOM visible tier's band starts,
  // heavier on the middle tier's, heaviest on the top tier's (matching the header).
  function gridBoundaries(axis) {
    var vis = visibleTiers();
    var classes = vis.length === 1 ? ["g-grid g-grid-yr"]
      : vis.length === 2 ? ["g-grid g-grid-yr", "g-grid"]
        : ["g-grid g-grid-yr", "g-grid g-grid-qtr", "g-grid"];
    var seen = {};
    var lines = [];
    for (var i = vis.length - 1; i >= 0; i--) { // bottom first so coarser tiers override class
      tierBands(axis, vis[i], CFG.fyStartMonth).forEach(function (b) {
        if (b.warn) return;
        var key = Math.round(b.left);
        if (key < 0 || key > axis.width) return;
        seen[key] = classes[i];
      });
    }
    Object.keys(seen).forEach(function (k) {
      lines.push({ left: Number(k), cls: seen[k] });
    });
    lines.sort(function (a, b) { return a.left - b.left; });
    return lines;
  }

  // ---------------------------------------------------------------- non-working time shading
  // One weekly repeating-linear-gradient per track (cheap: zero extra DOM in "behind" mode),
  // phase-aligned to the axis so Saturday is Saturday at any scroll position, plus one absolute
  // div per calendar holiday. Skipped below ~1.25 px/day where a day is sub-pixel (matching MS
  // Project, which stops showing non-working shading when days are too small to see).
  function nonworkStyle(axis) {
    var nw = CFG.nonworking;
    if (nw.draw === "none") return null;
    var ppd = axis.x(axis.t0 + DAY_MS) - axis.x(axis.t0);
    if (!(ppd >= 1.25)) return null;
    var cal = calendarByName(nw.calendar);
    var off = jsOffDays(cal);
    if (!off.length && !(cal.holidays || []).length) return null;
    var color = nw.color || "var(--nonwork, rgba(120,126,148,.16))";
    var stops = [];
    for (var d = 0; d < 7; d++) {
      var a = d * ppd, b = (d + 1) * ppd;
      if (off.indexOf(d) < 0) { stops.push("transparent " + a + "px " + b + "px"); continue; }
      if (nw.pattern === "striped") {
        for (var p = a; p < b; p += 7) {
          var pe = Math.min(p + 4, b);
          stops.push(color + " " + p + "px " + pe + "px");
          if (pe < b) stops.push("transparent " + pe + "px " + Math.min(p + 7, b) + "px");
        }
      } else if (nw.pattern === "outlined") {
        stops.push(color + " " + a + "px " + (a + 1.5) + "px");
        stops.push("transparent " + (a + 1.5) + "px " + (b - 1.5) + "px");
        stops.push(color + " " + (b - 1.5) + "px " + b + "px");
      } else {
        stops.push(color + " " + a + "px " + b + "px");
      }
    }
    // phase: start the 7-day pattern on the Sunday at/before the axis origin
    var t0d = new Date(axis.t0);
    var sunday = axis.t0 - t0d.getUTCDay() * DAY_MS;
    var image = off.length ? "repeating-linear-gradient(90deg," + stops.join(",") + ")" : "none";
    // holidays inside the axis span (capped — a pathological calendar can't flood the DOM)
    var holis = [];
    (cal.holidays || []).some(function (iso) {
      var t = Date.parse(iso + "T00:00:00Z");
      if (isNaN(t) || t < axis.t0 - DAY_MS || t > axis.t1) return false;
      holis.push({ left: axis.x(t), width: Math.max(1, ppd) });
      return holis.length >= 800;
    });
    return { image: image, posX: axis.x(sunday), color: color, holidays: holis, front: nw.draw === "front" };
  }

  // Paint the shading onto one timeline track (called by every page as it builds each row).
  // "Behind" sets the track's own background (bars are positioned children — always on top);
  // "In front" appends a pointer-transparent overlay above the bars.
  function decorateTrack(track, axis) {
    var s = nonworkStyle(axis);
    if (!s) return;
    var host = track;
    if (s.front) {
      host = el("div", { class: "g-nonwork-front" });
      track.appendChild(host);
    }
    if (s.image !== "none") {
      host.style.backgroundImage = s.image;
      host.style.backgroundPosition = s.posX + "px 0";
    }
    s.holidays.forEach(function (h) {
      var d = el("div", { class: "g-nonwork-holiday" });
      d.style.left = h.left + "px";
      d.style.width = h.width + "px";
      d.style.background = s.color;
      if (s.front) host.appendChild(d);
      else host.insertBefore(d, host.firstChild);
    });
  }

  // ---------------------------------------------------------------- the dialog
  var lastAxis = null; // hint from the page's latest real axis — drives the preview span
  function axisHint(axis) { lastAxis = { t0: axis.t0, t1: axis.t1 }; }

  var TIER_TABS = [
    { key: "top", title: "Top Tier" },
    { key: "middle", title: "Middle Tier" },
    { key: "bottom", title: "Bottom Tier" },
  ];
  var overlay = null, work = null, activeTab = "middle";

  function previewAxis(width) {
    var t0 = lastAxis ? lastAxis.t0 : Date.UTC(2018, 0, 1);
    var t1 = lastAxis ? lastAxis.t1 : Date.UTC(2026, 6, 1);
    if (t1 <= t0) t1 = t0 + 365 * DAY_MS;
    return { t0: t0, t1: t1, width: width,
      x: function (ms) { return Math.round(((ms - t0) / (t1 - t0)) * width); } };
  }

  function renderPreview(box) {
    box.textContent = "";
    var width = Math.max(320, box.clientWidth - 2 || 520);
    var axis = previewAxis(width);
    var real = CFG; CFG = work; // tiers()/nonworkStyle read the module config — swap in the draft
    try {
      var scale = window.SFGantt.buildTierScale(axis, "g-scale", null);
      scale.classList.add("ts-preview-scale");
      box.appendChild(scale);
      var track = el("div", { class: "g-track ts-preview-track" });
      track.style.width = width + "px";
      decorateTrack(track, axis);
      box.appendChild(track);
    } finally { CFG = real; }
  }

  function field(labelText, input, title) {
    var wrap = el("label", { class: "ts-field", title: title || "" });
    wrap.appendChild(el("span", { class: "ts-field-name", text: labelText }));
    wrap.appendChild(input);
    return wrap;
  }
  function select(options, value, onChange) {
    var s = el("select");
    options.forEach(function (o) {
      var opt = el("option", { value: o.value, text: o.text });
      if (String(o.value) === String(value)) opt.selected = true;
      s.appendChild(opt);
    });
    s.addEventListener("change", function () { onChange(s.value); });
    return s;
  }
  function numberInput(value, min, max, onChange) {
    var i = el("input", { type: "number", min: String(min), max: String(max), value: String(value) });
    i.addEventListener("input", function () {
      var v = Math.max(min, Math.min(max, Number(i.value) || min));
      onChange(v);
    });
    return i;
  }
  function checkbox(checked, onChange) {
    var i = el("input", { type: "checkbox" });
    i.checked = !!checked;
    i.addEventListener("change", function () { onChange(i.checked); });
    return i;
  }

  function tierEnabled(key) {
    if (work.show === 3) return true;
    if (work.show === 2) return key !== "top";
    return key === "middle";
  }

  function buildTierPane(pane, key, refresh) {
    var t = work[key];
    var enabled = tierEnabled(key);
    var box = el("div", { class: "ts-group" + (enabled ? "" : " ts-disabled") });
    box.appendChild(el("h4", { text: TIER_TABS.filter(function (x) { return x.key === key; })[0].title + " formatting" }));
    if (!enabled) {
      box.appendChild(el("p", { class: "muted",
        text: "This tier is hidden by the current “Show” setting below — switch it to include this tier." }));
    }
    var row1 = el("div", { class: "ts-row" });
    row1.appendChild(field("Units:", select(
      UNIT_ORDER.map(function (u) { return { value: u, text: UNITS[u].name }; }),
      t.units,
      function (v) { t.units = v; t.label = LABELS[v][0].id; refresh(); }
    ), "Years down to Hours (no minutes)"));
    row1.appendChild(field("Label:", select(
      (LABELS[t.units] || []).map(function (d) { return { value: d.id, text: d.name }; }),
      t.label,
      function (v) { t.label = v; refresh(); }
    ), "How each period is written"));
    box.appendChild(row1);
    var row2 = el("div", { class: "ts-row" });
    row2.appendChild(field("Count:", numberInput(t.count, 1, 999, function (v) { t.count = v; refresh(); }),
      "Label every N units (e.g. Count 2 with Weeks = one band per fortnight)"));
    row2.appendChild(field("Align:", select(
      [{ value: "left", text: "Left" }, { value: "center", text: "Center" }, { value: "right", text: "Right" }],
      t.align, function (v) { t.align = v; refresh(); }
    )));
    box.appendChild(row2);
    var row3 = el("div", { class: "ts-row" });
    var fiscalCb = checkbox(t.fiscal, function (v) { t.fiscal = v; refresh(); });
    var fiscalWrap = el("label", { class: "ts-check",
      title: "Number Years / Half Years / Quarters by the fiscal year (set its start month below)" });
    fiscalWrap.appendChild(fiscalCb);
    fiscalWrap.appendChild(el("span", { text: " Use fiscal year" }));
    if (!UNITS[t.units].fiscalGrid) fiscalWrap.classList.add("ts-disabled");
    row3.appendChild(fiscalWrap);
    var ticksWrap = el("label", { class: "ts-check", title: "Vertical tick line at each band boundary" });
    ticksWrap.appendChild(checkbox(t.ticks, function (v) { t.ticks = v; refresh(); }));
    ticksWrap.appendChild(el("span", { text: " Tick lines" }));
    row3.appendChild(ticksWrap);
    box.appendChild(row3);
    pane.appendChild(box);

    // Timescale options (shared, shown on every tier tab — exactly like MS Project)
    var opts = el("div", { class: "ts-group" });
    opts.appendChild(el("h4", { text: "Timescale options" }));
    var orow = el("div", { class: "ts-row" });
    orow.appendChild(field("Show:", select(
      [
        { value: 1, text: "One tier (Middle)" },
        { value: 2, text: "Two tiers (Middle, Bottom)" },
        { value: 3, text: "Three tiers (Top, Middle, Bottom)" },
      ],
      work.show, function (v) { work.show = Number(v); refresh(); }
    )));
    orow.appendChild(field("Size:", numberInput(work.size, 25, 1000, function (v) { work.size = v; refresh(); }),
      "% zoom applied to the timeline (100 = the page's own Scale/Zoom setting)"));
    orow.appendChild(el("span", { class: "ts-unit", text: "%" }));
    opts.appendChild(orow);
    var orow2 = el("div", { class: "ts-row" });
    var sepWrap = el("label", { class: "ts-check", title: "Horizontal rule between the tier rows" });
    sepWrap.appendChild(checkbox(work.separator, function (v) { work.separator = v; refresh(); }));
    sepWrap.appendChild(el("span", { text: " Scale separator" }));
    orow2.appendChild(sepWrap);
    orow2.appendChild(field("Fiscal year starts:", select(
      MONTHS_L.map(function (m, i) { return { value: i, text: m }; }),
      work.fyStartMonth, function (v) { work.fyStartMonth = Number(v); refresh(); }
    ), "Month the fiscal year begins (October = US Government FY)"));
    opts.appendChild(orow2);
    pane.appendChild(opts);
  }

  function buildNonworkPane(pane, refresh) {
    var nw = work.nonworking;
    var box = el("div", { class: "ts-group" });
    box.appendChild(el("h4", { text: "Formatting options" }));
    var draw = el("div", { class: "ts-row ts-draw" });
    [["behind", "Behind task bars"], ["front", "In front of task bars"], ["none", "Do not draw"]]
      .forEach(function (pair) {
        var lab = el("label", { class: "ts-check" });
        var r = el("input", { type: "radio", name: "tsDraw", value: pair[0] });
        r.checked = nw.draw === pair[0];
        r.addEventListener("change", function () { if (r.checked) { nw.draw = pair[0]; refresh(); } });
        lab.appendChild(r);
        lab.appendChild(el("span", { text: " " + pair[1] }));
        draw.appendChild(lab);
      });
    box.appendChild(draw);
    var row = el("div", { class: "ts-row" });
    var color = el("input", { type: "color",
      value: /^#/.test(nw.color) ? nw.color.slice(0, 7) : "#7d8494" });
    color.addEventListener("input", function () { nw.color = color.value + "44"; refresh(); });
    // color inputs only speak #rrggbb; the stored value adds a soft alpha so bars stay readable
    row.appendChild(field("Color:", color, "Shading color (drawn translucent so bars stay readable)"));
    row.appendChild(field("Pattern:", select(
      [
        { value: "solid", text: "Solid" },
        { value: "striped", text: "Striped" },
        { value: "outlined", text: "Outlined (edges only)" },
      ],
      nw.pattern, function (v) { nw.pattern = v; refresh(); }
    )));
    box.appendChild(row);
    var row2 = el("div", { class: "ts-row" });
    var names = [];
    CALS.forEach(function (c) { if (names.indexOf(c.name) < 0) names.push(c.name); });
    if (!names.length) names.push(STANDARD.name);
    row2.appendChild(field("Calendar:", select(
      names.map(function (n) { return { value: n, text: n }; }),
      nw.calendar || names[0], function (v) { nw.calendar = v; refresh(); }
    ), "Which calendar's non-working days (weekends + holidays) to shade"));
    box.appendChild(row2);
    box.appendChild(el("p", { class: "muted ts-note",
      text: "Shading appears when the zoom is wide enough for a day to be visible (≥ ~1.25 px/day); holidays from the selected calendar are shaded individually." }));
    pane.appendChild(box);
  }

  function close() {
    if (overlay) { overlay.remove(); overlay = null; }
  }

  function open() {
    close();
    work = JSON.parse(JSON.stringify(CFG)); // edit a draft; OK commits, Cancel discards
    overlay = el("div", { class: "ts-overlay" });
    var dlg = el("div", { class: "ts-dialog", role: "dialog", "aria-modal": "true",
      "aria-label": "Timescale" });
    var head = el("div", { class: "ts-head" });
    head.appendChild(el("b", { text: "Timescale" }));
    var closeBtn = el("button", { class: "ts-x", type: "button", "aria-label": "Close", text: "×" });
    closeBtn.addEventListener("click", close);
    head.appendChild(closeBtn);
    dlg.appendChild(head);

    var tabs = el("div", { class: "ts-tabs", role: "tablist" });
    var pane = el("div", { class: "ts-pane" });
    var preview = el("div", { class: "ts-preview-box" });
    var previewWrap = el("div", { class: "ts-group" });
    previewWrap.appendChild(el("h4", { text: "Preview" }));
    previewWrap.appendChild(preview);

    function paint() {
      pane.textContent = "";
      if (activeTab === "nonwork") buildNonworkPane(pane, paint);
      else buildTierPane(pane, activeTab, paint);
      Array.prototype.forEach.call(tabs.children, function (b) {
        b.classList.toggle("ts-tab-on", b.dataset.tab === activeTab);
      });
      renderPreview(preview);
    }
    TIER_TABS.concat([{ key: "nonwork", title: "Non-working time" }]).forEach(function (t) {
      var b = el("button", { class: "ts-tab", type: "button", text: t.title, role: "tab" });
      b.dataset.tab = t.key;
      b.addEventListener("click", function () { activeTab = t.key; paint(); });
      tabs.appendChild(b);
    });
    dlg.appendChild(tabs);
    dlg.appendChild(pane);
    dlg.appendChild(previewWrap);

    var foot = el("div", { class: "ts-foot" });
    var reset = el("button", { type: "button", text: "Reset to default" });
    reset.addEventListener("click", function () { work = defaults(); paint(); });
    var ok = el("button", { type: "button", class: "ts-ok", text: "OK" });
    ok.addEventListener("click", function () {
      CFG = work;
      save();
      close();
      window.dispatchEvent(new CustomEvent("sf-timescale"));
    });
    var cancel = el("button", { type: "button", text: "Cancel" });
    cancel.addEventListener("click", close);
    foot.appendChild(reset);
    foot.appendChild(el("span", { class: "ts-spacer" }));
    foot.appendChild(ok);
    foot.appendChild(cancel);
    dlg.appendChild(foot);

    overlay.appendChild(dlg);
    overlay.addEventListener("click", function (ev) { if (ev.target === overlay) close(); });
    document.addEventListener("keydown", function esc(ev) {
      if (ev.key === "Escape") { close(); document.removeEventListener("keydown", esc); }
    });
    document.body.appendChild(overlay);
    paint();
  }

  // every page's "Timescale…" toolbar button opens the dialog — one binding covers all pages
  function wireButton() {
    var btn = document.getElementById("timescaleBtn");
    if (btn) btn.addEventListener("click", open);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wireButton);
  else wireButton();

  return {
    config: function () { return CFG; },
    sizeFactor: function () { return (Number(CFG.size) || 100) / 100; },
    tiers: tiers,
    gridBoundaries: gridBoundaries,
    decorateTrack: decorateTrack,
    nonworkStyle: nonworkStyle,
    setCalendars: setCalendars,
    axisHint: axisHint,
    open: open,
    close: close,
  };
})();
