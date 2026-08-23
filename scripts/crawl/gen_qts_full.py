# -*- coding: utf-8 -*-
"""把全唐诗解析结果(qts_all.json)转为本项目网页格式:
- 按诗人拆分生成 poems_qts_<诗人>.py (与既有 poems_*.py 同结构)
- 对卷二已有的151首名篇, 注入详尽字段(tijie/notes/appreciation/famous/sources)
- 生成 docs/唐诗全量总览.md (诗人->诗数索引, 不展开全文避免超大文件)
字段对齐既有: id,title,author,poet_id,dynasty,genre,year,source,verse,tijie,notes,appreciation,famous,sources
"""
import os, json, re
from collections import defaultdict, OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CRAWL = os.path.join(ROOT, "scripts/crawl")
DATA = os.path.join(ROOT, "scripts", "data")
DOCS = os.path.join(ROOT, "docs")

# 加载全唐诗
qts = json.load(open(os.path.join(CRAWL, "qts_all.json"), encoding="utf-8"))
# 加载卷二种子(详尽注解)
seed = json.load(open(os.path.join(CRAWL, "qts_seed_vol2.json"), encoding="utf-8")) if os.path.exists(os.path.join(CRAWL,"qts_seed_vol2.json")) else []

# 卷二种子建索引 (author,title)->详尽字段
seed_idx = {(p['author'], p['title']): p for p in seed}

# 按诗人分组 (保持原文顺序, 用自增序号作 pid 避免哈希碰撞)
by_author = OrderedDict()
for p in qts:
    by_author.setdefault(p['author'], []).append(p)

poet_id_map = {}
for idx, name in enumerate(by_author.keys(), 1):
    poet_id_map[name] = f"qts_{idx:04d}"

# 生成每个诗人的 py 文件
os.makedirs(DATA, exist_ok=True)
GEN_DIR = os.path.join(DATA, "qts_full")
os.makedirs(GEN_DIR, exist_ok=True)

count_files = 0
count_poems = 0
for author, poems in by_author.items():
    pid = poet_id_map[author]
    # 若作者已存在于现有 py, 沿用其 poet_id 风格(取现有文件中的 poet_id)
    recs = []
    for idx, p in enumerate(poems, 1):
        key = (author, p['title'])
        if key in seed_idx:
            s = seed_idx[key]
            rec = {
                "id": f"{pid}-{idx:03d}",
                "title": p['title'],
                "author": author,
                "poet_id": pid,
                "dynasty": "唐",
                "genre": s.get('genre', '未知'),
                "year": s.get('year', ''),
                "source": p.get('source','') or s.get('source',''),
                "verse": p['verse'],
                "tijie": s.get('tijie', ''),
                "notes": s.get('notes', []),
                "appreciation": s.get('appreciation', ''),
                "famous": s.get('famous', []),
                "sources": s.get('sources', []),
            }
        else:
            rec = {
                "id": f"{pid}-{idx:03d}",
                "title": p['title'],
                "author": author,
                "poet_id": pid,
                "dynasty": "唐",
                "genre": "未知",
                "year": "",
                "source": "《全唐诗》" + (("·" + p['volume']) if p.get('volume') else ""),
                "verse": p['verse'],
                "tijie": "",
                "notes": [],
                "appreciation": "",
                "famous": [],
                "sources": ["《全唐诗》（清·曹寅等编，康熙扬州诗局本）"],
            }
        recs.append(rec)
    # 写 py 文件
    fn = f"poems_{pid}.py"
    with open(os.path.join(GEN_DIR, fn), "w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write(f"# 全唐诗原文（清·曹寅本）· 诗人：{author}\n")
        f.write(f"# 共 {len(recs)} 首，由 parse_caoyin.py 解析自本地《全唐诗》文件\n")
        f.write("poems = [\n")
        for r in recs:
            f.write("    " + repr(r) + ",\n")
        f.write("]\n")
    count_files += 1
    count_poems += len(recs)

# 生成总览 md (索引, 不展开全文)
overview = []
overview.append("# 唐诗全量总览（全唐诗原文 · 清曹寅本）\n")
overview.append(f"> 数据源：本地《全唐诗》（清·曹寅等编，康熙扬州诗局本，GB18030 txt）\n")
overview.append(f"> 经 parse_caoyin.py 解析，共 **{count_poems} 首** / **{len(by_author)} 位**唐代诗人。\n")
overview.append(f"> 全部诗作原文已按诗人拆分至 `scripts/data/qts_full/poems_qts_*.py`，可直接喂 `generate_*.py` 生成网页。\n")
overview.append(f"> 其中 {len(seed_idx)} 首名篇已注入完整注释/赏析/题解（见卷二），其余为原文层（注释赏析待补）。\n\n")
overview.append("## 诗人索引（按诗作数量降序）\n")
overview.append("\n| 诗人 | 诗数 | 文件 |\n|---|---|---|")
for author, poems in sorted(by_author.items(), key=lambda x: -len(x[1])):
    pid = poet_id_map[author]
    overview.append(f"| {author} | {len(poems)} | poems_{pid}.py |")
overview.append("\n")

with open(os.path.join(DOCS, "唐诗全量总览.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(overview))

print(f"生成完成: {count_files} 个诗人文件, {count_poems} 首诗 -> {GEN_DIR}")
print(f"总览: {os.path.join(DOCS,'唐诗全量总览.md')}")
print(f"名篇注入: {len(seed_idx)} 首")
