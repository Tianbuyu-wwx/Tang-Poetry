# -*- coding: utf-8 -*-
import os, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CRAWL = os.path.join(ROOT, "scripts/crawl")

def load_module(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(CRAWL, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

# 加载各批次
sample = load_module("gen_vol2_sample")
batch2 = load_module("vol2_batch2")
batch3 = load_module("vol2_batch3")
batch4a = load_module("vol2_batch4a")
batch4b = load_module("vol2_batch4b")
batch5a = load_module("vol2_batch5a")
batch5b = load_module("vol2_batch5b")
batch6a = load_module("vol2_batch6a")
batch6b = load_module("vol2_batch6b")
batch6c = load_module("vol2_batch6c")

poems = []
poems += sample.poems
poems += batch2.BATCH2
poems += batch3.BATCH3
poems += batch4a.BATCH4A
poems += batch4b.BATCH4B
poems += batch5a.BATCH5A
poems += batch5b.BATCH5B
poems += batch6a.BATCH6A
poems += batch6b.BATCH6B
poems += batch6c.BATCH6C

# 过滤占位/校验条目
poems = [p for p in poems if p.get("tijie","").find("占位")<0 and p.get("sources")!=["占位"]]

print("total poems:", len(poems))

def md(p):
    L=[]
    L.append(f"## 《{p['title']}》　{p['author']}")
    L.append("")
    meta=[("体裁",p["genre"]),("年代",p["year"]),("出处",p["source"])]
    L.append("**"+ " ｜ ".join(f"{k}：{v}" for k,v in meta) +"**")
    L.append("")
    L.append("**原文**")
    L.append("")
    for line in p["verse"]:
        L.append("> "+line)
    L.append("")
    L.append("**题解**")
    L.append("")
    L.append(p["tijie"])
    L.append("")
    L.append("**注释**")
    L.append("")
    for term,expl in p["notes"]:
        L.append(f"- **{term}**：{expl}")
    L.append("")
    L.append("**赏析**")
    L.append("")
    L.append(p["appreciation"])
    L.append("")
    L.append("**名句**")
    L.append("")
    for line,gl in p["famous"]:
        L.append(f"- 「{line}」——{gl}")
    L.append("")
    L.append("**出处溯源**")
    L.append("")
    for s in p["sources"]:
        L.append(f"- {s}")
    L.append("")
    L.append("---")
    L.append("")
    return "\n".join(L)

header = "# 唐诗扩充·卷二（名篇全集）\n\n"
header += f"> 本卷共收录 **{len(poems)} 首** 唐诗名篇，每首含：原文、题解、注释、赏析、名句、出处溯源。\n"
header += "> 格式与本项目既有《唐诗三百首》数据完全一致。注释/赏析依据上海辞书出版社《唐诗鉴赏辞典》（1983）、\n"
header += "> 袁行霈《中国文学史》等权威典籍撰写；原文以百度汉语抓取核验，并依《全唐诗》校勘。\n"
header += "> 覆盖王之涣、张继、李绅、崔护、王翰、金昌绪、张志和、李贺等此前收录较薄之重要诗人，\n"
header += "> 以及李白、杜甫、王维、孟浩然、王昌龄、贺知章、柳宗元、贾岛等名家之更多代表诗作。\n\n---\n\n"

body = "".join(md(p) for p in poems)
OUT = os.path.join(ROOT, "docs/唐诗扩充_卷二_名篇全集.md")
open(OUT,"w",encoding="utf-8").write(header+body)
print("written:", OUT, "chars:", len(header+body))
