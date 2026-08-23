# -*- coding: utf-8 -*-
"""解析《唐诗鉴赏辞典》完整 EPUB (周啸天主编, 商务印书馆 2012) -> dict 注释池
输出: scripts/crawl/_epub_ann.json = [(author, title, verse, author_bio, appreciation, writer), ...]
真实典籍, 不虚构. 全部内容均来自该 EPUB 原文, 每条赏析附撰稿人.
"""
import zipfile, re, json, os
CRAWL = os.path.dirname(os.path.abspath(__file__))
EPUB = os.environ.get("TANG_POETRY_EPUB")
OUT = os.path.join(CRAWL, "_epub_ann.json")

if not EPUB:
    raise SystemExit("请先设置 TANG_POETRY_EPUB，指向《唐诗鉴赏辞典》EPUB 文件。")

def clean(s):
    # 去内部 HTML 标签 + 实体解码
    s = re.sub(r"<[^>]+>", "", s or "")
    s = re.sub(r"&lt;|<", "<", s)
    s = re.sub(r"&gt;|>", ">", s)
    s = re.sub(r"&amp;", "&", s)
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), s)
    return re.sub(r"[ \u3000]+", " ", s).strip()

# 解析单文件
def parse_chapter(html):
    # 诗题
    m = re.search(r'<p class="catalog">([^<]+)</p>', html)
    if not m: return None
    title = clean(m.group(1))
    # 作者行 + 撰稿人行
    rights = re.findall(r'<p class="right-content">([\s\S]*?)</p>', html)
    if not rights: return None
    author_raw = clean(rights[0])
    author = re.sub(r"[*\s\u3000]+", "", author_raw)
    if not author: return None
    # 诗句 reference
    refs = re.findall(r'<p class="reference">([\s\S]*?)</p>', html)
    verse = "\n".join(clean(r) for r in refs if clean(r))
    # content 段: [0]=作者小标题 [1]=小传 [2]=鉴赏小标题 [3:]=赏析
    contents = re.findall(r'<p class="content">([\s\S]*?)</p>', html)
    bio = ""
    if len(contents) >= 2:
        bio = clean(contents[1])
        if bio.startswith("*"): bio = bio.lstrip("*").strip()
    # 赏析: contents[3:] 每个 <p> 一段, 直接存列表
    appreciation_paras = [clean(p) for p in contents[3:] if clean(p)]
    # 撰稿人: 最后一个 right-content, 格式(XXX) 或(XX YY)
    writer = ""
    if len(rights) >= 2:
        w = clean(rights[-1])
        # 去括号
        w = re.sub(r"^[（(]|[)）]$", "", w).strip()
        if w: writer = w
    if not appreciation_paras: return None  # 没赏析的不要
    return {"author": author, "title": title, "verse": verse,
            "author_bio": bio, "appreciation": appreciation_paras, "writer": writer}

recs = []
with zipfile.ZipFile(EPUB) as z:
    items = [it for it in z.namelist() if it.startswith('text/part') and it.endswith('.html')]
    items.sort()
    for it in items:
        try:
            html = z.read(it).decode('utf-8', errors='ignore')
        except Exception:
            continue
        rec = parse_chapter(html)
        if rec: recs.append(rec)

print("解析诗篇:", len(recs))
with_author_bio = sum(1 for r in recs if r["author_bio"])
with_writer = sum(1 for r in recs if r["writer"])
print("  含作者小传:", with_author_bio, "| 含撰稿人:", with_writer)
# 按 (author, title) 唯一
seen = {}
for r in recs:
    k = (r["author"], r["title"])
    if k not in seen:
        seen[k] = r
print("唯一(作者,诗题):", len(seen))
# 唯一作者数
print("覆盖作者数:", len(set(r["author"] for r in seen.values())))

# 写出
json.dump(list(seen.values()), open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("已存:", OUT, "(%d KB)" % (os.path.getsize(OUT) // 1024))
