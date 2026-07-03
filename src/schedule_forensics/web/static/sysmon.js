/* Schedule Forensics — live machine telemetry dock (CPU / RAM / disk / GPU / temps).
 *
 * Polls the LOCAL /api/system endpoint (loopback only — CSP connect-src 'self') every 2s and
 * renders compact chips that expand to detail cards on click. Off by default in the standard
 * themes, ON by default in the JARVIS theme; the choice persists in localStorage and is always
 * available from the dock's own show/hide button. Polling pauses when the tab is hidden.
 * Values a platform can't provide arrive as null and render as "—". Numbers are data-no-i18n.
 */
"use strict";

(function () {
  var KEY = "sf-sysmon"; // "on" | "off" | null (null = follow the theme default)
  var dock = null;
  var timer = null;
  var expanded = {};

  function pref() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function setPref(v) {
    try { localStorage.setItem(KEY, v); } catch (e) { /* storage unavailable */ }
  }
  function wanted() {
    var p = pref();
    if (p === "on") return true;
    if (p === "off") return false;
    return document.documentElement.getAttribute("data-theme") === "jarvis";
  }

  function fmt(v, suffix) {
    return v == null ? "—" : v + (suffix || "");
  }
  function level(pct) {
    if (pct == null) return "";
    if (pct >= 90) return "crit";
    if (pct >= 75) return "warn";
    return "";
  }

  function chip(id, label, hint) {
    var el = document.createElement("div");
    el.className = "sysmon-chip";
    el.id = "sm-" + id;
    el.setAttribute("role", "button");
    el.setAttribute("tabindex", "0");
    el.setAttribute("title", hint);
    el.innerHTML =
      '<span class="sm-label" data-no-i18n>' + label + "</span>" +
      '<span class="sm-bar"><i style="width:0%"></i></span>' +
      '<span class="sm-val" data-no-i18n>—</span>';
    function toggle() {
      expanded[id] = !expanded[id];
      var d = document.getElementById("smd-" + id);
      if (d) d.hidden = !expanded[id];
    }
    el.addEventListener("click", toggle);
    el.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
    });
    return el;
  }

  function detail(id, title) {
    var el = document.createElement("div");
    el.className = "sysmon-detail";
    el.id = "smd-" + id;
    el.hidden = true;
    el.innerHTML = "<h4>" + title + '</h4><div class="sm-body" data-no-i18n></div>';
    return el;
  }

  function setChip(id, pct, valText) {
    var el = document.getElementById("sm-" + id);
    if (!el) return;
    var bar = el.querySelector(".sm-bar");
    bar.className = "sm-bar " + level(pct);
    bar.firstChild.style.width = (pct == null ? 0 : Math.min(100, pct)) + "%";
    el.querySelector(".sm-val").textContent = valText;
  }

  function rows(pairs) {
    return pairs.map(function (p) {
      return '<div class="sm-row"><span>' + p[0] + "</span><span>" + p[1] + "</span></div>";
    }).join("");
  }

  function render(s) {
    setChip("cpu", s.cpu.percent, fmt(s.cpu.percent, "%"));
    setChip("ram", s.memory.percent, fmt(s.memory.percent, "%"));
    setChip("disk", s.disk.percent, fmt(s.disk.percent, "%"));
    var gpuPct = s.gpu.util_percent;
    setChip("gpu", gpuPct, gpuPct == null ? "—" : fmt(gpuPct, "%"));

    var bodies = {
      cpu: rows([
        ["Load", fmt(s.cpu.percent, "%")],
        ["Cores", fmt(s.cpu.cores)],
        ["Temperature", fmt(s.cpu.temp_c, " °C")],
      ]),
      ram: rows([
        ["Used", fmt(s.memory.used_gb, " GB")],
        ["Total", fmt(s.memory.total_gb, " GB")],
        ["Load", fmt(s.memory.percent, "%")],
      ]),
      disk: rows([
        ["Used", fmt(s.disk.used_gb, " GB")],
        ["Total", fmt(s.disk.total_gb, " GB")],
        ["Load", fmt(s.disk.percent, "%")],
      ]),
      gpu: rows([
        ["Device", s.gpu.name || "—"],
        ["Utilization", fmt(s.gpu.util_percent, "%")],
        ["VRAM", fmt(s.gpu.mem_percent, "%")],
        ["Temperature", fmt(s.gpu.temp_c, " °C")],
      ]),
    };
    Object.keys(bodies).forEach(function (id) {
      var d = document.getElementById("smd-" + id);
      if (d) d.querySelector(".sm-body").innerHTML = bodies[id];
    });
  }

  function poll() {
    if (document.hidden) return; // pause in background tabs
    fetch("/api/system").then(function (r) { return r.json(); }).then(render)
      .catch(function () { /* endpoint briefly unavailable — keep last values */ });
  }

  function start() {
    if (timer) return;
    poll();
    timer = setInterval(poll, 2000);
  }
  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
  }

  function build() {
    dock = document.createElement("div");
    dock.id = "sysmonDock";
    dock.setAttribute("data-no-i18n", "");
    [["cpu", "CPU", "Processor load — click to expand cores and temperature"],
     ["ram", "RAM", "Memory in use — click to expand totals"],
     ["gpu", "GPU", "Graphics utilization (NVIDIA) — click to expand VRAM and temperature"],
     ["disk", "DISK", "System drive usage — click to expand totals"]].forEach(function (c) {
      dock.appendChild(detail(c[0], c[1]));
      dock.appendChild(chip(c[0], c[1], c[2]));
    });
    var btn = document.createElement("button");
    btn.id = "sysmonToggle";
    btn.type = "button";
    btn.textContent = "◉ telemetry";
    btn.title = "Show or hide the live system telemetry dock";
    btn.addEventListener("click", function () {
      var on = dock.querySelector(".sysmon-chip").style.display !== "none";
      setPref(on ? "off" : "on");
      apply();
    });
    dock.appendChild(btn);
    document.body.appendChild(dock);
  }

  function apply() {
    var on = wanted();
    dock.querySelectorAll(".sysmon-chip,.sysmon-detail").forEach(function (el) {
      el.style.display = on ? "" : "none";
      if (!on) el.hidden = el.classList.contains("sysmon-detail");
    });
    if (on) start(); else stop();
  }

  document.addEventListener("DOMContentLoaded", function () {
    build();
    apply();
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden && wanted()) poll();
    });
    // re-apply when the theme button cycles into/out of JARVIS
    new MutationObserver(apply).observe(document.documentElement, {
      attributes: true, attributeFilter: ["data-theme"],
    });
  });
})();
