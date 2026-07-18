/* Schedule Forensics — /groups value dropdown.
 *
 * Progressive enhancement for the Groups & Filters page: each filter row is a simple alphabetical
 * FIELD dropdown + VALUE dropdown (operator 2026-07-17, replacing the MS-Project checkbox popup).
 * The server renders both selects (so the current selection round-trips and the form works with JS
 * disabled); this script only repopulates the VALUE menu from the field's actual distinct values
 * (/api/group-values, already A–Z) when the FIELD or the preview VERSION changes.
 * Dependency-free; nothing leaves the machine.
 */
"use strict";

(function () {
  var form = document.querySelector("form.group-form");
  if (!form) return;

  function currentVersion() {
    var sel = form.querySelector("select[name=version]");
    return (sel && sel.value) || form.getAttribute("data-version") || "";
  }

  // Fill a value <select> with "(any value)" + the given values (A–Z from the API), keeping `chosen`
  // selected if it is still one of them.
  function fill(valsel, values, chosen) {
    valsel.textContent = "";
    var any = document.createElement("option");
    any.value = "";
    any.textContent = "(any value)";
    valsel.appendChild(any);
    values.forEach(function (v) {
      var o = document.createElement("option");
      o.value = v;
      o.textContent = v;
      if (v === chosen) o.selected = true;
      valsel.appendChild(o);
    });
  }

  // Re-pull `field`'s values for the current version and repaint `valsel`. `keep` retains the
  // current choice (version change); a fresh field starts at "(any value)".
  function refill(field, valsel, keep) {
    var f = field.value;
    var want = keep ? valsel.value : "";
    if (!f) {
      fill(valsel, [], "");
      return;
    }
    var url = "/api/group-values?version=" + encodeURIComponent(currentVersion()) +
      "&field=" + encodeURIComponent(f);
    fetch(url)
      .then(function (r) { return r.ok ? r.json() : { values: [] }; })
      .then(function (j) { fill(valsel, j.values || [], want); })
      .catch(function () { /* leave the server-rendered options on fetch failure */ });
  }

  var rows = Array.prototype.slice.call(form.querySelectorAll(".group-row"));
  rows.forEach(function (row) {
    var field = row.querySelector("select.gf-field");
    var valsel = row.querySelector("select.gf-valsel");
    if (!field || !valsel) return;
    // the server already rendered the options for a pre-selected field; only refetch on change
    field.addEventListener("change", function () { refill(field, valsel, false); });
  });

  // changing the preview version re-pulls every row's values for that version (keeping choices)
  var versionSel = form.querySelector("select[name=version]");
  if (versionSel) {
    versionSel.addEventListener("change", function () {
      rows.forEach(function (row) {
        var field = row.querySelector("select.gf-field");
        var valsel = row.querySelector("select.gf-valsel");
        if (field && valsel && field.value) refill(field, valsel, true);
      });
    });
  }
})();
