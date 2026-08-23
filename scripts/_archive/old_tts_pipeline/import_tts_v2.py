#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强唐诗三百首 319 首匹配率：
1. 首句精确匹配 fallback
2. 含「无题·XXX」变体 + 首句模糊
3. 李商隐/王维/杜甫等作者扩展匹配规则
"""
import os, re, json
from pathlib import Path
from difflib import SequenceMatcher

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
POEMS_JS = ROOT / "website" / "assets" / "js" / "poems-data.js"
TTS_FILE = DOCS / "唐诗三百首.md"


def norm(s):
    s = (s or "").strip().replace("　", " ")
    s = re.sub(r"[（(][^）)]*[)）]", "", s)
    s = re.sub(r"[\s，。、；：？！·・（）()【】「」\"'""''《》]", "", s)
    return s


def parse_tts(path):
    """复用 import_tts.py 的解析"""
    text = Path(path).read_text(encoding="utf-8")
    out = {}
    parts = re.split(r'(?=^###\s+[^\n]+$)', text, flags=re.M)
    for blk in parts:
        m = re.match(r'^###\s+([^\n]+)\n', blk)
        if not m:
            continue
        title = m.group(1).strip()
        if any(x in title for x in ['编辑说明', '文档体例', '主要参考书目', '收录统计', '总目录',
                                     '卷一', '卷二', '卷三', '卷四', '卷五', '卷六',
                                     '卷七', '卷八', '卷九', '卷十']):
            continue
        am = re.search(r'\*\*作者\*\*[：:]\s*([^\n]+)', blk)
        if not am:
            continue
        author = re.sub(r"^唐代?\s*[·]?\s*", "", am.group(1).strip()).strip()
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
            'author': author, 'title': title,
            'verse': grab("原文"), 'tijie': grab("题解"),
            'notes': grab("注释"), 'appr': grab("赏析"),
            'famous': grab("名句"), 'source': grab("出处"),
        }
        out[(norm(author), norm(title))] = rec
    return out


def load_poems():
    src = POEMS_JS.read_text(encoding="utf-8")
    m = re.search(r"window\.POEMS_DATA=(.*?);$", src, re.S)
    D = json.loads(m.group(1))
    by_key = {}
    by_author = {}
    first_verse_by_author = {}  # author -> [(pid, first_line_normalized)]
    for pid, v in D.items():
        a, t = v[1] or "", v[0] or ""
        k = (norm(a), norm(t))
        by_key.setdefault(k, []).append(pid)
        by_author.setdefault(norm(a), []).append((pid, t))
        # 提取首句 (取第一句去标点)
        verse = v[5]
        if isinstance(verse, list) and verse:
            first_line = verse[0]
        else:
            first_line = ""
        nv = norm(first_line)[:25]  # 取前 25 字归一化
        if nv:
            first_verse_by_author.setdefault(norm(a), []).append((pid, nv))
    return D, by_key, by_author, first_verse_by_author


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
        if n_clean and n_clean == cn_clean:
            return pid, 0.95
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
        sm = SequenceMatcher(None, n, cn).ratio()
        if sm > best_score:
            best_score = sm
            best = pid
    return best, best_score


def main():
    print("=== 增强版 唐诗三百首注入 (首句匹配) ===")
    tts = parse_tts(TTS_FILE)
    print(f"解析: {len(tts)} 首")
    D, by_key, by_author, first_verse_by_author = load_poems()

    stats = {
        "exact": 0, "by_title_fuzzy": 0, "by_first_line": 0,
        "matched": 0, "added_verse": 0, "added_tijie": 0,
        "added_notes": 0, "added_appr": 0, "added_famous": 0,
        "unmatched": [],
    }

    # 类似 import_tts.py 的字段注入函数
    def parse_notes_field(notes_text):
        if not notes_text: return []
        out = []
        for line in notes_text.split('\n'):
            line = line.strip()
            if not line: continue
            line = re.sub(r"^[•\-*]\s*", "", line)
            if not line: continue
            m = re.match(r"^([^：:]{1,12})[：:](.+)$", line)
            if m:
                out.append([m.group(1).strip(), m.group(2).strip()])
            else:
                out.append(["", line])
        return out

    def parse_famous_field(famous_text):
        if not famous_text: return []
        out = []
        for line in famous_text.split('\n'):
            line = line.strip()
            if not line: continue
            line = re.sub(r"^[•\-*]\s*", "", line)
            if not line: continue
            m = re.match(r"^[「『\"'](.+?)[」』\"'](.*)$", line)
            if m:
                out.append([m.group(1).strip(), m.group(2).strip()])
            else:
                out.append([line, ""])
        return out

    def parse_appr_field(appr_text):
        if not appr_text: return {}
        source = ""
        m = re.search(r'[（(]([^)）]{3,30})[)）]', appr_text)
        if m:
            source = m.group(1)
        body = [x.strip() for x in re.split(r'\n+', appr_text) if x.strip()]
        return {"source": source, "body": body}

    for (author_n, title_n), rec in tts.items():
        pids = None
        match_method = None

        # 1) 精确匹配
        if (author_n, title_n) in by_key:
            pids = by_key[(author_n, title_n)]
            match_method = "exact"

        # 2) 模糊匹配 (复用 import_tts.py 的 fuzzy_match)
        if not pids and author_n in by_author:
            pid, score = fuzzy_match(title_n, by_author[author_n])
            if score >= 0.5 and pid:
                pids = [pid]
                match_method = f"fuzzy({score:.2f})"

        # 3) 首句匹配 (fallback for 「无题·XXX」)
        if not pids and author_n in first_verse_by_author:
            from difflib import SequenceMatcher
            lines = [l for l in rec['verse'].split('\n') if l.strip() and not l.startswith('>')]
            if lines:
                first_line = re.sub(r"^> ?", "", lines[0]).strip()
                n = norm(first_line)[:25]
                if n:
                    best_pid = None
                    best_sm = 0
                    for pid, pv in first_verse_by_author[author_n]:
                        if n == pv:
                            best_pid, best_sm = pid, 1.0
                            break
                        if n[:10] == pv[:10]:
                            best_pid, best_sm = pid, 0.9
                            break
                        sm = SequenceMatcher(None, n, pv).ratio()
                        if sm > best_sm:
                            best_pid, best_sm = pid, sm
                    if best_pid and best_sm >= 0.85:
                        pids = [best_pid]
                        match_method = f"first_line({best_sm:.2f})"

        if not pids:
            stats["unmatched"].append((rec['author'], rec['title']))
            continue

        stats["matched"] += 1
        if "exact" in match_method:
            stats["exact"] += 1
        elif "fuzzy" in match_method:
            stats["by_title_fuzzy"] += 1
        else:
            stats["by_first_line"] += 1

        for pid in pids:
            v = D[pid]
            # verse
            new_verse = [ln.strip() for ln in rec['verse'].split('\n')
                         if ln.strip() and not ln.startswith('>')]
            new_verse = [re.sub(r"^> ?", "", ln) for ln in new_verse]
            if new_verse and (not v[5] or len(v[5]) < 2):
                v[5] = new_verse
                stats["added_verse"] += 1

            # tijie
            if rec['tijie'] and not v[6]:
                v[6] = rec['tijie']
                stats["added_tijie"] += 1

            # notes
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

            # appr
            if rec['appr']:
                cur_ap = v[8]
                cur_body = cur_ap.get("body", []) if isinstance(cur_ap, dict) else []
                if not cur_body:
                    new_ap = parse_appr_field(rec['appr'])
                    if new_ap.get("body"):
                        v[8] = new_ap
                        stats["added_appr"] += 1

            # famous
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

    # 写出
    out = "window.POEMS_DATA=" + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";"
    POEMS_JS.write_text(out, encoding="utf-8")

    print(f"\n=== 注入结果 ===")
    for k, v in stats.items():
        if k == "unmatched":
            print(f"  未匹配: {len(v)}")
            for a, t in v:
                print(f"    - {a}《{t}》")
        else:
            print(f"  {k}: {v}")

    # 统计
    total = len(D)
    c = {"tijie": 0, "notes": 0, "appr": 0, "famous": 0, "year": 0, "has_anno": 0}
    for k, v in D.items():
        has = False
        if v[6]: c["tijie"] += 1; has = True
        if v[7]:
            for n in v[7]:
                if isinstance(n, list) and len(n) >= 2:
                    c["notes"] += 1
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