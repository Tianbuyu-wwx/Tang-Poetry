# -*- coding: utf-8 -*-
"""
生成 76 位诗人的详情页： website/poets/{poet-id}.html
数据来源： website/assets/js/poets-data.js （全站共享的 POETS_DATA）
诗作列表： 由 scripts/generate_poems.py 的 POEMS 按 poet_id 分组得到

设计：复用 poem.css 的视觉系统（水墨/宣纸/朱砂），与诗页面、诗人索引页一致。
结构：topbar → main(诗人身份卡 + 完整生平 + 诗作总览) → footer
"""
import os
import re
import importlib.util

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(BASE, "scripts", "generate_poems.py")
POETS_JS = os.path.join(BASE, "website", "assets", "js", "poets-data.js")
OUT_DIR = os.path.join(BASE, "website", "poets")

# ---------- 1. 加载 POEMS 分组 ----------
spec = importlib.util.spec_from_file_location("genp", GEN)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.load_extra_data()
POEMS = mod.POEMS

by_poet = {}
for p in POEMS:
    by_poet.setdefault(p["poet_id"], []).append(p)

# ---------- 2. 用 Node 提取 POETS_DATA（安全处理内嵌引号 / 生卒 / 生平） ----------
node_script = r'''
const fs = require('fs');
global.window = {};
global.document = { querySelector: function(){return null;}, getElementById: function(){return null;}, addEventListener: function(){} };
const code = fs.readFileSync(%r, 'utf8');
eval(code);
fs.writeFileSync(%r, JSON.stringify(window.POETS_DATA));
''' % (POETS_JS, os.path.join(BASE, "scripts", "poets_data_tmp.json"))
node_path = os.path.join(BASE, "scripts", "_extract_poets.js")
with open(node_path, "w", encoding="utf-8") as f:
    f.write(node_script)
# 用原生 Windows 路径调用 node，避免 MSYS 路径转换问题
import subprocess
ret = subprocess.run(["node", os.path.join(BASE, "scripts", "_extract_poets.js")],
                     cwd=BASE, capture_output=True, text=True)
if ret.returncode != 0:
    raise RuntimeError("node 提取失败: " + ret.stderr)
import json
with open(os.path.join(BASE, "scripts", "poets_data_tmp.json"), encoding="utf-8") as f:
    POETS_DATA = json.load(f)
os.remove(node_path)
os.remove(os.path.join(BASE, "scripts", "poets_data_tmp.json"))

# ---------- 3. HTML 转义 ----------
def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

# ---------- 4. 页面模板 ----------
PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} · 诗人 · 唐诗三百首</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;700;900&family=Ma+Shan+Zheng&family=ZCOOL+XiaoWei&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/css/poem.css?v=5">
<style>
  .poet-detail {{ max-width: 1080px; margin: 0 auto; padding: 3rem 3rem 5rem; position: relative; z-index: 2; }}
  .pd-head {{ display: flex; align-items: center; gap: 2rem; padding-bottom: 2.5rem; margin-bottom: 3rem; border-bottom: 1px solid var(--rule); position: relative; }}
  .pd-head::after {{ content: ""; position: absolute; left: 0; bottom: -1px; width: 60px; height: 2px; background: var(--cinnabar); }}
  .pd-seal {{ width: 86px; height: 86px; background: var(--cinnabar); color: var(--paper); display: grid; place-items: center; font-family: "Ma Shan Zheng", serif; font-size: 52px; border-radius: 4px; flex-shrink: 0; position: relative; box-shadow: inset 0 0 0 2px rgba(255,255,255,0.2), inset 0 0 0 3px var(--cinnabar), 0 4px 14px rgba(122,40,40,0.3); transform: rotate(-2deg); }}
  .pd-seal::before {{ content: ""; position: absolute; inset: 5px; border: 1px solid rgba(255,255,255,0.45); border-radius: 2px; }}
  .pd-title h1 {{ font-family: "Ma Shan Zheng", serif; font-size: 64px; letter-spacing: 10px; color: var(--ink-deep); line-height: 1; margin-bottom: 0.6rem; font-weight: 400; }}
  .pd-title .meta {{ font-family: "ZCOOL XiaoWei", serif; font-size: 15px; letter-spacing: 3px; color: var(--ink-light); }}
  .pd-summary {{ font-family: "Noto Serif SC", serif; font-size: 16px; line-height: 2; color: var(--ink); text-align: justify; text-justify: inter-character; margin-bottom: 3rem; padding: 1.5rem 1.8rem; background: linear-gradient(135deg, rgba(168,50,50,0.04), rgba(168,50,50,0.02)); border-left: 3px solid var(--cinnabar); }}
  .pd-section {{ margin: 2.8rem 0; }}
  .pd-section h2 {{ display: flex; align-items: center; gap: 0.9rem; font-family: "ZCOOL XiaoWei", serif; font-size: 22px; color: var(--ink-deep); letter-spacing: 4px; margin-bottom: 1.4rem; font-weight: 700; }}
  .pd-section h2::before {{ content: ""; width: 22px; height: 22px; background: var(--cinnabar); border-radius: 2px; flex-shrink: 0; box-shadow: inset 0 0 0 1.5px var(--paper); }}
  .pd-life p {{ font-family: "Noto Serif SC", serif; font-size: 15px; line-height: 2; color: var(--ink); text-align: justify; text-justify: inter-character; margin-bottom: 1rem; text-indent: 2em; }}
  .pd-life p:first-child::first-letter {{ font-family: "Ma Shan Zheng", serif; font-size: 2.4em; float: left; line-height: 0.95; padding: 0.1em 0.12em 0 0; color: var(--cinnabar); font-weight: 700; }}
  .pd-life p:last-child {{ margin-bottom: 0; }}
  .pd-poem-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem 1.4rem; }}
  .pd-poem {{ display: flex; align-items: baseline; justify-content: space-between; gap: 0.8rem; padding: 0.85rem 1.1rem; text-decoration: none; color: var(--ink); background: var(--paper-deep); border-left: 2px solid transparent; transition: all 0.2s; }}
  .pd-poem:hover {{ background: var(--paper); border-left-color: var(--cinnabar); transform: translateX(2px); }}
  .pd-poem .pt {{ font-family: "ZCOOL XiaoWei", serif; font-size: 17px; letter-spacing: 2px; }}
  .pd-poem .pg {{ font-family: "Noto Serif SC", serif; font-size: 11px; color: var(--ink-faint); letter-spacing: 1px; flex-shrink: 0; }}
  .pd-count {{ font-family: "ZCOOL XiaoWei", serif; font-size: 14px; color: var(--cinnabar); letter-spacing: 2px; }}
</style>
</head>
<body>

<header class="topbar">
  <a class="logo" href="../index.html">
    <div class="logo-seal"><span>唐</span></div>
    <div class="logo-text">
      <div class="t1">唐诗三百首</div>
      <div class="t2">Tang Poetry · 300</div>
    </div>
  </a>
  <div class="topbar-center">
    <div class="crumb">
      <a href="../index.html">首页</a>
      <span class="sep">›</span>
      <a href="index.html">诗人索引</a>
      <span class="sep">›</span>
      <span>{name}</span>
    </div>
  </div>
  <div class="topbar-right">
    <a class="nav-link" href="../navigation.html">导航</a>
  </div>
</header>

<main class="poet-detail">
  <header class="pd-head">
    <div class="pd-seal">{seal}</div>
    <div class="pd-title">
      <h1>{name}</h1>
      <div class="meta">{name_en}</div>
    </div>
  </header>

  <div class="pd-summary">{summary}</div>

  <section class="pd-section">
    <h2>生平 <span class="en" style="margin-left:.5rem;font-family:'Noto Serif SC';font-size:11px;letter-spacing:3px;color:var(--ink-faint);text-transform:uppercase;font-weight:400;">Biography</span></h2>
    <div class="pd-life">{life}</div>
  </section>

  <section class="pd-section">
    <h2>诗作总览 <span style="margin-left:.5rem;font-family:'Noto Serif SC';font-size:11px;letter-spacing:3px;color:var(--ink-faint);text-transform:uppercase;font-weight:400;">Works</span></h2>
    <p class="pd-count" style="margin-bottom:1.4rem;">本卷收录 {count} 首</p>
    <div class="pd-poem-grid">{poems}</div>
  </section>
</main>

<footer class="site">
  <div class="seal-line">
    <span class="mini-seal">唐</span>
    <span>唐诗三百首 · 鉴赏全集</span>
    <span class="mini-seal">詩</span>
  </div>
  <div>底本：现代增补版《唐诗三百首》｜ 赏析主要依据：上海辞书出版社《唐诗鉴赏辞典》（1983 年版）</div>
  <div>© 2026 唐诗三百首 · 仅用于学习与赏析</div>
</footer>

</body>
</html>
"""

os.makedirs(OUT_DIR, exist_ok=True)

# ---------- 5. 生成 ----------
gen_count = 0
for pid, info in POETS_DATA.items():
    poems = by_poet.get(pid, [])
    seal = info.get("sealChar", pid[0])
    name = info.get("name", pid).replace(" ", "")
    name_en = info.get("nameEn", "")
    summary = info.get("summary", "")
    life_paras = info.get("life", [])
    life_html = "".join("<p>%s</p>" % esc(p) for p in life_paras)

    # 按体裁分组排序，与诗页面"同卷诗作"顺序不同，这里按 POEMS 原顺序即可
    poems_html = ""
    for p in poems:
        title = esc(p["title"])
        genre = esc(p.get("genre", "").split(" ")[0].split("·")[0].strip())
        poems_html += '<a class="pd-poem" href="../poems/%s.html"><span class="pt">%s</span><span class="pg">%s</span></a>\n    ' % (p["id"], title, genre)

    html = PAGE.format(
        name=esc(name),
        seal=esc(seal),
        name_en=esc(name_en),
        summary=esc(summary),
        life=life_html,
        count=len(poems),
        poems=poems_html,
    )
    with open(os.path.join(OUT_DIR, pid + ".html"), "w", encoding="utf-8") as f:
        f.write(html)
    gen_count += 1

print("共生成 %d 个诗人详情页到 %s" % (gen_count, OUT_DIR))
