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

parsed = api_parse("詩人玉屑/卷15")
wikitext = parsed["wikitext"]
# Clean similar to prototype
lines = wikitext.splitlines()
cleaned = []
in_header = False
for line in lines:
    stripped = line.strip()
    if stripped.startswith("{{header") or stripped.startswith("{{header2"):
        in_header = True
        continue
    if in_header and stripped == "}}":
        in_header = False
        continue
    if in_header:
        continue
    cleaned.append(line)
text = "\n".join(cleaned)
text = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", text)
text = re.sub(r"'''?|''", "", text)
text = re.sub(r"<sub>.*?</sub>", "", text, flags=re.S)
text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.S)

for line in text.splitlines()[:80]:
    print(repr(line))
