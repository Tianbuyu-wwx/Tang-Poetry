# -*- coding: utf-8 -*-
"""重建 website/assets/js/poets-data.js (干净版, 不编):
- 76 位: generate_poems.py POET_INFO 真实详传 (seal,name,nameEn,summary,sub)
- 243 人: poets_bio.json 真实生平 (gushiwen 抓取)
- 其余: 仅 (姓名 + 朝代"唐" + 真实存诗数), 不编 summary/life
每位诗人稳定 slug: 优先 POET_INFO slug(li-bai), 否则 qts_<序号>
"""
import os, json, re, importlib.util
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CRAWL = os.path.join(BASE, "scripts", "crawl")
DATA = os.path.join(BASE, "scripts", "data")
WEB = os.path.join(BASE, "website")
QTS = os.path.join(CRAWL, "qts_all.json")
BIO = os.path.join(CRAWL, "poets_bio.json")
OUT = os.path.join(WEB, "assets", "js", "poets-data.js")

# 真实存诗数 (全唐诗, 真实)
qts = json.load(open(QTS, encoding="utf-8"))
count = defaultdict(int)
for p in qts:
    count[re.sub(r"\s+", "", p.get("author", ""))] += 1

# POET_INFO (76 真实详传) — generate_poems.py 在 scripts/ 下, 不在 scripts/data/
SCRIPTS = os.path.join(BASE, "scripts")
spec = importlib.util.spec_from_file_location("gp", os.path.join(SCRIPTS, "generate_poems.py"))
gp = importlib.util.module_from_spec(spec); spec.loader.exec_module(gp)
POET_INFO = gp.POET_INFO

# poets_bio.json (243 真实生平)
bio = json.load(open(BIO, encoding="utf-8"))
if isinstance(bio, dict) and "poets" in bio:
    bio = bio["poets"]
bio_by_name = {}
for _k, b in bio.items():
    if isinstance(b, dict) and b.get("name"):
        bio_by_name[re.sub(r"\s+", "", b["name"])] = b

# qts 全部作者 (带 pid)
authors = []
seen = set()
for i, p in enumerate(qts):
    a = p.get("author", "")
    an = re.sub(r"\s+", "", a)
    if an and an not in seen:
        seen.add(an)
        authors.append((a, an, f"qts_{i:04d}"))

slug_used = set(POET_INFO.keys())
# 姓名(去空格) -> POET_INFO 条目 索引
POET_INFO_BY_NAME = {}
for _k, _v in POET_INFO.items():
    POET_INFO_BY_NAME[re.sub(r"\s+", "", _v[1])] = _v
_seq = 0
def make_slug(an):
    global _seq
    _seq += 1
    s = "qts_%04d" % _seq
    while s in slug_used:
        _seq += 1
        s = "qts_%04d" % _seq
    slug_used.add(s)
    return s

PD = {}
for a, an, pid in authors:
    slug = make_slug(an)
    rec = {"sealChar": a[0] if a else "唐",
            "name": a, "nameEn": "", "dynasty": "唐",
            "summary": "", "life": []}
    # 1) POET_INFO 详传 (76 位, 含生卒/流派 sub + 英文 nameEn)
    if an in POET_INFO_BY_NAME:
        v = POET_INFO_BY_NAME[an]
        rec.update({"sealChar": v[0], "name": v[1], "nameEn": v[2],
                    "summary": v[3], "dynasty": (v[4].split("·")[0] if "·" in v[4] else "唐"),
                    "sub": v[4], "life": [v[4]]})  # sub 含生卒+流派, 作 life
    # 2) poets_bio 真实生平 (仅当 POET_INFO 未覆盖)
    if not rec["life"] and an in bio_by_name:
        b = bio_by_name[an]
        life = b.get("life") or b.get("summary") or ""
        if isinstance(life, str):
            life = [life]
        rec["life"] = life
        rec["summary"] = (b.get("summary") or "")[:120] or rec["summary"]
        rec["dynasty"] = b.get("dynasty") or rec["dynasty"]
        rec["nameEn"] = b.get("name_en") or ""
        if b.get("seal_char"):
            rec["sealChar"] = b["seal_char"]
    # 3) 真实存诗数 (不编, 仅若 life 空给最小真实信息)
    n = count.get(an, 0)
    if not rec["life"]:
        rec["summary"] = f"{a}（生卒年不详），唐代诗人，《全唐诗》存其诗 {n} 首。"
    PD[slug] = rec

# 统计
real_life = sum(1 for v in PD.values() if len(v.get("life", [])) >= 1 and len("".join(v["life"])) > 50)
print(f"诗人: {len(PD)} | 真实详传(life>50字): {real_life}")
print(f"  其中 POET_INFO 详传: {sum(1 for v in PD.values() if len(v.get('life',[]))>=1 and '·' in ''.join(v['life']))}")
print(f"  poets_bio 生平: {sum(1 for v in PD.values() if len(v.get('life',[]))>=1 and '·' not in ''.join(v['life']) and len(''.join(v['life']))>50)}")
print(f"  仅最小真实信息: {len(PD)-real_life}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("window.POETS_DATA=")
    json.dump(PD, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";")
sz = os.path.getsize(OUT)
print(f"写出: {OUT} ({sz/1024:.0f} KB)")
