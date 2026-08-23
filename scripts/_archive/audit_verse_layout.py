# -*- coding: utf-8 -*-
"""扫描所有诗页面，检查 verse 分段情况"""
import os
import glob
import re

folder = r'e:\项目\Tang Poetry\website\poems'

issues_jueju = []  # 绝句应为 2 段
issues_lushi = []  # 律诗应为 4 段
issues_other = []

for fp in sorted(glob.glob(os.path.join(folder, '*.html'))):
    with open(fp, 'r', encoding='utf-8') as f:
        s = f.read()
    m = re.search(r'<div class="verse">(.*?)</div>', s, re.DOTALL)
    if not m:
        continue
    verse_html = m.group(1)
    p_count = len(re.findall(r'<p>', verse_html))
    m2 = re.search(r'<span class="meta-value">([^<]*?(?:绝句|律诗|古诗|乐府))', s)
    genre = m2.group(1) if m2 else '?'
    fname = os.path.basename(fp)

    if '绝句' in genre and p_count != 2:
        issues_jueju.append((fname, genre, p_count))
    elif '律诗' in genre and p_count != 4:
        issues_lushi.append((fname, genre, p_count))
    elif '古诗' in genre or '乐府' in genre:
        # 古诗和乐府不限分段
        pass

print(f'绝句分段异常（应为 2 段一联）：{len(issues_jueju)} 首')
for f, g, p in issues_jueju[:50]:
    print(f'  {f}  [{g}]  p={p}')

print(f'\n律诗分段异常（应为 4 段一联）：{len(issues_lushi)} 首')
for f, g, p in issues_lushi[:50]:
    print(f'  {f}  [{g}]  p={p}')
