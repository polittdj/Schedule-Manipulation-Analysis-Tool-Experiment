// Keep-alive, close-beacon, and quit. Every page beats every 3s so the server knows the browser
// is open; when all windows close the beats stop and the launcher's watchdog shuts the server
// down (that is how closing the tool turns everything off). window.sfQuit() (the nav "Quit")
// stops it now.
//
// The close beacon (ADR-0482) is what makes "I closed the window" different from "I walked
// away". Without it both look identical to the server and both wait the full 600s idle grace,
// so a closed tool kept running for ten minutes — holding the local model's VRAM with it.
//
// It fires on `pagehide` ONLY, and that restriction is the whole design:
//   * NOT `visibilitychange` — that fires on a tab switch or a minimise, where the page is very
//     much alive; arming the fuse there would leave it to a BACKGROUND tab's beats to cancel,
//     and browsers throttle those.
//   * NOT when `event.persisted` — that is the back/forward cache, where the page is frozen and
//     coming back. Beaconing there would stop the tool behind a Back button.
// And the beacon does NOT mean "stop": this app is 35 server-rendered routes, so EVERY link
// click unloads the page. It arms a short fuse that the next page's first beat cancels — and
// that beat is sent immediately on load, below, before any interval is scheduled.
(function () {
  function beat() {
    fetch('/api/heartbeat', { method: 'POST' }).catch(function () {});
  }
  beat();
  var hb = setInterval(beat, 3000);
  window.addEventListener('pagehide', function (ev) {
    if (ev && ev.persisted) return; // bfcache: still alive, coming back
    // sendBeacon, not fetch: it is the only send guaranteed to survive unload.
    navigator.sendBeacon('/api/closing');
  });
  window.sfQuit = function () {
    clearInterval(hb);
    fetch('/api/shutdown', { method: 'POST' }).catch(function () {});
    document.body.innerHTML =
      '<main><div class=panel><h2>Schedule Forensics stopped</h2>' +
      '<p class=muted>The local server is shutting down. You can close this window.</p></div></main>';
    return false;
  };
})();
