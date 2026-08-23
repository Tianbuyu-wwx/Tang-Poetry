#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入 docs/唐诗三百首.md 的注释到 poems-data.js
- 解析 320 首诗的 注释/题解/赏析/名句/出处 字段
- 按 (作者, 诗题) 归一化键匹配 poem_id
- 校对《唐诗鉴赏辞典》已有的 887 赏析：缺失/更详细时补
- 不重复，不覆盖更优内容
- 写回 poems-data.js
"""
import os, re, json
from pathlib import Path
from difflib import SequenceMatcher

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
POEMS_JS = ROOT / "website" / "assets" / "js" / "poems-data.js"
TTS_FILE = DOCS / "唐诗三百首.md"

# 简单归一化
def norm(s):
    s = (s or "").strip()
    s = s.replace("　", " ")
    s = re.sub(r"[（(][^）)]*[)）]", "", s)
    s = re.sub(r"[\s，。、；：？！·・（）()【】「」\"'""''《》]", "", s)
    return s


def parse_tts(path):
    """解析唐诗三百首.md, 返回 {(author, title): {...}}"""
    text = Path(path).read_text(encoding="utf-8")
    # 找每首诗块: ### 诗题 作者\n...\n### 下一首
    out = {}
    # 找诗块: ### 诗题\n... (作者行在下一行, 然后 原文/题解/注释/赏析/名句/出处)
    # 实际: 用 ### 诗题 切分, 然后找下一行 **作者**:
    parts = re.split(r'(?=^###\s+[^\n]+$)', text, flags=re.M)
    for blk in parts:
        m = re.match(r'^###\s+([^\n]+)\n', blk)
        if not m:
            continue
        title = m.group(1).strip()
        # 跳过非诗标题(目录/编辑说明等)
        if any(x in title for x in ['编辑说明', '文档体例', '主要参考书目', '收录统计', '总目录',
                                     '卷一', '卷二', '卷三', '卷四', '卷五', '卷六',
                                     '卷七', '卷八', '卷九', '卷十']):
            continue
        # 找作者行: **作者**：...
        am = re.search(r'\*\*作者\*\*[：:]\s*([^\n]+)', blk)
        if not am:
            continue
        author_full = am.group(1).strip()
        author = re.sub(r"^唐代?\s*[·]?\s*", "", author_full).strip()
        if not author:
            continue

        def grab(field):
            pat = r'####\s+' + field + r'\s*\n+(.*?)(?=\n####|\Z)'
            mm = re.search(pat, blk, re.S)
            if mm:
                t = mm.group(1).strip()
                t = re.sub(r'^\s*[-*]\s+', '• ', t, flags=re.M)
                t = re.sub(r'\n+', '\n', t)
                return t
            return ""

        rec = {
            'author': author,
            'title': title,
            'verse': grab("原文"),
            'tijie': grab("题解"),
            'notes': grab("注释"),
            'appr': grab("赏析"),
            'famous': grab("名句"),
            'source': grab("出处"),
        }
        out[(norm(author), norm(title))] = rec
    return out


def load_poems():
    src = POEMS_JS.read_text(encoding="utf-8")
    m = re.search(r"window\.POEMS_DATA=(.*?);$", src, re.S)
    D = json.loads(m.group(1))
    # 建归一化键 -> poem_id
    by_key = {}
    by_author = {}
    for pid, v in D.items():
        a, t = v[1] or "", v[0] or ""
        k = (norm(a), norm(t))
        by_key.setdefault(k, []).append(pid)
        by_author.setdefault(norm(a), []).append((pid, t))
    return D, by_key, by_author


def fuzzy_match(title, candidates):
    """title 模糊匹配 candidates (作者下所有诗), 返回最佳"""
    n = norm(title)
    if not n:
        return None, 0
    best = None
    best_score = 0
    for pid, ct in candidates:
        cn = norm(ct)
        if cn == n:
            return pid, 1.0
        # 去尾数字/组数/卷号
        n_clean = re.sub(r'[（(]?[一二三四五六七八九十百零\d]+(?:首|章|卷|篇)?[）)]?$', '', n)
        cn_clean = re.sub(r'[（(]?[一二三四五六七八九十百零\d]+(?:首|章|卷|篇)?[）)]?$', '', cn)
        n_clean = n_clean.rstrip('之')
        cn_clean = cn_clean.rstrip('之')
        # 优先去尾匹配 (行路难 ↔ 行路难三首)
        if n_clean and n_clean == cn_clean:
            return pid, 0.95
        # 包含关系
        if n in cn or cn in n:
            score = min(len(n), len(cn)) / max(len(cn), len(n))
            if score > best_score:
                best_score = score
                best = pid
            continue
        if n_clean in cn or cn_clean in n:
            score = min(len(n_clean), len(cn_clean)) / max(len(cn_clean), len(n_clean), 1) * 0.85
            if score > best_score:
                best_score = score
                best = pid
            continue
        # 序列匹配 fallback
        sm = SequenceMatcher(None, n, cn).ratio()
        if sm > best_score:
            best_score = sm
            best = pid
    return best, best_score


def parse_notes_field(notes_text):
    """解析注释文本为 [[term, gloss], ...]"""
    if not notes_text:
        return []
    out = []
    for line in notes_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # 去掉前导 • - 等
        line = re.sub(r"^[•\-*]\s*", "", line)
        if not line:
            continue
        # 尝试 "词：释" 格式
        m = re.match(r"^([^：:]{1,12})[：:](.+)$", line)
        if m:
            out.append([m.group(1).strip(), m.group(2).strip()])
        else:
            out.append(["", line])
    return out


def parse_famous_field(famous_text):
    """解析名句文本为 [[line, note], ...]"""
    if not famous_text:
        return []
    out = []
    for line in famous_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[•\-*]\s*", "", line)
        if not line:
            continue
        m = re.match(r"^[「『\"'](.+?)[」』\"'](.*)$", line)
        if m:
            out.append([m.group(1).strip(), m.group(2).strip()])
        else:
            out.append([line, ""])
    return out


def parse_appr_field(appr_text):
    """解析赏析文本为 [{source, body: [...]}]"""
    if not appr_text:
        return {}
    # 找 (出处) 或 【出处】 开头的句子
    source = ""
    m = re.search(r'[（(]([^)）]{3,30})[)）]', appr_text)
    if m:
        source = m.group(1)
    body = [x.strip() for x in re.split(r'\n+', appr_text) if x.strip()]
    return {"source": source, "body": body}


def main():
    print("=" * 60)
    print("唐诗三百首 注释导入 + 鉴赏辞典校对")
    print("=" * 60)

    # 1) 解析唐诗三百首
    print("\n[1/4] 解析 docs/唐诗三百首.md...")
    tts = parse_tts(TTS_FILE)
    print(f"  解析: {len(tts)} 首诗")

    # 2) 加载 poems-data
    print("\n[2/4] 加载 poems-data.js...")
    D, by_key, by_author = load_poems()
    print(f"  已加载: {len(D)} 首")

    # 3) 匹配 + 注入
    print("\n[3/4] 匹配并注入...")
    stats = {"matched": 0, "added_verse": 0, "added_tijie": 0,
             "added_notes": 0, "added_appr": 0, "added_famous": 0,
             "unmatched": []}

    for (author_n, title_n), rec in tts.items():
        # 精确匹配
        if (author_n, title_n) in by_key:
            pids = by_key[(author_n, title_n)]
        else:
            # 作者下模糊匹配
            if author_n in by_author:
                pid, score = fuzzy_match(title_n, by_author[author_n])
                if score >= 0.5 and pid:
                    pids = [pid]
                else:
                    stats["unmatched"].append((rec['author'], rec['title']))
                    continue
            else:
                stats["unmatched"].append((rec['author'], rec['title']))
                continue
        for pid in pids:
            v = D[pid]
            stats["matched"] += 1

            # 1. 原文 (verse) - 仅在空时填
            new_verse = [ln.strip() for ln in rec['verse'].split('\n') if ln.strip()]
            if new_verse and (not v[5] or len(v[5]) < 2):
                v[5] = new_verse
                stats["added_verse"] += 1

            # 2. 题解 (tijie) - 仅在空时填
            if rec['tijie'] and not v[6]:
                v[6] = rec['tijie']
                stats["added_tijie"] += 1

            # 3. 注释 (notes) - 合并: 已有的 + 新解析的
            new_notes = parse_notes_field(rec['notes'])
            if new_notes:
                cur_notes = v[7] or []
                cur_texts = {n[1] if isinstance(n, list) and len(n) >= 2 else str(n) for n in cur_notes}
                for n in new_notes:
                    if n[1] not in cur_texts:
                        cur_notes.append(n)
                        cur_texts.add(n[1])
                v[7] = cur_notes
                stats["added_notes"] += 1

            # 4. 赏析 (appr) - 仅在空时填
            if rec['appr']:
                cur_ap = v[8]
                cur_body = cur_ap.get("body", []) if isinstance(cur_ap, dict) else []
                if not cur_body:
                    new_ap = parse_appr_field(rec['appr'])
                    if new_ap.get("body"):
                        v[8] = new_ap
                        stats["added_appr"] += 1
                else:
                    # 校对：检查唐诗三百首版本是否更长 (萧涤非版通常更详细)
                    if len(rec['appr']) > sum(len(b) for b in cur_body) * 1.5:
                        new_ap = parse_appr_field(rec['appr'])
                        if new_ap.get("body"):
                            v[8] = new_ap
                            stats["added_appr"] += 1

            # 5. 名句 (famous) - 合并
            new_famous = parse_famous_field(rec['famous'])
            if new_famous:
                cur_famous = v[9] or []
                cur_lines = {f[0] for f in cur_famous if isinstance(f, list) and len(f) >= 1}
                for f in new_famous:
                    if f[0] and f[0] not in cur_lines:
                        cur_famous.append(f)
                        cur_lines.add(f[0])
                v[9] = cur_famous
                stats["added_famous"] += 1

    # 4) 写回
    print("\n[4/4] 写回 poems-data.js...")
    out = "window.POEMS_DATA=" + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";"
    POEMS_JS.write_text(out, encoding="utf-8")
    print(f"  写出: {os.path.getsize(POEMS_JS)//1024} KB")

    # 报告
    print("\n" + "=" * 60)
    print("注入结果")
    print("=" * 60)
    for k, v in stats.items():
        if k == "unmatched":
            print(f"  未匹配: {len(v)} 首")
            for a, t in v[:10]:
                print(f"    - {a}《{t}》")
            if len(v) > 10:
                print(f"    ... +{len(v)-10} more")
        else:
            print(f"  {k}: {v}")

    # 最终覆盖
    total = len(D)
    c = {"tijie": 0, "notes_real": 0, "appr": 0, "famous": 0, "year": 0, "has_anno": 0}
    for k, v in D.items():
        has = False
        if v[6]: c["tijie"] += 1; has = True
        if v[7]:
            for n in v[7]:
                if isinstance(n, list) and len(n) >= 2:
                    c["notes_real"] += 1
                    break
        ap = v[8]
        if isinstance(ap, dict) and ap.get("body"):
            c["appr"] += 1; has = True
        if v[9]: c["famous"] += 1
        if v[3]: c["year"] += 1
        if has: c["has_anno"] += 1
    print(f"\n=== 最终覆盖 ({total} 首) ===")
    for k, v in c.items():
        print(f"  {k}: {v} ({v/total*100:.2f}%)")


if __name__ == "__main__":
    main()