#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 gushiwen 诗人页提取完整生平：优先 '生平'/'简介' 段落正文，回退 meta description。
输出追加到 poets_bio.json 的 'life' 字段。
"""
import re, json, time, urllib.request


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
data = json.load(open("poets_bio.json", encoding="utf-8"))


def fetch(url, tries=3):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception:
            if t == tries - 1:
                return None
            time.sleep(1.5 * (t + 1))
    return None


def clean(html):
    h = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    h = re.sub(r"<style.*?</style>", "", h, flags=re.S)
    # remove obvious ui junk
    h = re.sub(r"展开阅读全文", "", h)
    t = re.sub(r"<[^>]+>", " ", h)
    t = re.sub(r"[\u3000\xa0]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_life(d):
    b = re.sub(r"<script.*?</script>", "", d, flags=re.S)
    b = re.sub(r"<style.*?</style>", "", b, flags=re.S)
    # Look for the '生平' section block: gushiwen wraps sections; find '生平' then capture following text until next section header
    # Strategy: get the big content div text and locate the longest coherent bio paragraph.
    text = clean(d)
    # Find the '生平' marker and take 1500 chars after it
    idx = text.find("生平")
    if idx > 0:
        seg = text[idx: idx + 1600]
        # cut at known section breaks
        for mk in ["诗歌风格", "思想核心", "家庭成员", "轶事典故", "书法成就", "生平 生平"]:
            j = seg.find(mk, 30)
            if j > 0:
                seg = seg[:j]
                break
        if len(seg) > 80:
            return seg.strip()
    # fallback: first substantial paragraph mentioning the poet
    mm = re.search(r'<meta name="description" content="([^"]+)"', d)
    return mm.group(1).strip() if mm else ""


def main():
    total = len(data)
    done = 0
    for aid, v in data.items():
        if v.get("life") and len(v["life"]) > 80:
            done += 1
            continue
        d = fetch(f"https://www.gushiwen.cn/authorv_{aid}.aspx")
        if d:
            v["life"] = extract_life(d)
        else:
            v["life"] = v.get("bio", "")
        done += 1
        if done % 20 == 0:
            print(f"  [{done}/{total}]")
        time.sleep(0.35)
    json.dump(data, open("poets_bio.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    lens = [len(v.get("life", "")) for v in data.values()]
    print(f"DONE life capture. avg={sum(lens)//len(lens)} max={max(lens)} min={min(lens)}")


if __name__ == "__main__":
    main()
