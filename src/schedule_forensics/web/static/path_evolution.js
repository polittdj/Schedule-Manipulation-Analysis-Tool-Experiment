/* Schedule Forensics — Critical-Path Evolution stepper (M18 item 7).
 *
 * Dependency-free (no CDN — air-gap posture). A Bow-Wave-style Prev/Next/Auto-play stepper
 * over /api/evolution: each frame is one version's critical path, with activities that
 * entered the path since the prior version highlighted, those that left listed struck
 * through, and a callout for the finish movement + schedule-optics signals.
 */
"use strict";

(function () {
  var box = document.getElementById("evoChart");
  if (!box) return;

  var data = null, index = 0, timer = null;

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function name(snap, uid) {
    return snap.names[String(uid)] || ("UID " + uid);
  }

  function render() {
    var snap = data.snapshots[index];
    document.getElementById("evoLabel").textContent =
      (index + 1) + " / " + data.snapshots.length + " — " + snap.label;
    box.innerHTML = "";

    // callout: finish + movement + optics
    var callout = el("div", "ev-callout");
    var move = snap.finish_delta_days;
    var moveText =
      move == null ? "" :
      move > 0 ? " (slipped " + move + "d)" :
      move < 0 ? " (pulled in " + (-move) + "d)" : " (no move)";
    callout.appendChild(el("span", "ev-finish", "Project finish: " + snap.project_finish + moveText));
    var sig = el("span", "ev-signals");
    var bits = [
      snap.entered.length + " entered",
      snap.left.length + " left",
      snap.duration_changed.length + " duration-changed on path",
    ];
    if (snap.shortened_on_path.length) bits.push(snap.shortened_on_path.length + " shortened on path");
    if (snap.removed_logic_count) bits.push(snap.removed_logic_count + " logic links removed");
    sig.textContent = bits.join(" · ");
    // a path shedding work while the finish holds/improves is the red-flag combination
    if ((snap.shortened_on_path.length || snap.removed_logic_count || snap.left.length) &&
        move != null && move <= 0) {
      sig.classList.add("ev-flag");
    }
    callout.appendChild(sig);
    box.appendChild(callout);

    // critical path: entered (green) / stayed (grey), with a duration badge
    var enteredSet = {}, durSet = {};
    snap.entered.forEach(function (u) { enteredSet[u] = 1; });
    snap.duration_changed.forEach(function (u) { durSet[u] = 1; });
    var list = el("ul", "ev-list");
    snap.critical.forEach(function (uid) {
      var li = el("li", "ev-item " + (enteredSet[uid] ? "ev-entered" : "ev-stayed"));
      li.appendChild(el("span", "ev-uid", "UID " + uid));
      li.appendChild(el("span", "ev-name", name(snap, uid)));
      if (durSet[uid]) li.appendChild(el("span", "ev-badge", "▲dur"));
      list.appendChild(li);
    });
    box.appendChild(el("h3", null, "Critical path — " + snap.critical.length + " activities"));
    box.appendChild(list);

    // activities that left the path since the prior version
    if (snap.left.length) {
      box.appendChild(el("h3", null, "Left the critical path (" + snap.left.length + ")"));
      var leftList = el("ul", "ev-list");
      snap.left.forEach(function (uid) {
        var li = el("li", "ev-item ev-left");
        li.appendChild(el("span", "ev-uid", "UID " + uid));
        li.appendChild(el("span", "ev-name", name(snap, uid)));
        leftList.appendChild(li);
      });
      box.appendChild(leftList);
    }
  }

  function step(delta) {
    index = (index + delta + data.snapshots.length) % data.snapshots.length;
    render();
  }

  function stopAuto() {
    if (timer) { clearInterval(timer); timer = null; }
    document.getElementById("evoPlay").textContent = "▶ Auto-play";
  }

  function toggleAuto() {
    if (timer) { stopAuto(); return; }
    document.getElementById("evoPlay").textContent = "⏸ Stop";
    timer = setInterval(function () { step(1); }, 1800);
  }

  fetch("/api/evolution")
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      data = d;
      render();
      document.getElementById("prevEvo").addEventListener("click", function () { stopAuto(); step(-1); });
      document.getElementById("nextEvo").addEventListener("click", function () { stopAuto(); step(1); });
      document.getElementById("evoPlay").addEventListener("click", toggleAuto);
    })
    .catch(function () { box.textContent = "Failed to load the path-evolution data."; });
})();
