# -*- coding: utf-8 -*-
"""把 scripts/data/poems_others_batch1-4.py 中严格匹配漏掉、但宽松匹配命中的诗补入 poems-data.js
自包含: 直接读 batch 文件, 解析宽松键, 仅追加不覆盖已有赏析
"""
import os, re, json, ast
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(BASE, "scripts", "data")
POEMS_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_work", "poems-data.js")

def norm(s):
    s = s or ""
    s = re.sub(r"（[^）]*）", "", s); s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[\s，。、；：？！·・（）()【】「」""'""' ]", "", s).strip()
def soft(s):
    s = s or ""
    s = re.sub(r"（[^）]*）", "", s); s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[·其一二三五六七八九十]+$", "", s)
    s = re.sub(r"^(相和歌辞|横吹曲辞|敕勒歌|杂曲歌辞|清商曲辞|琴曲歌辞|舞曲歌辞|近代曲辞|杂歌谣辞|新乐府|乐府|郊庙歌辞|燕射歌辞|鼓吹曲辞)·?","",s)
    return re.sub(r"[\s，。、；：？！·・（）()【】「」""'""' ]", "", s).strip()

# 收集 batch 记录
batch=[]
for bn in [1,2,3,4]:
    f=os.path.join(DATA,f"poems_others_batch{bn}.py")
    if not os.path.exists(f): continue
    src=open(f,encoding="utf-8").read()
    m=ast.parse(src)
    for node in ast.walk(m):
        if isinstance(node,ast.Assign) and getattr(node.targets[0],'id',None)=='POEMS_LOCAL':
            batch.extend(ast.literal_eval(node.value))
# 建 pool: 归一化(a,t) -> rec
pool={}
for r in batch:
    a=norm(r.get("author","")); t=soft(r.get("title",""))
    if not a or not t: continue
    pool[(a,t)]=r
print("batch pool:",len(pool))

# 加载 poems-data
src=open(POEMS_JS,encoding="utf-8").read()
body=src[len("window.POEMS_DATA="):]
if body.endswith(";"):body=body[:-1]
D=json.loads(body)
# 建 data 索引 (norm a -> [(soft t, key)])
didx={}
for k,v in D.items():
    a=norm(v[1]); t=soft(v[0])
    if a: didx.setdefault(a,[]).append((t,k))

def get_appr(r):
    a=r.get('appreciation','')
    if isinstance(a,dict):
        return (a.get('source',''),a.get('body',[]))
    if isinstance(a,str) and a.strip():
        return ("",[x.strip() for x in re.split(r"\n+",a.strip()) if x.strip()])
    return ("",[])

added=0
for a,cand in didx.items():
    if a not in [norm(p.get("author","")) for p in batch]: continue
    for (st,dk) in cand:
        if not st: continue
        v=D[dk]
        has=v[8] and v[8].get('body') and len(v[8]['body'])
        if has: continue
        # 在 pool 里找该作者的同标题子串匹配
        for (pa,pt),pr in pool.items():
            if pa==a and st and pt and (st in pt or pt in st) and len(st)>=2:
                src_note,ab=get_appr(pr)
                if ab:
                    v[8]={"source":src_note,"body":ab}
                    if (not v[7] or not len(v[7])) and pr.get('notes'): v[7]=pr['notes']
                    if (not v[6] or not str(v[6]).strip()) and pr.get('tijie') and len(str(pr['tijie']))>10: v[6]=pr['tijie']
                    if (not v[9] or not len(v[9])) and pr.get('famous'): v[9]=pr['famous']
                    if (not v[10] or not len(v[10])) and pr.get('sources'):
                        real=[s for s in pr['sources'] if s and "《全唐诗》曹寅本" not in s]
                        if real: v[10]=real
                    added+=1
                    print("补充:",v[1],v[0],"| 赏析",len(ab),"段")
                break

with open(POEMS_JS,"w",encoding="utf-8") as f:
    f.write("window.POEMS_DATA=")
    json.dump(D,f,ensure_ascii=False,separators=(",",":"))
    f.write(";")
print("补充:",added,"首")
