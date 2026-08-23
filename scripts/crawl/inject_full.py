# -*- coding: utf-8 -*-
"""把 scripts/data/poems_*.py 中真实批注合并进 scripts/_work/poems-data.js
- 匹配键: 归一化 (author, title)  —— 去括注/标点/空白
- 对每首 POEMS_DATA 诗, 取所有匹配 py 记录中 richness 最高的一条
- 仅覆盖 当前为空/未知 的字段, 不抹掉已注入的 dict_annotations(155)
- 真实字段: genre/year/tijie/notes/appreciation(dict)/famous/sources
- 绝不虚构: py 里没有的字段保持原样(空/未知)
"""
import os, json, ast, glob, re

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(BASE, "scripts", "data")
WEB = os.path.join(BASE, "website")
POEMS_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_work", "poems-data.js")
OUT = POEMS_JS

def norm(s):
    s = s or ""
    s = re.sub(r"（[^）]*）", "", s)
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[\s，。、；：？！·・（）()【】「」""'""' ]", "", s).strip()

# ---------- 1. 扫描 data/*.py ----------
def richness(p):
    score = 0
    a = p.get('appreciation', '')
    if isinstance(a, dict):
        a = ''.join(a.get('body', []))
    if isinstance(a, str) and len(a) > 30: score += 3
    if p.get('tijie') and len(str(p.get('tijie'))) > 10: score += 1
    if p.get('notes'): score += 2
    if p.get('famous'): score += 1
    if p.get('year') and str(p.get('year')).strip(): score += 1
    if p.get('genre') and p.get('genre') != '未知' and p.get('genre') != '古诗': score += 1
    return score

pool = {}  # (a,t) -> richest record
for f in glob.glob(os.path.join(DATA, "poems_*.py")):
    try:
        src = open(f, encoding="utf-8").read()
        m = ast.parse(src)
        for node in ast.walk(m):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', None) == 'POEMS_LOCAL':
                for p in ast.literal_eval(node.value):
                    a = norm(p.get('author', '')); t = norm(p.get('title', ''))
                    if not a or not t: continue
                    k = (a, t)
                    if k not in pool or richness(p) > richness(pool[k]):
                        pool[k] = p
    except Exception:
        pass
print("py 批注池唯一 (author,title):", len(pool))

# ---------- 2. 加载现有 poems-data.js ----------
src = open(POEMS_JS, encoding="utf-8").read()
# 去掉前缀 window.POEMS_DATA= 与结尾 ; 后 json 解析
body = src[len("window.POEMS_DATA="):]
if body.endswith(";"): body = body[:-1]
D = json.loads(body)
print("POEMS_DATA 现有:", len(D))

# ---------- 3. 合并 ----------
def get_appr_dict(p):
    a = p.get('appreciation', '')
    src_note = ""
    if isinstance(a, dict):
        body = a.get('body', [])
        src_note = a.get('source', '') or ""
    elif isinstance(a, str) and a.strip():
        body = [x.strip() for x in re.split(r"\n+", a.strip()) if x.strip()]
    else:
        body = []
    return (src_note, body)

merged = 0
for kid, rec in D.items():
    a = norm(rec[1]); t = norm(rec[0])
    p = pool.get((a, t))
    if not p: continue
    # genre (idx2): 仅当当前为 未知/空 且 py 有更具体值
    if (not rec[2] or rec[2] == "未知") and p.get('genre') and p.get('genre') != "古诗":
        rec[2] = p['genre']
    # year (idx3)
    if (not rec[3] or not str(rec[3]).strip()) and p.get('year') and str(p.get('year')).strip():
        rec[3] = str(p['year'])
    # tijie (idx6)
    if (not rec[6] or not str(rec[6]).strip()) and p.get('tijie') and len(str(p['tijie'])) > 10:
        rec[6] = p['tijie']
    # notes (idx7)
    if (not rec[7] or not len(rec[7])) and p.get('notes'):
        rec[7] = p['notes']
    # appreciation (idx8) dict
    cur = rec[8]
    cur_has = isinstance(cur, dict) and cur.get('body') and len(cur['body'])
    if not cur_has:
        src_note, body = get_appr_dict(p)
        if body:
            rec[8] = {"source": src_note, "body": body}
    # famous (idx9)
    if (not rec[9] or not len(rec[9])) and p.get('famous'):
        rec[9] = p['famous']
    # sources (idx10): 仅合并真实引用, 跳过泛化底本标记
    if (not rec[10] or not len(rec[10])) and p.get('sources'):
        real = [s for s in p['sources'] if s and "《全唐诗》曹寅本" not in s]
        if real:
            rec[10] = real
    merged += 1

with open(OUT, "w", encoding="utf-8") as f:
    f.write("window.POEMS_DATA=")
    json.dump(D, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";")
print("合并覆盖诗数:", merged)
print("写出:", OUT, "(%d KB)" % (os.path.getsize(OUT)//1024))
