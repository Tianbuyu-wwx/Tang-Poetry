#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""抓取百度汉语单首诗：原文 + 注释 + 译文 + 赏析。
用法: python fetch_hanyu.py <诗名> [作者]
"""
import re, sys, json, urllib.parse, urllib.request, time

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")

def strip(html):
    h = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    h = re.sub(r"<style.*?</style>", "", h, flags=re.S)
    return h

def search_pid(title, author=None):
    q = title + (" " + author if author else "")
    url = "https://hanyu.baidu.com/s?wd=" + urllib.parse.quote(q)
    d = get(url)
    pids = re.findall(r'/shici/detail\?pid=([0-9a-f]+)', d)
    # also grab titles to pick best match
    items = re.findall(r'/shici/detail\?pid=([0-9a-f]+)"[^>]*>([^<]+)</a>', d)
    for pid, t in items:
        if t.strip() == title:
            return pid
    return pids[0] if pids else None

def clean_block(html, start_kw):
    # find the block after a keyword like 注释/译文/赏析
    i = html.find(start_kw)
    if i < 0:
        return ""
    # the content is in a following tag; capture until next section marker
    seg = html[i:i+4000]
    # remove tags
    seg = re.sub(r"<[^>]+>", " ", seg)
    seg = re.sub(r"\s+", " ", seg).strip()
    # cut at known next markers
    for mk in ["译文", "赏析", "拼音", "作者", "【", "登录", "下载百度汉语"]:
        j = seg.find(mk, len(start_kw))
        if j > 0:
            seg = seg[:j]
            break
    return seg.strip()

def fetch(title, author=None):
    pid = search_pid(title, author)
    if not pid:
        return {"error": "no pid", "title": title}
    d = get("https://hanyu.baidu.com/shici/detail?pid=" + pid)
    b = strip(d)
    body = re.search(r'poem-list-item-body[^>]*>(.*?)</div>', b, flags=re.S)
    poem = re.sub(r"<[^>]+>", "", body.group(1)).strip() if body else ""
    return {
        "title": title, "author": author, "pid": pid,
        "verse": poem.replace(" ", ""),
        "zhushi": clean_block(d, "注释"),
        "yiwen": clean_block(d, "译文"),
        "shangxi": clean_block(d, "赏析"),
    }

if __name__ == "__main__":
    title = sys.argv[1]
    author = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(fetch(title, author), ensure_ascii=False, indent=1))
