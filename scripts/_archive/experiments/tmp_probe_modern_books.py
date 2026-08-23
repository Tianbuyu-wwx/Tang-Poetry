# -*- coding: utf-8 -*-
"""探测《人间词话》《饮冰室诗话》在维基文库的页面。"""
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "TangPoetrySite/1.0 (public-domain source integration)"

def api_parse(page):
    query = urlencode({
        "action": "parse",
        "page": page,
        "prop": "text|wikitext",
        "format": "json",
        "formatversion": 2,
    })
    request = Request(f"{API_URL}?{query}", headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=45) as response:
        payload = json.load(response)
    return payload

for page in ["人間詞話", "飲冰室詩話", "飲冰室詩話/卷一", "人間詞話/卷上"]:
    print(f"\n=== {page} ===")
    try:
        result = api_parse(page)
        if "error" in result:
            print("error:", result["error"])
        else:
            parse = result["parse"]
            print("title:", parse["title"])
            print("wikitext length:", len(parse["wikitext"]))
            print("first 1000 chars:")
            print(parse["wikitext"][:1000])
    except Exception as e:
        print("exception:", e)
