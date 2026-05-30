/*
  Crosfield analytics beacon — fires a single pageview ping on load.
  Same-origin POST; no third-party request. Respects Do-Not-Track.
  Window helper: window.cfTrack(name, metadata?) records a custom event.
*/
(function () {
  if (window.navigator && window.navigator.doNotTrack === "1") return;

  function send(url, body) {
    try {
      var blob = new Blob([JSON.stringify(body)], {type: "application/json"});
      if (navigator.sendBeacon && navigator.sendBeacon(url, blob)) return;
      fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body),
        keepalive: true,
      }).catch(function () { /* swallow */ });
    } catch (e) { /* swallow */ }
  }

  // Fire pageview after onload so we don't block render
  function fire() {
    send("/analytics/pageview/", {
      path: window.location.pathname + window.location.search,
      referrer: document.referrer || "",
    });
  }
  if (document.readyState === "complete") fire();
  else window.addEventListener("load", fire, {once: true});

  // Expose custom event API
  window.cfTrack = function (name, metadata) {
    if (!name) return;
    send("/analytics/event/", {
      name: name,
      path: window.location.pathname,
      metadata: metadata || {},
    });
  };
})();
