/* Schedule Forensics — ONE tooltip per hover, with a 1.5s hover-intent delay (ADR-0286).
 *
 * The tool grew two tooltip families: the styled CSS callouts (``data-sf-hint`` and the
 * ``.dcma-tip`` sibling box) and the browser's own native tooltip from a ``title=`` attribute.
 * Several triggers carried BOTH — e.g. the DCMA-14 check name renders a rich ``.dcma-tip`` AND a
 * plain-text ``title=`` (kept as a no-CSS fallback) — so one hover produced two overlapping boxes
 * (operator bug report, screenshot on the /analysis DCMA table).
 *
 * This module enforces a single tooltip everywhere, with no per-call-site edits:
 *
 *   1. A trigger that ALREADY has a custom tooltip gets its ``title`` moved to ``data-sf-title``.
 *      The text is preserved (exports, no-CSS readers, and assistive tech that reads the
 *      ``aria-describedby`` target still see it) but the browser no longer paints its own box.
 *   2. A plain ``title`` on an element that can host a pseudo-element is PROMOTED to
 *      ``data-sf-hint``, so it renders as the same styled callout and obeys the same delay
 *      instead of the OS tooltip's own uncontrollable timing. Replaced/void elements (inputs,
 *      selects, images, svg, iframes …) cannot host ``::after``, so they keep their native
 *      ``title`` — still exactly one tooltip.
 *
 * The delay is CSS (``--sf-tip-delay``) for both CSS families; the JS-positioned floating tip in
 * app.js reads ``window.SF_TIP_DELAY_MS`` so every surface waits the same 1.5s. Because the CSS
 * delay is a ``transition-delay``, moving the cursor away before it elapses cancels the reveal —
 * the tooltip only appears after the pointer rests on the target for the full interval.
 *
 * Runs on load AND on DOM insertions: the charts, SRA/SSI tables and trend drills are rendered
 * client-side after page load, so newly built triggers are normalised as they appear.
 */
(function () {
  "use strict";

  window.SF_TIP_DELAY_MS = 1500;

  /* Elements that cannot render a ::after pseudo-element — a promoted hint would be invisible,
     so these keep their native title (still a single tooltip). */
  var NO_PSEUDO = /^(INPUT|SELECT|TEXTAREA|OPTION|OPTGROUP|IMG|SVG|PATH|CANVAS|IFRAME|BR|HR|AREA|EMBED|OBJECT|VIDEO|AUDIO|TRACK|SOURCE|COL|COLGROUP)$/;

  function hasCustomTip(node) {
    if (node.hasAttribute("data-sf-hint")) return true;
    var cl = node.classList;
    if (cl && (cl.contains("dcma-metric") || cl.contains("viz-hint"))) return true;
    var next = node.nextElementSibling;
    return !!(next && next.classList && next.classList.contains("dcma-tip"));
  }

  function normalise(node) {
    var title = node.getAttribute("title");
    if (title === null) return;
    if (hasCustomTip(node)) {
      // (1) a custom tooltip already covers this trigger — retire the native one.
      node.setAttribute("data-sf-title", title);
      node.removeAttribute("title");
      return;
    }
    if (NO_PSEUDO.test(node.tagName)) return; // (2b) cannot host ::after — leave it native
    if (!title.trim()) return;
    // (2a) promote to the shared styled callout so it matches every other tooltip.
    node.setAttribute("data-sf-hint", title);
    node.setAttribute("data-sf-title", title);
    node.removeAttribute("title");
  }

  function scan(root) {
    if (root.nodeType !== 1) return;
    if (root.hasAttribute && root.hasAttribute("title")) normalise(root);
    var nodes = root.querySelectorAll ? root.querySelectorAll("[title]") : [];
    for (var i = 0; i < nodes.length; i++) normalise(nodes[i]);
  }

  function boot() {
    scan(document.body);
    if (typeof MutationObserver !== "function") return;
    // Only walk what was actually inserted — a full-document rescan on every mutation is far too
    // expensive on the 2,000-row activity grids.
    new MutationObserver(function (records) {
      for (var r = 0; r < records.length; r++) {
        var added = records[r].addedNodes;
        for (var n = 0; n < added.length; n++) scan(added[n]);
      }
    }).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
