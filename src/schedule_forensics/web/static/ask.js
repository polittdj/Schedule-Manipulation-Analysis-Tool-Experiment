/* Schedule Forensics — the Ask-the-AI panel every page carries (M18 "AI at full power").
 *
 * Scope: the whole workbook (multi-version cited facts) or one loaded schedule. Answers
 * may be model-interpreted (settings: AI answer mode) and are ALWAYS grounded by — and
 * shown with — the engine's computed, cited facts. The standing disclaimer is permanent:
 * AI can err — verify against citations. Dependency-free; nothing leaves the machine.
 */
"use strict";

(function () {
  var btn = document.getElementById("askBtn");
  if (!btn) return;

  function el(tag, attrs, kids) {
    var node = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "text") node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { node.appendChild(c); });
    return node;
  }

  function ask() {
    var out = document.getElementById("askOut");
    var input = document.getElementById("askInput");
    var q = input.value.trim();
    if (!q) return;
    var scopeEl = document.getElementById("askScope");
    var scope = scopeEl ? scopeEl.value : "";
    out.textContent = "Thinking locally…";
    var body = new URLSearchParams();
    body.set("question", q);
    var url = scope ? "/api/ask/" + encodeURIComponent(scope) : "/api/ask";
    fetch(url, { method: "POST", body: body })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        out.textContent = "";
        if (!res.ok) { out.textContent = res.j.error || "Could not answer."; return; }
        if (res.j.answer) {
          out.appendChild(el("p", { class: "ask-answer", text: res.j.answer }));
          out.appendChild(el("p", {
            class: "muted",
            text: res.j.mode === "interpretive"
              ? "AI can err — verify this answer against the cited facts below."
              : "Model-generated strictly from the cited facts below — verify against them.",
          }));
        } else {
          out.appendChild(el("p", {
            class: "muted",
            text: "No local model is active (or strict mode discarded its answer) — these are " +
              "the engine's cited facts that match your question:",
          }));
        }
        var ul = el("ul");
        (res.j.facts || []).forEach(function (f) {
          var cite = (f.citations || []).map(function (c) { return c.task + " (UID " + c.uid + ")"; }).join("; ");
          ul.appendChild(el("li", { text: f.text + (cite ? "  [" + cite + "]" : "") }));
        });
        out.appendChild(ul);
      })
      .catch(function () { out.textContent = "Could not answer."; });
  }

  btn.addEventListener("click", ask);
  document.getElementById("askInput").addEventListener("keydown", function (e) {
    if (e.key === "Enter") ask();
  });
})();
