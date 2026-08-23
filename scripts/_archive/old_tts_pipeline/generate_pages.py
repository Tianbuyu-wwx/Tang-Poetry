# -*- coding: utf-8 -*-
"""
从 POEMS 数据自动生成 navigation.html（导航页）和 poets/index.html（诗人索引页）
"""
import os, importlib.util, json
from collections import defaultdict

# 加载所有诗数据
spec = importlib.util.spec_from_file_location('gp', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'generate_poems.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
POEMS = mod.POEMS
mod.load_extra_data()

# 加载诗人信息
POET_INFO = mod.POET_INFO

# 按诗人分组
by_poet = defaultdict(list)
for p in POEMS:
    by_poet[p['poet_id']].append(p)

# 按体裁分组
GENRE_MAP = {
    '五言绝句': '五绝', '七言绝句': '七绝', '五言律诗': '五律', '七言律诗': '七律',
    '五言古诗': '五古', '七言古诗': '七古', '五言排律': '五排', '七言排律': '七排',
}
def genre_short(genre):
    """提取体裁简称"""
    for k, v in GENRE_MAP.items():
        if k in genre:
            return v
    if '乐府' in genre:
        return '乐府'
    if '歌行' in genre:
        return '歌行'
    return genre[:2]

by_genre = defaultdict(list)
for p in POEMS:
    by_genre[genre_short(p['genre'])].append(p)

# 按主题分组（简单按诗题关键词）
THEME_KEYWORDS = [
    ('边塞征戍', ['边', '塞', '征', '戍', '关', '月', '军', '战', '将', '凉州', '出塞', '入塞']),
    ('山水田园', ['山', '水', '田', '园', '溪', '林', '野', '江', '湖', '村', '农', '渔', '柴']),
    ('送别赠答', ['送', '别', '赠', '寄', '酬', '答', '留别', '赠别']),
    ('咏史怀古', ['咏史', '怀古', '古迹', '故', '昔', '怀', '叹', '庙', '陵', '台', '楼']),
    ('宫怨闺情', ['宫', '怨', '闺', '春怨', '后宫', '玉台', '宫词']),
    ('羁旅乡思', ['旅', '宿', '泊', '夜', '行', '游', '望', '怀', '思', '归', '客']),
    ('饮酒咏怀', ['酒', '饮', '酌', '醉', '怀', '咏', '志']),
    ('写景四季', ['春', '夏', '秋', '冬', '雪', '雨', '风', '月', '日', '晓', '夜']),
]
by_theme = defaultdict(list)
for p in POEMS:
    title = p['title']
    matched = False
    for theme_name, keywords in THEME_KEYWORDS:
        if any(kw in title for kw in keywords):
            by_theme[theme_name].append(p)
            matched = True
            break
    if not matched:
        by_theme['其他'].append(p)

# 朝代排序
DYNASTY_ORDER = ['初唐', '盛唐', '中唐', '晚唐', '唐', '五代']
def dynasty_rank(poet_id):
    info = POET_INFO.get(poet_id, ('?', '?', '?', '?', '?'))
    sub = info[4]
    for i, d in enumerate(DYNASTY_ORDER):
        if d in sub:
            return i
    return len(DYNASTY_ORDER)

# ============================================================
# 生成 navigation.html
# ============================================================

WEBSITE_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'website'))

def poet_display_name(poet_id):
    info = POET_INFO.get(poet_id)
    if info:
        return info[1]
    return poet_id

def poet_dynasty(poet_id):
    info = POET_INFO.get(poet_id)
    if info:
        sub = info[4]
        for d in DYNASTY_ORDER:
            if d in sub:
                return d
    return '唐'

def poet_en_name(poet_id):
    info = POET_INFO.get(poet_id)
    if info:
        return info[2].split(' · ')[0] if ' · ' in info[2] else info[2]
    return ''

# 按 (朝代, 诗数降序, 诗人名) 排序
sorted_poets = sorted(by_poet.keys(),
                     key=lambda pid: (dynasty_rank(pid), -len(by_poet[pid]), poet_display_name(pid)))

nav_html_parts = []
nav_html_parts.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>导航 · 唐诗三百首</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;700;900&family=Ma+Shan+Zheng&family=ZCOOL+XiaoWei&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/css/poem.css?v=5">
<style>
  .nav-page { max-width: 1280px; margin: 0 auto; padding: 3rem 3rem 5rem; position: relative; z-index: 2; }
  .nav-header { text-align: center; margin-bottom: 3rem; }
  .nav-header h1 { font-family: "Ma Shan Zheng", serif; font-size: 64px; letter-spacing: 12px; color: var(--ink-deep); margin-bottom: 0; font-weight: 400; }
  .search-box { max-width: 560px; margin: 0 auto 2.5rem; position: relative; }
  .search-box input { width: 100%; padding: 0.85rem 1.2rem 0.85rem 2.8rem; background: var(--paper); border: none; border-bottom: 2px solid var(--rule); font-family: "ZCOOL XiaoWei", "STKaiti", serif; font-size: 16px; letter-spacing: 3px; color: var(--ink); outline: none; transition: all 0.3s; }
  .search-box input::placeholder { color: var(--ink-faint); letter-spacing: 4px; }
  .search-box input:focus { border-bottom-color: var(--cinnabar); background: var(--paper-warm); }
  .search-box::before { content: "🔍"; position: absolute; left: 1rem; top: 50%; transform: translateY(-50%); font-size: 16px; opacity: 0.5; pointer-events: none; }
  .search-box .clear-btn { position: absolute; right: 0.8rem; top: 50%; transform: translateY(-50%); background: none; border: none; font-size: 18px; color: var(--ink-faint); cursor: pointer; padding: 4px 8px; display: none; }
  .search-box .clear-btn.show { display: block; }
  .search-box .clear-btn:hover { color: var(--cinnabar); }
  .search-summary { text-align: center; font-family: "ZCOOL XiaoWei", serif; font-size: 13px; color: var(--ink-light); letter-spacing: 2px; margin-bottom: 1.5rem; min-height: 1.2em; }
  .search-summary .num { color: var(--cinnabar); font-weight: 700; }
  .tabs { display: flex; justify-content: center; gap: 0; margin-bottom: 3rem; border-bottom: 1px solid var(--rule); }
  .tab { background: none; border: none; padding: 1rem 2.5rem; font-family: "ZCOOL XiaoWei", serif; font-size: 18px; letter-spacing: 4px; color: var(--ink-light); cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.3s; }
  .tab:hover { color: var(--ink); }
  .tab.active { color: var(--cinnabar); border-bottom-color: var(--cinnabar); }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }
  .poet-section { margin-bottom: 3rem; padding-bottom: 2rem; border-bottom: 1px dashed var(--rule); }
  .poet-section:last-child { border-bottom: none; }
  .poet-section-header { display: flex; align-items: baseline; gap: 1rem; margin-bottom: 1.2rem; flex-wrap: wrap; }
  .poet-section-header .dynasty { font-family: "ZCOOL XiaoWei", serif; font-size: 14px; color: var(--cinnabar); padding: 2px 10px; border: 1px solid var(--cinnabar); border-radius: 2px; letter-spacing: 2px; }
  .poet-section-header .poet-name { font-family: "Ma Shan Zheng", serif; font-size: 28px; color: var(--ink-deep); letter-spacing: 4px; }
  .poet-section-header .poet-en { font-size: 13px; color: var(--ink-faint); letter-spacing: 1px; }
  .poet-section-header .count { margin-left: auto; font-family: "ZCOOL XiaoWei", serif; font-size: 14px; color: var(--ink-light); }
  .poem-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px 16px; }
  .poem-link { display: flex; align-items: baseline; gap: 8px; padding: 6px 10px; text-decoration: none; color: var(--ink); border-left: 2px solid transparent; transition: all 0.2s; font-size: 14px; }
  .poem-link:hover { background: var(--paper-deep); border-left-color: var(--cinnabar); }
  .poem-link .title { flex: 1; font-family: "Noto Serif SC", serif; }
  .poem-link .genre { font-size: 12px; color: var(--ink-faint); font-family: "ZCOOL XiaoWei", serif; }
  .poem-link.hidden { display: none; }
  .poet-section.hidden { display: none; }
  .genre-section.hidden { display: none; }
  .genre-section { margin-bottom: 3rem; }
  .genre-section h3 { font-family: "Ma Shan Zheng", serif; font-size: 28px; color: var(--ink-deep); margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--rule); letter-spacing: 4px; }
  .genre-section .count { font-size: 14px; color: var(--ink-light); font-family: "ZCOOL XiaoWei", serif; margin-left: 1rem; }
  /* 紧凑 topbar（覆盖 poem.css 的诗页面版） */
  .topbar { position: sticky; top: 0; background: rgba(250,246,237,0.95); border-bottom: 1px solid var(--rule); padding: 0.7rem 2rem; display: flex; justify-content: space-between; align-items: center; z-index: 100; backdrop-filter: blur(8px); grid-template-columns: auto 1fr auto; gap: 1.2rem; }
  .topbar .logo { display: flex; align-items: center; gap: 0.7rem; text-decoration: none; color: var(--ink-deep); }
  .topbar .logo-seal { width: 40px; height: 40px; background: var(--cinnabar); border-radius: 3px; display: grid; place-items: center; position: relative; box-shadow: inset 0 0 0 2px rgba(255,255,255,0.18), inset 0 0 0 3px var(--cinnabar), 0 2px 6px rgba(122,40,40,0.25); transform: rotate(-1.5deg); }
  .topbar .logo-seal::before { content: ""; position: absolute; inset: 3px; border: 1px solid rgba(255,255,255,0.4); border-radius: 2px; }
  .topbar .logo-seal span { font-family: "Ma Shan Zheng", "STKaiti", serif; font-size: 24px; color: var(--paper); font-weight: 700; line-height: 1; letter-spacing: -1px; text-shadow: 0 1px 0 rgba(122,40,40,0.4); position: relative; z-index: 1; }
  .topbar .logo-text { display: flex; flex-direction: column; line-height: 1.15; }
  .topbar .logo-text .t1 { font-family: "ZCOOL XiaoWei", "STKaiti", serif; font-size: 18px; font-weight: 700; letter-spacing: 3px; color: var(--ink-deep); }
  .topbar .logo-text .t2 { font-family: "Noto Serif SC", serif; font-size: 9px; letter-spacing: 2px; color: var(--ink-light); text-transform: uppercase; margin-top: 1px; }
  .topbar nav { display: flex; gap: 1.5rem; }
  .topbar nav a { color: var(--ink-light); text-decoration: none; font-family: "ZCOOL XiaoWei", serif; font-size: 14px; letter-spacing: 2px; transition: color 0.2s; border-bottom: 1px solid transparent; padding-bottom: 2px; }
  .topbar nav a:hover { color: var(--cinnabar); border-bottom-color: var(--cinnabar); }
  .topbar nav a.current { color: var(--cinnabar); border-bottom-color: var(--cinnabar); }
  .footer { text-align: center; padding: 2rem; color: var(--ink-light); font-size: 13px; border-top: 1px solid var(--rule); margin-top: 4rem; font-family: "ZCOOL XiaoWei", serif; letter-spacing: 2px; position: relative; z-index: 2; }
</style>
</head>
<body>
<header class="topbar">
  <a class="logo" href="index.html">
    <div class="logo-seal"><span>唐</span></div>
    <div class="logo-text">
      <div class="t1">唐诗三百首</div>
      <div class="t2">Tang Poetry · 300</div>
    </div>
  </a>
  <div></div>
  <nav>
    <a href="index.html">首页</a>
    <a href="navigation.html" class="current">导航</a>
    <a href="poets/index.html">诗人</a>
    <a href="about.html">关于</a>
  </nav>
</header>
<main class="nav-page">
  <header class="nav-header">
    <h1>导 航</h1>
  </header>
  <div class="search-box">
    <input type="text" id="searchInput" placeholder="检索诗题、诗人、体裁…" autocomplete="off">
    <button class="clear-btn" id="searchClear" aria-label="清除">×</button>
  </div>
  <div class="search-summary" id="searchSummary"></div>
  <div class="tabs">
    <button class="tab active" data-tab="by-poet">按诗人</button>
    <button class="tab" data-tab="by-genre">按体裁</button>
    <button class="tab" data-tab="by-theme">按主题</button>
  </div>
''')

# 按诗人分卷
nav_html_parts.append('  <div class="tab-panel active" id="by-poet">\n')
for poet_id in sorted_poets:
    poems = by_poet[poet_id]
    dynasty = poet_dynasty(poet_id)
    name = poet_display_name(poet_id)
    en = poet_en_name(poet_id)
    nav_html_parts.append(f'    <div class="poet-section" data-poet-name="{name}">\n')
    nav_html_parts.append(f'      <div class="poet-section-header">\n')
    nav_html_parts.append(f'        <span class="dynasty">{dynasty}</span>\n')
    nav_html_parts.append(f'        <span class="poet-name">{name}</span>\n')
    if en:
        nav_html_parts.append(f'        <span class="poet-en">{en}</span>\n')
    nav_html_parts.append(f'        <span class="count">{len(poems)} 首</span>\n')
    nav_html_parts.append(f'      </div>\n      <div class="poem-grid">\n')
    for p in poems:
        gs = genre_short(p['genre'])
        nav_html_parts.append(f'        <a class="poem-link" href="poems/{p["id"]}.html" data-title="{p["title"]}" data-poet="{name}" data-genre="{gs}"><span class="title">{p["title"]}</span><span class="genre">{gs}</span></a>\n')
    nav_html_parts.append('      </div>\n    </div>\n')
nav_html_parts.append('  </div>\n')

# 按体裁
nav_html_parts.append('  <div class="tab-panel" id="by-genre">\n')
genre_order = ['五绝', '七绝', '五律', '七律', '五古', '七古', '五排', '乐府', '歌行']
for gs in genre_order:
    if gs in by_genre:
        poems = by_genre[gs]
        nav_html_parts.append(f'    <div class="genre-section" data-genre="{gs}">\n')
        nav_html_parts.append(f'      <h3>{gs}<span class="count">共 {len(poems)} 首</span></h3>\n')
        nav_html_parts.append(f'      <div class="poem-grid">\n')
        for p in poems:
            nav_html_parts.append(f'        <a class="poem-link" href="poems/{p["id"]}.html" data-title="{p["title"]}" data-poet="{p["author"]}" data-genre="{gs}"><span class="title">{p["title"]}</span><span class="genre">{p["author"]}</span></a>\n')
        nav_html_parts.append('      </div>\n    </div>\n')
nav_html_parts.append('  </div>\n')

# 按主题
nav_html_parts.append('  <div class="tab-panel" id="by-theme">\n')
for theme_name in [t[0] for t in THEME_KEYWORDS] + ['其他']:
    if theme_name in by_theme:
        poems = by_theme[theme_name]
        nav_html_parts.append(f'    <div class="genre-section" data-theme="{theme_name}">\n')
        nav_html_parts.append(f'      <h3>{theme_name}<span class="count">共 {len(poems)} 首</span></h3>\n')
        nav_html_parts.append(f'      <div class="poem-grid">\n')
        for p in poems:
            gs = genre_short(p['genre'])
            nav_html_parts.append(f'        <a class="poem-link" href="poems/{p["id"]}.html" data-title="{p["title"]}" data-poet="{p["author"]}" data-genre="{gs}"><span class="title">{p["title"]}</span><span class="genre">{p["author"]}</span></a>\n')
        nav_html_parts.append('      </div>\n    </div>\n')
nav_html_parts.append('  </div>\n')

nav_html_parts.append('''</main>
<footer class="footer">
  <div>底本：现代增补版《唐诗三百首》｜ 赏析主要依据：上海辞书出版社《唐诗鉴赏辞典》（1983 年版）</div>
  <div>© 2026 唐诗三百首 · 仅用于学习与赏析</div>
</footer>
<script>
  // Tab 切换
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(tab.dataset.tab).classList.add('active');
      runSearch();
    });
  });
  // 搜索过滤
  var searchInput = document.getElementById('searchInput');
  var searchClear = document.getElementById('searchClear');
  var searchSummary = document.getElementById('searchSummary');
  function runSearch() {
    var q = searchInput.value.trim().toLowerCase();
    searchClear.classList.toggle('show', q.length > 0);
    var total = 0, matched = 0;
    document.querySelectorAll('.tab-panel.active .poem-link').forEach(function(link) {
      total++;
      if (!q) { link.classList.remove('hidden'); matched++; return; }
      var title = (link.dataset.title || '').toLowerCase();
      var poet = (link.dataset.poet || '').toLowerCase();
      var genre = (link.dataset.genre || '').toLowerCase();
      if (title.indexOf(q) !== -1 || poet.indexOf(q) !== -1 || genre.indexOf(q) !== -1) {
        link.classList.remove('hidden');
        matched++;
      } else {
        link.classList.add('hidden');
      }
    });
    // 隐藏空 section
    document.querySelectorAll('.tab-panel.active .poet-section, .tab-panel.active .genre-section').forEach(function(sec) {
      var visible = sec.querySelectorAll('.poem-link:not(.hidden)').length;
      sec.classList.toggle('hidden', visible === 0);
    });
    if (q) {
      searchSummary.innerHTML = '检索 <span class="num">"' + q + '"</span> · 命中 <span class="num">' + matched + '</span> / ' + total + ' 首';
    } else {
      searchSummary.innerHTML = '';
    }
  }
  searchInput.addEventListener('input', runSearch);
  searchClear.addEventListener('click', function() {
    searchInput.value = '';
    runSearch();
    searchInput.focus();
  });
</script>
</body>
</html>
''')

nav_path = os.path.join(WEBSITE_DIR, 'navigation.html')
with open(nav_path, 'w', encoding='utf-8') as f:
    f.write(''.join(nav_html_parts))
print(f'生成 navigation.html ({len(POEMS)} 首诗, {len(by_poet)} 位诗人)')

# ============================================================
# 生成 poets/index.html
# ============================================================

poets_html_parts = []
poets_html_parts.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>诗人索引 · 唐诗三百首</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;700;900&family=Ma+Shan+Zheng&family=ZCOOL+XiaoWei&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/css/poem.css?v=5">
<style>
  .poets-page { max-width: 1280px; margin: 0 auto; padding: 3rem 3rem 5rem; position: relative; z-index: 2; }
  .poets-header { text-align: center; margin-bottom: 4rem; padding-bottom: 2.5rem; border-bottom: 1px solid var(--rule); position: relative; }
  .poets-header::after { content: ""; position: absolute; left: 50%; bottom: -1px; transform: translateX(-50%); width: 80px; height: 2px; background: var(--cinnabar); }
  .poets-header h1 { font-family: "Ma Shan Zheng", serif; font-size: 64px; letter-spacing: 12px; color: var(--ink-deep); margin-bottom: 0.5rem; font-weight: 400; }
  .poets-header .sub { font-family: "ZCOOL XiaoWei", serif; font-size: 16px; letter-spacing: 6px; color: var(--ink-light); }
  .poet-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; }
  .poet-card { background: var(--paper-deep); padding: 1.5rem; border-left: 3px solid var(--cinnabar); text-decoration: none; color: var(--ink); transition: all 0.3s; cursor: pointer; position: relative; }
  .poet-card:hover { background: var(--paper); box-shadow: 0 4px 16px rgba(0,0,0,0.08); transform: translateY(-2px); }
  .poet-card .head { display: flex; align-items: center; gap: 1rem; margin-bottom: 0.8rem; }
  .poet-card .seal { width: 48px; height: 48px; background: var(--cinnabar); color: var(--paper); display: flex; align-items: center; justify-content: center; font-family: "Ma Shan Zheng", serif; font-size: 28px; border-radius: 2px; flex-shrink: 0; }
  .poet-card .info { flex: 1; }
  .poet-card .name { font-family: "Ma Shan Zheng", serif; font-size: 24px; color: var(--ink-deep); letter-spacing: 3px; }
  .poet-card .meta { font-size: 12px; color: var(--ink-faint); letter-spacing: 1px; margin-top: 2px; font-family: "ZCOOL XiaoWei", serif; }
  .poet-card .summary { font-size: 13px; color: var(--ink-light); line-height: 1.6; margin-bottom: 0.6rem; }
  .poet-card .count { font-size: 13px; color: var(--cinnabar); font-family: "ZCOOL XiaoWei", serif; letter-spacing: 2px; }
  /* 紧凑 topbar */
  .topbar { position: sticky; top: 0; background: rgba(250,246,237,0.95); border-bottom: 1px solid var(--rule); padding: 0.7rem 2rem; display: flex; justify-content: space-between; align-items: center; z-index: 100; backdrop-filter: blur(8px); gap: 1.2rem; }
  .topbar .logo { display: flex; align-items: center; gap: 0.7rem; text-decoration: none; color: var(--ink-deep); }
  .topbar .logo-seal { width: 40px; height: 40px; background: var(--cinnabar); border-radius: 3px; display: grid; place-items: center; position: relative; box-shadow: inset 0 0 0 2px rgba(255,255,255,0.18), inset 0 0 0 3px var(--cinnabar), 0 2px 6px rgba(122,40,40,0.25); transform: rotate(-1.5deg); }
  .topbar .logo-seal::before { content: ""; position: absolute; inset: 3px; border: 1px solid rgba(255,255,255,0.4); border-radius: 2px; }
  .topbar .logo-seal span { font-family: "Ma Shan Zheng", "STKaiti", serif; font-size: 24px; color: var(--paper); font-weight: 700; line-height: 1; letter-spacing: -1px; text-shadow: 0 1px 0 rgba(122,40,40,0.4); position: relative; z-index: 1; }
  .topbar .logo-text { display: flex; flex-direction: column; line-height: 1.15; }
  .topbar .logo-text .t1 { font-family: "ZCOOL XiaoWei", "STKaiti", serif; font-size: 18px; font-weight: 700; letter-spacing: 3px; color: var(--ink-deep); }
  .topbar .logo-text .t2 { font-family: "Noto Serif SC", serif; font-size: 9px; letter-spacing: 2px; color: var(--ink-light); text-transform: uppercase; margin-top: 1px; }
  .topbar nav { display: flex; gap: 1.5rem; }
  .topbar nav a { color: var(--ink-light); text-decoration: none; font-family: "ZCOOL XiaoWei", serif; font-size: 14px; letter-spacing: 2px; transition: color 0.2s; border-bottom: 1px solid transparent; padding-bottom: 2px; }
  .topbar nav a:hover { color: var(--cinnabar); border-bottom-color: var(--cinnabar); }
  .topbar nav a.current { color: var(--cinnabar); border-bottom-color: var(--cinnabar); }
  .footer { text-align: center; padding: 2rem; color: var(--ink-light); font-size: 13px; border-top: 1px solid var(--rule); margin-top: 4rem; font-family: "ZCOOL XiaoWei", serif; letter-spacing: 2px; position: relative; z-index: 2; }
  .poet-modal-backdrop { position: fixed; inset: 0; background: rgba(26,26,26,0.6); backdrop-filter: blur(4px); display: none; align-items: center; justify-content: center; z-index: 1000; padding: 2rem; }
  .poet-modal-backdrop.open { display: flex; }
  .poet-modal { background: var(--paper); max-width: 720px; width: 100%; max-height: 80vh; overflow-y: auto; padding: 3rem; position: relative; border-left: 4px solid var(--cinnabar); }
  .poet-modal .close { position: absolute; top: 1rem; right: 1.5rem; background: none; border: none; font-size: 24px; color: var(--ink-light); cursor: pointer; }
  .poet-modal h2 { font-family: "Ma Shan Zheng", serif; font-size: 36px; color: var(--ink-deep); letter-spacing: 6px; margin-bottom: 0.5rem; }
  .poet-modal .en { font-size: 13px; color: var(--ink-faint); letter-spacing: 1px; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--rule); }
  .poet-modal .life p { font-size: 14px; line-height: 1.8; color: var(--ink); margin-bottom: 1rem; text-indent: 2em; }
  .poet-modal .poems-section { margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid var(--rule); }
  .poet-modal .poems-section h3 { font-family: "Ma Shan Zheng", serif; font-size: 20px; color: var(--ink-deep); letter-spacing: 3px; margin-bottom: 1rem; }
  .poet-modal .poems-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 6px 12px; }
  .poet-modal .poem-item { display: flex; align-items: baseline; gap: 8px; padding: 6px 10px; text-decoration: none; color: var(--ink); border-left: 2px solid transparent; transition: all 0.2s; }
  .poet-modal .poem-item:hover { background: var(--paper-deep); border-left-color: var(--cinnabar); }
  .poet-modal .poem-item .pt { flex: 1; font-family: "Noto Serif SC", serif; font-size: 14px; }
  .poet-modal .poem-item .pg { font-size: 11px; color: var(--ink-faint); font-family: "ZCOOL XiaoWei", serif; }
  .poet-modal .poems-list .empty { color: var(--ink-faint); font-size: 13px; text-align: center; padding: 1rem; }
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
  <nav>
    <a href="../index.html">首页</a>
    <a href="../navigation.html">导航</a>
    <a href="../poets/index.html" class="current">诗人</a>
    <a href="../about.html">关于</a>
  </nav>
</header>
<main class="poets-page">
  <header class="poets-header">
    <h1>诗人索引</h1>
    <div class="sub">共 ''' + str(len(by_poet)) + ''' 位诗人 · ''' + str(len(POEMS)) + ''' 首诗作</div>
  </header>
  <div class="poet-grid" id="poetGrid">
''')

for poet_id in sorted_poets:
    poems = by_poet[poet_id]
    info = POET_INFO.get(poet_id)
    if info:
        seal, name, en, summary, sub = info
    else:
        seal, name, en, summary, sub = '?', poet_id, '', '', ''
    dynasty = poet_dynasty(poet_id)
    # 构造诗作列表 JSON（id + title + genre）
    import json as _json
    poems_json = _json.dumps([{'id': p['id'], 'title': p['title'], 'genre': genre_short(p['genre'])} for p in poems], ensure_ascii=False)
    poets_html_parts.append(f'''    <div class="poet-card" id="{poet_id}" data-poet-id="{poet_id}" data-poems='{poems_json}'>
      <div class="head">
        <span class="seal">{seal}</span>
        <div class="info">
          <div class="name">{name}</div>
          <div class="meta">{sub}</div>
        </div>
      </div>
      <div class="summary">{summary[:80]}{'…' if len(summary) > 80 else ''}</div>
      <div class="count">{len(poems)} 首诗作 →</div>
    </div>
''')

poets_html_parts.append('''  </div>
</main>
<footer class="footer">
  <div>底本：现代增补版《唐诗三百首》｜ 赏析主要依据：上海辞书出版社《唐诗鉴赏辞典》（1983 年版）</div>
  <div>© 2026 唐诗三百首 · 仅用于学习与赏析</div>
</footer>
<div class="poet-modal-backdrop" id="poetModal">
  <div class="poet-modal">
    <button class="close" id="poetClose">×</button>
    <h2 id="poetModalName"></h2>
    <div class="en" id="poetModalEn"></div>
    <div class="life" id="poetModalLife"></div>
    <div class="poems-section">
      <h3>收录诗作</h3>
      <div class="poems-list" id="poetModalPoems"></div>
    </div>
  </div>
</div>
<script src="../assets/js/poets-data.js?v=5"></script>
<script>
  function showPoet(pid) {
    const card = document.getElementById(pid);
    if (!card) return;
    const p = window.POETS_DATA[pid];
    if (!p) return;
    document.getElementById('poetModalName').textContent = p.name;
    document.getElementById('poetModalEn').textContent = p.nameEn + ' · ' + p.dynasty;
    document.getElementById('poetModalLife').innerHTML = p.life.map(s => '<p>' + s + '</p>').join('');
    // 渲染诗作列表
    var poems = [];
    try { poems = JSON.parse(card.dataset.poems || '[]'); } catch(e) {}
    var listEl = document.getElementById('poetModalPoems');
    if (poems.length === 0) {
      listEl.innerHTML = '<p class="empty">暂无收录</p>';
    } else {
      listEl.innerHTML = poems.map(function(pm) {
        return '<a class="poem-item" href="../poems/' + pm.id + '.html"><span class="pt">' + pm.title + '</span><span class="pg">' + pm.genre + '</span></a>';
      }).join('');
    }
    document.getElementById('poetModal').classList.add('open');
  }
  // 诗人卡片点击 -> 显示浮窗
  document.querySelectorAll('.poet-card').forEach(card => {
    card.addEventListener('click', () => showPoet(card.dataset.poetId));
  });
  document.getElementById('poetClose').addEventListener('click', () => {
    document.getElementById('poetModal').classList.remove('open');
  });
  document.getElementById('poetModal').addEventListener('click', (e) => {
    if (e.target.id === 'poetModal') {
      document.getElementById('poetModal').classList.remove('open');
    }
  });
  // 通过 hash 自动定位并打开诗人浮窗
  if (location.hash) {
    const pid = location.hash.slice(1);
    setTimeout(() => {
      const card = document.getElementById(pid);
      if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.style.outline = '2px solid var(--cinnabar)';
        setTimeout(() => { card.style.outline = ''; }, 2000);
      }
      showPoet(pid);
    }, 300);
  }
</script>
</body>
</html>
''')

poets_dir = os.path.join(WEBSITE_DIR, 'poets')
os.makedirs(poets_dir, exist_ok=True)
poets_path = os.path.join(poets_dir, 'index.html')
with open(poets_path, 'w', encoding='utf-8') as f:
    f.write(''.join(poets_html_parts))
print(f'生成 poets/index.html ({len(by_poet)} 位诗人)')

# ============================================================
# 生成 about.html
# ============================================================

about_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>关于 · 唐诗三百首</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;700;900&family=Ma+Shan+Zheng&family=ZCOOL+XiaoWei&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/css/poem.css?v=5">
<style>
  .about-page { max-width: 820px; margin: 0 auto; padding: 3rem 2rem 5rem; position: relative; z-index: 2; }
  .about-header { text-align: center; margin-bottom: 4rem; padding-bottom: 2.5rem; border-bottom: 1px solid var(--rule); position: relative; }
  .about-header::after { content: ""; position: absolute; left: 50%; bottom: -1px; transform: translateX(-50%); width: 80px; height: 2px; background: var(--cinnabar); }
  .about-header h1 { font-family: "Ma Shan Zheng", serif; font-size: 64px; letter-spacing: 12px; color: var(--ink-deep); margin-bottom: 0.5rem; font-weight: 400; }
  .about-header .sub { font-family: "ZCOOL XiaoWei", serif; font-size: 16px; letter-spacing: 6px; color: var(--ink-light); }
  .about-section { margin-bottom: 3rem; }
  .about-section h2 { font-family: "Ma Shan Zheng", serif; font-size: 32px; color: var(--ink-deep); letter-spacing: 6px; margin-bottom: 1.5rem; padding-left: 1rem; border-left: 4px solid var(--cinnabar); }
  .about-section p { font-size: 15px; line-height: 2; color: var(--ink); margin-bottom: 1rem; text-indent: 2em; }
  .about-section ul { padding-left: 2em; }
  .about-section li { font-size: 15px; line-height: 2; color: var(--ink); margin-bottom: 0.5rem; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1.5rem; margin: 2rem 0; }
  .stat { text-align: center; padding: 1.5rem; background: var(--paper-deep); border-top: 2px solid var(--cinnabar); }
  .stat .num { font-family: "Ma Shan Zheng", serif; font-size: 40px; color: var(--cinnabar); letter-spacing: 2px; }
  .stat .label { font-family: "ZCOOL XiaoWei", serif; font-size: 14px; color: var(--ink-light); letter-spacing: 3px; margin-top: 0.5rem; }
  /* 紧凑 topbar */
  .topbar { position: sticky; top: 0; background: rgba(250,246,237,0.95); border-bottom: 1px solid var(--rule); padding: 0.7rem 2rem; display: flex; justify-content: space-between; align-items: center; z-index: 100; backdrop-filter: blur(8px); gap: 1.2rem; }
  .topbar .logo { display: flex; align-items: center; gap: 0.7rem; text-decoration: none; color: var(--ink-deep); }
  .topbar .logo-seal { width: 40px; height: 40px; background: var(--cinnabar); border-radius: 3px; display: grid; place-items: center; position: relative; box-shadow: inset 0 0 0 2px rgba(255,255,255,0.18), inset 0 0 0 3px var(--cinnabar), 0 2px 6px rgba(122,40,40,0.25); transform: rotate(-1.5deg); }
  .topbar .logo-seal::before { content: ""; position: absolute; inset: 3px; border: 1px solid rgba(255,255,255,0.4); border-radius: 2px; }
  .topbar .logo-seal span { font-family: "Ma Shan Zheng", "STKaiti", serif; font-size: 24px; color: var(--paper); font-weight: 700; line-height: 1; letter-spacing: -1px; text-shadow: 0 1px 0 rgba(122,40,40,0.4); position: relative; z-index: 1; }
  .topbar .logo-text { display: flex; flex-direction: column; line-height: 1.15; }
  .topbar .logo-text .t1 { font-family: "ZCOOL XiaoWei", "STKaiti", serif; font-size: 18px; font-weight: 700; letter-spacing: 3px; color: var(--ink-deep); }
  .topbar .logo-text .t2 { font-family: "Noto Serif SC", serif; font-size: 9px; letter-spacing: 2px; color: var(--ink-light); text-transform: uppercase; margin-top: 1px; }
  .topbar nav { display: flex; gap: 1.5rem; }
  .topbar nav a { color: var(--ink-light); text-decoration: none; font-family: "ZCOOL XiaoWei", serif; font-size: 14px; letter-spacing: 2px; transition: color 0.2s; border-bottom: 1px solid transparent; padding-bottom: 2px; }
  .topbar nav a:hover { color: var(--cinnabar); border-bottom-color: var(--cinnabar); }
  .topbar nav a.current { color: var(--cinnabar); border-bottom-color: var(--cinnabar); }
  .footer { text-align: center; padding: 2rem; color: var(--ink-light); font-size: 13px; border-top: 1px solid var(--rule); margin-top: 4rem; font-family: "ZCOOL XiaoWei", serif; letter-spacing: 2px; position: relative; z-index: 2; }
</style>
</head>
<body>
<header class="topbar">
  <a class="logo" href="index.html">
    <div class="logo-seal"><span>唐</span></div>
    <div class="logo-text">
      <div class="t1">唐诗三百首</div>
      <div class="t2">Tang Poetry · 300</div>
    </div>
  </a>
  <nav>
    <a href="index.html">首页</a>
    <a href="navigation.html">导航</a>
    <a href="poets/index.html">诗人</a>
    <a href="about.html" class="current">关于</a>
  </nav>
</header>
<main class="about-page">
  <header class="about-header">
    <h1>关于本站</h1>
    <div class="sub">一部水墨写意的唐诗鉴赏文集</div>
  </header>

  <div class="stats">
    <div class="stat"><div class="num">''' + str(len(POEMS)) + '''</div><div class="label">首诗作</div></div>
    <div class="stat"><div class="num">''' + str(len(by_poet)) + '''</div><div class="label">位诗人</div></div>
    <div class="stat"><div class="num">''' + str(len(by_genre)) + '''</div><div class="label">种体裁</div></div>
    <div class="stat"><div class="num">4</div><div class="label">个朝代</div></div>
  </div>

  <section class="about-section">
    <h2>底本与体例</h2>
    <p>本站以现代增补版《唐诗三百首》为底本，共收录 ''' + str(len(POEMS)) + ''' 首唐诗，分属初唐、盛唐、中唐、晚唐四个时期 ''' + str(len(by_poet)) + ''' 位诗人。每首诗均配有完整原文、详细注释、深度赏析与名句摘录。</p>
    <p>赏析文字主要依据上海辞书出版社《唐诗鉴赏辞典》（1983 年版），该辞典由萧涤非、程千帆、霍松林、刘学锴等当代古典文学名家撰文，是唐诗鉴赏领域的权威著作。参以袁行霈主编《中国文学史》、闻一多《唐诗杂论》、沈祖棻《唐人七绝诗浅释》等。</p>
  </section>

  <section class="about-section">
    <h2>视觉风格</h2>
    <p>本站采用「水墨写意」视觉风格，以宣纸肌理为底，朱砂方印为识，墨色浓淡为层次。设计理念：</p>
    <ul>
      <li>色彩：以 oklch 色彩空间定义，纸色 <code>#faf6ed</code>、墨色 <code>#1a1a1a</code>、朱砂 <code>#a83232</code> 三色为基调</li>
      <li>字体：标题用 Ma Shan Zheng（马善政毛笔楷书），副标题用 ZCOOL XiaoWei（站酷小薇），正文用 Noto Serif SC（思源宋体）</li>
      <li>LOGO：朱砂方印「唐」字，灵感源自传统篆刻印章</li>
      <li>排版：竖排标题、横排正文，参酌古籍版式而加以现代化处理</li>
    </ul>
  </section>

  <section class="about-section">
    <h2>技术架构</h2>
    <p>本站为纯静态网站，无后端依赖，所有页面由 Python 脚本批量生成。</p>
    <ul>
      <li>诗作数据：以 Python 模块化方式组织，每位诗人独立数据文件</li>
      <li>页面生成：Python 模板引擎批量渲染 HTML</li>
      <li>共享资源：CSS 与 JS 全站共享，避免重复</li>
      <li>诗人浮窗：点击诗人卡片自动加载完整生平</li>
      <li>响应式设计：适配桌面、平板、手机</li>
    </ul>
  </section>

  <section class="about-section">
    <h2>使用指南</h2>
    <ul>
      <li><strong>导航页</strong>：提供按诗人、按体裁、按主题三种浏览方式</li>
      <li><strong>诗人索引</strong>：72 位诗人卡片式展示，点击查看完整生平</li>
      <li><strong>诗页面</strong>：含原文、注释、赏析、名句、出处溯源、同卷诗作、上下首翻页</li>
      <li><strong>诗人浮窗</strong>：在任何诗页面点击诗人卡片，即可弹出该诗人完整生平</li>
    </ul>
  </section>

  <section class="about-section">
    <h2>致谢</h2>
    <p>感谢历代唐诗研究者，特别是《唐诗鉴赏辞典》的诸位撰稿先生，他们的研究成果是本站赏析文字的根基。感谢古诗文网（gushiwen.cn）提供诗作原文核对。</p>
    <p>本站仅供学习与赏析之用，不作商业用途。</p>
  </section>

</main>
<footer class="footer">
  <div>底本：现代增补版《唐诗三百首》｜ 赏析主要依据：上海辞书出版社《唐诗鉴赏辞典》（1983 年版）</div>
  <div>© 2026 唐诗三百首 · 仅用于学习与赏析</div>
</footer>
</body>
</html>
'''

about_path = os.path.join(WEBSITE_DIR, 'about.html')
with open(about_path, 'w', encoding='utf-8') as f:
    f.write(about_html)
print(f'生成 about.html')

print('\n全部生成完毕！')
