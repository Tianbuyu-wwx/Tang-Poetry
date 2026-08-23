# -*- coding: utf-8 -*-
"""列出维基文库某书名前缀下的所有子页面标题。"""
import json, sys, urllib.request, urllib.parse

API = "https://zh.wikisource.org/w/api.php"

def list_pages(prefix):
    titles = []
    apcontinue = None
    while True:
        params = {
            "action": "query",
            "list": "allpages",
            "apprefix": prefix,
            "apnamespace": 0,
            "aplimit": 500,
            "format": "json",
        }
        if apcontinue:
            params["apcontinue"] = apcontinue
        url = API + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "TangPoetrySite/1.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.load(resp)
        pages = data["query"]["allpages"]
        titles.extend([p["title"] for p in pages])
        if "continue" not in data:
            break
        apcontinue = data["continue"].get("apcontinue")
    return titles

if __name__ == "__main__":
    prefix = sys.argv[1]
    titles = list_pages(prefix)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    text = f"prefix: {prefix}\ncount: {len(titles)}\n" + "\n".join(titles)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"written {out}: {len(titles)} titles")
    else:
        print(text)
