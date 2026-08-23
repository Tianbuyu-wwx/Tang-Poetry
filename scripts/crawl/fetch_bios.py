#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量抓取 gushiwen 243 位唐诗人权威生平简介(meta description)。
输出: poets_bio.json  -> {author_id: {"name","authorv","bio","url"}}
"""
import re, json, time, urllib.request, urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
MAP = json.load(open("tang_poets_map.json", encoding="utf-8"))
OUT = "poets_bio.json"


def fetch(url, tries=3):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            if t == tries - 1:
                return None
            time.sleep(1.5 * (t + 1))
    return None


def main():
    result = {}
    total = len(MAP)
    done = 0
    for aid, name in MAP.items():
        url = f"https://www.gushiwen.cn/authorv_{aid}.aspx"
        d = fetch(url)
        if not d:
            result[aid] = {"name": name, "authorv": aid, "bio": "", "url": url, "ok": False}
            done += 1
            continue
        mm = re.search(r'<meta name="description" content="([^"]+)"', d)
        bio = mm.group(1).strip() if mm else ""
        # also try to grab the on-page bio paragraph (gushiwen puts a longer bio in <p class="cont"> or div)
        result[aid] = {
            "name": name,
            "authorv": aid,
            "bio": bio,
            "url": url,
            "ok": len(bio) > 20,
        }
        done += 1
        if done % 20 == 0:
            print(f"  [{done}/{total}] last={name} bio_len={len(bio)}")
        time.sleep(0.35)  # 礼貌限速，避免被封
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = sum(1 for v in result.values() if v["ok"])
    print(f"DONE: {ok}/{total} bios captured -> {OUT}")


if __name__ == "__main__":
    main()
