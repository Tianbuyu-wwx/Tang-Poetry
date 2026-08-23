"""列出 generate_poems.py 内置的 POEMS（不含数据文件）。"""
import sys
sys.path.insert(0, r'e:\项目\Tang Poetry\scripts')
# 阻止加载数据文件
import os
def _no_load(*a, **kw):
    print('(跳过数据文件加载)')
    return []
import importlib.util
_orig = importlib.util.spec_from_file_location

# 先读取 generate_poems.py 源码，只执行 POEMS 列表部分
with open(r'e:\项目\Tang Poetry\scripts\generate_poems.py', encoding='utf-8') as f:
    src = f.read()

# 找 POEMS = [] 到 load_data_from_files() 之间
start = src.find('POEMS = []')
end = src.find('def load_extra_data')
if start == -1 or end == -1:
    print('无法定位 POEMS 定义')
    sys.exit(1)
builtin_src = src[start:end]
ns = {'__file__': r'e:\项目\Tang Poetry\scripts\generate_poems.py'}
exec(builtin_src, ns)
POEMS = ns['POEMS']
print(f'内置 POEMS 数: {len(POEMS)}')
for i, p in enumerate(POEMS, 1):
    print(f'{i:2d}. [{p["author"]}] {p["title"]} ({p["genre"]}) id={p["id"]}')
