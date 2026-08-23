# -*- coding: utf-8 -*-
"""把 docs/ 下权威批注注入 poems-data.js
自包含: 直接解析 docs/*.md (不依赖任何临时 json)
- docs/唐诗三百首.md: 320 首 (题解+注释+赏析+名句+出处)
- docs/唐诗扩充_卷二_名篇全集.md: 151 首
- docs/唐诗扩充总录.md: 151 首 (与卷二重叠, 取更丰富)
- docs/唐诗扩充_卷二_名篇样例.md: 15 首
匹配键: 归一化 (author, title)
优先级: docs 权威批注 > 已有 scripts/data 批注 > 底本
字段映射: idx0 title, idx1 author, idx2 genre, idx3 year, idx4 source(原),
          idx5 verse, idx6 tijie, idx7 notes[[t,g]], idx8 appreciation{source,body[]},
          idx9 famous[[l,gl]], idx10 sources[...]
"""
import os, re, json

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(BASE, "docs")
WEB = os.path.join(BASE, "website")
POEMS_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_work", "poems-data.js")
CRAWL = os.path.join(BASE, "scripts", "crawl")

def norm(s):
    s = s or ""
    s = re.sub(r"（[^）]*）", "", s)
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[\s，。、；：？！·・（）()【】「」""'""' ]", "", s).strip()

# ---- 解析 docs/唐诗三百首.md (## 卷X 章节, ### 诗题, #### 原文/题解/注释/赏析/名句圈点/出处溯源) ----
def parse_ttss(path):
    if not os.path.exists(path): return []
    txt = open(path, encoding='utf-8').read()
    toc = {}
    pat = re.compile(r"-\s*\[([^·]+?)·([^\]\n]+?)\]\(#([^)]+)\)")
    for m in pat.finditer(txt):
        toc[m.group(3).strip()] = (m.group(1).strip(), m.group(2).strip())
    heads = list(re.finditer(r"^###\s+([^\n]+)$", txt, re.M))
    recs = []
    for i, h in enumerate(heads):
        title_raw = h.group(1).strip()
        if title_raw.startswith("卷") or title_raw in ("编辑说明", "总目录", "文档体例", "主要参考书目", "收录统计"):
            continue
        start, end = h.end(), heads[i + 1].start() if i + 1 < len(heads) else len(txt)
        block = txt[start:end]
        title_n = norm(title_raw)
        author = tname = None
        for anc, (a, t) in toc.items():
            if norm(t) == title_n:
                author, tname = a, t; break
        if not author:
            t2 = re.sub(r"[·其一二三五六七八九十]+$", "", title_raw).strip()
            for anc, (a, t) in toc.items():
                if norm(t) == norm(t2):
                    author, tname = a, t; break

        def grab(label):
            mm = re.search(r"####\s*" + label + r"\s*\n+([\s\S]*?)(?=\n####|\n###|\Z)", block)
            return mm.group(1).strip() if mm else ""

        notes = []
        nm = grab("注释")
        if nm:
            for line in nm.split("\n"):
                line = line.strip()
                mm = re.match(r"^\d+[\.、]\s*\*\*(.+?)\*\*[：:]\s*(.+)$", line)
                if mm:
                    notes.append([mm.group(1).strip(), mm.group(2).strip()])
        appr = grab("赏析")
        appr_src = ""
        if appr:
            sm2 = re.search(r">\s*\*\*出处\*\*[：:]\s*([^\n]+)", appr)
            if sm2:
                appr_src = sm2.group(1).strip()
                appr = re.sub(r">\s*\*\*出处\*\*[：:]\s*[^\n]+\n*", "", appr).strip()
        famous = []
        fm = grab("名句圈点")
        if fm:
            for line in fm.split("\n"):
                line = line.strip().lstrip("-").strip()
                mm = re.match(r"\*\*(.+?)\*\*[：:（(]\s*(.+)$", line)
                if mm:
                    famous.append([mm.group(1).strip(), mm.group(2).strip("（）()").strip()])
                elif "。" in line and line.startswith("**"):
                    mm = re.match(r"\*\*(.+?)\*\*[（(](.+?)[)）]", line)
                    if mm:
                        famous.append([mm.group(1).strip(), mm.group(2).strip()])
        src = []
        sm = grab("出处溯源")
        if sm:
            for line in sm.split("\n"):
                line = line.strip().lstrip("-").strip()
                if line:
                    src.append(line)
        if appr_src and appr_src not in src:
            src = [appr_src] + src
        if not (tijie := grab("题解")) and not appr and not notes:
            continue
        recs.append({'author': author or "", 'title': tname or title_raw, 'tijie': tijie,
                     'notes': notes, 'appr': appr, 'famous': famous, 'sources': src})
    return recs

# ---- 解析 docs/卷二名篇全集.md / 扩充总录.md / 名篇样例.md ----
# 结构: ## 《题》　作者, **体裁：... | 年代：... | 出处：...**, **题解**, **注释**, **赏析**, **名句**, **出处溯源**
def parse_vol2_style(path):
    if not os.path.exists(path): return []
    txt = open(path, encoding='utf-8').read()
    heads = list(re.finditer(r"^##\s*《([^》]+)》\s*([^\n]+)$", txt, re.M))
    recs = []
    for i, h in enumerate(heads):
        title = h.group(1).strip()
        author = re.sub(r"[（(].*?[)）]", "", h.group(2)).strip()
        start, end = h.end(), heads[i + 1].start() if i + 1 < len(heads) else len(txt)
        block = txt[start:end]

        def grab(label):
            mm = re.search(r"\*\*" + label + r"\*\*\s*\n+([\s\S]*?)(?=\n\*\*[^*]+\*\*|\n---|\Z)", block)
            return mm.group(1).strip() if mm else ""

        notes = []
        nm = grab("注释")
        if nm:
            for line in nm.split("\n"):
                line = line.strip()
                if line.startswith("-") and "：" in line:
                    term, gloss = line[1:].split("：", 1)
                    notes.append([term.strip().strip("*").strip(), gloss.strip()])
        famous = []
        fm = grab("名句")
        if fm:
            for line in fm.split("\n"):
                line = line.strip()
                if line.startswith("-") and "——" in line:
                    parts = line[1:].split("——", 1)
                    famous.append([parts[0].strip("「」 ").strip(), parts[1].strip()])
        src = []
        sm = grab("出处溯源")
        if sm:
            for line in sm.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    src.append(line[1:].strip())
        recs.append({'author': author, 'title': title, 'tijie': grab("题解"),
                     'notes': notes, 'appr': grab("赏析"), 'famous': famous, 'sources': src})
    return recs

# 合并所有 docs 批注
pool = {}
def add(rec):
    a = norm(rec.get('author', '')); t = norm(rec.get('title', ''))
    if not a or not t: return
    k = (a, t)
    score = 0
    for f in ('tijie', 'notes', 'appr', 'famous', 'sources'):
        v = rec.get(f)
        if isinstance(v, list): score += len(v)
        elif isinstance(v, str) and v.strip(): score += 2
    if k not in pool or score > pool[k][0]:
        pool[k] = (score, rec)

for path in [os.path.join(DOCS, "唐诗三百首.md"),
             os.path.join(DOCS, "唐诗扩充_卷二_名篇全集.md"),
             os.path.join(DOCS, "唐诗扩充总录.md"),
             os.path.join(DOCS, "唐诗扩充_卷二_名篇样例.md")]:
    parsed = parse_ttss(path) if "唐诗三百首" in path else parse_vol2_style(path)
    for r in parsed:
        add(r)
    print(f"  解析 {os.path.basename(path)}: {len(parsed)} 首")
print("docs 批注池唯一(author,title):", len(pool))

# 加载 poems-data.js
src = open(POEMS_JS, encoding='utf-8').read()
body = src[len("window.POEMS_DATA="):]
if body.endswith(";"): body = body[:-1]
D = json.loads(body)
print("POEMS_DATA 现有:", len(D))

def get_appr(rec):
    a = rec.get('appr', '')
    if isinstance(a, str) and a.strip():
        body_txt = [x.strip() for x in re.split(r"\n+", a.strip()) if x.strip()]
        return ("", body_txt)
    return ("", [])

merged = 0
for kid, rec in D.items():
    a = norm(rec[1]); t = norm(rec[0])
    hit = pool.get((a, t))
    if not hit: continue
    _, r = hit
    if (not rec[2] or rec[2] == "未知") and r.get('tijie'):
        # 体裁从 唐诗三百首.md 没有, 卷二也没有, 留空
        pass
    if (not rec[6] or not str(rec[6]).strip()) and r.get('tijie') and len(str(r['tijie'])) > 10:
        rec[6] = r['tijie']
    if (not rec[7] or not len(rec[7])) and r.get('notes'):
        rec[7] = r['notes']
    cur = rec[8]
    cur_has = isinstance(cur, dict) and cur.get('body') and len(cur['body'])
    if not cur_has:
        src_note, body_txt = get_appr(r)
        if body_txt:
            rec[8] = {"source": src_note, "body": body_txt}
    if (not rec[9] or not len(rec[9])) and r.get('famous'):
        rec[9] = r['famous']
    if (not rec[10] or not len(rec[10])) and r.get('sources'):
        real = [s for s in r['sources'] if s and "《全唐诗》曹寅本" not in s]
        if real:
            rec[10] = real
    merged += 1

with open(POEMS_JS, "w", encoding="utf-8") as f:
    f.write("window.POEMS_DATA=")
    json.dump(D, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";")
print("合并覆盖诗数:", merged)
print("写出:", POEMS_JS, "(%d KB)" % (os.path.getsize(POEMS_JS) // 1024))
