#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除:
1. 167 首空标题诗 (chinese-poetry 底本组诗子项缺失)
2. 25 项赏析 source 为空 (撰稿人信息原书就缺失)

策略: 不删整个诗, 只清空源字段
- 空标题: 清空 v[0] (title), 但保留 verse 主体 (部分诗正文完整)
  - 更合理: 删整首 (空标题 = 无意义的数据, 不应被检索)
- source 为空: 清空 v[8] (appr), 诗的其他字段保留
"""
import os, re, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POEMS_JS = ROOT / "website" / "assets" / "js" / "poems-data.js"
META_JS = ROOT / "website" / "assets" / "js" / "site-meta.js"


def main():
    print("=== 清理空标题诗 + 空 source 赏析 ===")
    src = POEMS_JS.read_text(encoding="utf-8")
    m = re.search(r"window\.POEMS_DATA=(.*?);$", src, re.S)
    D = json.loads(m.group(1))
    initial = len(D)

    # 1) 删空标题诗
    empty_title_pids = []
    for k, v in D.items():
        if not v[0].strip():
            empty_title_pids.append(k)
    for p in empty_title_pids:
        del D[p]
    print(f"删除空标题诗: {len(empty_title_pids)} 首")

    # 2) 清空 source 为空的赏析
    cleared_appr = 0
    for k, v in D.items():
        ap = v[8]
        if isinstance(ap, dict) and ap.get("body") and not ap.get("source", "").strip():
            v[8] = {}
            cleared_appr += 1
    print(f"清空 source 为空的赏析: {cleared_appr} 项")

    # 写回
    out = "window.POEMS_DATA=" + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";"
    POEMS_JS.write_text(out, encoding="utf-8")

    # 更新 site-meta
    annotated = sum(1 for v in D.values()
                    if v[6] or v[7] or (isinstance(v[8], dict) and v[8].get("body")))
    src2 = META_JS.read_text(encoding="utf-8")
    m2 = re.search(r"window\.SITE_META=(.*?);$", src2, re.S)
    meta = json.loads(m2.group(1))
    meta["poems"] = len(D)
    meta["annotated"] = annotated
    META_JS.write_text(
        "window.SITE_META=" + json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + ";",
        encoding="utf-8"
    )

    # 报告
    print(f"\n总诗数: {initial} → {len(D)} (删 {initial - len(D)} 首)")
    print(f"带批注诗: {annotated}")

    # 最终覆盖
    total = len(D)
    c = {"tijie": 0, "notes_real": 0, "appr": 0, "appr_with_src": 0, "famous": 0, "year": 0}
    for k, v in D.items():
        if v[6]: c["tijie"] += 1
        if v[7]:
            for n in v[7]:
                if isinstance(n, list) and len(n) >= 2:
                    c["notes_real"] += 1; break
        ap = v[8]
        if isinstance(ap, dict) and ap.get("body"):
            c["appr"] += 1
            if ap.get("source"): c["appr_with_src"] += 1
        if v[9]: c["famous"] += 1
        if v[3]: c["year"] += 1
    print(f"\n=== 最终覆盖 ({total} 首) ===")
    for k, v in c.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()