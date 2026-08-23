/*
 * 公告页（P4 · 社务内容）
 * ------------------------------------------------------------------
 * 数据源：window.NEWS_INDEX（由 build_society.parse_news 生成，已按日期倒序）
 *   [{id,title,date,author,tag,html}]
 * html 已由 build_society 的极简 Markdown 渲染器生成，此处仅注入容器。
 */
(function () {
  "use strict";

  var news = window.NEWS_INDEX || [];

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderCard(item) {
    return (
      '<article class="news-card">' +
      '<div class="news-top">' +
      '<span class="news-date">' + esc(item.date || "") + "</span>" +
      (item.tag ? '<span class="news-tag">' + esc(item.tag) + "</span>" : "") +
      "</div>" +
      '<h2 class="news-title">' + esc(item.title || "未题") + "</h2>" +
      (item.author ? '<div class="news-author">撰稿 · ' + esc(item.author) + "</div>" : "") +
      '<div class="news-body">' + (item.html || "") + "</div>" +
      "</article>"
    );
  }

  function render() {
    var body = document.getElementById("newsBody");
    body.innerHTML = news.map(renderCard).join("");
    document.getElementById("emptyHint").style.display = news.length ? "none" : "block";
  }

  render();
})();
