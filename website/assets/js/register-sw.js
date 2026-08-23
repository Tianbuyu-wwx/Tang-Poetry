(function () {
  "use strict";
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("./service-worker.js", { scope: "./" })
        .catch(function (err) {
          // 静默失败，不影响正常浏览
          console.warn("Service Worker 注册失败:", err);
        });
    });
  }
})();
