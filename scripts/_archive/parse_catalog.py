# -*- coding: utf-8 -*-
"""解析古诗文网唐诗三百首目录，按诗人分组统计"""
import re

text = open(r'C:\Users\Tianbuyu\AppData\Local\Temp\trae\toolcall-output\28916cad-f09f-419f-94b2-183007c68780.txt', encoding='utf-8').read()

# 匹配 [诗题](url)(作者) 模式
pat = re.compile(r'\[([^\]]+)\]\([^)]+\)\(([^)]+)\)')
poems = []
for m in pat.finditer(text):
    title = m.group(1).strip()
    author = m.group(2).strip()
    poems.append((title, author))

# 按诗人分组
by_poet = {}
for title, author in poems:
    by_poet.setdefault(author, []).append(title)

# 按诗数排序
sorted_poets = sorted(by_poet.items(), key=lambda x: -len(x[1]))

print(f'总计: {len(poems)} 首诗, {len(by_poet)} 位诗人\n')
print('诗人诗作数统计:')
for author, titles in sorted_poets:
    print(f'  {author}: {len(titles)} 首')
    for t in titles:
        print(f'    - {t}')
