/* Schedule Forensics — shared MS-Project-style Task Information dialog (ADR-0186).
 *
 * Extracted from app.js (ADR-0183) so EVERY Gantt on the site — the Activities grid, the
 * Path workspace, the Driving-Path corridor, the SRA grid, and the Critical-Path Evolution
 * chart — opens the SAME tabbed popup MS Project shows: General, Predecessors, Successors,
 * Resources, Advanced, Notes, Custom Fields, with the provenance footer (source file + UID).
 * Every value is the file's own data; nothing is derived client-side. Dependency-free,
 * same-origin only (air-gap posture). window.SFTaskInfo.
 *
 * Two entry points:
 *   open(act)              — `act` is a full /api/analysis activity row (the pages whose rows
 *                            already carry the payload, e.g. the SRA grid, pass it directly).
 *   openFrom(file, uid)    — fetch-and-cache /api/analysis/<file> (key OR display label — the
 *                            server resolves both) and open the row with that UniqueID.
 */
"use strict";

window.SFTaskInfo = (function () {
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "class") node.className = attrs[k];
      else if (k === "text") node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    }
    (children || []).forEach(function (c) { node.appendChild(c); });
    return node;
  }

  function fmt(v) {
    if (v === true) return "yes";
    if (v === false) return "no";
    if (v == null) return "";
    var s = String(v);
    return (window.SFGantt && SFGantt.fmtMDY(s)) || s;
  }

  // An ISO-8601 duration (PT184H0M0S) as working days at 8h/day — the raw form MS Project
  // stores in custom fields is meaningless to an operator ("PT184H0M0S" -> "23 wd (184h)").
  function humanizeDuration(v) {
    var m = /^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/.exec(String(v));
    if (!m) return null;
    var hours = (Number(m[1]) || 0) + (Number(m[2]) || 0) / 60 + (Number(m[3]) || 0) / 3600;
    var wd = hours / 8;
    return (Math.round(wd * 10) / 10) + " wd (" + (Math.round(hours * 10) / 10) + "h)";
  }

  // One drill value, made readable: dates MM/DD/YYYY (time stripped), ISO durations in working
  // days, booleans yes/no; null/blank means "don't show the row at all".
  function drillValue(v) {
    if (v === null || v === undefined) return null;
    if (typeof v === "boolean") return v ? "yes" : "no";
    var s = String(v).trim();
    if (!s) return null;
    var mdy = (window.SFGantt && SFGantt.fmtMDY(s)) || "";
    if (mdy) return mdy;
    var dur = humanizeDuration(s);
    if (dur) return dur;
    return fmt(v);
  }

  function close() {
    var ov = document.querySelector(".ti-overlay");
    if (ov) ov.parentNode.removeChild(ov);
    document.removeEventListener("keydown", onEsc);
  }
  function onEsc(ev) { if (ev.key === "Escape") close(); }

  function tiDL(pairs) {
    var dl = el("dl");
    pairs.forEach(function (pr) {
      var v = pr[1];
      if (v === null || v === undefined || v === "") return;
      dl.appendChild(el("dt", { text: pr[0] }));
      dl.appendChild(el("dd", { text: String(v) }));
    });
    return dl;
  }
  function tiTable(headers, rows, emptyText) {
    if (!rows.length) return el("p", { class: "muted", text: emptyText });
    var tbl = el("table", { class: "ti-table" });
    var tr0 = el("tr");
    headers.forEach(function (h) { tr0.appendChild(el("th", { text: h })); });
    tbl.appendChild(tr0);
    rows.forEach(function (r) {
      var tr = el("tr");
      r.forEach(function (c) { tr.appendChild(el("td", { text: c === null || c === undefined ? "" : String(c) })); });
      tbl.appendChild(tr);
    });
    return tbl;
  }

  function open(act) {
    if (!act) return;
    close();
    var overlay = el("div", { class: "ti-overlay" });
    overlay.addEventListener("click", function (ev) { if (ev.target === overlay) close(); });
    var dlg = el("div", { class: "ti-dialog", role: "dialog" });
    var kind = act.is_summary ? "Summary" : act.is_milestone ? "Milestone" : "Task";
    var head = el("div", { class: "ti-head" });
    head.appendChild(el("h3", { text: "Task Information — " + kind + " " + act.unique_id + ": " + act.name }));
    var closeBtn = el("button", { class: "ti-close", type: "button", text: "✕" });
    closeBtn.addEventListener("click", close);
    head.appendChild(closeBtn);
    dlg.appendChild(head);

    var dur = function (v) { return v === null || v === undefined ? null : v + " d"; };
    var money = function (v) { return v === null || v === undefined ? null : "$" + Number(v).toLocaleString(); };
    var tabs = [];
    tabs.push(["General", function () {
      var box = el("div");
      box.appendChild(tiDL([
        ["Name", act.name], ["Unique ID", act.unique_id], ["WBS", act.wbs || null],
        ["Outline level", act.outline_level],
        ["Percent complete", (act.percent_complete || 0) + "%"],
        ["Physical % complete", act.physical_percent_complete === null || act.physical_percent_complete === undefined ? null : act.physical_percent_complete + "%"],
        ["Duration", dur(act.duration_days) + (act.is_estimated_duration ? " (estimated)" : "") + (act.duration_is_elapsed ? " (elapsed)" : "")],
        ["Remaining duration", dur(act.remaining_duration_days)],
        ["Baseline duration", dur(act.baseline_duration_days)],
        ["Schedule mode", act.is_manual ? "Manually Scheduled" : "Auto Scheduled"],
        ["Active", act.is_active === false ? "no (INACTIVE)" : "yes"],
        ["Start", fmt(act.start)], ["Finish", fmt(act.finish)],
        ["Actual start", fmt(act.actual_start)], ["Actual finish", fmt(act.actual_finish)],
        ["Baseline start", fmt(act.baseline_start)], ["Baseline finish", fmt(act.baseline_finish)],
        ["Total float", dur(act.total_float_days)], ["Free float", dur(act.free_float_days)],
        ["Critical", act.is_critical ? "yes" : "no"],
        ["Milestone", act.is_milestone ? "yes" : null],
        ["Summary", act.is_summary ? "yes" : null],
      ]));
      return box;
    }]);
    tabs.push(["Predecessors", function () {
      return tiTable(["UID", "Name", "Type", "Lag (d)"],
        (act.predecessors || []).map(function (r) { return [r.uid, r.name, r.type, r.lag_days]; }),
        "No predecessors.");
    }]);
    tabs.push(["Successors", function () {
      return tiTable(["UID", "Name", "Type", "Lag (d)"],
        (act.successors || []).map(function (r) { return [r.uid, r.name, r.type, r.lag_days]; }),
        "No successors.");
    }]);
    tabs.push(["Resources", function () {
      var a = act.assignments || [];
      if (a.length) {
        return tiTable(["Resource", "Units", "Work (d)", "Remaining work (d)"],
          a.map(function (r) {
            return [r.resource, Math.round((r.units || 0) * 100) + "%", r.work_days, r.remaining_work_days];
          }), "");
      }
      return el("p", { class: "muted", text: act.resource_names ? "Assigned: " + act.resource_names + " (no per-assignment detail in the file)" : "No resources assigned." });
    }]);
    tabs.push(["Advanced", function () {
      return tiDL([
        ["Constraint type", act.constraint_type],
        ["Constraint date", fmt(act.constraint_date)],
        ["Deadline", fmt(act.deadline)],
        ["Work", dur(act.work_days)], ["Actual work", dur(act.actual_work_days)],
        ["Cost", money(act.cost)], ["Actual cost", money(act.actual_cost)],
        ["Budgeted cost (BAC)", act.budgeted_cost ? money(act.budgeted_cost) : null],
        ["Elapsed duration", act.duration_is_elapsed ? "yes" : null],
        ["Estimated duration", act.is_estimated_duration ? "yes" : null],
      ]);
    }]);
    tabs.push(["Notes", function () {
      if (act.notes) return el("div", { class: "ti-notes", text: act.notes });
      return el("p", { class: "muted", text: "No note recorded in the source file." });
    }]);
    tabs.push(["Custom Fields", function () {
      var custom = act.custom || {};
      var populated = Object.keys(custom).filter(function (k) {
        return drillValue(custom[k]) !== null;
      }).sort();
      if (!populated.length) return el("p", { class: "muted", text: "No populated custom fields." });
      return tiDL(populated.map(function (k) { return [k, drillValue(custom[k])]; }));
    }]);

    var bar = el("div", { class: "ti-tabs" });
    var body = el("div", { class: "ti-body" });
    tabs.forEach(function (tb, i) {
      var btn = el("button", { type: "button", text: tb[0] });
      if (i === 0) btn.className = "on";
      btn.addEventListener("click", function () {
        bar.querySelectorAll("button").forEach(function (b) { b.className = ""; });
        btn.className = "on";
        body.innerHTML = "";
        body.appendChild(tb[1]());
      });
      bar.appendChild(btn);
    });
    dlg.appendChild(bar);
    body.appendChild(tabs[0][1]());
    dlg.appendChild(body);
    // provenance: the file every figure in this dialog came from (operator: always visible)
    dlg.appendChild(el("div", { class: "ti-cite", text: "Source: " + (act.source_file || "loaded schedule") + " — UID " + act.unique_id + " “" + act.name + "”" }));
    overlay.appendChild(dlg);
    document.body.appendChild(overlay);
    document.addEventListener("keydown", onEsc);
  }

  // ---- openFrom: fetch-and-cache the /api/analysis payload, join by UniqueID ------------
  var cache = {}; // file label/key -> Promise<{uid: act}>
  function rowsFor(file) {
    if (!cache[file]) {
      cache[file] = fetch("/api/analysis/" + encodeURIComponent(file))
        .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
        .then(function (data) {
          var byUid = {};
          (data.activities || []).forEach(function (a) { byUid[a.unique_id] = a; });
          return byUid;
        });
      // a failed fetch must not poison the cache forever (e.g. the file finished loading later)
      cache[file].catch(function () { delete cache[file]; });
    }
    return cache[file];
  }
  function openFrom(file, uid) {
    if (!file || uid == null) return;
    rowsFor(file).then(function (byUid) {
      var act = byUid[uid];
      if (act) { open(act); return; }
      // honest miss: say so instead of showing nothing (e.g. a ghost row for a removed task)
      close();
      var overlay = el("div", { class: "ti-overlay" });
      overlay.addEventListener("click", function (ev) { if (ev.target === overlay) close(); });
      var dlg = el("div", { class: "ti-dialog", role: "dialog" });
      var head = el("div", { class: "ti-head" });
      head.appendChild(el("h3", { text: "Task Information — UID " + uid }));
      var closeBtn = el("button", { class: "ti-close", type: "button", text: "✕" });
      closeBtn.addEventListener("click", close);
      head.appendChild(closeBtn);
      dlg.appendChild(head);
      dlg.appendChild(el("p", { class: "muted", text: "UID " + uid + " is not present in " + file + " (it may have been removed in this version)." }));
      overlay.appendChild(dlg);
      document.body.appendChild(overlay);
      document.addEventListener("keydown", onEsc);
    }).catch(function () { /* fetch failed — leave the page as it was */ });
  }

  return { open: open, openFrom: openFrom, close: close };
})();
