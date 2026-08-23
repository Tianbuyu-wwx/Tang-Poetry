# -*- coding: utf-8 -*-
"""将全唐诗 JSON -> 按作者分文件的 poems_<poet_id>.py，对齐现有网站 schema。
- 复用现有 23 位诗人的 poet_id
- 其余作者用 pypinyin 生成 poet_id
- 对已有赏析的 151 首(题+作者命中)回填完整字段
- 其余诗: verse=原文, genre/year/tijie/notes/appreciation/famous 给合理默认(待补)
"""
import json, os, re, importlib.util
from collections import defaultdict, OrderedDict
from pypinyin import lazy_pinyin

CRAWL = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(os.path.dirname(CRAWL))
DATA = os.path.join(BASE, "scripts", "data")
OUT_DIR = os.path.join(DATA, "quanshitang")  # 新目录放全唐诗分文件，避免覆盖现有
os.makedirs(OUT_DIR, exist_ok=True)

def load(n):
    s = importlib.util.spec_from_file_location(n, os.path.join(CRAWL, n + ".py"))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

# 1) 全唐诗
poems = json.load(open(os.path.join(CRAWL, "all_tang_poems.json"), encoding="utf-8"))

# 2) 现有 poet_id 映射
existing = json.load(open(os.path.join(CRAWL, "existing_poet_ids.json"), encoding="utf-8"))

# 3) 已有赏析(151首) 建立 (author,title)->full poem 字典
mods = [load(x) for x in ['gen_vol2_sample','vol2_batch2','vol2_batch3','vol2_batch4a','vol2_batch4b','vol2_batch5a','vol2_batch5b','vol2_batch6a','vol2_batch6b','vol2_batch6c']]
annotated = {}
for m in mods:
    for k in [a for a in dir(m) if a.startswith('BATCH') or a=='poems']:
        for p in getattr(m, k):
            if p.get("tijie","").find("占位")<0 and p.get("sources")!=["占位"]:
                annotated[(p['author'], p['title'])] = p

# 4) 生成 poet_id (拼音)
def make_pid(name):
    if name in existing:
        return existing[name]
    py = lazy_pinyin(name)
    return "-".join(py).lower()

# 5) 按作者分组
by_author = OrderedDict()
for p in poems:
    by_author.setdefault(p['author'], []).append(p)

# 6) 体裁猜测 (基于句数/字数粗判)
def guess_genre(verse):
    if not verse: return "唐诗"
    lens = [len(v) for v in verse]
    avg = sum(lens)/len(lens)
    n = len(verse)
    if n == 4 and avg <= 6: return "绝句"
    if n == 8 and avg <= 8: return "律诗"
    return "古诗"

# 7) 生成每个作者的 py 文件
def py_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')

def gen_author_file(author, plist):
    pid = make_pid(author)
    lines = []
    lines.append("# -*- coding: utf-8 -*-")
    lines.append('"""')
    lines.append(f"{author}卷 · 全唐诗诗作（自动解析自《全唐诗》曹寅本）")
    lines.append(f"共 {len(plist)} 首。原文据《全唐诗》，重点名篇注释赏析据《唐诗鉴赏辞典》等权威典籍。")
    lines.append('"""')
    lines.append("")
    lines.append("POEMS_LOCAL = [")
    for idx, p in enumerate(plist, 1):
        title = p['title']
        vol = p['vol']
        verse = p['verse']
        key = (author, title)
        ann = annotated.get(key)
        lines.append(f"    # ---------- {idx}. {title} ----------")
        lines.append("    {")
        lines.append(f'        "id": "{pid}-{idx}",')
        lines.append(f'        "title": "{py_escape(title)}",')
        lines.append(f'        "author": "{py_escape(author)}",')
        lines.append(f'        "poet_id": "{pid}",')
        lines.append(f'        "dynasty": "唐",')
        genre = ann['genre'] if ann else guess_genre(verse)
        lines.append(f'        "genre": "{genre}",')
        year = ann['year'] if ann else ""
        lines.append(f'        "year": "{year}",')
        src = ann['source'] if ann else f"《全唐诗·卷{vol}》"
        lines.append(f'        "source": "{py_escape(src)}",')
        # verse
        lines.append('        "verse": [')
        for v in verse:
            lines.append(f'            "{py_escape(v)}",')
        lines.append('        ],')
        if ann:
            lines.append(f'        "tijie": "{py_escape(ann["tijie"])}",')
            lines.append('        "notes": [')
            for term, expl in ann['notes']:
                lines.append(f'            ("{py_escape(term)}", "{py_escape(expl)}"),')
            lines.append('        ],')
            # appreciation
            ap = ann['appreciation']
            if isinstance(ap, dict):
                lines.append('        "appreciation": {')
                lines.append(f'            "source": "{py_escape(ap.get("source",""))}",')
                lines.append('            "body": [')
                for b in ap.get('body', []):
                    lines.append(f'                "{py_escape(b)}",')
                lines.append('            ],')
                lines.append('        },')
            else:
                lines.append(f'        "appreciation": "{py_escape(ap)}",')
            lines.append('        "famous": [')
            for line, gloss in ann['famous']:
                lines.append(f'            ("{py_escape(line)}", "{py_escape(gloss)}"),')
            lines.append('        ],')
            lines.append('        "sources": [')
            for s in ann['sources']:
                lines.append(f'            "{py_escape(s)}",')
            lines.append('        ],')
        else:
            lines.append('        "tijie": "",')
            lines.append('        "notes": [],')
            lines.append('        "appreciation": "",')
            lines.append('        "famous": [],')
            lines.append('        "sources": ["《全唐诗》曹寅本"],')
        lines.append("    },")
    lines.append("]")
    content = "\n".join(lines)
    out = os.path.join(OUT_DIR, f"poems_{pid}.py")
    # 处理重名冲突（不同作者拼音相同）
    if os.path.exists(out):
        # 加到已存在文件? 简单处理: 用 author 哈希区分
        out = os.path.join(OUT_DIR, f"poems_{pid}_{abs(hash(author))%10000}.py")
    with open(out, "w", encoding="utf-8") as f:
        f.write(content)
    return pid, out

if __name__ == "__main__":
    total = 0
    annotated_hit = 0
    files = 0
    for author, plist in by_author.items():
        pid, out = gen_author_file(author, plist)
        files += 1
        total += len(plist)
        for p in plist:
            if (author, p['title']) in annotated:
                annotated_hit += 1
    print(f"生成完毕: {files} 个作者文件, {total} 首诗, 其中回填赏析 {annotated_hit} 首")
    print(f"输出目录: {OUT_DIR}")
