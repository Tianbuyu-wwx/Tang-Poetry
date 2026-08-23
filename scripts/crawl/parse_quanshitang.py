# -*- coding: utf-8 -*-
"""解析本地《全唐诗》(曹寅.txt, GB18030) -> 结构化 JSON。
格式: [{vol, title, author, verse:[...], raw_block}]
字段对齐网站: 后续由 build 脚本补全。
"""
import re, json, os

SRC = os.environ.get("TANG_POETRY_SOURCE", "")
OUT = os.path.join(os.path.dirname(__file__), "all_tang_poems.json")

if not SRC:
    raise SystemExit("请先设置 TANG_POETRY_SOURCE，指向 GB18030 编码的《全唐诗》文本。")

def parse():
    raw = open(SRC, "rb").read().decode("gb18030")
    # 标题行: ◎卷.N【题】作者
    head = re.compile(r"◎卷\.(\d+)【(.+?)】(.+?)\r")
    # 按标题切分
    matches = list(head.finditer(raw))
    poems = []
    for i, m in enumerate(matches):
        vol = int(m.group(1))
        title = m.group(2).strip()
        author = m.group(3).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        block = raw[start:end]
        # 去掉全角/半角缩进与空行，按换行分句
        lines = []
        for ln in block.split("\r\n"):
            ln = ln.strip()
            # 全角空格缩进去除（全唐诗每句前有的　）
            ln = ln.lstrip("　").strip()
            if ln:
                lines.append(ln)
        # 过滤掉疑似非诗内容（如残留 html 片段极少见）
        if not lines:
            continue
        poems.append({
            "vol": vol,
            "title": title,
            "author": author,
            "verse": lines,
        })
    return poems

if __name__ == "__main__":
    poems = parse()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(poems, f, ensure_ascii=False, indent=1)
    # 统计
    from collections import Counter
    auth = Counter(p["author"] for p in poems)
    vols = sorted(set(p["vol"] for p in poems))
    print("解析完成:")
    print("  总诗数:", len(poems))
    print("  卷数:", len(vols), "范围", vols[0], "~", vols[-1])
    print("  去重作者:", len(auth))
    print("  样例(前3):")
    for p in poems[:3]:
        print("   ", p["vol"], p["title"], p["author"], "句数", len(p["verse"]))
    print("  输出:", OUT)
