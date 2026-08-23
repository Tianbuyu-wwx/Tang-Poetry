# -*- coding: utf-8 -*-
"""全唐诗文本解析器：支持两种常见语料格式，输出统一 poem 记录 + 与已交付卷二种子合并去重。
用法：
  python parse_qts.py --json  <全唐诗json目录或单文件>   # chinese-poetry 格式
  python parse_qts.py --txt   <全唐诗.txt>              # 纯文本格式
  python parse_qts.py --json <dir> --seed <卷二种子json> --out <out.json>
"""
import os, sys, re, json, argparse


# ---------- chinese-poetry 全唐诗 json 解析 ----------
def parse_json(path):
    """支持单文件或目录（目录下所有 全唐诗第N卷.json）。"""
    recs = []
    files = []
    if os.path.isdir(path):
        for fn in sorted(os.listdir(path)):
            if fn.endswith('.json') and ('全唐诗' in fn or 'tang' in fn.lower()):
                files.append(os.path.join(path, fn))
    else:
        files = [path]
    for fp in files:
        try:
            data = json.load(open(fp, encoding='utf-8'))
        except Exception as e:
            sys.stderr.write(f"skip {fp}: {e}\n"); continue
        # chinese-poetry 结构: list of {title, author, paragraphs:[...]}
        if isinstance(data, list):
            for it in data:
                if isinstance(it, dict) and it.get('paragraphs'):
                    recs.append({
                        'title': it.get('title','').strip(),
                        'author': (it.get('author') or '').strip(),
                        'verse': [p.strip() for p in it['paragraphs'] if p.strip()],
                        'source': fp,
                    })
        elif isinstance(data, dict):
            # 可能是 {卷名: [ {title,author,paragraphs} ]}
            for k, v in data.items():
                if isinstance(v, list):
                    for it in v:
                        if isinstance(it, dict) and it.get('paragraphs'):
                            recs.append({
                                'title': it.get('title','').strip(),
                                'author': (it.get('author') or '').strip(),
                                'verse': [p.strip() for p in it['paragraphs'] if p.strip()],
                                'source': f"{fp}::{k}",
                            })
    return recs


# ---------- 全唐诗 txt 解析 ----------
# 常见格式A(chinese-poetry 的 全唐诗.txt):
#   卷一
#   【杜甫】望岳
#   岱宗夫如何，齐鲁青未了。
#   ...
# 常见格式B:
#   杜甫
#   望岳
#   岱宗夫如何...
VOL_RE = re.compile(r'^卷[一二三四五六七八九十百零〇\d]+', re.M)
AUTHOR_BRACKET = re.compile(r'^【([^】]+)】\s*(.+)$')
AUTHOR_Q = re.compile(r'^([^《\n]{1,12}?)\s*《([^》]+)》')
AUTHOR_LINE = re.compile(r'^[一-龥]{1,8}(?:·[一-龥]{1,6})?$')


def parse_txt(path):
    recs = []
    lines = [l.rstrip('\n') for l in open(path, encoding='utf-8', errors='ignore')]
    cur_author = ''
    cur_title = ''
    cur_verse = []
    cur_vol = ''
    def flush():
        nonlocal cur_author, cur_title, cur_verse
        if cur_title and cur_verse:
            recs.append({
                'title': cur_title.strip(),
                'author': cur_author.strip(),
                'verse': [v.strip() for v in cur_verse if v.strip()],
                'source': cur_vol,
            })
        cur_title = ''; cur_verse = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if VOL_RE.match(s):
            flush(); cur_vol = s; continue
        m = AUTHOR_BRACKET.match(s)
        if m:
            flush(); cur_author = m.group(1); cur_title = m.group(2); continue
        m = AUTHOR_Q.match(s)
        if m and len(cur_verse) == 0 and not cur_title:
            flush(); cur_author = m.group(1); cur_title = m.group(2); continue
        # 若为单独作者行（无《》），且当前无诗在进行
        if AUTHOR_LINE.match(s) and not cur_title:
            flush(); cur_author = s; continue
        # 否则视为诗行（标题或正文）。若尚无标题，本行作标题
        if not cur_title:
            cur_title = s
        else:
            cur_verse.append(s)
    flush()
    return recs


# ---------- 合并种子 + 去重 + 统计 ----------
def load_seed(seed_path):
    if not seed_path or not os.path.exists(seed_path):
        return []
    return json.load(open(seed_path, encoding='utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json')
    ap.add_argument('--txt')
    ap.add_argument('--seed')
    ap.add_argument('--out', default='qts_parsed.json')
    a = ap.parse_args()

    recs = []
    if a.json:
        recs += parse_json(a.json)
    if a.txt:
        recs += parse_txt(a.txt)

    # 清洗：去空标题/空正文，去明显非诗（如 "全唐诗" 之类）
    recs = [r for r in recs if r['title'] and r['verse'] and len(r['verse']) >= 1]

    # 种子（卷二 151 首）转成统一结构
    seed = load_seed(a.seed)
    for p in seed:
        recs.append({
            'title': p.get('title',''),
            'author': p.get('author',''),
            'verse': p.get('verse',[]),
            'source': p.get('source',''),
        })

    # 去重： (author, title) 保留首个
    seen = {}
    uniq = []
    for r in recs:
        key = (r['author'], r['title'])
        if key not in seen:
            seen[key] = True
            uniq.append(r)
    recs = uniq

    json.dump(recs, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    authors = {}
    for r in recs:
        authors[r['author']] = authors.get(r['author'], 0) + 1
    sys.stderr.write(f"解析完成：{len(recs)} 首，{len(authors)} 位诗人 -> {a.out}\n")
    sys.stderr.write("Top 作者: " + ", ".join(f"{k}({v})" for k,v in sorted(authors.items(), key=lambda x:-x[1])[:10]) + "\n")


if __name__ == '__main__':
    main()
