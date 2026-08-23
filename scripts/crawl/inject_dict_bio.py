# -*- coding: utf-8 -*-
import json, os, re
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def norm(s):
    s=s or ""; s=s.replace("　"," ")
    s=re.sub(r"（[^）]*）","",s); s=re.sub(r"\([^)]*\)","",s)
    return re.sub(r"[\s，。、；：？！·・（）()【】「」""'""' ]","",s).strip()
d=json.load(open(os.path.join(BASE,"scripts","crawl","tang_dict_entries.json"),encoding="utf-8"))
# 建 (author_norm -> bio) 池, 取最长
bio={}
for e in d:
    a=norm(e.get("author","")); b=e.get("author_bio","")
    if not a or not isinstance(b,str) or len(b.strip())<30: continue
    b=re.sub(r"&#(\d+);",lambda m:chr(int(m.group(1))),b)  # 解码实体
    if a not in bio or len(b)>len(bio[a]): bio[a]=b.strip()
print("tang_dict author_bio 唯一诗人:",len(bio))
# 加载 poets-data
src=open(os.path.join(BASE,"website","assets","js","poets-data.js"),encoding="utf-8").read()
body=src[len("window.POETS_DATA="):]
if body.endswith(";"):body=body[:-1]
PD=json.loads(body)
injected=0
for slug,p in PD.items():
    a=norm(p.get("name",""))
    if not a or a not in bio: continue
    cur=p.get("life") or []
    cur_len=len("".join(cur))
    if len(bio[a])>cur_len:  # 仅当辞典小传更完整
        p["life"]=[bio[a]]
        injected+=1
with open(os.path.join(BASE,"website","assets","js","poets-data.js"),"w",encoding="utf-8") as f:
    f.write("window.POETS_DATA=")
    json.dump(PD,f,ensure_ascii=False,separators=(",",":"))
    f.write(";")
real=sum(1 for p in PD.values() if len("".join(p.get("life") or []))>50)
print("本轮注入(被辞典小传覆盖):",injected)
print("life 真实详传(>50字):",real,"/ 总",len(PD))
