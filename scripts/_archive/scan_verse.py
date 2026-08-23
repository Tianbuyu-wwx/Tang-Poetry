# -*- coding: utf-8 -*-
"""扫描源数据中 10 首绝句的 verse 定义"""
import os
import glob
import re

target_ids = [
    'li-bai-du-zuo-jing-ting-shan',
    'li-bai-huang-he-lou-song-meng-hao-ran',
    'li-bai-jin-ling-jiu-si-liu-bie',
    'li-bai-jing-ye-si',
    'li-bai-qing-ping-diao-qi-er',
    'li-bai-qing-ping-diao-qi-san',
    'li-bai-wang-lu-shan-pu-bu',
    'li-bai-wang-tian-men-shan',
    'li-bai-zao-fa-bai-di-cheng',
    'li-bai-zeng-wang-lun',
]

files = [r'e:\项目\Tang Poetry\scripts\generate_poems.py']
files += glob.glob(r'e:\项目\Tang Poetry\scripts\data\*.py')

for fp in files:
    with open(fp, 'r', encoding='utf-8') as f:
        s = f.read()
    for tid in target_ids:
        pattern = '"id": "' + tid + '"'
        if pattern not in s:
            continue
        idx = s.find(pattern)
        verse_start = s.find('"verse":', idx)
        if verse_start == -1:
            continue
        bracket_start = s.find('[', verse_start)
        depth = 0
        end = bracket_start
        for i in range(bracket_start, min(bracket_start + 2000, len(s))):
            if s[i] == '[':
                depth += 1
            elif s[i] == ']':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        verse_block = s[verse_start:end]
        # 数 verse 中的字符串元素（行）
        str_count = verse_block.count('\n') - 1  # 粗略
        print('==> ' + tid + '  in ' + os.path.basename(fp))
        print(verse_block)
        print('---')
