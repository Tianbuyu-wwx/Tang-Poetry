# -*- coding: utf-8 -*-
"""
从 POEMS 数据自动生成 docs/唐诗三百首.md（320 首完整版）

输出结构：
- 文档头（编辑说明、参考书目、目录）
- 按体裁分卷
- 每首诗：诗题/作者/体裁/年代/原文/题解/注释/赏析/名句/出处
- 每位诗人首次出现时附上作者生平
"""
import os, re, importlib.util
from collections import OrderedDict

# 加载 generate_poems.py
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('gp', os.path.join(SCRIPT_DIR, 'generate_poems.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
POEMS = mod.POEMS
mod.load_extra_data()
POET_INFO = mod.POET_INFO

# 体裁分卷顺序
GENRE_ORDER = [
    ('五言古诗', '五言古诗', '卷一 · 五言古诗'),
    ('五言古诗 · 乐府', '五言古诗 · 乐府', '卷二 · 五言乐府'),
    ('七言古诗', '七言古诗', '卷三 · 七言古诗'),
    ('七言古诗 · 乐府', '七言古诗 · 乐府', '卷四 · 七言乐府'),
    ('五言律诗', '五言律诗', '卷五 · 五言律诗'),
    ('七言律诗', '七言律诗', '卷六 · 七言律诗'),
    ('五言绝句', '五言绝句', '卷七 · 五言绝句'),
    ('七言绝句', '七言绝句', '卷八 · 七言绝句'),
    ('七言绝句 · 乐府', '七言绝句 · 乐府', '卷九 · 七言乐府'),
    ('乐府', '乐府', '卷十 · 乐府'),
]

def strip_html(text):
    """去除 HTML 标签"""
    return re.sub(r'<[^>]+>', '', text)

def poet_full_bio(poet_id):
    """获取诗人生平（5 元组）"""
    info = POET_INFO.get(poet_id)
    if not info:
        return None
    seal, name, en, summary, sub = info
    return {
        'name': name.replace(' ', ''),  # 去掉空格
        'name_disp': name,
        'en': en,
        'summary': summary,
        'sub': sub,
    }

def format_poem(poem, poet_seen):
    """格式化单首诗为 md 片段"""
    pid = poem['poet_id']
    bio = poet_full_bio(pid)
    parts = []

    # 诗人首次出现时插入作者生平
    if pid not in poet_seen and bio:
        poet_seen.add(pid)
        parts.append(f'\n<a id="poet-{pid}"></a>')
        parts.append(f'\n> **作者生平**：{bio["name"]}（{bio["en"]}），{bio["summary"]}\n')

    parts.append(f'\n<a id="{poem["id"]}"></a>')
    parts.append(f'### {poem["title"]}\n')
    parts.append(f'**作者**：唐 · {poem["author"]}  ')
    parts.append(f'**体裁**：{poem["genre"]}  ')
    parts.append(f'**写作年代**：{poem.get("year", "未详")}  ')
    parts.append(f'**出处**：{poem.get("source", "《全唐诗》")}\n')

    # 原文
    parts.append('#### 原文\n')
    parts.append('> ' + '\n> '.join(strip_html(line) for line in poem['verse']) + '\n')

    # 题解
    if poem.get('tijie'):
        parts.append('#### 题解\n')
        parts.append(poem['tijie'] + '\n')

    # 注释
    if poem.get('notes'):
        parts.append('#### 注释\n')
        for i, (term, gloss) in enumerate(poem['notes'], 1):
            parts.append(f'{i}. **{term}**：{gloss}')
        parts.append('')

    # 赏析
    appr = poem.get('appreciation', {})
    if appr.get('body'):
        parts.append('#### 赏析\n')
        if appr.get('source'):
            parts.append(f'> **出处**：{appr["source"]}\n')
        for para in appr['body']:
            parts.append(para + '\n')

    # 名句
    if poem.get('famous'):
        parts.append('#### 名句圈点\n')
        for line, gloss in poem['famous']:
            parts.append(f'- **{strip_html(line)}**（{gloss}）')
        parts.append('')

    # 出处溯源
    if poem.get('sources'):
        parts.append('#### 出处溯源\n')
        for s in poem['sources']:
            parts.append(f'- {s}')
        parts.append('')

    parts.append('---')
    return '\n'.join(parts)

# 按体裁分组
by_genre = OrderedDict()
for genre_key, _, _ in GENRE_ORDER:
    by_genre[genre_key] = []
for p in POEMS:
    genre = p['genre']
    if genre in by_genre:
        by_genre[genre].append(p)
    else:
        # 未知体裁归入"其他"
        if '其他' not in by_genre:
            by_genre['其他'] = []
        by_genre['其他'].append(p)

# 按诗人朝代排序（同卷内）
DYNASTY_ORDER = ['初唐', '盛唐', '中唐', '晚唐', '唐', '五代']
def dynasty_rank(poet_id):
    info = POET_INFO.get(poet_id, ('?', '?', '?', '?', '?'))
    sub = info[4]
    for i, d in enumerate(DYNASTY_ORDER):
        if d in sub:
            return i
    return len(DYNASTY_ORDER)

for genre_key in by_genre:
    by_genre[genre_key].sort(key=lambda p: (dynasty_rank(p['poet_id']), p['author'], p['title']))

# ============================================================
# 生成 md
# ============================================================
md_parts = []

# 文档头
md_parts.append('''# 唐诗三百首 · 鉴赏全集

> 底本：现代增补版《唐诗三百首》共 320 首
> 鉴赏主要依据：上海辞书出版社《唐诗鉴赏辞典》（萧涤非、程千帆等撰文，1983 年版）
> 辅助依据：中华书局《唐诗三百首注评》（蘅塘退士编、金性尧注）、《中国文学史》（袁行霈主编，高等教育出版社）

---

## 编辑说明

### 文档体例

每首诗包含以下字段：

| 字段 | 说明 |
|------|------|
| 诗题 | 原题（保留序/跋/题注） |
| 作者 | 朝代 + 姓名 |
| 体裁 | 五古 / 七古 / 五律 / 七律 / 五绝 / 七绝 / 乐府 |
| 原文 | 据全唐诗校勘，保留异文注 |
| 题解 | 写作背景、年代、本事 |
| 注释 | 字词、典故、地理、人物 |
| 赏析 | 思想内容与艺术分析（标出处） |
| 名句 | 千古传诵句圈点 |
| 出处 | 赏析文献溯源 |

### 主要参考书目

1. 萧涤非、程千帆、马茂元、周汝昌等撰文，《唐诗鉴赏辞典》，上海辞书出版社，1983 年 12 月第 1 版
2. 金性尧注，《唐诗三百首注评》，上海古籍出版社 / 中华书局
3. 袁行霈主编，《中国文学史》（第二卷），高等教育出版社，1999 年
4. 闻一多，《唐诗杂论》，上海古籍出版社
5. 缪钺，《诗词散论》，陕西师范大学出版社
6. 钱钟书，《谈艺录》，中华书局
7. 全唐诗（清·曹寅等编），中华书局点校本
8. ctext.org 中国哲学书电子化计划（底本校对）

### 收录统计

- 共 **320 首** 诗作
- 共 **76 位** 诗人
- 按体裁分卷：五言古诗 / 五言乐府 / 七言古诗 / 七言乐府 / 五言律诗 / 七言律诗 / 五言绝句 / 七言绝句 / 七言乐府 / 乐府

---

## 总目录
''')

# 总目录
for genre_key, genre_name, juan_title in GENRE_ORDER:
    poems = by_genre.get(genre_key, [])
    if not poems:
        continue
    md_parts.append(f'\n### {juan_title}（{len(poems)} 首）\n')
    for p in poems:
        md_parts.append(f'- [{p["author"]} · {p["title"]}](#{p["id"]})')

md_parts.append('\n---\n')

# 各卷内容
poet_seen = set()
for genre_key, genre_name, juan_title in GENRE_ORDER:
    poems = by_genre.get(genre_key, [])
    if not poems:
        continue
    md_parts.append(f'\n## {juan_title}（{len(poems)} 首）\n')
    for p in poems:
        md_parts.append(format_poem(p, poet_seen))

# 文档尾
md_parts.append(f'''
---

## 全书统计

- **诗作总数**：{len(POEMS)} 首
- **诗人数**：{len(set(p["poet_id"] for p in POEMS))} 位
- **体裁分布**：
''')

genre_stat = {}
for p in POEMS:
    g = p['genre']
    genre_stat[g] = genre_stat.get(g, 0) + 1
for g, c in sorted(genre_stat.items(), key=lambda x: -x[1]):
    md_parts.append(f'  - {g}：{c} 首')

md_parts.append(f'''
- **诗人分布**（按诗数降序）：
''')

poet_stat = {}
for p in POEMS:
    pid = p['poet_id']
    poet_stat[pid] = poet_stat.get(pid, 0) + 1
for pid, c in sorted(poet_stat.items(), key=lambda x: -x[1]):
    bio = poet_full_bio(pid)
    name = bio['name'] if bio else pid
    md_parts.append(f'  - {name}：{c} 首')

md_parts.append('''
---

*文档版本：v1.0 完整版（320 首）*
*生成方式：由 scripts/generate_md.py 从 POEMS 数据自动生成*
*最后更新：2026-07-20*
''')

# 写入文件
output_path = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'docs', '唐诗三百首.md'))
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(md_parts))

print(f'已生成：{output_path}')
print(f'总诗作数：{len(POEMS)}')
print(f'诗人数：{len(set(p["poet_id"] for p in POEMS))}')
print(f'文件大小：{os.path.getsize(output_path)} bytes')
