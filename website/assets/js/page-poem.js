(function () {
  "use strict";
  window.OPTIMIZED_POEM_PAGE = true;

  var poetIndex = window.POET_SLIM || {};
  var loadedScripts = {};
  var modal = document.getElementById("poetModal");
  var modalBox = modal.querySelector(".poet-modal");
  var closeButton = document.getElementById("poetClose");
  var lastFocus = null;

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
    setOg("type", "article");
    setOg("url", location.href);
    setOg("site_name", window.BRAND ? window.BRAND.ogSiteName : "石湖诗社");
  }

  function normalizeName(value) {
    return String(value || "").replace(/\s+/g, "");
  }

  function loadScript(src) {
    if (loadedScripts[src]) return loadedScripts[src];
    loadedScripts[src] = new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.onload = resolve;
      script.onerror = function () { reject(new Error("无法载入 " + src)); };
      document.head.appendChild(script);
    });
    return loadedScripts[src];
  }

  function poemShardName(id) {
    var match = /^(open|curated|member)_(\d+)$/.exec(id);
    if (!match) return "misc";
    return match[1] + "-" + String(Math.floor(Number(match[2]) / 500)).padStart(3, "0");
  }

  function findPoet(author) {
    var wanted = normalizeName(author);
    for (var slug in poetIndex) {
      if (normalizeName(poetIndex[slug][0]) === wanted) return { slug: slug, data: poetIndex[slug] };
    }
    return null;
  }

  function splitSentences(segment) {
    var output = [];
    String(segment).split("\n").forEach(function (part) {
      var line = part.trim();
      if (!line) return;
      line.split(/ {2,}/).forEach(function (sub) {
        sub.trim().split(/(?<=[。？！；])/).forEach(function (sentence) {
          sentence = sentence.trim();
          if (sentence) output.push(sentence);
        });
      });
    });
    return output;
  }

  var CLASSICAL_PREFIXES = [
    // 史书/典籍
    "旧唐书","新唐书","北史","南史","晋书","后汉书","汉书","史记","三国志","隋书",
    "周书","梁书","陈书","魏书","北齐书","南齐书","宋书",
    "元和郡县志","水经注","文心雕龙","西京杂记","山海经","淮南子","吕氏春秋",
    "太平御览","艺文类聚","初学记","白孔六帖","玉台新咏","乐府诗集","古诗源",
    "唐诗品汇","沧浪诗话","六一诗话","苕溪渔隐丛话","诗人玉屑","滹南诗话",
    "世说新语","酉阳杂俎","博物志","搜神记",
    "风土记","荆楚岁时记","三秦记","洛阳伽蓝记","穆天子传","战国策","公羊传",
    "谷梁传","左氏传","左传","春秋","论语","孟子","荀子","老子","庄子","列子",
    "韩非子","管子","晏子春秋","墨子","尉缭子","商君书","抱朴子","文子","鹖冠子",
    "文选","尚书","周礼","仪礼","尔雅","说文","诗经","楚辞","易经","书经","礼记",
    // 先秦两汉魏晋作者
    "孔子","孟子","荀子","老子","庄子","列子","韩非子","管仲","晏婴",
    "屈原","宋玉","景差","贾谊","枚乘","司马相如","扬雄","班固","张衡",
    "蔡邕","孔融","曹操","曹丕","曹植","王粲","刘桢","阮瑀","徐幹",
    "陈琳","应玚","嵇康","阮籍","山涛","向秀","刘伶","王戎","阮咸",
    "陆机","陆云","潘岳","张协","左思","刘琨","郭璞","孙绰","许询",
    "陶渊明","陶潜","谢灵运","颜延之","鲍照","谢朓","谢惠连","谢庄","沈约","江淹",
    "庾信","徐陵","江总","阴铿","何逊","吴均","呉均","王褒","王融","范云",
    "任昉","丘迟","郦道元","刘勰","钟嵘","萧统","萧纲","萧绎",
    "梁武帝","梁元帝","梁简文帝","陈后主","陈後主",
    // 唐及后世诗人/文人
    "宋之问","沈佺期","王勃","杨炯","卢照邻","骆宾王","陈子昂","杜审言",
    "李峤","苏味道","崔融","上官仪","虞世南","欧阳询","褚遂良","薛稷",
    "太宗皇帝","高宗皇帝","中宗皇帝","玄宗皇帝","武则天","上官婉儿",
    "李白","杜甫","王维","孟浩然","王昌龄","高适","岑参","李颀",
    "崔颢","王之涣","王翰","张说","张九龄","贺知章","包融","张旭",
    "孟郊","贾岛","韩愈","柳宗元","刘禹锡","白居易","元稹","张籍",
    "王建","李绅","杜牧","李商隐","温庭筠","韦庄","司空图","韩偓",
    "罗隐","聂夷中","杜荀鹤","许浑","皮日休","陆龟蒙","僧齐己","齐己",
    // 常见帝王/人物
    "魏明帝","魏文帝","魏武帝","晋武帝","汉武帝","汉文帝","汉景帝","隋炀帝",
    "唐太宗","唐玄宗","汉高祖","秦始皇","楚襄王","鲁哀公","齐桓公","晋文公"
  ];

  var STYLE_WORDS = ["诗","赋","文","记","传","序","书","表","铭","箴","诔","碑","论","颂","说","志","注","笺","解","引","辞","曲","调","乐府","语录","纪事","提要","演义","评","谱","纂","钞","略","录","编","选","抄","注疏","正义","集解","章句","音义","释文"];

  function semanticSplitAnnotation(text, maxLen) {
    var result = [];
    var i = 0;
    while (i < text.length) {
      if (text.length - i <= maxLen) {
        result.push(text.slice(i).trim());
        break;
      }
      var tail = text.slice(i + maxLen - 5, i + maxLen + 5);
      var cut = maxLen;
      var m = tail.match(/[而以之于则故乃遂因与者也矣焉兮乎哉耶欤](?=[\u4e00-\u9fff])/);
      if (m) {
        cut = maxLen - 5 + m.index + 1;
      }
      result.push(text.slice(i, i + cut).trim());
      i += cut;
    }
    return result.filter(Boolean);
  }

  function findCitationBoundaries(text) {
    var boundaries = [0];
    CLASSICAL_PREFIXES.forEach(function (prefix) {
      var plen = prefix.length;
      var idx = 0;
      while ((idx = text.indexOf(prefix, idx)) !== -1) {
        // 前缀本身以文体词结尾（如水经注、西京杂记）可直接作为引用起点
        if (STYLE_WORDS.indexOf(prefix.charAt(plen - 1)) !== -1) {
          boundaries.push(idx);
          idx += 1;
          continue;
        }
        var after = text.slice(idx + plen, idx + plen + 10);
        var hasStyle = STYLE_WORDS.some(function (w) {
          var pos = after.indexOf(w);
          if (pos === -1 || pos > 6) return false;
          var before = after.slice(0, pos);
          return /^[\u4e00-\u9fff]{0,6}$/.test(before);
        });
        if (hasStyle) {
          boundaries.push(idx);
        }
        idx += 1;
      }
    });
    return boundaries.sort(function (a, b) { return a - b; }).filter(function (v, i, a) { return a.indexOf(v) === i; });
  }

  function splitAnnotationSentences(text) {
    var output = [];
    String(text).split("\n").forEach(function (part) {
      var line = part.trim();
      if (!line) return;
      line.split(/ {2,}/).forEach(function (sub) {
        sub = sub.trim();
        if (!sub) return;
        // 有标点则按标点切分
        if (/[。！？；]/.test(sub)) {
          sub.split(/(?<=[。！？；])/).forEach(function (sentence) {
            sentence = sentence.trim();
            if (sentence) output.push(sentence);
          });
          return;
        }
        // 无标点：先尝试按古籍引用边界切分
        var boundaries = findCitationBoundaries(sub);
        if (boundaries.length <= 1) {
          output.push.apply(output, semanticSplitAnnotation(sub, 38));
          return;
        }
        if (boundaries[boundaries.length - 1] !== sub.length) boundaries.push(sub.length);
        for (var i = 0; i < boundaries.length - 1; i++) {
          var piece = sub.slice(boundaries[i], boundaries[i + 1]).trim();
          if (!piece) continue;
          if (piece.length > 42) {
            output.push.apply(output, semanticSplitAnnotation(piece, 38));
          } else {
            output.push(piece);
          }
        }
      });
    });
    return output;
  }

  function noteItemHtml(note) {
    return '<li><span class="term">' + esc(note[0]) + "</span>" + esc(note[1]) + "</li>";
  }

  function classicalNoteItemHtml(note) {
    var sentences = splitAnnotationSentences(note[1]);
    var body = sentences.length > 1
      ? sentences.map(function (s) { return '<span class="note-sentence">' + esc(s) + "</span>"; }).join("")
      : esc(note[1]);
    return '<li><span class="term">' + esc(note[0]) + "</span>" + body + "</li>";
  }

  function renderClassicalText(text) {
    var sentences = splitAnnotationSentences(text);
    if (sentences.length <= 1) return esc(text);
    return sentences.map(function (s) { return '<span class="note-sentence">' + esc(s) + "</span>"; }).join("");
  }

  function isClassicalNote(note) {
    return /^(?:古注|古评|校注)·《/.test(String(note && note[0] || ""));
  }

  function isClassicalAppreciation(note) {
    return /^古评·《/.test(String(note && note[0] || ""));
  }

  function renderNoteList(notes) {
    return notes.map(noteItemHtml).join("");
  }

  function renderClassicalNoteList(notes) {
    return notes.map(classicalNoteItemHtml).join("");
  }

  function renderPoem(id, record, poetMatch) {
    var main = document.getElementById("poemMain");
    var title = record[0];
    var author = record[1];
    var genre = record[2] || "未知";
    var year = record[3] || "";
    var source = record[4] || "";
    var verse = record[5] || [];
    var context = record[6] || "";
    var notes = record[7] || [];
    var appreciation = record[8] || {};
    var famous = record[9] || [];
    var sources = record[10] || [];
    // 出处字段是数据管道标签，读者不需要看「chinese-poetry, MIT」这类术语
    var SOURCE_LABELS = {
      "《全唐诗》开放数据合并版（chinese-poetry，MIT）": "《全唐诗》开放底本",
      "项目既有整理本补录": "整理本补录",
      "石湖诗社": "石湖诗社"
    };
    var profile = poetMatch ? poetMatch.data : null;
    var dynasty = (profile && profile[5]) ? profile[5] : "今";
    var isModern = /^(?:新诗|现代诗|自由诗|白话诗)$/.test(genre);

    var verseHtml = "";
    verse.forEach(function (segment) {
      if (!String(segment).trim()) {
        verseHtml += '<p class="stanza-gap" aria-hidden="true"></p>';
        return;
      }
      splitSentences(segment).forEach(function (sentence) {
        verseHtml += "<p>" + esc(sentence) + "</p>";
      });
    });

    var contextHtml = context && String(context).trim()
      ? '<section class="section"><h2 class="section-title">题解 <span class="en">Context</span></h2><div class="section-body"><p>' + renderClassicalText(context) + "</p></div></section>"
      : "";

    var modernNotes = notes.filter(function (note) { return !isClassicalNote(note); });
    var classicalNotes = notes.filter(function (note) {
      return isClassicalNote(note) && !isClassicalAppreciation(note);
    });
    var classicalAppreciations = notes.filter(isClassicalAppreciation);
    var notesHtml = modernNotes.length
      ? '<section class="section"><h2 class="section-title">注释 <span class="en">Annotations</span></h2><ol class="notes-list">' + renderNoteList(modernNotes) + "</ol></section>"
      : "";
    var classicalHtml = "";
    if (classicalNotes.length) {
      var visible = classicalNotes.slice(0, 12);
      var remaining = classicalNotes.slice(12);
      var more = remaining.length
        ? '<details class="classical-more"><summary>展开其余 ' + remaining.length + ' 条古籍注释</summary><ol class="notes-list">' + renderClassicalNoteList(remaining) + "</ol></details>"
        : "";
      classicalHtml = '<section class="section secondary classical-commentary"><h2 class="section-title">古籍注释 <span class="en">Classical Annotations</span></h2><p class="classical-intro">以下为公版古籍中的字词、典故、校勘与诗意说明，按相邻诗句唯一匹配；保留古义与异文。</p><ol class="notes-list">' + renderClassicalNoteList(visible) + "</ol>" + more + "</section>";
    }

    var classicalAppreciationHtml = "";
    if (classicalAppreciations.length) {
      var visibleAppreciations = classicalAppreciations.slice(0, 12);
      var remainingAppreciations = classicalAppreciations.slice(12);
      var appreciationMore = remainingAppreciations.length
        ? '<details class="classical-more"><summary>展开其余 ' + remainingAppreciations.length + ' 条古籍赏评</summary><ol class="notes-list">' + renderClassicalNoteList(remainingAppreciations) + "</ol></details>"
        : "";
      classicalAppreciationHtml = '<section class="section secondary classical-appreciation"><h2 class="section-title">古籍赏评 <span class="en">Classical Appreciation</span></h2><p class="classical-intro">以下为公版选本与诗话中的古代品评，侧重章法、风格、炼字与历代接受；它与现代赏析分栏展示。</p><ol class="notes-list">' + renderClassicalNoteList(visibleAppreciations) + "</ol>" + appreciationMore + "</section>";
    }

    var appreciationHtml = "";
    if (appreciation && appreciation.body && appreciation.body.length) {
      var sourceNote = appreciation.source ? '<div class="source-note"><strong>出处：</strong>' + esc(appreciation.source) + "</div>" : "";
      var body = appreciation.body.map(function (paragraph) { return "<p>" + esc(paragraph) + "</p>"; }).join("");
      appreciationHtml = '<section class="section appreciation"><h2 class="section-title">赏析 <span class="en">Appreciation</span></h2>' + sourceNote + '<div class="section-body body">' + body + "</div></section>";
    }

    var famousHtml = "";
    if (famous.length) {
      var lines = famous.map(function (item) {
        return '<div class="line"><span class="text">' + esc(item[0]) + "</span>" + (item[1] ? '<span class="gloss">' + esc(item[1]) + "</span>" : "") + "</div>";
      }).join("");
      famousHtml = '<section class="section"><h2 class="section-title">名句 <span class="en">Famous Lines</span></h2><div class="famous-lines">' + lines + "</div></section>";
    }

    var sourcesHtml = "";
    if (sources.length) {
      sourcesHtml = '<section class="section secondary"><h2 class="section-title">出处溯源 <span class="en">Sources</span></h2><ul class="sources-list">' + sources.map(function (item) { return "<li>" + esc(item) + "</li>"; }).join("") + "</ul></section>";
    }

    main.innerHTML =
      '<header class="poem-header"><h1 class="poem-title">' + esc(title) + '</h1><div class="poem-byline"><span class="dynasty">' + esc(dynasty) + '</span><span class="author">' + esc(author) + '</span></div><div class="poem-meta">' + (isModern ? "" : '<div class="meta-item"><span class="meta-label">体裁</span><span class="meta-value">' + esc(genre) + "</span></div>") +
      (year ? '<div class="meta-item"><span class="meta-label">年代</span><span class="meta-value">' + esc(year) + "</span></div>" : "") +
      '<div class="meta-item"><span class="meta-label">出处</span><span class="meta-value">' + esc(SOURCE_LABELS[source] || source) + "</span></div></div></header>" +
      '<section class="poem-text"><div class="verse">' + verseHtml + "</div></section>" + contextHtml + notesHtml + classicalHtml + appreciationHtml + classicalAppreciationHtml + famousHtml + sourcesHtml;

    var description = (verse.length ? verse.join(" ").replace(/\s+/g, "").slice(0, 120) : title) + "… —— " + author + "《" + title + "》｜" + (window.BRAND ? window.BRAND.name : "石湖诗社") + "鉴赏";
    setSeoMeta(title + " · " + author + " · " + (window.BRAND ? window.BRAND.name : "石湖诗社"), description);
    document.getElementById("crumbAuthor").textContent = author + " 诗作";
    renderAside(id, author, poetMatch);
  }

  function renderAside(id, author, poetMatch) {
    var aside = document.getElementById("poetAside");
    // slim 索引字段：[0]=名 [1]=印章 [2]=英文名 [3]=有生平 [4]=分片号
    var profile = poetMatch ? poetMatch.data : null;
    var slug = poetMatch ? poetMatch.slug : "";
    var name = profile ? profile[0] : author;
    var seal = profile ? profile[1] : (author ? author.charAt(0) : "唐");
    var nameEn = profile ? profile[2] : "";
    var poetName = slug ? '<a href="./poet.html?id=' + encodeURIComponent(slug) + '">' + esc(name) + "</a>" : esc(name);

    aside.innerHTML =
      '<div class="poet-card" data-seal-char="' + esc(seal) + '"><div class="label">POET · 诗人</div><div class="name">' + poetName + "</div>" +
      (nameEn ? '<div class="name-en">' + esc(nameEn) + "</div>" : "") +
      '<p class="summary" id="asideSummary"></p>' +
      (profile && profile[3] ? '<button class="expand-btn" id="poetBtn" type="button">查看生平 <span class="arrow">▾</span></button>' : "") +
      '</div><div id="samePoetContainer"></div>';

    if (!profile || !slug) return;

    // 简介/同作者列表随对应分片异步补全，不阻塞正文渲染
    loadScript("./assets/js/poet-bio-shards/" + profile[4] + ".js?v=21").then(function () {
      var bio = (window.POET_BIO || {})[slug];
      if (!bio) return;
      var summaryBox = document.getElementById("asideSummary");
      if (summaryBox && bio[1]) summaryBox.textContent = bio[1];
    }).catch(function () { /* 侧栏简介缺失不影响正文 */ });

    loadScript("./assets/js/poet-work-shards/" + profile[4] + ".js?v=21").then(function () {
      var works = (window.POET_WORKS || {})[slug] || [];
      renderSamePoetWorks(id, author, slug, works);
    }).catch(function () {
      document.getElementById("samePoetContainer").innerHTML = '<p class="section-body">同作者诗作载入失败。</p>';
    });

    var biographyButton = document.getElementById("poetBtn");
    if (biographyButton) setupBiographyButton(biographyButton, slug, profile);
  }

  function renderSamePoetWorks(id, author, slug, works) {
    var container = document.getElementById("samePoetContainer");
    if (!works.length) return;
    var current = works.findIndex(function (work) { return work[0] === id; });
    var maximum = 80;
    var start = Math.max(0, current - 20);
    if (start + maximum > works.length) start = Math.max(0, works.length - maximum);
    var shown = works.slice(start, start + maximum);
    var items = shown.map(function (work) {
      var currentClass = work[0] === id ? ' class="current" aria-current="page"' : "";
      return '<li><a' + currentClass + ' href="./poem.html?id=' + encodeURIComponent(work[0]) + '"><span class="nm">' + esc(work[1]) + "</span>" + (work[2] ? '<span class="genre">' + esc(work[2]) + "</span>" : "") + "</a></li>";
    }).join("");
    var range = works.length > shown.length ? " · 当前显示第 " + (start + 1) + "—" + (start + shown.length) + " 首" : "";
    container.innerHTML = '<div class="same-poet"><div class="label">' + esc(author) + "卷 · 共 " + works.length + " 首" + range + "</div><ul>" + items + '</ul><a class="all-works" href="./poet.html?id=' + encodeURIComponent(slug) + '">查看全部 ' + works.length + " 首 →</a></div>";
  }

  function setupBiographyButton(button, slug, profile) {
    button.addEventListener("click", function () {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      var original = button.innerHTML;
      button.textContent = "正在载入生平…";
      // 生平数据在 bio 分片（约 33KB/片）；分片已随侧栏加载，此处通常直接命中
      loadScript("./assets/js/poet-bio-shards/" + profile[4] + ".js?v=21").then(function () {
        var bio = (window.POET_BIO || {})[slug];
        if (!bio) throw new Error("未找到诗人生平");
        document.getElementById("modalName").textContent = profile[0] || "";
        document.getElementById("modalSub").textContent = bio[4] || bio[3] || "";
        document.getElementById("modalLife").innerHTML = (bio[0] || []).map(function (paragraph) { return "<p>" + esc(paragraph) + "</p>"; }).join("");
        openModal(button);
      }).catch(function () {
        button.textContent = "生平载入失败，请重试";
      }).finally(function () {
        button.disabled = false;
        button.removeAttribute("aria-busy");
        if (button.textContent !== "生平载入失败，请重试") button.innerHTML = original;
      });
    });
  }

  function openModal(trigger) {
    lastFocus = trigger;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
    modalBox.focus();
  }

  function closeModal() {
    if (!modal.classList.contains("open")) return;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
    if (lastFocus) lastFocus.focus();
  }

  closeButton.addEventListener("click", closeModal);
  modal.addEventListener("click", function (event) { if (event.target === modal) closeModal(); });
  document.addEventListener("keydown", function (event) {
    if (!modal.classList.contains("open")) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeModal();
      return;
    }
    if (event.key !== "Tab") return;
    var focusable = Array.prototype.slice.call(modalBox.querySelectorAll('button:not([disabled]),a[href],[tabindex]:not([tabindex="-1"])'));
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (event.shiftKey && (document.activeElement === first || document.activeElement === modalBox)) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });

  var id = getParam("id");
  var main = document.getElementById("poemMain");
  main.innerHTML = '<p class="section-body" role="status">正在载入诗作…</p>';
  loadScript("./assets/js/poem-shards/" + poemShardName(id) + ".js?v=21").then(function () {
    var record = (window.POEM_SHARD || {})[id];
    if (!record) throw new Error("未找到诗作");
    renderPoem(id, record, findPoet(record[1]));
  }).catch(function () {
    main.innerHTML = '<header class="poem-header"><h1 class="poem-title">未找到</h1><p class="section-body">未找到诗作 <code>' + esc(id) + '</code>。请返回 <a href="./navigation.html">检索</a>。</p></header>';
  });
})();
