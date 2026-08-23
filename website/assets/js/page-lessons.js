/*
 * 社课页（P4 · 社务内容）
 * ------------------------------------------------------------------
 * 数据源：window.LESSONS_INDEX（由 build_society.parse_lessons 生成）
 *   { title, intro, lessons: [{id,title,theme,requirement,open,close,host,works:[poemId]}] }
 * 作品标题经 window.POEMS_INDEX 解析（{i,t,a,...}），链接到 poem.html?id=。
 */
(function () {
  "use strict";

  var data = window.LESSONS_INDEX || { lessons: [] };
  var poemIndex = window.POEMS_INDEX || [];
  var titleById = {};
  poemIndex.forEach(function (item) {
    titleById[item.i] = item.t;
  });

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function fmtDate(value) {
    return value ? esc(value) : "—";
  }

  function statusOf(close) {
    if (!close) return { text: "长期课", open: true };
    var today = new Date();
    var end = new Date(String(close).replace(/-/g, "/"));
    if (isNaN(end.getTime())) return { text: "课业", open: true };
    if (end >= today) return { text: "征稿中", open: true };
    return { text: "已截稿", open: false };
  }

  function renderWorks(works) {
    if (!works || !works.length) {
      return '<li class="none">本期习作待辑</li>';
    }
    return works
      .map(function (id) {
        var title = titleById[id] || id;
        return (
          '<li><a href="./poem.html?id=' + encodeURIComponent(id) + '">' +
          '<span class="t">' + esc(title) + "</span>" +
          '<span class="g">' + esc(id) + "</span></a></li>"
        );
      })
      .join("");
  }

  function renderCard(lesson) {
    var st = statusOf(lesson.close);
    return (
      '<article class="les-card">' +
      '<div class="les-title-row">' +
      '<span class="les-title">' + esc(lesson.title || "未题") + "</span>" +
      '<span class="les-status ' + (st.open ? "open" : "") + '">' + esc(st.text) + "</span>" +
      "</div>" +
      '<div class="les-meta">' +
      "<span>课业编号：<b>" + esc(lesson.id || "—") + "</b></span>" +
      "<span>主持：<b>" + esc(lesson.host || "—") + "</b></span>" +
      "<span>起：" + fmtDate(lesson.open) + "</span>" +
      "<span>止：" + fmtDate(lesson.close) + "</span>" +
      "</div>" +
      (lesson.theme ? '<div class="les-block"><div class="label">题意</div><div class="text">' + esc(lesson.theme) + "</div></div>" : "") +
      (lesson.requirement ? '<div class="les-block"><div class="label">要求</div><div class="text">' + esc(lesson.requirement) + "</div></div>" : "") +
      '<div class="les-block"><div class="label">入选之作</div><ul class="les-works">' + renderWorks(lesson.works) + "</ul></div>" +
      "</article>"
    );
  }

  function render() {
    var intro = document.getElementById("intro");
    if (intro) {
      intro.innerHTML = data.intro
        ? esc(data.intro)
        : "石湖诗社定期命题征集之作。列各课题意、要求与入选之作。";
    }
    var body = document.getElementById("lessonsBody");
    var lessons = data.lessons || [];
    body.innerHTML = lessons.map(renderCard).join("");
    document.getElementById("emptyHint").style.display = lessons.length ? "none" : "block";
  }

  render();
})();
