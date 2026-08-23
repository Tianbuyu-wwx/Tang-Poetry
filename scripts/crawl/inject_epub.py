# -*- coding: utf-8 -*-
"""把《唐诗鉴赏辞典》EPUB 解析的 918 首赏析 + 191 位作者小传注入
- 诗: 赏析(带撰稿人作 source), 缺失则补
- 诗人: life 用作者小传(取最长), 不覆盖已有 POET_INFO 短 sub
- 优先级: EPUB 鉴赏辞典 > docs 卷一总录/poets_bio > 已有
"""
import os, re, json
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ANN = os.path.join(BASE, "scripts", "crawl", "_epub_ann.json")
POEMS_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_work", "poems-data.js")
POETS_JS = os.path.join(BASE, "website", "assets", "js", "poets-data.js")

def norm(s):
    s = s or ""
    s = s.replace("　", " ")
    s = re.sub(r"（[^）]*）", "", s); s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[\s，。、；：？！·・（）()【】「」""'""' ]", "", s).strip()

ann = json.load(open(ANN, encoding="utf-8"))
# 按归一化 (author, title) 建池, 取最丰富
pool_poem = {}
for r in ann:
    a = norm(r["author"]); t = norm(r["title"])
    if not a or not t: continue
    k = (a, t)
    score = (len(r["appreciation"]) if r["appreciation"] else 0) + (len(r["author_bio"]) if r["author_bio"] else 0)
    if k not in pool_poem or score > pool_poem[k][0]:
        pool_poem[k] = (score, r)
print("EPUB 诗批注池唯一:", len(pool_poem))

# 作者小传池: 取每位作者最长的小传
pool_bio = {}
for r in ann:
    a = norm(r["author"])
    bio = r["author_bio"]
    if not a or not bio: continue
    if a not in pool_bio or len(bio) > len(pool_bio[a]):
        pool_bio[a] = bio
print("EPUB 作者小传池唯一:", len(pool_bio))

# 1) 注入 poems-data.js
src = open(POEMS_JS, encoding="utf-8").read()
body = src[len("window.POEMS_DATA="):]
if body.endswith(";"): body = body[:-1]
D = json.loads(body)

# 建 data 索引 (norm a -> [(soft t, key, norm t)])
by_author = {}
for k, v in D.items():
    a = norm(v[1])
    if a: by_author.setdefault(a, []).append((v[0], k, norm(v[0])))

added_poem = 0
for (a, t), (sc, r) in pool_poem.items():
    # 精确匹配
    cand = by_author.get(a, [])
    hit_key = None
    for (ot, dk, otn) in cand:
        if otn == t:
            hit_key = dk; break
    if not hit_key:
        # 子串匹配
        for (ot, dk, otn) in cand:
            if t and otn and (t in otn or otn in t) and len(t) >= 2:
                hit_key = dk; break
    if not hit_key: continue
    rec = D[hit_key]
    cur = rec[8]
    cur_has = isinstance(cur, dict) and cur.get("body") and len(cur["body"])
    if not cur_has:
        # appreciation 在 JSON 已是列表(每个 <p> 一段)
        body_txt = r["appreciation"] if isinstance(r["appreciation"], list) else [r["appreciation"]]
        if body_txt:
            rec[8] = {"source": r["writer"], "body": body_txt}
            added_poem += 1
    elif (not cur.get("source")) and r["writer"]:
        cur["source"] = r["writer"]

with open(POEMS_JS, "w", encoding="utf-8") as f:
    f.write("window.POEMS_DATA=")
    json.dump(D, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";")
print("本轮补充赏析:", added_poem, "| 写出", os.path.getsize(POEMS_JS) // 1024, "KB")

# 2) 注入 poets-data.js 的 life
src = open(POETS_JS, encoding="utf-8").read()
body = src[len("window.POETS_DATA="):]
if body.endswith(";"): body = body[:-1]
PD = json.loads(body)
added_bio = 0
for slug, p in PD.items():
    a = norm(p.get("name", ""))
    if not a or a not in pool_bio: continue
    cur = p.get("life") or []
    cur_len = len("".join(cur))
    bio = pool_bio[a]
    if len(bio) > cur_len:  # 仅当辞典小传更完整
        p["life"] = [bio]
        added_bio += 1

with open(POETS_JS, "w", encoding="utf-8") as f:
    f.write("window.POETS_DATA=")
    json.dump(PD, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";")

real = sum(1 for p in PD.values() if len("".join(p.get("life") or [])) > 50)
print("本轮补充诗人生平:", added_bio, "| life 真实详传(>50字):", real, "/", len(PD))
