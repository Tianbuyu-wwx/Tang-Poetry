# -*- coding: utf-8 -*-
"""重建 website/assets/js/poems-index.js
- 直接由 poems-data.js 生成, 保证 id 与 POEMS_DATA 完全一致
- 字段: window.POEMS_INDEX=[{i,t,a,f,n}]
    i: POEMS_DATA 的 key (qts_XXXXX)
    t: 诗题
    a: 作者
    f: 首句(用于检索/展示)
    n: 是否有真实注解(1/0)  —— 赏析或注释或题解任一非空即算
"""
import os, json

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB = os.path.join(BASE, "website")
DATA_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_work", "poems-data.js")
OUT = os.path.join(WEB, "assets", "js", "poems-index.js")

src = open(DATA_JS, encoding="utf-8").read()
body = src[len("window.POEMS_DATA="):]
if body.endswith(";"): body = body[:-1]
D = json.loads(body)

index = []
for k, v in D.items():
    title = v[0] or ""
    author = v[1] or ""
    verse = v[5] or []
    first = ""
    for seg in verse:
        seg = seg.strip()
        if seg:
            # 取第一句(遇逗号/句号截断)
            first = seg.split("，")[0].split("。")[0].split("、")[0][:40]
            break
    has_ann = 1 if (v[8] and v[8].get("body") and len(v[8]["body"])) or (v[7] and len(v[7])) or (v[6] and str(v[6]).strip()) else 0
    index.append({"i": k, "t": title, "a": author, "f": first, "n": has_ann})

with open(OUT, "w", encoding="utf-8") as f:
    f.write("window.POEMS_INDEX=")
    json.dump(index, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";")

print("poems-index.js: %d 条, 其中带注解 %d" % (len(index), sum(x["n"] for x in index)))
print("写出:", OUT, "(%d KB)" % (os.path.getsize(OUT) // 1024))
