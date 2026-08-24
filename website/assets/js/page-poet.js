(function () {
  "use strict";
  window.OPTIMIZED_POET_PAGE = true;

  var poets = window.POETS_DATA || {};
  var poetIndex = window.POETS_INDEX || {};
  var page = document.getElementById("poetPage");
  var chunkSize = 120;
  var visible = chunkSize;
  var works = [];

  function getParam(name) {
    var match = new RegExp("[?&]" + name + "=([^&]*)").exec(location.search);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function esc(value) {
    return String(value == null ? "" : value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function setMeta(name, content) {
    var selector = 'meta[name="' + name + '"]';
    var tag = document.querySelector(selector);
    if (!tag) {
      tag = document.createElement("meta");
      tag.setAttribute("name", name);
      document.head.appendChild(tag);
    }
    tag.setAttribute("content", content);
  }

  function setOg(property, content) {
    var selector = 'meta[property="og:' + property + '"]';
    var tag = document.querySelector(selector);
    if (!tag) {
      tag = document.createElement("meta");
      tag.setAttribute("property", "og:" + property);
      document.head.appendChild(tag);
    }
    tag.setAttribute("content", content);
  }

  function setSeoMeta(title, description) {
    document.title = title;
    setMeta("description", description);
    setOg("title", title);
    setOg("description", description);
    setOg("type", "profile");
    setOg("url", location.href);
    setOg("site_name", window.BRAND ? window.BRAND.ogSiteName : "石湖诗社");
  }

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.onload = resolve;
      script.onerror = function () { reject(new Error("无法载入作品列表")); };
      document.head.appendChild(script);
    });
  }

  function renderWorks() {
    var list = document.getElementById("worksList");
    var shown = works.slice(0, visible);
    list.innerHTML = shown.length ? shown.map(function (work) {
      return '<li><a href="./poem.html?id=' + encodeURIComponent(work[0]) + '"><span>' + esc(work[1]) + "</span>" + (work[2] ? '<span class="g">' + esc(work[2]) + "</span>" : "") + "</a></li>";
    }).join("") : '<li><span class="poet-empty">《全唐诗》未收录其诗作条目。</span></li>';
    var status = document.getElementById("worksStatus");
    status.textContent = works.length ? "已显示 " + Math.min(visible, works.length) + " / " + works.length + " 首" : "暂无诗作";
    var more = document.getElementById("worksMore");
    more.hidden = visible >= works.length;
    if (!more.hidden) more.textContent = "再显示 " + Math.min(chunkSize, works.length - visible) + " 首";
  }

  var slug = getParam("id");
  var poet = poets[slug];
  var indexEntry = poetIndex[slug];
  if (!poet || !indexEntry) {
    page.innerHTML = '<h1 class="poet-section-title">未找到诗人</h1><p class="poet-empty">未找到该诗人。<a href="./poets.html">返回索引</a></p>';
    return;
  }

  var name = poet.name || "佚名";
  var life = poet.life || [];
  var bioHtml = life.length
    ? life.map(function (paragraph) { return "<p>" + esc(paragraph) + "</p>"; }).join("")
    : poet.summary ? "<p>" + esc(poet.summary) + "</p>" : '<p class="poet-empty">暂无详细生平资料。</p>';
  var sources = poet.sources || [];
  var sourceHtml = "";
  if (sources.length) {
    sourceHtml = '<div class="poet-sources">生平资料来源：' + sources.map(function (source) {
      if (typeof source === "string") return esc(source);
      var label = source.label || source.name || source.url || "资料来源";
      return source.url ? '<a href="' + esc(source.url) + '" target="_blank" rel="noopener">' + esc(label) + "</a>" : esc(label);
    }).join(" · ") + "</div>";
  }

  page.innerHTML =
    '<div class="poet-hero"><div class="big-seal">' + esc(poet.sealChar || name[0] || "唐") + "</div><div><h1>" + esc(name) + '</h1><div class="pen">' + esc(poet.nameEn || poet.sub || "") + (poet.nameEn || poet.sub ? " · " : "") + esc(indexEntry[3] === "唐" ? "唐代" : indexEntry[3]) + " · 存诗 " + indexEntry[7] + " 首</div></div></div>" +
    '<div class="poet-bio">' + bioHtml + "</div>" + sourceHtml +
    '<div class="poet-section-title">诗作全集 <span class="en">Works</span></div>' +
    '<div class="works-status" id="worksStatus" role="status">正在载入作品…</div><ul class="poet-works" id="worksList"></ul><div class="works-actions"><button class="list-more" id="worksMore" type="button" hidden>显示更多</button></div>';

  var description = (poet.summary || (life.length ? life[0] : "") || name + "，唐代诗人。") + (indexEntry[7] ? " 全唐诗收录其诗作 " + indexEntry[7] + " 首。" : "");
  if (description.length > 160) description = description.slice(0, 157) + "…";
  setSeoMeta(name + " · " + (window.BRAND ? window.BRAND.name : "石湖诗社"), description);
  document.getElementById("crumbName").textContent = name;
  document.getElementById("worksMore").addEventListener("click", function () {
    visible += chunkSize;
    renderWorks();
  });

  loadScript("./assets/js/poet-work-shards/" + indexEntry[8] + ".js?v=15").then(function () {
    works = (window.POET_WORKS || {})[slug] || [];
    renderWorks();
  }).catch(function () {
    document.getElementById("worksStatus").textContent = "作品列表载入失败，请刷新页面重试。";
  });
})();
