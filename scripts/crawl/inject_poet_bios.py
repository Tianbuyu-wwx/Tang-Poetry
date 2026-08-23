# -*- coding: utf-8 -*-
"""把 docs/唐诗扩充_卷一_诗人总录.md (243位权威生平) 注入 poets-data.js 的 life 字段
- 解析: ## 诗人名 块下的 **生平简介**（据古诗文网）：之后正文
- 匹配: 归一化诗人名 -> POETS_DATA[slug].name
- 规则: 仅当当前 life 文本长度 < 卷一总录生平长度 时才覆盖(卷一更权威/更完整)
       不覆盖 sub(诗人卡生卒流派)、nameEn 等, 只补 life 浮窗内容
- 不虚构: 仅用 docs 真实生平
"""
import os, re, json

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(BASE, "docs")
WEB = os.path.join(BASE, "website")
POETS_JS = os.path.join(WEB, "assets", "js", "poets-data.js")

def norm(s):
    return re.sub(r"[\s，。、；：？！·・（）()【】「」""'""' ]", "", s or "").strip()

# HTML 实体解码(防 docs 原文 &#224; 之类乱码)
def decode_entities(s):
    if not s:
        return s
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), s)
    s = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), s)
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return s

# 1) 解析卷一总录
txt = open(os.path.join(DOCS, "唐诗扩充_卷一_诗人总录.md"), encoding="utf-8").read()
heads = list(re.finditer(r"^##\s+([^\n]+)$", txt, re.M))
bio_pool = {}  # norm_name -> life_text
for i, h in enumerate(heads):
    name = h.group(1).strip()
    if name == "目录":
        continue
    start = h.end()
    end = heads[i + 1].start() if i + 1 < len(heads) else len(txt)
    block = txt[start:end]
    # 取 **生平简介**（据古诗文网）：之后内容
    m = re.search(r"\*\*生平简介\*\*[（(][^)）]*[)）][：:]\s*\n+([\s\S]*?)(?=\n---|\Z)", block)
    if not m:
        # 兼容无（据...）写法
        m = re.search(r"\*\*生平简介\*\*[：:]\s*\n+([\s\S]*?)(?=\n---|\Z)", block)
    life = m.group(1).strip() if m else ""
    if life:
        bio_pool[norm(name)] = decode_entities(life)
print("卷一总录解析诗人:", len(bio_pool))

# 2) 加载 poets-data.js
src = open(POETS_JS, encoding="utf-8").read()
body = src[len("window.POETS_DATA="):]
if body.endswith(";"): body = body[:-1]
PD = json.loads(body)

# 3) 注入
injected = 0
for slug, p in PD.items():
    nm = norm(p.get("name", ""))
    if not nm:
        continue
    # 先解码已有的 life(来自 poets_bio 可能含实体)
    cur = p.get("life") or []
    if cur:
        p["life"] = [decode_entities(x) for x in cur]
        cur = p["life"]
    life_txt = bio_pool.get(nm)
    if not life_txt:
        continue
    cur_len = len("".join(cur))
    # 仅当 卷一更完整 才替换(覆盖空/最小真实信息/或短于卷一的POET_INFO短sub)
    if life_txt and len(life_txt) > cur_len:
        # 按自然句/小标题切分, 每段作为 life 数组一项
        paras = [x.strip() for x in re.split(r"\n{2,}|(?<=。)\s+", life_txt) if x.strip()]
        # 若未分段(整段), 按句号+空格强制切
        if len(paras) <= 1 and len(life_txt) > 200:
            paras = [x.strip() for x in re.split(r"(?<=。)\s*", life_txt) if x.strip()]
        p["life"] = paras
        injected += 1

with open(POETS_JS, "w", encoding="utf-8") as f:
    f.write("window.POETS_DATA=")
    json.dump(PD, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";")

# 统计
real = sum(1 for p in PD.values() if len("".join(p.get("life") or [])) > 50)
empty = sum(1 for p in PD.values() if not "".join(p.get("life") or []))
print("注入(被卷一覆盖)诗人数:", injected)
print("写出:", POETS_JS, "(%d KB)" % (os.path.getsize(POETS_JS) // 1024))
print("life 覆盖: 真实详传(>50字) %d / 空 %d / 总 %d" % (real, empty, len(PD)))
