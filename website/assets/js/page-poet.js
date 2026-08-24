(function () {
  "use strict";
  window.OPTIMIZED_POET_PAGE = true;

  var slim = window.POET_SLIM || {};
  var page = document.getElementById("poetPage");
  var chunkSize = 120;
  var visible = chunkSize;
  var works = [];

  function getParam(name) {
    var match = new RegExp("[?&]" + name + "=([^&]*)").exec(location.search);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.onload = resolve;
      script.onerror = function () { reject(new Error("无法载入" + src)); };
      document.head.appendChild(script);
    });
  }

  var slug = getParam("id");
  var entry = slim[slug];
  if (!entry) {
    page.innerHTML = '<h1 class="poet-section-title">未找到诗人</h1><p class="poet-empty">未找到该诗人。<a href="./poets.html">返回索引</a></p>';
    return;
  }

  // entry: [name, sealChar, nameEn, hasLife, workShard]
  var name = entry[0] || "佚名";
  var seal = entry[1] || (name ? name.charAt(0) : "唐");
  var nameEn = entry[2] || "";
  var hasLife = !!entry[3];
  var shard = entry[4];
  var bioInfo = null;

  page.innerHTML =
    '<div class="poet-hero"><div class="big-seal">' + esc(seal) + '</div><div><h1>' + esc(name) + "</h1>" +
    '<div class="pen" id="poetPen"></div></div></div>' +
    '<div class="poet-bio" id="poetBio"><p class="poet-empty">正在载入生平资料…</p></div>' +
    '<div class="poet-section-title">诗作全集 <span class="en">Works</span></div>' +
    '<div class="works-status" id="worksStatus" role="status">正在载入作品…</div><ul class="poet-works" id="worksList"></ul><div class="works-actions"><button class="list-more" id="worksMore" type="button" hidden>显示更多</button></div>';

  document.title = name + " · " + (window.BRAND ? window.BRAND.name : "石湖诗社");
  document.getElementById("crumbName").textContent = name;

  // 生平与作品两个分片并行加载，谁后到谁补全标题行（避免竞态把存诗数写成 0）
  function refreshPen() {
    var parts = [nameEn || "", bioInfo ? (bioInfo[4] || "") : ""].filter(Boolean);
    var dynasty = bioInfo ? (bioInfo[3] || "") : "";
    if (dynasty) parts.push(dynasty === "唐" ? "唐代" : dynasty);
    parts.push("存诗 " + works.length + " 首");
    document.getElementById("poetPen").textContent = parts.join(" · ");
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
    refreshPen();
  }

  document.getElementById("worksMore").addEventListener("click", function () {
    visible += chunkSize;
    renderWorks();
  });

  // 作品分片：渲染列表并回填存诗数
  loadScript("./assets/js/poet-work-shards/" + shard + ".js?v=17").then(function () {
    works = (window.POET_WORKS || {})[slug] || [];
    renderWorks();
  }).catch(function () {
    document.getElementById("worksStatus").textContent = "作品列表载入失败，请刷新页面重试。";
  });

  // 生平分片（约 33KB/片）：补全年代、简介、生平与资料来源
  loadScript("./assets/js/poet-bio-shards/" + shard + ".js?v=17").then(function () {
    var bio = (window.POET_BIO || {})[slug];
    if (!bio) throw new Error("no bio");
    bioInfo = bio;
    var life = bio[0] || [];
    var summary = bio[1] || "";
    var sources = bio[2] || [];

    var bioHtml = life.length
      ? life.map(function (paragraph) { return "<p>" + esc(paragraph) + "</p>"; }).join("")
      : summary ? "<p>" + esc(summary) + "</p>" : '<p class="poet-empty">暂无详细生平资料。</p>';
    var bioBox = document.getElementById("poetBio");
    bioBox.innerHTML = bioHtml;

    if (sources.length) {
      bioBox.insertAdjacentHTML("afterend", '<div class="poet-sources">生平资料来源：' + sources.map(function (source) {
        if (typeof source === "string") return esc(source);
        var label = source.label || source.name || source.url || "资料来源";
        return source.url ? '<a href="' + esc(source.url) + '" target="_blank" rel="noopener">' + esc(label) + "</a>" : esc(label);
      }).join(" · ") + "</div>");
    }

    var description = summary || (life.length ? life[0] : "") || (name + "，唐代诗人。");
    if (description.length > 160) description = description.slice(0, 157) + "…";
    description += works.length ? " 全唐诗收录其诗作 " + works.length + " 首。" : "";
    setSeoMeta(description);
    refreshPen();
  }).catch(function () {
    document.getElementById("poetBio").innerHTML = '<p class="poet-empty">生平资料载入失败，请刷新重试。</p>';
    refreshPen();
  });

  function setSeoMeta(description) {
    var existing = document.querySelector('meta[data-seo="dynamic"]');
    if (existing) { existing.setAttribute("content", description); return; }
    var meta = document.createElement("meta");
    meta.setAttribute("name", "description");
    meta.setAttribute("content", description);
    meta.setAttribute("data-seo", "dynamic");
    document.head.appendChild(meta);
  }
})();
