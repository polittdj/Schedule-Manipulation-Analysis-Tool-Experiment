// Keep-alive + quit. Every page beats every 3s so the server knows the browser is open; when
// all windows close the beats stop and the launcher's watchdog shuts the server down (that is
// how closing the tool turns everything off). window.sfQuit() (the nav "Quit") stops it now.
(function () {
  function beat() {
    fetch('/api/heartbeat', { method: 'POST' }).catch(function () {});
  }
  beat();
  var hb = setInterval(beat, 3000);
  window.sfQuit = function () {
    clearInterval(hb);
    fetch('/api/shutdown', { method: 'POST' }).catch(function () {});
    document.body.innerHTML =
      '<main><div class=panel><h2>Schedule Forensics stopped</h2>' +
      '<p class=muted>The local server is shutting down. You can close this window.</p></div></main>';
    return false;
  };
})();
