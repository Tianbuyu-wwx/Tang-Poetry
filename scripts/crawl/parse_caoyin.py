# -*- coding: utf-8 -*-
"""解析《全唐诗》(曹寅本 HTML-txt, GB18030 编码):
结构:
  第一卷李世民
  ◎卷.1【帝京篇十首】李世民 秦川雄帝宅，函谷壮皇居。...
每首诗:  ◎卷.X【诗题】作者  正文(作者名后紧跟正文首句)
输出统一 records: {title, author, verse:[...], volume}
"""
import re, json, argparse, sys


def parse(path):
    raw = open(path, 'rb').read()
    txt = raw.decode('gb18030', errors='ignore')
    txt = re.sub(r'<[^>]+>', ' ', txt)
    txt = txt.replace('\r', '\n')
    recs = []
    cur_author_by_vol = ''
    cur_volume = ''
    lines = txt.split('\n')
    i = 0
    VOL_RE = re.compile(r'^(第[一二三四五六七八九十百零〇\d]+卷)\s*(.+?)\s*$')
    POEM_RE = re.compile(r'◎?\s*卷\.?\d+\s*【([^】]+)】\s*(\S+)\s*(.*)$')
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1; continue
        mv = VOL_RE.match(line)
        if mv:
            cur_volume = mv.group(1).strip()
            cur_author_by_vol = mv.group(2).strip()
            i += 1; continue
        mp = POEM_RE.match(line)
        if mp:
            title = mp.group(1).strip()
            author = mp.group(2).strip()
            body = mp.group(3).strip()
            # 正文若以作者名重复开头(如「世民 秦川...」)，去掉
            if body.startswith(author):
                body = body[len(author):].strip()
            verse_parts = [body] if body else []
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt:
                    j += 1; continue
                if VOL_RE.match(nxt) or POEM_RE.match(nxt) or nxt.startswith('◎'):
                    break
                verse_parts.append(nxt)
                j += 1
            full = ' '.join(p for p in verse_parts if p).strip()
            full = re.sub(r'^[\s，。、；：]+', '', full)
            if full:
                recs.append({
                    'title': title,
                    'author': author or cur_author_by_vol,
                    'verse': [full],
                    'volume': cur_volume,
                })
            i = j
            continue
        i += 1
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--out', default='qts_parsed.json')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    recs = parse(a.path)
    if a.limit:
        recs = recs[:a.limit]
    json.dump(recs, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    authors = {}
    for r in recs:
        authors[r['author']] = authors.get(r['author'], 0) + 1
    sys.stderr.write(f"解析: {len(recs)} 首, {len(authors)} 位诗人 -> {a.out}\n")
    sys.stderr.write("Top: " + ", ".join(f"{k}({v})" for k,v in sorted(authors.items(), key=lambda x:-x[1])[:15]) + "\n")


if __name__ == '__main__':
    main()
