/* Schedule Forensics — progressive AI polish (keeps heavy pages from blocking on the model).
 *
 * The Risks and Executive-Briefing pages render their full, engine-computed (deterministic) content
 * server-side and open INSTANTLY. Any element carrying `data-ai-endpoint` is then upgraded in the
 * background: this fetches that local endpoint, and if the server returns {polished:true, html},
 * swaps the element's content for the local-AI-interpreted version. A slow or absent model never
 * blocks the page (the synchronous on-load generation used to make these pages "not open" on big
 * workbooks); on failure the engine read simply stays. Dependency-free, same-origin only (air-gap).
 */
"use strict";

(function () {
  var nodes = document.querySelectorAll("[data-ai-endpoint]");
  if (!nodes.length) return;
  nodes.forEach(function (node) {
    var url = node.getAttribute("data-ai-endpoint");
    if (!url) return;
    var status = document.createElement("div");
    status.className = "ai-polish-status";
    status.textContent = "✦ Interpreting with the local AI…";
    node.parentNode.insertBefore(status, node);
    fetch(url)
      .then(function (r) {
        return r.ok ? r.json() : Promise.reject(r.status);
      })
      .then(function (d) {
        if (d && d.polished && typeof d.html === "string") {
          node.innerHTML = d.html;
          status.textContent = "✦ Interpreted by the local AI — verify against the citations.";
        } else {
          // no local model active (or nothing to add) — keep the engine read, drop the notice
          if (status.parentNode) status.parentNode.removeChild(status);
        }
      })
      .catch(function () {
        status.textContent = "Local-AI interpretation unavailable — showing the engine read.";
      });
  });
})();
