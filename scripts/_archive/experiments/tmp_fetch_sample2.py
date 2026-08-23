# -*- coding: utf-8 -*-
import json, urllib.request, urllib.parse, re

API = "https://zh.wikisource.org/w/api.php"

def fetch(page):
    params = {"action":"parse","page":page,"prop":"text|wikitext","format":"json","formatversion":2}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent":"TangPoetrySite/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.load(resp)["parse"]

for page in ["三體唐詩 (四庫全書本)/卷1", "才調集 (四庫全書本)/卷1", "王右丞集箋註/卷之一"]:
    try:
        parsed = fetch(page)
        text = re.sub(r"<[^>]+>", "", parsed["text"]).replace("&nbsp;"," ")
        with open(f"scripts/tmp_sample_{page.replace('/','_')}.txt","w",encoding="utf-8") as f:
            f.write(text[:4000])
        print(page, "angle", text.count("〈"), text.count("〉"), "chars", len(text))
    except Exception as e:
        print(page, "error", e)
