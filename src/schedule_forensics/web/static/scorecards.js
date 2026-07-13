/* Schedule Forensics — Assessment Scorecards: on-demand reserve / buffer sizing.
 *
 * The NASA STAT / GAO-10 / SRA-readiness ribbons are server-rendered (they need no JS). This
 * script drives only the reserve card: it reads the committed finish date + iteration count,
 * fetches /api/scorecards/buffer for the selected version, and renders the reserve table (finish
 * and buffer-days at P50/P70/P80/P90) plus the confidence the committed date is met today.
 *
 * The Monte-Carlo runs server-side on demand (off the page-load path). Fully local — one fetch to
 * the app's own /api endpoint; no external asset, no framework (air-gap, Law 1).
 */
"use strict";

(function () {
  var form = document.getElementById("reserveForm");
  var out = document.getElementById("reserveOut");
  var run = document.getElementById("reserveRun");
  if (!form || !out || !run) return;

  var file = form.getAttribute("data-file") || "";

  function el(tag, text, cls) {
    var node = document.createElement(tag);
    if (text != null) node.textContent = String(text);
    if (cls) node.className = cls;
    return node;
  }

  function fmtDays(d) {
    return d > 0 ? d.toFixed(1) + " working days" : "none (committed date already beats it)";
  }

  function render(data) {
    out.textContent = "";
    var conf = Math.round((data.committed_confidence || 0) * 1000) / 10;
    var head = el("p");
    head.className = "page-takeaway";
    head.setAttribute("data-no-i18n", "");
    head.textContent =
      "Committed " + data.committed_date + " is met in " + conf + "% of runs — " +
      "reserve to reach P70: " + fmtDays(data.recommended_p70_days) +
      "; to reach P80: " + fmtDays(data.recommended_p80_days) + ".";
    out.appendChild(head);

    var note = el("p", null, "muted");
    note.textContent =
      "SRA over " + data.iterations + " iterations (" + data.label +
      "); deterministic finish " + data.deterministic_finish_date +
      ". Reserve = working days between the committed date and the finish at each confidence.";
    out.appendChild(note);

    var table = el("table");
    table.className = "scorecard-table";
    var hr = el("tr");
    ["Confidence", "Finish date", "Reserve needed"].forEach(function (h) {
      var th = el("th", h);
      th.setAttribute("scope", "col");
      hr.appendChild(th);
    });
    table.appendChild(hr);
    (data.rows || []).forEach(function (r) {
      var tr = el("tr");
      tr.appendChild(el("td", "P" + r.percentile));
      tr.appendChild(el("td", r.finish_date));
      tr.appendChild(el("td", fmtDays(r.reserve_days)));
      table.appendChild(tr);
    });
    out.appendChild(table);
  }

  function sizeReserve() {
    var date = (document.getElementById("reserveDate") || {}).value || "";
    var iters = (document.getElementById("reserveIters") || {}).value || "1000";
    if (!date) {
      out.textContent = "";
      out.appendChild(el("p", "Enter a committed finish date first.", "notice"));
      return;
    }
    out.textContent = "";
    out.appendChild(el("p", "Running the Monte-Carlo…", "muted"));
    run.disabled = true;
    var url =
      "/api/scorecards/buffer?file=" + encodeURIComponent(file) +
      "&committed=" + encodeURIComponent(date) +
      "&iterations=" + encodeURIComponent(iters);
    fetch(url)
      .then(function (resp) {
        return resp.json().then(function (body) {
          return { ok: resp.ok, body: body };
        });
      })
      .then(function (res) {
        run.disabled = false;
        if (!res.ok) {
          out.textContent = "";
          out.appendChild(el("p", (res.body && res.body.error) || "Could not size the reserve.", "notice err"));
          return;
        }
        render(res.body);
      })
      .catch(function () {
        run.disabled = false;
        out.textContent = "";
        out.appendChild(el("p", "The reserve request failed. Is the app still running?", "notice err"));
      });
  }

  run.addEventListener("click", sizeReserve);
})();
