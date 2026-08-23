(function () {
  "use strict";

  var btn = document.createElement("button");
  btn.className = "back-to-top";
  btn.setAttribute("aria-label", "返回顶部");
  btn.setAttribute("type", "button");
  btn.textContent = "↑";
  btn.style.display = "none";
  document.body.appendChild(btn);

  var visible = false;
  function check() {
    var threshold = window.innerHeight * 0.6;
    var shouldShow = (window.pageYOffset || document.documentElement.scrollTop || 0) > threshold;
    if (shouldShow === visible) return;
    visible = shouldShow;
    btn.style.display = visible ? "block" : "none";
  }

  btn.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  window.addEventListener("scroll", check, { passive: true });
  window.addEventListener("resize", check, { passive: true });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", check);
  } else {
    check();
  }
})();
