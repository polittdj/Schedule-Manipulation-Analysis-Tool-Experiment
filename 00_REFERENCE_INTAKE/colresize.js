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

  // The page-wide AI status light is the header globe (globe.js): spins up + glows while a model
  // generates, red flash on failure. The operator could not tell if a slow 72B model was thinking
  // or stuck — now every page shows it, plus a live elapsed-seconds counter here in the panel.
  var globe = document.querySelector(".nasa-globe");
  var busyTimer = null;

  function setThinking(on) {
    if (globe) globe.classList.toggle("ai-thinking", !!on);
  }

  function flashError() {
    if (!globe) return;
    globe.classList.add("ai-error");
    setTimeout(function () { globe.classList.remove("ai-error"); }, 2600);
  }

  function startWorking(out) {
    setThinking(true);
    var t0 = Date.now();
    out.textContent = "";
    var line = el("p", { class: "ai-working" });
    line.appendChild(el("span", { class: "ai-dot", text: "✦" }));
    line.appendChild(document.createTextNode(" The local AI is working… "));
    var secs = el("span", { class: "muted ai-secs", text: "(0s)" });
    line.appendChild(secs);
    var hint = el("p", { class: "muted ai-hint" });
    out.appendChild(line);
    out.appendChild(hint);
    busyTimer = setInterval(function () {
      var s = Math.round((Date.now() - t0) / 1000);
      secs.textContent = "(" + s + "s)";
      if (s === 20) {
        hint.textContent = "A large local model (e.g. llama3.1:70b / qwen2.5:72b) can take several "
          + "minutes for its first answer — it is working, not stuck (the spinning globe above is the "
          + "live indicator). Smaller models like qwen2.5:7b answer in seconds.";
      }
    }, 1000);
    return function stop() {
      if (busyTimer) { clearInterval(busyTimer); busyTimer = null; }
      setThinking(false);
      return Math.round((Date.now() - t0) / 1000);
    };
  }

  function renderFacts(out, facts) {
    var ul = el("ul");
    (facts || []).forEach(function (f) {
      var cite = (f.citations || []).map(function (c) {
        return c.task + " (UID " + c.uid + ")";
      }).join("; ");
      ul.appendChild(el("li", { text: f.text + (cite ? "  [" + cite + "]" : "") }));
    });
    out.appendChild(ul);
  }

  // One-click DETERMINISTIC driving path to a UID — straight from the engine, no model involved
  // (the operator hit the model getting this wrong; this path can't).
  function drivingPath() {
    var out = document.getElementById("askOut");
    var uidEl = document.getElementById("drivePathUid");
    var uid = uidEl ? uidEl.value.trim() : "";
    if (!uid) return;
    var scopeEl = document.getElementById("askScope");
    var scope = scopeEl ? scopeEl.value : "";
    out.textContent = "Computing the driving path…";
    fetch("/api/driving-path?uid=" + encodeURIComponent(uid) +
          "&scope=" + encodeURIComponent(scope))
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        out.textContent = "";
        if (!res.ok) { out.textContent = res.j.error || "Could not compute."; return; }
        out.appendChild(el("p", { class: "ask-answer", text: res.j.answer }));
        out.appendChild(el("p", {
          class: "muted", text: "Engine result — exact, computed directly (no AI).",
        }));
        renderFacts(out, res.j.facts);
      })
      .catch(function () { out.textContent = "Could not compute the driving path."; });
  }

  function ask() {
    var out = document.getElementById("askOut");
    var input = document.getElementById("askInput");
    var q = input.value.trim();
    if (!q) return;
    var scopeEl = document.getElementById("askScope");
    var scope = scopeEl ? scopeEl.value : "";
    var stop = startWorking(out);
    var body = new URLSearchParams();
    body.set("question", q);
    var url = scope ? "/api/ask/" + encodeURIComponent(scope) : "/api/ask";
    fetch(url, { method: "POST", body: body })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        var took = stop();
        out.textContent = "";
        if (!res.ok) {
          flashError();
          out.textContent = res.j.error || "Could not answer.";
          return;
        }
        if (res.j.answer) {
          out.appendChild(el("p", { class: "ask-answer", text: res.j.answer }));
          out.appendChild(el("p", {
            class: "muted",
            text: res.j.mode === "interpretive"
              ? "AI can err — verify this answer against the cited facts below."
              : "Model-generated strictly from the cited facts below — verify against them.",
          }));
        } else {
          var note = el("p", { class: "muted" });
          note.appendChild(document.createTextNode(
            "No local model is active (or strict mode discarded its answer) — these are the " +
            "engine's cited facts that match your question. For a full written analysis, "));
          note.appendChild(el("a", { href: "/settings" }, [document.createTextNode("enable a local Ollama model in AI Settings")]));
          note.appendChild(document.createTextNode("."));
          out.appendChild(note);
        }
        if (res.j.second_answer) {
          out.appendChild(el("p", { class: "muted", text: "Second model (" + (res.j.second_model || "?") + "):" }));
          out.appendChild(el("p", { class: "ask-answer ask-second", text: res.j.second_answer }));
        }
        if (res.j.agreement) {
          out.appendChild(el("p", {
            class: res.j.agreement.indexOf("DIFFER") >= 0 ? "ask-agreement differ" : "ask-agreement",
            text: res.j.agreement,
          }));
        }
        if (res.j.answer) {
          out.appendChild(el("p", { class: "muted ai-took", text: "Answered locally in " + took + "s." }));
        }
        renderFacts(out, res.j.facts);
      })
      .catch(function () {
        stop();
        flashError();
        out.textContent = "Could not answer (the local model may have timed out — raise the "
          + "generation timeout in AI Settings, or use a smaller, faster model).";
      });
  }

  btn.addEventListener("click", ask);
  document.getElementById("askInput").addEventListener("keydown", function (e) {
    if (e.key === "Enter") ask();
  });
  var dpBtn = document.getElementById("drivePathBtn");
  if (dpBtn) dpBtn.addEventListener("click", drivingPath);
  var dpUid = document.getElementById("drivePathUid");
  if (dpUid) dpUid.addEventListener("keydown", function (e) {
    if (e.key === "Enter") drivingPath();
  });
})();
