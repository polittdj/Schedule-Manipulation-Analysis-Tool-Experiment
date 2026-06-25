/* Schedule Forensics — AI Settings live model pickers (fully local; no network beyond this host).
 *
 * Two conveniences over the AI config form:
 *
 *  1) LIVE MODEL DROPDOWNS. When the operator changes the backend or its endpoint, probe that LOCAL
 *     server (GET /api/ai/models — loopback-only, fail-closed) and repopulate the Model dropdown
 *     with the ids it actually serves. This is what makes the OpenAI-compatible backend (LM Studio /
 *     llamafile / vLLM) work in one flow: you pick the exact model id the server reports instead of
 *     guessing or carrying over an Ollama name. The cross-check second model is a live dropdown too.
 *
 *  2) CROSS-CHECK AUTOFILL. Turning the cross-check on copies the primary model id into the (still
 *     blank) second-model box so a one-click cross-check works; it never clobbers a chosen value.
 *
 * Dependency-free, same-origin only (air-gap): the only fetch is to /api/ai/models on this host.
 */
"use strict";

(function () {
  function $(id) { return document.getElementById(id); }

  function kindOf(v) { return v === "openai" ? "openai" : "ollama"; }

  function endpointFor(kind) {
    var el = kind === "openai"
      ? document.querySelector("input[name=openai_endpoint]")
      : document.querySelector("input[name=endpoint]");
    return el ? el.value : "";
  }

  // Repopulate a <select> with the served model ids, keeping the current value selected (added and
  // flagged "not served" when the server doesn't list it). A blank option = the server's default.
  function fill(select, models, statusEl, reason) {
    if (!select) return;
    var cur = select.value;
    select.innerHTML = "";
    var blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "(server default / loaded model)";
    select.appendChild(blank);
    var served = false;
    models.forEach(function (m) {
      var o = document.createElement("option");
      o.value = m;
      o.textContent = m;
      if (m === cur) { o.selected = true; served = true; }
      select.appendChild(o);
    });
    if (cur && !served) {
      var o2 = document.createElement("option");
      o2.value = cur;
      o2.textContent = cur + " — not installed";
      o2.selected = true;
      select.appendChild(o2);
    } else if (!cur) {
      blank.selected = true;
    }
    if (statusEl) {
      statusEl.textContent = models.length
        ? models.length + " model(s) available"
        : (reason ? "not reachable: " + reason : "no models loaded");
    }
  }

  function probe(kind, select, statusEl, then) {
    if (!select) return;
    if (statusEl) statusEl.textContent = "checking…";
    fetch("/api/ai/models?kind=" + encodeURIComponent(kind) +
          "&endpoint=" + encodeURIComponent(endpointFor(kind)))
      .then(function (r) { return r.json(); })
      .then(function (j) {
        fill(select, (j && j.models) || [], statusEl, j && j.reason);
        if (then) then();
      })
      .catch(function () { if (statusEl) statusEl.textContent = "check failed"; });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var backendSel = $("backendSel");
    var primaryModel = $("primaryModel");
    var secondSel = $("secondBackend");
    var secondModel = $("secondModel");
    var primaryStatus = $("primaryModelStatus");
    var secondStatus = $("secondModelStatus");
    var ollamaEp = document.querySelector("input[name=endpoint]");
    var openaiEp = document.querySelector("input[name=openai_endpoint]");

    function refreshPrimary() {
      var v = backendSel ? backendSel.value : "ollama";
      if (v !== "ollama" && v !== "openai") {
        if (primaryStatus) primaryStatus.textContent = "(no local model list for this backend)";
        return;
      }
      probe(kindOf(v), primaryModel, primaryStatus);
    }

    // Pick the second model the same way, then autofill it from the primary if still blank.
    function refreshSecond() {
      var v = secondSel ? secondSel.value : "none";
      if (v !== "ollama" && v !== "openai") {
        if (secondStatus) secondStatus.textContent = "off";
        return;
      }
      probe(kindOf(v), secondModel, secondStatus, function () {
        if (secondModel && secondModel.value.trim() === "" && primaryModel) {
          var p = (primaryModel.value || "").trim();
          if (p) {
            // select the primary id if the server serves it, else add it as a chosen option
            var match = Array.prototype.some.call(secondModel.options, function (o) {
              if (o.value === p) { o.selected = true; return true; }
              return false;
            });
            if (!match) {
              var o = document.createElement("option");
              o.value = p; o.textContent = p; o.selected = true;
              secondModel.appendChild(o);
            }
          }
        }
      });
    }

    if (backendSel) backendSel.addEventListener("change", refreshPrimary);
    if (secondSel) secondSel.addEventListener("change", refreshSecond);
    if (ollamaEp) {
      ollamaEp.addEventListener("change", function () { refreshPrimary(); refreshSecond(); });
    }
    if (openaiEp) {
      openaiEp.addEventListener("change", function () { refreshPrimary(); refreshSecond(); });
    }
    var refreshBtn = $("refreshModels");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function (e) {
        e.preventDefault();
        refreshPrimary();
        refreshSecond();
      });
    }
  });
})();
