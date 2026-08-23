# -*- coding: utf-8 -*-
import json, urllib.request, urllib.parse

API = "https://zh.wikisource.org/w/api.php"

def fetch(page):
    params = {"action":"parse","page":page,"prop":"text|wikitext","format":"json","formatversion":2}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent":"TangPoetrySite/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.load(resp)["parse"]

page = "御選唐宋詩醇 (四庫全書本)/卷02"
parsed = fetch(page)
text = parsed["text"]
wiki = parsed["wikitext"]
# Simple strip html tags for preview
import re
clean = re.sub(r"<[^>]+>", "", text).replace("&nbsp;"," ")
with open("scripts/tmp_sample.txt","w",encoding="utf-8") as f:
    f.write("=== HTML TEXT (first 3000) ===\n")
    f.write(clean[:3000])
    f.write("\n\n=== WIKITEXT (first 3000) ===\n")
    f.write(wiki[:3000])
print("angle count", clean.count("〈"), clean.count("〉"))
print("written scripts/tmp_sample.txt")
