/* Schedule Forensics — the load/draw seam (R-09, ADR-0521).
 *
 * A fetch failure and a DRAW failure are different findings and must never print the same
 * sentence. Every fetch-driven page module used to be shaped like this:
 *
 *     fetch("/api/…")
 *       .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
 *       .then(function (d) { …builds the panel, draws the chart… })
 *       .catch(function () { box.textContent = <the module's LOAD sentence>; });
 *
 * This file deliberately carries NEITHER the load sentence nor the draw sentence as a literal:
 * the census that finds the sixteen consumers reads `web/static/*.js`, so a seam quoting the
 * literal it censuses counts ITSELF and the population goes to seventeen. The pre-commit hook
 * learned the same lesson (it must never write a signature literal in its own comments), and
 * `test_the_seam_never_quotes_the_literals_it_censuses` keeps this one honest.
 *
 * The terminal `.catch` is attached to the WHOLE chain, so it also covered the `.then` that
 * draws. When the draw threw — `SFChartFrame` not yet defined (CI-03 / ADR-0461), a shape the
 * renderer did not expect, a helper that regressed — the analyst was told the data failed to
 * LOAD. The data had arrived; a 200 was measured on every one of the sixteen modules while that
 * sentence was on screen. In a tool whose output is testimony, a true symptom with a false
 * explanation sends the reader to the wrong place.
 *
 * `SFLoad.drawn(build, report)` wraps the drawing callback. A throw inside `build` is caught HERE,
 * reported by `report` in the module's own words, and NOT re-thrown — so the chain's terminal
 * `.catch` never runs and never overwrites the draw sentence with the load sentence. What reaches
 * that terminal `.catch` afterwards is exactly what it always claimed: a transport or parse
 * failure.
 *
 * Deliberately SYNCHRONOUS only. Measured 2026-09-21 across all sixteen wrapped callbacks: none
 * returns a promise (no `return fetch(…)`, no `return x.then(…)`, no `return Promise.…`), so a
 * rejected thenable cannot slip past this try/catch today. A module that later returns a promise
 * from its drawing callback would bypass the seam — `test_render_throw_is_not_a_load_failure`
 * would keep passing while the page lied again, so add the thenable branch if that day comes.
 *
 * No build step, no dependency: emitted in the layout HEAD beside gantt.js / chartframe.js so the
 * seam is defined before any body script — or any callback a body script schedules — can run.
 */
(function () {
  "use strict";

  function log(message, err) {
    if (window.console && window.console.error) window.console.error("SFLoad: " + message, err);
  }

  /* Wrap a drawing callback. `build` receives the fetched payload; `report` receives the Error
   * and says, in the module's own words, that the DATA ARRIVED and the draw did not finish. */
  function drawn(build, report) {
    return function (payload) {
      try {
        return build(payload);
      } catch (err) {
        // the report must never itself become the failure the analyst sees
        try {
          report(err);
        } catch (reportErr) {
          log("the draw-failure report threw", reportErr);
        }
        // NOT re-thrown on purpose: re-throwing hands the chain's terminal .catch a draw error
        // and it would print the load sentence — the exact conflation this seam exists to end.
        log("the draw threw; the data had already arrived", err);
        return undefined;
      }
    };
  }

  window.SFLoad = { drawn: drawn };
})();
