# -*- coding: utf-8 -*-
import urllib.request, json, time, re
from urllib.parse import urlencode
from urllib.request import Request
from urllib.error import HTTPError, URLError
from http.client import IncompleteRead

API = "https://zh.wikisource.org/w/api.php"

def api_parse(page, attempts=4):
    q = urlencode({"action": "parse", "page": page, "prop": "wikitext",
                   "format": "json", "formatversion": 2})
    req = Request(f"{API}?{q}", headers={"User-Agent": "TangPoetrySite/1.0"})
    for a in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                p = json.load(r)
            if "error" in p:
                raise RuntimeError(p["error"].get("code"))
            return p["parse"]["wikitext"]
        except (HTTPError, URLError, TimeoutError, IncompleteRead) as e:
            if a == attempts:
                raise
            time.sleep(2 * a)

def clean(wt):
    lines = [l for l in wt.splitlines()
             if not l.strip().startswith("{{header")
             and not (l.strip().startswith("{{") and l.strip().endswith("}}"))]
    t = "\n".join(lines)
    t = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", t)
    t = re.sub(r"'''?|''", "", t)
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"\{\{.*?\}\}", "", t, flags=re.S)
    return t

for i in range(1, 22):
    for cand in [f"詩人玉屑/卷{i:02d}", f"詩人玉屑 (四庫全書本)/卷{i:02d}"]:
        try:
            wt = api_parse(cand)
            t = clean(wt)
            q = t.count("「") + t.count("『")
            h = t.count("===")
            print(f"{cand}: OK len={len(t)} quotes={q} headers={h}")
            break
        except RuntimeError:
            continue
    else:
        print(f"卷{i:02d}: 全部缺失")
    time.sleep(0.4)
