# -*- coding: utf-8 -*-
"""建干净注解库: 从 tang_dict_entries.json (190条真实赏析) 匹配 qts_all (42132首),
输出 dict_annotations.json : { (author, 归一化title): {title(全唐诗实际), author, verse(辞典原诗),
    tijie(空), notes(空), appreciation(赏析正文), famous(空),
    sources:[真实出处], writer(撰者), author_bio(作者介绍) } }
仅注入有真实赏析的; 其余诗不补(不编)。
出处格式: 据《唐诗鉴赏辞典》（周啸天主编，商务印书馆国际有限公司，2012年1月版）「诗题」条，撰者××，第X版。
(注: EPUB 流式无纸页号, 诚实不编造页码)
"""
import json, os, re
from collections import defaultdict

CRAWL = os.path.dirname(os.path.abspath(__file__))
dict_entries = json.load(open(f"{CRAWL}/tang_dict_entries.json", encoding="utf-8"))
qts = json.load(open(f"{CRAWL}/qts_all.json", encoding="utf-8"))

PREFIX = re.compile(r'^(乐府杂曲·|相和歌辞·|横吹曲辞·|杂曲歌辞·|近代曲辞·|琴曲歌辞·|舞曲歌辞·|鼓吹曲辞·)+')
def norm(s):
    s = PREFIX.sub('', s)
    s = re.sub(r'（.*?）|\(.*?\)', '', s)
    s = re.sub(r'·其[一二三四五六七八九十]+$', '', s)
    s = s.replace('，','').replace(',','').replace(' ','').replace('　','').replace('’','').replace('‘','')
    return s.strip()

BOOK = "《唐诗鉴赏辞典》（周啸天主编，商务印书馆国际有限公司，2012年1月版）"

# qts 按作者建题名列表 (归一化题 -> 实际题)
qts_by_author = defaultdict(list)
for p in qts:
    qts_by_author[re.sub(r'\s+','', p['author'])].append(norm(p['title']))

def match_title(author_norm, tk):
    cands = qts_by_author.get(author_norm, [])
    for ct in cands:
        if tk == ct:
            return ct
    for ct in cands:
        if tk and ct and (tk in ct or ct in tk) and abs(len(tk)-len(ct)) <= 4:
            return ct
    return None

annotations = {}
miss = []
for e in dict_entries:
    a = re.sub(r'\s+','', e['author'])
    tk = norm(e['title'])
    ct = match_title(a, tk)
    if not ct:
        miss.append((e['author'], e['title']))
        continue
    writer = e.get('writer','').replace(' ','')
    src = f"据{BOOK}「{ct}」条" + (f"，撰者{writer}" if writer else "")
    key = f"{a}\u0001{ct}"  # 用不可见分隔符做复合键(字符串)
    annotations[key] = {
        "author": a,
        "title_qts": ct,
        "verse_dict": e.get('poem',''),       # 辞典原诗(可能异字, 供参考, 不覆盖全唐诗原文)
        "appreciation": e.get('appreciation',''),
        "sources": [src],
        "writer": writer,
        "author_bio": e.get('author_bio',''),
    }

with open(f"{CRAWL}/dict_annotations.json", "w", encoding="utf-8") as f:
    json.dump(annotations, f, ensure_ascii=False, indent=1)

print(f"辞典条目: {len(dict_entries)}")
print(f"成功匹配注入: {len(annotations)}")
print(f"未匹配: {len(miss)}")
# 样例
k = next(iter(annotations))
v = annotations[k]
print(f"\n样例: {v['author']}/{v['title_qts']}")
print(f"  赏析: {v['appreciation'][:60]}...")
print(f"  出处: {v['sources'][0]}")
print(f"  撰者: {v['writer']}")
