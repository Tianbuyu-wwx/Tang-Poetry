# -*- coding: utf-8 -*-
"""独立生成全唐诗网页：复用 generate_poems.py 的 render_poem 模板，
仅加载 scripts/data/qts_full/ 下的 POEMS_LOCAL 数据，输出到 website/qts_poems/。
不修改现有 generate_poems.py，不污染现有 76 位诗人网页。
"""
import os, sys, importlib.util

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(BASE, "scripts", "generate_poems.py")
QTS_DIR = os.path.join(BASE, "scripts", "data", "qts_full")
OUT_DIR = os.path.join(BASE, "website", "qts_poems")
os.makedirs(OUT_DIR, exist_ok=True)

# 复用 render_poem + HTML_TEMPLATE
spec = importlib.util.spec_from_file_location("genp", GEN)
genp = importlib.util.module_from_spec(spec); spec.loader.exec_module(genp)
render_poem = genp.render_poem
HTML_TEMPLATE = genp.HTML_TEMPLATE
POET_INFO = genp.POET_INFO

# 加载 qts_full 所有 POEMS_LOCAL
POEMS = []
LIMIT = int(os.environ.get("QTS_LIMIT", "0"))
for fn in sorted(os.listdir(QTS_DIR)):
    if not (fn.startswith("poems_") and fn.endswith(".py")):
        continue
    fpath = os.path.join(QTS_DIR, fn)
    try:
        s = importlib.util.spec_from_file_location("qts." + fn[:-3], fpath)
        m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
        if hasattr(m, "POEMS_LOCAL"):
            POEMS.extend(m.POEMS_LOCAL)
    except Exception as e:
        sys.stderr.write(f"skip {fn}: {e}\n")
    if LIMIT and len(POEMS) >= LIMIT:
        break

sys.stderr.write(f"加载 {len(POEMS)} 首来自 {QTS_DIR}\n")

# 自动 prev/next
for i, poem in enumerate(POEMS):
    if i > 0:
        poem["prev"] = (POEMS[i-1]["id"], POEMS[i-1]["title"])
    if i < len(POEMS) - 1:
        poem["next"] = (POEMS[i+1]["id"], POEMS[i+1]["title"])

# 同卷诗作
by_poet = {}
for poem in POEMS:
    by_poet.setdefault(poem["poet_id"], []).append(poem)

# 生成（用 genp.render_poem，但需保证 POET_INFO 已注入——render_poem 内部用全局 POET_INFO）
import types
genp.POET_INFO = POET_INFO  # 确保

n = 0
for poem in POEMS:
    same_items = [(p["id"], p["title"], p["genre"]) for p in by_poet.get(poem["poet_id"], [])]
    try:
        html = render_poem(poem, same_poet_items=same_items)
    except Exception as e:
        sys.stderr.write(f"render fail {poem.get('id')}: {e}\n")
        continue
    out_path = os.path.join(OUT_DIR, poem["id"] + ".html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    n += 1

print(f"共生成 {n} 首诗 HTML -> {OUT_DIR}")
