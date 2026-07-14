// Dashboard dropzone. Uploads via fetch (not a full-page form.submit) so a browser-side file-READ
// failure surfaces as a catchable error in-app instead of nuking the page to Chrome's
// net::ERR_ACCESS_DENIED. That error is a browser abort BEFORE the request is sent: Chrome reads a
// picked file's bytes lazily at POST time, and an un-hydrated OneDrive Files-On-Demand placeholder
// (or a file open in MS Project) makes that read fail — killing the whole navigation. So we PRE-READ
// each picked file here (file.arrayBuffer(), catchable): readable files are uploaded, unreadable
// ones are dropped and reported by name (with the self-service fix), and one bad file no longer
// aborts the entire batch. Pre-buffering the bytes also decouples the send from disk, sidestepping
// the sibling ERR_UPLOAD_FILE_CHANGED race if OneDrive hydrates mid-upload.
//
// The server answers the fetch (X-SF-Ajax) with JSON {redirect}; we navigate there ourselves, so the
// single-file jump to /analysis/... and the server-side import flash both still render on that GET.
//
// Two ways in: pick/drag individual files (loose), or pick a whole folder (webkitdirectory — the
// folder is one Project, every schedule inside it, any sub-folder depth, is a version). The raw
// multipart POST can't carry a file's folder path or last-modified time, so we send a companion JSON
// array (webkitRelativePath + lastModified, per readable file, in order) alongside the files.
//
// Drag-and-drop: a file dropped ANYWHERE on the page must be opened by the tool, not the browser, so
// we preventDefault dragover+drop at the WINDOW level and feed the files in.
(function () {
  var form = document.getElementById('uploadForm'),
    input = document.getElementById('fileInput'),
    folderInput = document.getElementById('folderInput'),
    notice = document.getElementById('uploadNotice'),
    dz = document.getElementById('dropzone');
  if (!form || !input || !dz) return;

  function overlay(show) {
    var ov = document.getElementById('loadOverlay');
    if (ov) { ov.hidden = !show; ov.setAttribute('aria-hidden', show ? 'false' : 'true'); }
  }
  function showNotice(html) {
    if (!notice) return;
    notice.innerHTML = html;
    notice.hidden = false;
  }
  function hideNotice() { if (notice) { notice.hidden = true; notice.textContent = ''; } }
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  // A restored (BFCache/back) page must not resurrect the overlay or a stale FileList.
  window.addEventListener('pageshow', function () {
    overlay(false);
    dz.classList.remove('busy');
    clearInput(input);
    clearInput(folderInput);
  });
  function clearInput(el) {
    if (el && el.value) { try { el.value = ''; } catch (e) { /* readonly on very old engines */ } }
  }

  // Pre-read each picked file. Returns { readable:[File], meta:[{rel,mtime}], skipped:[{path,reason}] }.
  // file.arrayBuffer() forces the byte read NOW (catchable): a cloud placeholder / locked file rejects
  // with a NotReadableError instead of failing invisibly at send time.
  async function preread(fileList) {
    var readable = [], meta = [], skipped = [];
    for (var i = 0; i < fileList.length; i++) {
      var f = fileList[i];
      try {
        var buf = await f.arrayBuffer();
        readable.push(new File([buf], f.name, { type: f.type, lastModified: f.lastModified }));
        meta.push({ rel: f.webkitRelativePath || '', mtime: f.lastModified || null });
      } catch (err) {
        skipped.push({ path: f.webkitRelativePath || f.name, reason: (err && err.name) || 'ReadError' });
      }
    }
    return { readable: readable, meta: meta, skipped: skipped };
  }

  function skipHint(skipped) {
    var names = skipped.map(function (s) { return esc(s.path); }).slice(0, 5).join(', ');
    var more = skipped.length > 5 ? ' (+' + (skipped.length - 5) + ' more)' : '';
    return 'Could not read ' + skipped.length + (skipped.length === 1 ? ' file' : ' files') +
      ': ' + names + more + '. This usually means the file is online-only in OneDrive or open in ' +
      'Microsoft Project. In File Explorer right-click it &rarr; "Always keep on this device", ' +
      'close Microsoft Project, then try again.';
  }

  async function upload(source) {
    var picked = (source && source.files) ? Array.prototype.slice.call(source.files) : [];
    if (!picked.length) return;
    hideNotice();
    dz.classList.add('busy');
    overlay(true);
    var r;
    try {
      r = await preread(picked);
    } catch (e) {
      overlay(false); dz.classList.remove('busy');
      showNotice('Could not read the selected files. Please try again.');
      return;
    }
    if (!r.readable.length) {
      // nothing readable — stay on the page and explain, instead of a dead browser error tab
      overlay(false); dz.classList.remove('busy');
      showNotice(skipHint(r.skipped));
      return;
    }
    var fd = new FormData();
    for (var j = 0; j < r.readable.length; j++) fd.append('files', r.readable[j], r.readable[j].name);
    fd.append('file_meta', JSON.stringify(r.meta));
    if (r.skipped.length) fd.append('skipped_files', JSON.stringify(r.skipped));
    try {
      var resp = await fetch('/upload', { method: 'POST', body: fd, headers: { 'X-SF-Ajax': '1' } });
      var data = await resp.json();
      window.location = (data && data.redirect) || '/';
    } catch (e) {
      overlay(false); dz.classList.remove('busy');
      var msg = 'The upload could not be completed.';
      if (r.skipped.length) msg += ' ' + skipHint(r.skipped);
      showNotice(msg);
    }
  }

  var exampleForm = document.getElementById('exampleForm');
  if (exampleForm) exampleForm.addEventListener('submit', function () { overlay(true); });
  var pick = document.getElementById('pickBtn');
  if (pick) pick.onclick = function () { input.click(); };
  var pickFolder = document.getElementById('pickFolderBtn');
  if (pickFolder && folderInput) pickFolder.onclick = function () { folderInput.click(); };
  input.onchange = function () { if (input.files && input.files.length) upload(input); };
  if (folderInput) folderInput.onchange = function () {
    if (folderInput.files && folderInput.files.length) upload(folderInput);
  };

  // Window-wide: stop the browser opening a dropped file and handle it ourselves.
  window.addEventListener('dragover', function (ev) { ev.preventDefault(); }, false);
  window.addEventListener('drop', function (ev) {
    ev.preventDefault();
    dz.classList.remove('over');
    upload({ files: ev.dataTransfer && ev.dataTransfer.files });
  }, false);
  ['dragover', 'dragenter'].forEach(function (e) {
    dz.addEventListener(e, function (ev) { ev.preventDefault(); dz.classList.add('over'); });
  });
  dz.addEventListener('dragleave', function () { dz.classList.remove('over'); });
})();
