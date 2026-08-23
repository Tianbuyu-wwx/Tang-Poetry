#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 hanyu.baidu.com 抓取单首诗原文，用于核验/补全诗作文字。"""
import re, json, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")

def fetch_verse(title, author=None):
    q = title + (" " + author if author else "")
    url = "https://hanyu.baidu.com/s?wd=" + urllib.parse.quote(q)
    d = get(url)
    pids = re.findall(r'/shici/detail\?pid=([0-9a-f]+)"[^>]*>([^<]+)</a>', d)
    for pid, t in pids:
        if t.strip() == title:
            # fetch detail, extract poem-list-item-body
            dd = get("https://hanyu.baidu.com/shici/detail?pid=" + pid)
            m = re.search(r'poem-list-item-body[^>]*>(.*?)</div>', dd, flags=re.S)
            if m:
                return re.sub(r"<[^>]+>", "", m.group(1)).replace(" ", "").strip()
    # fallback: any poem-list-item-body
    m = re.search(r'poem-list-item-body[^>]*>(.*?)</div>', d, flags=re.S)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).replace(" ", "").strip()
    return None

if __name__ == "__main__":
    import sys
    t = sys.argv[1]
    a = sys.argv[2] if len(sys.argv) > 2 else None
    print(fetch_verse(t, a))
