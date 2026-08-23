/*
 * 社员名录页（P1.4）
 * ------------------------------------------------------------------
 * 数据源：window.MEMBERS_INDEX（由 build_frontend_assets.build_poet_assets 生成）
 *   { slug: [name, sealChar, nameEn, period, summary, sub, works] }
 *   works: [[poemId, title, genre], ...]
 * 社员量级小（几十位），故作品清单内联在索引中，本页无需再加载分片。
 */
(function () {
  "use strict";

  var members = window.MEMBERS_INDEX || {};
  var currentFilter = "";
  var ordered = [];

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function highlighted(text, q) {
    if (!q) return esc(text);
    var parts = String(text).split(q);
    if (parts.length === 1) return esc(text);
    return parts.map(esc).join("<mark>" + esc(q) + "</mark>");
  }

  Object.keys(members).forEach(function (slug) {
    var m = members[slug];
    ordered.push({
      slug: slug,
      name: m[0] || "",
      seal: m[1] || (m[0] || "").charAt(0),
      nameEn: m[2] || "",
      period: m[3] || "",
      summary: m[4] || "",
      sub: m[5] || "",
      works: m[6] || []
    });
  });

  // 作品多者在前，同数按姓名排序，保证名录顺序稳定
  ordered.sort(function (a, b) {
    if (b.works.length !== a.works.length) return b.works.length - a.works.length;
    return a.name.localeCompare(b.name, "zh-Hans-CN");
  });

  function matches() {
    if (!currentFilter) return ordered;
    return ordered.filter(function (item) {
      if (item.name.replace(/\s+/g, "").toLowerCase().indexOf(currentFilter) >= 0) return true;
      return item.works.some(function (work) {
        return String(work[1] || "").toLowerCase().indexOf(currentFilter) >= 0;
      });
    });
  }

  function renderWorks(item) {
    if (!item.works.length) {
      return '<li class="none">暂无上站作品</li>';
    }
    return item.works
      .map(function (work) {
        return (
          '<li><a href="./poem.html?id=' +
          encodeURIComponent(work[0]) +
          '"><span class="t">' +
          highlighted(work[1], currentFilter) +
          "</span>" +
          (work[2] ? '<span class="g">' + esc(work[2]) + "</span>" : "") +
          "</a></li>"
        );
      })
      .join("");
  }

  function renderCard(item) {
    var tags = [];
    if (item.sub) tags.push(item.sub);
    if (item.period) tags.push(item.period);
    tags.push(item.works.length + " 首");

    return (
      '<article class="mem-card">' +
      '<div class="seal">' + esc(item.seal) + "</div>" +
      "<div>" +
      '<div class="mem-name"><a href="./poet.html?id=' +
      encodeURIComponent(item.slug) +
      '">' +
      highlighted(item.name, currentFilter) +
      "</a>" +
      (item.nameEn ? '<span class="en">' + esc(item.nameEn) + "</span>" : "") +
      "</div>" +
      '<div class="mem-tags">' +
      tags
        .map(function (tag) {
          return "<span>" + esc(tag) + "</span>";
        })
        .join("") +
      "</div>" +
      (item.summary ? '<div class="mem-summary-text">' + esc(item.summary) + "</div>" : "") +
      '<div class="mem-works-label">作品</div>' +
      '<ul class="mem-works">' + renderWorks(item) + "</ul>" +
      "</div>" +
      "</article>"
    );
  }

  function render() {
    var all = matches();
    document.getElementById("membersBody").innerHTML = all.map(renderCard).join("");
    document.getElementById("emptyHint").style.display = all.length ? "none" : "block";

    var works = all.reduce(function (sum, item) {
      return sum + item.works.length;
    }, 0);
    var summary = document.getElementById("summary");
    if (currentFilter) {
      summary.innerHTML =
        '找到 <span class="num">' + all.length + '</span> 位社员 · <span class="num">' + works + "</span> 首作品";
    } else {
      summary.innerHTML =
        '在册社员 <span class="num">' + all.length + '</span> 位 · 上站作品 <span class="num">' + works + "</span> 首";
    }
  }

  var timer = null;
  var input = document.getElementById("searchInput");
  if (input) {
    input.addEventListener("input", function (event) {
      clearTimeout(timer);
      var value = event.target.value;
      timer = setTimeout(function () {
        currentFilter = value.trim().replace(/\s+/g, "").toLowerCase();
        render();
      }, 150);
    });
  }

  render();
})();
