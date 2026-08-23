# -*- coding: utf-8 -*-
"""从所有诗作数据中提取名句，生成 JS 数组写入 website/assets/js/famous-lines.js"""
import os
import sys
import glob
import json
import importlib.util

# 先加载 generate_poems.py 中的内置 POEMS（14 首）
gen_poems_path = os.path.join(os.path.dirname(__file__), 'generate_poems.py')
spec = importlib.util.spec_from_file_location('generate_poems', gen_poems_path)
gen_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen_mod)
all_poems = list(gen_mod.POEMS)

# 加载 scripts/data/ 下的所有诗作数据文件
data_dir = os.path.join(os.path.dirname(__file__), 'data')
for py_file in sorted(glob.glob(os.path.join(data_dir, '*.py'))):
    if py_file.endswith('__init__.py'):
        continue
    fname = os.path.basename(py_file)
    mod_name = 'poems_' + os.path.splitext(fname)[0].replace('poems_', '')
    spec = importlib.util.spec_from_file_location(mod_name, py_file)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        if hasattr(mod, 'POEMS_LOCAL'):
            all_poems.extend(mod.POEMS_LOCAL)
    except Exception as e:
        print(f'Warning: failed to load {fname}: {e}')

# 提取名句
famous_lines = []
seen = set()
for poem in all_poems:
    famous = poem.get('famous', [])
    title = poem.get('title', '')
    author = poem.get('author', '')
    for line, gloss in famous:
        # 去除 HTML 标签
        import re
        clean_line = re.sub(r'<[^>]+>', '', line).strip()
        if not clean_line or len(clean_line) < 4:
            continue
        key = clean_line[:20]
        if key in seen:
            continue
        seen.add(key)
        famous_lines.append({
            'line': clean_line,
            'source': f'—— {author}《{title}》'
        })

print(f'Total famous lines extracted: {len(famous_lines)}')

# 写入 JS 文件
js_path = os.path.join(os.path.dirname(__file__), '..', 'website', 'assets', 'js', 'famous-lines.js')
with open(js_path, 'w', encoding='utf-8') as f:
    f.write('/* ============================================================\n')
    f.write('   名句数据 · 首页随机展示\n')
    f.write(f'   共 {len(famous_lines)} 条名句，从 320 首唐诗中提取\n')
    f.write('   ============================================================ */\n\n')
    f.write('window.FAMOUS_LINES = ')
    f.write(json.dumps(famous_lines, ensure_ascii=False, indent=2))
    f.write(';\n')

print(f'Written to: {js_path}')
