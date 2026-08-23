# -*- coding: utf-8 -*-
"""把 tang_dict_entries.json (190首《唐诗鉴赏辞典》条目) 的权威赏析注入 poems-data.js
- 仅补 appreciation(加分撰写人作为真实出处), 不覆盖已有的题解/注释/名句
- 匹配: 归一化 (author, title)  —— 源里 author/title 含全角空格, 需清洗
- 不虚构: 仅用原件 appreciation 文本
"""
import os, re, json
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CRAWL=os.path.join(BASE,"scripts","crawl")
POEMS_JS=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_work", "poems-data.js")

def norm(s):
    s=s or ""
    s=s.replace("　"," ")  # 全角空格->半角
    s=re.sub(r"（[^）]*）","",s); s=re.sub(r"\([^)]*\)","",s)
    return re.sub(r"[\s，。、；：？！·・（）()【】「」""'""' ]","",s).strip()

entries=json.load(open(os.path.join(CRAWL,"tang_dict_entries.json"),encoding="utf-8"))
pool={}
for e in entries:
    a=norm(e.get('author','')); t=norm(e.get('title',''))
    if not a or not t: continue
    ap=e.get('appreciation','')
    if isinstance(ap,str) and len(ap.strip())>30:
        writer=e.get('writer','') or ""
        # 按段切分
        body=[x.strip() for x in re.split(r"\n+",ap.strip()) if x.strip()]
        if body:
            pool[(a,t)]={"source":writer.strip(),"body":body}
print("tang_dict 可注入赏析(去重后):",len(pool))

src=open(POEMS_JS,encoding="utf-8").read()
body=src[len("window.POEMS_DATA="):]
if body.endswith(";"):body=body[:-1]
D=json.loads(body)

# 建 data 索引: 作者归一化 -> [(原始标题, key, 归一化标题)]
by_author={}
for k,v in D.items():
    a=norm(v[1])
    if a: by_author.setdefault(a,[]).append((v[0],k,norm(v[0])))

# 预建 pool 的宽松查找: (author_norm, title_norm) -> 条目
added=0
matched_keys=set()
for k,v in D.items():
    a=norm(v[1]); t=norm(v[0])
    # 精确
    if (a,t) in pool:
        hit=pool[(a,t)]
    else:
        # 子串: 在 pool 里找作者同且标题互含
        hit=None
        for (pa,pt),pv in pool.items():
            if pa==a and t and pt and (t in pt or pt in t) and len(t)>=2:
                hit=pv; break
    if not hit: continue
    cur=v[8]
    has=isinstance(cur,dict) and cur.get('body') and len(cur['body'])
    if not has:
        v[8]=hit
        added+=1
    elif (not cur.get('source')) and hit.get('source'):
        cur['source']=hit['source']

with open(POEMS_JS,"w",encoding="utf-8") as f:
    f.write("window.POEMS_DATA=")
    json.dump(D,f,ensure_ascii=False,separators=(",",":"))
    f.write(";")
print("本轮补充赏析诗数(含宽松匹配):",added,"| 写出",os.path.getsize(POEMS_JS)//1024,"KB")
# 覆盖率
ap=sum(1 for v in D.values() if v[8] and v[8].get('body') and len(v[8]['body']))
print("赏析覆盖:",ap,"/ 总",len(D))
