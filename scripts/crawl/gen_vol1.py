#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成卷一·诗人总录 md（gushiwen 真实抓取生平）。
结合现有数据覆盖情况标注每位诗人是否已收录诗作。
"""
import json, re, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
bio = json.load(open(os.path.join(ROOT, "scripts/crawl/poets_bio.json"), encoding="utf-8"))

# 现有已覆盖诗人及首数
covered = {}
for f in glob.glob(os.path.join(ROOT, "scripts/data/poems_*.py")):
    txt = open(f, encoding="utf-8").read()
    for a in re.findall(r'"author":\s*"([^"]+)"', txt):
        covered[a] = covered.get(a, 0) + 1

# 排序：按覆盖首数降序（名家在前），再按名字
items = sorted(bio.values(), key=lambda v: (-covered.get(v["name"], 0), v["name"]))

lines = []
lines.append("# 全唐诗人总录（扩充版）")
lines.append("")
lines.append("> 本卷收录 **%d 位** 唐代诗人权威生平，底本依据古诗文网（gushiwen.cn）「唐代诗人」名录与作者简介，" % len(bio))
lines.append("> 该站生平简介以《新唐书》《旧唐书》《唐诗纪事》《唐才子传》等传统文献为据，属通行权威来源。")
lines.append("> 标注「已收录 N 首」者，指其诗作已纳入本项目《唐诗三百首》既有数据；未标注者将在后续卷次补入代表诗作。")
lines.append("")
lines.append("## 目录")
lines.append("")
for i, v in enumerate(items, 1):
    tag = f"（已收录 {covered[v['name']]} 首）" if v["name"] in covered else ""
    lines.append(f"{i}. [{v['name']}](#{v['name']}) {tag}")
lines.append("")
lines.append("---")
lines.append("")

for v in items:
    name = v["name"]
    life = v.get("life", "").strip()
    # 去掉开头的「生平」标记
    life = re.sub(r"^生平\s*", "", life)
    n_cov = covered.get(name, 0)
    lines.append(f"## {name}")
    if n_cov:
        lines.append(f"**诗作收录**：已纳入本项目 {n_cov} 首")
    lines.append("")
    lines.append("**生平简介**（据古诗文网）：")
    lines.append("")
    if life:
        lines.append(life)
    else:
        lines.append("（生平资料暂缺）")
    lines.append("")
    lines.append("---")
    lines.append("")

out = os.path.join(ROOT, "docs/唐诗扩充_卷一_诗人总录.md")
open(out, "w", encoding="utf-8").write("\n".join(lines))
print("written:", out, "poets:", len(items))
