/**
 * 通用懒加载脚本
 * - <img data-src="..." data-srcset="..." data-sizes="..." class="lazy">
 * - <div data-bg="url(...)" class="lazy-bg">
 * - 支持 IntersectionObserver 降级处理
 */
(function () {
  "use strict";

  var LAZY_CLASS = "lazy";
  var BG_CLASS = "lazy-bg";
  var LOADED_CLASS = "lazy-loaded";

  function loadImage(img) {
    var src = img.getAttribute("data-src");
    var srcset = img.getAttribute("data-srcset");
    var sizes = img.getAttribute("data-sizes");
    if (!src && !srcset) return;
    if (src) img.src = src;
    if (srcset) img.srcset = srcset;
    if (sizes) img.sizes = sizes;
    img.classList.add(LOADED_CLASS);
    img.removeAttribute("data-src");
    img.removeAttribute("data-srcset");
    img.removeAttribute("data-sizes");
  }

  function loadBackground(el) {
    var bg = el.getAttribute("data-bg");
    if (!bg) return;
    el.style.backgroundImage = bg;
    el.classList.add(LOADED_CLASS);
    el.removeAttribute("data-bg");
  }

  function queryLazy() {
    return Array.prototype.slice.call(
      document.querySelectorAll("." + LAZY_CLASS + ", ." + BG_CLASS)
    );
  }

  function loadAll() {
    queryLazy().forEach(function (el) {
      if (el.tagName.toLowerCase() === "img") loadImage(el);
      else loadBackground(el);
    });
  }

  if (
    !("IntersectionObserver" in window) ||
    !("IntersectionObserverEntry" in window)
  ) {
    loadAll();
    return;
  }

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        if (el.tagName.toLowerCase() === "img") loadImage(el);
        else loadBackground(el);
        observer.unobserve(el);
      });
    },
    { rootMargin: "200px 0px", threshold: 0.01 }
  );

  function observeLazy() {
    queryLazy().forEach(function (el) {
      if (!el.classList.contains(LOADED_CLASS)) observer.observe(el);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", observeLazy);
  } else {
    observeLazy();
  }

  // 暴露全局方法，方便动态内容触发
  window.LAZY_LOAD = { refresh: observeLazy, loadAll: loadAll };
})();
