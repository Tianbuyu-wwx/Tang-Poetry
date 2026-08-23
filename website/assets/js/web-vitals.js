(function () {
  "use strict";
  if (!window.performance || !window.PerformanceObserver) return;

  function sendMetric(name, value) {
    // 输出到控制台，也可扩展为发送到后端监控服务
    console.log("[Web Vitals] " + name + ": " + value + (name === "CLS" ? "" : "ms"));
  }

  // FCP
  try {
    new PerformanceObserver(function (list) {
      var entries = list.getEntries();
      var last = entries[entries.length - 1];
      if (last) sendMetric("FCP", Math.round(last.startTime));
    }).observe({ type: "paint", buffered: true });
  } catch (e) {}

  // LCP
  try {
    new PerformanceObserver(function (list) {
      var entries = list.getEntries();
      var last = entries[entries.length - 1];
      if (last) sendMetric("LCP", Math.round(last.startTime));
    }).observe({ type: "largest-contentful-paint", buffered: true });
  } catch (e) {}

  // CLS
  try {
    var cls = 0;
    new PerformanceObserver(function (list) {
      list.getEntries().forEach(function (entry) {
        if (!entry.hadRecentInput) {
          cls += entry.value;
        }
      });
      sendMetric("CLS", Math.round(cls * 1000) / 1000);
    }).observe({ type: "layout-shift", buffered: true });
  } catch (e) {}

  // FID
  try {
    new PerformanceObserver(function (list) {
      list.getEntries().forEach(function (entry) {
        sendMetric("FID", Math.round(entry.processingStart - entry.startTime));
      });
    }).observe({ type: "first-input", buffered: true });
  } catch (e) {}

  // TTFB
  window.addEventListener("load", function () {
    var nav = performance.getEntriesByType("navigation")[0];
    if (nav) sendMetric("TTFB", Math.round(nav.responseStart - nav.startTime));
  });
})();
