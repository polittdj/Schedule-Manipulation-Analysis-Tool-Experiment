/* Schedule Forensics — /groups value picker.
 *
 * Progressive enhancement for the Groups & Filters page: when a filter row's FIELD is chosen, an
 * MS-Project-style value dropdown (SFChecklist — checkboxes with All / None + search) is mounted
 * from that field's actual distinct values (/api/group-values for the selected version). The
 * checked values are written into hidden value{i} inputs the form submits. The form still works
 * with JS disabled (the server-rendered hidden inputs round-trip the current selection).
 * Dependency-free; nothing leaves the machine.
 */
"use strict";

(function () {
  var form = document.querySelector("form.group-form");
  if (!form || !window.SFChecklist) return;

  function currentVersion() {
    var sel = form.querySelector("select[name=version]");
    return (sel && sel.value) || form.getAttribute("data-version") || "";
  }

  function setHidden(box, i, values) {
    box.textContent = "";
    values.forEach(function (v) {
      var inp = document.createElement("input");
      inp.type = "hidden";
      inp.name = "value" + i;
      inp.value = v;
      box.appendChild(inp);
    });
  }

  function mountRow(row) {
    var i = row.getAttribute("data-row");
    var select = row.querySelector("select.gf-field");
    var mount = row.querySelector(".gf-values");
    var hidden = row.querySelector(".gf-hidden");
    if (!select || !mount || !hidden) return;

    function build(field, preselected) {
      mount.textContent = "";
      if (!field) { setHidden(hidden, i, []); return; }
      var url = "/api/group-values?version=" + encodeURIComponent(currentVersion()) +
        "&field=" + encodeURIComponent(field);
      fetch(url)
        .then(function (r) { return r.ok ? r.json() : { values: [] }; })
        .then(function (j) {
          var values = j.values || [];
          // a subset preselection restores the saved filter; null/empty = all selected
          var selectedSet = preselected && preselected.length ? new Set(preselected) : null;
          function chosen(set) {
            return set ? values.filter(function (v) { return set.has(v); }) : values.slice();
          }
          var node = window.SFChecklist.filter({
            values: values,
            selected: selectedSet,
            label: "Values",
            title: "Choose values to filter by",
            onChange: function (set) { setHidden(hidden, i, chosen(set)); },
          });
          mount.appendChild(node);
          setHidden(hidden, i, chosen(selectedSet)); // initialise to the current selection
        })
        .catch(function () { /* leave hidden inputs as server-rendered on fetch failure */ });
    }

    var pre = [];
    try { pre = JSON.parse(row.getAttribute("data-selected") || "[]"); } catch (e) { pre = []; }
    if (select.value) build(select.value, pre);
    // changing the field starts a fresh (all-selected) value list for that row
    select.addEventListener("change", function () { build(select.value, []); });
  }

  var rows = form.querySelectorAll(".group-row");
  rows.forEach(mountRow);

  // changing the version re-pulls every row's values for that version
  var versionSel = form.querySelector("select[name=version]");
  if (versionSel) {
    versionSel.addEventListener("change", function () {
      rows.forEach(function (row) {
        var s = row.querySelector("select.gf-field");
        if (s && s.value) s.dispatchEvent(new Event("change"));
      });
    });
  }
})();
