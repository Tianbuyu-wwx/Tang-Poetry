# -*- coding: utf-8 -*-
"""扫描 poets/index.html 中所有诗人卡片的 seal 和 count"""
import re

with open(r'e:\项目\Tang Poetry\website\poets\index.html', 'r', encoding='utf-8') as f:
    s = f.read()

# 提取每个 poet-card 的 seal 和 count
cards = re.findall(
    r'<div class="poet-card" id="([^"]+)"[^>]*>.*?<span class="seal">([^<]*)</span>.*?<div class="count">([^<]*)</div>',
    s, re.DOTALL)

print(f'Total poet cards: {len(cards)}')

empty_seal = [c for c in cards if not c[1].strip()]
print(f'Empty seal: {len(empty_seal)}')
for c in empty_seal[:10]:
    print(f'  {c[0]}: seal="{c[1]}" count="{c[2]}"')

zero_count = [c for c in cards if '0 首' in c[2]]
print(f'Zero count: {len(zero_count)}')
for c in zero_count[:10]:
    print(f'  {c[0]}: seal="{c[1]}" count="{c[2]}"')

odd_count = [c for c in cards if '首诗作' not in c[2]]
print(f'Odd count format: {len(odd_count)}')
for c in odd_count[:10]:
    print(f'  {c[0]}: seal="{c[1]}" count="{c[2]}"')

# 列出所有 count
print('\nAll cards (id -> seal, count):')
for c in cards:
    print(f'  {c[0]}: seal="{c[1]}" count="{c[2]}"')
