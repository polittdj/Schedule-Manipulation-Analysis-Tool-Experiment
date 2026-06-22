/* Schedule Forensics — AI Settings conveniences (fully local; no network).
 *
 * Auto-populates the cross-check "second model" id when the operator turns the
 * cross-check on: picking a second backend copies the primary model id into the
 * (empty) second-model box so a one-click cross-check works out of the gate. The
 * value stays editable — clear it or type another model (e.g. qwen2.5:14b) to run
 * a genuinely different second opinion. Never overwrites a value the operator
 * already typed.
 */
"use strict";

(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var secondBackend = document.getElementById("secondBackend");
    var secondModel = document.getElementById("secondModel");
    var primaryModel = document.getElementById("primaryModel");
    if (!secondBackend || !secondModel || !primaryModel) return;

    function primaryValue() {
      // works for both the <select> (installed models) and <input> (free text) variants
      return (primaryModel.value || "").trim();
    }

    secondBackend.addEventListener("change", function () {
      // only when turning the cross-check ON, and only into an empty box (never clobber input)
      if (secondBackend.value !== "none" && secondModel.value.trim() === "") {
        secondModel.value = primaryValue();
      }
    });
  });
})();
