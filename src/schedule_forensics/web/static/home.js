// Dashboard dropzone. Submits the real <form> (no fetch): the browser follows the 303 itself,
// so the single-file jump to /analysis/... and the one-shot import flash both survive (a fetch
// would auto-follow the redirect on a hidden request and swallow both).
//
// Drag-and-drop fix: a file dropped ANYWHERE on the page must be opened by the tool, not by the
// browser. By default a browser navigates to (opens) a file dropped on the document, so unless we
// preventDefault dragover+drop at the WINDOW level the drop never reaches the app. We therefore
// accept the drop window-wide (the visible zone is just a hint) and feed the files into the form.
(function () {
  var form = document.getElementById('uploadForm'),
    input = document.getElementById('fileInput'),
    dz = document.getElementById('dropzone');
  if (!form || !input || !dz) return;
  // reveal the full-screen "Loading your projects…" overlay the instant an import starts, so a slow
  // import (a big .mpp/.xer) never looks like the tool is stuck. It stays up until the POST navigates.
  function showLoading() {
    var ov = document.getElementById('loadOverlay');
    if (ov) { ov.hidden = false; ov.setAttribute('aria-hidden', 'false'); }
  }
  function submit() {
    dz.classList.add('busy');
    showLoading();
    form.submit();
  }
  // the "Load example" import can also take a moment — show the same indicator on its submit
  var exampleForm = document.getElementById('exampleForm');
  if (exampleForm) exampleForm.addEventListener('submit', showLoading);
  var pick = document.getElementById('pickBtn');
  if (pick) pick.onclick = function () { input.click(); };
  input.onchange = function () {
    if (input.files && input.files.length) submit();
  };

  // Put the dropped files onto the hidden file input, then submit the real form. Assigning the
  // DataTransfer FileList directly works in modern browsers; the DataTransfer rebuild is a fallback.
  function accept(files) {
    if (!files || !files.length) return;
    try {
      input.files = files;
    } catch (e) {
      try {
        var dt = new DataTransfer();
        for (var i = 0; i < files.length; i++) dt.items.add(files[i]);
        input.files = dt.files;
      } catch (e2) { return; }
    }
    submit();
  }

  // Window-wide: stop the browser from opening a dropped file and handle it ourselves. Only file
  // drags carry dataTransfer.files, so other interactions are unaffected.
  window.addEventListener('dragover', function (ev) { ev.preventDefault(); }, false);
  window.addEventListener('drop', function (ev) {
    ev.preventDefault();
    dz.classList.remove('over');
    accept(ev.dataTransfer && ev.dataTransfer.files);
  }, false);

  // Zone-local affordance only (highlight while a file hovers the visible target).
  ['dragover', 'dragenter'].forEach(function (e) {
    dz.addEventListener(e, function (ev) { ev.preventDefault(); dz.classList.add('over'); });
  });
  dz.addEventListener('dragleave', function () { dz.classList.remove('over'); });
})();
