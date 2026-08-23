# -*- coding: utf-8 -*-
"""解析《唐诗鉴赏辞典》EPUB 提取的文本 (tang_dict/text/part*.html)，
抽取每条: 诗题 / 作者 / 原诗 / 作者介绍 / 赏析正文 / 撰者。
条目结构 (每行一条, 去标签后):
  诗题行 (如 '从军行二首')
  作者行 (如 '虞世南')
  '*' 分隔
  原诗 (多行, 到下一个小标题前)
  小标题 '作者'
  作者介绍 (多行, 到 '鉴赏' 前)
  小标题 '鉴赏'
  赏析正文 (多行, 到 '(撰者)' 或 下一条目起点前)
  '(撰者)' 行 (如 '（方　牧）')
输出: 每条 dict -> tang_dict_entries.json
"""
import os, re, json, glob

CRAWL = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(CRAWL, "tang_dict", "text")

def clean(html):
    txt = re.sub(r'<[^>]+>', '\n', html)
    txt = re.sub(r'&nbsp;', ' ', txt)
    txt = re.sub(r'[ \t]+', '', txt)
    txt = re.sub(r'\n\s*\n+', '\n', txt)
    return [l.strip() for l in txt.split('\n') if l.strip()]

def parse_part(lines):
    """返回该 part 的条目 list。"""
    entries = []
    i = 0
    n = len(lines)
    while i < n:
        # 条目起点: lines[i]=诗题, lines[i+1]=作者, lines[i+2]='*'
        if i + 2 < n and lines[i+2] == '*' and lines[i+1] and lines[i]:
            title = lines[i]
            author = lines[i+1]
            j = i + 3  # 原诗起点
            # 原诗: 直到遇到小标题 '作者' 或 '鉴赏' 或 下一条目起点(连续 诗题+作者+'*')
            poem_lines = []
            k = j
            while k < n:
                ln = lines[k]
                if ln == '作者' or ln == '鉴赏':
                    break
                # 下一条目起点 (诗题+作者+'*' 紧邻)
                if k + 2 < n and lines[k+2] == '*' and lines[k+1] and lines[k]:
                    break
                poem_lines.append(ln)
                k += 1
            # 现在 k 在 '作者' 或 '鉴赏' 或末尾
            # 作者介绍块
            author_bio = ''
            if k < n and lines[k] == '作者':
                k += 1
                bio_lines = []
                while k < n and lines[k] != '鉴赏':
                    bio_lines.append(lines[k]); k += 1
                author_bio = ''.join(bio_lines)
            # 赏析块
            appreciation = ''
            writer = ''
            if k < n and lines[k] == '鉴赏':
                k += 1
                appr_lines = []
                while k < n:
                    ln = lines[k]
                    # 撰者标注: '（xxx）' 且不含常见正文标点长句
                    m = re.match(r'^（(.+?)）\s*$', ln)
                    if m and len(m.group(1)) <= 6:
                        writer = m.group(1)
                        k += 1
                        break
                    # 下一条目起点
                    if k + 2 < n and lines[k+2] == '*' and lines[k+1] and lines[k]:
                        break
                    appr_lines.append(ln); k += 1
                appreciation = ''.join(appr_lines)
            entries.append({
                'title': title,
                'author': author,
                'poem': ''.join(poem_lines),
                'author_bio': author_bio,
                'appreciation': appreciation,
                'writer': writer,
            })
            i = k if k > i + 2 else i + 3
        else:
            i += 1
    return entries

all_entries = []
for fn in sorted(glob.glob(os.path.join(ROOT, "part*.html"))):
    d = open(fn, encoding='utf-8', errors='ignore').read()
    lines = clean(d)
    entries = parse_part(lines)
    all_entries.extend(entries)

# 过滤明显非条目 (无赏析 或 诗题过短/过长)
clean_entries = [e for e in all_entries if e['appreciation'] and len(e['appreciation']) > 30]

print("原始条目:", len(all_entries), "含赏析有效:", len(clean_entries))
# 去重 (同 作者+诗题 保留较长赏析)
seen = {}
for e in clean_entries:
    key = (e['author'], e['title'])
    if key not in seen or len(e['appreciation']) > len(seen[key]['appreciation']):
        seen[key] = e
print("去重后:", len(seen))

with open(os.path.join(CRAWL, "tang_dict_entries.json"), "w", encoding="utf-8") as f:
    json.dump(list(seen.values()), f, ensure_ascii=False, indent=1)
print("写出 tang_dict_entries.json")

# 样例
for e in list(seen.values())[:2]:
    print("\n---", e['author'], "/", e['title'], "撰:", e['writer'], "---")
    print("  原诗:", e['poem'][:40])
    print("  赏析:", e['appreciation'][:80])
    print("  作者介:", e['author_bio'][:50])
