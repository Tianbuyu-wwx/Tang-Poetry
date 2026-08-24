/* 渲染冒烟测试：poet 页（slim + bio/works 分片）与 poem 页（slim 侧栏）。
   Node 环境模拟最小 DOM，断言真实产出内容。 */
"use strict";
const fs = require("fs");
const path = require("path");
const BASE = path.resolve(__dirname, "..", "website");

function loadWindow() {
  const w = {};
  global.window = w;
  const files = ["assets/js/poet-slim.js"];
  for (const f of files) {
    // eslint-disable-next-line no-eval
    eval(fs.readFileSync(path.join(BASE, f), "utf8"));
  }
  return w;
}

function makeDom() {
  const elements = {};
  function el(id) {
    if (!elements[id]) {
      elements[id] = {
        id,
        innerHTML: "",
        textContent: "",
        hidden: false,
        classList: { add() {}, remove() {}, contains: () => false },
        setAttribute() {},
        getAttribute: () => null,
        addEventListener() {},
        appendChild() {},
        querySelector: () => null,
        focus() {},
      };
    }
    return elements[id];
  }
  el("poetPage");
  el("crumbName");
  el("poetPen");
  el("poetBio");
  el("poetMain");
  el("crumbAuthor");
  el("asideSummary");
  return {
    el,
    getElementById: (id) => (elements[id] ? elements[id] : null),
    createElement: (tag) => ({ tag, setAttribute() {}, appendChild() {} }),
    querySelector: () => null,
    querySelectorAll: () => [],
    head: { appendChild() {} },
    addEventListener() {},
    title: "",
    readyState: "complete",
  };
}

const w = loadWindow();
console.log("POET_SLIM poets:", Object.keys(w.POET_SLIM).length);
if (Object.keys(w.POET_SLIM).length !== 3658) throw new Error("slim 覆盖数不对");

// 取一个有生平、作品多的诗人（杜甫 open_ 命名空间下按作者名找）
let duSlug = null;
for (const [slug, e] of Object.entries(w.POET_SLIM)) {
  if (e[0] === "杜甫") { duSlug = slug; break; }
}
console.log("杜甫 slug:", duSlug, "entry:", JSON.stringify(w.POET_SLIM[duSlug]));
if (!duSlug || !w.POET_SLIM[duSlug][3]) throw new Error("杜甫应有生平");

// 模拟 poet.html 环境：加载分片后校验 bio 与 works 都能取到
const shard = w.POET_SLIM[duSlug][4];
global.document = makeDom();
global.location = { search: "?id=" + duSlug };
delete global.window;
global.window = w;
// eslint-disable-next-line no-eval
eval(fs.readFileSync(path.join(BASE, "assets/js/poet-work-shards/" + shard + ".js"), "utf8"));
// eslint-disable-next-line no-eval
eval(fs.readFileSync(path.join(BASE, "assets/js/poet-bio-shards/" + shard + ".js"), "utf8"));
const works = (w.POET_WORKS || {})[duSlug] || [];
const bio = (w.POET_BIO || {})[duSlug];
console.log("杜甫 works:", works.length, "| life paras:", (bio[0] || []).length, "| summary:", String(bio[1]).slice(0, 30), "…");
if (!works.length) throw new Error("杜甫作品分片为空");
if (!bio || !(bio[0] || []).length) throw new Error("杜甫生平为空");

// poem.html：slim 反查（page-poem.js 的 findPoet 依赖 normalize 后的名字匹配）
const wanted = "杜甫";
let found = null;
for (const [slug2, e] of Object.entries(w.POET_SLIM)) {
  const norm = String(e[0]).replace(/\s+/g, "");
  if (norm === wanted) { found = slug2; break; }
}
console.log("poem 页反查杜甫 →", found);
if (!found) throw new Error("slim 反查失败");

console.log("SMOKE OK ✓");
