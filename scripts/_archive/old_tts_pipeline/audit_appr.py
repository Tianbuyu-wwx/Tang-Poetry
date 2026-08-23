#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校对 947 首赏析:
1. 撰稿人提取: body 首段常有 "本节主要据XX撰" 模式, 提取到 source
2. 统一 source 字段: 去掉 "赏析：" 前缀
3. 修张祜空标题 (data 错误)
4. 删去重复 (curated_00041/00061 在 import_docs 时已新增 source, 但和 open_* 重复)
5. 写回 poems-data.js + site-meta.js
"""
import os, re, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POEMS_JS = ROOT / "website" / "assets" / "js" / "poems-data.js"
META_JS = ROOT / "website" / "assets" / "js" / "site-meta.js"


def extract_writer_from_body(body):
    """从 body 首段提取撰稿人: 模式 '本节主要据XX撰' 或 '据XX《...》'"""
    if not body or not body[0]:
        return None, body
    first = body[0].strip()
    # 模式1: > **出处**: 本节主要据XX撰"..."条, 《唐诗鉴赏辞典》
    m = re.search(r'本节主要据(\S+?)撰[「"\u201c]', first)
    if m:
        return m.group(1).strip(), body
    # 模式2: > **出处**: 据XX《唐诗鉴赏辞典》"..."条（上海辞书出版社，1983 年版）
    m = re.search(r'据(\S+?)《唐诗鉴赏辞典》', first)
    if m:
        return m.group(1).strip(), body
    # 模式3: 据XX及XX《唐诗鉴赏辞典》(双作者, 取主作者)
    # 找 "据X及Y《唐诗鉴赏辞典》", 拆出第一个 X
    m = re.search(r'据(\S+?)(?:及|与)\S+?《唐诗鉴赏辞典》', first)
    if m:
        return m.group(1).strip(), body
    # 模式4: 兜底: （撰稿人名）
    m = re.search(r'（([^）]+)）', first)
    if m:
        cand = m.group(1).strip()
        if len(cand) <= 8 and re.fullmatch(r'[\u4e00-\u9fff\s·]+', cand):
            # 拒绝明显的非人名(术语/引文片段)
            if not re.search(r'(别称|云云|即|注[：:]|记[：:]|曰|释义|引|指|为|诗曰|即|以|用|作)', cand):
                return cand, [first]
    return None, body


def normalize_source(s):
    """统一 source 格式: 去掉 '赏析：' 前缀, 全角空格转半角"""
    if not s:
        return s
    s = re.sub(r'^赏析[：:]', '', s)
    s = re.sub(r'^（([^）]+)）', r'\1', s)
    # 全角空格 → 普通空格
    s = s.replace('\u3000', ' ')
    return re.sub(r'\s+', ' ', s).strip()


def main():
    print("=== 赏析校对 ===")
    src = POEMS_JS.read_text(encoding="utf-8")
    m = re.search(r"window\.POEMS_DATA=(.*?);$", src, re.S)
    D = json.loads(m.group(1))

    stats = {
        "extracted_writer": 0,
        "normalized_source": 0,
        "fixed_empty_title": 0,
        "removed_duplicate": 0,
    }

    # 1) 提取撰稿人 + 统一 source
    for k, v in D.items():
        ap = v[8]
        if not (isinstance(ap, dict) and ap.get("body")):
            continue
        body = ap["body"]
        cur_source = ap.get("source", "")

        # 清理: 若当前 source 是术语/引文片段(如"别称"子规""), 清空
        if cur_source:
            non_person = ("别称", "云云", "注[：:]", "记[：:]", "诗曰", "释义")
            is_bad = any(p in cur_source for p in non_person) or cur_source.startswith("见") or cur_source.startswith("即")
            if is_bad:
                ap["source"] = ""
                cur_source = ""
                ap["body"] = []
                stats["removed_garbage"] = stats.get("removed_garbage", 0) + 1
        # 清理: body 存在但 source 空(上轮清除遗留) → 也清 body
        if not cur_source and body:
            ap["body"] = []

        # 从 body 首段提取
        writer, new_body = extract_writer_from_body(body)
        # 若当前 source 是"出版社/书名"等非人名, 用提取的 writer 替换
        if writer:
            NON_PERSON = ("出版社", "书局", "年版", "百科", "辞典,", "《")
            is_non_person = any(s in cur_source for s in NON_PERSON) or not cur_source
            if is_non_person and writer != cur_source:
                ap["source"] = writer
                if not cur_source:
                    stats["extracted_writer"] += 1
                else:
                    stats["normalized_source"] += 1

        # 统一已有 source
        if cur_source:
            new_s = normalize_source(cur_source)
            if new_s != cur_source and new_s != ap.get("source", ""):
                ap["source"] = new_s
                stats["normalized_source"] += 1

        # 2) 修张祜空标题: 根据 source 提及的诗名补
        if not v[0].strip():
            if "宫词" in str(body[0]) if body else False:
                v[0] = "宫词"
                stats["fixed_empty_title"] += 1

    # 3) 删重复 (curated_00041/00061 已在 open_000xx 存在)
    title_to_pids = {}
    for k, v in D.items():
        key = (v[1], v[0])
        title_to_pids.setdefault(key, []).append(k)

    to_delete = []
    for key, pids in title_to_pids.items():
        if len(pids) > 1 and any(p.startswith("curated_") for p in pids):
            # 删 curated 重复, 保留 open
            for p in pids:
                if p.startswith("curated_"):
                    to_delete.append(p)
    for p in to_delete:
        del D[p]
        stats["removed_duplicate"] += 1

    # 写回
    out = "window.POEMS_DATA=" + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";"
    POEMS_JS.write_text(out, encoding="utf-8")

    # 更新 site-meta
    annotated = sum(1 for v in D.values()
                    if v[6] or v[7] or (isinstance(v[8], dict) and v[8].get("body")))
    src2 = META_JS.read_text(encoding="utf-8")
    m2 = re.search(r"window\.SITE_META=(.*?);$", src2, re.S)
    meta = json.loads(m2.group(1))
    meta["annotated"] = annotated
    META_JS.write_text(
        "window.SITE_META=" + json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + ";",
        encoding="utf-8"
    )

    # 报告
    print(f"\n=== 校对结果 ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"\n最终带批注诗: {annotated}")

    # 最终覆盖
    total = len(D)
    c = {"tijie": 0, "notes_real": 0, "appr": 0, "appr_with_source": 0, "famous": 0, "year": 0}
    for k, v in D.items():
        if v[6]: c["tijie"] += 1
        if v[7]:
            for n in v[7]:
                if isinstance(n, list) and len(n) >= 2:
                    c["notes_real"] += 1
                    break
        ap = v[8]
        if isinstance(ap, dict) and ap.get("body"):
            c["appr"] += 1
            if ap.get("source"):
                c["appr_with_source"] += 1
        if v[9]: c["famous"] += 1
        if v[3]: c["year"] += 1
    print(f"\n=== 最终覆盖 ({total} 首) ===")
    for k, v in c.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()