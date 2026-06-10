// Dashboard dropzone. Submits the real <form> (no fetch): the browser follows the 303 itself,
// so the single-file jump to /analysis/... and the one-shot import flash both survive (a fetch
// would auto-follow the redirect on a hidden request and swallow both).
(function () {
  var form = document.getElementById('uploadForm'),
    input = document.getElementById('fileInput'),
    dz = document.getElementById('dropzone');
  if (!form || !input || !dz) return;
  function submit() {
    dz.classList.add('busy');
    form.submit();
  }
  document.getElementById('pickBtn').onclick = function () {
    input.click();
  };
  input.onchange = function () {
    if (input.files && input.files.length) submit();
  };
  ['dragover', 'dragenter'].forEach(function (e) {
    dz.addEventListener(e, function (ev) {
      ev.preventDefault();
      dz.classList.add('over');
    });
  });
  ['dragleave', 'drop'].forEach(function (e) {
    dz.addEventListener(e, function (ev) {
      ev.preventDefault();
      dz.classList.remove('over');
    });
  });
  dz.addEventListener('drop', function (ev) {
    var f = ev.dataTransfer && ev.dataTransfer.files;
    if (f && f.length) {
      input.files = f;
      submit();
    }
  });
})();
