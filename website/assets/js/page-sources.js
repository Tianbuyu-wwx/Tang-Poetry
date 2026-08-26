(function () {
  "use strict";
  window.OPTIMIZED_SOURCES_PAGE = true;

  var books = window.SOURCES_INDEX || [];
  var root = document.getElementById("library");
  var loadedBooks = {};
  var searchToken = 0;

  function esc(value) {
    return String(value == null ? "" : value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function escAttr(value) { return esc(value).replace(/"/g, "&quot;"); }
  function param(name) {
    var match = new RegExp("[?&]" + name + "=([^&]*)").exec(location.search);
    return match ? decodeURIComponent(match[1]) : "";
  }
  function link(book, chapter) { return "sources.html?book=" + encodeURIComponent(book.id) + "&chapter=" + chapter; }

  function loadBook(bookId) {
    if (window.SOURCE_BOOKS && window.SOURCE_BOOKS[bookId]) return Promise.resolve(window.SOURCE_BOOKS[bookId]);
    if (loadedBooks[bookId]) return loadedBooks[bookId];
    loadedBooks[bookId] = new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = "assets/js/source-books/" + bookId + ".js?v=21";
      script.async = true;
      script.onload = function () { resolve(window.SOURCE_BOOKS[bookId]); };
      script.onerror = function () { reject(new Error("无法载入典籍")); };
      document.head.appendChild(script);
    });
    return loadedBooks[bookId];
  }

  function snippet(text, query) {
    var at = text.indexOf(query);
    var start = Math.max(0, at - 55);
    var end = Math.min(text.length, at + query.length + 90);
    return (start ? "…" : "") + text.slice(start, end) + (end < text.length ? "…" : "");
  }
  function highlighted(text, query) {
    if (!query) return esc(text);
    return String(text).split(query).map(esc).join("<mark>" + esc(query) + "</mark>");
  }

  function renderReader(meta, chapterIndex) {
    root.innerHTML = '<p class="summary" role="status">正在载入《' + esc(meta.title) + "》正文…</p>";
    loadBook(meta.id).then(function (book) {
      var chapter = book.chapters[chapterIndex];
      if (!chapter) { renderHome(); return; }
      var previous = chapterIndex > 0 ? '<a href="' + link(book, chapterIndex - 1) + '">← 上一章</a>' : "<span></span>";
      var next = chapterIndex + 1 < book.chapters.length ? '<a href="' + link(book, chapterIndex + 1) + '">下一章 →</a>' : "<span></span>";
      var paragraphs = (chapter.text || "").split(/\n\s*\n/).filter(function(p){ return p.trim().length > 0; }).map(function(p){
        return "<p>" + esc(p).replace(/\n/g, "<br>") + "</p>";
      }).join("");
      root.innerHTML =
        '<a class="back" href="sources.html">← 返回典籍检索</a>' +
        '<div class="reader-head"><h1>' + esc(book.title) + " · " + esc(chapter.title) +
        '</h1><div class="meta">' + esc(book.author) + " · " + esc(book.edition) +
        " · 第 " + (chapterIndex + 1) + " / " + book.chapters.length + " 章</div></div>" +
        '<div class="reader-nav">' + previous + next + "</div>" +
        '<article class="reader-text">' + paragraphs + "</article>" +
        '<div class="reader-nav">' + previous + next + "</div>" +
        '<div class="license">来源：<a href="' + escAttr(book.sourceUrl) +
        '" target="_blank" rel="noopener">' + esc(book.source) + "</a> · " + esc(book.license) +
        "。开放录入可能存在异体字、断句或底本问题，引用前请回查原页面与影印底本。</div>";
      document.title = chapter.title + " · " + book.title + " · " + (window.BRAND ? window.BRAND.name : "石湖诗社");
    }).catch(function () {
      root.innerHTML = '<p class="summary" role="alert">典籍正文载入失败，请刷新页面重试。</p>';
    });
  }

  function renderHome() {
    var options = '<option value="all">全部典籍</option>';
    var cards = "";
    books.forEach(function (book) {
      options += '<option value="' + escAttr(book.id) + '">' + esc(book.title) + "</option>";
      cards += '<a class="book-card" href="' + link(book, 0) + '"><h2>' + esc(book.title) + '</h2><div class="meta">' + esc(book.author) + " · " + book.chapters.length + " 章</div><p>" + esc(book.description) + "</p></a>";
    });
    root.innerHTML = '<div class="library-head"><h1>典籍资料</h1><p>全文检索 ' + books.length + ' 部公版唐诗选本、诗话、传记与古代注评。这里保留古籍原意与来源，不将文言评点冒充现代白话注释。</p></div><div class="tools"><label class="sr-only" for="bookFilter">选择典籍</label><select id="bookFilter">' + options + '</select><label class="sr-only" for="sourceSearch">检索典籍全文</label><input id="sourceSearch" placeholder="搜索诗人、诗题、诗句或评语…" autocomplete="off"></div><div class="search-help">支持中文单字检索；首次搜索时会载入全部典籍正文。</div><div class="summary" id="sourceSummary" aria-live="polite">共 ' + books.length + ' 部典籍</div><div id="sourceResults" class="book-grid">' + cards + "</div>";

    var input = document.getElementById("sourceSearch");
    var filter = document.getElementById("bookFilter");
    var results = document.getElementById("sourceResults");
    var summary = document.getElementById("sourceSummary");
    var timer = null;

    function renderCards(selected) {
      var filtered = books.filter(function (book) { return selected === "all" || selected === book.id; });
      results.className = "book-grid";
      results.innerHTML = filtered.map(function (book) {
        return '<a class="book-card" href="' + link(book, 0) + '"><h2>' + esc(book.title) + '</h2><div class="meta">' + esc(book.author) + " · " + book.chapters.length + " 章</div><p>" + esc(book.description) + "</p></a>";
      }).join("");
      summary.textContent = "共 " + filtered.length + " 部典籍";
      results.removeAttribute("aria-busy");
    }

    function runSearch(query, selected, token) {
      var hits = [];
      books.some(function (meta) {
        if (selected !== "all" && selected !== meta.id) return false;
        var book = window.SOURCE_BOOKS[meta.id];
        return book.chapters.some(function (chapter, chapterIndex) {
          var at = chapter.text.indexOf(query);
          if (at >= 0 || chapter.title.indexOf(query) >= 0) hits.push({ book: book, chapter: chapter, chapterIndex: chapterIndex, at: at });
          return hits.length >= 100;
        });
      });
      if (token !== searchToken) return;
      results.className = "";
      results.innerHTML = hits.length ? hits.map(function (hit) {
        var text = hit.at >= 0 ? snippet(hit.chapter.text, query) : hit.chapter.title;
        return '<a class="result" href="' + link(hit.book, hit.chapterIndex) + '"><h3>' + esc(hit.book.title) + " · " + highlighted(hit.chapter.title, query) + "</h3><p>" + highlighted(text, query) + "</p></a>";
      }).join("") : '<p class="summary">未找到匹配内容。</p>';
      results.removeAttribute("aria-busy");
      summary.textContent = "找到 " + hits.length + " 个章节" + (hits.length === 100 ? "（仅显示前 100 项）" : "");
    }

    function search() {
      var query = input.value.trim();
      var selected = filter.value;
      var token = ++searchToken;
      if (!query) { renderCards(selected); return; }
      summary.textContent = "正在载入典籍全文并检索“" + query + "”…";
      results.setAttribute("aria-busy", "true");
      Promise.all(books.filter(function (book) { return selected === "all" || selected === book.id; }).map(function (book) { return loadBook(book.id); })).then(function () {
        runSearch(query, selected, token);
      }).catch(function () {
        if (token !== searchToken) return;
        results.removeAttribute("aria-busy");
        summary.textContent = "典籍全文载入失败，请稍后重试。";
      });
    }

    input.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(search, 220); });
    filter.addEventListener("change", search);
  }

  var bookId = param("book");
  var chapter = parseInt(param("chapter"), 10);
  var meta = books.find(function (book) { return book.id === bookId; });
  if (meta && !isNaN(chapter)) renderReader(meta, chapter);
  else renderHome();
})();
