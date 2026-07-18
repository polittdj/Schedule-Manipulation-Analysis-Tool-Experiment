/* Schedule Forensics — page-chrome event delegation (ADR-0268).
 *
 * The strict CSP (script-src 'self') forbids inline event handlers, so every interactive
 * bit of server-rendered chrome is delegated here instead, marked by data attributes:
 *   select[data-sf-autosubmit]      — submit the owning form on change (the classic
 *                                     onchange="this.form.submit()" selects)
 *   select[data-sf-navselect]       — navigate to the selected option's value (the
 *                                     source-banner file switcher)
 *   select[data-sf-nexturl-submit]  — stamp the CURRENT page into the form's next_url,
 *                                     then submit (the banner Project switcher; the app
 *                                     sends Referrer-Policy: no-referrer, so returning to
 *                                     the page the operator was reading needs an explicit
 *                                     next_url — validated server-side)
 *   form[data-sf-confirm]           — window.confirm(message) gate on submit (Wipe Session)
 *   #sfQuitLink                     — window.sfQuit() (defined by heartbeat.js on every page)
 * Delegation on document means late-rendered chrome (AJAX panels) is covered automatically.
 */
"use strict";

(function () {
  document.addEventListener("change", function (e) {
    var el = e.target;
    if (!el || !el.matches) return;
    if (el.matches("select[data-sf-autosubmit]")) {
      if (el.form) el.form.submit();
    } else if (el.matches("select[data-sf-navselect]")) {
      if (el.value) location.href = el.value;
    } else if (el.matches("select[data-sf-nexturl-submit]")) {
      if (el.form) {
        if (el.form.next_url) el.form.next_url.value = location.pathname + location.search;
        el.form.submit();
      }
    }
  });
  document.addEventListener("submit", function (e) {
    var f = e.target;
    if (f && f.matches && f.matches("form[data-sf-confirm]")) {
      if (!window.confirm(f.getAttribute("data-sf-confirm"))) e.preventDefault();
    }
  });
  document.addEventListener("click", function (e) {
    var q = e.target && e.target.closest ? e.target.closest("#sfQuitLink") : null;
    if (q) {
      e.preventDefault();
      if (window.sfQuit) window.sfQuit();
    }
  });
})();
