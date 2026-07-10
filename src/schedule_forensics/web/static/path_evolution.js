/* Schedule Forensics — Critical-Path Evolution Gantt stepper (M18 item 7 + follow-up).
 *
 * Dependency-free SVG (no CDN — air-gap posture). A Prev/Next/Auto-play stepper over
 * /api/evolution: each frame draws one version's critical path as a Gantt on a LOCKED date
 * axis (held fixed across every version so the path visibly extends as the finish slips).
 * Activities that ENTERED the path are green, those that STAYED grey, and a ▲ marks a
 * duration change; activities that LEFT the path are drawn below as dashed/struck ghost bars
 * at their prior position. Every entered/left activity carries a reason chip explaining WHY
 * it moved (new task / duration change / logic change / constraint / slip / completed) — hover
 * for the detail.
 *
 * Each row also carries grid columns beside the bar — % complete, duration (working days),
 * start and finish — with the activity name wrapped small (no longer truncated). A
 * "hide completed" toggle drops finished activities, using the robust complete flag
 * (≥100% OR an actual finish — ADR-0051), so a real .mpp/.xer reporting 99.x% still hides.
 *
 * Zoom/pan controls scope the locked date axis (the window stays inside the full axis so bars
 * remain comparable across frames). A ?target=<uid> focus (data-target on #evoChart, echoed by
 * /api/evolution) highlights that activity's row in every frame and notes whether it is on the
 * current version's critical path.
 *
 * A "filter the path" selector switches between four scopes: the driving path to the focused
 * UID (its predecessors, from the server's path_to_target), one chosen version's critical path
 * tracked across every frame, an entered/left/stayed movement filter, and a name/UID search.
 */
"use strict";

(function () {
  var box = document.getElementById("evoChart");
  if (!box) return;
  var NS = "http://www.w3.org/2000/svg";
  var DAY = 86400000;

  // reason code -> { short label, theme color }
  var REASON = {
    new: { label: "new task", color: "var(--ok)" },
    duration_up: { label: "duration ↑", color: "var(--warn)" },
    duration_down: { label: "duration ↓", color: "var(--warn)" },
    constraint: { label: "constraint", color: "var(--warn)" },
    logic_added: { label: "logic added", color: "var(--accent)" },
    logic_removed: { label: "logic removed", color: "var(--bad)" },
    slack_consumed: { label: "slip elsewhere", color: "var(--muted)" },
    completed: { label: "completed", color: "var(--ok)" },
    removed: { label: "removed", color: "var(--bad)" },
    gained_float: { label: "gained float", color: "var(--muted)" },
  };

  // lo/hi are the VISIBLE date window (zoom/pan move them inside the full [fullLo, fullHi]).
  var data = null, index = 0, timer = null, lo = 0, hi = 1, fullLo = 0, fullHi = 1;
  var hideDone = false, focusUid = null;
  // filter-by-path: switchable modes — none | driving | version | movement | search
  var filterMode = "none", filterVersion = 0, searchText = "";
  var moveSet = { entered: true, stayed: true, left: true };

  function svgEl(tag, attrs) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if ((k === "fill" || k === "stroke") && String(attrs[k]).indexOf("var(") === 0) {
        n.style[k] = attrs[k];
      } else n.setAttribute(k, attrs[k]);
    }
    return n;
  }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function clip(s, n) { s = String(s || ""); return s.length > n ? s.slice(0, n - 1) + "…" : s; }

  // wrap a name into <=maxLines lines of <=perLine chars (word-aware; last line ellipsized)
  function wrapName(name, perLine, maxLines) {
    var words = String(name || "").split(/\s+/), lines = [], cur = "";
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      if (!cur) cur = w;
      else if ((cur + " " + w).length <= perLine) cur += " " + w;
      else { lines.push(cur); cur = w; if (lines.length === maxLines - 1) break; }
    }
    if (cur && lines.length < maxLines) lines.push(cur);
    // any words left after the line budget → ellipsize the final line
    if (lines.length === maxLines) {
      var consumed = lines.join(" ").length;
      if (consumed < String(name || "").length) lines[maxLines - 1] = clip(lines[maxLines - 1] + " …", perLine);
    }
    return lines.length ? lines : [""];
  }
  // dates read MM/DD/YYYY like every other Gantt (shared SFGantt.fmtMDY; data stays ISO)
  function fmtDate(iso) {
    if (!iso) return "—";
    var s = String(iso);
    return (window.SFGantt && SFGantt.fmtMDY(s)) || s;
  }

  function callout(snap) {
    var c = el("div", "ev-callout");
    var move = snap.finish_delta_days;
    var moveText = move == null ? "" :
      move > 0 ? " (slipped " + move + "d)" :
      move < 0 ? " (pulled in " + (-move) + "d)" : " (no move)";
    c.appendChild(el("span", "ev-finish", "Project finish: " + snap.project_finish + moveText));
    var sig = el("span", "ev-signals");
    var bits = [
      snap.entered.length + " entered",
      snap.left.length + " left",
      snap.duration_changed.length + " duration-changed on path",
    ];
    if (snap.shortened_on_path.length) bits.push(snap.shortened_on_path.length + " shortened on path");
    if (snap.removed_logic_count) bits.push(snap.removed_logic_count + " logic links removed");
    sig.textContent = bits.join(" · ");
    if ((snap.shortened_on_path.length || snap.removed_logic_count || snap.left.length) &&
        move != null && move <= 0) {
      sig.classList.add("ev-flag");
    }
    c.appendChild(sig);
    return c;
  }

  function legend() {
    var wrap = el("div", "legend");
    if (data && data.tier === "all") {
      // colour-by-tier legend (driving-slack tiers to the focus)
      [["driving", "var(--bad)", "critical / driving (0d)"],
        ["secondary", "var(--warn)", "secondary (≤ secondary days)"],
        ["tertiary", "var(--accent)", "tertiary"]].forEach(function (p) {
        var s = el("span", "", "■ " + p[2]);
        s.style.color = p[1];
        s.style.marginRight = "10px";
        wrap.appendChild(s);
      });
      return wrap;
    }
    [["ev-entered", "entered the path"], ["ev-stayed", "stayed"], ["ev-left", "left the path"]]
      .forEach(function (p) { wrap.appendChild(el("span", p[0], p[1])); });
    wrap.appendChild(el("span", "ev-stayed", "▲ duration change · hover a reason for detail"));
    return wrap;
  }

  // column layout: a left grid (name + %/dur/start/finish), then the Gantt plot, then the chip
  var COL = { name: 6, pct: 300, dur: 348, start: 360, finish: 432, plotL: 512 };

  function barDatesOn() {
    var cb = document.getElementById("evoBarDates");
    return !!(cb && cb.checked);
  }

  // rows: [{uid, name, start, finish, kind, durBadge, reason, detail, percent_complete, duration, complete}]
  // srcLabel = the schedule file these rows were read from (Task Information provenance);
  // "left the path" ghost rows are drawn at their PRIOR-version position, so their caller
  // passes the prior version's label.
  function gantt(rows, srcLabel) {
    var wrap = el("div", "evo-gantt");
    if (!rows.length) { wrap.appendChild(el("p", "muted", "—")); return wrap; }
    var W = 1180, rowH = 30, padT = 46, padB = 8, plotL = COL.plotL, plotR = W - 130;
    var H = padT + rows.length * rowH + padB;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img" });
    if (window.SFA11y) SFA11y.label(svg, "Critical-path evolution — the critical path per version");
    var x = function (ms) { return plotL + ((ms - lo) / (hi - lo)) * (plotR - plotL); };

    function colText(xx, yy, s, opts) {
      opts = opts || {};
      var t = svgEl("text", { x: xx, y: yy, "font-size": opts.size || 10, fill: opts.fill || "var(--ink)" });
      if (opts.anchor) t.setAttribute("text-anchor", opts.anchor);
      t.textContent = s;
      svg.appendChild(t);
      return t;
    }

    // header row: column titles + the locked axis gridlines/years
    colText(COL.name, padT - 26, "Activity", { fill: "var(--muted)" });
    colText(COL.pct, padT - 26, "%", { fill: "var(--muted)", anchor: "end" });
    colText(COL.dur, padT - 26, "Dur", { fill: "var(--muted)", anchor: "end" });
    colText(COL.start, padT - 26, "Start", { fill: "var(--muted)" });
    colText(COL.finish, padT - 26, "Finish", { fill: "var(--muted)" });
    // MS-Project-style stacked time axis: month (faint) / quarter (medium) / year (heavy)
    // gridlines down the plot, with year and quarter labels in the header. Month and quarter
    // lines are gated by zoom so a wide frame doesn't turn to mush.
    var gridTop = padT - 6, gridBot = H - padB;
    var monthPx = x(lo + 30 * DAY) - x(lo); // approx pixels per month at this zoom
    function gline(ms, op) {
      var tx = x(ms);
      if (tx >= plotL && tx <= plotR) {
        svg.appendChild(svgEl("line", { x1: tx, y1: gridTop, x2: tx, y2: gridBot,
          stroke: "var(--line)", "stroke-width": 1, opacity: op }));
      }
    }
    function bandLabel(s, e, yy, text, size, minW) {
      var l = Math.max(plotL, x(s)), r = Math.min(plotR, x(e));
      if (r - l < minW) return;
      var t = svgEl("text", { x: (l + r) / 2, y: yy, "text-anchor": "middle", "font-size": size, fill: "var(--muted)" });
      t.textContent = text;
      svg.appendChild(t);
    }
    function eachPeriod(startOf, advance, fn) {
      var dd = new Date(lo); startOf(dd); var guard = 0;
      while (dd.getTime() <= hi && guard++ < 4000) {
        var nd = new Date(dd); advance(nd); fn(dd.getTime(), nd.getTime(), dd); dd = nd;
      }
    }
    if (monthPx >= 9) {
      eachPeriod(function (dd) { dd.setUTCDate(1); dd.setUTCHours(0, 0, 0, 0); },
        function (dd) { dd.setUTCMonth(dd.getUTCMonth() + 1); },
        function (s) { gline(s, 0.16); });
    }
    eachPeriod(function (dd) { dd.setUTCMonth(Math.floor(dd.getUTCMonth() / 3) * 3, 1); dd.setUTCHours(0, 0, 0, 0); },
      function (dd) { dd.setUTCMonth(dd.getUTCMonth() + 3); },
      function (s, e, dd) { gline(s, 0.4); bandLabel(s, e, padT - 16, "Q" + (Math.floor(dd.getUTCMonth() / 3) + 1), 9, 22); });
    eachPeriod(function (dd) { dd.setUTCMonth(0, 1); dd.setUTCHours(0, 0, 0, 0); },
      function (dd) { dd.setUTCFullYear(dd.getUTCFullYear() + 1); },
      function (s, e, dd) { gline(s, 0.8); bandLabel(s, e, padT - 30, String(dd.getUTCFullYear()), 11, 26); });
    svg.appendChild(svgEl("line", { x1: COL.name, y1: padT - 8, x2: W, y2: padT - 8, stroke: "var(--line)", "stroke-width": 1 }));

    rows.forEach(function (r, i) {
      var top = padT + i * rowH, cy = top + rowH / 2;
      // highlight the focused activity's row across every frame
      if (focusUid != null && r.uid === focusUid) {
        svg.appendChild(svgEl("rect", {
          x: COL.name - 2, y: top + 1, width: W - COL.name, height: rowH - 2,
          rx: 3, fill: "var(--accent)", opacity: 0.14,
        }));
      }
      var labelColor = tierColor(r) || (r.kind === "entered" ? "var(--ok)" : r.kind === "left" ? "var(--bad)" : "var(--ink)");

      // name wrapped to <=2 small lines, prefixed with the UID; struck through if it left
      var lines = wrapName(r.name, 38, 2);
      var nameTop = cy - (lines.length - 1) * 5 - 2;
      var lab = svgEl("text", { x: COL.name, y: nameTop, "font-size": 10, fill: labelColor });
      if (r.kind === "left") lab.setAttribute("text-decoration", "line-through");
      lines.forEach(function (ln, li) {
        var ts = svgEl("tspan", { x: COL.name, dy: li === 0 ? 0 : 11 });
        ts.textContent = (li === 0 ? "U" + r.uid + " · " : "") + ln;
        lab.appendChild(ts);
      });
      // MS-Project Task Information on click (shared dialog — ADR-0186), sourced from the
      // file these rows were read from so the figures match the frame on screen
      if (srcLabel && window.SFTaskInfo) {
        lab.style.cursor = "pointer";
        lab.addEventListener("click", function () { SFTaskInfo.openFrom(srcLabel, r.uid); });
      }
      svg.appendChild(lab);

      // grid columns: % complete, duration, start, finish
      if (r.percent_complete != null) colText(COL.pct, cy + 3, r.percent_complete + "%", { anchor: "end", fill: "var(--muted)" });
      if (r.duration) colText(COL.dur, cy + 3, r.duration, { anchor: "end", fill: "var(--muted)" });
      colText(COL.start, cy + 3, fmtDate(r.start), { size: 9, fill: "var(--muted)" });
      colText(COL.finish, cy + 3, fmtDate(r.finish), { size: 9, fill: "var(--muted)" });

      if (r.start && r.finish) {
        var x1 = x(Date.parse(r.start)), x2 = x(Date.parse(r.finish));
        var bw = Math.max(2, x2 - x1);
        var barColor = tierColor(r) || (r.kind === "entered" ? "var(--ok)" : r.kind === "left" ? "var(--bad)" : "var(--accent)");
        var rect = svgEl("rect", { x: x1, y: cy - 6, width: bw, height: 12, rx: 2, fill: barColor });
        // hover call-out (chartframe tooltip + native SVG title) — same as the top tiles' charts
        var bt = svgEl("title", {});
        bt.textContent =
          "U" + r.uid + " · " + r.name + " — " + (r.kind || "on path") +
          ", " + fmtDate(r.start) + " → " + fmtDate(r.finish) +
          (r.percent_complete != null ? ", " + r.percent_complete + "%" : "") +
          (r.reason && REASON[r.reason] ? " (" + REASON[r.reason].label + ")" : "");
        rect.appendChild(bt);
        if (r.kind === "left") { rect.setAttribute("opacity", "0.45"); rect.setAttribute("stroke-dasharray", "3 2"); }
        if (srcLabel && window.SFTaskInfo) {
          rect.style.cursor = "pointer";
          rect.addEventListener("click", function () { SFTaskInfo.openFrom(srcLabel, r.uid); });
        }
        svg.appendChild(rect);
        if (r.durBadge) colText(x2 + 3, cy + 4, "▲", { size: 11, fill: "var(--warn)" });
        // MS-Project "dates on bars" (parity with the Activities Gantt — ADR-0186): start
        // left of the bar, finish right of it, clamped into the plot area
        if (barDatesOn()) {
          var sTxt = fmtDate(r.start), fTxt = fmtDate(r.finish);
          if (x1 - 4 > plotL + 40) colText(x1 - 4, cy + 3, sTxt, { size: 8, anchor: "end", fill: "var(--muted)" });
          if (x2 + 4 < plotR - 40) colText(x2 + 4, cy + 3, fTxt, { size: 8, fill: "var(--muted)" });
        }
      }

      if (r.reason && REASON[r.reason]) {
        var rc = REASON[r.reason];
        var t = colText(plotR + 8, cy + 4, rc.label, { fill: rc.color });
        if (r.detail) { var ti = svgEl("title", {}); ti.textContent = r.detail; t.appendChild(ti); }
      }
    });
    wrap.appendChild(svg);
    // underlying-data table (revealed by the tile's "Data" toggle / read by assistive tech) — the
    // critical path in THIS version, so the bottom Evolution tile matches the top tiles' "Data" view
    if (window.SFA11y) {
      wrap.appendChild(
        SFA11y.table(
          "Critical path this version",
          ["UID", "Name", "Status", "Start", "Finish", "%"],
          rows.map(function (r) {
            return [
              "U" + r.uid,
              r.name,
              r.kind || "on path",
              fmtDate(r.start),
              fmtDate(r.finish),
              r.percent_complete != null ? r.percent_complete + "%" : "",
            ];
          })
        )
      );
    }
    return wrap;
  }

  function carry(r, extra) {
    var o = {
      uid: r.uid, name: r.name, start: r.start, finish: r.finish,
      percent_complete: r.percent_complete, duration: r.duration, complete: r.complete,
      tier: r.tier,
    };
    for (var k in extra) o[k] = extra[k];
    return o;
  }
  // driving-slack tier colours (only used in the "all tiers" evolution mode)
  var TIER_COLOR = { driving: "var(--bad)", secondary: "var(--warn)", tertiary: "var(--accent)" };
  function tierColor(r) {
    return (data && data.tier === "all" && r.tier) ? TIER_COLOR[r.tier] : null;
  }
  function currentRows(snap) {
    return snap.critical_rows.map(function (r) {
      return carry(r, {
        kind: r.entered ? "entered" : "stayed",
        durBadge: r.duration_changed, reason: r.entered ? r.reason : null, detail: r.detail,
      });
    });
  }
  function leftRows(snap) {
    return snap.left_rows.map(function (r) {
      return carry(r, { kind: "left", durBadge: false, reason: r.reason, detail: r.detail });
    });
  }
  function visible(rows) { return hideDone ? rows.filter(function (r) { return !r.complete; }) : rows; }

  function setOf(arr) { var o = {}; (arr || []).forEach(function (u) { o[u] = true; }); return o; }

  // filter-by-path: scope the rows by the active mode (applied to both the critical rows and
  // the "left the path" ghost rows)
  function applyFilter(rows, snap) {
    if (filterMode === "movement") return rows.filter(function (r) { return moveSet[r.kind]; });
    if (filterMode === "search") {
      var q = searchText.trim().toLowerCase();
      if (!q) return rows;
      return rows.filter(function (r) {
        return String(r.uid).indexOf(q) >= 0 || String(r.name || "").toLowerCase().indexOf(q) >= 0;
      });
    }
    if (filterMode === "driving") {
      var dset = setOf(snap.path_to_target);
      return rows.filter(function (r) { return dset[r.uid]; });
    }
    if (filterMode === "version") {
      var vsnap = data.snapshots[filterVersion];
      var cset = setOf(vsnap ? vsnap.critical : []);
      return rows.filter(function (r) { return cset[r.uid]; });
    }
    return rows;  // "none"
  }

  function filterNote(snap) {
    if (filterMode === "driving") {
      return focusUid == null ? "Set a Focus UID above to use the driving-path filter."
        : "Showing the chain that drives UID " + focusUid + " (its predecessors on the path).";
    }
    if (filterMode === "version") {
      var v = data.snapshots[filterVersion];
      return v ? "Showing version “" + v.label + "”'s critical path tracked across every frame." : "";
    }
    return "";
  }

  function render() {
    var snap = data.snapshots[index];
    document.getElementById("evoLabel").textContent =
      (index + 1) + " / " + data.snapshots.length + " — " + snap.label +
      (snap.status_date ? " (data date " + snap.status_date + ")" : "");
    box.innerHTML = "";
    box.appendChild(callout(snap));
    box.appendChild(legend());
    if (focusUid != null) {
      var onPath = snap.critical_rows.some(function (r) { return r.uid === focusUid; });
      box.appendChild(el("p", onPath ? "ev-focus-on" : "muted",
        onPath ? "Focus UID " + focusUid + " is on this version's critical path (highlighted)."
               : "Focus UID " + focusUid + " is not on this version's critical path."));
    }
    var noteEl = document.getElementById("evoFilterNote");
    if (noteEl) noteEl.textContent = filterNote(snap);

    var crit = applyFilter(visible(currentRows(snap)), snap);
    var total = snap.critical_rows.length;
    box.appendChild(el("h3", null, "Critical path — " + crit.length +
      (crit.length !== total ? " of " + total : "") + " activities"));
    box.appendChild(gantt(crit, snap.label));
    var leftV = applyFilter(visible(leftRows(snap)), snap);
    if (leftV.length) {
      box.appendChild(el("h3", null, "Left the critical path (" + leftV.length + ") — where they were, and why"));
      // ghost rows are drawn at their PRIOR-version position — cite that version's file
      var priorLabel = index > 0 ? data.snapshots[index - 1].label : snap.label;
      box.appendChild(gantt(leftV, priorLabel));
    }
  }

  function step(delta) {
    index = (index + delta + data.snapshots.length) % data.snapshots.length;
    render();
  }

  // zoom/pan keep the visible window inside the locked full axis so bars stay comparable
  function clampView() {
    if (hi - lo >= fullHi - fullLo) { lo = fullLo; hi = fullHi; return; }
    if (lo < fullLo) { hi += fullLo - lo; lo = fullLo; }
    if (hi > fullHi) { lo -= hi - fullHi; hi = fullHi; }
  }
  function zoom(factor) {
    var c = (lo + hi) / 2, span = (hi - lo) * factor;
    if (span < 7 * DAY) span = 7 * DAY;  // floor: never zoom past a week-wide window
    lo = c - span / 2; hi = c + span / 2; clampView(); render();
  }
  function pan(frac) {
    // When fully zoomed out the window already spans the whole axis, so a plain pan is clamped
    // straight back (the arrows looked dead). Make the first click responsive: jump to the half of
    // the axis the arrow points at; subsequent clicks then slide the window by `frac`.
    if (hi - lo >= fullHi - fullLo) {
      var span = (fullHi - fullLo) / 2;
      if (frac < 0) { lo = fullLo; hi = fullLo + span; }  // ◀ earlier half
      else { lo = fullHi - span; hi = fullHi; }           // ▶ later half
      clampView(); render(); return;
    }
    var d = (hi - lo) * frac; lo += d; hi += d; clampView(); render();
  }
  function resetZoom() { lo = fullLo; hi = fullHi; render(); }
  function stopAuto() {
    if (timer) { clearInterval(timer); timer = null; }
    document.getElementById("evoPlay").textContent = "▶ Auto-play";
  }
  function toggleAuto() {
    if (timer) { stopAuto(); return; }
    // A2: honor prefers-reduced-motion — advance one frame, don't auto-flip on a timer
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      step(1); return;
    }
    document.getElementById("evoPlay").textContent = "⏸ Stop";
    timer = setInterval(function () { step(1); }, 1800);
  }

  var tgt = box.getAttribute("data-target");
  var tierMode = box.getAttribute("data-tier") || "off";
  fetch("/api/evolution?tier=" + encodeURIComponent(tierMode) +
        (tgt ? "&target=" + encodeURIComponent(tgt) : ""))
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      data = d;
      focusUid = (d.target == null) ? null : Number(d.target);
      if (d.axis && d.axis.min && d.axis.max) {
        lo = Date.parse(d.axis.min); hi = Date.parse(d.axis.max);
        if (!(hi > lo)) hi = lo + 30 * DAY;
        var pad = (hi - lo) * 0.04;
        lo -= pad; hi += pad;
      }
      fullLo = lo; fullHi = hi;  // the locked full axis; zoom/pan move lo/hi within it
      render();
      function on(id, fn) { var n = document.getElementById(id); if (n) n.addEventListener("click", fn); }
      on("prevEvo", function () { stopAuto(); step(-1); });
      on("nextEvo", function () { stopAuto(); step(1); });
      on("evoPlay", toggleAuto);
      on("evoZoomIn", function () { zoom(0.6); });
      on("evoZoomOut", function () { zoom(1 / 0.6); });
      on("evoPanL", function () { pan(-0.25); });
      on("evoPanR", function () { pan(0.25); });
      on("evoZoomReset", resetZoom);
      var hd = document.getElementById("evoHideDone");
      if (hd) hd.addEventListener("change", function () { hideDone = hd.checked; render(); });
      // MS-Project "dates on bars" (parity with the Activities Gantt — ADR-0186)
      var bd = document.getElementById("evoBarDates");
      if (bd) bd.addEventListener("change", render);

      // filter-by-path controls: a mode selector that toggles its sub-control
      var verSel = document.getElementById("evoFilterVersion");
      if (verSel) {
        d.snapshots.forEach(function (s, i) {
          var o = document.createElement("option");
          o.value = i; o.textContent = s.label;
          verSel.appendChild(o);
        });
        verSel.addEventListener("change", function () { filterVersion = Number(verSel.value); render(); });
      }
      var modeSel = document.getElementById("evoFilterMode");
      var moveBox = document.getElementById("evoFilterMovement");
      var textBox = document.getElementById("evoFilterText");
      function showSub() {
        if (verSel) verSel.style.display = filterMode === "version" ? "" : "none";
        if (moveBox) moveBox.style.display = filterMode === "movement" ? "" : "none";
        if (textBox) textBox.style.display = filterMode === "search" ? "" : "none";
      }
      if (modeSel) modeSel.addEventListener("change", function () {
        filterMode = modeSel.value; showSub(); render();
      });
      Array.prototype.forEach.call(document.querySelectorAll(".evoMove"), function (cb) {
        cb.addEventListener("change", function () { moveSet[cb.value] = cb.checked; render(); });
      });
      if (textBox) textBox.addEventListener("input", function () { searchText = textBox.value; render(); });
    })
    .catch(function () { box.textContent = "Failed to load the path-evolution data."; });
})();
