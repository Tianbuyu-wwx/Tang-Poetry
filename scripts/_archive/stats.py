# -*- coding: utf-8 -*-
p = r'e:\项目\Tang Poetry\scripts\generate_poems.py'
s = open(p, encoding='utf-8').read()
lines = s.split('\n')
poems_count = s.count('POEMS.append')
print(f'Total lines: {len(lines)}')
print(f'POEMS.append count: {poems_count}')
# 找第一个 POEMS.append 和最后一个的行号
first = None
last = None
for i, l in enumerate(lines, 1):
    if 'POEMS.append' in l:
        if first is None:
            first = i
        last = i
print(f'First POEMS.append at line: {first}')
print(f'Last POEMS.append at line: {last}')
print(f'Lines for poems data: {last - first}')
print(f'Avg lines per poem: {(last - first) / poems_count:.1f}')
