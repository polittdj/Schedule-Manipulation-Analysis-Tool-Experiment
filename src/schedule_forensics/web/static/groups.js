/* Schedule Forensics — /groups value autocomplete.
 *
 * Progressive enhancement for the Groups & Filters page: when a filter row's FIELD is chosen,
 * each value input's <datalist> is filled with that field's actual distinct values (from
 * /api/group-values for the selected version), so the operator picks a real value instead of
 * typing a code blind. The form still works with JS disabled. Dependency-free; nothing leaves
 * the machine.
 */
"use strict";

(function () {
  var form = document.querySelector("form.group-form");
  if (!form) return;

  function currentVersion() {
    var sel = form.querySelector("select[name=version]");
    return (sel && sel.value) || form.getAttribute("data-version") || "";
  }

  function fillDatalist(field, listEl) {
    listEl.textContent = "";
    if (!field) return;
    var url = "/api/group-values?version=" + encodeURIComponent(currentVersion()) +
      "&field=" + encodeURIComponent(field);
    fetch(url)
      .then(function (r) { return r.ok ? r.json() : { values: [] }; })
      .then(function (j) {
        (j.values || []).forEach(function (v) {
          var opt = document.createElement("option");
          opt.value = v;
          listEl.appendChild(opt);
        });
      })
      .catch(function () { /* leave the datalist empty on failure — the input still works */ });
  }

  function rowOf(select) {
    var row = select.closest(".group-row");
    return row && row.querySelector("input.gf-value");
  }

  var selects = form.querySelectorAll("select.gf-field");
  selects.forEach(function (select) {
    var input = rowOf(select);
    if (!input) return;
    var listEl = document.getElementById(input.getAttribute("list"));
    function refresh() { if (listEl) fillDatalist(select.value, listEl); }
    select.addEventListener("change", refresh);
    if (select.value) refresh(); // a pre-selected field (from the query string) fills immediately
  });

  // changing the version re-pulls every row's values for that version
  var versionSel = form.querySelector("select[name=version]");
  if (versionSel) {
    versionSel.addEventListener("change", function () {
      selects.forEach(function (select) {
        var input = rowOf(select);
        var listEl = input && document.getElementById(input.getAttribute("list"));
        if (listEl) fillDatalist(select.value, listEl);
      });
    });
  }
})();
