# -*- coding: utf-8 -*-
"""修复所有赏析和诗人生平被默认成 1 段的问题
- 赏析: poems-data.js 中 body 段数 < EPUB 池段数 时覆盖为 EPUB 多段
- 诗人生平: 按卷一总录的小节标题(家世背景/父母/轶事典故...)切段
- 不覆盖更丰富的现状; 只在 1 段 + 长文 时切
"""
import os, re, json
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EPUB_JSON = os.path.join(BASE, "scripts", "crawl", "_epub_ann.json")
VOL1_MD = os.path.join(BASE, "docs", "唐诗扩充_卷一_诗人总录.md")
POEMS_JS = os.path.join(BASE, "website", "assets", "js", "poems-data.js")
POETS_JS = os.path.join(BASE, "website", "assets", "js", "poets-data.js")

def norm(s):
    s = s or ""
    s = s.replace("　", " ")
    s = re.sub(r"（[^）]*）", "", s); s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[\s，。、；：？！·・（）()【】「」""'""' ]", "", s).strip()

# 1) 加载 EPUB 池(按段列表)
ann = json.load(open(EPUB_JSON, encoding="utf-8"))
epub_poem = {}
for r in ann:
    a = norm(r["author"]); t = norm(r["title"])
    if not a or not t: continue
    if isinstance(r["appreciation"], list) and len(r["appreciation"]) > 1:
        epub_poem[(a, t)] = r["appreciation"]
print("EPUB 多段赏析池:", len(epub_poem))

# 2) 加载 poems-data, 修复赏析
src = open(POEMS_JS, encoding="utf-8").read()
body = src[len("window.POEMS_DATA="):]
if body.endswith(";"): body = body[:-1]
D = json.loads(body)

by_author = {}
for k, v in D.items():
    a = norm(v[1])
    if a: by_author.setdefault(a, []).append((v[0], k, norm(v[0])))

fixed_poem = 0
for (a, t), paras in epub_poem.items():
    cand = by_author.get(a, [])
    hit = None
    for (ot, dk, otn) in cand:
        if otn == t: hit = dk; break
    if not hit:
        for (ot, dk, otn) in cand:
            if t and otn and (t in otn or otn in t) and len(t) >= 2: hit = dk; break
    if not hit: continue
    rec = D[hit]
    cur = rec[8]
    cur_paras = cur.get("body") if isinstance(cur, dict) else []
    cur_n = len(cur_paras) if cur_paras else 0
    if cur_n < len(paras):  # EPUB 更完整, 覆盖
        rec[8] = {"source": cur.get("source") if isinstance(cur, dict) else "", "body": paras}
        fixed_poem += 1

with open(POEMS_JS, "w", encoding="utf-8") as f:
    f.write("window.POEMS_DATA=")
    json.dump(D, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";")
print("赏析修复(段数提升):", fixed_poem, "| 写出", os.path.getsize(POEMS_JS)//1024, "KB")

# 3) 诗人生平按小标题切段
# 卷一总录的小节标题集合
SECT_HEADS = ["家世背景","父母","家庭成员","轶事典故","死因之谜","思想核心",
              "书法成就","早年经历","晚年结局","完善","文学成就","艺术成就",
              "创作风格","创作背景","政治主张","诗作内容","人物评价","后世影响",
              "交游","婚姻","子女","官职","主要作品","纪念","赠序","作品",
              "序文","墓志铭","评价","人物","生平","评述","注释","作者","鉴赏"]

# 解析卷一总录
def parse_vol1_life(path):
    txt = open(path, encoding="utf-8").read()
    heads = list(re.finditer(r"^##\s+([^\n]+)$", txt, re.M))
    pool = {}
    for i, h in enumerate(heads):
        name = h.group(1).strip()
        if name == "目录": continue
        start = h.end(); end = heads[i+1].start() if i+1<len(heads) else len(txt)
        block = txt[start:end]
        m = re.search(r"\*\*生平简介\*\*[（(][^)）]*[)）][：:]\s*\n+([\s\S]*?)(?=\n---|\Z)", block)
        if not m: continue
        life = m.group(1).strip()
        if not life: continue
        # 按小标题切段
        # 模式: 小标题 + (空格/全角空格) + 内容; 切出 [标题, 内容] 列表
        head_pat = "|".join(re.escape(h) for h in SECT_HEADS)
        pieces = re.split(r"(?:^|\s)(" + head_pat + r")\s+", life)
        # re.split 保留分隔符: [前置, 小标题1, 内容1, 小标题2, 内容2, ...]
        paras = []
        # 跳过前置(无小标题时的整段)
        idx = 0
        if pieces and pieces[0].strip() and not any(p in pieces[0] for p in SECT_HEADS):
            # 前置是首段(通常以 家世背景 开头, 已切掉)
            if pieces[0].strip():
                paras.append(pieces[0].strip())
            idx = 1
        # 现在偶数 idx 是小标题, 奇数是内容
        while idx+1 < len(pieces):
            head = pieces[idx].strip()
            content = pieces[idx+1].strip()
            if content:
                paras.append(head + "  " + content)
            idx += 2
        if not paras:  # 没切出来, 退回整段
            paras = [life]
        pool[norm(name)] = paras
    return pool

# 先解析
if os.path.exists(VOL1_MD):
    vol1_pool = parse_vol1_life(VOL1_MD)
    print("卷一总录诗人池:", len(vol1_pool))
else:
    vol1_pool = {}
    print("卷一总录不存在, 跳过")

# 加载 poets-data
src = open(POETS_JS, encoding="utf-8").read()
body = src[len("window.POETS_DATA="):]
if body.endswith(";"): body = body[:-1]
PD = json.loads(body)

fixed_life = 0
for slug, p in PD.items():
    a = norm(p.get("name", ""))
    if not a or a not in vol1_pool: continue
    paras = vol1_pool[a]
    cur = p.get("life") or []
    # 仅当现有 life 是 1 段, 而卷一有多段时切
    if len(cur) <= 1 and len(paras) > 1:
        p["life"] = paras
        fixed_life += 1
    elif len(paras) > len(cur):
        p["life"] = paras
        fixed_life += 1

with open(POETS_JS, "w", encoding="utf-8") as f:
    f.write("window.POETS_DATA=")
    json.dump(PD, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";")

real = sum(1 for p in PD.values() if len("".join(p.get("life") or []))>50)
multi = sum(1 for p in PD.values() if len(p.get("life") or [])>1)
print("诗人生平修复:", fixed_life, "| 多段诗人:", multi, "| 真实详传:", real, "/ 总", len(PD))
