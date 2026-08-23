# -*- coding: utf-8 -*-
import json, re
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
    return payload["parse"]

parsed = api_parse("詩人玉屑/卷04")
print("title:", parsed["title"])
print("wikitext length:", len(parsed["wikitext"]))
print("\nfirst 3000 chars:")
print(parsed["wikitext"][:3000])
