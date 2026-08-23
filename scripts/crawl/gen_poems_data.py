# -*- coding: utf-8 -*-
"""重建 scripts/_work/poems-data.js (完整诗库构建中间产物, 不随站点托管):
- 42132 首全唐诗原文 (来自 qts_all.json, 真实曹寅本)
- 注入 dict_annotations.json 里 153 首真实赏析 (带详细出处, 不编)
- 字段数组(11项, 与 Poem 卡片契约一致):
    [0] title        诗题
    [1] author       作者
    [2] genre        体裁
    [3] year         年代
    [4] source       出处(底本)
    [5] verse        正文 [str] (一句一段, 解析时已是整段)
    [6] tijie        题解 (辞典未单列, 留空不编)
    [7] notes        注释 [[term, gloss]...]  (辞典未单列, 留空)
    [8] appreciation 赏析 dict {"source":..., "body":[段落...]}  (无则空)
    [9] famous       名句 [[line, gloss]...]  (留空)
    [10] sources     出处溯源 [str...]
- 其余诗只留原文, 不补假赏析。
"""
import os, json, re

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CRAWL = os.path.join(BASE, "scripts", "crawl")
WEB = os.path.join(BASE, "website")
QTS = os.path.join(CRAWL, "qts_all.json")
ANN = os.path.join(CRAWL, "dict_annotations.json")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_work", "poems-data.js")

qts = json.load(open(QTS, encoding="utf-8"))
ann = json.load(open(ANN, encoding="utf-8"))

# 归一化: 去空白 + 去括注(全/半角) + 去常见标点, 提升 (author,title) 匹配率
_PUNCT = re.compile(r"[，。、；：？！·・（）\(\)【】「」“”\"' ]")
def norm(s):
    s = s or ""
    s = re.sub(r"（[^）]*）", "", s)        # 去中文括注 如（一作朱斌诗）
    s = re.sub(r"\([^)]*\)", "", s)          # 去半角括注
    s = _PUNCT.sub("", s)
    return s.strip()

# 注解按 (author, title) 归一化索引
ann_map = {}
for key, v in ann.items():
    a, t = key.split("\u0001", 1)
    ann_map[(norm(a), norm(t))] = v

# 同作者+标题核心的兜底(仅用于 词牌/乐府 重名极少场景)
def split_paragraphs(txt):
    if not txt:
        return []
    return [p.strip() for p in re.split(r"\n+", txt.strip()) if p.strip()]

data = {}
injected = 0
for p in qts:
    a = p.get("author", "")
    t = p.get("title", "")
    verse = p.get("verse", []) or []
    rec = [
        t, a,
        p.get("genre", "") or "未知",
        p.get("year", ""),
        p.get("source", "") or "《全唐诗》（清·曹寅等编，康熙扬州诗局本）",
        verse,
        "",    # tijie
        [],    # notes
        {},    # appreciation (dict: source + body)
        [],    # famous
        [],    # sources
    ]
    kv = ann_map.get((norm(a), norm(t)))
    if kv:
        body = split_paragraphs(kv.get("appreciation", ""))
        src = ""
        if kv.get("writer"):
            src = "赏析：" + kv["writer"]
        rec[8] = {"source": src, "body": body} if body else {}
        rec[10] = kv.get("sources", []) or []
        injected += 1
    data[f"qts_{len(data):05d}"] = rec

with open(OUT, "w", encoding="utf-8") as f:
    f.write("window.POEMS_DATA=")
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";")

sz = os.path.getsize(OUT)
print(f"poems-data.js: {len(data)} 首, 其中真实注解: {injected}")
print(f"写出: {OUT} ({sz/1024/1024:.2f} MB)")
