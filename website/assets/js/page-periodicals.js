/*
 * 社刊页（P4 · 社务内容）
 * ------------------------------------------------------------------
 * 数据源：window.PERIODICALS_INDEX（由 build_society.parse_periodicals 生成，已按日期倒序）
 *   [{id,title,issue,date,editor,description,works:[{id,note}]}]
 * 作品标题经 window.POEMS_INDEX 解析，链接到 poem.html?id=。
 */
(function () {
  "use strict";

  var periodicals = window.PERIODICALS_INDEX || [];
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

  function renderWorks(works) {
    if (!works || !works.length) {
      return '<li><span class="g">本期作品待辑</span></li>';
    }
    return works
      .map(function (w) {
        var id = w.id || "";
        var title = titleById[id] || id;
        return (
          "<li>" +
          '<a href="./poem.html?id=' + encodeURIComponent(id) + '">' + esc(title) + "</a>" +
          '<span class="g">' + esc(id) + "</span>" +
          (w.note ? '<span class="note">' + esc(w.note) + "</span>" : "") +
          "</li>"
        );
      })
      .join("");
  }

  function renderCard(p) {
    return (
      '<article class="per-card">' +
      '<div class="per-title-row">' +
      '<span class="per-title">' + esc(p.title || "未题") + "</span>" +
      (p.issue ? '<span class="per-issue">' + esc(p.issue) + "</span>" : "") +
      "</div>" +
      '<div class="per-meta">' +
      (p.date ? "<span>刊期：" + esc(p.date) + "</span>" : "") +
      (p.editor ? "<span>主编：<b>" + esc(p.editor) + "</b></span>" : "") +
      "</div>" +
      (p.description ? '<div class="per-desc">' + esc(p.description) + "</div>" : "") +
      '<ul class="per-works">' + renderWorks(p.works) + "</ul>" +
      "</article>"
    );
  }

  function render() {
    var body = document.getElementById("periodicalsBody");
    body.innerHTML = periodicals.map(renderCard).join("");
    document.getElementById("emptyHint").style.display = periodicals.length ? "none" : "block";
  }

  render();
})();
