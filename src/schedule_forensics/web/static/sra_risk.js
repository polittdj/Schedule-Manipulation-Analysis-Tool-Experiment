/* Schedule Forensics — unified risk register: client-side days <-> % auto-derivation.
 *
 * A risk is entered ONCE with two magnitudes for the same event: an additive impact in DAYS (the SSI
 * model) and a multiplicative % uplift (the legacy model). The operator types one; this derives the
 * other from the affected tasks' AVERAGE remaining duration (window.SF_REMAIN_DAYS = uid -> remaining
 * working days), so the two magnitudes produce the same total schedule impact across the affected set:
 *
 *     pct = days / avg_remaining * 100      days = pct / 100 * avg_remaining
 *
 * Typing in a field LOCKS it (a hidden flag tells the server to use it verbatim for that model);
 * clearing it unlocks it. Changing the affected UIDs re-derives the unlocked field. The server mirrors
 * this exact math (_reconcile_magnitudes) so the JS-off / Load path agrees. Dependency-free, air-gap-safe.
 */
"use strict";

(function () {
  var form = document.getElementById("riskForm");
  if (!form) return;
  var _remEl = document.getElementById("sfRemainDays");
  var rem = {};
  if (_remEl) { try { rem = JSON.parse(_remEl.textContent || "{}"); } catch (e) { rem = {}; } }
  var daysEl = document.getElementById("riskDays");
  var pctEl = document.getElementById("riskPct");
  var affEl = document.getElementById("riskAffected");
  var daysLock = document.getElementById("riskDaysLocked");
  var pctLock = document.getElementById("riskPctLocked");
  if (!daysEl || !pctEl || !affEl || !daysLock || !pctLock) return;

  function avgRemaining() {
    var sum = 0,
      n = 0;
    affEl.value.split(/[\s,]+/).forEach(function (u) {
      if (!u) return;
      var d = rem[u];
      if (typeof d === "number" && isFinite(d)) {
        sum += d;
        n += 1;
      }
    });
    return n ? sum / n : 0;
  }
  function num(el) {
    var v = parseFloat(el.value);
    return isFinite(v) ? v : null;
  }
  function round2(x) {
    return Math.round(x * 100) / 100;
  }

  // derive the UNLOCKED magnitude from the LOCKED one (does nothing if both are locked or none is)
  function derive() {
    var avg = avgRemaining();
    var d = num(daysEl),
      p = num(pctEl);
    var dLocked = daysLock.value === "1",
      pLocked = pctLock.value === "1";
    if (avg <= 0) {
      // no derivation basis: CLEAR the unlocked field instead of leaving a stale derived value
      // that would post as if freshly derived (audit L4)
      if (dLocked && !pLocked) pctEl.value = "";
      else if (pLocked && !dLocked) daysEl.value = "";
      return;
    }
    if (dLocked && !pLocked && d !== null) {
      pctEl.value = round2((d / avg) * 100);
    } else if (pLocked && !dLocked && p !== null) {
      daysEl.value = round2((p / 100) * avg);
    }
  }

  daysEl.addEventListener("input", function () {
    daysLock.value = daysEl.value.trim() === "" ? "" : "1"; // typing locks days; clearing unlocks
    derive();
  });
  pctEl.addEventListener("input", function () {
    pctLock.value = pctEl.value.trim() === "" ? "" : "1"; // typing locks %; clearing unlocks
    derive();
  });
  affEl.addEventListener("input", derive); // re-fit the unlocked magnitude to the new affected set
})();
