# -*- coding: utf-8 -*-
"""对 import_docs 输出的 poems-data.js 二次补强:
A. year 字段: 按作者 CBDB 生卒年范围粗估(开头/中间), 以及从 notes/verse 提取「(数字)」纪年
B. tijie 字段: 从古注里正则抽「本事始载于...」「首二句写...」等题解句式
C. famous 字段: 从古注里抽「千古名句」「脍炙人口」或「此句为后人所传诵」+ 名句内容

不破坏已有数据: 仅在字段为空时填充, 且只填字段, 不覆盖其他
"""
import os, json, re
from pathlib import Path

BASE = str(Path(__file__).resolve().parent.parent)
BIO = os.path.join(BASE, "docs", "quan_tang_shi_poets_biographies.json")
POEMS_JS = os.path.join(BASE, "website", "assets", "js", "poems-data.js")

# ---------- 1. 诗人生卒年映射 ----------
poets = json.load(open(BIO, encoding='utf-8'))['poets']
# name -> (birth_year, death_year)
name_to_years = {}
name_to_dynasty = {}  # name -> 朝代(唐/隋唐/五代/...)
for p in poets:
    name = p.get('name', '').strip()
    if not name: continue
    yrs = []
    # cbdb_summaries 第一条
    if p.get('cbdb_summaries'):
        s = p['cbdb_summaries'][0]
        # cbdb 格式: "601—636年" (全角破折号 U+2014 + 「年」)
        m = re.findall(r"(\d{3,4})[—\-](?:约)?(\d{3,4})年", s)
        if m:
            try:
                b, d_ = int(m[0][0]), int(m[0][1])
                if 500 < b < 1500 and 500 < d_ < 1600 and d_ > b:
                    yrs = (b, d_)
            except: pass
        # 备选: 「约620-712年」
        if not yrs:
            m = re.findall(r"约(\d{3,4})[—\-](\d{3,4})年?", s)
            if m:
                try:
                    yrs = (int(m[0][0]), int(m[0][1]))
                except: pass
    # 推断朝代(粗略): 生卒年范围
    # 初唐 618-712, 盛唐 712-820, 中唐 766-840, 晚唐 830-907
    # 但更稳的: 用诗人字典注释里的「...初唐」/「...盛唐」字样
    dyn = ""
    bio = p.get('biography', '')
    for k in ['初唐', '盛唐', '中唐', '晚唐', '五代']:
        if k in bio[:60]:
            dyn = k; break
    name_to_years[name] = yrs
    name_to_dynasty[name] = dyn

print(f"诗人姓名 -> (生,卒): {sum(1 for v in name_to_years.values() if v)}/{len(name_to_years)}")
print(f"诗人姓名 -> 朝代: {sum(1 for v in name_to_dynasty.values() if v)}/{len(name_to_dynasty)}")

# ---------- 加载 poems-data ----------
src = open(POEMS_JS, encoding='utf-8').read()
body = src[len("window.POEMS_DATA="):]
if body.endswith(";"): body = body[:-1]
D = json.loads(body)

# ---------- A. year 字段补强 ----------
def simplify(s): return re.sub(r"[\s　]", "", s or "")
def normalize_for_match(s): return re.sub(r"[\s　，。、；：？！·・（）()【】「」]", "", s or "")

# 公元纪年模式: 「(xxx)」「（xxx）」「xxx年」+ 600-999 范围
year_in_brackets = re.compile(r"[\(（](\d{2,4})[\)）]")
year_year = re.compile(r"(\d{3,4})年")

def fill_year(poem):
    cur = poem[3]
    if cur and str(cur).strip(): return None
    notes = poem[7] or []
    sources = poem[10] or []
    # 1) 从 notes 抽 (xxx) / xxx年
    text = ""
    if isinstance(notes, list):
        for n in notes:
            if isinstance(n, list) and len(n) >= 2:
                text += str(n[1]) + "\n"
    text += " ".join(str(s) for s in sources)
    nums = []
    for m in year_in_brackets.findall(text):
        try:
            n = int(m)
            if 600 < n < 1100: nums.append(n)
        except: pass
    for m in year_year.findall(text):
        try:
            n = int(m)
            if 600 < n < 1100: nums.append(n)
        except: pass
    if nums:
        return f"约{nums[0]}"
    # 2) 按作者 CBDB 生卒年粗估 (取中位)
    author = poem[1] or ""
    if author in name_to_years and name_to_years[author]:
        b, d_ = name_to_years[author]
        if b and d_:
            mid = (b + d_) // 2
            return f"约{mid}前后"
    # 3) 按作者朝代映射
    if author in name_to_dynasty and name_to_dynasty[author]:
        d_ = name_to_dynasty[author]
        rng = {"初唐": "618-712", "盛唐": "712-820", "中唐": "766-840", "晚唐": "830-907"}.get(d_, "")
        return rng
    return None

a_added = 0
for k, v in D.items():
    y = fill_year(v)
    if y:
        v[3] = y
        a_added += 1
print(f"[A] year 字段补强: {a_added} 首")

# ---------- B. tijie 字段补强 ----------
# 古注里常含学术指引(见xx卷/出xx书/本事始载于), 用作弱形式题解
def fill_tijie(poem):
    cur = poem[6]
    if cur and str(cur).strip(): return None
    notes = poem[7] or []
    if isinstance(notes, list):
        # 找第一条古注的「本事始载于」类语句
        for n in notes:
            if isinstance(n, list) and len(n) >= 2:
                term, gloss = n[0], n[1]
                if '古注·《' in term or '古评·《' in term or '校注·《' in term:
                    # 取「本事始载于」「据xx云」「xx记」「出xx」等指引
                    m = re.search(r"(本事始载于.{4,40})", gloss)
                    if m: return m.group(1) + "。"
                    m = re.search(r"(据《.{2,12}》.{4,40})", gloss)
                    if m: return m.group(1) + "。"
                    m = re.search(r"(出.{1,8}《.{2,12}》)", gloss)
                    if m: return m.group(1) + "。"
                    # fallback: 取古注前 50 字
                    first = gloss.strip().split("\n")[0][:50]
                    if first and len(first) >= 8:
                        return first
    return None

b_added = 0
for k, v in D.items():
    t = fill_tijie(v)
    if t:
        v[6] = t
        b_added += 1
print(f"[B] tijie 字段补强: {b_added} 首 (古籍指引型题解)")

# ---------- C. famous 字段补强 ----------
# 古注里含「千古名句」「脍炙人口」「后世传诵」+ 标记的句
# 严格模式: 仅当古注明确说"千古传诵/脍炙人口/名句"时, 才提取为 famous
# 同时: 清除之前污染的「诗末句」虚假名句
def fill_famous(poem):
    cur = poem[9]
    if cur and len(cur) > 0:
        # 清除"诗末句"类虚假名句(无古籍点评标注)
        is_real = False
        for f in cur:
            if isinstance(f, list) and len(f) >= 2 and isinstance(f[1], str):
                if '古籍' in f[1] or '名句' in f[1]:
                    is_real = True; break
        if not is_real:
            poem[9] = []
        else:
            return None
    notes = poem[7] or []
    if isinstance(notes, list):
        for n in notes:
            if isinstance(n, list) and len(n) >= 2:
                term, gloss = n[0], n[1]
                if '古注·《' in term or '古评·《' in term or '校注·《' in term:
                    if re.search(r"(?:千古传诵|脍炙人口|后世传诵|此句为.{1,3}名句|此乃.{1,3}名句)", gloss):
                        m = re.search(r"[\"「《](.{4,20}?)[\"」》]", gloss)
                        if m: return [m.group(1), "古籍点评摘录"]
    return None

c_cleaned = 0
for k, v in D.items():
    if v[9] and any('诗末句' in str((f[1] if isinstance(f, list) and len(f) >= 2 else '')) for f in v[9]):
        v[9] = []
        c_cleaned += 1
print(f"[C] famous 字段清洗虚假「诗末句」: {c_cleaned} 首")

c_added = 0
for k, v in D.items():
    f = fill_famous(v)
    if f:
        v[9] = [f]
        c_added += 1
print(f"[C] famous 字段补强: {c_added} 首 (严格: 仅古籍明确点评的名句)")

# ---------- 写回 ----------
with open(POEMS_JS, "w", encoding="utf-8") as f:
    f.write("window.POEMS_DATA=")
    json.dump(D, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";")
print(f"\n写出: {POEMS_JS} ({os.path.getsize(POEMS_JS)//1024} KB)")

# 最终覆盖统计
stats = {'tijie':0,'notes':0,'appr':0,'famous':0,'year':0,'has_any':0}
for k,v in D.items():
    has = False
    if v[6]: stats['tijie']+=1; has=True
    if v[7]: stats['notes']+=1; has=True
    if isinstance(v[8],dict) and v[8].get('body'): stats['appr']+=1; has=True
    if v[9]: stats['famous']+=1; has=True
    if v[3]: stats['year']+=1
    if has: stats['has_any']+=1
print(f"\n=== 补强后最终覆盖 (总 {len(D)} 首) ===")
for k,v in stats.items():
    print(f"  {k}: {v} ({v/len(D)*100:.2f}%)")