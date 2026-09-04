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
// One folder whose schedules sit in several sub-folders is ASKED about before anything uploads
// (one Project, or one per sub-folder — see ingest()/askSubfolders below); the answer only changes
// the companion paths, never the server.
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
  // OR-03 (ADR-0328): the Boot Audio Hum rides the load overlay. One guarded helper so audio can
  // NEVER block or break a load — no SFLaunchAudio (script missing, API absent), no sound, same
  // upload. prime() is called ONLY from the genuine gesture handlers below (pick / folder /
  // example submit / drop — deliberately NOT from input.onchange, which browsers may not treat
  // as user activation); start/stop/fade follow the overlay's own lifecycle.
  function hum(action) {
    var a = window.SFLaunchAudio;
    if (!a) return Promise.resolve();
    try {
      if (action === 'prime') a.prime();
      else if (action === 'start') a.start();
      else if (action === 'stop') return a.stop() || Promise.resolve();
      else if (action === 'fade') return a.fadeOut(180) || Promise.resolve();
    } catch (e) { /* audio is decoration; the load always wins */ }
    return Promise.resolve();
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
    hideAsk();
    clearInput(input);
    clearInput(folderInput);
  });
  function clearInput(el) {
    if (el && el.value) { try { el.value = ''; } catch (e) { /* readonly on very old engines */ } }
  }

  // Pre-read each picked file. Returns { readable:[File], meta:[{rel,mtime}], skipped:[{path,reason}] }.
  // file.arrayBuffer() forces the byte read NOW (catchable): a cloud placeholder / locked file rejects
  // with a NotReadableError instead of failing invisibly at send time.
  //
  // BOUNDED CONCURRENCY (ADR-0289). This used to await one file at a time, so a folder drop paid the
  // full per-file latency serially — and on OneDrive-backed files that latency is a network hydrate,
  // not a disk read, so an N-file folder took N round-trips end to end. A small worker pool overlaps
  // them. The bound matters in both directions: unbounded (Promise.all over the whole FileList) would
  // open every read at once, which spikes memory by the size of the entire selection and gets
  // throttled by the browser on large folders; PREREAD_CONCURRENCY keeps at most a handful of buffers
  // alive at any moment.
  //
  // ORDER IS PRESERVED EXACTLY. Results land in index-addressed slots and are compacted in index
  // order afterwards, so `readable`, `meta` and `skipped` come out byte-for-byte identical to the
  // sequential version (readable[j] stays aligned with meta[j], which /upload relies on). Only the
  // wall-clock changes.
  var PREREAD_CONCURRENCY = 6;

  async function preread(fileList) {
    var files = Array.prototype.slice.call(fileList);
    var slots = new Array(files.length); // { ok:true, file, meta } | { ok:false, skip }
    var next = 0;

    async function worker() {
      while (true) {
        var i = next++;
        if (i >= files.length) return;
        var f = files[i];
        try {
          var buf = await f.arrayBuffer();
          slots[i] = {
            ok: true,
            file: new File([buf], f.name, { type: f.type, lastModified: f.lastModified }),
            meta: { rel: f.webkitRelativePath || '', mtime: f.lastModified || null }
          };
        } catch (err) {
          slots[i] = {
            ok: false,
            skip: { path: f.webkitRelativePath || f.name, reason: (err && err.name) || 'ReadError' }
          };
        }
      }
    }

    var pool = [];
    for (var w = 0; w < Math.min(PREREAD_CONCURRENCY, files.length); w++) pool.push(worker());
    await Promise.all(pool); // a worker never rejects — every failure is captured into its slot

    var readable = [], meta = [], skipped = [];
    for (var i = 0; i < slots.length; i++) {
      var s = slots[i];
      if (!s) continue;
      if (s.ok) { readable.push(s.file); meta.push(s.meta); }
      else skipped.push(s.skip);
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

  // ---- dropped-FOLDER traversal (operator 2026-08-21: several folders at once, each its own
  // Project). A dropped folder arrives as a directory DataTransferItem; dataTransfer.files
  // cannot descend into it — the bare directory File fails its byte read, so before this the
  // folder's schedules never loaded and the operator was told the folder was "online-only in
  // OneDrive". Chromium's directory-picker DIALOG cannot multi-select (webkitdirectory
  // overrides multiple — WICG entries-api #24), so the drop is THE way to select several
  // folders at one time. Each dropped folder's files carry rel = "Folder/sub/file.ext" — the
  // same per-file companion path a folder PICK sends — and the server already groups per top
  // folder, so N dropped folders land as N Projects with no server change.
  //
  // dropEntries must run SYNCHRONOUSLY inside the drop handler (the items list goes inert once
  // the handler yields); the async walk runs after, over the captured entries. Returns null
  // when no item exposes a real entry (a synthetic DataTransfer, an old engine) so the caller
  // falls back to dataTransfer.files — the historical path, byte-for-byte.
  function dropEntries(dt) {
    var items = dt && dt.items;
    if (!items || !items.length) return null;
    var roots = [];
    for (var i = 0; i < items.length; i++) {
      var entry = null;
      try { entry = items[i].webkitGetAsEntry && items[i].webkitGetAsEntry(); }
      catch (e) { entry = null; }
      if (entry) roots.push(entry);
    }
    return roots.length ? roots : null;
  }

  // A preread()-shaped File-like carrying a companion path the platform File cannot (a real
  // File's webkitRelativePath is read-only): name/type/lastModified/webkitRelativePath plus an
  // arrayBuffer() that reads the underlying File's bytes. preread() treats these as first-class
  // inputs — the ADR-0289 harness's own stubs are the proof.
  function fileLike(f, rel) {
    return { name: f.name, type: f.type, lastModified: f.lastModified,
      webkitRelativePath: rel,
      arrayBuffer: function () { return f.arrayBuffer(); } };
  }

  // Walk the captured entries into preread()-shaped File-likes: name/type/lastModified/
  // webkitRelativePath/arrayBuffer — files under a dropped folder carry rel rooted at that
  // folder's own name; a loose dropped file keeps rel '' (loose semantics unchanged). Chrome's
  // readEntries hands back at most 100 entries per call, so each directory drains until an
  // empty batch. An entry whose File cannot be materialized becomes a File-like whose read
  // rejects, so preread() reports it by its rel path like any other unreadable file.
  function walkEntries(roots) {
    return new Promise(function (resolve) {
      var out = [], pending = 0, seeded = false;
      function settle() { if (seeded && pending === 0) resolve(out); }
      function addFile(entry, rel) {
        pending += 1;
        entry.file(function (f) { out.push(fileLike(f, rel)); pending -= 1; settle(); },
          function (err) {
            out.push({ name: entry.name, type: '', lastModified: null,
              webkitRelativePath: rel,
              arrayBuffer: function () {
                var e = err || new Error('NotReadableError');
                if (!e.name) e.name = 'NotReadableError';
                return Promise.reject(e);
              } });
            pending -= 1; settle();
          });
      }
      function addDir(entry, prefix) {
        pending += 1;
        var reader = entry.createReader();
        (function drain() {
          reader.readEntries(function (batch) {
            if (!batch.length) { pending -= 1; settle(); return; }
            for (var i = 0; i < batch.length; i++) {
              var e = batch[i];
              if (e.isDirectory) addDir(e, prefix + e.name + '/');
              else addFile(e, prefix + e.name);
            }
            drain(); // Chrome batches readEntries (100 max) — drain until the empty batch
          }, function () { pending -= 1; settle(); });
        })();
      }
      for (var i = 0; i < roots.length; i++) {
        if (roots[i].isDirectory) addDir(roots[i], roots[i].name + '/');
        else addFile(roots[i], '');
      }
      seeded = true;
      settle();
    });
  }

  // ---- WP5 build B (ADR-0459): a PARENT folder that holds several project folders.
  // The picker dialog delivers ONE folder per pick (fact 1 of 2026-08-21), so an operator whose
  // projects sit side by side under a parent — Programs/Apollo/…, Programs/Artemis/… — can only
  // pick the parent, and the server groups by TOP folder, so that pick used to land as ONE
  // Project "Programs" with every schedule a version. Right for year sub-folders
  // (Project/2024/x.mpp IS one Project with versions), wrong for sibling programs — and the
  // paths alone can never say which (ADR-0258: a folder is one Project by the operator's rule;
  // guessing is forbidden). So when ONE folder root's schedule files span two or more immediate
  // sub-folders, ASK. "One per sub-folder" re-roots each file's companion rel at its sub-folder
  // (Programs/Apollo/a1.xml → Apollo/a1.xml) and the unchanged server groups them apart; a file
  // directly under the parent keeps its two-segment rel and so keeps the parent as its Project.
  // Files the server would ignore anyway (no schedule extension) never count. Several dropped
  // roots never ask — each is already its own Project (ADR-0437) — and a loose file in the
  // gesture means it was not a single-folder gesture at all.
  var ACCEPT = String(input.getAttribute('accept') || '').toLowerCase().split(',')
    .map(function (s) { return s.trim(); }).filter(Boolean);
  function isSchedule(name) {
    var dot = String(name).lastIndexOf('.');
    if (dot < 0) return false;
    return !ACCEPT.length || ACCEPT.indexOf(String(name).slice(dot).toLowerCase()) >= 0;
  }
  function relOf(f) {
    return String(f.webkitRelativePath || '').replace(/\\/g, '/').replace(/^\/+|\/+$/g, '');
  }
  // null when the gesture is unambiguous; else { root, groups: [{ name, count }], top, total }.
  function subfolderPlan(files) {
    var root = null, counts = {}, order = [], top = 0, total = 0;
    for (var i = 0; i < files.length; i++) {
      var parts = relOf(files[i]).split('/');
      if (parts.length < 2 || !parts[0]) return null;   // a loose file: not a folder gesture
      if (root === null) root = parts[0];
      else if (parts[0] !== root) return null;           // several roots: each its own Project
      if (!isSchedule(parts[parts.length - 1])) continue;
      total += 1;
      if (parts.length === 2) { top += 1; continue; }
      var sub = parts[1];
      if (!Object.prototype.hasOwnProperty.call(counts, sub)) { counts[sub] = 0; order.push(sub); }
      counts[sub] += 1;
    }
    if (root === null || order.length < 2) return null;
    // the FileList arrives in filesystem-traversal order, which differs machine to machine;
    // the question lists the sub-folders by name so the same folder always reads the same way
    order.sort(function (a, b) { return a.localeCompare(b); });
    return { root: root, top: top, total: total,
      groups: order.map(function (n) { return { name: n, count: counts[n] }; }) };
  }
  // Programs/Apollo/a1.xml → Apollo/a1.xml; a two-segment rel (Programs/top.xml) is left alone.
  function reroot(files) {
    return files.map(function (f) {
      var parts = relOf(f).split('/');
      return parts.length < 3 ? f : fileLike(f, parts.slice(1).join('/'));
    });
  }

  var askBox = document.getElementById('dzAsk');
  function hideAsk() { if (askBox) askBox.hidden = true; }
  function askSubfolders(plan, files) {
    var title = document.getElementById('dzAskTitle'), list = document.getElementById('dzAskList'),
      note = document.getElementById('dzAskNote'), split = document.getElementById('dzAskSplit'),
      one = document.getElementById('dzAskOne'), cancel = document.getElementById('dzAskCancel');
    if (!askBox || !title || !list || !note || !split || !one || !cancel) {
      // the shell is server-rendered beside the dropzone and pinned by test; without it the only
      // honest move is to stop and say so — never to pick one shape over the other in silence
      showNotice('This folder holds several project folders, but the page is missing the box that ' +
        'asks how to load them. Reload the page and try again.');
      return;
    }
    // built with createElement/textContent — folder names are operator content (ADR-0439)
    function plural(n, word) { return n + ' ' + word + (n === 1 ? '' : 's'); }
    title.textContent = '“' + plan.root + '” holds schedules in ' +
      plural(plan.groups.length, 'sub-folder') +
      (plan.top ? ' (and ' + plural(plan.top, 'schedule') + ' directly inside it)' : '') +
      '. How should they load?';
    while (list.firstChild) list.removeChild(list.firstChild);
    plan.groups.forEach(function (g) {
      var li = document.createElement('li');
      li.textContent = g.name + ' — ' + plural(g.count, 'schedule');
      list.appendChild(li);
    });
    split.textContent = plan.groups.length + ' Projects, one per sub-folder';
    one.textContent = 'One Project “' + plan.root + '” — ' + plural(plan.total, 'version');
    note.textContent = plan.top
      ? plural(plan.top, 'schedule') + ' directly under “' + plan.root + '” ' +
        (plan.top === 1 ? 'stays' : 'stay') + ' in Project “' + plan.root + '” either way.'
      : '';
    note.hidden = !plan.top;
    function done() {
      hideAsk();
      split.onclick = one.onclick = cancel.onclick = null;
      askBox.onkeydown = null;
    }
    function abandon() { done(); clearInput(input); clearInput(folderInput); }
    // the buttons do NOT prime the hum: the gesture that produced this question already did
    split.onclick = function () { done(); upload({ files: reroot(files) }); };
    one.onclick = function () { done(); upload({ files: files }); };
    cancel.onclick = abandon;
    askBox.onkeydown = function (ev) { if (ev.key === 'Escape') abandon(); };
    askBox.hidden = false;
    split.focus();
  }
  // Every way in funnels through here — picked files, the picked folder, a drop's traversal or
  // its dataTransfer.files fallback. Ambiguous → ask; otherwise upload exactly as before.
  function ingest(fileList) {
    var picked = fileList ? Array.prototype.slice.call(fileList) : [];
    if (!picked.length) return;
    var plan = subfolderPlan(picked);
    if (plan) { askSubfolders(plan, picked); return; }
    upload({ files: picked });
  }

  async function upload(source) {
    var picked = (source && source.files) ? Array.prototype.slice.call(source.files) : [];
    if (!picked.length) return;
    hideNotice();
    hideAsk();
    dz.classList.add('busy');
    overlay(true);
    hum('start');
    var r;
    try {
      r = await preread(picked);
    } catch (e) {
      overlay(false); dz.classList.remove('busy'); hum('stop');
      showNotice('Could not read the selected files. Please try again.');
      return;
    }
    if (!r.readable.length) {
      // nothing readable — stay on the page and explain, instead of a dead browser error tab
      overlay(false); dz.classList.remove('busy'); hum('stop');
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
      // the hum spans gesture -> POST resolution; fade (<=200ms) BEFORE the navigation cuts it
      try { await hum('fade'); } catch (e2) { /* never hold the redirect for audio */ }
      window.location = (data && data.redirect) || '/';
    } catch (e) {
      overlay(false); dz.classList.remove('busy'); hum('stop');
      var msg = 'The upload could not be completed.';
      if (r.skipped.length) msg += ' ' + skipHint(r.skipped);
      showNotice(msg);
    }
  }

  var exampleForm = document.getElementById('exampleForm');
  if (exampleForm) {
    // native form navigation: the hum plays while the server imports and ends at unload
    exampleForm.addEventListener('submit', function () { hum('prime'); hum('start'); overlay(true); });
  }
  var pick = document.getElementById('pickBtn');
  if (pick) pick.onclick = function () { hum('prime'); input.click(); };
  var pickFolder = document.getElementById('pickFolderBtn');
  if (pickFolder && folderInput) pickFolder.onclick = function () { hum('prime'); folderInput.click(); };
  input.onchange = function () { if (input.files && input.files.length) ingest(input.files); };
  if (folderInput) folderInput.onchange = function () {
    if (folderInput.files && folderInput.files.length) ingest(folderInput.files);
  };

  // Window-wide: stop the browser opening a dropped file and handle it ourselves.
  window.addEventListener('dragover', function (ev) { ev.preventDefault(); }, false);
  window.addEventListener('drop', function (ev) {
    ev.preventDefault();
    hum('prime'); // a drop is a genuine gesture — the context may be born here
    dz.classList.remove('over');
    // entries captured synchronously (the list goes inert after the handler yields); folders
    // traverse into rel-pathed File-likes so each dropped folder becomes its own Project
    var roots = dropEntries(ev.dataTransfer);
    if (roots) {
      walkEntries(roots).then(function (files) { ingest(files); });
      return;
    }
    ingest(ev.dataTransfer && ev.dataTransfer.files);
  }, false);
  ['dragover', 'dragenter'].forEach(function (e) {
    dz.addEventListener(e, function (ev) { ev.preventDefault(); dz.classList.add('over'); });
  });
  dz.addEventListener('dragleave', function () { dz.classList.remove('over'); });
})();
