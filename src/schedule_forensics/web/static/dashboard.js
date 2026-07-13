/* Schedule Forensics — Dashboard health cards.
 *
 * Dependency-free (no CDN — air-gap posture). Fetches /api/dashboard and renders one health
 * card per loaded schedule: KPI stats, an activity status-mix bar, and a DCMA-14 verdict
 * ribbon — each with a legend and a one-line description. The whole card links to the full
 * report so the operator can dive in for the detail. Renders async so the landing page is
 * instant; an unschedulable file degrades to a flagged card.
 */
"use strict";

(function () {
  var box = document.getElementById("dashboardHealth");
  if (!box) return;

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function stat(label, value) {
    var c = el("div", "stat-card");
    c.appendChild(el("div", "stat-value", value));
    c.appendChild(el("div", "stat-label", label));
    return c;
  }
  function legend(items) {
    var row = el("div", "chart-legend");
    items.forEach(function (it) {
      var cell = el("span", "chart-legend-item");
      var sw = el("span", "chart-swatch");
      sw.style.background = it.color;
      cell.appendChild(sw);
      cell.appendChild(el("span", null, it.label));
      row.appendChild(cell);
    });
    return row;
  }
  function statusBar(mix, uids, fileKey) {
    mix = mix || {};
    uids = uids || {};
    var total = (mix.complete || 0) + (mix.in_progress || 0) + (mix.planned || 0);
    var bar = el("div", "dash-bar");
    if (total) {
      [["complete", "var(--ok)"], ["in_progress", "var(--warn)"], ["planned", "var(--accent)"]]
        .forEach(function (s) {
          var v = mix[s[0]] || 0;
          if (!v) return;
          var seg = el("span", "dash-seg");
          seg.style.width = (100 * v / total) + "%";
          seg.style.background = s[1];
          var label = s[0].replace("_", " ");
          seg.title = label + ": " + v;
          // click the segment to list its activities (the shared handler preventDefaults, so the
          // click does NOT also follow the card's <a> link)
          if (window.SFDrill) SFDrill.mark(seg, uids[s[0]], fileKey, "Status: " + label);
          bar.appendChild(seg);
        });
    }
    return bar;
  }

  fetch("/api/dashboard")
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (data) {
      var cards = data.cards || [];
      if (!cards.length) { box.textContent = "No schedules loaded."; return; }
      cards.forEach(function (c) {
        var card = el("a", "dash-card");
        card.href = "/analysis/" + encodeURIComponent(c.key);
        var head = el("div", "dash-head");
        head.appendChild(el("span", "dash-name", c.name));
        head.appendChild(el("span", "dash-open", "Open report →"));
        card.appendChild(head);
        if (c.source_file) card.appendChild(el("div", "muted dash-src", c.source_file));

        if (!c.solvable) {
          card.appendChild(el("p", "notice err",
            "Network can't be solved — open the report for the reason."));
          box.appendChild(card);
          return;
        }

        var grid = el("div", "stat-grid");
        grid.appendChild(stat("Activities", String(c.activities)));
        grid.appendChild(stat("% complete", c.percent_complete + "%"));
        grid.appendChild(stat("Critical", c.critical_count + " (" + c.critical_pct + "%)"));
        var fin = c.cpm_finish + (c.finish_delta_days != null
          ? " (" + (c.finish_delta_days > 0 ? "+" : "") + c.finish_delta_days + "d vs base)" : "");
        grid.appendChild(stat("Computed finish", fin));
        grid.appendChild(stat("Data date", c.data_date || "—"));
        card.appendChild(grid);

        card.appendChild(el("p", "chart-desc",
          "Activity status mix — share of activities complete / in progress / planned (not started)."));
        card.appendChild(statusBar(c.status_mix, c.status_mix_uids, c.key));
        card.appendChild(legend([
          { label: "Complete", color: "var(--ok)" },
          { label: "In progress", color: "var(--warn)" },
          { label: "Planned", color: "var(--accent)" },
        ]));

        var dcma = c.dcma || [];
        var pass = 0, fail = 0, na = 0;
        dcma.forEach(function (d) {
          if (d.status === "PASS") pass++; else if (d.status === "FAIL") fail++; else na++;
        });
        card.appendChild(el("p", "chart-desc",
          "DCMA 14-point checks at a glance — " + pass + " pass · " + fail + " fail · " + na +
          " n/a. Each chip is one check; click the card for the full audit with offending activities."));
        var ribbon = el("div", "dcma-ribbon");
        dcma.forEach(function (d) {
          var chip = el("span", "dcma-chip dcma-" + d.status.toLowerCase(), d.name);
          chip.title = d.name + ": " + d.status;
          ribbon.appendChild(chip);
        });
        card.appendChild(ribbon);
        card.appendChild(legend([
          { label: "Pass", color: "var(--ok)" },
          { label: "Fail", color: "var(--bad)" },
          { label: "N/A", color: "var(--muted)" },
        ]));

        box.appendChild(card);
      });
    })
    .catch(function () { box.textContent = "Failed to load the dashboard health summary."; });
})();
