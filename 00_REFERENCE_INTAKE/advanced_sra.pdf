/* Recreation harness — serves the REAL static JS the same JSON the FastAPI server would.
 *
 * The recreated screens load the tool's actual CSS + JS (copied verbatim from
 * src/schedule_forensics/web/static/). This file stands in for app.py: it intercepts
 * fetch("/api/...") and answers with a realistic mock session — a NASA-flavored launch
 * campaign loaded as three monthly IMS versions with a slipping finish and degrading
 * DCMA quality (the story the real tool is built to surface).
 *
 * Also provides SFBoot(): injects the real static scripts AFTER the DOM exists (they are
 * IIFEs that expect server-rendered HTML), then re-fires DOMContentLoaded for the ones
 * that defer (theme.js, sysmon.js), and neutralizes dead navigation (links/forms point at
 * server routes that do not exist here).
 */
"use strict";

/* globals the layout <head> normally sets */
window.SF_LANG = "en";
window.SF_I18N = {};

(function () {
  var STATIC = "src/schedule_forensics/web/static/";

  /* ── Mock session: “Meridian Lunar Cargo — Flight 3” launch campaign, 3 IMS versions ── */

  var DCMA_NAMES = [
    "Logic", "Leads", "Lags", "FS Relationships", "SS/FF Relationships", "SF Relationships",
    "Hard Constraints", "High Float", "Negative Float", "High Duration", "Invalid Dates",
    "Resources", "Missed Activities", "Critical Path Test", "CPLI", "BEI",
  ];
  function dcma(failNames, naNames) {
    return DCMA_NAMES.map(function (n) {
      var s = failNames.indexOf(n) >= 0 ? "FAIL" : (naNames || []).indexOf(n) >= 0 ? "NOT_APPLICABLE" : "PASS";
      return { name: n, status: s === "NOT_APPLICABLE" ? "NA" : s };
    });
  }

  var CARDS = [
    {
      key: "MLC-3 IMS 2026-04", name: "MLC-3 IMS 2026-04",
      source_file: "MLC3_IMS_2026-04.mpp", solvable: true,
      activities: 238, percent_complete: 41,
      critical_count: 24, critical_pct: 10,
      cpm_finish: "11/18/2026", finish_delta_days: 0,
      data_date: "04/03/2026",
      status_mix: { complete: 96, in_progress: 10, planned: 132 },
      dcma: dcma(["High Float"], []),
    },
    {
      key: "MLC-3 IMS 2026-05", name: "MLC-3 IMS 2026-05",
      source_file: "MLC3_IMS_2026-05.mpp", solvable: true,
      activities: 244, percent_complete: 52,
      critical_count: 30, critical_pct: 12,
      cpm_finish: "12/04/2026", finish_delta_days: 16,
      data_date: "05/01/2026",
      status_mix: { complete: 127, in_progress: 8, planned: 109 },
      dcma: dcma(["High Float", "Negative Float", "BEI"], []),
    },
    {
      key: "MLC-3 IMS 2026-06", name: "MLC-3 IMS 2026-06",
      source_file: "MLC3_IMS_2026-06.mpp", solvable: true,
      activities: 250, percent_complete: 60,
      critical_count: 36, critical_pct: 14,
      cpm_finish: "12/21/2026", finish_delta_days: 33,
      data_date: "06/05/2026",
      status_mix: { complete: 150, in_progress: 6, planned: 94 },
      dcma: dcma(["Logic", "High Float", "Negative Float", "Missed Activities", "CPLI", "BEI"], []),
    },
  ];

  window.SF_MOCK = { cards: CARDS };

  /* Ask-the-AI canned exchange (shape: ask.js) */
  var ASK_FACTS = [
    { text: "Computed finish moved from 11/18/2026 (IMS 2026-04) to 12/21/2026 (IMS 2026-06) — 33 calendar days later across two updates.",
      citations: [{ task: "MLC-3 Launch", uid: 9001 }] },
    { text: "36 of 250 activities (14%) are on the critical path in IMS 2026-06, up from 24 (10%) in IMS 2026-04.",
      citations: [{ task: "Vehicle — Integrated Vehicle Stack Complete", uid: 6120 }] },
    { text: "Negative float entered the network in IMS 2026-05: 5 activities at −4 wd, all on the fairing-encapsulation chain.",
      citations: [{ task: "LCM — Payload Fairing Encapsulation", uid: 5230 }, { task: "LCM — Acoustic Blanket Install", uid: 5228 }] },
    { text: "BEI fell to 0.87 in IMS 2026-06 (threshold ≥ 0.95): 21 activities baselined to finish by the data date have not completed.",
      citations: [{ task: "Stage 2 — Avionics Functional Test", uid: 4410 }] },
  ];

  /* /api/system telemetry (shape: sysmon.js) */
  function systemSnapshot() {
    var t = Date.now() / 1000;
    function wob(base, amp, f) { return Math.round(base + amp * Math.sin(t * f)); }
    return {
      cpu: { percent: wob(23, 9, 0.9), cores: 16, temp_c: wob(54, 4, 0.5) },
      memory: { percent: wob(46, 3, 0.3), used_gb: 14.7, total_gb: 32.0 },
      disk: { percent: 61, used_gb: 622.4, total_gb: 1024.0 },
      gpu: { name: "NVIDIA RTX A2000", util_percent: wob(12, 8, 1.3), mem_percent: 34, temp_c: wob(47, 3, 0.7) },
    };
  }

  /* ── fetch shim ─────────────────────────────────────────────────────────────────────── */
  var realFetch = window.fetch.bind(window);
  function json(data) {
    return Promise.resolve(new Response(JSON.stringify(data), {
      status: 200, headers: { "Content-Type": "application/json" },
    }));
  }

  window.SF_MOCK_ROUTES = {}; // per-page additions: exact path (before "?") → data | function(url)

  window.fetch = function (input, init) {
    var url = typeof input === "string" ? input : (input && input.url) || "";
    if (url.charAt(0) === "/") {
      var path = url.split("?")[0];
      var extra = window.SF_MOCK_ROUTES[path];
      if (extra !== undefined) return json(typeof extra === "function" ? extra(url) : extra);
      if (path === "/api/dashboard") return json({ cards: CARDS });
      if (path === "/api/system") return json(systemSnapshot());
      if (path === "/api/heartbeat" || path === "/api/shutdown") return json({ ok: true });
      if (path === "/api/translate") return json({ translations: {} });
      if (path === "/api/ask" || path.indexOf("/api/ask/") === 0) {
        return new Promise(function (resolve) {
          setTimeout(function () {
            resolve(new Response(JSON.stringify({
              answer: "The finish is slipping because the controlling chain through payload-fairing " +
                "encapsulation lost its margin: 12 activities went to negative float in IMS 2026-05, and " +
                "the June update added 33 calendar days to the computed finish while BEI fell to 0.87 — " +
                "the near-term plan is not being executed as written.",
              mode: "annotate",
              facts: ASK_FACTS,
            }), { status: 200, headers: { "Content-Type": "application/json" } }));
          }, 1400); // visible “AI working…” state, like a fast local model
        });
      }
      if (path === "/api/driving-path") {
        return json({
          answer: "Driving path to UID 9001 (MLC-3 Launch): 5230 Payload Fairing Encapsulation → " +
            "6080 Payload Mate to Adapter → 6120 Integrated Vehicle Stack Complete → 7040 Wet Dress " +
            "Rehearsal → 8010 Flight Readiness Review → 9001 MLC-3 Launch. Controlling slack 0d at every link.",
          facts: ASK_FACTS.slice(0, 2),
        });
      }
      // unknown /api → empty ok (page-specific routes are registered by each recreation)
      if (path.indexOf("/api/") === 0) return json({});
    }
    return realFetch(input, init);
  };

  /* ── boot: inject the real static scripts after the DOM is mounted ─────────────────── */
  window.SF_PAGE_MAP = window.SF_PAGE_MAP || {}; // "/route" → "file.dc.html" (filled as screens are built)

  function neutralize(root) {
    // Links to server routes: map to a recreated screen when we have one, else no-op.
    document.addEventListener("click", function (ev) {
      var a = ev.target && ev.target.closest ? ev.target.closest("a[href]") : null;
      if (!a) return;
      var href = a.getAttribute("href");
      if (!href || href.charAt(0) !== "/") return; // let #anchors and files through
      ev.preventDefault();
      var mapped = window.SF_PAGE_MAP[href.split("?")[0]];
      if (mapped) window.location.href = mapped;
    }, true);
    // Forms post to the server: swallow both the event and programmatic .submit().
    Array.prototype.forEach.call(document.querySelectorAll("form"), function (f) {
      f.addEventListener("submit", function (ev) { ev.preventDefault(); });
      try { f.submit = function () {}; } catch (e) { /* readonly on odd engines */ }
    });
  }

  window.SFBoot = function (scripts, done) {
    var i = 0;
    function next() {
      if (i >= scripts.length) {
        // theme.js / sysmon.js etc. registered DOMContentLoaded listeners after the real event —
        // re-fire it so their bindings run.
        document.dispatchEvent(new Event("DOMContentLoaded", { bubbles: true }));
        neutralize(document);
        if (done) done();
        return;
      }
      var s = document.createElement("script");
      s.src = STATIC + scripts[i++];
      s.onload = next;
      s.onerror = next;
      document.body.appendChild(s);
    }
    next();
  };
})();
