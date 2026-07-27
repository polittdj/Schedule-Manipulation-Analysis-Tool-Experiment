/* Mock /api routes for the Analysis screen — a realistic MLC-3 launch-campaign IMS.
 *
 * Generates ~425 activities (summaries, work packages, milestones) with CPM-plausible
 * dates/floats around the 2026-06-05 data date, matching _analysis_data() in app.py so the
 * REAL static/app.js + scatter.js + histogram.js render the grid, Gantt, charts and drills
 * exactly as the live tool does. Loaded after mock-api.js (registers into SF_MOCK_ROUTES).
 */
"use strict";

(function () {
  var DD = "2026-06-05"; // data date

  /* ── calendar helpers (Mon-Fri working days) ─────────────────────────────────────────── */
  var HOLIDAYS = ["2026-07-03", "2026-09-07", "2026-11-26", "2026-11-27", "2026-12-25"];
  function toDate(iso) { return new Date(iso + "T00:00:00"); }
  function iso(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" +
      String(d.getDate()).padStart(2, "0");
  }
  function isWork(d) {
    var w = d.getDay();
    if (w === 0 || w === 6) return false;
    return HOLIDAYS.indexOf(iso(d)) < 0;
  }
  function addWd(isoDate, wd) { // add working days (wd may be 0; returns next working day aligned)
    var d = toDate(isoDate);
    while (!isWork(d)) d.setDate(d.getDate() + 1);
    var n = Math.abs(wd), step = wd >= 0 ? 1 : -1;
    while (n > 0) {
      d.setDate(d.getDate() + step);
      if (isWork(d)) n--;
    }
    return iso(d);
  }

  /* ── task factory ────────────────────────────────────────────────────────────────────── */
  var rows = [];
  var order = 0;
  function push(t) { t.order = order++; rows.push(t); return t; }

  function base(uid, name, level) {
    return {
      unique_id: uid, name: name, wbs: "", start: "", finish: "",
      baseline_start: "", baseline_finish: "", actual_start: "", actual_finish: "",
      deadline: "", constraint_type: "none", constraint_date: "",
      duration_days: 0, remaining_duration_days: 0, baseline_duration_days: 0,
      work_days: null, actual_work_days: null, cost: null, actual_cost: null,
      budgeted_cost: null, percent_complete: 0, physical_percent_complete: null,
      complete: false, is_milestone: false, is_summary: false, is_manual: false,
      is_active: true, is_estimated_duration: false, duration_is_elapsed: false,
      outline_level: level, resource_names: "", assignments: [], predecessors: [],
      successors: [], notes: "", source_file: "MLC3_IMS_2026-06.mpp", custom: {},
      total_float_days: null, free_float_days: null, is_critical: false,
    };
  }

  function summary(uid, name, level, wbs) {
    var t = base(uid, name, level);
    t.is_summary = true; t.wbs = wbs;
    return push(t);
  }

  // task(uid, name, level, wbs, startISO, durWd, float, opts)
  function task(uid, name, level, wbs, start, dur, tf, o) {
    o = o || {};
    var t = base(uid, name, level);
    t.wbs = wbs;
    t.start = start;
    t.finish = dur > 0 ? addWd(start, dur - 1) : start;
    var slip = o.slip != null ? o.slip : (tf <= 0 ? 8 : tf <= 5 ? 3 : 0); // current vs baseline
    t.baseline_start = addWd(t.start, -slip);
    t.baseline_finish = addWd(t.finish, -slip);
    t.duration_days = dur;
    t.baseline_duration_days = o.bdur != null ? o.bdur : dur;
    t.total_float_days = tf;
    t.free_float_days = o.ff != null ? o.ff : (tf <= 0 ? 0 : Math.min(tf, uid % 14));
    t.is_critical = tf <= 0;
    t.is_milestone = !!o.ms;
    if (o.res) {
      t.resource_names = o.res;
      t.assignments = o.res.split(", ").map(function (r) {
        return { resource: r, units: 1, work_days: dur, remaining_work_days: t.complete ? 0 : dur };
      });
    }
    if (o.cw) t.custom["CA-WBS"] = o.cw;
    // status vs the data date
    var done = t.finish < DD && !o.forceOpen;
    var started = t.start < DD;
    if (done) {
      t.complete = true; t.percent_complete = 100;
      t.actual_start = t.start; t.actual_finish = t.finish;
      t.remaining_duration_days = 0;
    } else if (started) {
      var wdTotal = dur, elapsed = 0, d = toDate(t.start), dd = toDate(DD);
      while (d < dd) { if (isWork(d)) elapsed++; d.setDate(d.getDate() + 1); }
      t.percent_complete = Math.max(5, Math.min(90, Math.round(100 * elapsed / Math.max(1, wdTotal))));
      t.actual_start = t.start;
      t.remaining_duration_days = Math.max(1, wdTotal - elapsed);
    } else {
      t.remaining_duration_days = dur;
    }
    if (o.constraint) { t.constraint_type = o.constraint; t.constraint_date = o.cdate || t.start; }
    if (o.deadline) t.deadline = o.deadline;
    if (o.notes) t.notes = o.notes;
    return push(t);
  }

  function link(pred, succ, type, lag) {
    var p = byUid[pred], s = byUid[succ];
    if (!p || !s) return;
    p.successors.push({ uid: succ, name: s.name, type: type || "FS", lag_days: lag || 0 });
    s.predecessors.push({ uid: pred, name: p.name, type: type || "FS", lag_days: lag || 0 });
  }

  /* ── build the campaign ──────────────────────────────────────────────────────────────── */
  summary(1000, "MLC-3 Flight Campaign", 1, "0");

  // 1.1 Program milestones & reviews
  summary(1100, "Program Milestones & Reviews", 2, "1");
  task(1101, "Campaign Authorization to Proceed", 3, "1", "2026-01-05", 0, 0, { ms: true });
  task(1102, "Stage 1 Booster Arrival (KSC)", 3, "1", "2026-02-16", 0, 4, { ms: true });
  task(1103, "Stage 2 Arrival (KSC)", 3, "1", "2026-03-09", 0, 6, { ms: true });
  task(1104, "Lunar Cargo Module Arrival", 3, "1", "2026-04-13", 0, 0, { ms: true });
  task(1105, "Integration Readiness Review", 3, "1", "2026-07-15", 0, 0, { ms: true, forceOpen: true });
  task(1106, "Wet Dress Rehearsal Complete", 3, "1", "2026-10-13", 0, 0, { ms: true, forceOpen: true });
  task(1107, "Flight Readiness Review", 3, "1", "2026-12-08", 0, 0, { ms: true, forceOpen: true, deadline: "2026-11-20" });
  task(1108, "Launch Readiness Review", 3, "1", "2026-12-16", 0, 0, { ms: true, forceOpen: true });
  var LAUNCH = task(9001, "MLC-3 Launch", 3, "1", "2026-12-21", 0, 0, { ms: true, forceOpen: true, constraint: "MFO", cdate: "2026-12-21", notes: "Lunar transfer window opens 12/18; backup window 01/12/2027." });

  /* generator for subsystem work packages */
  var uidSeq = 2000;
  function pkg(wbs, level, sumName, units, steps, opt) {
    opt = opt || {};
    var s = summary(uidSeq++, sumName, level, wbs);
    var chainEnds = [];
    units.forEach(function (u, ui) {
      var start = addWd(opt.start, ui * (opt.stagger != null ? opt.stagger : 6));
      var prev = null;
      steps.forEach(function (st, si) {
        var uid = uidSeq++;
        var tf = opt.tf != null ? (typeof opt.tf === "function" ? opt.tf(ui, si) : opt.tf) : 12;
        var nm = (u ? u + " — " : "") + st[0];
        var t = task(uid, nm, level + 1, wbs + "." + (ui + 1), start, st[1], tf, {
          res: st[2] || opt.res, cw: opt.cw, slip: opt.slip,
        });
        if (prev) link(prev.unique_id, uid, "FS", 0);
        prev = t;
        start = addWd(start, st[1]);
      });
      if (prev) chainEnds.push(prev.unique_id);
    });
    return { summary: s, ends: chainEnds };
  }

  var byUid = {};
  rows.forEach(function (r) { byUid[r.unique_id] = r; });
  // (link() needs byUid live — rebuild as tasks are added)
  var _push = push;
  push = function (t) { byUid[t.unique_id] = t; return _push(t); };

  // 2 Campaign Planning & Pathfinders (complete by DD)
  summary(1150, "Campaign Planning & Pathfinders", 2, "2");
  pkg("2.1", 3, "Campaign Planning", ["Plan"], [
    ["IMS Baseline Development", 8, "Planning"], ["Integrated Baseline Review Prep", 5, "Planning"],
    ["Integrated Baseline Review", 2, "Systems Eng"], ["Baseline Disposition & Update", 4, "Planning"],
  ], { start: "2026-01-05", tf: 14, cw: "CA-110" });
  pkg("2.2", 3, "Pathfinder Operations", ["Lift Pathfinder", "Transport Pathfinder", "Mate Pathfinder"], [
    ["Procedure Dry Run", 3, "Integration Crew A"], ["Crane Certification Run", 2, "Move Crew"],
    ["Lessons-Learned Closeout", 2, "Systems Eng"],
  ], { start: "2026-01-19", stagger: 7, tf: 10, cw: "CA-111" });
  pkg("2.3", 3, "Crew Training & Certification", ["Crew A", "Crew B", "Cryo Team", "Launch Team"], [
    ["Hazardous Ops Refresher", 2, "Training"], ["Task-Specific Certification", 4, "Training"],
    ["Certification Board", 1, "QA"],
  ], { start: "2026-02-02", stagger: 5, tf: 12, cw: "CA-112" });

  // 3 Stage 1 Booster Processing (mostly complete/in-work, modest float)
  summary(1200, "Stage 1 Booster Processing", 2, "3");
  pkg("3.1", 3, "Receiving & Inspection", ["Booster"], [
    ["Offload & Transport to HIF", 3, "Move Crew"], ["Receiving Inspection", 5, "QA"],
    ["Transport Damage Assessment", 2, "QA"], ["Handling Fixture Install", 3, "Integration Crew A"],
  ], { start: "2026-02-17", tf: 9, cw: "CA-120" });
  pkg("3.2", 3, "Engine Section Processing", ["Engine 1", "Engine 2", "Engine 3", "Engine 4"], [
    ["Borescope Inspection", 4, "Propulsion"], ["TVC Actuator Checkout", 5, "Propulsion"],
    ["Turbopump Torque Check", 2, "Propulsion"], ["Ancillary Line Inspection", 3, "Propulsion"],
    ["Heat Shield Blanket Install", 6, "Thermal"], ["Engine Section Closeout", 3, "QA"],
  ], { start: "2026-03-02", stagger: 5, tf: function (ui, si) { return 6 + ui * 2; }, cw: "CA-121" });
  pkg("3.3", 3, "Aft Skirt & Umbilicals", ["Booster"], [
    ["Aft Skirt Mate", 4, "Integration Crew A"], ["Umbilical Plate Fit Check", 3, "Fluids"],
    ["Purge Line Leak Check", 4, "Fluids"], ["Aft Closeout Photos", 1, "QA"],
  ], { start: "2026-04-06", tf: 8, cw: "CA-122" });
  pkg("3.4", 3, "Booster Structures & TPS", ["Fwd Skirt", "Intertank", "LOX Tank", "Fuel Tank"], [
    ["NDE Inspection", 4, "QA"], ["TPS Repair & Closeout", 5, "Thermal"],
    ["Cork Ablator Touch-Up", 3, "Thermal"], ["Structures QA Buy-Off", 2, "QA"],
  ], { start: "2026-03-16", stagger: 6, tf: function (ui) { return 8 + ui * 3; }, slip: -2, cw: "CA-124" });
  pkg("3.5", 3, "Stage 1 Systems Test", ["Booster"], [
    ["Power-On Functional", 5, "Avionics"], ["Hydraulic System Test", 4, "Fluids"],
    ["RF Open-Loop Test", 3, "Avionics"], ["Stage 1 Test Data Review", 3, "Systems Eng"],
  ], { start: "2026-05-11", tf: 5, cw: "CA-123" });

  // 4 Stage 2 Processing (in work at DD; avionics chain slipping)
  summary(1300, "Stage 2 Processing", 2, "4");
  pkg("4.1", 3, "Stage 2 Receiving", ["Stage 2"], [
    ["Offload & Transport to HIF", 2, "Move Crew"], ["Receiving Inspection", 4, "QA"],
    ["Handling Ring Install", 2, "Integration Crew B"],
  ], { start: "2026-03-10", tf: 11, cw: "CA-130" });
  pkg("4.2", 3, "Stage 2 Avionics", ["Stage 2"], [
    ["Avionics Bay Access", 2, "Avionics"], ["Flight Computer Swap (FCA-2)", 6, "Avionics"],
    ["Harness Continuity Check", 4, "Avionics"], ["Avionics Functional Test", 8, "Avionics"],
    ["Functional Test Data Review", 4, "Systems Eng"],
  ], { start: "2026-05-04", tf: 2, slip: 12, cw: "CA-131" });
  pkg("4.3", 3, "Avionics Box Retest", ["IMU A", "IMU B", "Flight Battery 1", "Flight Battery 2", "TM Transmitter", "C-Band Transponder"], [
    ["Bench Acceptance Retest", 3, "Avionics"], ["Vibration Screen", 2, "Test Lab"],
    ["Thermal Cycle Screen", 3, "Test Lab"], ["Reinstall & Retest", 2, "Avionics"],
  ], { start: "2026-04-13", stagger: 4, tf: function (ui) { return 4 + (ui % 3) * 4; }, cw: "CA-133" });
  pkg("4.4", 3, "Stage 2 Propulsion", ["Stage 2"], [
    ["RCS Thruster Install", 6, "Propulsion"], ["RCS Leak Check", 4, "Fluids"],
    ["Helium COPV Inspection", 3, "Propulsion"], ["Propulsion Closeout", 2, "QA"],
  ], { start: "2026-05-18", tf: 7, cw: "CA-132" });

  // 5 Lunar Cargo Module (payload) — the CRITICAL chain, fairing chain negative
  summary(1400, "Lunar Cargo Module (Payload)", 2, "5");
  pkg("5.1", 3, "LCM Receiving & Test", ["LCM"], [
    ["Offload to PPF", 2, "Move Crew"], ["Receiving Inspection", 4, "QA"],
    ["Solar Array Deployment Test", 6, "Payload Ops"], ["Battery Conditioning", 5, "Payload Ops"],
    ["End-to-End Comms Test", 5, "Payload Ops"],
  ], { start: "2026-04-14", tf: 0, slip: 6, cw: "CA-140" });
  pkg("5.2", 3, "Cargo Integration", ["Rover Pallet", "Science Pallet", "Consumables Rack A", "Consumables Rack B"], [
    ["Cargo Fit Check", 2, "Payload Ops"], ["Cargo Install & Torque", 3, "Payload Ops"],
    ["Mass Properties Update", 1, "Systems Eng"], ["Cargo Closeout Inspection", 2, "QA"],
  ], { start: "2026-05-18", stagger: 5, tf: function (ui) { return 3 + ui * 2; }, cw: "CA-143" });
  pkg("5.3", 3, "LCM Propellant Servicing", ["LCM"], [
    ["Servicing Cart Hookup", 2, "Cryo Ops"], ["Oxidizer Load", 3, "Cryo Ops"],
    ["Fuel Load", 3, "Cryo Ops"], ["Pressurant Top-Off", 2, "Cryo Ops"],
    ["Servicing Closeout & Decon", 3, "Cryo Ops"],
  ], { start: "2026-06-24", tf: 0, cw: "CA-141" });
  pkg("5.4", 3, "Fairing Encapsulation", ["LCM"], [
    ["Fairing Half Prep", 4, "Payload Ops"], ["Acoustic Blanket Install", 5, "Thermal"],
    ["LCM Mate to Adapter", 3, "Integration Crew B"], ["Payload Fairing Encapsulation", 4, "Payload Ops"],
    ["Encapsulated Transport to VAB", 2, "Move Crew"],
  ], { start: "2026-07-13", tf: -4, slip: 10, cw: "CA-142" });

  // 6 Ground Systems & GSE (high float — DCMA-06 offenders live here)
  summary(1500, "Ground Systems & GSE", 2, "6");
  pkg("6.1", 3, "Pad Fluid Systems", ["LOX Farm", "LH2 Farm", "Helium", "Nitrogen", "Water Deluge", "ECS Air"], [
    ["System Refurbishment", 10, "Pad Systems"], ["Valve Replacement", 6, "Pad Systems"],
    ["Instrumentation Recal", 4, "Pad Systems"], ["Proof & Leak Test", 5, "Fluids"],
    ["System Certification", 3, "QA"],
  ], { start: "2026-04-20", stagger: 8, tf: function (ui) { return 34 + ui * 6; }, cw: "CA-150" });
  pkg("6.2", 3, "Mobile Launcher", ["ML-2"], [
    ["Swing Arm Actuator Refurb", 12, "Pad Systems"], ["Umbilical Retest", 6, "Pad Systems"],
    ["Sound Suppression Water Test", 4, "Pad Systems"], ["Crawler Transport Fit Check", 2, "Move Crew"],
  ], { start: "2026-05-04", tf: 30, cw: "CA-151" });
  pkg("6.3", 3, "Pad Structures", ["FSS Level 1-4", "FSS Level 5-8", "Lightning Towers", "Flame Trench"], [
    ["Corrosion Remediation", 8, "Pad Systems"], ["Structural Inspection", 4, "QA"],
    ["Paint & Seal", 6, "Pad Systems"],
  ], { start: "2026-05-25", stagger: 9, tf: function (ui) { return 40 + ui * 7; }, cw: "CA-153" });
  pkg("6.4", 3, "Range & Tracking", ["Range"], [
    ["FTS Battery Install", 3, "Range Safety"], ["FTS End-to-End Test", 4, "Range Safety"],
    ["Tracking Station Readiness", 5, "Range Safety"],
  ], { start: "2026-09-14", tf: 18, cw: "CA-152" });

  // 7 Integration & Stacking (critical)
  summary(1600, "Integration & Stacking", 2, "7");
  pkg("7.1", 3, "Vehicle Stacking", ["Vehicle"], [
    ["Stage 1 Lift & Set on ML", 3, "Integration Crew A"], ["Stage 2 Mate", 4, "Integration Crew A"],
    ["Interstage Torque & Closeout", 5, "Integration Crew A"], ["Encapsulated Payload Lift & Mate", 3, "Integration Crew B"],
    ["Integrated Vehicle Stack Complete", 0, "Integration Crew B"],
  ], { start: "2026-08-10", tf: 0, cw: "CA-160" });
  pkg("7.2", 3, "Integrated Test", ["Vehicle"], [
    ["Umbilical Connect & Verify", 4, "Pad Systems"], ["Integrated Power-On", 3, "Avionics"],
    ["Integrated Vehicle Test (IVT)", 8, "Systems Eng"], ["IVT Data Review", 4, "Systems Eng"],
    ["Ordnance Install", 3, "Range Safety"],
  ], { start: "2026-09-07", tf: 0, cw: "CA-161" });
  pkg("7.3", 3, "Interface Verification", ["Stage 1/Stage 2 IF", "Stage 2/PLA IF", "Vehicle/ML IF"], [
    ["Interface Torque Audit", 2, "QA"], ["Electrical IF Verification", 3, "Avionics"],
    ["Fluid IF Leak Check", 3, "Fluids"],
  ], { start: "2026-09-14", stagger: 4, tf: function (ui) { return 4 + ui * 3; }, cw: "CA-162" });

  // 8 Pad Operations & Launch (critical; includes margin)
  summary(1700, "Pad Operations & Launch", 2, "8");
  pkg("8.1", 3, "Rollout & WDR", ["Vehicle"], [
    ["Rollout to Pad 39C", 2, "Move Crew"], ["Pad Validation Checks", 4, "Pad Systems"],
    ["Wet Dress Rehearsal", 3, "Launch Team"], ["WDR Data Review & Scrub Fixes", 5, "Systems Eng"],
    ["Rollback for Ordnance Closeout", 2, "Move Crew"],
  ], { start: "2026-10-05", tf: 0, cw: "CA-170" });
  pkg("8.2", 3, "Launch Campaign", ["Vehicle"], [
    ["Static Fire (Flight Duration)", 1, "Launch Team"], ["Static Fire Data Review", 4, "Systems Eng"],
    ["Final Vehicle Closeouts", 5, "Integration Crew A"], ["Launch Countdown Demonstration", 2, "Launch Team"],
    ["L-2 Day Countdown Pickup", 2, "Launch Team"],
  ], { start: "2026-11-09", tf: 0, cw: "CA-171" });
  task(uidSeq++, "Schedule Margin — Pad Ops", 3, "8", "2026-12-09", 5, 0, { res: "Launch Team", notes: "Program-held margin protecting the launch window." });

  // 9 Flight Software & Mission Ops (parallel, moderate float)
  summary(1800, "Flight Software & Mission Ops", 2, "9");
  pkg("9.1", 3, "Flight Software", ["FSW 4.2", "FSW 4.3"], [
    ["Build Release", 5, "Software"], ["HWIL Regression", 8, "Software"],
    ["Guidance Sim Campaign", 6, "Software"], ["Software Acceptance Review", 2, "Systems Eng"],
    ["Load & Verify on Vehicle", 3, "Avionics"],
  ], { start: "2026-05-11", stagger: 25, tf: function (ui) { return ui ? 12 : 4; }, cw: "CA-180" });
  pkg("9.2", 3, "Mission Operations Readiness", ["MOC"], [
    ["Flight Rules Baseline", 6, "Mission Ops"], ["Joint Integrated Sim 1", 3, "Mission Ops"],
    ["Joint Integrated Sim 2", 3, "Mission Ops"], ["Launch Countdown Sim", 2, "Mission Ops"],
    ["MOC Certification", 2, "Mission Ops"],
  ], { start: "2026-07-06", tf: 15, cw: "CA-181" });
  pkg("9.3", 3, "Recovery & Logistics", ["Recovery"], [
    ["Recovery Vessel Refit", 12, "Logistics"], ["Recovery Rehearsal", 4, "Logistics"],
    ["Downrange Asset Deployment", 6, "Logistics"],
  ], { start: "2026-08-03", tf: 52, cw: "CA-182" });

  /* stitch the campaign-level driving chain */
  link(1104, 9001, "FS", 0); // placeholder logical tie
  link(1107, 1108, "FS", 0);
  link(1108, 9001, "FS", 0);
  link(1106, 1107, "FS", 0);

  /* roll up summary spans from their descendants (MS Project stores summary dates) */
  (function rollup() {
    var best = {}; // top wbs segment of children under each summary uid via outline walk
    // walk rows in order; maintain stack of open summaries by outline_level
    var stack = [];
    rows.forEach(function (r) {
      while (stack.length && stack[stack.length - 1].outline_level >= r.outline_level) stack.pop();
      if (!r.is_summary && r.start && r.finish) {
        stack.forEach(function (s) {
          if (!s.start || r.start < s.start) s.start = r.start;
          if (!s.finish || r.finish > s.finish) s.finish = r.finish;
          if (!s.baseline_start || r.baseline_start < s.baseline_start) s.baseline_start = r.baseline_start;
          if (!s.baseline_finish || r.baseline_finish > s.baseline_finish) s.baseline_finish = r.baseline_finish;
        });
      }
      if (r.is_summary) stack.push(r);
    });
    rows.forEach(function (r) {
      if (!r.is_summary) return;
      if (r.start && r.finish) {
        var d = toDate(r.start), e = toDate(r.finish), wd = 0;
        while (d <= e) { if (isWork(d)) wd++; d.setDate(d.getDate() + 1); }
        r.duration_days = wd;
        var allDone = true, dd = DD;
        // a summary is complete when its span ended before the data date
        if (r.finish < dd) { r.complete = true; r.percent_complete = 100; r.actual_start = r.start; r.actual_finish = r.finish; }
        else if (r.start < dd) { r.percent_complete = 50; r.actual_start = r.start; }
      }
    });
  })();

  /* ── /api/analysis payload ───────────────────────────────────────────────────────────── */
  var D = window.SF_DCMA_DOCS = {
    DCMA01: ["DCMA 01", "Logic", "Incomplete activities missing a predecessor and/or successor.", "count(incomplete without pred or succ) / incomplete <= 5%", "No more than 5% of incomplete activities may be missing a predecessor or a successor.", "Every activity must be tied into the network on both ends so a slip anywhere flows through to the finish. Dangling tasks break that chain.", "12 open-ended tasks on a 783-activity plan = 1.5% -> PASS (well under 5%).", "180 of 600 incomplete tasks (30%) have no successor -> FAIL; the finish date cannot be trusted."],
    DCMA02: ["DCMA 02", "Leads", "Relationships with a negative lag (a lead). Counted as DISTINCT incomplete-successor activities (the Fuse-validated activity scope), not raw relationships: a task with two lead predecessors is ONE offender (QC audit D22).", "count(distinct incomplete successors of lag < 0 links) == 0", "Zero relationships may carry a negative lag (a lead).", "Leads (negative lag) let a successor start before its predecessor finishes, compressing the plan in a way that hides true logic and can mask a slip.", "No relationship has a negative lag -> PASS.", "A 'FS -5d' link pulls a successor 5 days early -> FAIL; remodel as an SS with a positive lag."],
    DCMA03: ["DCMA 03", "Lags", "Relationships with a positive lag into an incomplete successor. Counted as DISTINCT incomplete-successor activities over a total-links denominator (the Fuse-validated scope): a task with two lagged predecessors is ONE offender (QC audit D22).", "count(distinct incomplete successors of lag > 0 links) / links <= 5%", "No more than 5% of relationships may carry a positive lag.", "Lags bury real work (cure, delivery, review) inside a relationship where it cannot be progressed, resourced, or seen — over-use distorts the critical path.", "8 lagged links out of 900 (0.9%) -> PASS.", "140 of 900 links (16%) bury cure/delivery time as lag -> FAIL; model the wait as a real task."],
    DCMA04_FS: ["DCMA 04 FS", "FS Relationships", "Share of relationships that are Finish-to-Start.", "count(FS) / links >= 90%", "At least 90% of relationships must be Finish-to-Start.", "Finish-to-Start is the clearest, most defensible logic. A schedule built mostly from FS links is easier to analyse and behaves predictably under change.", "92% of links are FS -> PASS.", "FS share is 71% (heavy SS/FF use) -> FAIL; the true driving path is obscured."],
    DCMA04_SSFF: ["DCMA 04 SSFF", "SS/FF Relationships", "Start-Start / Finish-Finish links into incomplete work.", "count(SS|FF into incomplete)", "Informational: the count of SS/FF links into incomplete work should reflect real overlap, not missing detail.", "SS/FF links model genuine overlap, but each one should reflect real concurrency rather than a workaround for missing detail.", "A handful of SS/FF links, each a genuine concurrency -> acceptable.", "Dozens of SS/FF links standing in for missing detail -> review and break them into FS-linked tasks."],
    DCMA04_SF: ["DCMA 04 SF", "SF Relationships", "Start-to-Finish relationships (discouraged).", "count(SF into incomplete)", "Zero Start-to-Finish relationships (they are almost never correct).", "Start-to-Finish logic is rarely correct and is almost never needed; it inverts the normal flow of work and confuses analysis.", "No SF links in the network -> PASS.", "Any SF link -> review; it inverts the normal flow of work and usually signals a modelling error."],
    DCMA05: ["DCMA 05", "Hard Constraints", "Activities with a hard/mandatory constraint (MSO/MFO/SNLT/FNLT).", "count(hard constraint) / activities <= 5%", "No more than 5% of activities may carry a hard constraint (MSO/MFO/SNLT/FNLT).", "Hard constraints override network logic, freezing dates so the schedule no longer reacts to upstream slips. They mask true float and hide risk.", "10 of 600 activities (1.7%) hard-constrained -> PASS.", "120 of 600 (20%) hard-constrained -> FAIL; dates are imposed, not logic-driven."],
    DCMA06: ["DCMA 06", "High Float", "Incomplete activities with total float > 44 working days.", "count(total_float > 44d) / incomplete <= 5%", "No more than 5% of incomplete activities may have total float over 44 working days.", "Very high float usually means an activity is not properly tied to its successors, so it floats free of the network and understates risk.", "15 of 600 incomplete tasks (2.5%) above 44 d -> PASS.", "200 of 600 (33%) float free of the network -> FAIL; successor logic is missing."],
    DCMA07: ["DCMA 07", "Negative Float", "Incomplete activities with total float < 0.", "count(total_float < 0) == 0", "Zero incomplete activities may have negative total float.", "Negative float means the plan is already behind a constraint or deadline — work must be recovered for the schedule to be achievable.", "No task carries negative float -> PASS; the plan is achievable as drawn.", "40 tasks at -12 d total float -> FAIL; a path cannot meet its imposed finish."],
    DCMA08: ["DCMA 08", "High Duration", "Incomplete activities with baseline duration > 44 working days.", "count(baseline_dur > 44d) / incomplete <= 5%", "No more than 5% of incomplete activities may have a baseline duration over 44 working days.", "Long activities are hard to status accurately and hide progress and risk inside a single bar; they should be decomposed into measurable detail.", "12 of 600 (2%) run longer than 44 d -> PASS.", "150 of 600 (25%) exceed 44 d -> FAIL; decompose them so progress is visible."],
    DCMA09: ["DCMA 09", "Invalid Dates", "Actuals after the status date, or a stored forecast (early) date already in the past without the matching actual — the Bible's Invalid Forecast Dates conditions, scored on the file's OWN stored start/finish dates (Acumen basis, ADR-0176), with recomputed CPM only as a fallback for files carrying no stored dates. Task-level count (Fuse's Metric History counts fields, so its figure can be up to 2x this activity count).", "((EarlyStart<Now)*(ActualStart=\"\")) + ((EarlyFinish<Now)*(ActualFinish=\"\")) + actuals after Now == 0", "Zero actuals after the data date and zero incomplete (forecast) work scheduled in the past.", "Actual dates in the future or forecast (incomplete) work in the past are logically impossible and corrupt every downstream calculation.", "Every actual is on or before the data date and every forecast is after it -> PASS.", "An actual finish dated two weeks after the data date -> FAIL; the schedule was not statused."],
    DCMA10: ["DCMA 10", "Resources", "Incomplete, real-duration activities with no resource assigned.", "count(no resource) / incomplete-with-duration <= 5%", "No more than 5% of incomplete, real-duration activities may have no resource assigned.", "A resource-loaded schedule supports cost and earned-value analysis; unresourced real-duration work cannot be costed or levelled.", "Every open task is resourced or flagged level-of-effort -> PASS.", "300 of 600 open tasks carry no resource -> FAIL; the plan cannot be costed or levelled."],
    DCMA11: ["DCMA 11", "Missed Activities", "Baselined-due-by-status activities not finished on time.", "count(due not finished on time) / due <= 5%", "No more than 5% of activities baselined to finish by the data date may still be unfinished.", "Tasks baselined to finish by now that have not is the most direct measure of slip against the plan of record.", "5 of 200 due tasks slipped (2.5%) -> PASS.", "60 of 200 due tasks (30%) not finished -> FAIL; the schedule is behind its baseline."],
    DCMA12: ["DCMA 12", "Critical Path Test", "A delay on a critical activity must flow to the project finish.", "inject delay on critical task -> finish moves by the delay", "A delay injected on a critical activity must move the project finish by the same amount.", "A schedule must have a continuous, controlling critical path; if a delay on a critical task does not move the finish, the network logic is broken.", "Inject +10 d on a critical task and the finish moves +10 d -> PASS.", "The finish does not move -> FAIL; a constraint or open end is absorbing the delay (broken critical path)."],
    DCMA13: ["DCMA 13", "CPLI", "Critical Path Length Index.", "(remaining crit-path length + project total float) / remaining crit-path length >= 0.95", "Critical Path Length Index must be at least 0.95 (1.0 means the path just fits).", "CPLI measures how realistic the finish is: 1.0 means the critical path just fits, below ~0.95 means the path is already eroding into negative float.", "CPLI of 1.02 -> PASS; the finish has a little slack.", "CPLI of 0.78 -> FAIL; the controlling path is eroding into negative float."],
    DCMA14: ["DCMA 14", "BEI", "Baseline Execution Index (BEI - Value Tasks; Normal activities only). Cumulative: BOTH terms score the same baselined-due population — tasks completed ahead of a baseline finish that is not yet due do not inflate the numerator (ADR-0176; verified vs every Acumen oracle incl. Hard_File_updated 0.27).", "complete among baselined-due / Normal tasks baselined-to-finish-by-status >= 0.95", "Baseline Execution Index must be at least 0.95 (work completed / work baselined to be complete).", "BEI tracks throughput against the baseline: are activities being completed as fast as the plan said they would be?", "BEI of 0.98 -> PASS; throughput is on plan.", "BEI of 0.62 -> FAIL; work is finishing far slower than baselined - an early slip signal."],
  };

  // status/measure per check for THIS file (IMS 2026-06: Logic, High Float, Negative Float,
  // Missed Activities, CPLI, BEI fail; Resources n/a)
  var CHECKS = {
    DCMA01: ["FAIL", 14, 100, 14.0, "%", "14 of 100 (14%)"],
    DCMA02: ["PASS", 0, 186, 0, "%", "0 of 186 (0%)"],
    DCMA03: ["PASS", 0, 186, 0, "%", "0 of 186 (0%)"],
    DCMA04_FS: ["PASS", 186, 186, 100.0, "%", "186 of 186 (100%)"],
    DCMA04_SSFF: ["PASS", 0, 186, 0, "%", "0 of 186 (0%)"],
    DCMA04_SF: ["PASS", 0, 186, 0, "%", "0 of 186 (0%)"],
    DCMA05: ["PASS", 1, 250, 0.4, "%", "1 of 250 (0.4%)"],
    DCMA06: ["FAIL", 29, 100, 29.0, "%", "29 of 100 (29%)"],
    DCMA07: ["FAIL", 5, 100, 5.0, "%", "5 of 100 (5%)"],
    DCMA08: ["PASS", 0, 100, 0, "%", "0 of 100 (0%)"],
    DCMA09: ["PASS", 0, 250, 0, "%", "0 of 250 (0%)"],
    DCMA10: ["PASS", 0, 94, 0, "%", "0 of 94 (0%)"],
    DCMA11: ["FAIL", 21, 153, 13.7, "%", "21 of 153 (13.7%)"],
    DCMA12: ["PASS", 0, 0, 1, "", "pass"],
    DCMA13: ["FAIL", 0, 0, 0.91, "ratio", "0.91"],
    DCMA14: ["FAIL", 0, 0, 0.87, "ratio", "0.87"],
  };
  var dcma = {};
  Object.keys(CHECKS).forEach(function (id) {
    var c = CHECKS[id], d = D[id];
    dcma[id] = {
      label: d[0], name: d[1], status: c[0], count: c[1], value: c[3], measure: c[5],
      definition: d[2], why: d[5], threshold: d[4], example_ok: d[6], example_fail: d[7],
    };
  });

  var FINDINGS = [
    { severity: "HIGH", category: "Risk", title: "Negative float on the fairing-encapsulation chain (−4 wd)", citations: [{ file: "MLC3_IMS_2026-06.mpp", uid: byName("LCM — Payload Fairing Encapsulation"), task: "LCM — Payload Fairing Encapsulation" }, { file: "MLC3_IMS_2026-06.mpp", uid: byName("LCM — Acoustic Blanket Install"), task: "LCM — Acoustic Blanket Install" }] },
    { severity: "HIGH", category: "Risk", title: "BEI 0.87 — throughput below the 0.95 execution bar", citations: [{ file: "MLC3_IMS_2026-06.mpp", uid: byName("Stage 2 — Avionics Functional Test"), task: "Stage 2 — Avionics Functional Test" }] },
    { severity: "MEDIUM", category: "Concern", title: "29 incomplete activities carry > 44 wd of float (possible missing successors)", citations: [{ file: "MLC3_IMS_2026-06.mpp", uid: byName("LOX Farm — System Refurbishment"), task: "LOX Farm — System Refurbishment" }] },
    { severity: "MEDIUM", category: "Concern", title: "21 baselined-due activities not finished by the data date (DCMA-11 13.7%)", citations: [{ file: "MLC3_IMS_2026-06.mpp", uid: byName("Stage 2 — Flight Computer Swap (FCA-2)"), task: "Stage 2 — Flight Computer Swap (FCA-2)" }] },
    { severity: "LOW", category: "Opportunity", title: "Mobile Launcher refurb float (30 wd) could absorb a payload-chain resequence", citations: [{ file: "MLC3_IMS_2026-06.mpp", uid: byName("ML-2 — Swing Arm Actuator Refurb"), task: "ML-2 — Swing Arm Actuator Refurb" }] },
  ];
  function byName(n) {
    for (var i = 0; i < rows.length; i++) if (rows[i].name === n) return rows[i].unique_id;
    return 0;
  }

  var ANALYSIS = {
    name: "MLC-3 IMS 2026-06",
    source_file: "MLC3_IMS_2026-06.mpp",
    tasks: rows.length,
    status_date: DD,
    calendar: {
      name: "MLC Standard 5x8", working_minutes_per_day: 480,
      work_weekdays: [0, 1, 2, 3, 4], holidays: HOLIDAYS,
    },
    calendars: [
      { name: "MLC Standard 5x8", work_weekdays: [0, 1, 2, 3, 4], holidays: HOLIDAYS },
      { name: "Pad Ops 7-Day", work_weekdays: [0, 1, 2, 3, 4, 5, 6], holidays: [] },
    ],
    dcma: dcma,
    baseline_compliance: {
      completed_on_time: 114, completed_late: 36, not_completed: 100,
      started_on_time: 118, started_late: 38, not_started: 94,
    },
    float_bands: {
      float_total_0: { count: 36, population: 100, value: 36.0 },
      float_total_lt5: { count: 41, population: 100, value: 41.0 },
      float_total_lt10: { count: 52, population: 100, value: 52.0 },
      float_free_0: { count: 43, population: 100, value: 43.0 },
      float_free_lt5: { count: 74, population: 100, value: 74.0 },
      float_free_lt10: { count: 89, population: 100, value: 89.0 },
    },
    completion: {
      completed_ahead: { count: 16, population: 150, value: 10.7, unit: "%" },
      completed_on_schedule: { count: 98, population: 150, value: 65.3, unit: "%" },
      completed_behind: { count: 36, population: 150, value: 24.0, unit: "%" },
      avg_days_ahead: { count: 16, population: 16, value: 2.0, unit: "days" },
      avg_days_late: { count: 36, population: 36, value: 6.8, unit: "days" },
      avg_completion_variance: { count: 150, population: 150, value: 1.4, unit: "days" },
      longer_than_planned: { count: 22, population: 150, value: 14.7, unit: "%" },
      shorter_than_planned: { count: 9, population: 150, value: 6.0, unit: "%" },
      duration_ratio_min: { count: 0, population: 150, value: 0.8, unit: "ratio" },
      duration_ratio_avg: { count: 0, population: 150, value: 1.12, unit: "ratio" },
      duration_ratio_max: { count: 0, population: 150, value: 1.9, unit: "ratio" },
      mei: { count: 4, population: 4, value: 1.0, unit: "ratio" },
      epi: { count: 0, population: 0, value: 0.91, unit: "ratio" },
      start_finish_ratio: { count: 0, population: 0, value: 1.04, unit: "ratio" },
      elapsed_since_last_finish: { count: 3, population: 1, value: 3, unit: "days" },
    },
    activities: rows,
    custom_field_labels: ["CA-WBS"],
    findings: FINDINGS,
  };

  /* driving trace for the launch (UID 9001) */
  function traceRows() {
    var chain = [
      ["LCM — End-to-End Comms Test", "DRIVING", 0],
      ["LCM — Servicing Cart Hookup", "DRIVING", 0],
      ["LCM — Oxidizer Load", "DRIVING", 0],
      ["LCM — Fuel Load", "DRIVING", 0],
      ["LCM — Pressurant Top-Off", "DRIVING", 0],
      ["LCM — Servicing Closeout & Decon", "DRIVING", 0],
      ["LCM — Fairing Half Prep", "DRIVING", 0],
      ["LCM — Acoustic Blanket Install", "DRIVING", 0],
      ["LCM — LCM Mate to Adapter", "DRIVING", 0],
      ["LCM — Payload Fairing Encapsulation", "DRIVING", 0],
      ["LCM — Encapsulated Transport to VAB", "DRIVING", 0],
      ["Vehicle — Encapsulated Payload Lift & Mate", "DRIVING", 0],
      ["Vehicle — Integrated Vehicle Stack Complete", "DRIVING", 0],
      ["Vehicle — Umbilical Connect & Verify", "DRIVING", 0],
      ["Vehicle — Integrated Power-On", "DRIVING", 0],
      ["Vehicle — Integrated Vehicle Test (IVT)", "DRIVING", 0],
      ["Vehicle — IVT Data Review", "DRIVING", 0],
      ["Vehicle — Ordnance Install", "DRIVING", 0],
      ["Vehicle — Rollout to Pad 39C", "DRIVING", 0],
      ["Vehicle — Pad Validation Checks", "DRIVING", 0],
      ["Vehicle — Wet Dress Rehearsal", "DRIVING", 0],
      ["Wet Dress Rehearsal Complete", "DRIVING", 0],
      ["Vehicle — WDR Data Review & Scrub Fixes", "DRIVING", 0],
      ["Vehicle — Static Fire (Flight Duration)", "DRIVING", 0],
      ["Vehicle — Static Fire Data Review", "DRIVING", 0],
      ["Vehicle — Final Vehicle Closeouts", "DRIVING", 0],
      ["Flight Readiness Review", "DRIVING", 0],
      ["Launch Readiness Review", "DRIVING", 0],
      ["MLC-3 Launch", "DRIVING", 0],
      ["Stage 2 — Avionics Functional Test", "SECONDARY", 2],
      ["Stage 2 — Functional Test Data Review", "SECONDARY", 2],
      ["Stage 2 — RCS Leak Check", "SECONDARY", 7],
      ["Booster — Power-On Functional", "SECONDARY", 5],
      ["Range — FTS End-to-End Test", "TERTIARY", 18],
      ["ML-2 — Umbilical Retest", "TERTIARY", 20],
    ];
    var out = [], ordi = 0;
    chain.forEach(function (c) {
      var t = byUid[byName(c[0])];
      if (!t) return;
      out.push({
        unique_id: t.unique_id, name: t.name, duration_days: t.duration_days,
        start: t.start, finish: t.finish, driving_slack_days: c[2], tier: c[1],
        complete: t.complete, is_milestone: t.is_milestone, finish_ord: ordi++,
      });
    });
    return out;
  }

  var enc = encodeURIComponent("MLC-3 IMS 2026-06");
  ["MLC-3 IMS 2026-06", "MLC-3 IMS 2026-05", "MLC-3 IMS 2026-04"].forEach(function (name) {
    window.SF_MOCK_ROUTES["/api/analysis/" + encodeURIComponent(name)] = ANALYSIS;
    window.SF_MOCK_ROUTES["/api/driving/" + encodeURIComponent(name)] = function (url) {
      var m = /target=(\d+)/.exec(url);
      var uid = m ? Number(m[1]) : 9001;
      if (uid !== 9001) {
        return { target_uid: uid, target_name: "", note: "No driving path found to UID " + uid + " (mock data traces to UID 9001 — MLC-3 Launch).", rows: [], data_date: DD };
      }
      return { target_uid: 9001, target_name: "MLC-3 Launch", rows: traceRows(), data_date: DD };
    };
  });
  window.SF_MOCK_ROUTES["/api/ai/narrative"] = {};
})();
