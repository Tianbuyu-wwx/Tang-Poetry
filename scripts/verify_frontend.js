/* 验证静态数据脚本和 HTML 内联脚本均可被 JavaScript 引擎解析。 */
"use strict";

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const website = path.join(root, "website");
const jsDirectory = path.join(website, "assets", "js");

function filesUnder(directory, extension) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) return filesUnder(target, extension);
    return entry.name.endsWith(extension) ? [target] : [];
  });
}

let checked = 0;
for (const file of filesUnder(jsDirectory, ".js")) {
  new Function(fs.readFileSync(file, "utf8"));
  checked += 1;
  console.log(`[OK] JavaScript：${path.relative(root, file)}`);
}

const inlinePattern = /<script(?![^>]*\bsrc\s*=)[^>]*>([\s\S]*?)<\/script>/gi;
for (const file of filesUnder(website, ".html")) {
  const html = fs.readFileSync(file, "utf8");
  let match;
  let inline = 0;
  while ((match = inlinePattern.exec(html)) !== null) {
    if (!match[1].trim()) continue;
    new Function(match[1]);
    inline += 1;
    checked += 1;
  }
  console.log(`[OK] HTML 内联脚本：${path.relative(root, file)}（${inline} 段）`);
}

console.log(`前端语法验证通过：共解析 ${checked} 段脚本。`);
